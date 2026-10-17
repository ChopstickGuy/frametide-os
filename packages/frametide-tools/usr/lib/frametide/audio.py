"""Audio-Logik für die Steuerung: Geräte, Lautstärke, Mikrofontest und
Rauschunterdrückung über PipeWires eingebaute WebRTC-Verarbeitung (echo-cancel)."""
import json
import os
import re
import subprocess

from frametide_i18n import _

CONF_DIR = os.path.join(os.path.expanduser("~"), ".config", "pipewire", "pipewire.conf.d")
NOISE_CONF = os.path.join(CONF_DIR, "90-frametide-noise-suppression.conf")
CLEAN_SOURCE = "frametide_clean_mic"


def run(argv, timeout=10):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout
    except (OSError, subprocess.SubprocessError):
        return 127, ""


def devices():
    """{'sinks': [...], 'sources': [...]} mit id, name, description, default."""
    code, out = run(["pw-dump"])
    if code != 0:
        return {"sinks": [], "sources": []}
    data = json.loads(out or "[]")
    defaults = {}
    for obj in data:
        if obj.get("type") == "PipeWire:Interface:Metadata" and obj.get("props", {}).get("metadata.name") == "default":
            for entry in obj.get("metadata", []):
                if entry.get("key") in ("default.audio.sink", "default.audio.source"):
                    value = entry.get("value")
                    if isinstance(value, str):
                        try:
                            value = json.loads(value)
                        except ValueError:
                            value = {}
                    defaults[entry["key"]] = (value or {}).get("name")
    result = {"sinks": [], "sources": []}
    for obj in data:
        props = obj.get("info", {}).get("props", {})
        cls = props.get("media.class")
        if cls not in ("Audio/Sink", "Audio/Source"):
            continue
        name = props.get("node.name", "")
        if name.startswith("frametide_") and name != CLEAN_SOURCE:
            continue  # interne Knoten der Rauschunterdrückung ausblenden
        kind = "sinks" if cls == "Audio/Sink" else "sources"
        key = "default.audio.sink" if kind == "sinks" else "default.audio.source"
        result[kind].append({
            "id": obj["id"], "name": name,
            "description": props.get("node.description") or props.get("node.nick") or name,
            "default": defaults.get(key) == name,
            "bluetooth": "bluez" in name,
            "usb": "usb" in name.lower(),
        })
    return result


def volume(node_id):
    """(Lautstärke 0–1.5, stumm?)"""
    code, out = run(["wpctl", "get-volume", str(node_id)])
    m = re.search(r"Volume:\s*([\d.]+)", out)
    return (float(m.group(1)) if m else 0.0), "MUTED" in out


def set_volume(node_id, value):
    run(["wpctl", "set-volume", str(node_id), f"{max(0.0, min(1.5, value)):.2f}"])


def set_mute(node_id, muted):
    run(["wpctl", "set-mute", str(node_id), "1" if muted else "0"])


def set_default(node_id):
    run(["wpctl", "set-default", str(node_id)])


# ------------------------------------------------------------ Rauschunterdrückung

def noise_suppression_enabled():
    return os.path.exists(NOISE_CONF)


def noise_suppression_config(auto_gain=False):
    """PipeWire-Konfiguration: virtuelles, gereinigtes Mikrofon über WebRTC
    (Rauschunterdrückung, Echo-Unterdrückung, Hochpass). monitor.mode nutzt die
    vorhandene Ausgabe als Echo-Referenz – es entsteht kein zusätzliches Ausgabegerät."""
    agc = "true" if auto_gain else "false"
    return f"""# Von Frametide (Steuerung → Audio) erzeugt
context.modules = [
    {{ name = libpipewire-module-echo-cancel
        args = {{
            library.name = aec/libspa-aec-webrtc
            monitor.mode = true
            aec.args = {{
                webrtc.noise_suppression = true
                webrtc.high_pass_filter = true
                webrtc.extended_filter = true
                webrtc.delay_agnostic = true
                webrtc.gain_control = {agc}
            }}
            capture.props = {{
                node.name = "frametide_capture"
                node.passive = true
            }}
            source.props = {{
                node.name = "{CLEAN_SOURCE}"
                node.description = "{_('Mikrofon mit Rauschunterdrückung')}"
                priority.session = 2000
            }}
        }}
    }}
]
"""


def restart_pipewire():
    run(["systemctl", "--user", "restart", "pipewire.service", "pipewire-pulse.service", "wireplumber.service"],
        timeout=20)


def set_noise_suppression(enabled, auto_gain=False):
    if enabled:
        os.makedirs(CONF_DIR, exist_ok=True)
        with open(NOISE_CONF, "w") as f:
            f.write(noise_suppression_config(auto_gain))
    elif os.path.exists(NOISE_CONF):
        os.remove(NOISE_CONF)
    restart_pipewire()
    if enabled:
        # das gereinigte Mikrofon als Standard setzen (kurz warten, bis es erscheint)
        import time
        for _attempt in range(20):
            clean = [s for s in devices()["sources"] if s["name"] == CLEAN_SOURCE]
            if clean:
                set_default(clean[0]["id"])
                return True
            time.sleep(0.25)
        return False
    return True


def auto_gain_enabled():
    return noise_suppression_enabled() and "webrtc.gain_control = true" in open(NOISE_CONF).read()


# ------------------------------------------------------------------ Mikrofontest

TEST_FILE = "/tmp/frametide-mic-test.wav"


def record_argv(source_name=None):
    argv = ["pw-record", "--rate", "48000", "--channels", "1"]
    if source_name:
        argv += ["--target", source_name]
    return argv + [TEST_FILE]


def play_argv():
    return ["pw-play", TEST_FILE]
