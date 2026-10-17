#!/usr/bin/python3
"""Frametide Willkommen – erster Start: die wichtigsten Wege mit einem Klick."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frametide_common as ft  # noqa: E402
from frametide_common import Adw, Gio, GLib, Gtk, _  # noqa: E402

CONFIG = os.path.join(GLib.get_user_config_dir(), "frametide")
DONT_SHOW = os.path.join(CONFIG, "welcome-done")

TILES = [
    # Icon, Titel, Beschreibung, Befehl
    ("frametide-store", _("Apps & Spiele"), _("Steam, Discord, Office, Kreativ-Apps …"), ["frametide-store"]),
    ("frametide-center", _("Updates & Treiber"), _("System aktuell halten, Grafiktreiber"), ["frametide-center", "updates"]),
    ("input-gaming", _("Spiele-Check"), _("Läuft mein Spiel unter Linux?"), ["frametide-center", "games"]),
    ("frametide-logo", _("Von Windows umziehen"), _("Dateien, Lesezeichen, WLAN, Spiele"), ["frametide-migrate"]),
    ("frametide-dev", _("Entwickeln"), _("Git, Sprachen, Datenbanken, Projekte"), ["frametide-dev"]),
    ("openrgb", _("RGB & Lüfter"), _("Beleuchtung und Lüfterkurven"), ["frametide-center", "hardware"]),
    ("org.gnome.Settings", _("Einstellungen"), _("Bildschirm, Ton, Konten, Design"), ["gnome-control-center"]),
]


def status_text():
    hw = os.path.exists("/var/lib/frametide/hwsetup.done")
    apps = os.path.exists("/var/lib/frametide/vendor-apps.done")
    if hw and apps:
        return _("✓ Treiber eingerichtet · Chrome und VS Code installiert")
    return _("Treiber, Chrome und VS Code werden im Hintergrund eingerichtet, sobald Internet da ist. "
             "Du kannst schon loslegen.")


class Tile(Gtk.Button):
    def __init__(self, icon, title, subtitle, command):
        super().__init__(css_classes=["card", "ft-tile"])
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=18, margin_bottom=18,
                      margin_start=12, margin_end=12)
        box.append(ft.icon_widget(icon, 56))
        box.append(Gtk.Label(label=title, css_classes=["heading"], wrap=True, justify=Gtk.Justification.CENTER))
        box.append(Gtk.Label(label=subtitle, css_classes=["dim-label", "caption"], wrap=True,
                             justify=Gtk.Justification.CENTER, max_width_chars=22))
        self.set_child(box)
        self.connect("clicked", lambda _b: Gio.Subprocess.new(command, Gio.SubprocessFlags.NONE))


class WelcomeWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=_("Willkommen bei Frametide OS"),
                         default_width=880, default_height=740)
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin_top=28,
                       margin_bottom=24, margin_start=32, margin_end=32)
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, css_classes=["ft-hero"])
        hero.append(Gtk.Label(label=_("Willkommen bei Frametide OS"), xalign=0, css_classes=["title-1"]))
        hero.append(Gtk.Label(label=_("Alles Wichtige ist nur einen Klick entfernt."), xalign=0, wrap=True))
        page.append(hero)

        grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True,
                           min_children_per_line=2, max_children_per_line=3,
                           column_spacing=12, row_spacing=12)
        for tile in TILES:
            grid.append(Tile(*tile))
        page.append(grid)

        status = Adw.ActionRow(title=_("Einrichtung"), subtitle=status_text())
        status.add_prefix(Gtk.Image(icon_name="emblem-system-symbolic"))
        box = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        box.append(status)
        page.append(box)

        bottom = Gtk.Box(spacing=12)
        self.show_again = Gtk.CheckButton(label=_("Beim Anmelden anzeigen"), active=not os.path.exists(DONT_SHOW),
                                          hexpand=True)
        self.show_again.connect("toggled", self.on_toggle)
        close = Gtk.Button(label=_("Los geht's"), css_classes=["suggested-action", "pill"])
        close.connect("clicked", lambda _b: self.close())
        bottom.append(self.show_again)
        bottom.append(close)
        page.append(bottom)

        view = Adw.ToolbarView(content=Gtk.ScrolledWindow(child=page, hscrollbar_policy=Gtk.PolicyType.NEVER))
        view.add_top_bar(Adw.HeaderBar(show_title=False))
        self.set_content(view)

    def on_toggle(self, check):
        os.makedirs(CONFIG, exist_ok=True)
        if check.get_active():
            if os.path.exists(DONT_SHOW):
                os.remove(DONT_SHOW)
        else:
            open(DONT_SHOW, "w").close()


class WelcomeApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.frametide.Welcome", flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
        # Autostart: nur beim ersten Mal, bis der Haken entfernt wird; nie im Live-System
        if "--autostart" in args and (os.path.exists(DONT_SHOW) or "boot=casper" in open("/proc/cmdline").read()):
            return 0
        ft.load_css()
        (self.props.active_window or WelcomeWindow(self)).present()
        return 0


if __name__ == "__main__":
    sys.exit(WelcomeApp().run(sys.argv))
