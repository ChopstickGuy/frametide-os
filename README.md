# Vektor OS 1.0 „Ignition“

Eine auf **Ubuntu 26.10** basierende Distribution mit GNOME. Priorität eins ist
**maximale Gaming-Leistung durch korrekt eingerichtete Treiber**, danach folgen
niedrige Latenz und ein modernes, dunkles Design.

## Was Vektor anders macht als Ubuntu

| Bereich | Vektor OS |
|---|---|
| **Treiber** | `vektor-hwsetup` erkennt beim ersten Start GPU und CPU und installiert den passenden Treiber. NVIDIA wird über die vorsignierten Ubuntu-Module eingerichtet, Secure Boot funktioniert also ohne MOK. Dazu kommen 32-Bit-Bibliotheken für Steam/Proton, Kernel-Parameter (z. B. `nvidia-drm.modeset=1`, amdgpu für ältere GCN-Karten), Suspend-Dienste und Hybrid-Grafik-Unterstützung |
| **Kernel** | Ubuntu-Kernel 7.3 (signiert, kompatibel mit Treibern) mit `preempt=full` für niedrigere Latenz |
| **Speicher** | zram mit zstd statt Swap-Datei, abgestimmte `vm.*`-Werte, `vm.max_map_count` für Proton-Spiele |
| **Datenträger** | I/O-Scheduler je nach Gerätetyp: NVMe `none`, SSD `mq-deadline`, HDD `bfq` |
| **Gaming** | Steam (.deb), GameMode (vorkonfiguriert), MangoHud, Gamescope, Lutris, vkBasalt, CoreCtrl, große Shader-Caches gegen Ruckler |
| **Desktop** | GNOME 51 dunkel mit Teal-Akzent, Inter und JetBrains Mono, Papirus-Icons, Dock unten, **VRR aktiviert**, flache Mausbeschleunigung |
| **Ballast** | Kein Snap, Firefox als .deb direkt von Mozilla, Flathub vorkonfiguriert |
| **Installer** | Calamares mit Vektor-Branding, kein Swap auf der Festplatte (zram), BIOS und UEFI mit Secure Boot |

## Aufbau

```
config/vektor.conf        Name, Version, Ubuntu-Basis (zentrale Stelle)
build.sh                  ISO-Build: debootstrap → chroot → squashfs → ISO
scripts/chroot-install.sh Paketinstallation im Image
packages/                 Vektor-Pakete (.deb), gebaut mit build-debs.sh
  vektor-base             Tuning, zram, sysctl, I/O, Branding (os-release)
  vektor-hwsetup          Hardware-/Treiber-Erkennung (Python)
  vektor-gaming           Gaming-Stack + GameMode-Profil
  vektor-desktop          GNOME-Design, Wallpaper, Boot-Logo
  vektor-dev              Entwicklerwerkzeuge
  vektor-live             Live-System + Calamares (wird bei Installation entfernt)
iso/grub.cfg              Bootmenü der Live-ISO
artwork/                  Logo und Wallpaper (SVG)
tools/check-packages.py   prüft alle Paketnamen gegen das Ubuntu-Archiv
.github/workflows/        CI: prüfen, ISO bauen, Release bei Tag v*
```

## ISO bauen

Benötigt Ubuntu/Debian, root und etwa 25 GB freien Speicher:

```bash
sudo apt install debootstrap squashfs-tools xorriso dosfstools mtools curl librsvg2-bin
python3 tools/check-packages.py     # schneller Vorab-Check
sudo ./build.sh                     # Ergebnis: out/vektor-os-1.0-ignition-amd64.iso
```

Ohne eigenen Build-Rechner: das Repo auf GitHub pushen und unter *Actions* den
Workflow „ISO bauen“ starten. Die ISO erscheint dann als Download-Artefakt.

Testen in einer VM:

```bash
qemu-system-x86_64 -enable-kvm -m 8G -smp 4 -cdrom out/vektor-os-*.iso \
  -bios /usr/share/ovmf/OVMF.fd -vga virtio
```

## Treiber-Einrichtung

Nach der Installation läuft `vektor-hwsetup` einmalig beim ersten Start mit
Internetverbindung. Danach meldet GNOME „Neustart erforderlich“.

```bash
vektor-hwsetup                 # erkannte Hardware und geplante Schritte anzeigen
sudo vektor-hwsetup --apply    # erneut ausführen, z. B. nach GPU-Wechsel
cat /var/log/vektor-hwsetup.log
```

Optionen in `/etc/vektor/hwsetup.conf`:

- `AMD64V3=yes` aktiviert Ubuntus x86-64-v3-optimierte Pakete, wenn die CPU sie
  unterstützt (Haswell/Zen 1 oder neuer). Die Option ist **experimentell**.
- `AMD_OVERDRIVE=yes` schaltet Übertakten und Undervolting für AMD-GPUs in
  CoreCtrl frei.

## Gaming-Tipps

- Steam-Startoption für GameMode: `gamemoderun %command%`
- FPS-Overlay: `mangohud %command%` (beides kombinierbar)
- Proton-GE: „ProtonPlus“ aus GNOME Software (Flathub) installieren

## Hinweise

- **Support-Zeitraum:** Ubuntu 26.10 ist ein Interim-Release mit Updates bis
  etwa Juli 2027. Für Vektor 2.0 entweder auf 27.04 wechseln oder für
  Langzeitstabilität auf 26.04 LTS umstellen. Dafür nur `UBUNTU_SUITE` und
  `UBUNTU_VERSION` in `config/vektor.conf` ändern.
- **Name:** Vor einer öffentlichen Veröffentlichung „Vektor OS“ auf
  Markenkonflikte prüfen.

## Roadmap

- **1.1**: NVIDIA-Treiber offline auf der ISO, Willkommens-App (GTK4/libadwaita)
- **1.2**: eigenes APT-Repo (Mesa-Backports, scx-Scheduler/`sched_ext`), Benchmarks gegen Ubuntu
- **2.0**: optionaler Gaming-Kernel als eigenes, signiertes Paket
