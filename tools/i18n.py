#!/usr/bin/env python3
"""Übersetzungen für Frametide Store/Center – ohne externe Werkzeuge.

  tools/i18n.py extract            Texte aus dem Code nach po/frametide.pot
  tools/i18n.py check              fehlende Übersetzungen in po/*.po anzeigen
  tools/i18n.py compile ZIEL       po/*.po -> ZIEL/<sprache>/LC_MESSAGES/frametide.mo
"""
import ast
import glob
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = sorted(glob.glob(os.path.join(ROOT, "packages/frametide-tools/usr/lib/frametide/*.py")))
PO_DIR = os.path.join(ROOT, "po")


def extract():
    ids = {}
    for path in SOURCES:
        for node in ast.walk(ast.parse(open(path).read())):
            if (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "_" and node.args
                    and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                ids.setdefault(node.args[0].value, f"{os.path.basename(path)}:{node.lineno}")
    return ids


def quote(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def parse_po(path):
    entries, msgid, msgstr, target = {}, None, None, None
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line.startswith("msgid "):
            if msgid is not None:
                entries[msgid] = msgstr
            msgid, msgstr, target = ast.literal_eval(line[6:]), "", "id"
        elif line.startswith("msgstr "):
            msgstr, target = ast.literal_eval(line[7:]), "str"
        elif line.startswith('"'):
            if target == "id":
                msgid += ast.literal_eval(line)
            else:
                msgstr += ast.literal_eval(line)
    if msgid is not None:
        entries[msgid] = msgstr
    return entries


def write_mo(entries, path):
    """GNU-gettext .mo-Format (Little Endian)."""
    items = sorted((k.encode(), v.encode()) for k, v in entries.items() if v or k == "")
    n = len(items)
    ids = b"".join(k + b"\0" for k, _ in items)
    strs = b"".join(v + b"\0" for _, v in items)
    start = 7 * 4 + 16 * n
    id_off, str_off, offsets = start, start + len(ids), []
    for k, v in items:
        offsets.append((len(k), id_off, len(v), str_off))
        id_off += len(k) + 1
        str_off += len(v) + 1
    out = struct.pack("<7I", 0x950412DE, 0, n, 28, 28 + 8 * n, 0, 0)
    out += b"".join(struct.pack("<2I", l, o) for l, o, _, _ in offsets)
    out += b"".join(struct.pack("<2I", l, o) for _, _, l, o in offsets)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(out + ids + strs)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    ids = extract()
    if cmd == "extract":
        os.makedirs(PO_DIR, exist_ok=True)
        with open(os.path.join(PO_DIR, "frametide.pot"), "w", encoding="utf-8") as f:
            f.write('msgid ""\nmsgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n')
            for msgid, ref in ids.items():
                f.write(f"#: {ref}\nmsgid {quote(msgid)}\nmsgstr \"\"\n\n")
        print(f"{len(ids)} Texte -> po/frametide.pot")
    elif cmd == "check":
        bad = 0
        for po in sorted(glob.glob(os.path.join(PO_DIR, "*.po"))):
            entries = parse_po(po)
            missing = [m for m in ids if not entries.get(m)]
            unused = [m for m in entries if m and m not in ids]
            fmt = [m for m in ids if entries.get(m) and
                   set(re.findall(r"\{\w+\}", m)) != set(re.findall(r"\{\w+\}", entries[m]))]
            print(f"{os.path.basename(po)}: {len(ids) - len(missing)}/{len(ids)} übersetzt"
                  f"{', ' + str(len(unused)) + ' ungenutzt' if unused else ''}")
            for m in missing:
                print(f"  FEHLT: {m}")
            for m in fmt:
                print(f"  PLATZHALTER: {m}")
            bad += len(missing) + len(fmt)
        sys.exit(1 if bad else 0)
    elif cmd == "compile":
        for po in sorted(glob.glob(os.path.join(PO_DIR, "*.po"))):
            lang = os.path.basename(po)[:-3]
            entries = parse_po(po)
            entries[""] = "Content-Type: text/plain; charset=UTF-8\n"
            write_mo(entries, os.path.join(sys.argv[2], lang, "LC_MESSAGES", "frametide.mo"))
            print(f"{lang}: {sum(1 for v in entries.values() if v) - 1} Texte")


if __name__ == "__main__":
    main()
