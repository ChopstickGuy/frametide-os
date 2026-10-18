#!/usr/bin/python3
"""Frametide – mit dem Internet verbinden (vor der Installation im Live-System).

Zeigt die WLAN-Netze und verbindet per NetworkManager. Der Installer (Calamares,
Modul networkcfg) übernimmt die Verbindung ins installierte System – dort lädt
Frametide beim ersten Start sofort Grafiktreiber und Updates.

  frametide-network-setup            Fenster anzeigen, Rückgabe 0 beim Schließen
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frametide_common as ft  # noqa: E402
from frametide_common import Adw, Gio, GLib, Gtk, WaveHero, _  # noqa: E402

CSS = """
.ns-title { color: #F3F6FD; font-size: 1.7em; font-weight: 800; letter-spacing: -0.02em; }
.ns-sub { color: alpha(#C9D1E3, .88); }
.ns-kicker { color: #22D3EE; font-size: 0.78em; font-weight: 700; letter-spacing: 0.14em; }
.ns-footer { padding: 14px 24px 22px 24px; }
.ns-ok { color: @success_color; font-weight: 700; }
"""


def nmcli(*args, timeout=30):
    return ft.run(["nmcli", *args], timeout=timeout)


def split_terse(line):
    """nmcli -t trennt mit ':' und maskiert ':' im Inhalt als '\\:'."""
    fields, cur, esc = [], "", False
    for ch in line:
        if esc:
            cur, esc = cur + ch, False
        elif ch == "\\":
            esc = True
        elif ch == ":":
            fields.append(cur)
            cur = ""
        else:
            cur += ch
    fields.append(cur)
    return fields


def scan(rescan=False):
    """Liste der WLAN-Netze (stärkstes zuerst, je SSID nur einmal) + Verbindungsstatus."""
    out = nmcli("-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list",
                "--rescan", "yes" if rescan else "auto")
    nets = {}
    for line in out.splitlines():
        parts = split_terse(line)
        if len(parts) < 4 or not parts[1]:
            continue
        in_use, ssid, signal, security = parts[0] == "*", parts[1], int(parts[2] or 0), parts[3]
        if ssid not in nets or signal > nets[ssid]["signal"] or in_use:
            nets[ssid] = {"ssid": ssid, "signal": signal, "secure": bool(security and security != "--"),
                          "active": in_use or nets.get(ssid, {}).get("active", False)}
    state = nmcli("-t", "networking", "connectivity", "check").strip()
    wired = any(split_terse(l)[:2] == ["ethernet", "connected"]
                for l in nmcli("-t", "-f", "TYPE,STATE", "device").splitlines())
    return sorted(nets.values(), key=lambda n: (not n["active"], -n["signal"])), state, wired


def signal_icon(signal):
    level = "excellent" if signal >= 75 else "good" if signal >= 50 else "ok" if signal >= 25 else "weak"
    return f"network-wireless-signal-{level}-symbolic"


def connect(ssid, password):
    argv = ["nmcli", "-w", "45", "device", "wifi", "connect", ssid] + (["password", password] if password else [])
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=60,
                              env=dict(os.environ, LC_ALL="C"))
        ok = proc.returncode == 0
        # Live-System: falls Polkit das Anlegen systemweiter Verbindungen verweigert, per sudo
        if not ok and ("authoriz" in proc.stderr.lower() or "privilege" in proc.stderr.lower()):
            ok = subprocess.run(["sudo", "-n", *argv], capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.SubprocessError):
        ok = False
    if not ok:
        # fehlgeschlagenes Profil nicht liegen lassen (sonst entstehen „SSID 1“, „SSID 2“ …)
        nmcli("connection", "delete", "id", ssid)
    return ok


class NetworkWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=_("Mit dem Internet verbinden"), default_width=540,
                         default_height=740)
        self.busy = False

        hero = Gtk.Overlay()
        hero.set_child(WaveHero(height=200))
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_start=28, margin_end=28,
                       margin_top=30, valign=Gtk.Align.START)
        text.append(Gtk.Label(label=_("Vor der Installation").upper(), xalign=0, css_classes=["ns-kicker"]))
        text.append(Gtk.Label(label=_("Mit dem Internet verbinden"), xalign=0, css_classes=["ns-title"]))
        text.append(Gtk.Label(label=_("Empfohlen: Frametide lädt dann beim ersten Start sofort Grafiktreiber "
                                      "und Updates. Die Verbindung wird ins installierte System übernommen."),
                              xalign=0, wrap=True, css_classes=["ns-sub"]))
        hero.add_overlay(text)

        self.status = Adw.ActionRow(title=_("Suche nach Netzwerken …"))
        self.status_icon = Gtk.Image(icon_name="network-wireless-acquiring-symbolic")
        self.status.add_prefix(self.status_icon)
        refresh = Gtk.Button(icon_name="view-refresh-symbolic", css_classes=["flat"], valign=Gtk.Align.CENTER,
                             tooltip_text=_("Erneut suchen"))
        refresh.connect("clicked", lambda _b: self.refresh(rescan=True))
        self.status.add_suffix(refresh)
        top = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        top.append(self.status)

        self.list = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        more = Adw.ActionRow(title=_("Verstecktes Netzwerk oder Firmen-WLAN …"), activatable=True)
        more.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        more.connect("activated", lambda _r: Gio.Subprocess.new(["gnome-control-center", "wifi"],
                                                                Gio.SubprocessFlags.NONE))
        extra = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        extra.append(more)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14, margin_top=18, margin_bottom=8,
                          margin_start=24, margin_end=24)
        content.append(top)
        content.append(self.list)
        content.append(extra)

        footer = Gtk.Box(spacing=12, css_classes=["ns-footer"])
        skip = Gtk.Button(label=_("Ohne Internet fortfahren"), css_classes=["flat"], hexpand=True,
                          halign=Gtk.Align.START)
        skip.connect("clicked", lambda _b: self.close())
        self.next = Gtk.Button(label=_("Weiter zur Installation"), css_classes=["suggested-action", "pill"])
        self.next.connect("clicked", lambda _b: self.close())
        footer.append(skip)
        footer.append(self.next)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        body.append(hero)
        body.append(Gtk.ScrolledWindow(child=content, vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER))
        body.append(footer)
        self.toasts = Adw.ToastOverlay(child=body)
        self.set_content(self.toasts)
        self.set_default_widget(self.next)

        self.refresh(rescan=True)
        GLib.timeout_add_seconds(8, self.refresh)

    # ------------------------------------------------------------ Anzeige
    def refresh(self, rescan=False):
        if not self.busy:
            ft.in_thread(lambda: scan(rescan), self.show)
        return True

    def show(self, result):
        if isinstance(result, Exception):
            return False
        nets, state, wired = result
        online = state == "full"
        active = next((n for n in nets if n["active"]), None)
        if online and wired and not active:
            self.status.set_title(_("Verbunden über Kabel"))
            self.status.set_subtitle(_("Alles bereit – du kannst weitermachen."))
        elif online and active:
            self.status.set_title(_("Verbunden mit {ssid}").format(ssid=active["ssid"]))
            self.status.set_subtitle(_("Alles bereit – du kannst weitermachen."))
        elif active:
            self.status.set_title(_("Verbunden mit {ssid}").format(ssid=active["ssid"]))
            self.status.set_subtitle(_("Noch kein Internet – evtl. Anmeldeseite im Browser nötig."))
        else:
            self.status.set_title(_("Nicht verbunden"))
            self.status.set_subtitle(_("Wähle dein WLAN aus der Liste.") if nets else
                                     _("Keine WLAN-Netze gefunden. Kabel anschließen oder erneut suchen."))
        self.status_icon.set_from_icon_name("network-wireless-connected-symbolic" if online else
                                            "network-wireless-offline-symbolic")
        self.next.set_label(_("Weiter zur Installation"))

        self.list.remove_all()
        for net in nets[:12]:
            row = Adw.ActionRow(title=net["ssid"], activatable=not net["active"])
            row.add_prefix(Gtk.Image(icon_name=signal_icon(net["signal"])))
            if net["active"]:
                row.add_suffix(Gtk.Label(label=_("Verbunden"), css_classes=["ns-ok"]))
            elif net["secure"]:
                row.add_suffix(Gtk.Image(icon_name="channel-secure-symbolic", css_classes=["dim-label"]))
            row.connect("activated", lambda _r, n=net: self.choose(n))
            self.list.append(row)
        self.list.set_visible(bool(nets))
        return False

    # ----------------------------------------------------------- Verbinden
    def choose(self, net):
        if not net["secure"]:
            self.do_connect(net["ssid"], "")
            return
        dialog = Adw.AlertDialog(heading=net["ssid"], body=_("WLAN-Passwort eingeben"))
        entry = Adw.PasswordEntryRow(title=_("Passwort"))
        box = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        box.append(entry)
        dialog.set_extra_child(box)
        dialog.add_response("cancel", _("Abbrechen"))
        dialog.add_response("connect", _("Verbinden"))
        dialog.set_response_appearance("connect", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("connect")
        entry.connect("entry-activated", lambda _e: dialog.response("connect"))
        dialog.connect("response", lambda _d, r: r == "connect" and self.do_connect(net["ssid"], entry.get_text()))
        dialog.present(self)
        entry.grab_focus()

    def do_connect(self, ssid, password):
        self.busy = True
        self.status.set_title(_("Verbinde mit {ssid} …").format(ssid=ssid))
        self.status.set_subtitle("")
        self.status_icon.set_from_icon_name("network-wireless-acquiring-symbolic")
        ft.in_thread(lambda: connect(ssid, password), lambda ok: self.connected(ssid, ok))

    def connected(self, ssid, ok):
        self.busy = False
        if ok is True:
            self.toasts.add_toast(Adw.Toast(title=_("Verbunden mit {ssid}").format(ssid=ssid)))
        else:
            self.toasts.add_toast(Adw.Toast(title=_("Verbindung fehlgeschlagen – Passwort richtig?"), timeout=5))
        self.refresh()
        return False


class NetworkApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.frametide.NetworkSetup")

    def do_activate(self):
        ft.load_css()
        provider = Gtk.CssProvider()
        provider.load_from_string(CSS) if hasattr(provider, "load_from_string") else provider.load_from_data(CSS, -1)
        Gtk.StyleContext.add_provider_for_display(Gtk.Widget.get_display(Gtk.Label()), provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        (self.props.active_window or NetworkWindow(self)).present()


if __name__ == "__main__":
    NetworkApp().run(sys.argv)
    sys.exit(0)
