#!/usr/bin/env bash
# Frametide OS – ISO-Build
#
#   sudo ./build.sh            alles bauen (Pakete -> Root-Dateisystem -> ISO)
#   sudo ./build.sh rootfs     nur Root-Dateisystem
#   sudo ./build.sh iso        nur ISO aus vorhandenem Root-Dateisystem
#   sudo ./build.sh clean      Arbeitsverzeichnis löschen
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=config/frametide.conf
source "$ROOT/config/frametide.conf"
WORK="${WORK:-$ROOT/work}"
OUT="${OUT:-$ROOT/out}"
CHROOT="$WORK/chroot"
ISODIR="$WORK/iso"
# Signaturschlüssel der Hersteller-Paketquellen
declare -A REPO_KEYS=(
    [mozilla]="https://packages.mozilla.org/apt/repo-signing-key.gpg"
    [vscode]="https://packages.microsoft.com/keys/microsoft.asc"
    [google-chrome]="https://dl.google.com/linux/linux_signing_key.pub"
    [github-cli]="https://cli.github.com/packages/githubcli-archive-keyring.gpg"
    [github-desktop]="https://mirror.mwt.me/shiftkey-desktop/gpgkey"
    [coolercontrol]="https://dl.cloudsmith.io/public/coolercontrol/coolercontrol/gpg.key"
    [mise]="https://mise.jdx.dev/gpg-key.pub"
)

