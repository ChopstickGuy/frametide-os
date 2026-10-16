"""Gemeinsamer Code für Frametide Store und Frametide Center."""
import json
import os
import re
import subprocess
import urllib.request

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

# Zeilen zeigen Text immer wörtlich an (Gerätenamen, Paketnamen, „&“ …) statt ihn als Markup zu lesen
for _row in (Adw.ActionRow, Adw.SwitchRow, Adw.ExpanderRow):
    def _plain_init(self, *args, _orig=_row.__init__, **kwargs):
        texts = {k: kwargs.pop(k) for k in ("title", "subtitle") if k in kwargs}
        kwargs["use_markup"] = False  # SwitchRow erbt von ActionRow → Wrapper kann doppelt laufen
        _orig(self, *args, **kwargs)
        for key, value in texts.items():  # erst nach use_markup=False setzen
            getattr(self, f"set_{key}")(value or "")
    _row.__init__ = _plain_init

from frametide_i18n import GERMAN, LANG, _, localized  # noqa: E402,F401

HELPER = "/usr/lib/frametide/frametide-helper"
DATA_DIR = os.environ.get("FRAMETIDE_DATA", "/usr/share/frametide")
FLATHUB_ICONS = "/var/lib/flatpak/appstream/flathub/x86_64/active/icons/128x128"

# ArtCraft-Apps: Paketname -> GitHub-Repository (github.com/storytold/<repo>)
CRAFT_REPOS = {
    "wordcraft": "wordcraft", "gridcraft": "gridcraft", "deckcraft": "deckcraft",
    "pdfcraft": "pdfcraft", "photocraft": "photocraft", "lightcraft": "lightcraft",
    "vectorcraft": "vectorcraft", "filmcraft": "filmcraft", "effectcraft": "effectcraft",
    "soundcraft": "soundcraft", "designcraft": "designcraft", "figcraft": "figcraft",
    "cadcraft": "cadcraft", "artcraft-launcher": "craft-launcher",
}

CSS = """
.ft-card { padding: 14px; border-radius: 14px; }
.ft-card:hover { background-color: alpha(currentColor, .04); }
.ft-badge { font-size: 0.75em; padding: 1px 8px; border-radius: 99px;
            background-color: alpha(currentColor, .08); }
.ft-badge.success { background-color: alpha(@success_color, .18); }
.ft-badge.warning { background-color: alpha(@warning_color, .18); }
.ft-badge.error { background-color: alpha(@error_color, .18); }
.ft-hero { padding: 28px 32px; border-radius: 18px;
           background-image: linear-gradient(120deg, alpha(#22D3EE,.22), alpha(#A855F7,.22)); }
.ft-tile { padding: 0; border-radius: 16px; }
.ft-tile:hover { background-color: alpha(@accent_bg_color, .12); }
.ft-big-number { font-size: 2.2em; font-weight: 700; font-feature-settings: "tnum"; }
"""


