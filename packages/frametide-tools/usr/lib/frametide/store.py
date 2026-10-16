#!/usr/bin/python3
"""Frametide Store – kuratierte Apps (Ubuntu, Flathub, ArtCraft) mit einem Klick."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frametide_common as ft  # noqa: E402
from frametide_common import Adw, Gio, Gtk, _  # noqa: E402

SOURCE_LABEL = {"apt": "Ubuntu", "flatpak": "Flathub", "craft": "ArtCraft"}


class AppCard(Gtk.Box):
    def __init__(self, store, app):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=14,
                         css_classes=["card", "ft-card"], valign=Gtk.Align.START,
                         width_request=280)
        self.store, self.app = store, app
        self.append(ft.icon_widget(app["icon"], 52, app["id"]))

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, hexpand=True,
                       valign=Gtk.Align.CENTER)
        text.append(Gtk.Label(label=app["name"], xalign=0, css_classes=["heading"],
                              ellipsize=3, max_width_chars=18, width_chars=12))
        text.append(Gtk.Label(label=ft.localized(app, "summary"), xalign=0, wrap=True, lines=2,
                              ellipsize=3, css_classes=["dim-label", "caption"],
                              max_width_chars=20, width_chars=16))
        text.append(Gtk.Label(label=SOURCE_LABEL[app["source"]], xalign=0, halign=Gtk.Align.START,
                              css_classes=["ft-badge", "caption"]))
        self.append(text)

        self.button = Gtk.Button(valign=Gtk.Align.CENTER, width_request=104)
        self.button.connect("clicked", self.on_clicked)
        self.append(self.button)
        self.update()

    def installed(self):
        return self.store.is_installed(self.app)

    def update(self):
        busy = self.store.busy_id == self.app["id"]
        queued = self.app["id"] in self.store.queue_ids()
        if busy or queued:
            box = Gtk.Box(spacing=6, halign=Gtk.Align.CENTER)
            box.append(Gtk.Spinner(spinning=busy))
            box.append(Gtk.Label(label=_("Läuft …") if busy else _("Wartet")))
            self.button.set_child(box)
            self.button.set_sensitive(False)
            self.button.set_css_classes([])
        elif self.installed():
            self.button.set_child(None)
            self.button.set_label(_("Entfernen"))
            self.button.set_sensitive(True)
            self.button.set_css_classes(["flat"])
        else:
            self.button.set_child(None)
            self.button.set_label(_("Installieren"))
            self.button.set_sensitive(True)
            self.button.set_css_classes(["suggested-action"])

    def on_clicked(self, _button):
        if self.installed():
            self.store.confirm_remove(self.app)
        else:
            self.store.enqueue(self.app, "install")


class StoreWindow(Adw.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title="Frametide Store",
                         default_width=1180, default_height=760)
        with open(os.path.join(ft.DATA_DIR, "store", "catalog.json")) as f:
            self.catalog = json.load(f)
        self.apps = [a for c in self.catalog["categories"] for a in c["apps"]]
        self.cards, self.queue, self.busy_id = [], [], None
        self.refresh_state()

        self.toasts = Adw.ToastOverlay()
        split = Adw.NavigationSplitView(sidebar_width_fraction=0.22, min_sidebar_width=220)
        split.set_sidebar(self.build_sidebar())
        split.set_content(self.build_content())
        self.toasts.set_child(split)
        self.set_content(self.toasts)
        self.sidebar.select_row(self.sidebar.get_row_at_index(0))

    # -------------------------------------------------------------- Aufbau
    def build_sidebar(self):
        self.sidebar = Gtk.ListBox(css_classes=["navigation-sidebar"])
        self.pages = [("discover", _("Entdecken"), "starred-symbolic")]
        self.pages += [(c["id"], ft.localized(c, "name"), c["icon"]) for c in self.catalog["categories"]]
        self.pages += [("installed", _("Installiert"), "emblem-ok-symbolic")]
        for _id, name, icon in self.pages:
            row = Gtk.Box(spacing=12, margin_start=6, margin_top=6, margin_bottom=6)
            row.append(Gtk.Image.new_from_icon_name(icon))
            row.append(Gtk.Label(label=name, xalign=0))
            self.sidebar.append(row)
        self.sidebar.connect("row-selected", self.on_page_selected)
        view = Adw.ToolbarView()
        view.add_top_bar(Adw.HeaderBar(title_widget=Adw.WindowTitle(title="Store")))
        view.set_content(Gtk.ScrolledWindow(child=self.sidebar))
        return Adw.NavigationPage(title="Store", child=view)

    def build_content(self):
        self.search = Gtk.SearchEntry(placeholder_text=_("Apps suchen – auch auf ganz Flathub"),
                                      width_request=380)
        self.search.connect("search-changed", self.on_search)
        header = Adw.HeaderBar(title_widget=self.search)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                            margin_top=24, margin_bottom=32, margin_start=24, margin_end=24)
        clamp = Adw.Clamp(maximum_size=1200, child=self.body)
        view = Adw.ToolbarView()
        view.add_top_bar(header)
        view.set_content(Gtk.ScrolledWindow(child=clamp, vexpand=True,
                                            hscrollbar_policy=Gtk.PolicyType.NEVER))
        self.content_page = Adw.NavigationPage(title=_("Entdecken"), child=view)
        return self.content_page

    def clear(self):
        while child := self.body.get_first_child():
            self.body.remove(child)
        self.cards = []

    def section(self, title, apps, subtitle=None):
        if title:
            self.body.append(Gtk.Label(label=title, xalign=0, css_classes=["title-2"]))
        if subtitle:
            self.body.append(Gtk.Label(label=subtitle, xalign=0, wrap=True, css_classes=["dim-label"]))
        grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True,
                           min_children_per_line=1, max_children_per_line=3,
                           column_spacing=12, row_spacing=12)
        for app in apps:
            card = AppCard(self, app)
            self.cards.append(card)
            grid.append(card)
        self.body.append(grid)
        return grid

    def show_page(self, page_id):
        self.clear()
        if page_id == "discover":
            self.content_page.set_title(_("Entdecken"))
            hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, css_classes=["ft-hero"])
            hero.append(Gtk.Label(label=_("Willkommen im Frametide Store"), xalign=0,
                                  css_classes=["title-1"]))
            hero.append(Gtk.Label(label=_("Spiele, Kreativ-Apps, Office und Werkzeuge – geprüft und "
                                          "mit einem Klick installiert."), xalign=0, wrap=True))
            self.body.append(hero)
            self.section(_("Empfohlen"), [a for a in self.apps if a.get("featured")])
            craft = [a for a in self.apps if a["source"] == "craft" and not self.is_installed(a)]
            if craft:
                row = Adw.ActionRow(title=_("Komplettes ArtCraft-Paket installieren"),
                                    subtitle=_("{n} weitere Craft-Apps (Foto, Video, Vektor, Audio, CAD …)")
                                    .format(n=len(craft)))
                row.add_prefix(Gtk.Image.new_from_icon_name("applications-graphics-symbolic"))
                btn = Gtk.Button(label=_("Alle installieren"), valign=Gtk.Align.CENTER,
                                 css_classes=["suggested-action"])
                btn.connect("clicked", lambda _b: [self.enqueue(a, "install") for a in craft])
                row.add_suffix(btn)
                box = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
                box.append(row)
                self.body.append(box)
        elif page_id == "installed":
            self.content_page.set_title(_("Installiert"))
            apps = [a for a in self.apps if self.is_installed(a)]
            self.section(None, apps, _("Aus dem Store installierte Apps. Updates gibt es im Frametide Center."))
        else:
            cat = next(c for c in self.catalog["categories"] if c["id"] == page_id)
            self.content_page.set_title(ft.localized(cat, "name"))
            self.section(ft.localized(cat, "name"), cat["apps"])

    # ------------------------------------------------------------- Status
    def refresh_state(self):
        apt = [a["ref"] for a in self.apps if a["source"] in ("apt", "craft")]
        self.apt_installed = ft.apt_installed(apt)
        self.flatpak_installed = ft.flatpak_installed()

    def is_installed(self, app):
        if app["source"] == "flatpak":
            return app["ref"] in self.flatpak_installed
        return app["ref"] in self.apt_installed

    def queue_ids(self):
        return {a["id"] for a, _action in self.queue}

    def update_cards(self):
        for card in self.cards:
            card.update()

    # ------------------------------------------------------- Installation
    def enqueue(self, app, action):
        if app["id"] in self.queue_ids() or self.busy_id == app["id"]:
            return
        self.queue.append((app, action))
        self.update_cards()
        if self.busy_id is None:
            self.next_job()

    def next_job(self):
        if not self.queue:
            self.busy_id = None
            self.update_cards()
            return
        app, action = self.queue.pop(0)
        self.busy_id = app["id"]
        self.update_cards()
        src, ref = app["source"], app["ref"]
        if src == "flatpak":
            argv = (["flatpak", "install", "--system", "-y", "--noninteractive", "flathub", ref]
                    if action == "install" else ["flatpak", "uninstall", "--system", "-y", "--noninteractive", ref])
        elif src == "craft" and action == "install":
            argv = ft.helper_argv("craft-install", ref)
        else:
            argv = ft.helper_argv("install" if action == "install" else "remove", ref)
        self.last_lines = []
        ft.Task(argv, on_line=self.last_lines.append,
                on_done=lambda status: self.job_done(app, action, status))

    def job_done(self, app, action, status):
        self.refresh_state()
        if status == 0:
            text = _("{app} wurde installiert") if action == "install" else _("{app} wurde entfernt")
            self.toasts.add_toast(Adw.Toast(title=text.format(app=app["name"]), timeout=3))
        elif status in (126, 127) and not self.last_lines:
            self.toasts.add_toast(Adw.Toast(title=_("Abgebrochen"), timeout=3))
        else:
            reason = self.last_lines[-1] if self.last_lines else _("Fehlercode {code}").format(code=status)
            self.toasts.add_toast(Adw.Toast(title=f"{app['name']}: {reason}", timeout=6))
        self.next_job()

    def confirm_remove(self, app):
        dialog = Adw.MessageDialog(transient_for=self, heading=_("{app} entfernen?").format(app=app["name"]),
                                   body=_("Deine eigenen Dateien bleiben erhalten."))
        dialog.add_response("cancel", _("Abbrechen"))
        dialog.add_response("remove", _("Entfernen"))
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", lambda _d, r: r == "remove" and self.enqueue(app, "remove"))
        dialog.present()

    # --------------------------------------------------------------- Suche
    def on_page_selected(self, _box, row):
        if row is not None:
            self.search.set_text("")
            self.show_page(self.pages[row.get_index()][0])

    def on_search(self, entry):
        text = entry.get_text().strip().lower()
        if not text:
            row = self.sidebar.get_selected_row()
            self.show_page(self.pages[row.get_index()][0] if row else "discover")
            return
        self.clear()
        self.content_page.set_title(_("Suche"))
        hits = [a for a in self.apps
                if text in " ".join((a["name"], a["summary"], a.get("summary_en", ""))).lower()]
        if hits:
            self.section(_("Im Store"), hits)
        if len(text) >= 3:
            known = {a["ref"] for a in self.apps}
            lines = []
            ft.Task(["flatpak", "search", "--columns=application,name,description", text],
                    on_line=lines.append,
                    on_done=lambda _s: self.show_flathub(text, lines, known))
        elif not hits:
            self.body.append(Adw.StatusPage(icon_name="system-search-symbolic", title=_("Nichts gefunden")))

    def show_flathub(self, text, lines, known):
        if self.search.get_text().strip().lower() != text:
            return  # Suche hat sich inzwischen geändert
        extra = []
        for line in lines:
            parts = line.split("\t")
            if len(parts) >= 2 and "." in parts[0] and parts[0] not in known:
                extra.append({"id": "fh:" + parts[0], "name": parts[1], "summary": (parts[2:] or [""])[0],
                              "icon": parts[0], "source": "flatpak", "ref": parts[0]})
        if extra:
            self.section(_("Weitere Apps von Flathub"), extra[:30])
        elif not self.cards:
            self.body.append(Adw.StatusPage(icon_name="system-search-symbolic", title=_("Nichts gefunden"),
                                            description=_("Versuch einen anderen Suchbegriff.")))


class StoreApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.frametide.Store", flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        ft.load_css()
        (self.props.active_window or StoreWindow(self)).present()


if __name__ == "__main__":
    sys.exit(StoreApp().run(sys.argv))
