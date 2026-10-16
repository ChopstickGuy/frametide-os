#!/usr/bin/env bash
# Baut alle Vektor-Pakete nach out/debs/ (kein root nötig).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$(dirname "$here")"
# shellcheck source=../config/vektor.conf
source "$root/config/vektor.conf"
out="${1:-$root/out/debs}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$out"

# Boot-Logo (Plymouth) als PNG rendern
watermark="$here/vektor-desktop/usr/share/plymouth/themes/spinner/watermark.png"
if command -v rsvg-convert >/dev/null; then
    rsvg-convert -w 128 -h 128 "$root/artwork/logo.svg" -o "$watermark"
elif [ ! -f "$watermark" ]; then
    echo "WARNUNG: rsvg-convert fehlt – Boot-Logo wird ohne Wasserzeichen gebaut" >&2
fi

for pkg in "$here"/vektor-*/; do
    name="$(basename "$pkg")"
    cp -a "$pkg" "$work/$name"
    # Platzhalter in Textdateien ersetzen
    grep -rlI '@VERSION@\|@CODENAME@\|@CODENAME_PRETTY@\|@UBUNTU_SUITE@\|@URL@\|@LIVE_USER@' "$work/$name" 2>/dev/null |
    while read -r f; do
        sed -i -e "s|@VERSION@|$DISTRO_VERSION|g" \
               -e "s|@CODENAME_PRETTY@|$DISTRO_CODENAME_PRETTY|g" \
               -e "s|@CODENAME@|$DISTRO_CODENAME|g" \
               -e "s|@UBUNTU_SUITE@|$UBUNTU_SUITE|g" \
               -e "s|@URL@|$DISTRO_URL|g" \
               -e "s|@LIVE_USER@|$LIVE_USER|g" "$f"
    done
    find "$work/$name" -type d -exec chmod 0755 {} +
    find "$work/$name" -type f -exec chmod go-w {} +
    dpkg-deb --root-owner-group -Zxz --build "$work/$name" "$out/${name}_${DISTRO_VERSION}_all.deb" >/dev/null
    echo "gebaut: ${name}_${DISTRO_VERSION}_all.deb"
done
