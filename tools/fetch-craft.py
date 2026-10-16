#!/usr/bin/env python3
"""Lädt die neuesten ArtCraft-.deb-Pakete aus den GitHub-Releases und prüft
jede Datei gegen die von GitHub veröffentlichte SHA256-Prüfsumme.

  tools/fetch-craft.py ZIELORDNER wordcraft gridcraft ...
"""
import hashlib
import json
import os
import sys
import urllib.request

REPOS = {"artcraft-launcher": "craft-launcher"}


def fetch(app, dest):
    repo = REPOS.get(app, app)
    with urllib.request.urlopen(f"https://api.github.com/repos/storytold/{repo}/releases/latest") as r:
        release = json.load(r)
    asset = next(a for a in release["assets"] if a["name"].endswith("-linux-x86_64.deb"))
    expected = (asset.get("digest") or "").removeprefix("sha256:")
    if not expected:
        sys.exit(f"{app}: keine Prüfsumme veröffentlicht")
    path = os.path.join(dest, asset["name"])
    print(f"{app} {release['tag_name']} ({asset['size'] // 1_000_000} MB)", flush=True)
    urllib.request.urlretrieve(asset["browser_download_url"], path)
    with open(path, "rb") as f:
        if hashlib.sha256(f.read()).hexdigest() != expected:
            os.remove(path)
            sys.exit(f"{app}: Prüfsumme stimmt nicht")


if __name__ == "__main__":
    os.makedirs(sys.argv[1], exist_ok=True)
    for name in sys.argv[2:]:
        fetch(name, sys.argv[1])
