# Frametide OS im Vergleich (Stand Oktober 2026)

## Überblick

| | **Frametide 1.0** | CachyOS | SteamOS 3.8 | Bazzite | Nobara 44 |
|---|---|---|---|---|---|
| Basis | Ubuntu 26.04 LTS | Arch (rolling) | Arch (Valve) | Fedora Atomic | Fedora |
| Updates/Stabilität | LTS bis 2031 | rolling | Valve-getestet | atomar | halb-rolling |
| Kernel | Ubuntu HWE 7.0, signiert | eigener, BORE-Scheduler | Valve-Kernel | eigener (HDR, Handhelds) | gepatcht |
| Pakete für moderne CPUs | optional x86-64-v3 | v3/v4/Zen4 + PGO/LTO | – | – | – |
| Proton-Variante | Valve-Proton (+ ProtonPlus im Store) | **proton-cachyos** | Valve-Proton | Valve/GE | GE-Proton (vom Nobara-Autor) |
| Konsolen-Modus (Big Picture) | – | Handheld-Edition | **Kern-Feature** | ja | ja (HTPC-Edition) |
| Rollback/Snapshots | **fehlt** | btrfs + Snapper | A/B-Image | **90 Tage, auto bei 3 Fehlstarts** | – |
| Treiber automatisch | ja (inkl. 32-Bit, Hybrid) | chwd | feste Hardware | Images | Unified ISO |
| **Secure Boot ohne Basteln** | **ja (NVIDIA ohne MOK)** | nein (manuell) | nein | mit Schlüssel-Registrierung | eingeschränkt |
| RGB + Lüfter in einer GUI | **ja (Frametide Center)** | nein | nein | OpenRGB per Befehl | nein |
| Office-/Kreativ-Suite vorinstalliert | **ArtCraft** | nein | nein | nein | nein |
| Eigener Store | ja (kuratiert + Flathub) | Shelly | Discover | Bazaar | Discover |
| Sprache | Deutsch zuerst, 10 offline | Englisch | Englisch | Englisch | Englisch |

## Was wir übernehmen sollten

| Priorität | Idee (Vorbild) | Nutzen | Aufwand |
|---|---|---|---|
| 1 | **Snapshots vor jedem Update + Rückkehr im Bootmenü** (CachyOS, Bazzite) | Ein kaputtes Update ist mit einem Klick rückgängig | mittel: btrfs als Standard, Snapper + grub-btrfs, apt-Hook |
| 2 | **Frametide Game Mode**: Steam Big Picture in Gamescope als eigene Sitzung im Login (SteamOS, Bazzite) | Konsolen-Erlebnis am TV, weniger Overhead, HDR in Spielen | mittel |
| 3 | **Proton-GE/proton-cachyos automatisch aktuell halten** (CachyOS, Nobara) | Mehr Spiele laufen sofort, Codecs für Zwischensequenzen | klein |
| 4 | **Kernel-Auswahl im Center**: HWE / HWE-edge, später eigener Gaming-Kernel (CachyOS) | Neueste Hardware ohne Terminal | klein |
| 5 | **Eigenes APT-Repo mit x86-64-v3-Builds + neuem Mesa** (CachyOS) | Messbar schneller bei CPU-lastigen Aufgaben | groß |
| 6 | **sched_ext-Scheduler** (scx_lavd/bpfland) als Option (CachyOS) | Weniger Ruckler bei Hintergrundlast | mittel (selbst paketieren) |
| 7 | **Handheld-Edition** (Bazzite, SteamOS) | Legion Go, ROG Ally, MSI Claw | groß |
| 8 | **Automatischer Rollback nach 3 Fehlstarts** (Bazzite) | Kein „schwarzer Bildschirm“ nach Updates | mittel (nach Punkt 1) |

## Was wir zusätzlich besser machen können (gibt es so noch nirgends)

1. **Spiele-Check vor dem Kauf/Umstieg**: Das Center liest die Steam-Bibliothek und zeigt pro Spiel
   die ProtonDB-Bewertung und den Anti-Cheat-Status (z. B. „läuft“ / „blockiert: Valorant“).
   Damit wissen Umsteiger vorab, was auf Linux spielbar ist.
2. **Windows-Umzugsassistent**: Dokumente, Bilder, Browser-Lesezeichen und WLAN-Passwörter aus
   einer Windows-Installation übernehmen. Steam-Spiele von der Windows-Platte werden erkannt.
3. **Ein-Klick-Profile im Center**: „Leise“, „Ausgewogen“, „Maximum“. Jedes Profil schaltet
   Lüfterkurve, RGB, Energieprofil und GPU-Leistungsstufe gemeinsam um (das, was unter Windows
   iCUE, Armoury Crate und Afterburner getrennt erledigen).
4. **Frametide Bench**: Reproduzierbarer Benchmark (Spiele-Szenen und CPU-Tests), damit wir
   jede Optimierung messen und gegen Ubuntu/CachyOS/Windows veröffentlichen können.
5. **Dev-Container per Klick**: Fertige Distrobox-/Podman-Umgebungen (z. B. Arch, Fedora, Python-KI
   mit CUDA/ROCm) aus dem Store. Entwickler bekommen so jedes Werkzeug ohne Risiko fürs System.

## Unser Aushängeschild

**„Frametide OS – Wechsle von Windows, ohne etwas zu verlieren.“**

Die anderen Gaming-Distributionen richten sich an Linux-Kenner (CachyOS), an eine bestimmte
Hardware (SteamOS) oder an reine Spieler (Bazzite). Frametide verbindet als einzige diese drei
Bereiche, und zwar ohne Terminal:

1. **Hardware, die einfach funktioniert**: Treiber, Secure Boot, RGB und Lüfter laufen automatisch,
   gesteuert aus *einem* Frametide Center statt drei Hersteller-Tools.
2. **Spielen, Arbeiten und Erschaffen ab dem ersten Start**: Steam plus ArtCraft (Word-, Excel-,
   PowerPoint-, Photoshop- und Premiere-Alternativen), VS Code und Chrome. Alles ist vorinstalliert
   oder im Store einen Klick entfernt.
3. **Stabil wie Ubuntu LTS, getunt für Spiele**: fünf Jahre Updates statt Rolling-Release-Risiko.
   Mit Punkt 1 der Liste oben kommen Snapshots als Sicherheitsnetz dazu.
