"""Spiele-Check: installierte Steam-Spiele finden und prüfen, wie gut sie unter
Linux laufen (ProtonDB) und ob ein Anti-Cheat Linux blockiert (AreWeAntiCheatYet)."""
import glob
import json
import os
import re
import time
import urllib.parse
import urllib.request

from frametide_i18n import _

HOME = os.path.expanduser("~")
STEAM_ROOTS = [
    os.path.join(HOME, ".local/share/Steam"),
    os.path.join(HOME, ".steam/steam"),
    os.path.join(HOME, ".var/app/com.valvesoftware.Steam/.local/share/Steam"),
]
CACHE_DIR = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.join(HOME, ".cache")), "frametide")
AWACY_URL = "https://raw.githubusercontent.com/AreWeAntiCheatYet/AreWeAntiCheatYet/HEAD/games.json"
PROTONDB_URL = "https://www.protondb.com/api/v1/reports/summaries/{appid}.json"
SEARCH_URL = "https://store.steampowered.com/api/storesearch/?term={term}&cc=de&l=german"
# Werkzeuge, die Steam wie Spiele installiert
TOOL_NAME = re.compile(r"^(Proton|Steam Linux Runtime|Steamworks Common|SteamVR)", re.I)
HEADERS = {"User-Agent": "FrametideOS-GameCheck/1.0"}


# ------------------------------------------------------------ Steam-Dateien

def parse_vdf(text):
    """Minimaler Parser für Valves KeyValues-Format (libraryfolders.vdf, appmanifest_*.acf)."""
    tokens = re.findall(r'"((?:[^"\\]|\\.)*)"|([{}])', text)
    stack, current, key = [], {}, None
    for string, brace in tokens:
        if brace == "{":
            new = {}
            current[key] = new
            stack.append(current)
            current, key = new, None
        elif brace == "}":
            current = stack.pop() if stack else current
        elif key is None:
            key = string.replace("\\\\", "\\")
        else:
            current[key] = string.replace("\\\\", "\\")
            key = None
    return current


def steam_libraries(roots=None):
    libraries = []
    for root in roots or STEAM_ROOTS:
        vdf = os.path.join(root, "steamapps", "libraryfolders.vdf")
        if not os.path.exists(vdf):
            continue
        data = parse_vdf(open(vdf, encoding="utf-8", errors="replace").read())
        folders = data.get("libraryfolders", data)
        for entry in folders.values():
            if isinstance(entry, dict) and entry.get("path"):
                path = os.path.join(entry["path"], "steamapps")
                if os.path.isdir(path) and os.path.realpath(path) not in map(os.path.realpath, libraries):
                    libraries.append(path)
    return libraries


def installed_games(roots=None):
    games = {}
    for library in steam_libraries(roots):
        for manifest in glob.glob(os.path.join(library, "appmanifest_*.acf")):
            state = parse_vdf(open(manifest, encoding="utf-8", errors="replace").read()).get("AppState", {})
            appid, name = state.get("appid"), state.get("name", "")
            if appid and name and not TOOL_NAME.match(name):
                games[appid] = name
    return sorted(games.items(), key=lambda item: item[1].lower())


# --------------------------------------------------------------- Online-Daten

def _get_json(url, timeout=15):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=timeout) as r:
        return json.load(r)


def search_steam(term, limit=6):
    data = _get_json(SEARCH_URL.format(term=urllib.parse.quote(term)))
    return [(str(item["id"]), item["name"]) for item in data.get("items", []) if item.get("type") == "app"][:limit]


def protondb(appid):
    try:
        return _get_json(PROTONDB_URL.format(appid=appid))
    except Exception:
        return {}


def anticheat_list(max_age=86400):
    """Alle AreWeAntiCheatYet-Einträge, einen Tag lang zwischengespeichert."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, "awacy.json")
    if not os.path.exists(path) or time.time() - os.path.getmtime(path) > max_age:
        try:
            data = _get_json(AWACY_URL, timeout=30)
            with open(path, "w") as f:
                json.dump(data, f)
            return data
        except Exception:
            if not os.path.exists(path):
                return []
    with open(path) as f:
        return json.load(f)


def anticheat_by_name(term, limit=4):
    """Für Spiele, die es nicht auf Steam gibt (z. B. Valorant, Fortnite)."""
    term = term.lower()
    return [g for g in anticheat_list() if term in g.get("name", "").lower()][:limit]


def anticheat_db(max_age=86400):
    """Steam-AppID -> AreWeAntiCheatYet-Eintrag."""
    return {str(g["storeIds"]["steam"]): g for g in anticheat_list(max_age) if g.get("storeIds", {}).get("steam")}


# ------------------------------------------------------------------ Bewertung

# Stufe: good / ok / bad / unknown
TIERS = {
    "native": ("good", _("Native Linux-Version")),
    "platinum": ("good", _("Läuft perfekt")),
    "gold": ("good", _("Läuft sehr gut")),
    "silver": ("ok", _("Läuft mit kleinen Problemen")),
    "bronze": ("ok", _("Läuft, aber mit Problemen")),
    "borked": ("bad", _("Läuft nicht")),
}


def anticheat_verdict(entry):
    """Bewertung nur aus dem Anti-Cheat-Eintrag (für Nicht-Steam-Spiele)."""
    names = ", ".join(entry.get("anticheats", [])) or "Anti-Cheat"
    status = entry.get("status")
    if status == "Denied":
        return "bad", _("Anti-Cheat blockiert"), f"{names} – {_('vom Hersteller blockiert')}"
    if status == "Broken":
        return "bad", _("Anti-Cheat blockiert"), f"{names} – {_('funktioniert nicht unter Linux')}"
    if status in ("Supported", "Running"):
        return "good", _("Anti-Cheat läuft unter Linux"), names
    return "unknown", _("Noch keine Bewertung"), names


def verdict(appid, anticheats):
    """(Stufe, Text, Details) für ein Spiel."""
    ac = anticheats.get(str(appid))
    if ac and ac.get("status") in ("Denied", "Broken"):
        names = ", ".join(ac.get("anticheats", [])) or "Anti-Cheat"
        reason = _("vom Hersteller blockiert") if ac["status"] == "Denied" else _("funktioniert nicht unter Linux")
        return "bad", _("Anti-Cheat blockiert"), f"{names} – {reason}"
    summary = protondb(appid)
    tier = summary.get("trendingTier") or summary.get("tier")
    level, text = TIERS.get(tier, ("unknown", _("Noch keine Bewertung")))
    details = []
    if summary.get("total"):
        details.append(_("ProtonDB: {n} Berichte").format(n=summary["total"]))
    if ac:
        details.append(_("Anti-Cheat: {names} – unterstützt").format(names=", ".join(ac.get("anticheats", []))))
    return level, text, " · ".join(details)
