#!/usr/bin/env bash
# Installiert die ISO wie der Calamares-Installer auf eine virtuelle Platte, damit CI das
# installierte System anschließend booten kann.
#   uefi: GPT mit EFI-Partition + ext4      bios: MBR mit einer ext4-Partition (wie „Festplatte löschen“)
#   sudo tools/ci-install-test.sh out/frametide-os-*.iso disk.img [uefi|bios]
set -euo pipefail
ISO="$1"; DISK="$2"; MODE="${3:-uefi}"; MNT=/mnt/ft-install
log() { printf '\n==> %s\n' "$*"; }
cleanup() {
    for m in run sys/firmware/efi/efivars sys proc dev/pts dev boot/efi ""; do
        mountpoint -q "$MNT/$m" 2>/dev/null && umount -lf "$MNT/$m"
    done
    mountpoint -q /mnt/ft-sq && umount -lf /mnt/ft-sq
    mountpoint -q /mnt/ft-iso && umount -lf /mnt/ft-iso
    for l in ${LOOPS:-}; do losetup -d "$l" 2>/dev/null || true; done
}
trap cleanup EXIT

rm -f "$DISK"; truncate -s 40G "$DISK"
# Partitionen über ihre Position in der Image-Datei einhängen (Runner-Kernel legen
# für Loop-Geräte nicht immer Partitionsgeräte an)
loop_at() { losetup -f --show -o $(($1 * 512)) --sizelimit $((($2 - $1 + 1) * 512)) "$DISK"; }
if [ "$MODE" = uefi ]; then
    log "Platte partitionieren (GPT: 512 MB EFI + ext4)"
    sgdisk -n1:0:+512M -t1:ef00 -n2:0:0 -t2:8304 "$DISK" >/dev/null
    sector() { sgdisk -i "$1" "$DISK" | awk -v k="$2" '$0 ~ k {print $3}'; }
    EFI_DEV=$(loop_at "$(sector 1 "First sector")" "$(sector 1 "Last sector")")
    ROOT_DEV=$(loop_at "$(sector 2 "First sector")" "$(sector 2 "Last sector")")
    LOOPS="$EFI_DEV $ROOT_DEV"
    echo "EFI: $EFI_DEV  Root: $ROOT_DEV"
    mkfs.vfat -F32 -n EFI "$EFI_DEV" >/dev/null
else
    log "Platte partitionieren (MBR: eine ext4-Partition)"
    printf 'label: dos\nstart=2048, type=83, bootable\n' | sfdisk -q "$DISK"
    DISK_DEV=$(losetup -f --show "$DISK")
    ROOT_DEV=$(loop_at 2048 $(($(stat -c %s "$DISK") / 512 - 1)))
    LOOPS="$DISK_DEV $ROOT_DEV"
    echo "Platte: $DISK_DEV  Root: $ROOT_DEV"
fi
mkfs.ext4 -q -L frametide "$ROOT_DEV"

log "System entpacken (wie Calamares unpackfs)"
mkdir -p /mnt/ft-iso /mnt/ft-sq "$MNT"
mount -o loop,ro "$ISO" /mnt/ft-iso
mount -t squashfs -o loop,ro /mnt/ft-iso/casper/filesystem.squashfs /mnt/ft-sq
mount -o noatime "$ROOT_DEV" "$MNT"
rsync -aHAXSr --filter='-x trusted.overlay.*' --exclude /proc/ --exclude /sys/ --exclude /dev/ \
    --exclude /run/ --exclude /run/udev/ /mnt/ft-sq/ "$MNT/"
[ "$MODE" = uefi ] && mkdir -p "$MNT/boot/efi" && mount "$EFI_DEV" "$MNT/boot/efi"
for d in dev dev/pts proc sys run; do mkdir -p "$MNT/$d"; mount --bind "/$d" "$MNT/$d"; done
mkdir -p "$MNT/cdrom" && mount --bind /mnt/ft-iso "$MNT/cdrom"

log "fstab, machine-id, Testbenutzer"
printf 'UUID=%s / ext4 defaults,noatime 0 1\n' "$(blkid -s UUID -o value "$ROOT_DEV")" > "$MNT/etc/fstab"
if [ "$MODE" = uefi ]; then
    printf 'UUID=%s /boot/efi vfat umask=0077 0 1\n' "$(blkid -s UUID -o value "$EFI_DEV")" >> "$MNT/etc/fstab"
fi
chroot "$MNT" systemd-machine-id-setup >/dev/null
chroot "$MNT" useradd -m -s /bin/bash -G sudo,video,render,gamemode -c "Test" tester 2>/dev/null \
    || chroot "$MNT" useradd -m -s /bin/bash -G sudo -c "Test" tester
echo "tester:frametide" | chroot "$MNT" chpasswd
echo "frametide-test" > "$MNT/etc/hostname"

log "Live-Pakete entfernen (Calamares: packages)"
chroot "$MNT" env DEBIAN_FRONTEND=noninteractive apt-get -y remove frametide-live calamares casper

log "Initramfs (Calamares: shellprocess@initramfs)"
chroot "$MNT" /usr/lib/frametide/update-initramfs-all

log "GRUB-Paket und Bootloader (Calamares: grubpkg + bootloader)"
chroot "$MNT" env FRAMETIDE_BOOT_MODE="$([ "$MODE" = uefi ] && echo efi || echo pc)" \
    /usr/lib/frametide/install-grub-package
if [ "$MODE" = uefi ]; then
    chroot "$MNT" grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=ubuntu \
        --uefi-secure-boot --no-nvram
    # Fallback-Pfad EFI/BOOT (wie Calamares installEFIFallback) – startet auch ohne NVRAM-Eintrag
    chroot "$MNT" grub-install --target=x86_64-efi --efi-directory=/boot/efi --uefi-secure-boot \
        --no-nvram --removable
else
    # Root liegt hier auf einem eigenen Loop-Gerät statt auf der Partition → Module explizit
    chroot "$MNT" grub-install --target=i386-pc --modules="part_msdos ext2" "$DISK_DEV"
fi
chroot "$MNT" update-grub
[ "$MODE" = uefi ] && ls -R "$MNT/boot/efi/EFI" | head -20
ls "$MNT/boot"
log "Installation abgeschlossen"
