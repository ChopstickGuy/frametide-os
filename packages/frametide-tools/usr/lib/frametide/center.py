#!/usr/bin/python3
"""Frametide Center – Updates, Treiber, RGB & Lüfter und Systemoptionen an einem Ort."""
import glob
import importlib.machinery
import importlib.util
import json
import os
import platform
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frametide_common as ft  # noqa: E402
from frametide_common import Adw, Gio, GLib, Gtk, _  # noqa: E402

HWSETUP = os.environ.get("FRAMETIDE_HWSETUP", "/usr/sbin/frametide-hwsetup")
HW_CONF = "/etc/frametide/hwsetup.conf"


def load_hwsetup():
    loader = importlib.machinery.SourceFileLoader("frametide_hwsetup", HWSETUP)
    spec = importlib.util.spec_from_loader("frametide_hwsetup", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def hw_conf():
    conf = {}
    if os.path.exists(HW_CONF):
        for line in open(HW_CONF):
            m = re.match(r"\s*([A-Z0-9_]+)\s*=\s*(\S+)", line)
            if m:
                conf[m.group(1)] = m.group(2).strip("\"'").lower()
    return conf


def group(title, description=None):
    return Adw.PreferencesGroup(title=title, description=description)


def button(label, style="suggested-action", callback=None):
    b = Gtk.Button(label=label, valign=Gtk.Align.CENTER, css_classes=[style] if style else [])
    if callback:
        b.connect("clicked", lambda _b: callback())
    return b


class TaskPanel(Gtk.Box):
    """Fortschrittsanzeige + ausklappbares Protokoll für privilegierte Aufgaben."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8, visible=False)
        self.status = Gtk.Label(xalign=0, css_classes=["heading"], hexpand=True)
        self.bar = Gtk.ProgressBar()
        expander, self.append_log = ft.log_view()
        self.stop_btn = Gtk.Button(label=_("Stoppen"), css_classes=["destructive-action"], visible=False,
                                   valign=Gtk.Align.CENTER)
        self.stop_btn.connect("clicked", lambda _b: self.stop())
        head = Gtk.Box(spacing=12)
        head.append(self.status)
        head.append(self.stop_btn)
        self.append(head)
        self.append(self.bar)
        self.append(expander)
        self.running = False
        self.job = None

    def stop(self):
        proc = getattr(self.job, "proc", None)
        if self.running and proc is not None:
            self.stop_btn.set_sensitive(False)
            self.status.set_label(_("Wird gestoppt …"))
            proc.send_signal(15)

    def start(self, title, argv, on_done=None, cancellable=False):
        """cancellable: „Stoppen“-Knopf zeigen (nur für Aufgaben, die SIGTERM sauber behandeln)."""
        if self.running:
            return
        self.running = True
        self.set_visible(True)
        self.status.set_label(title)
        self.stop_btn.set_visible(cancellable)
        self.stop_btn.set_sensitive(True)
        state = {"pulse": True}
        pulse = GLib.timeout_add(120, lambda: (state["pulse"] and self.bar.pulse(), True)[1])

        def line(text):
            pct = ft.progress_of(text)
            if pct is not None and ":" in text[:10]:
                state["pulse"] = False
                self.bar.set_fraction(pct / 100)
                return
            self.append_log(text)
            if text.startswith("» "):
                self.status.set_label(text[2:])

        def done(status):
            GLib.source_remove(pulse)
            self.running = False
            self.stop_btn.set_visible(False)
            self.bar.set_fraction(1.0 if status == 0 else 0.0)
            if status == 0:
                self.status.set_label(_("Erledigt ✓"))
            elif status in (126, 127, 130, 143):
                self.status.set_label(_("Abgebrochen"))
            else:
                self.status.set_label(_("Fehlgeschlagen (Code {code}) – Details unten").format(code=status))
            if on_done:
                on_done(status)
        self.job = ft.Task(argv, on_line=line, on_done=done)


# ======================================================================= Updates

class UpdatesPage(Adw.PreferencesPage):
    def __init__(self):
        super().__init__(title=_("Updates"), icon_name="software-update-available-symbolic")
        self.summary = group(None)
        self.summary_row = Adw.ActionRow(title=_("Updates prüfen"), subtitle=_("Noch nicht gesucht"))
        self.summary_row.add_prefix(Gtk.Image(icon_name="software-update-available-symbolic", pixel_size=32))
        self.check_btn = button(_("Suchen"), "flat", self.check)
        self.upgrade_btn = button(_("Alles aktualisieren"), "suggested-action", self.upgrade)
        self.upgrade_btn.set_visible(False)
        self.summary_row.add_suffix(self.check_btn)
        self.summary_row.add_suffix(self.upgrade_btn)
        self.summary.add(self.summary_row)
        self.task = TaskPanel()
        self.summary.add(self.task)
        self.add(self.summary)

        self.details = group(_("Verfügbare Updates"))
        self.rows = {}
        for key, title, icon in (("apt", _("System und Programme"), "system-software-install-symbolic"),
                                 ("flatpak", _("Flatpak-Apps"), "application-x-addon-symbolic"),
                                 ("craft", _("ArtCraft-Apps"), "applications-graphics-symbolic")):
            row = Adw.ExpanderRow(title=title, subtitle="–")
            row.add_prefix(Gtk.Image(icon_name=icon))
            self.rows[key] = row
            self.details.add(row)
        self.details.set_visible(False)
        self.add(self.details)

        fw = group(_("Firmware"), _("BIOS-, SSD- und Geräte-Firmware über fwupd (Hersteller-Updates)."))
        row = Adw.ActionRow(title=_("Firmware aktualisieren"),
                            subtitle=_("Nur bei Netzstrom ausführen – der Rechner startet ggf. neu."))
        row.add_suffix(button(_("Prüfen und installieren"), "flat",
                              lambda: self.task.start(_("Firmware …"), ft.helper_argv("firmware-update"))))
        fw.add(row)
        self.add(fw)
        GLib.idle_add(self.check)

    def check(self):
        self.summary_row.set_subtitle(_("Suche läuft …"))
        self.check_btn.set_sensitive(False)
        ft.in_thread(lambda: {"apt": ft.apt_upgradable(refresh=True), "flatpak": ft.flatpak_upgradable(),
                              "craft": ft.craft_upgradable()}, self.show)

    def show(self, result):
        self.check_btn.set_sensitive(True)
        if isinstance(result, Exception):
            self.summary_row.set_subtitle(_("Suche fehlgeschlagen: {error}").format(error=result))
            return False
        total = sum(len(v) for v in result.values())
        for key, row in self.rows.items():
            items = result[key]
            for child in getattr(row, "_items", []):
                row.remove(child)
            row._items = []
            row.set_subtitle(_("{n} Updates").format(n=len(items)) if items else _("Aktuell"))
            for name, version in items[:200]:
                r = Adw.ActionRow(title=name, subtitle=version)
                row.add_row(r)
                row._items.append(r)
        self.details.set_visible(total > 0)
        self.upgrade_btn.set_visible(total > 0)
        if total == 0:
            self.summary_row.set_title(_("Alles aktuell"))
            self.summary_row.set_subtitle(_("Dein System ist auf dem neuesten Stand."))
        else:
            self.summary_row.set_title(_("{n} Updates verfügbar").format(n=total))
            self.summary_row.set_subtitle(_("Installiert im Hintergrund – du kannst weiterarbeiten oder spielen."))
        return False

    def upgrade(self):
        self.upgrade_btn.set_sensitive(False)
        self.task.start(_("Updates werden installiert …"), ft.helper_argv("upgrade"), self.upgraded)

    def upgraded(self, _status):
        self.upgrade_btn.set_sensitive(True)
        self.check()
        # Neue Frametide-Version? Dann kurz zeigen, was neu ist
        try:
            Gio.Subprocess.new(["frametide-whats-new", "--if-pending"], Gio.SubprocessFlags.NONE)
        except GLib.Error:
            pass


# ======================================================================= Treiber

MESA_SOURCE = "/etc/apt/sources.list.d/frametide-mesa-latest.sources"


class DriversPage(Adw.PreferencesPage):
    def __init__(self):
        super().__init__(title=_("Treiber"), icon_name="video-display-symbolic")
        self.task = TaskPanel()
        try:
            hw = load_hwsetup()
            self.gpus, self.cpu = hw.detect_gpus(), hw.detect_cpu()
        except Exception:
            self.gpus, self.cpu = [], None

        cards = group(_("Grafikkarten"),
                      _("Frametide richtet den passenden Treiber beim ersten Start automatisch ein."))
        for gpu in self.gpus:
            row = Adw.ActionRow(title=gpu.name or f"{gpu.vendor} {gpu.device_id}",
                                subtitle=self.driver_text(gpu))
            row.add_prefix(Gtk.Image(icon_name="video-display-symbolic", pixel_size=32))
            if gpu.boot_vga:
                row.add_suffix(Gtk.Label(label=_("Primär"), css_classes=["ft-badge", "caption"],
                                         valign=Gtk.Align.CENTER))
            cards.add(row)
        if not self.gpus:
            cards.add(Adw.ActionRow(title=_("Keine Grafikkarte erkannt")))
        auto = Adw.ActionRow(title=_("Treiber automatisch einrichten"),
                             subtitle=_("Erkennt die Hardware erneut und installiert die empfohlenen Treiber."))
        auto.add_suffix(button(_("Ausführen"), "flat",
                               lambda: self.task.start(_("Treiber werden eingerichtet …"),
                                                       ft.helper_argv("driver-auto"))))
        cards.add(auto)
        cards.add(self.task)
        self.add(cards)

        if any(g.vendor == "nvidia" for g in self.gpus):
            self.nvidia = group(_("NVIDIA-Treiberversion"),
                                _("„open“ = offene Kernel-Module (empfohlen ab RTX 20/GTX 16). "
                                  "Nach einem Wechsel bitte neu starten."))
            self.nvidia.add(Adw.ActionRow(title=_("Verfügbare Treiber werden ermittelt …")))
            self.add(self.nvidia)
            ft.in_thread(self.ubuntu_drivers, self.show_nvidia)

        mesa = ft.apt_version("mesa-vulkan-drivers")
        info = group(_("Grafik-Stack"))
        vulkan32 = _("installiert") if ft.apt_installed(["mesa-vulkan-drivers:i386"]) else _("fehlt")
        for title, value in (("Kernel", platform.release()), (_("Mesa (AMD/Intel)"), mesa or "–"),
                             (_("Vulkan 32-Bit (Steam)"), vulkan32)):
            info.add(Adw.ActionRow(title=title, subtitle=value, css_classes=["property"]))
        latest = Adw.SwitchRow(title=_("Neueste Mesa-Treiber"),
                               subtitle=_("Für AMD- und Intel-Grafik: aktuelle Mesa-Version statt der "
                                          "LTS-Version – oft mehr FPS in neuen Spielen. Quelle: Kisak-PPA. "
                                          "Ausschalten stellt Ubuntus Version wieder her."),
                               active=os.path.exists(MESA_SOURCE))
        latest.connect("notify::active", lambda r, _p: self.task.start(
            _("Mesa-Treiber werden umgestellt …"),
            ft.helper_argv("mesa-latest", "on" if r.get_active() else "off")))
        info.add(latest)
        self.add(info)

    @staticmethod
    def driver_text(gpu):
        if gpu.driver == "nvidia":
            version = ft.run(["cat", "/sys/module/nvidia/version"]).strip()
            return _("NVIDIA-Treiber {version}").format(version=version) if version else _("NVIDIA-Treiber")
        names = {"amdgpu": "AMDGPU (Mesa RADV)",
                 "radeon": _("radeon (alt – Vulkan erst nach Einrichtung)"),
                 "i915": "Intel i915 (Mesa)", "xe": "Intel Xe (Mesa)",
                 "nouveau": _("nouveau (offen, eingeschränkt)")}
        return names.get(gpu.driver, _("Treiber: {driver}").format(driver=gpu.driver or _("keiner")))

    @staticmethod
    def ubuntu_drivers():
        out = ft.run(["ubuntu-drivers", "devices"], timeout=120)
        drivers = []
        for line in out.splitlines():
            m = re.match(r"driver\s*:\s*(nvidia-driver-\S+)(.*)", line.strip())
            if m and "server" not in m.group(1):
                drivers.append((m.group(1), "recommended" in m.group(2)))
        installed = ft.apt_installed([d for d, _rec in drivers])
        return drivers, installed

    def show_nvidia(self, result):
        title, description = self.nvidia.get_title(), self.nvidia.get_description()
        self.remove(self.nvidia)
        self.nvidia = group(title, description)
        drivers, installed = ([], set()) if isinstance(result, Exception) else result
        first = None
        for name, recommended in sorted(drivers, reverse=True):
            row = Adw.ActionRow(title=name, subtitle=_("Empfohlen") if recommended else None)
            check = Gtk.CheckButton(active=name in installed, valign=Gtk.Align.CENTER)
            if first:
                check.set_group(first)
            first = first or check
            check.connect("toggled", lambda c, n=name: c.get_active() and n not in installed and
                          self.task.start(_("{pkg} wird installiert …").format(pkg=n),
                                          ft.helper_argv("driver-install", n)))
            row.add_prefix(check)
            row.set_activatable_widget(check)
            self.nvidia.add(row)
        if not drivers:
            self.nvidia.add(Adw.ActionRow(
                title=_("Keine Treiber gefunden"),
                subtitle=_("Sehr alte Karten laufen mit dem offenen nouveau/NVK-Treiber.")))
        self.add(self.nvidia)
        return False


# ======================================================================== Spiele

LEVEL_STYLE = {"good": "success", "ok": "warning", "bad": "error", "unknown": "dim-label"}


def verdict_badge(level, text):
    return Gtk.Label(label=text, valign=Gtk.Align.CENTER, css_classes=["ft-badge", "caption", LEVEL_STYLE[level]])


class GamesPage(Adw.PreferencesPage):
    """Zeigt pro Spiel, wie gut es unter Linux läuft und ob ein Anti-Cheat blockiert."""

    def __init__(self):
        super().__init__(title=_("Spiele"), icon_name="input-gaming-symbolic")
        import games
        self.games = games

        check = group(_("Spiel prüfen"),
                      _("Läuft mein Spiel unter Linux? Daten von ProtonDB und AreWeAntiCheatYet."))
        self.entry = Adw.EntryRow(title=_("Spielname, z. B. Elden Ring"), show_apply_button=True)
        self.entry.connect("apply", self.on_search)
        self.entry.connect("entry-activated", self.on_search)
        check.add(self.entry)
        self.add(check)
        self.results = group(_("Ergebnis"))
        self.results.set_visible(False)
        self.add(self.results)

        self.library = group(_("Deine installierten Steam-Spiele"))
        self.summary = Adw.ActionRow(title=_("Bibliothek wird gelesen …"))
        self.library.add(self.summary)
        self.add(self.library)
        self.library_rows = []
        ft.in_thread(self.load_library, self.show_library)

    # -------------------------------------------------------- Bibliothek
    def load_library(self):
        installed = self.games.installed_games()
        anticheats = self.games.anticheat_db()
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(6) as pool:
            verdicts = list(pool.map(lambda g: self.games.verdict(g[0], anticheats), installed))
        return list(zip(installed, verdicts))

    def show_library(self, result):
        if isinstance(result, Exception) or not result:
            self.summary.set_title(_("Keine installierten Steam-Spiele gefunden"))
            self.summary.set_subtitle(_("Installiere Spiele in Steam oder prüfe oben ein Spiel nach Namen."))
            return False
        counts = {"good": 0, "ok": 0, "bad": 0, "unknown": 0}
        for (appid, name), (level, text, details) in result:
            counts[level] += 1
            row = Adw.ActionRow(title=name, subtitle=details)
            row.add_suffix(verdict_badge(level, text))
            self.library.add(row)
        self.summary.set_title(_("{n} Spiele geprüft").format(n=len(result)))
        self.summary.set_subtitle(_("{good} laufen gut · {ok} mit Einschränkungen · {bad} blockiert/defekt · "
                                    "{unknown} unbekannt").format(**counts))
        return False

    # ------------------------------------------------------------- Suche
    def on_search(self, _entry):
        term = self.entry.get_text().strip()
        if len(term) < 2:
            return
        self.results.set_visible(True)
        self.results.set_title(_("Ergebnis für „{term}“").format(term=term))
        for row in getattr(self, "_result_rows", []):
            self.results.remove(row)
        self._result_rows = [Adw.ActionRow(title=_("Suche läuft …"))]
        self.results.add(self._result_rows[0])

        def lookup():
            anticheats = self.games.anticheat_db()
            found = [(name, self.games.verdict(appid, anticheats)) for appid, name in self.games.search_steam(term)]
            steam_names = {n.lower() for n, _v in found}
            found += [(g["name"], self.games.anticheat_verdict(g))
                      for g in self.games.anticheat_by_name(term) if g["name"].lower() not in steam_names]
            return found
        ft.in_thread(lookup, self.show_results)

    def show_results(self, result):
        for row in self._result_rows:
            self.results.remove(row)
        self._result_rows = []
        if isinstance(result, Exception):
            result = []
            rows = [Adw.ActionRow(title=_("Keine Verbindung"), subtitle=_("Für den Spiele-Check wird Internet benötigt."))]
        else:
            rows = []
        for name, (level, text, details) in result:
            row = Adw.ActionRow(title=name, subtitle=details)
            row.add_suffix(verdict_badge(level, text))
            rows.append(row)
        if not rows:
            rows = [Adw.ActionRow(title=_("Nichts gefunden"))]
        for row in rows:
            self.results.add(row)
            self._result_rows.append(row)
        return False


# ========================================================================= Audio

class AudioPage(Adw.PreferencesPage):
    """Ausgabe, Mikrofon, Rauschunterdrückung und Mikrofontest an einem Ort."""

    def __init__(self, window):
        super().__init__(title=_("Audio"), icon_name="audio-volume-high-symbolic")
        import audio
        self.audio, self.window = audio, window
        self.signature = None

        self.out_group = group(_("Ausgabe"), _("Wohin der Ton geht – Kopfhörer, Headset oder Lautsprecher."))
        self.in_group = group(_("Mikrofon"))
        self.add(self.out_group)
        self.add(self.in_group)
        self.dynamic_rows = []

        ns = group(_("Rauschunterdrückung"),
                   _("Entfernt Tastatur, Lüfter und Hintergrundgeräusche aus deinem Mikrofon – "
                     "für Discord, Teams und Spiele-Chat. Läuft direkt im Audiosystem, ohne Zusatzprogramm."))
        self.ns_switch = Adw.SwitchRow(title=_("Hintergrundgeräusche entfernen"),
                                       subtitle=_("Beim Umschalten ist der Ton kurz weg."),
                                       active=audio.noise_suppression_enabled())
        self.agc_switch = Adw.SwitchRow(title=_("Automatische Mikrofon-Lautstärke"),
                                        subtitle=_("Gleicht leises und lautes Sprechen aus."),
                                        active=audio.auto_gain_enabled(),
                                        sensitive=audio.noise_suppression_enabled())
        self.ns_switch.connect("notify::active", self.on_noise)
        self.agc_switch.connect("notify::active", self.on_noise)
        ns.add(self.ns_switch)
        ns.add(self.agc_switch)
        self.add(ns)

        test = group(_("Mikrofon testen"))
        self.test_row = Adw.ActionRow(title=_("Aufnehmen und anhören"),
                                      subtitle=_("Nimmt 4 Sekunden auf und spielt sie dir vor."))
        self.test_btn = button(_("Test starten"), "suggested-action", self.mic_test)
        self.test_row.add_suffix(self.test_btn)
        test.add(self.test_row)
        self.add(test)

        self.refresh()
        GLib.timeout_add_seconds(3, self.refresh)

    # ------------------------------------------------------------- Geräte
    def refresh(self):
        ft.in_thread(self.audio.devices, self.show)
        return True

    def show(self, devs):
        if isinstance(devs, Exception):
            return False
        sig = json.dumps(devs, sort_keys=True)
        if sig == self.signature:
            return False  # nichts geändert → Regler nicht unter den Fingern neu aufbauen
        self.signature = sig
        for grp, row in self.dynamic_rows:
            grp.remove(row)
        self.dynamic_rows = []
        for grp, items, empty in ((self.out_group, devs["sinks"], _("Kein Ausgabegerät gefunden")),
                                  (self.in_group, devs["sources"], _("Kein Mikrofon gefunden"))):
            first = None
            default = None
            for dev in items:
                icon = ("bluetooth-active-symbolic" if dev["bluetooth"] else
                        "audio-headset-symbolic" if dev["usb"] else
                        "audio-speakers-symbolic" if grp is self.out_group else "audio-input-microphone-symbolic")
                row = Adw.ActionRow(title=dev["description"])
                row.add_prefix(Gtk.Image(icon_name=icon))
                check = Gtk.CheckButton(active=dev["default"], valign=Gtk.Align.CENTER)
                if first:
                    check.set_group(first)
                first = first or check
                check.connect("toggled", lambda c, d=dev: c.get_active() and not d["default"]
                              and (self.audio.set_default(d["id"]), self.refresh()))
                row.add_suffix(check)
                row.set_activatable_widget(check)
                grp.add(row)
                self.dynamic_rows.append((grp, row))
                if dev["default"]:
                    default = dev
            if not items:
                row = Adw.ActionRow(title=empty)
                grp.add(row)
                self.dynamic_rows.append((grp, row))
            if default:
                row = self.volume_row(default)
                grp.add(row)
                self.dynamic_rows.append((grp, row))
        return False

    def volume_row(self, dev):
        vol, muted = self.audio.volume(dev["id"])
        row = Adw.ActionRow(title=_("Lautstärke"))
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        scale.set_value(round(vol * 100))
        scale.set_hexpand(True)
        scale.set_size_request(260, -1)
        scale.set_draw_value(False)
        scale.connect("value-changed", lambda s: self.audio.set_volume(dev["id"], s.get_value() / 100))
        mute = Gtk.ToggleButton(icon_name="audio-volume-muted-symbolic", active=muted, valign=Gtk.Align.CENTER,
                                tooltip_text=_("Stumm"), css_classes=["flat"])
        mute.connect("toggled", lambda b: self.audio.set_mute(dev["id"], b.get_active()))
        row.add_suffix(scale)
        row.add_suffix(mute)
        return row

    # ------------------------------------------------- Rauschunterdrückung
    def on_noise(self, _switch, _param):
        enabled, gain = self.ns_switch.get_active(), self.agc_switch.get_active()
        self.agc_switch.set_sensitive(enabled)
        self.ns_switch.set_sensitive(False)
        ft.in_thread(lambda: self.audio.set_noise_suppression(enabled, gain), self.noise_done)

    def noise_done(self, ok):
        self.ns_switch.set_sensitive(True)
        self.signature = None
        self.refresh()
        if ok is True and self.ns_switch.get_active():
            self.window.toast(_("Rauschunterdrückung aktiv – „Mikrofon mit Rauschunterdrückung“ ist jetzt Standard."))
        elif isinstance(ok, Exception) or ok is False:
            self.window.toast(_("Rauschunterdrückung konnte nicht gestartet werden."))
        return False

    # ------------------------------------------------------------ Mikrofontest
    def mic_test(self):
        self.test_btn.set_sensitive(False)
        self.test_row.set_subtitle(_("Sprich jetzt … (4 Sekunden)"))
        proc = Gio.Subprocess.new(self.audio.record_argv(), Gio.SubprocessFlags.NONE)

        def stop():
            proc.send_signal(2)  # SIGINT → Datei wird sauber abgeschlossen
            GLib.timeout_add(400, play)
            return False

        def play():
            self.test_row.set_subtitle(_("Wiedergabe …"))
            player = Gio.Subprocess.new(self.audio.play_argv(), Gio.SubprocessFlags.NONE)
            player.wait_async(None, lambda *_a: (self.test_btn.set_sensitive(True),
                                                 self.test_row.set_subtitle(_("Nimmt 4 Sekunden auf und spielt sie dir vor."))))
            return False
        GLib.timeout_add(4000, stop)


# ================================================================= RGB & Lüfter

class HardwarePage(Adw.PreferencesPage):
    def __init__(self, window):
        super().__init__(title=_("RGB & Lüfter"), icon_name="weather-clear-symbolic")
        self.window = window
        self.task = TaskPanel()

        # --- Live-Sensoren
        self.temps = group(_("Temperaturen"))
        self.fans = group(_("Lüfter und Pumpen"),
                          _("Kurven, Profile und AIO-Kühler stellst du in CoolerControl ein."))
        self.cc_row = Adw.ActionRow(title="CoolerControl",
                                    subtitle=_("Lüfterkurven, Pumpen, AIO-Wasserkühlungen"))
        self.cc_row.add_prefix(Gtk.Image(icon_name="weather-windy-symbolic"))
        self.cc_row.add_suffix(button(_("Öffnen"), "flat", lambda: self.launch(
            "org.coolercontrol.CoolerControl.desktop", "coolercontrol")))
        self.add(self.temps)
        self.add(self.fans)
        self.sensor_rows = {}

        # --- RGB
        rgb = group(_("RGB-Beleuchtung"),
                    _("Mainboard, RAM, Grafikkarte, Lüfter, Tastatur und Maus – "
                      "herstellerübergreifend über OpenRGB."))
        from gi.repository import Gdk
        self.color = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog(with_alpha=False), valign=Gtk.Align.CENTER)
        rgba = Gdk.RGBA()
        rgba.parse("#22D3EE")
        self.color.set_rgba(rgba)
        row = Adw.ActionRow(title=_("Farbe für alle Geräte"),
                            subtitle=_("Statische Farbe auf alle erkannten Geräte"))
        row.add_prefix(Gtk.Image(icon_name="color-select-symbolic"))
        row.add_suffix(self.color)
        row.add_suffix(button(_("Anwenden"), "suggested-action", self.apply_color))
        rgb.add(row)
        off = Adw.ActionRow(title=_("Beleuchtung ausschalten"))
        off.add_suffix(button(_("Aus"), "flat", lambda: self.openrgb(
            ["--mode", "static", "--color", "000000"], _("Beleuchtung aus"))))
        rgb.add(off)
        self.devices = Adw.ExpanderRow(title=_("Erkannte Geräte"), subtitle=_("Noch nicht gesucht"))
        self.devices.add_suffix(button(_("Suchen"), "flat", self.scan_rgb))
        rgb.add(self.devices)
        orgb = Adw.ActionRow(title="OpenRGB", subtitle=_("Effekte, Zonen, Profile und Geräte im Detail"))
        orgb.add_suffix(button(_("Öffnen"), "flat", lambda: self.launch("org.openrgb.OpenRGB.desktop", "openrgb")))
        rgb.add(orgb)
        self.add(rgb)

        # --- Erweitert
        adv = group(_("Erweitert"), _("Nur nötig, wenn Geräte oder Lüfter oben fehlen."))
        smbus = Adw.SwitchRow(title=_("Erweiterter SMBus-Zugriff"),
                              subtitle=_("Für RGB auf manchen Mainboards und RAM-Riegeln "
                                         "(acpi_enforce_resources=lax). Neustart nötig."))
        smbus.set_active(hw_conf().get("SMBUS_LAX") == "yes")
        smbus.connect("notify::active", lambda s, _p: self.task.start(
            _("Einstellung wird angewendet …"),
            ft.helper_argv("set-option", "SMBUS_LAX", "yes" if s.get_active() else "no")))
        adv.add(smbus)
        mok = _("bei Secure Boot einmalig MOK-Bestätigung")
        for pkg, title, sub in (("it87-dkms", _("Lüftertreiber für ITE-Chips"),
                                 _("Gigabyte und viele andere Mainboards")),
                                ("nct6687d-dkms", _("Lüftertreiber für Nuvoton NCT6687"),
                                 _("Viele MSI-Mainboards"))):
            r = Adw.ActionRow(title=title, subtitle=f"{sub} · {mok}")
            r.add_suffix(button(_("Installieren"), "flat", lambda p=pkg: self.task.start(
                _("{pkg} wird installiert …").format(pkg=p), ft.helper_argv("fan-driver", p))))
            adv.add(r)
        detect = Adw.ActionRow(title=_("Sensoren neu erkennen"), subtitle="lm-sensors sensors-detect")
        detect.add_suffix(button(_("Ausführen"), "flat", lambda: self.task.start(
            _("Sensoren werden erkannt …"), ft.helper_argv("sensors-detect"))))
        adv.add(detect)
        adv.add(self.task)
        self.add(adv)

        self.update_sensors()
        self.timer = GLib.timeout_add_seconds(2, self.update_sensors)

    # --------------------------------------------------------------- Sensoren
    @staticmethod
    def read_sensors():
        temps, fans = [], []
        try:
            data = json.loads(ft.run(["sensors", "-j"]) or "{}")
        except json.JSONDecodeError:
            data = {}
        for chip, features in data.items():
            if not isinstance(features, dict):
                continue
            short = chip.split("-")[0]
            for label, values in features.items():
                if not isinstance(values, dict):
                    continue
                for key, value in values.items():
                    if key.endswith("_input") and key.startswith("temp") and 0 < value < 150:
                        temps.append((f"{short} · {label}", f"{value:.0f} °C", value))
                    elif key.endswith("_input") and key.startswith("fan"):
                        fans.append((f"{short} · {label}", _("{rpm} U/min").format(rpm=f"{value:.0f}"), value))
        nv = ft.run(["nvidia-smi", "--query-gpu=name,temperature.gpu,fan.speed",
                     "--format=csv,noheader,nounits"], timeout=5)
        for line in nv.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 3 and parts[1].isdigit():
                temps.append((f"{parts[0]} · GPU", f"{parts[1]} °C", float(parts[1])))
                if parts[2].isdigit():
                    fans.append((f"{parts[0]} · {_('Lüfter')}", f"{parts[2]} %", float(parts[2])))
        return temps, fans

    def update_sensors(self):
        ft.in_thread(self.read_sensors, self.show_sensors)
        return True

    def show_sensors(self, result):
        if isinstance(result, Exception):
            return False
        temps, fans = result
        for grp, items, empty in ((self.temps, temps, _("Keine Temperatursensoren gefunden")),
                                  (self.fans, fans, _("Keine Lüftersensoren gefunden – siehe „Erweitert“"))):
            for title, value, raw in items or [(empty, "", None)]:
                key = (id(grp), title)
                row = self.sensor_rows.get(key)
                if row is None:
                    row = Adw.ActionRow(title=title)
                    row.value = Gtk.Label(css_classes=["numeric", "heading"])
                    row.add_suffix(row.value)
                    grp.add(row)
                    self.sensor_rows[key] = row
                row.value.set_label(value)
                hot = raw is not None and grp is self.temps and raw >= 85
                row.value.set_css_classes(["numeric", "heading", "error" if hot else "accent"])
        if self.cc_row.get_parent() is None:
            self.fans.add(self.cc_row)
        return False

    # -------------------------------------------------------------------- RGB
    def openrgb(self, args, done_text):
        lines = []
        ft.Task(["openrgb", "--noautoconnect", *args], on_line=lines.append,
                on_done=lambda s: self.window.toast(done_text if s == 0 else
                                                    f"OpenRGB: {lines[-1] if lines else s}"))

    def apply_color(self):
        c = self.color.get_rgba()
        hexcolor = "".join(f"{round(v * 255):02X}" for v in (c.red, c.green, c.blue))
        self.openrgb(["--mode", "static", "--color", hexcolor],
                     _("Farbe #{color} angewendet").format(color=hexcolor))

    def scan_rgb(self):
        self.devices.set_subtitle(_("Suche läuft … (kann einige Sekunden dauern)"))
        lines = []

        def done(_status):
            for child in getattr(self.devices, "_items", []):
                self.devices.remove(child)
            self.devices._items = []
            found = [m.group(1) for m in (re.match(r"^\d+:\s+(.+)$", l.strip()) for l in lines) if m]
            for name in found:
                r = Adw.ActionRow(title=name)
                self.devices.add_row(r)
                self.devices._items.append(r)
            self.devices.set_subtitle(
                _("{n} Geräte").format(n=len(found)) if found else
                _("Keine Geräte gefunden – evtl. „Erweiterter SMBus-Zugriff“ aktivieren"))
            self.devices.set_expanded(bool(found))
        ft.Task(["openrgb", "--noautoconnect", "--list-devices"], on_line=lines.append, on_done=done)

    def launch(self, desktop_id, fallback):
        info = Gio.DesktopAppInfo.new(desktop_id)
        try:
            info.launch([], None) if info else Gio.Subprocess.new([fallback], Gio.SubprocessFlags.NONE)
        except GLib.Error as e:
            self.window.toast(_("Konnte {app} nicht starten: {error}").format(app=fallback, error=e.message))


# ======================================================================== System

class SystemPage(Adw.PreferencesPage):
    def __init__(self):
        super().__init__(title=_("System"), icon_name="preferences-system-symbolic")
        self.task = TaskPanel()
        os_release = dict(re.findall(r'^(\w+)="?([^"\n]*)"?$', ft.run(["cat", "/etc/os-release"]), re.M))
        mem = int(re.search(r"MemTotal:\s+(\d+)", ft.run(["cat", "/proc/meminfo"]) or "MemTotal: 0").group(1))
        cpu = re.search(r"model name\s*:\s*(.+)", ft.run(["cat", "/proc/cpuinfo"]))
        info = group(_("Über dieses System"))
        for title, value in (("System", os_release.get("PRETTY_NAME", "Frametide OS")),
                             (_("Basis"), f"Ubuntu {os_release.get('UBUNTU_CODENAME', '')}".strip()),
                             ("Kernel", platform.release()),
                             (_("Prozessor"), cpu.group(1) if cpu else "–"),
                             (_("Arbeitsspeicher"), f"{mem / 1024 / 1024:.0f} GB")):
            info.add(Adw.ActionRow(title=title, subtitle=value, css_classes=["property"]))
        self.add(info)

        conf = hw_conf()
        perf = group(_("Leistung"))
        for key, title, subtitle in (
                ("AMD64V3", _("x86-64-v3-optimierte Pakete"),
                 _("Schnellere Pakete für CPUs ab Intel Haswell / AMD Zen (experimentell)")),
                ("AMD_OVERDRIVE", _("AMD-GPU-Übertaktung freischalten"),
                 _("Erlaubt Übertakten und Undervolting in CoreCtrl. Neustart nötig.")),
                ("MITIGATIONS_OFF", _("CPU-Sicherheitsbremsen abschalten"),
                 _("Mehr Leistung v. a. auf älteren CPUs, aber weniger Schutz vor Spectre & Co. "
                   "Nur für reine Gaming-PCs. Neustart nötig."))):
            row = Adw.SwitchRow(title=title, subtitle=subtitle, active=conf.get(key) == "yes")
            row.connect("notify::active", lambda r, _p, k=key: self.task.start(
                _("Einstellung wird angewendet …"),
                ft.helper_argv("set-option", k, "yes" if r.get_active() else "no")))
            perf.add(row)
        if glob.glob("/sys/class/power_supply/BAT*"):
            ac = Adw.SwitchRow(title=_("Am Netzteil volle Leistung"),
                               subtitle=_("Laptop: Energieprofil „Leistung“, solange das Netzteil steckt – "
                                          "Lüfter und Leistungsgrenzen erlauben höhere Takte. "
                                          "Im Akkubetrieb „Ausgewogen“."),
                               active=conf.get("AC_PERFORMANCE", "yes") != "no")
            ac.connect("notify::active", lambda r, _p: self.task.start(
                _("Einstellung wird angewendet …"),
                ft.helper_argv("set-option", "AC_PERFORMANCE", "yes" if r.get_active() else "no")))
            perf.add(ac)
        perf.add(self.task)
        self.add(perf)

        tools = group(_("Werkzeuge"))
        news = Adw.ActionRow(title=_("Was ist neu"), subtitle=_("Die Neuerungen des letzten Frametide-Updates"))
        news.add_suffix(button(_("Anzeigen"), "flat",
                               lambda: Gio.Subprocess.new(["frametide-whats-new"], Gio.SubprocessFlags.NONE)))
        tools.add(news)
        bench = Adw.ActionRow(title="Frametide Bench",
                              subtitle=_("Misst CPU, Speicher, Latenz, SSD und GPU (ca. 4 Minuten). "
                                         "Ergebnis: ~/.local/share/frametide-bench"))
        bench.add_suffix(button(_("Starten"), "flat", lambda: self.task.start(
            _("Benchmark läuft – bitte nichts anderes starten …"), ["frametide-bench"], cancellable=True)))
        tools.add(bench)
        move = Adw.ActionRow(title=_("Windows-Umzug"),
                             subtitle=_("Dateien, Lesezeichen, WLAN und Steam-Spiele von Windows übernehmen"))
        move.add_suffix(button(_("Öffnen"), "flat",
                               lambda: Gio.Subprocess.new(["frametide-migrate"], Gio.SubprocessFlags.NONE)))
        tools.add(move)
        self.add(tools)


class CenterWindow(Adw.ApplicationWindow):
    def __init__(self, application, page=None):
        super().__init__(application=application, title="Frametide Center",
                         default_width=1120, default_height=800)
        self.toasts = Adw.ToastOverlay()
        stack = Adw.ViewStack()
        for name, widget in (("updates", UpdatesPage()), ("drivers", DriversPage()), ("games", GamesPage()),
                             ("audio", AudioPage(self)), ("hardware", HardwarePage(self)), ("system", SystemPage())):
            stack.add_titled_with_icon(widget, name, widget.get_title(), widget.get_icon_name())
        header = Adw.HeaderBar(title_widget=Adw.ViewSwitcher(stack=stack, policy=Adw.ViewSwitcherPolicy.WIDE))
        view = Adw.ToolbarView(content=stack)
        view.add_top_bar(header)
        self.toasts.set_child(view)
        self.set_content(self.toasts)
        if page:
            stack.set_visible_child_name(page)

    def toast(self, text):
        self.toasts.add_toast(Adw.Toast(title=text, timeout=4))


class CenterApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.frametide.Center",
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

    def do_command_line(self, command_line):
        args = command_line.get_arguments()[1:]
        page = args[0].lstrip("-") if args else None
        ft.load_css()
        win = self.props.active_window or CenterWindow(self, page)
        win.present()
        return 0


if __name__ == "__main__":
    sys.exit(CenterApp().run(sys.argv))