def load_css():
    provider = Gtk.CssProvider()
    provider.load_from_string(CSS) if hasattr(provider, "load_from_string") else provider.load_from_data(CSS, -1)
    Gtk.StyleContext.add_provider_for_display(
        Gtk.Widget.get_display(Gtk.Label()), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def helper_argv(*args):
    return ["pkexec", HELPER, f"--lang={'de' if GERMAN else 'en'}", *args]


def run(argv, timeout=60):
    """Kurzer, synchroner Aufruf; gibt stdout zurück ('' bei Fehler)."""
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


# ---------------------------------------------------------------- Paketstatus

def apt_installed(packages):
    """Menge der installierten Debian-Pakete aus `packages`."""
    if not packages:
        return set()
    out = run(["dpkg-query", "-W", "-f=${Package}\t${db:Status-Abbrev}\n", *packages])
    return {line.split("\t")[0] for line in out.splitlines() if line.endswith("ii ")}


def apt_version(package):
    lines = run(["dpkg-query", "-W", "-f=${Version}\n", package]).splitlines()
    return lines[0].strip() if lines else ""


def flatpak_installed():
    out = run(["flatpak", "list", "--app", "--columns=application"])
    return {line.strip() for line in out.splitlines() if line.strip()}


def apt_upgradable():
    out = run(["apt", "list", "--upgradable"], timeout=120)
    result = []
    for line in out.splitlines():
        m = re.match(r"^([^/]+)/\S+\s+(\S+)", line)
        if m:
            result.append((m.group(1), m.group(2)))
    return result


def flatpak_upgradable():
    out = run(["flatpak", "remote-ls", "--updates", "--columns=application,version"], timeout=120)
    return [tuple((line.split("\t") + [""])[:2]) for line in out.splitlines() if line.strip()]


def craft_latest(app):
    """(Version, Download-URL, sha256) der neuesten Linux-.deb einer Craft-App."""
    url = f"https://api.github.com/repos/storytold/{CRAFT_REPOS[app]}/releases/latest"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    for asset in data.get("assets", []):
        if asset["name"].endswith("-linux-x86_64.deb"):
            digest = (asset.get("digest") or "").removeprefix("sha256:")
            return data["tag_name"].lstrip("v"), asset["browser_download_url"], digest
    raise LookupError(f"keine Linux-.deb für {app}")


def craft_upgradable():
    result = []
    for app in sorted(apt_installed(list(CRAFT_REPOS))):
        try:
            latest, _, _ = craft_latest(app)
        except Exception:
            continue
        current = apt_version(app).split("-")[0]
        if current and subprocess.run(["dpkg", "--compare-versions", latest, "gt", current]).returncode == 0:
            result.append((app, latest))
    return result


# ------------------------------------------------------------------ Aufgaben

class Task:
    """Startet einen Prozess asynchron und liefert jede Ausgabezeile an `on_line`."""

    def __init__(self, argv, on_line=None, on_done=None):
        self.on_line, self.on_done = on_line, on_done
        flags = Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_MERGE
        try:
            self.proc = Gio.Subprocess.new(argv, flags)
        except GLib.Error as e:
            GLib.idle_add(self._finish, 127, str(e))
            return
        self.stream = Gio.DataInputStream.new(self.proc.get_stdout_pipe())
        self._read()

    def _read(self):
        self.stream.read_line_async(GLib.PRIORITY_DEFAULT, None, self._on_line)

    def _on_line(self, stream, result):
        line, _ = stream.read_line_finish_utf8(result)
        if line is None:
            self.proc.wait_async(None, lambda p, r: (p.wait_finish(r), self._finish(p.get_exit_status())))
            return
        if self.on_line:
            self.on_line(line)
        self._read()

    def _finish(self, status, message=None):
        if message and self.on_line:
            self.on_line(message)
        if self.on_done:
            self.on_done(status)
        return False


def in_thread(func, callback):
    """Führt `func` in einem Thread aus und ruft `callback(ergebnis)` im GTK-Hauptthread."""
    import threading

    def worker():
        try:
            result = func()
        except Exception as e:  # Fehler als Ergebnis zurückgeben
            result = e
        GLib.idle_add(callback, result)
    threading.Thread(target=worker, daemon=True).start()


def icon_widget(icon, size=48, app_id=None):
    """Logo aus dem Store-Cache, Flathub-Appstream, Icon-Theme oder Fallback."""
    cached = os.path.join(DATA_DIR, "store", "icons", f"{app_id}.png") if app_id else ""
    path = cached if os.path.exists(cached) else os.path.join(FLATHUB_ICONS, f"{icon}.png")
    if os.path.exists(path):
        image = Gtk.Image.new_from_file(path)
    else:
        theme = Gtk.IconTheme.get_for_display(Gtk.Widget.get_display(Gtk.Label()))
        image = Gtk.Image.new_from_icon_name(icon if theme.has_icon(icon) else "application-x-executable")
    image.set_pixel_size(size)
    return image


def log_view():
    """Ausklappbares Protokoll für laufende Aufgaben."""
    buffer = Gtk.TextBuffer()
    view = Gtk.TextView(buffer=buffer, editable=False, monospace=True, cursor_visible=False,
                        wrap_mode=Gtk.WrapMode.WORD_CHAR, top_margin=8, bottom_margin=8,
                        left_margin=10, right_margin=10)
    scroller = Gtk.ScrolledWindow(child=view, min_content_height=160)
    expander = Gtk.Expander(label=_("Details anzeigen"), child=scroller)

    def append(line):
        buffer.insert(buffer.get_end_iter(), line + "\n")
        view.scroll_to_mark(buffer.get_insert(), 0, False, 0, 0)
    return expander, append
