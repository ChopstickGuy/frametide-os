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
    [ -n "${LOOP:-}" ] && losetup -d "$LOOP" 2>/dev/null || true
}
trap cleanup EXIT

log "Platte partitionieren (GPT: 512 MB EFI + ext4)"
rm -f "$DISK"; truncate -s 40G "$DISK"
sgdisk -q -n1:0:+512M -t1:ef00 -c1:EFI -n2:0:0 -t2:8304 -c2:root "$DISK"
LOOP=$(losetup -Pf --show "$DISK")
partx -u "$LOOP" 2>/dev/null || true
udevadm settle 2>/dev/null || true
for _ in $(seq 20); do [ -b "${LOOP}p2" ] && break; sleep 0.5; done
# Ohne udev (z. B. in Containern) die Partitionsgeräte selbst anlegen
for n in 1 2; do
    dev="${LOOP}p$n"; sys="/sys/block/$(basename "$LOOP")/$(basename "$LOOP")p$n/dev"
    if [ ! -b "$dev" ] && [ -f "$sys" ]; then
        IFS=: read -r major minor < "$sys"; mknod "$dev" b "$major" "$minor"
    fi
done
[ -b "${LOOP}p2" ] || { echo "Partitionen nicht gefunden"; exit 1; }
mkfs.vfat -F32 -n EFI "${LOOP}p1" >/dev/null
mkfs.ext4 -q -L frametide "${LOOP}p2"

log "System entpacken (wie Calamares unpackfs)"
mkdir -p /mnt/ft-iso /mnt/ft-sq "$MNT"
mount -o loop,ro "$ISO" /mnt/ft-iso
mount -t squashfs -o loop,ro /mnt/ft-iso/casper/filesystem.squashfs /mnt/ft-sq
mount -o noatime "${LOOP}p2" "$MNT"
rsync -aHAXSr --filter='-x trusted.overlay.*' --exclude /proc/ --exclude /sys/ --exclude /dev/ \
    --exclude /run/ --exclude /run/udev/ /mnt/ft-sq/ "$MNT/"
mkdir -p "$MNT/boot/efi" && mount "${LOOP}p1" "$MNT/boot/efi"
for d in dev dev/pts proc sys run; do mkdir -p "$MNT/$d"; mount --bind "/$d" "$MNT/$d"; done
mkdir -p "$MNT/cdrom" && mount --bind /mnt/ft-iso "$MNT/cdrom"

log "fstab, machine-id, Testbenutzer"
root_uuid=$(blkid -s UUID -o value "${LOOP}p2"); efi_uuid=$(blkid -s UUID -o value "${LOOP}p1")
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