# Erste existierende Datei aus einer Liste (ohne Fehler, wenn keine existiert)
first_file() { local f; for f in "$@"; do [ -f "$f" ] && { echo "$f"; return 0; }; done; return 0; }
log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\033[1;31mFehler: %s\033[0m\n' "$*" >&2; exit 1; }

require() {
    [ "$EUID" -eq 0 ] || die "bitte mit sudo ausführen"
    local missing=()
    for cmd in debootstrap mksquashfs xorriso mkfs.vfat mcopy curl rsvg-convert dpkg-deb; do
        command -v "$cmd" >/dev/null || missing+=("$cmd")
    done
    [ ${#missing[@]} -eq 0 ] || die "fehlende Werkzeuge: ${missing[*]}
  sudo apt install debootstrap squashfs-tools xorriso dosfstools mtools curl librsvg2-bin"
}

unmount_chroot() {
    for m in run dev/pts dev sys proc; do
        mountpoint -q "$CHROOT/$m" && umount -lf "$CHROOT/$m"
    done
    return 0
}
trap unmount_chroot EXIT

mount_chroot() {
    mount --bind /dev "$CHROOT/dev"
    mount -t devpts devpts "$CHROOT/dev/pts"
    mount -t proc proc "$CHROOT/proc"
    mount -t sysfs sysfs "$CHROOT/sys"
    mount -t tmpfs tmpfs "$CHROOT/run"
}

build_rootfs() {
    log "Frametide-Pakete bauen"
    rm -rf "$OUT/debs"
    "$ROOT/packages/build-debs.sh" "$OUT/debs"

    log "Ubuntu $UBUNTU_VERSION ($UBUNTU_SUITE) Grundsystem"
    # Ältere debootstrap-Versionen kennen neue Ubuntu-Codenamen noch nicht
    [ -e "/usr/share/debootstrap/scripts/$UBUNTU_SUITE" ] ||
        ln -s gutsy "/usr/share/debootstrap/scripts/$UBUNTU_SUITE"
    unmount_chroot
    rm -rf "$CHROOT"
    mkdir -p "$CHROOT"
    debootstrap --arch="$ARCH" --components=main,restricted,universe,multiverse \
        --include=ca-certificates,gpg \
        "$UBUNTU_SUITE" "$CHROOT" "$MIRROR"

    log "System im Chroot einrichten"
    mount_chroot
    mkdir -p "$CHROOT/tmp/frametide/debs"
    cp "$ROOT/config/frametide.conf" "$ROOT/scripts/chroot-install.sh" "$CHROOT/tmp/frametide/"
    cp "$OUT"/debs/*.deb "$CHROOT/tmp/frametide/debs/"
    log "Schlüssel der Hersteller-Paketquellen"
    mkdir -p "$CHROOT/tmp/frametide/keys"
    for name in "${!REPO_KEYS[@]}"; do
        curl -fsSL "${REPO_KEYS[$name]}" -o "$CHROOT/tmp/frametide/keys/$name.key"
    done
    log "ArtCraft-Apps herunterladen und prüfen"
    "$ROOT/tools/fetch-craft.py" "$CHROOT/tmp/frametide/craft" $CRAFT_PREINSTALL
    rm -f "$CHROOT/etc/resolv.conf"
    cp -L /etc/resolv.conf "$CHROOT/etc/resolv.conf"
    # Keine Dienste während des Builds starten
    printf '#!/bin/sh\nexit 101\n' > "$CHROOT/usr/sbin/policy-rc.d"
    chmod 755 "$CHROOT/usr/sbin/policy-rc.d"

    chroot "$CHROOT" /tmp/frametide/chroot-install.sh

    rm -f "$CHROOT/usr/sbin/policy-rc.d"
    ln -sf ../run/systemd/resolve/stub-resolv.conf "$CHROOT/etc/resolv.conf"
    unmount_chroot
}

build_iso() {
    [ -d "$CHROOT/boot" ] || die "kein Root-Dateisystem – zuerst: sudo ./build.sh rootfs"
    log "ISO-Struktur"
    rm -rf "$ISODIR"
    mkdir -p "$ISODIR"/{casper,.disk,EFI/boot,boot/grub/i386-pc,boot/grub/fonts}

    local kernel initrd
    kernel="$(find "$CHROOT/boot" -maxdepth 1 -name 'vmlinuz-*' | sort -V | tail -1)"
    [ -n "$kernel" ] || die "kein Kernel im Root-Dateisystem"
    initrd="$CHROOT/boot/initrd.img-${kernel##*/vmlinuz-}"
    cp "$kernel" "$ISODIR/casper/vmlinuz"
    cp "$initrd" "$ISODIR/casper/initrd"

    chroot "$CHROOT" dpkg-query -W --showformat='${Package} ${Version}\n' > "$ISODIR/casper/filesystem.manifest"
    printf '%s\n' casper calamares frametide-live > "$ISODIR/casper/filesystem.manifest-remove"
    du -sx --block-size=1 "$CHROOT" | cut -f1 > "$ISODIR/casper/filesystem.size"
    echo "$DISTRO_NAME $DISTRO_VERSION \"$DISTRO_CODENAME_PRETTY\" - $ARCH ($(date +%Y%m%d))" > "$ISODIR/.disk/info"

    log "SquashFS komprimieren (zstd – schnelles Entpacken = schneller Live-Start)"
    mksquashfs "$CHROOT" "$ISODIR/casper/filesystem.squashfs" \
        -noappend -comp zstd -Xcompression-level 19 -b 1M -wildcards -e 'proc/*' 'sys/*' 'dev/*' 'run/*' 'tmp/*'

    log "Bootloader (BIOS + UEFI mit Secure Boot)"
    sed -e "s|@DISTRO_NAME@|$DISTRO_NAME|g" -e "s|@DISTRO_VERSION@|$DISTRO_VERSION|g" \
        "$ROOT/iso/grub.cfg" > "$ISODIR/boot/grub/grub.cfg"
    cp "$CHROOT/usr/share/grub/unicode.pf2" "$ISODIR/boot/grub/fonts/"

    # BIOS: fertiges El-Torito-Image aus grub-pc-bin (wie Ubuntus eigene ISOs) + Module
    cp "$CHROOT/usr/lib/grub/i386-pc/eltorito.img" "$ISODIR/boot/grub/i386-pc/eltorito.img"
    cp "$CHROOT"/usr/lib/grub/i386-pc/*.mod "$CHROOT"/usr/lib/grub/i386-pc/*.lst "$ISODIR/boot/grub/i386-pc/"

    # UEFI: von Microsoft/Canonical signierte shim + GRUB -> bootet mit aktivem Secure Boot
    local shim grub mm
    shim="$(first_file "$CHROOT"/usr/lib/shim/shimx64.efi.signed.latest "$CHROOT"/usr/lib/shim/shimx64.efi.signed)"
    mm="$(first_file "$CHROOT"/usr/lib/shim/mmx64.efi.signed "$CHROOT"/usr/lib/shim/mmx64.efi)"
    grub="$CHROOT/usr/lib/grub/x86_64-efi-signed/gcdx64.efi.signed"
    [ -f "$shim" ] && [ -f "$grub" ] || die "signierte shim/GRUB nicht gefunden"
    cp "$shim" "$ISODIR/EFI/boot/bootx64.efi"
    cp "$grub" "$ISODIR/EFI/boot/grubx64.efi"
    if [ -n "$mm" ]; then cp "$mm" "$ISODIR/EFI/boot/mmx64.efi"; fi

    local efiimg="$WORK/efiboot.img"
    rm -f "$efiimg"
    truncate -s 10M "$efiimg"
    mkfs.vfat -F 12 -n FRAMETIDE "$efiimg" >/dev/null
    mmd -i "$efiimg" ::/EFI ::/EFI/boot
    mcopy -i "$efiimg" "$ISODIR"/EFI/boot/*.efi ::/EFI/boot/

    log "ISO erzeugen"
    mkdir -p "$OUT"
    xorriso -as mkisofs -r -V "$ISO_LABEL" -J -joliet-long -l -iso-level 3 \
        -partition_offset 16 \
        --grub2-mbr "$CHROOT/usr/lib/grub/i386-pc/boot_hybrid.img" \
        --mbr-force-bootable \
        -append_partition 2 0xEF "$efiimg" -appended_part_as_gpt \
        -c boot.catalog \
        -b boot/grub/i386-pc/eltorito.img -no-emul-boot -boot-load-size 4 -boot-info-table --grub2-boot-info \
        -eltorito-alt-boot -e '--interval:appended_partition_2:all::' -no-emul-boot \
        -o "$OUT/$ISO_NAME" "$ISODIR"
    (cd "$OUT" && sha256sum "$ISO_NAME" > "$ISO_NAME.sha256")
    log "Fertig: $OUT/$ISO_NAME ($(du -h "$OUT/$ISO_NAME" | cut -f1))"
}

case "${1:-all}" in
    all)    require; build_rootfs; build_iso ;;
    rootfs) require; build_rootfs ;;
    iso)    require; build_iso ;;
    clean)  [ "$EUID" -eq 0 ] || die "bitte mit sudo ausführen"; unmount_chroot; rm -rf "$WORK" ;;
    *)      die "unbekannter Befehl: $1 (all|rootfs|iso|clean)" ;;
esac
