#!/usr/bin/env python3
"""Prüft, ob alle Abhängigkeiten der Frametide-Pakete und alle im Build-Skript
installierten Pakete im Ubuntu-Archiv existieren – bevor ein 30-minütiger
ISO-Build daran scheitert.

  tools/check-packages.py
"""
import glob
import lzma
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPONENTS = ["main", "restricted", "universe", "multiverse"]
# Kommen aus Fremdquellen bzw. werden selbst gebaut
EXTERNAL = {"firefox"}


def conf():
    values = {}
    for line in open(os.path.join(ROOT, "config/frametide.conf")):
        m = re.match(r'(\w+)="([^"]*)"', line)
        if m:
            values[m.group(1)] = m.group(2)
    return values


def archive_packages(mirror, suite, arch):
    names = set()
    for dist, comp in [(d, c) for d in (suite, f"{suite}-updates") for c in COMPONENTS]:
        url = f"{mirror}/dists/{dist}/{comp}/binary-{arch}/Packages.xz"
        with urllib.request.urlopen(url) as r:
            text = lzma.decompress(r.read()).decode("utf-8", "replace")
        names |= set(re.findall(r"^Package: (\S+)", text, re.M))
        # virtuelle Pakete (Provides) zählen ebenfalls
        for provides in re.findall(r"^Provides: (.+)", text, re.M):
            names |= {p.split()[0] for p in provides.split(",")}
    return names


def control_deps():
    deps, local = {}, set()
    for control in glob.glob(os.path.join(ROOT, "packages/*/DEBIAN/control")):
        text = open(control).read()
        local.add(re.search(r"^Package: (\S+)", text, re.M).group(1))
        for field in ("Depends", "Recommends"):
            m = re.search(rf"^{field}: (.*(?:\n .*)*)", text, re.M)
            for dep in (m.group(1).replace("\n", " ").split(",") if m else []):
                for alt in dep.split("|"):
                    deps.setdefault(alt.split()[0].split(":")[0], set()).add(os.path.basename(os.path.dirname(os.path.dirname(control))))
    return deps, local


def script_packages():
    pkgs = {}
    text = open(os.path.join(ROOT, "scripts/chroot-install.sh")).read()
    for cmd in re.findall(r"apt_install ((?:[^\n]|\\\n)+)", text):
        for word in cmd.replace("\\\n", " ").split():
            if word != "\\" and not word.startswith(("-", "/", "$")):
                pkgs.setdefault(word.split(":")[0], set()).add("chroot-install.sh")
    return pkgs


def main():
    c = conf()
    print(f"Lade Paketlisten für Ubuntu {c['UBUNTU_VERSION']} ({c['UBUNTU_SUITE']}) …")
    available = archive_packages(c["MIRROR"], c["UBUNTU_SUITE"], c["ARCH"])
    deps, local = control_deps()
    for name, src in script_packages().items():
        deps.setdefault(name, set()).update(src)

    missing = {n: s for n, s in deps.items() if n not in available and n not in local and n not in EXTERNAL}
    print(f"{len(deps)} Pakete geprüft, {len(available)} im Archiv.")
    for name, src in sorted(missing.items()):
        print(f"  FEHLT: {name}  (benötigt von {', '.join(sorted(src))})")
    if missing:
        return 1
    print("Alles vorhanden ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
