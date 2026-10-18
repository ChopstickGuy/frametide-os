#!/usr/bin/env bash
# Baut alle Frametide-Pakete nach out/debs/ (kein root nötig).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$(dirname "$here")"
# shellcheck source=../config/frametide.conf
source "$root/config/frametide.conf"
out="${1:-$root/out/debs}"
# Paketversion steigt mit jedem Commit, damit installierte Systeme Updates erkennen
# (1.0 → 1.0.312 → 1.0.313 …). FRAMETIDE_PKG_VERSION überschreibt das.
commits="$(git -C "$root" rev-list --count HEAD 2>/dev/null || echo 0)"
PKG_VERSION="${FRAMETIDE_PKG_VERSION:-$DISTRO_VERSION.$commits}"
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
        install -Dm644 "$root/artwork/wordmark.png" "$dir/usr/share/pixmaps/frametide-wordmark.png"
        # Apps-Knopf im Dock: Ubuntus Dock sucht zuerst „view-app-grid-ubuntu-symbolic“ und fände sonst
        # das Ubuntu-Logo aus Yaru – unser neutrales Raster liegt in hicolor und ersetzt (per
        # dpkg-divert, siehe preinst) Yarus Datei, damit es unabhängig von der Suchreihenfolge greift
        install -Dm644 "$root/artwork/icon-terminal.svg" "$dir/usr/share/icons/hicolor/scalable/apps/frametide-terminal.svg"
        install -Dm644 "$root/artwork/icons/view-app-grid-symbolic.svg" \
            "$dir/usr/share/icons/hicolor/scalable/actions/view-app-grid-ubuntu-symbolic.svg"
        install -Dm644 "$root/artwork/icons/view-app-grid-symbolic.svg" \
            "$dir/usr/share/icons/Yaru/scalable/actions/view-app-grid-ubuntu-symbolic.svg"
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
        install -d "$dir/usr/share/icons"
        cp -a "$root/artwork/cursors/Frametide" "$dir/usr/share/icons/Frametide"
        install -d "$dir/usr/share/sounds/frametide/stereo"
        install -m644 "$root/artwork/sounds/index.theme" "$dir/usr/share/sounds/frametide/"
        install -m644 "$root"/artwork/sounds/stereo/*.wav "$dir/usr/share/sounds/frametide/stereo/"
        # Fenster-Layouts (Tiling Assistant aus Ubuntu 26.10) unter eigener UUID
        local ext="$dir/usr/share/gnome-shell/extensions/tiling-assistant@frametide"
        install -d "$ext"
        cp -a "$root/vendor/tiling-assistant/tiling-assistant@leleat-on-github/." "$ext/"
        python3 - "$ext/metadata.json" <<'PY'
import json, sys
path = sys.argv[1]
meta = json.load(open(path))
meta.update(uuid="tiling-assistant@frametide", name="Frametide Tiling",
            url="https://github.com/ChopstickGuy/frametide-os/tree/main/vendor/tiling-assistant")
json.dump(meta, open(path, "w"), indent=2)
PY
        # Startbildschirm-Theme: Grafiken aus artwork/plymouth
        install -m644 "$root"/artwork/plymouth/*.png "$dir/usr/share/plymouth/themes/frametide/"
        # Boot-Logo (Plymouth-Wasserzeichen) als PNG
        if command -v rsvg-convert >/dev/null; then
            install -d "$dir/usr/share/plymouth/themes/spinner"
            rsvg-convert -w 112 -h 112 "$root/artwork/logo.svg" -o "$dir/usr/share/plymouth/themes/spinner/watermark.png"
        else
            echo "WARNUNG: rsvg-convert fehlt – Ubuntu-Boot-Logo bleibt erhalten" >&2
            sed -i '/# BEGIN watermark/,/# END watermark/d' "$dir/DEBIAN/preinst" "$dir/DEBIAN/postrm"
        fi
        ;;
    frametide-tools)
        python3 "$root/tools/i18n.py" compile "$dir/usr/share/locale" >/dev/null
        install -Dm644 "$root/artwork/icon-store.svg" "$dir/usr/share/icons/hicolor/scalable/apps/frametide-store.svg"
        install -Dm644 "$root/artwork/icon-center.svg" "$dir/usr/share/icons/hicolor/scalable/apps/frametide-center.svg"
        install -Dm644 "$root/artwork/icon-dev.svg" "$dir/usr/share/icons/hicolor/scalable/apps/frametide-dev.svg"
        ;;
    frametide-earport)
        # AirPods-Unterstützung: aus dem geprüften Quellcode bauen (vendor/earport), samt Projekt-Tests
        (cd "$root/vendor/earport" && sha256sum --quiet -c SHA256SUMS) || { echo "earport: Prüfsumme falsch" >&2; exit 1; }
        local src="$work/earport-src"
        mkdir -p "$src"
        tar -xzf "$root"/vendor/earport/earport-*-source.tar.gz -C "$src" --strip-components=1
        meson setup "$src/daemon/build" "$src/daemon" --buildtype=release --prefix=/usr >/dev/null
        meson compile -C "$src/daemon/build" >/dev/null
        meson test -C "$src/daemon/build" --print-errorlogs >/dev/null || { echo "earport: Tests fehlgeschlagen" >&2; exit 1; }
        DESTDIR="$dir" meson install -C "$src/daemon/build" --no-rebuild >/dev/null
        install -d "$dir/usr/share/gnome-shell/extensions/earport@anoryth.github.io"
        cp -a "$src/extension/." "$dir/usr/share/gnome-shell/extensions/earport@anoryth.github.io/"
        rm -rf "$src"
        ;;
    frametide-live)
        install -m644 "$root/artwork/logo.svg" "$root/artwork/logo-icon.svg" "$root/artwork/wordmark.png" "$dir/etc/calamares/branding/frametide/"
        ;;
    esac
}

for pkg in "$here"/frametide-*/; do
    name="$(basename "$pkg")"
    # EarPort wird kompiliert: ohne Build-Werkzeuge überspringen (in der CI Pflicht)
    if [ "$name" = frametide-earport ] && ! command -v meson >/dev/null; then
        if [ -n "${FRAMETIDE_REQUIRE_EARPORT:-}" ]; then
            echo "FEHLER: meson fehlt – frametide-earport kann nicht gebaut werden" >&2; exit 1
        fi
        echo "WARNUNG: meson fehlt – frametide-earport wird übersprungen" >&2
        continue
    fi
    cp -a "$pkg" "$work/$name"
    find "$work/$name" -name __pycache__ -type d -prune -exec rm -rf {} +
    install_artwork "$name" "$work/$name"
    # Platzhalter in Textdateien ersetzen
    sed -i "s|^Version: @VERSION@|Version: $PKG_VERSION|" "$work/$name/DEBIAN/control"
    { grep -rlI '@VERSION@\|@CODENAME@\|@CODENAME_PRETTY@\|@UBUNTU_SUITE@\|@URL@\|@LIVE_USER@\|@APT_REPO_URL@' "$work/$name" 2>/dev/null || true; } |
    while read -r f; do
        sed -i -e "s|@VERSION@|$DISTRO_VERSION|g" \
               -e "s|@CODENAME_PRETTY@|$DISTRO_CODENAME_PRETTY|g" \
               -e "s|@CODENAME@|$DISTRO_CODENAME|g" \
               -e "s|@UBUNTU_SUITE@|$UBUNTU_SUITE|g" \
               -e "s|@URL@|$DISTRO_URL|g" \
               -e "s|@LIVE_USER@|$LIVE_USER|g" \
               -e "s|@APT_REPO_URL@|$APT_REPO_URL|g" "$f"
    done
    find "$work/$name" -type d -exec chmod 0755 {} +
    find "$work/$name" -type f -exec chmod go-w {} +
    arch="$(awk '/^Architecture:/{print $2}' "$work/$name/DEBIAN/control")"
    dpkg-deb --root-owner-group -Zxz --build "$work/$name" "$out/${name}_${PKG_VERSION}_${arch}.deb" >/dev/null
    echo "gebaut: ${name}_${PKG_VERSION}_${arch}.deb"
done
