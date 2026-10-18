# Fremdcode

| Verzeichnis | Quelle | Version | Lizenz |
|---|---|---|---|
| `earport/` | [Anoryth/earport](https://github.com/Anoryth/earport), Quellcode des Release v0.6.0 | 0.6.0 | GPL-3.0-or-later |
| `tiling-assistant/` | [ubuntu/Tiling-Assistant](https://github.com/ubuntu/Tiling-Assistant), aus Ubuntu 26.10 (`gnome-shell-ubuntu-extensions 51.26.10.6ubuntu`) | 56 | GPL-2.0-or-later |

`tiling-assistant` bringt die Layout-Auswahl beim Ziehen von Fenstern (neu in Ubuntu 26.10) auf
GNOME 50. `packages/build-debs.sh` installiert sie als `tiling-assistant@frametide` in
`frametide-desktop`; die ältere Ubuntu-Variante (`tiling-assistant@ubuntu.com`) wird per
gschema-Override abgeschaltet.

`earport` (AirPods in den GNOME-Schnelleinstellungen) wird beim Paketbau aus diesem Quellcode
kompiliert – inklusive der Projekt-Tests – und als `frametide-earport` verpackt (nur über den App
Store, nicht auf der ISO). `SHA256SUMS` stellt sicher, dass der geprüfte Stand gebaut wird.
Durchgesehen vor der Aufnahme (0.6.0): kein Netzwerkzugriff, keine Rechteausweitung, Daten nur in
`~/.config/earport` (0700), einziger Hilfsprozess ein festes `pactl`-Skript ohne eingesetzte Werte.
