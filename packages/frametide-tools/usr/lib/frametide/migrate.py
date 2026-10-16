"""Windows-Umzug: findet Windows-Partitionen und übernimmt Dateien, Browser-Lesezeichen,
WLAN-Profile und installierte Steam-Spiele – nur lesend auf der Windows-Seite."""
import glob
import html
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from frametide_i18n import _
from games import parse_vdf

SKIP_USERS = {"public", "default", "default user", "all users", "defaultapppool", "wdagutilityaccount"}

# Windows-Ordner -> XDG-Ordner unter Linux
FOLDERS = [
    ("Documents", "DOCUMENTS", _("Dokumente")),
    ("Pictures", "PICTURES", _("Bilder")),
    ("Music", "MUSIC", _("Musik")),
    ("Videos", "VIDEOS", _("Videos")),
    ("Desktop", "DESKTOP", _("Schreibtisch")),
    ("Downloads", "DOWNLOAD", _("Downloads")),
]

BROWSERS = [
    ("Google Chrome", "AppData/Local/Google/Chrome/User Data"),
    ("Microsoft Edge", "AppData/Local/Microsoft/Edge/User Data"),
    ("Brave", "AppData/Local/BraveSoftware/Brave-Browser/User Data"),
    ("Opera", "AppData/Roaming/Opera Software/Opera Stable"),
]


# -------------------------------------------------------------- Partitionen

def windows_partitions():
    """NTFS- und BitLocker-Partitionen: [{path, label, size, mountpoint, bitlocker}]."""
    out = subprocess.run(["lsblk", "-J", "-b", "-o", "PATH,FSTYPE,LABEL,SIZE,MOUNTPOINT"],
                         capture_output=True, text=True).stdout or "{}"
    result = []

    def walk(devices):
        for dev in devices:
            fstype = (dev.get("fstype") or "").lower()
            if fstype in ("ntfs", "ntfs3", "bitlocker"):
                result.append({"path": dev["path"], "label": dev.get("label") or "",
                               "size": int(dev.get("size") or 0), "mountpoint": dev.get("mountpoint"),
                               "bitlocker": fstype == "bitlocker"})
            walk(dev.get("children", []))
    walk(json.loads(out).get("blockdevices", []))
    return result


def mount_readonly(device):
    """Hängt die Partition nur lesend ein (udisks fragt bei Bedarf nach dem Passwort)."""
    proc = subprocess.run(["udisksctl", "mount", "-b", device, "-o", "ro"], capture_output=True, text=True)
    m = re.search(r" at (.+?)\.?$", proc.stdout.strip())
    if m:
        return m.group(1)
    if "AlreadyMounted" in proc.stderr or "already mounted" in proc.stderr:
        m = re.search(r"at [`'\"](.+?)[`'\"]", proc.stderr)
        if m:
            return m.group(1)
    raise RuntimeError(proc.stderr.strip() or _("Partition konnte nicht eingehängt werden"))


def is_windows(root):
    return os.path.isdir(os.path.join(root, "Windows", "System32")) and os.path.isdir(os.path.join(root, "Users"))


def windows_users(root):
    users_dir = os.path.join(root, "Users")
    return sorted(u for u in os.listdir(users_dir)
                  if u.lower() not in SKIP_USERS and os.path.isdir(os.path.join(users_dir, u, "Desktop")))


def folder_size(path, limit_files=200000):
    total, count = 0, 0
    for base, _dirs, files in os.walk(path, onerror=lambda e: None):
        for f in files:
            try:
                total += os.lstat(os.path.join(base, f)).st_size
            except OSError:
                pass
            count += 1
            if count > limit_files:
                return total
    return total


# ---------------------------------------------------------------- Dateien

def user_folders(root, user):
    """[(Windows-Pfad, Linux-Ziel, Anzeigename)] für vorhandene Ordner."""
    from gi.repository import GLib
    special = {name: getattr(GLib.UserDirectory, f"DIRECTORY_{name}") for _w, name, _l in FOLDERS}
    result = []
    for win, xdg, label in FOLDERS:
        src = os.path.join(root, "Users", user, win)
        if os.path.isdir(src) and os.listdir(src):
            dest = GLib.get_user_special_dir(special[xdg]) or os.path.join(os.path.expanduser("~"), win)
            result.append((src, dest, label))
    return result


