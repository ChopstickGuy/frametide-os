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
cp /tmp/frametide/mozilla.asc /etc/apt/keyrings/packages.mozilla.org.asc
cat > /etc/apt/sources.list.d/mozilla.sources <<'SRC'
Types: deb
URIs: https://packages.mozilla.org/apt
Suites: mozilla
Components: main
Signed-By: /etc/apt/keyrings/packages.mozilla.org.asc
SRC
cat > /etc/apt/preferences.d/frametide-mozilla.pref <<'PREF'
Package: firefox*
Pin: origin packages.mozilla.org
Pin-Priority: 1000
PREF

dpkg --add-architecture i386
apt-get update
apt_install ca-certificates locales
apt-get -y full-upgrade

echo ">>> Locales"
sed -i -E 's/^# *(de_DE.UTF-8|en_US.UTF-8)/\1/' /etc/locale.gen
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

echo ">>> 32-Bit-Grafiktreiber (Steam/Proton)"
apt_install mesa-vulkan-drivers:i386 libgl1-mesa-dri:i386 libglx-mesa0:i386 libvulkan1:i386

echo ">>> GRUB-Pakete für den Offline-Installer vorhalten"
mkdir -p /var/cache/frametide/grub
(cd /var/cache/frametide/grub && apt-get download grub-efi-amd64 grub-pc)

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
