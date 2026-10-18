#!/usr/bin/env bash
# Erzeugt aus den gebauten Frametide-Paketen eine signierte, flache APT-Paketquelle.
#   tools/make-apt-repo.sh out/debs site/        (GPG-Schlüssel muss im Schlüsselbund liegen)
# Ergebnis:
#   site/apt/            Pakete, Packages(.gz/.xz), Release, InRelease, Release.gpg, Schlüssel
#   site/frametide-base.deb   fester Name für die einmalige Einrichtung bestehender Installationen
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
debs="$(realpath "$1")"; site="$(realpath -m "$2")"; key="${3:-}"
repo="$site/apt"
rm -rf "$site"; mkdir -p "$repo"
for deb in "$debs"/frametide-*_*.deb; do
    case "$(basename "$deb")" in frametide-live_*) continue ;; esac  # nur fürs Live-System
    cp "$deb" "$repo/"
done
cd "$repo"
apt-ftparchive packages . > Packages
gzip -9kn Packages; xz -9k Packages
apt-ftparchive \
    -o APT::FTPArchive::Release::Origin="Frametide OS" \
    -o APT::FTPArchive::Release::Label="Frametide OS" \
    -o APT::FTPArchive::Release::Suite="stable" \
    -o APT::FTPArchive::Release::Description="Frametide OS packages" \
    release . > Release
gpg_args=(--batch --yes ${key:+--local-user "$key"})
gpg "${gpg_args[@]}" --clearsign -o InRelease Release
gpg "${gpg_args[@]}" -abs -o Release.gpg Release
cp "$root/packages/frametide-base/usr/share/keyrings/frametide-archive-keyring.gpg" .
cd - >/dev/null
cp "$repo"/frametide-base_*_all.deb "$site/frametide-base.deb"
cat > "$site/index.html" <<'HTML'
<!doctype html><meta charset="utf-8"><title>Frametide OS packages</title>
<style>body{font:16px/1.5 system-ui,sans-serif;max-width:40rem;margin:4rem auto;padding:0 1rem;background:#05070F;color:#C9D1E3}a{color:#22D3EE}code{background:#141a2b;padding:.1em .3em;border-radius:4px}</style>
<h1>Frametide OS packages</h1>
<p>This is the APT repository for <a href="https://github.com/ChopstickGuy/frametide-os">Frametide OS</a>.
New installations use it automatically.</p>
<p>Installed from the first ISO (1.0.0-alpha1)? Enable updates once:</p>
<pre><code>wget -O /tmp/frametide-base.deb https://chopstickguy.github.io/frametide-os/frametide-base.deb
sudo apt install /tmp/frametide-base.deb
sudo apt update && sudo apt full-upgrade</code></pre>
HTML
ls -la "$repo"