def copy_folder(src, dest, on_progress=None):
    """Kopiert ohne vorhandene Dateien zu überschreiben; meldet Prozent über rsync."""
    os.makedirs(dest, exist_ok=True)
    proc = subprocess.Popen(["rsync", "-a", "--ignore-existing", "--no-perms", "--chmod=Du=rwx,Fu=rw",
                             "--exclude=desktop.ini", "--exclude=Thumbs.db",
                             # exportierte WLAN-Profile enthalten Passwörter im Klartext → nicht mitkopieren
                             "--exclude=WLAN-*.xml", "--exclude=Wi-Fi-*.xml", "--exclude=WiFi-*.xml",
                             "--info=progress2",
                             src.rstrip("/") + "/", dest], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in iter(proc.stdout.readline, ""):
        m = re.search(r"(\d+)%", line)
        if m and on_progress:
            on_progress(int(m.group(1)))
    return proc.wait()


# --------------------------------------------------------------- Lesezeichen

def _chromium_tree(node):
    if node.get("type") == "url":
        return {"title": node.get("name", ""), "url": node.get("url", "")}
    return {"title": node.get("name", ""), "children": [_chromium_tree(c) for c in node.get("children", [])]}


def browser_bookmarks(root, user):
    """[(Browser, Ordnerbaum)] aus Chrome, Edge, Brave, Opera und Firefox."""
    home = os.path.join(root, "Users", user)
    found = []
    for name, rel in BROWSERS:
        for path in glob.glob(os.path.join(home, rel, "*", "Bookmarks")) + glob.glob(os.path.join(home, rel, "Bookmarks")):
            try:
                data = json.load(open(path, encoding="utf-8"))
            except (OSError, ValueError):
                continue
            roots = [_chromium_tree(r) for r in data.get("roots", {}).values() if isinstance(r, dict)]
            tree = {"title": name, "children": [r for r in roots if r.get("children")]}
            if tree["children"]:
                profile = os.path.basename(os.path.dirname(path))
                if profile not in ("Default", os.path.basename(rel)):
                    tree["title"] += f" ({profile})"
                found.append((tree["title"], tree))
    for places in glob.glob(os.path.join(home, "AppData/Roaming/Mozilla/Firefox/Profiles/*/places.sqlite")):
        tree = _firefox_tree(places)
        if tree and tree["children"]:
            found.append((tree["title"], tree))
    return found


def _firefox_tree(path):
    with tempfile.TemporaryDirectory() as tmp:
        copy = os.path.join(tmp, "places.sqlite")
        shutil.copy(path, copy)  # Original nie direkt öffnen (nur lesend eingehängt, ggf. gesperrt)
        try:
            db = sqlite3.connect(copy)
            rows = db.execute("SELECT b.id, b.parent, b.type, b.title, p.url FROM moz_bookmarks b "
                              "LEFT JOIN moz_places p ON p.id = b.fk ORDER BY b.parent, b.position").fetchall()
            db.close()
        except sqlite3.Error:
            return None
    children = {}
    for bid, parent, typ, title, url in rows:
        children.setdefault(parent, []).append((bid, typ, title, url))

    def build(bid, title):
        node = {"title": title or "", "children": []}
        for cid, typ, ctitle, url in children.get(bid, []):
            if typ == 1 and url and not url.startswith("place:"):
                node["children"].append({"title": ctitle or url, "url": url})
            elif typ == 2:
                sub = build(cid, ctitle)
                if sub["children"]:
                    node["children"].append(sub)
        return node
    return build(1, "Firefox")


def bookmarks_html(trees):
    """Netscape-Lesezeichenformat – lässt sich in jeden Browser importieren."""
    lines = ["<!DOCTYPE NETSCAPE-Bookmark-file-1>",
             '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
             f"<TITLE>{html.escape(_('Lesezeichen aus Windows'))}</TITLE>",
             f"<H1>{html.escape(_('Lesezeichen aus Windows'))}</H1>", "<DL><p>"]

    def emit(node, depth):
        pad = "    " * depth
        if "url" in node:
            lines.append(f'{pad}<DT><A HREF="{html.escape(node["url"], quote=True)}">{html.escape(node["title"])}</A>')
        else:
            lines.append(f"{pad}<DT><H3>{html.escape(node['title'])}</H3>")
            lines.append(f"{pad}<DL><p>")
            for child in node["children"]:
                emit(child, depth + 1)
            lines.append(f"{pad}</DL><p>")
    for _name, tree in trees:
        emit(tree, 1)
    lines.append("</DL><p>")
    return "\n".join(lines) + "\n"


def count_bookmarks(tree):
    return 1 if "url" in tree else sum(count_bookmarks(c) for c in tree.get("children", []))


# --------------------------------------------------------------------- WLAN

def wifi_profiles(root, user=None):
    """[{ssid, auth, key}] – key nur, wenn er im Klartext vorliegt.

    Windows speichert WLAN-Passwörter verschlüsselt (DPAPI). Klartext gibt es nur in
    Profilen, die mit „netsh wlan export profile key=clear“ exportiert wurden; danach
    suchen wir zusätzlich auf Desktop, in Dokumente und Downloads.
    """
    paths = glob.glob(os.path.join(root, "ProgramData/Microsoft/Wlansvc/Profiles/Interfaces/*/*.xml"))
    if user:
        for folder in ("Desktop", "Documents", "Downloads"):
            paths += glob.glob(os.path.join(root, "Users", user, folder, "**", "*.xml"), recursive=True)
    profiles = {}
    for path in paths:
        try:
            tree = ET.parse(path)
        except (ET.ParseError, OSError):
            continue
        ns = {"w": "http://www.microsoft.com/networking/WLAN/profile/v1"}
        r = tree.getroot()
        if not r.tag.endswith("WLANProfile"):
            continue
        ssid = r.findtext("w:SSIDConfig/w:SSID/w:name", namespaces=ns) or r.findtext("w:name", namespaces=ns)
        auth = r.findtext(".//w:authEncryption/w:authentication", namespaces=ns) or ""
        protected = (r.findtext(".//w:sharedKey/w:protected", namespaces=ns) or "true").lower() == "true"
        key = None if protected else r.findtext(".//w:sharedKey/w:keyMaterial", namespaces=ns)
        if ssid and (ssid not in profiles or key):
            profiles[ssid] = {"ssid": ssid, "auth": auth, "key": key}
    return sorted(profiles.values(), key=lambda p: p["ssid"].lower())


def import_wifi(profile):
    """Legt die WLAN-Verbindung im NetworkManager an (nur WPA/WPA2/WPA3-Personal und offen)."""
    auth = profile["auth"].upper()
    cmd = ["nmcli", "connection", "add", "type", "wifi", "con-name", profile["ssid"],
           "ssid", profile["ssid"], "connection.autoconnect", "yes"]
    if auth in ("WPAPSK", "WPA2PSK", "WPA3SAE") and profile["key"]:
        key_mgmt = "sae" if auth == "WPA3SAE" else "wpa-psk"
        cmd += ["wifi-sec.key-mgmt", key_mgmt, "wifi-sec.psk", profile["key"]]
    elif auth != "OPEN":
        return False
    return subprocess.run(cmd, capture_output=True).returncode == 0


# --------------------------------------------------------------- Steam-Spiele

def windows_steam_games(root):
    """[(appid, Name, Größe, Manifest, Spielordner)] von dieser Windows-Partition."""
    libraries = [os.path.join(root, "Program Files (x86)", "Steam", "steamapps")]
    vdf = os.path.join(libraries[0], "libraryfolders.vdf")
    if os.path.exists(vdf):
        for entry in parse_vdf(open(vdf, encoding="utf-8", errors="replace").read()).get("libraryfolders", {}).values():
            if isinstance(entry, dict) and entry.get("path", "").upper().startswith("C:"):
                path = os.path.join(root, *re.split(r"[\\/]+", entry["path"][3:]), "steamapps")
                if path not in libraries:
                    libraries.append(path)
    games = []
    for library in libraries:
        for manifest in glob.glob(os.path.join(library, "appmanifest_*.acf")):
            state = parse_vdf(open(manifest, encoding="utf-8", errors="replace").read()).get("AppState", {})
            folder = os.path.join(library, "common", state.get("installdir", ""))
            if state.get("appid") and state.get("installdir") and os.path.isdir(folder):
                games.append((state["appid"], state.get("name", state["installdir"]),
                              int(state.get("SizeOnDisk", 0) or 0), manifest, folder))
    return sorted(games, key=lambda g: g[1].lower())


def linux_steam_library():
    path = os.path.expanduser("~/.local/share/Steam/steamapps")
    return path if os.path.isdir(path) else None


def copy_steam_game(manifest, folder, library, on_progress=None):
    """Kopiert Spiel + Manifest; Steam prüft die Dateien beim nächsten Start und lädt nur Fehlendes."""
    dest = os.path.join(library, "common", os.path.basename(folder))
    rc = copy_folder(folder, dest, on_progress)
    if rc == 0:
        shutil.copy(manifest, os.path.join(library, os.path.basename(manifest)))
    return rc
