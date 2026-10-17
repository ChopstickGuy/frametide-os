#!/usr/bin/python3
"""Frametide Entwicklerzentrale – Einrichtung, lokale Dienste & Ports, Projekt-Starter."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import devtools as dt  # noqa: E402
import frametide_common as ft  # noqa: E402
from frametide_common import Adw, Gio, GLib, Gtk, _  # noqa: E402

PROJECTS_DIR = os.path.join(os.path.expanduser("~"), _("Projekte"))


def group(title, description=None):
    return Adw.PreferencesGroup(title=title, description=description)


def button(label, style="flat", callback=None):
    b = Gtk.Button(label=label, valign=Gtk.Align.CENTER, css_classes=[style] if style else [])
    if callback:
        b.connect("clicked", lambda _b: callback())
    return b


def open_terminal(*command):
    for prefix in (["xdg-terminal-exec"], ["ptyxis", "--new-window", "--"], ["gnome-terminal", "--"]):
        if dt.have(prefix[0]):
            Gio.Subprocess.new(prefix + list(command), Gio.SubprocessFlags.NONE)
            return True
    return False


class SetupPage(Adw.PreferencesPage):
    def __init__(self, window):
        super().__init__(title=_("Einrichtung"), icon_name="emblem-system-symbolic")
        self.window = window

        # --- Git
        name, email = dt.git_identity()
        git = group(_("Git"), _("Name und E-Mail erscheinen in deinen Commits."))
        self.name = Adw.EntryRow(title=_("Name"), text=name)
        self.email = Adw.EntryRow(title=_("E-Mail"), text=email)
        git.add(self.name)
        git.add(self.email)
        save = Adw.ActionRow(title=_("Git einrichten"),
                             subtitle=_("Setzt auch „main“ als Standard-Branch und sinnvolle Push-/Pull-Vorgaben."))
        save.add_suffix(button(_("Speichern"), "suggested-action", self.save_git))
        git.add(save)
        self.add(git)

        # --- SSH & GitHub
        keys = group(_("SSH-Schlüssel & GitHub"))
        self.ssh_row = Adw.ActionRow(title=_("SSH-Schlüssel"))
        keys.add(self.ssh_row)
        self.gh_row = Adw.ActionRow(title="GitHub")
        keys.add(self.gh_row)
        self.add(keys)
        self.refresh_keys()

        # --- Sprachen
        langs = group(_("Programmiersprachen"),
                      _("Über mise: immer die neueste Version, mehrere Versionen parallel, ohne das System zu "
                        "verändern. Pro Projekt lassen sich Versionen in einer mise.toml festlegen."))
        self.lang_rows = {}
        installed = dt.mise_installed_tools()
        for tool, label, _cmd in dt.LANGUAGES:
            row = Adw.ActionRow(title=label)
            row.btn = button(_("Installieren"), "flat", lambda t=tool: self.install_lang(t))
            row.add_suffix(row.btn)
            self.lang_rows[tool] = row
            langs.add(row)
        self.show_langs(installed)
        if not dt.have("mise"):
            langs.set_description(_("mise ist nicht installiert – im App Store oder mit „sudo apt install mise“."))
        self.task = Gtk.Label(xalign=0, wrap=True, css_classes=["dim-label", "caption"])
        langs.add(self.task)
        self.add(langs)

    def save_git(self):
        name, email = self.name.get_text().strip(), self.email.get_text().strip()
        if not name or "@" not in email:
            self.window.toast(_("Bitte Name und eine gültige E-Mail eingeben."))
            return
        dt.set_git_identity(name, email)
        self.window.toast(_("Git ist eingerichtet."))

    def refresh_keys(self):
        for row in (self.ssh_row, self.gh_row):
            while getattr(row, "_suffixes", None):
                row.remove(row._suffixes.pop())
            row._suffixes = []
        key = dt.ssh_public_key()
        if key:
            self.ssh_row.set_subtitle(_("Vorhanden (ed25519)"))
            b = button(_("Kopieren"), "flat", lambda: self.copy(key, _("Öffentlicher Schlüssel kopiert")))
        else:
            self.ssh_row.set_subtitle(_("Noch kein Schlüssel – nötig für GitHub, GitLab und Server."))
            b = button(_("Erstellen"), "suggested-action", self.make_key)
        self.ssh_row.add_suffix(b)
        self.ssh_row._suffixes.append(b)

        user = dt.github_status()
        if user:
            self.gh_row.set_subtitle(_("Angemeldet als {user}").format(user=user))
            b = button(_("Schlüssel hochladen"), "flat",
                       lambda: open_terminal("gh", "ssh-key", "add", dt.SSH_KEY + ".pub", "--title", "Frametide OS"))
        else:
            self.gh_row.set_subtitle(_("Nicht angemeldet – Anmeldung im Browser, lädt den SSH-Schlüssel mit hoch."))
            b = button(_("Anmelden"), "suggested-action",
                       lambda: open_terminal("gh", "auth", "login", "--web", "--git-protocol", "ssh"))
        self.gh_row.add_suffix(b)
        self.gh_row._suffixes.append(b)

    def make_key(self):
        if dt.create_ssh_key(self.email.get_text().strip()):
            self.window.toast(_("SSH-Schlüssel erstellt"))
        self.refresh_keys()

    def copy(self, text, message):
        self.get_display().get_clipboard().set(text)
        self.window.toast(message)

    def show_langs(self, installed):
        for tool, row in self.lang_rows.items():
            version = installed.get(tool)
            row.set_subtitle(_("Version {v}").format(v=version) if version else _("Nicht installiert"))
            row.btn.set_label(_("Aktualisieren") if version else _("Installieren"))
            row.btn.set_sensitive(dt.have("mise"))

    def install_lang(self, tool):
        for row in self.lang_rows.values():
            row.btn.set_sensitive(False)
        self.task.set_label(_("{tool} wird installiert – das kann ein paar Minuten dauern …").format(tool=tool))
        lines = []

        def done(status):
            self.task.set_label(_("Fertig ✓ – in neuen Terminals verfügbar.") if status == 0
                                else (lines[-1] if lines else _("Fehlgeschlagen")))
            ft.in_thread(dt.mise_installed_tools, lambda inst: (self.show_langs(inst), False)[1])
        ft.Task(dt.mise_install_argv(tool), on_line=lambda l: (lines.append(l), self.task.set_label(l[:120])),
                on_done=done)


class ServicesPage(Adw.PreferencesPage):
    def __init__(self, window):
        super().__init__(title=_("Dienste & Ports"), icon_name="network-server-symbolic")
        self.window = window
        self.services = group(_("Datenbanken & Dienste"),
                              _("Laufen als Container nur auf diesem Rechner (127.0.0.1). Daten bleiben beim Stoppen "
                                "erhalten. Benutzer „dev“, Passwort „frametide“."))
        self.rows = {}
        for svc in dt.SERVICES:
            row = Adw.ActionRow(title=svc[1], subtitle=svc[6])
            row.toggle = button(_("Starten"), "flat")
            row.toggle.connect("clicked", lambda _b, s=svc: self.toggle(s))
            row.add_suffix(button(_("Kopieren"), "flat", lambda s=svc: self.copy(s[6])))
            row.add_suffix(row.toggle)
            self.rows[svc[0]] = row
            self.services.add(row)
        if not dt.have("podman"):
            self.services.set_description(_("Podman fehlt – „sudo apt install podman“."))
        self.add(self.services)

        self.ports = group(_("Laufende Server"), _("Deine Programme, die gerade auf einem Port lauschen."))
        self.add(self.ports)
        self.port_rows = []
        self.refresh()
        GLib.timeout_add_seconds(3, self.refresh)

    def copy(self, text):
        self.get_display().get_clipboard().set(text)
        self.window.toast(_("Kopiert: {text}").format(text=text))

    def toggle(self, svc):
        running = self.states.get(svc[0]) == "running"
        argv = dt.service_stop_argv(svc) if running else dt.service_start_argv(svc)
        row = self.rows[svc[0]]
        row.toggle.set_sensitive(False)
        row.toggle.set_label(_("Stoppt …") if running else _("Startet …"))
        lines = []

        def done(status):
            row.toggle.set_sensitive(True)
            if status != 0:
                self.window.toast(lines[-1] if lines else _("Fehlgeschlagen"))
            self.refresh()
        ft.Task(argv, on_line=lines.append, on_done=done)

    def refresh(self):
        ft.in_thread(lambda: (dt.service_states(), dt.listening_ports()), self.show)
        return True

    def show(self, result):
        if isinstance(result, Exception):
            return False
        self.states, ports = result
        for sid, row in self.rows.items():
            if not row.toggle.get_sensitive():
                continue
            running = self.states.get(sid) == "running"
            row.toggle.set_label(_("Stoppen") if running else _("Starten"))
            row.toggle.set_css_classes(["destructive-action"] if running else ["suggested-action"])
        for r in self.port_rows:
            self.ports.remove(r)
        self.port_rows = []
        for port, prog, pid, addr in ports:
            row = Adw.ActionRow(title=f"{prog} · :{port}", subtitle=f"{addr or '*'} · PID {pid}")
            row.add_suffix(button(_("Öffnen"), "flat",
                                  lambda p=port: Gio.AppInfo.launch_default_for_uri(f"http://localhost:{p}", None)))
            row.add_suffix(button(_("Beenden"), "flat", lambda p=pid: (os.kill(p, 15), self.refresh())))
            self.ports.add(row)
            self.port_rows.append(row)
        if not ports:
            empty = Adw.ActionRow(title=_("Gerade läuft kein Server"),
                                  subtitle=_("Starte z. B. „npm run dev“ – er erscheint dann hier."))
            self.ports.add(empty)
            self.port_rows.append(empty)
        return False


class ProjectsPage(Adw.PreferencesPage):
    def __init__(self, window):
        super().__init__(title=_("Projekte"), icon_name="folder-new-symbolic")
        self.window = window
        new = group(_("Neues Projekt"), _("Mit Git, .gitignore, Dev-Container, VS-Code-Empfehlungen und README."))
        self.name = Adw.EntryRow(title=_("Projektname"))
        new.add(self.name)
        self.template_ids = list(dt.TEMPLATES)
        self.template = Adw.ComboRow(title=_("Vorlage"),
                                     model=Gtk.StringList.new([dt.TEMPLATES[t]["name"] for t in self.template_ids]))
        new.add(self.template)
        self.base = PROJECTS_DIR
        self.location = Adw.ActionRow(title=_("Ort"), subtitle=self.pretty(self.base))
        self.location.add_suffix(button(_("Ändern"), "flat", self.choose_dir))
        new.add(self.location)
        self.git = Adw.SwitchRow(title=_("Git-Repository anlegen"), active=True)
        self.devcontainer = Adw.SwitchRow(title=_("Dev-Container-Konfiguration"), active=True)
        new.add(self.git)
        new.add(self.devcontainer)
        create = Adw.ActionRow(title=_("Projekt erstellen"), subtitle=_("Öffnet danach VS Code im Projekt."))
        create.add_suffix(button(_("Erstellen"), "suggested-action", self.create))
        new.add(create)
        self.add(new)
        self.recent = group(_("Deine Projekte"))
        self.add(self.recent)
        self.recent_rows = []
        self.list_projects()

    def choose_dir(self):
        dialog = Gtk.FileDialog(title=_("Ort für Projekte"))
        dialog.select_folder(self.window, None, self.on_dir)

    def on_dir(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:
            return
        self.base = folder.get_path()
        self.location.set_subtitle(self.pretty(self.base))
        self.list_projects()

    def create(self):
        name = self.name.get_text().strip()
        if not name:
            self.window.toast(_("Bitte einen Projektnamen eingeben."))
            return
        base = self.base
        try:
            os.makedirs(base, exist_ok=True)
            path = dt.create_project(base, name, self.template_ids[self.template.get_selected()],
                                     self.git.get_active(), self.devcontainer.get_active())
        except (OSError, FileExistsError) as e:
            self.window.toast(str(e))
            return
        self.window.toast(_("Projekt erstellt: {path}").format(path=path))
        self.name.set_text("")
        self.open_project(path)
        self.list_projects()

    @staticmethod
    def pretty(path):
        return path.replace(os.path.expanduser("~"), "~", 1)

    @staticmethod
    def open_project(path):
        if dt.have("code"):
            Gio.Subprocess.new(["code", path], Gio.SubprocessFlags.NONE)
        else:
            Gio.AppInfo.launch_default_for_uri(Gio.File.new_for_path(path).get_uri(), None)

    def list_projects(self):
        for r in self.recent_rows:
            self.recent.remove(r)
        self.recent_rows = []
        base = self.base
        entries = []
        if os.path.isdir(base):
            entries = sorted((e for e in os.scandir(base) if e.is_dir() and not e.name.startswith(".")),
                             key=lambda e: e.stat().st_mtime, reverse=True)[:12]
        for e in entries:
            row = Adw.ActionRow(title=e.name, subtitle=e.path.replace(os.path.expanduser("~"), "~", 1))
            row.add_suffix(button(_("Öffnen"), "flat", lambda p=e.path: self.open_project(p)))
            row.add_suffix(button(_("Terminal"), "flat",
                                  lambda p=e.path: open_terminal("bash", "-c", f"cd {GLib.shell_quote(p)} && exec bash")))
            self.recent.add(row)
            self.recent_rows.append(row)
        if not entries:
            row = Adw.ActionRow(title=_("Noch keine Projekte"))
            self.recent.add(row)
            self.recent_rows.append(row)


class DevWindow(Adw.ApplicationWindow):
    def __init__(self, app, page=None):
        super().__init__(application=app, title=_("Entwicklerzentrale"), default_width=980, default_height=780)
        self.toasts = Adw.ToastOverlay()
        stack = Adw.ViewStack()
        for name, widget in (("setup", SetupPage(self)), ("services", ServicesPage(self)),
                             ("projects", ProjectsPage(self))):
            stack.add_titled_with_icon(widget, name, widget.get_title(), widget.get_icon_name())
        view = Adw.ToolbarView(content=stack)
        view.add_top_bar(Adw.HeaderBar(title_widget=Adw.ViewSwitcher(stack=stack,
                                                                     policy=Adw.ViewSwitcherPolicy.WIDE)))
        self.toasts.set_child(view)
        self.set_content(self.toasts)
        if page:
            stack.set_visible_child_name(page)

    def toast(self, text):
        self.toasts.add_toast(Adw.Toast(title=text, timeout=4))


class DevApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.frametide.Dev", flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
        ft.load_css()
        (self.props.active_window or DevWindow(self, args[0] if args else None)).present()
        return 0


if __name__ == "__main__":
    sys.exit(DevApp().run(sys.argv))
