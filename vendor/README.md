# Fremdcode

| Verzeichnis | Quelle | Version | Lizenz |
|---|---|---|---|
| `tiling-assistant/` | [ubuntu/Tiling-Assistant](https://github.com/ubuntu/Tiling-Assistant), aus Ubuntu 26.10 (`gnome-shell-ubuntu-extensions 51.26.10.6ubuntu`) | 56 | GPL-2.0-or-later |

`tiling-assistant` bringt die Layout-Auswahl beim Ziehen von Fenstern (neu in Ubuntu 26.10) auf
GNOME 50. `packages/build-debs.sh` installiert sie als `tiling-assistant@frametide` in
`frametide-desktop`; die ältere Ubuntu-Variante (`tiling-assistant@ubuntu.com`) wird per
gschema-Override abgeschaltet.
