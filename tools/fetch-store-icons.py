#!/usr/bin/env python3
"""Lädt die Logos aller Store-Apps (128 px) nach
packages/frametide-tools/usr/share/frametide/store/icons/<id>.png,
damit der Store auch offline echte App-Logos zeigt.

Quellen: Flathub (auch für Ubuntu-Pakete mit Flathub-Gegenstück) und die
ArtCraft-Repositories. Erneut ausführen, wenn sich der Katalog ändert.
"""
import concurrent.futures
import json
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "packages/frametide-tools/usr/share/frametide/store")
CRAFT_REPOS = {"artcraft-launcher": "craft-launcher"}
# Ubuntu-Pakete -> gleiches Programm auf Flathub (nur für das Logo)
FLATHUB_EQUIV = {
    "steam": "com.valvesoftware.Steam", "lutris": "net.lutris.Lutris",
    "goverlay": "io.github.benjamimgois.goverlay", "chrome": "com.google.Chrome",
    "firefox": "org.mozilla.firefox", "vscode": "com.visualstudio.code",
    "github-desktop": "io.github.shiftey.Desktop", "neovim": "io.neovim.nvim",
    "openrgb": "org.openrgb.OpenRGB", "cockpit": "org.cockpit_project.CockpitClient", "wireshark": "org.wireshark.Wireshark", "coolercontrol": "org.coolercontrol.CoolerControl",
    "piper": "org.freedesktop.Piper", "solaar": "io.github.pwr_solaar.solaar",
    "openrazer": "app.polychromatic.controller", "corectrl": "org.corectrl.CoreCtrl",
    "gparted": "org.gnome.GParted", "timeshift": "com.linuxmint.timeshift",
    "resources": "net.nokyan.Resources",
}


# Feste Logo-Adressen für Apps ohne Flathub-Eintrag
ICON_URLS = {
    "net-merge": "https://raw.githubusercontent.com/rohit267/net-merge/main/docs/icon.png",
    "sniffnet": "https://raw.githubusercontent.com/GyulyVGC/sniffnet/main/resources/logos/raw/icon.png",
}


def icon_url(app):
    if app["id"] in ICON_URLS:
        return ICON_URLS[app["id"]]
    if app["source"] == "craft":
        repo = CRAFT_REPOS.get(app["ref"], app["ref"])
        return (f"https://raw.githubusercontent.com/storytold/{repo}/HEAD/assets/app-icon/"
                f"hicolor/128x128/apps/ai.storyteller.{app['ref']}.png")
    flathub_id = app["ref"] if app["source"] == "flatpak" else FLATHUB_EQUIV.get(app["id"])
    if not flathub_id:
        return None
    with urllib.request.urlopen(f"https://flathub.org/api/v2/appstream/{flathub_id}", timeout=30) as r:
        return json.load(r).get("icon")


def fetch(app):
    target = os.path.join(STORE, "icons", f"{app['id']}.png")
    try:
        url = icon_url(app)
        if not url:
            return app["id"], "kein Logo-Quelle (Icon-Theme)"
        with urllib.request.urlopen(url, timeout=30) as r:
            data = r.read()
        if not data.startswith(b"\x89PNG"):
            return app["id"], "kein PNG"
        with open(target, "wb") as f:
            f.write(data)
        return app["id"], None
    except Exception as e:
        return app["id"], str(e)


def main():
    os.makedirs(os.path.join(STORE, "icons"), exist_ok=True)
    catalog = json.load(open(os.path.join(STORE, "catalog.json")))
    apps = [a for c in catalog["categories"] for a in c["apps"]]
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        results = list(pool.map(fetch, apps))
    ok = sum(1 for _, err in results if err is None)
    print(f"{ok}/{len(apps)} Logos geladen")
    for app_id, err in results:
        if err:
            print(f"  {app_id}: {err}")


if __name__ == "__main__":
    main()
