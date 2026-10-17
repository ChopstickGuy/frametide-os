#!/usr/bin/env bash
# Installiert die ISO wie der Calamares-Installer auf eine virtuelle Platte (UEFI, GPT),
# damit CI das installierte System anschließend booten kann.
#   sudo tools/ci-install-test.sh out/frametide-os-*.iso disk.img
set -euo pipefail
ISO="$1"; DISK="$2"; MNT=/mnt/ft-install
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

log "Platte partitionieren (GPT: 512 MB EFI + ext4)"
rm -f "$DISK"; truncate -s 40G "$DISK"
sgdisk -n1:0:+512M -t1:ef00 -n2:0:0 -t2:8304 "$DISK" >/dev/null
# Partitionen über ihre Position in der Image-Datei einhängen (Runner-Kernel legen
# für Loop-Geräte nicht immer Partitionsgeräte an)
part_loop() {
    local first last
    first=$(sgdisk -i "$1" "$DISK" | awk '/First sector/{print $3}')
    last=$(sgdisk -i "$1" "$DISK" | awk '/Last sector/{print $3}')
    losetup -f --show -o $((first * 512)) --sizelimit $(((last - first + 1) * 512)) "$DISK"
}
EFI_DEV=$(part_loop 1); ROOT_DEV=$(part_loop 2)
LOOPS="$EFI_DEV $ROOT_DEV"
echo "EFI: $EFI_DEV  Root: $ROOT_DEV"
mkfs.vfat -F32 -n EFI "$EFI_DEV" >/dev/null
mkfs.ext4 -q -L frametide "$ROOT_DEV"

log "System entpacken (wie Calamares unpackfs)"
mkdir -p /mnt/ft-iso /mnt/ft-sq "$MNT"
mount -o loop,ro "$ISO" /mnt/ft-iso
mount -t squashfs -o loop,ro /mnt/ft-iso/casper/filesystem.squashfs /mnt/ft-sq
mount -o noatime "$ROOT_DEV" "$MNT"
rsync -aHAXSr --filter='-x trusted.overlay.*' --exclude /proc/ --exclude /sys/ --exclude /dev/ \
    --exclude /run/ --exclude /run/udev/ /mnt/ft-sq/ "$MNT/"
mkdir -p "$MNT/boot/efi" && mount "$EFI_DEV" "$MNT/boot/efi"
for d in dev dev/pts proc sys run; do mkdir -p "$MNT/$d"; mount --bind "/$d" "$MNT/$d"; done
mkdir -p "$MNT/cdrom" && mount --bind /mnt/ft-iso "$MNT/cdrom"

log "fstab, machine-id, Testbenutzer"
root_uuid=$(blkid -s UUID -o value "$ROOT_DEV"); efi_uuid=$(blkid -s UUID -o value "$EFI_DEV")
printf 'UUID=%s / ext4 defaults,noatime 0 1\nUUID=%s /boot/efi vfat umask=0077 0 1\n' "$root_uuid" "$efi_uuid" > "$MNT/etc/fstab"
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
chroot "$MNT" env DEBIAN_FRONTEND=noninteractive sh -c 'dpkg -i /var/cache/frametide/grub/grub-efi-amd64_*.deb && rm -rf /var/cache/frametide/grub'
chroot "$MNT" grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=ubuntu \
    --uefi-secure-boot --no-nvram --force-extra-removable
chroot "$MNT" update-grub
ls -R "$MNT/boot/efi/EFI" | head -20
ls "$MNT/boot"
log "Installation abgeschlossen"
