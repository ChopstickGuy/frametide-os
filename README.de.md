<div align="center">

<img src="docs/banner.png" alt="Frametide OS" width="100%">

[![Build](https://github.com/ChopstickGuy/frametide-os/actions/workflows/build-iso.yml/badge.svg)](https://github.com/ChopstickGuy/frametide-os/actions/workflows/build-iso.yml)
[![Lizenz: GPL v3](https://img.shields.io/badge/lizenz-GPLv3-22D3EE)](LICENSE)
[![Ubuntu 26.04 LTS](https://img.shields.io/badge/basis-Ubuntu%2026.04%20LTS-6D7CFF)](https://ubuntu.com)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-A855F7)](#status)

[Download](https://sourceforge.net/projects/frametide-os/files/) ·
[Screenshots](#screenshots) ·
[Enthalten](#was-dabei-ist) ·
[Selbst bauen](#selbst-bauen) ·
[English](README.md)

</div>

Frametide OS ist Ubuntu 26.04 LTS mit GNOME 50, eingerichtet zum Spielen und Programmieren.
Was man nach einer Ubuntu-Installation sonst von Hand erledigt, ist schon erledigt:
Grafiktreiber, Steam, Lüfter- und RGB-Steuerung, Entwicklerwerkzeuge – dazu ein paar kleine
Apps, die das alles an einem Ort bündeln.

Darunter ist es weiterhin Ubuntu: dieselben Pakete, dieselbe Dokumentation und fünf Jahre Updates.

## Was anders ist als bei Ubuntu

- **Treiber beim ersten Start.** NVIDIA-, AMD- und Intel-Grafik wird erkannt und im
  Hintergrund eingerichtet, inklusive der 32-Bit-Bibliotheken für Steam und Hybrid-Grafik
  bei Laptops.
- **Gaming-Werkzeuge an Bord.** Steam, Proton, GameMode, MangoHud und Gamescope sind
  vorinstalliert, `ntsync`, größere Shader-Caches und lineare Mausbeschleunigung aktiv.
- **Abgestimmt, aber nichts Exotisches.** zram, I/O-Scheduler je Laufwerkstyp, `preempt=full`,
  `noatime`, BBR, höhere Dateilimits. Updates laufen mit niedrigster Priorität.
- **Kein Snap, keine Telemetrie.** Apps kommen aus apt und Flathub.
- **Fenster-Layouts.** Fenster an den oberen Rand ziehen und ein Layout wählen (aus Ubuntu 26.10).
- **Updates ohne Neuinstallation.** Frametides eigene Apps und Einstellungen kommen über
  *Steuerung → Updates*; ein kurzes „Was ist neu“-Fenster zeigt die Neuerungen.
- **Schneller Start.** Bootmenü ausgeblendet, kein Warten aufs Netzwerk, ein ruhiger
  Startbildschirm.
- **Ruhiger Desktop.** Dunkles GNOME mit Petrol-Akzent, festes Dock, klassisches
  Anwendungsmenü, App-Ordner, leise, tiefe Systemklänge und ein Lade-Zeiger als Welle.
- **10 Sprachen offline.** Deutsch, Englisch, Französisch, Spanisch, Italienisch, Polnisch,
  Portugiesisch, Niederländisch, Türkisch und Russisch. Frametides eigene Apps gibt es auf
  Deutsch, Englisch, Spanisch, Italienisch und Portugiesisch. Die ISO startet auf Englisch, andere
  Sprachen stehen im Startmenü.

## Die Apps

| | |
|---|---|
| **App Store** | Rund 150 ausgewählte Apps mit echten Icons, dazu Suche in ganz Flathub. Quellen: apt, Flathub, ArtCraft und einige Hersteller-Pakete. |
| **Steuerung** | Updates (System, Flatpak, ArtCraft, Firmware), Grafiktreiber inkl. optional neuester Mesa, **Spiele-Check** (ProtonDB + Anti-Cheat-Status), **Audio**, RGB & Lüfter und Leistungsoptionen. |
| **Entwickeln** | Git, SSH-Schlüssel und GitHub-Anmeldung; Sprachen über `mise`; PostgreSQL, MySQL, Redis u. a. als lokale Container; Live-Liste der Ports von Dev-Servern; Projekt-Starter mit Vorlagen. |
| **PC-Umzug** | Holt Dokumente, Fotos, Lesezeichen, WLAN-Netze und Steam-Spiele von einem Windows-Laufwerk. Windows wird dabei nur gelesen, nie verändert. |
| **Bench** | Wiederholbarer Benchmark (CPU, Speicher, Latenz, SSD, GPU, Startzeit) mit JSON-Ergebnis zum Vergleichen. |
| **Tasks** | Task-Manager auf <kbd>Strg</kbd>+<kbd>Umschalt</kbd>+<kbd>Esc</kbd>. |

Auf der Audio-Seite wählst du Headset, Lautsprecher oder Mikrofon, stellst die Lautstärke ein,
testest dein Mikrofon und schaltest die **Rauschunterdrückung** ein. Sie läuft direkt in PipeWire
(WebRTC) und wirkt deshalb in Discord, Teams und Spielen, ohne Zusatzprogramm.

## Screenshots

<table>
<tr>
<td width="50%"><img src="docs/screenshots/store.png" alt="App Store"><p align="center"><sub>App Store</sub></p></td>
<td width="50%"><img src="docs/screenshots/games.png" alt="Spiele-Check"><p align="center"><sub>Steuerung → Spiele</sub></p></td>
</tr>
<tr>
<td width="50%"><img src="docs/screenshots/audio.png" alt="Audio und Rauschunterdrückung"><p align="center"><sub>Steuerung → Audio</sub></p></td>
<td width="50%"><img src="docs/screenshots/develop.png" alt="Projekt-Starter"><p align="center"><sub>Entwickeln → Projekte</sub></p></td>
</tr>
</table>

<sub>Screenshots in englischer Oberfläche; auf deutschen Systemen erscheint alles auf Deutsch.</sub>

<details>
<summary>Logo und Hintergrundbilder</summary>
<br>
<img src="artwork/previews/overview.png" alt="Logo und sieben Hintergrundbilder">
</details>

## Was dabei ist

| | |
|---|---|
| **Basis** | Ubuntu 26.04 LTS, HWE-Kernel, GNOME 50, Mesa |
| **Gaming** | Steam, Proton, GameMode, MangoHud, Gamescope, Lutris |
| **Office** | ArtCraft: WordCraft, GridCraft, DeckCraft, PdfCraft |
| **Entwicklung** | GitHub Desktop, GitHub CLI, mise, Podman, Distrobox |
| **Medien** | Video-Codecs (GStreamer libav/ugly/bad, FFmpeg) |
| **Hardware** | OpenRGB, CoolerControl, lm-sensors, fwupd |
| **Handy** | GSConnect – koppelt sich mit der App KDE Connect (Android/iOS) |
| **Beim ersten Start** | Google Chrome und VS Code, direkt von Google und Microsoft (deren Lizenzen erlauben keine Weitergabe auf der ISO) |
| **Installer** | Calamares; funktioniert offline, BIOS und UEFI mit Secure Boot |

## Ausprobieren

1. ISO von [SourceForge](https://sourceforge.net/projects/frametide-os/files/) laden.
   Builds von `main` gibt es unter
   [Actions → Build ISO → Artifacts](https://github.com/ChopstickGuy/frametide-os/actions/workflows/build-iso.yml).
2. Prüfen: `sha256sum -c frametide-os-*.iso.sha256`
3. Erst in einer VM testen (UEFI, 8 GB RAM, 40 GB Festplatte) oder mit
   [Ventoy](https://www.ventoy.net) bzw. [Impression](https://flathub.org/apps/io.gitlab.adhami3310.Impression)
   auf einen USB-Stick schreiben. Im Installer ist **Festplatte löschen** der einfachste Weg.

## Status

Frametide OS ist **Alpha**. Jeder Build wird von der CI in QEMU installiert und gestartet
(UEFI und BIOS), auf echter Hardware lief es aber noch selten. Bitte nicht auf einem Rechner
installieren, auf den du angewiesen bist.

Bekannte Einschränkungen:

- Windows speichert WLAN-Passwörter verschlüsselt. Der PC-Umzug kann sie nur übernehmen, wenn
  sie vorher exportiert wurden (`netsh wlan export profile key=clear`).
- VRR wird pro Monitor unter *Einstellungen → Anzeigen* eingeschaltet.
- RGB und Lüfter: unterstützt wird, was OpenRGB und CoolerControl können – das meiste, aber
  nicht alles.
- Manche Multiplayer-Spiele sperren Linux über ihr Anti-Cheat. Der Spiele-Check zeigt, welche.

Vergleich mit CachyOS, Bazzite, SteamOS und anderen: [docs/VERGLEICH.md](docs/VERGLEICH.md).

## Nützliches

```bash
frametide-hwsetup                 # erkannte Hardware und geplante Schritte anzeigen
sudo frametide-hwsetup --apply    # Treiber neu einrichten, z. B. nach GPU-Wechsel
cat /var/log/frametide-hwsetup.log
```

- Steam-Startoption: `gamemoderun %command%`, mit FPS-Anzeige `gamemoderun mangohud %command%`
- Proton-GE: ProtonPlus aus dem App Store
- Battle.net / WoW: Faugus Launcher aus dem App Store – Schritt für Schritt in [docs/BATTLENET.md](docs/BATTLENET.md)
- Optionen in `/etc/frametide/hwsetup.conf` (oder in Steuerung → System), z. B.
  `AMD_OVERDRIVE=yes` für Übertakten/Undervolting bei AMD-Grafik

## Selbst bauen

```bash
sudo apt install debootstrap squashfs-tools xorriso dosfstools mtools curl librsvg2-bin \
    meson ninja-build libglib2.0-dev libbluetooth-dev   # die letzten vier bauen das AirPods-Paket
python3 tools/check-packages.py   # prüft Paketnamen gegen das Ubuntu-Archiv
sudo ./build.sh                   # → out/frametide-os-1.0-ignition-amd64.iso (~25 GB frei)
```

Aufbau des Repos: siehe [englische README](README.md#build-it-yourself).

## Mitmachen

Fehlerberichte, Ideen und Übersetzungen sind willkommen – siehe [CONTRIBUTING.md](CONTRIBUTING.md)
und die [Issue-Vorlagen](https://github.com/ChopstickGuy/frametide-os/issues/new/choose).
Eine neue Sprache ist eine Datei in `po/`.

## Lizenz

Frametides eigener Code und das Artwork stehen unter der [GNU GPL v3](LICENSE). Enthaltene
Programme behalten ihre eigenen Lizenzen.

<sub>Frametide OS ist ein unabhängiges Community-Projekt und steht in keiner Verbindung zu
Canonical, Valve, Google, Microsoft oder dem ArtCraft-Team. Ubuntu ist eine Marke von
Canonical Ltd. Alle anderen Marken gehören ihren Inhabern.</sub>
