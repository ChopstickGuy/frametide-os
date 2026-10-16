#!/usr/bin/env bash
# Baut alle Frametide-Pakete nach out/debs/ (kein root nötig).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$(dirname "$here")"
# shellcheck source=../config/frametide.conf
source "$root/config/frametide.conf"
out="${1:-$root/out/debs}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$out"

# Artwork liegt nur in artwork/ und wird beim Bauen in die Pakete kopiert
install_artwork() {
    local name="$1" dir="$2"
    case "$name" in
    frametide-desktop)
        install -Dm644 "$root/artwork/logo-icon.svg" "$dir/usr/share/icons/hicolor/scalable/apps/frametide-logo.svg"
        install -Dm644 "$root/artwork/logo-icon.svg" "$dir/usr/share/pixmaps/frametide-logo.svg"
        install -d "$dir/usr/share/backgrounds/frametide" "$dir/usr/share/gnome-background-properties"
        cp "$root"/artwork/wallpapers/*.svg "$dir/usr/share/backgrounds/frametide/"
        {
            echo '<?xml version="1.0"?>'
            echo '<!DOCTYPE wallpapers SYSTEM "gnome-wp-list.dtd">'
            echo '<wallpapers>'
            for wp in "$root"/artwork/wallpapers/*.svg; do
                local base title
                base="$(basename "$wp")"
                title="$(basename "$wp" .svg | sed -e 's/^frametide-//' -e 's/-/ /g' -e 's/\b./\u&/g')"
                printf '  <wallpaper deleted="false"><name>Frametide %s</name><filename>/usr/share/backgrounds/frametide/%s</filename><options>zoom</options><shade_type>solid</shade_type><pcolor>#05070F</pcolor><scolor>#05070F</scolor></wallpaper>\n' "$title" "$base"
            done
            echo '</wallpapers>'
        } > "$dir/usr/share/gnome-background-properties/frametide.xml"
        install -d "$dir/usr/share/sounds/frametide/stereo"
        install -m644 "$root/artwork/sounds/index.theme" "$dir/usr/share/sounds/frametide/"
        install -m644 "$root"/artwork/sounds/stereo/*.wav "$dir/usr/share/sounds/frametide/stereo/"
        # Boot-Logo (Plymouth-Wasserzeichen) als PNG
        if command -v rsvg-convert >/dev/null; then
            install -d "$dir/usr/share/plymouth/themes/spinner"
            rsvg-convert -w 112 -h 112 "$root/artwork/logo.svg" -o "$dir/usr/share/plymouth/themes/spinner/watermark.png"
        else
            echo "WARNUNG: rsvg-convert fehlt – Ubuntu-Boot-Logo bleibt erhalten" >&2
            rm -f "$dir/DEBIAN/preinst"
            sed -i '/dpkg-divert/,/watermark.png$/d' "$dir/DEBIAN/postrm"
        fi
        ;;
    frametide-live)
        install -m644 "$root/artwork/logo.svg" "$root/artwork/logo-icon.svg" "$dir/etc/calamares/branding/frametide/"
        ;;
    esac
}

for pkg in "$here"/frametide-*/; do
    name="$(basename "$pkg")"
    cp -a "$pkg" "$work/$name"
    install_artwork "$name" "$work/$name"
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
