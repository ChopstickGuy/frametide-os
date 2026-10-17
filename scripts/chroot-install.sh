#!/usr/bin/env bash
# Läuft INNERHALB des Image-Chroots. Wird von build.sh aufgerufen.
set -euo pipefail
source /tmp/frametide/frametide.conf
export DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8
apt_install() { apt-get install -y -o Dpkg::Options::=--force-confold "$@"; }

echo ">>> Paketquellen (Ubuntu $UBUNTU_VERSION + Mozilla)"
rm -f /etc/apt/sources.list
cat > /etc/apt/sources.list.d/ubuntu.sources <<SRC
Types: deb
URIs: $MIRROR
Suites: $UBUNTU_SUITE $UBUNTU_SUITE-updates $UBUNTU_SUITE-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb
URIs: $SECURITY_MIRROR
Suites: $UBUNTU_SUITE-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
SRC

# Kein Snap: schnellerer Start, weniger Hintergrundlast. Apps kommen als .deb oder Flatpak.
cat > /etc/apt/preferences.d/frametide-no-snap.pref <<'PREF'
Package: snapd
Pin: release a=*
Pin-Priority: -10
PREF
# Firefox als echtes .deb direkt von Mozilla
install -d -m 0755 /etc/apt/keyrings
# Schlüssel einheitlich als Binär-Keyring ablegen (egal ob ASCII-armored oder nicht)
for key in /tmp/frametide/keys/*.key; do
    name="$(basename "$key" .key)"
    if grep -q -- "-----BEGIN PGP" "$key"; then
        gpg --dearmor < "$key" > "/etc/apt/keyrings/$name.gpg"
    else
        cp "$key" "/etc/apt/keyrings/$name.gpg"
    fi
    chmod 644 "/etc/apt/keyrings/$name.gpg"
done
cat > /etc/apt/sources.list.d/mozilla.sources <<'SRC'
Types: deb
URIs: https://packages.mozilla.org/apt
Suites: mozilla
Components: main
Signed-By: /etc/apt/keyrings/mozilla.gpg
SRC
cat > /etc/apt/preferences.d/frametide-mozilla.pref <<'PREF'
Package: firefox*
Pin: origin packages.mozilla.org
Pin-Priority: 1000
PREF

# Weitere Hersteller-Quellen: VS Code, Chrome, GitHub CLI, GitHub Desktop, CoolerControl
add_repo() {  # name url suites components
    printf 'Types: deb\nURIs: %s\nSuites: %s\nComponents: %s\nArchitectures: amd64\nSigned-By: /etc/apt/keyrings/%s.gpg\n' \
        "$2" "$3" "$4" "$1" > "/etc/apt/sources.list.d/$1.sources"
}
add_repo vscode https://packages.microsoft.com/repos/code stable main
add_repo github-cli https://cli.github.com/packages stable main
add_repo github-desktop https://mirror.mwt.me/shiftkey-desktop/deb/ any main
add_repo coolercontrol https://dl.cloudsmith.io/public/coolercontrol/coolercontrol/deb/ubuntu "$UBUNTU_SUITE" main
add_repo mise https://mise.jdx.dev/deb stable main
# Chrome verwaltet seine Quelle selbst unter diesem Dateinamen – wir legen sie passend an
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] https://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list
# VS Code soll keine eigene, doppelte Quelle anlegen
echo "code code/add-microsoft-repo boolean false" | debconf-set-selections

dpkg --add-architecture i386
apt-get update
apt_install ca-certificates locales
apt-get -y full-upgrade

echo ">>> Locales"
sed -i -E 's/^# *((de_DE|en_US|en_GB|fr_FR|es_ES|it_IT|pl_PL|pt_PT|pt_BR|nl_NL|tr_TR|ru_RU)\.UTF-8)/\1/' /etc/locale.gen
locale-gen
update-locale LANG=de_DE.UTF-8

echo ">>> Steam-Lizenz vorab akzeptieren"
echo "steam steam/question select I AGREE" | debconf-set-selections
echo "steam steam/license note ''" | debconf-set-selections

echo ">>> Kernel, Bootloader, Desktop"
apt_install linux-generic-hwe-26.04 casper \
    shim-signed grub-efi-amd64-signed grub-efi-amd64-bin grub-pc-bin grub2-common efibootmgr \
    ubuntu-desktop-minimal

echo ">>> Frametide-Pakete"
apt_install /tmp/frametide/debs/*.deb

echo ">>> Flathub-Katalog für den Store vorladen"
flatpak update --appstream --system || true

echo ">>> ArtCraft-Apps (geprüfte .deb aus den GitHub-Releases)"
apt_install /tmp/frametide/craft/*.deb

echo ">>> Standard-Software"
apt_install gh github-desktop coolercontrol mise
# Chrome und VS Code: Lizenz verbietet Weitergabe auf der ISO → Installation beim ersten Start (frametide-apps)

echo ">>> Sprachpakete: $LANGUAGES"
declare -A FIREFOX_L10N=([de]=de [en]=en-gb [fr]=fr [es]=es-es [it]=it [pl]=pl [pt]=pt-pt [nl]=nl [tr]=tr [ru]=ru)
declare -A HUNSPELL=([de]=de-de [en]=en-us [fr]=fr [es]=es [it]=it [pl]=pl [pt]=pt-pt [nl]=nl [tr]=tr [ru]=ru)
lang_pkgs=()
for l in $LANGUAGES; do
    lang_pkgs+=("language-pack-$l" "language-pack-gnome-$l" "hunspell-${HUNSPELL[$l]}" "firefox-l10n-${FIREFOX_L10N[$l]}")
done
apt_install "${lang_pkgs[@]}"

echo ">>> 32-Bit-Grafiktreiber (Steam/Proton)"
apt_install mesa-vulkan-drivers:i386 libgl1-mesa-dri:i386 libglx-mesa0:i386 libvulkan1:i386

echo ">>> GRUB-Pakete für den Offline-Installer vorhalten"
# Je Startmodus das GRUB-Paket samt allen fehlenden Abhängigkeiten (z. B. grub-gfxpayload-lists
# bei grub-pc), damit der Installer ohne Internet auskommt.
for entry in efi:grub-efi-amd64 pc:grub-pc; do
    dir="/var/cache/frametide/grub/${entry%%:*}"
    mkdir -p "$dir"
    mapfile -t need < <(apt-get -s -o Debug::NoLocking=1 install --no-install-recommends "${entry#*:}" |
                        awk '/^Inst /{print $2}')
    echo "    ${entry%%:*}: ${need[*]:-(bereits vollständig)}"
    if [ "${#need[@]}" -gt 0 ]; then
        (cd "$dir" && apt-get download "${need[@]}")
    fi
done

echo ">>> Ballast entfernen (schnellerer Start, aufgeräumtes System)"
# Absturzberichte, Telemetrie, Ubuntu-Einrichtungsassistent, Snap (alles nur „Recommends“)
for pkg in snapd apport apport-gtk whoopsie kerneloops popularity-contest ubuntu-report \
           gnome-initial-setup; do
    dpkg -s "$pkg" >/dev/null 2>&1 && apt-get -y purge "$pkg"
done

echo ">>> Aufräumen"
apt-get -y autoremove --purge
apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
truncate -s 0 /etc/machine-id
rm -f /var/lib/dbus/machine-id
update-initramfs -u -k all
