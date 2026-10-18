#!/usr/bin/python3
"""Frametide – „Was ist neu“: zeigt nach einem Update kurz die Neuerungen.

  frametide-whats-new               neueste Versionshinweise anzeigen
  frametide-whats-new --if-pending  nur, wenn seit dem letzten Update noch nicht gesehen
                                    (Autostart beim Anmelden und nach Updates in Steuerung)

Ein Paket-Update (frametide-tools postinst) schreibt die ID der neuesten Hinweise nach
/var/lib/frametide/whats-new-pending. Gesehene IDs merkt sich jeder Benutzer selbst.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frametide_common as ft  # noqa: E402
from frametide_common import Adw, Gio, GLib, Gtk, _  # noqa: E402
from frametide_common import INDIGO, TEAL, VIOLET, WaveHero, rgb  # noqa: E402
from frametide_i18n import localized  # noqa: E402

NOTES = os.path.join(os.environ.get("FRAMETIDE_DATA", "/usr/share/frametide"), "whats-new.json")
PENDING = "/var/lib/frametide/whats-new-pending"
SEEN = os.path.join(GLib.get_user_config_dir(), "frametide", "whats-new-seen")
RELEASES_URL = "https://github.com/ChopstickGuy/frametide-os/releases"

CSS = """
.wn-title { color: #F3F6FD; font-size: 1.9em; font-weight: 800; letter-spacing: -0.02em; }
.wn-sub { color: alpha(#C9D1E3, .85); }
.wn-kicker { color: #22D3EE; font-size: 0.78em; font-weight: 700; letter-spacing: 0.14em; }
.wn-item-title { font-weight: 700; }
.wn-badge-icon { color: #FFFFFF; }
.wn-footer { padding: 14px 24px 22px 24px; }
"""


def load_notes():
    try:
        with open(NOTES) as f:
            return json.load(f).get("releases", [])
    except (OSError, ValueError):
        return []


def read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


class IconBadge(Gtk.Overlay):
    """Rundes Symbol mit Farbverlauf – jede Neuerung bekommt ihren Farbton."""

    def __init__(self, icon, index):
        super().__init__(valign=Gtk.Align.START)
        area = Gtk.DrawingArea(content_width=42, content_height=42)
        stops = (TEAL, INDIGO, VIOLET)
        a, b = stops[index % 3], stops[(index + 1) % 3]

        def draw(_area, cr, w, h):
            import cairo
            grad = cairo.LinearGradient(0, h, w, 0)
            grad.add_color_stop_rgb(0, *rgb(a)[:3])
            grad.add_color_stop_rgb(1, *rgb(b)[:3])
            cr.arc(w / 2, h / 2, min(w, h) / 2, 0, 2 * math.pi)
            cr.set_source(grad)
            cr.fill()
        area.set_draw_func(draw)
        self.set_child(area)
        self.add_overlay(Gtk.Image(icon_name=icon, pixel_size=20, css_classes=["wn-badge-icon"],
                                   halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER))


class WhatsNewWindow(Adw.ApplicationWindow):
    def __init__(self, app, release):
        super().__init__(application=app, title=_("Neu in Frametide OS"), default_width=540,
                         default_height=720, resizable=True)
        self.release = release
        self.connect("close-request", self.on_close)

        hero = Gtk.Overlay()
        hero.set_child(WaveHero())
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_start=28, margin_end=28,
                       margin_top=34, valign=Gtk.Align.START)
        text.append(Gtk.Label(label=_("UPDATE").upper(), xalign=0, css_classes=["wn-kicker"]))
        text.append(Gtk.Label(label=_("Neu in Frametide OS"), xalign=0, css_classes=["wn-title"]))
        sub = localized(release, "title") if release.get("title") else ""
        if release.get("date"):
            sub = f"{sub} · {release['date']}" if sub else release["date"]
        if sub:
            text.append(Gtk.Label(label=sub, xalign=0, css_classes=["wn-sub"]))
        hero.add_overlay(text)
        close = Gtk.Button(icon_name="window-close-symbolic", css_classes=["circular", "osd"],
                           halign=Gtk.Align.END, valign=Gtk.Align.START, margin_top=12, margin_end=12,
                           tooltip_text=_("Schließen"))
        close.connect("clicked", lambda _b: self.close())
        hero.add_overlay(close)

        items = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=18, margin_bottom=8,
                        margin_start=24, margin_end=24)
        self.revealers = []
        for i, item in enumerate(release.get("items", [])):
            row = Gtk.Box(spacing=14, margin_top=8, margin_bottom=8)
            row.append(IconBadge(item.get("icon", "starred-symbolic"), i))
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True)
            col.append(Gtk.Label(label=localized(item, "title"), xalign=0, wrap=True, css_classes=["wn-item-title"]))
            col.append(Gtk.Label(label=localized(item, "text"), xalign=0, wrap=True,
                                 css_classes=["dim-label"]))
            row.append(col)
            rev = Gtk.Revealer(child=row, transition_type=Gtk.RevealerTransitionType.SLIDE_UP,
                               transition_duration=320)
            items.append(rev)
            self.revealers.append(rev)

        footer = Gtk.Box(spacing=12, css_classes=["wn-footer"])
        more = Gtk.LinkButton(uri=RELEASES_URL, label=_("Alle Änderungen"), hexpand=True,
                              halign=Gtk.Align.START)
        ok = Gtk.Button(label=_("Alles klar"), css_classes=["suggested-action", "pill"])
        ok.connect("clicked", lambda _b: self.close())
        footer.append(more)
        footer.append(ok)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        body.append(hero)
        body.append(Gtk.ScrolledWindow(child=items, vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER))
        body.append(footer)
        self.set_content(body)
        self.set_default_widget(ok)
        GLib.timeout_add(250, self.reveal_next, 0)

    def reveal_next(self, index):
        if index < len(self.revealers):
            self.revealers[index].set_reveal_child(True)
            GLib.timeout_add(110, self.reveal_next, index + 1)
        return False

    def on_close(self, _window):
        os.makedirs(os.path.dirname(SEEN), exist_ok=True)
        with open(SEEN, "w") as f:
            f.write(self.release.get("id", ""))
        return False


class WhatsNewApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.frametide.WhatsNew", flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
        releases = load_notes()
        if not releases:
            return 0
        release = releases[0]
        if "--if-pending" in args:
            pending = read(PENDING)
            if not pending or pending == read(SEEN) or "boot=casper" in read("/proc/cmdline"):
                return 0
            release = next((r for r in releases if r.get("id") == pending), release)
        ft.load_css()
        provider = Gtk.CssProvider()
        provider.load_from_string(CSS) if hasattr(provider, "load_from_string") else provider.load_from_data(CSS, -1)
        Gtk.StyleContext.add_provider_for_display(Gtk.Widget.get_display(Gtk.Label()), provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        (self.props.active_window or WhatsNewWindow(self, release)).present()
        return 0


if __name__ == "__main__":
    sys.exit(WhatsNewApp().run(sys.argv))
