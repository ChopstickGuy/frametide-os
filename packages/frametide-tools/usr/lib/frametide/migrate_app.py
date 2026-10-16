#!/usr/bin/python3
"""Windows-Umzug – übernimmt Dateien, Lesezeichen, WLAN und Steam-Spiele von Windows."""
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frametide_common as ft  # noqa: E402
import migrate  # noqa: E402
from frametide_common import Adw, Gio, GLib, Gtk, _  # noqa: E402


def human(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit in ("B", "KB") else f"{size:.1f} {unit}"
        size /= 1024


def page(title, child, button=None):
    view = Adw.ToolbarView(content=child)
    view.add_top_bar(Adw.HeaderBar())
    if button:
        bar = Gtk.Box(halign=Gtk.Align.CENTER, margin_top=12, margin_bottom=12)
        bar.append(button)
        view.add_bottom_bar(bar)
    return Adw.NavigationPage(title=title, child=view)


class MigrateWindow(Adw.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title=_("Windows-Umzug"), default_width=760, default_height=720)
        self.nav = Adw.NavigationView()
        self.set_content(self.nav)
        self.root = os.environ.get("FRAMETIDE_MIGRATE_ROOT")  # zum Testen ohne Partition
        if self.root:
            GLib.idle_add(self.show_choices)
        else:
            self.nav.add(self.build_start())

    # ------------------------------------------------------------ Schritt 1
    def build_start(self):
        prefs = Adw.PreferencesPage()
        intro = Adw.PreferencesGroup(
            title=_("Willkommen beim Umzug von Windows"),
            description=_("Wähle die Windows-Partition aus. Sie wird nur gelesen – an Windows wird nichts verändert."))
        prefs.add(intro)
        self.parts = Adw.PreferencesGroup(title=_("Gefundene Windows-Partitionen"))
        prefs.add(self.parts)
        parts = migrate.windows_partitions()
        self.part_check = None
        for p in parts:
            name = p["label"] or os.path.basename(p["path"])
            row = Adw.ActionRow(title=f"{name} ({human(p['size'])})", subtitle=p["path"])
            if p["bitlocker"]:
                row.set_subtitle(_("Mit BitLocker verschlüsselt – bitte in Windows vorher entschlüsseln "
                                   "oder die Dateien auf einen USB-Stick kopieren."))
                row.add_prefix(Gtk.Image(icon_name="channel-secure-symbolic"))
            else:
                check = Gtk.CheckButton(valign=Gtk.Align.CENTER, active=self.part_check is None)
                check.device = p["path"]
                if self.part_check:
                    check.set_group(self.part_check)
                self.part_check = self.part_check or check
                row.add_prefix(check)
                row.set_activatable_widget(check)
            self.parts.add(row)
        if not parts:
            self.parts.add(Adw.ActionRow(title=_("Keine Windows-Partition gefunden"),
                                         subtitle=_("Ist Windows auf einer anderen Festplatte, schließe sie an und starte den Umzug erneut.")))
        tip = Adw.PreferencesGroup(title=_("Tipp"), description=_(
            "Wenn Windows „Schnellstart“ nutzt, ist die Partition gesperrt. Fahre Windows dann einmal über "
            "„Neu starten“ herunter oder schalte Schnellstart in den Energieoptionen aus."))
        prefs.add(tip)
        self.next_btn = Gtk.Button(label=_("Weiter"), css_classes=["suggested-action", "pill"],
                                   sensitive=self.part_check is not None)
        self.next_btn.connect("clicked", self.on_mount)
        return page(_("Windows-Umzug"), prefs, self.next_btn)

    def on_mount(self, _btn):
        group_member = self.part_check
        device = next((c.device for c in self.all_checks(group_member) if c.get_active()), group_member.device)
        self.next_btn.set_sensitive(False)
        self.next_btn.set_label(_("Wird eingehängt …"))

        def work():
            return migrate.mount_readonly(device)

        def done(result):
            self.next_btn.set_sensitive(True)
            self.next_btn.set_label(_("Weiter"))
            if isinstance(result, Exception):
                self.error(_("Partition konnte nicht gelesen werden"), str(result))
            elif not migrate.is_windows(result):
                self.error(_("Keine Windows-Installation"), _("Auf dieser Partition wurde kein Windows gefunden."))
            else:
                self.root = result
                self.show_choices()
            return False
        ft.in_thread(work, done)

    @staticmethod
    def all_checks(first):
        checks, w = [], first.get_parent()
        while w and not isinstance(w, Adw.PreferencesGroup):
            w = w.get_parent()
        stack = [w] if w else []
        while stack:
            node = stack.pop()
            if isinstance(node, Gtk.CheckButton):
                checks.append(node)
            child = node.get_first_child()
            while child:
                stack.append(child)
                child = child.get_next_sibling()
        return checks

    # ------------------------------------------------------------ Schritt 2
    def show_choices(self):
        users = migrate.windows_users(self.root)
        if not users:
            self.error(_("Kein Benutzerkonto gefunden"), _("Unter „Users“ wurden keine Benutzerordner gefunden."))
            return False
        prefs = Adw.PreferencesPage()
        who = Adw.PreferencesGroup(title=_("Windows-Benutzer"))
        self.user_row = Adw.ComboRow(title=_("Benutzer"), model=Gtk.StringList.new(users))
        self.user_row.connect("notify::selected", lambda *_a: self.fill_choices())
        who.add(self.user_row)
        prefs.add(who)
        self.choices = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        prefs_box = prefs
        self.prefs = prefs_box
        self.groups = []
        start = Gtk.Button(label=_("Umzug starten"), css_classes=["suggested-action", "pill"])
        start.connect("clicked", self.start)
        self.nav.push(page(_("Was soll übernommen werden?"), prefs, start))
        self.fill_choices()
        return False

    def user(self):
        return self.user_row.get_model().get_string(self.user_row.get_selected())

    def fill_choices(self):
        for g in self.groups:
            self.prefs.remove(g)
        self.groups, self.selection = [], {"folders": [], "games": []}
        user = self.user()

        files = Adw.PreferencesGroup(title=_("Dateien"), description=_("Vorhandene Dateien unter Linux werden nie überschrieben."))
        for src, dest, label in migrate.user_folders(self.root, user):
            row = Adw.SwitchRow(title=label, subtitle=_("Größe wird berechnet …"), active=True)
            self.selection["folders"].append((row, src, dest, label))
            files.add(row)
            ft.in_thread(lambda s=src: migrate.folder_size(s),
                         lambda size, r=row, d=dest: r.set_subtitle(
                             f"{human(size)} → {d.replace(os.path.expanduser('~'), '~', 1)}") or False)
        self.add_group(files)

        trees = migrate.browser_bookmarks(self.root, user)
        self.trees = trees
        web = Adw.PreferencesGroup(title=_("Browser-Lesezeichen"))
        count = sum(migrate.count_bookmarks(t) for _n, t in trees)
        self.bookmarks_row = Adw.SwitchRow(
            title=_("{n} Lesezeichen").format(n=count),
            subtitle=", ".join(n for n, _t in trees) or _("Keine gefunden"), active=count > 0, sensitive=count > 0)
        web.add(self.bookmarks_row)
        self.add_group(web)

        self.wifi = migrate.wifi_profiles(self.root, user)
        with_key = [p for p in self.wifi if p["key"]]
        wlan = Adw.PreferencesGroup(title=_("WLAN"), description=_(
            "Windows speichert WLAN-Passwörter verschlüsselt. Für die Übernahme vorher in Windows ausführen: "
            "netsh wlan export profile key=clear folder=%USERPROFILE%\\Desktop"))
        self.wifi_row = Adw.SwitchRow(
            title=_("{n} WLAN-Netzwerke mit Passwort").format(n=len(with_key)),
            subtitle=", ".join(p["ssid"] for p in with_key) or _("Ohne Export keine Passwörter verfügbar"),
            active=bool(with_key), sensitive=bool(with_key))
        wlan.add(self.wifi_row)
        self.add_group(wlan)

        games = migrate.windows_steam_games(self.root)
        library = migrate.linux_steam_library()
        steam = Adw.PreferencesGroup(title=_("Steam-Spiele"), description=_(
            "Installierte Spiele werden kopiert statt neu heruntergeladen. Steam prüft sie beim nächsten Start."))
        if games and not library:
            steam.add(Adw.ActionRow(title=_("Steam zuerst einmal starten und anmelden"),
                                    subtitle=_("Danach den Umzug erneut öffnen, um Spiele zu übernehmen.")))
        for appid, name, size, manifest, folder in games:
            row = Adw.SwitchRow(title=name, subtitle=human(size), active=False, sensitive=bool(library))
            self.selection["games"].append((row, name, manifest, folder))
            steam.add(row)
        if not games:
            steam.add(Adw.ActionRow(title=_("Keine Steam-Spiele auf dieser Partition")))
        self.library = library
        self.add_group(steam)

    def add_group(self, group):
        self.prefs.add(group)
        self.groups.append(group)

    # ------------------------------------------------------------ Schritt 3
    def start(self, _btn):
        jobs = [(_("Kopiere {name}").format(name=label), "folder", (src, dest))
                for row, src, dest, label in self.selection["folders"] if row.get_active()]
        if self.bookmarks_row.get_active():
            jobs.append((_("Lesezeichen"), "bookmarks", None))
        if self.wifi_row.get_active():
            jobs.append((_("WLAN-Netzwerke"), "wifi", None))
        jobs += [(_("Kopiere Spiel {name}").format(name=name), "game", (manifest, folder))
                 for row, name, manifest, folder in self.selection["games"] if row.get_active()]
        if not jobs:
            return

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_start=32, margin_end=32,
                      valign=Gtk.Align.CENTER)
        self.status = Gtk.Label(css_classes=["title-3"], wrap=True)
        self.bar = Gtk.ProgressBar(show_text=True)
        self.overall = Gtk.Label(css_classes=["dim-label"])
        for w in (self.status, self.bar, self.overall):
            box.append(w)
        self.nav.push(page(_("Umzug läuft"), Adw.Clamp(child=box, maximum_size=560)))
        self.results = []
        threading.Thread(target=self.run_jobs, args=(jobs,), daemon=True).start()

    def ui(self, func, *args):
        GLib.idle_add(lambda: (func(*args), False)[1])

    def run_jobs(self, jobs):
        user = self.user()
        for i, (title, kind, data) in enumerate(jobs, 1):
            self.ui(self.status.set_label, title)
            self.ui(self.overall.set_label, _("Schritt {i} von {n}").format(i=i, n=len(jobs)))
            self.ui(self.bar.set_fraction, 0.0)
            progress = lambda pct: self.ui(self.bar.set_fraction, pct / 100)
            try:
                if kind == "folder":
                    ok = migrate.copy_folder(*data, progress) == 0
                    self.results.append((title, ok))
                elif kind == "game":
                    ok = migrate.copy_steam_game(*data, self.library, progress) == 0
                    self.results.append((title, ok))
                elif kind == "bookmarks":
                    from gi.repository import GLib as G
                    docs = G.get_user_special_dir(G.UserDirectory.DIRECTORY_DOCUMENTS) or os.path.expanduser("~")
                    os.makedirs(docs, exist_ok=True)
                    self.bookmark_file = os.path.join(docs, _("Lesezeichen aus Windows") + ".html")
                    with open(self.bookmark_file, "w", encoding="utf-8") as f:
                        f.write(migrate.bookmarks_html(self.trees))
                    self.results.append((title, True))
                elif kind == "wifi":
                    keyed = [p for p in self.wifi if p["key"]]
                    ok = sum(migrate.import_wifi(p) for p in keyed)
                    self.results.append((_("{ok} von {n} WLAN-Netzwerken").format(ok=ok, n=len(keyed)), ok == len(keyed)))
            except Exception as e:  # einzelner Fehler soll den Rest nicht abbrechen
                self.results.append((f"{title}: {e}", False))
            self.ui(self.bar.set_fraction, 1.0)
        self.ui(self.finish)

    def finish(self):
        prefs = Adw.PreferencesPage()
        ok = all(r for _t, r in self.results)
        details = Adw.PreferencesGroup(
            title=_("Umzug abgeschlossen") if ok else _("Umzug mit Problemen abgeschlossen"),
            description=_("Willkommen bei Frametide OS!") if ok else _("Details siehe unten."))
        for title, success in self.results:
            row = Adw.ActionRow(title=title)
            row.add_suffix(Gtk.Image(icon_name="emblem-ok-symbolic" if success else "dialog-error-symbolic"))
            details.add(row)
        prefs.add(details)
        if getattr(self, "bookmark_file", None):
            hint = Adw.PreferencesGroup(title=_("Lesezeichen importieren"), description=_(
                "Im Browser: Lesezeichen → Lesezeichen importieren → HTML-Datei. Die Datei liegt hier:"))
            hint.add(Adw.ActionRow(title=self.bookmark_file.replace(os.path.expanduser("~"), "~", 1)))
            prefs.add(hint)
        close = Gtk.Button(label=_("Fertig"), css_classes=["suggested-action", "pill"])
        close.connect("clicked", lambda _b: self.close())
        self.nav.push(page(_("Fertig"), prefs, close))

    def error(self, title, text):
        dialog = Adw.MessageDialog(transient_for=self, heading=title, body=text)
        dialog.add_response("ok", _("OK"))
        dialog.present()


class MigrateApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.frametide.Migrate", flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        ft.load_css()
        (self.props.active_window or MigrateWindow(self)).present()


if __name__ == "__main__":
    sys.exit(MigrateApp().run(sys.argv))
