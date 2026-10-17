#!/usr/bin/env python3
"""Erzeugt das Frametide-Cursor-Theme: Lade-Zeiger als Welle, die im Kreis läuft.
Alle übrigen Zeiger erbt das Theme von Yaru (Ubuntu-Standard).

  python3 artwork/generate-cursors.py      (braucht resvg oder rsvg-convert)

Ergebnis: artwork/cursors/Frametide/ (Xcursor-Dateien + index.theme)
"""
import math
import os
import shutil
import struct
import subprocess
import tempfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "cursors", "Frametide")
SIZES = (24, 32, 48, 64)
FRAMES = 24
DELAY_MS = 42  # ca. 1 Umdrehung pro Sekunde

ARROW = ("M 0 0 L 0 17 L 4.2 13 L 7 19.2 L 9.6 18.1 L 6.9 12 L 12.4 12 Z")  # klassischer Pfeil, 20 px Raster


def wave_ring(cx, cy, radius, amp, phase, width):
    """Welle, die als Kometenschweif im Kreis läuft: vorne kräftig, hinten ausblendend.
    Die Wellenberge wandern zusätzlich entlang des Rings."""
    segments, span = 14, 300  # 300° sichtbarer Schweif in 14 Abschnitten
    out = []
    for s_idx in range(segments):
        pts = []
        a0 = s_idx * span / segments
        for j in range(0, 23):
            deg = a0 + j * (span / segments) / 22
            a = math.radians(deg) + phase
            r = radius + amp * math.sin(math.radians(deg) * 7 - 3 * phase)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        d = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in pts)
        alpha = ((s_idx + 1) / segments) ** 1.6
        w = width * (0.55 + 0.45 * (s_idx + 1) / segments)
        cap = "round" if s_idx == segments - 1 else "butt"  # nur die Spitze rund → keine Perlen
        out.append(f'<path d="{d}" fill="none" stroke="url(#g)" stroke-opacity="{alpha:.2f}" '
                   f'stroke-width="{w:.2f}" stroke-linecap="{cap}" stroke-linejoin="round"/>')
    return "".join(out)


def frame_svg(kind, k):
    phase = 2 * math.pi * k / FRAMES
    grad = ('<defs><linearGradient id="g" x1="0" y1="1" x2="1" y2="0">'
            '<stop offset="0" stop-color="#22D3EE"/><stop offset=".55" stop-color="#6D7CFF"/>'
            '<stop offset="1" stop-color="#A855F7"/></linearGradient></defs>')
    if kind == "wait":
        # Großer Wellenring, mittig (Hotspot in der Mitte)
        body = (f'<circle cx="16" cy="16" r="11" fill="#05070F" fill-opacity=".35"/>'
                + wave_ring(16, 16, 9.5, 0.9, phase, 2.6))
    else:
        # Pfeil + kleiner Wellenring unten rechts (Hotspot an der Pfeilspitze)
        body = (f'<g transform="translate(2 1) scale(1.0)"><path d="{ARROW}" fill="#F3F6FD" '
                f'stroke="#05070F" stroke-width="1.2" stroke-linejoin="round"/></g>'
                f'<circle cx="22" cy="22" r="7.5" fill="#05070F" fill-opacity=".35"/>'
                + wave_ring(22, 22, 6, 0.6, phase, 2.0))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">{grad}{body}</svg>'


def render(svg_text, size, tmp):
    src = os.path.join(tmp, "f.svg")
    dst = os.path.join(tmp, "f.png")
    open(src, "w").write(svg_text)
    if shutil.which("resvg"):
        subprocess.run(["resvg", "-w", str(size), "-h", str(size), src, dst], check=True)
    else:
        subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), src, "-o", dst], check=True)
    return read_png_rgba(dst)


def read_png_rgba(path):
    """Minimaler PNG-Leser (8 Bit RGBA, ohne Interlacing) → (Breite, Höhe, Zeilen als bytes)."""
    data = open(path, "rb").read()
    pos, idat, width = 8, b"", 0
    while pos < len(data):
        length, ctype = struct.unpack(">I4s", data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + length]
        if ctype == b"IHDR":
            width, height, depth, color = struct.unpack(">IIBB", chunk[:10])
            assert depth == 8 and color == 6, "nur RGBA8"
        elif ctype == b"IDAT":
            idat += chunk
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride, rows, prev = width * 4, [], bytearray(width * 4)
    for y in range(height):
        f = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - 4] if i >= 4 else 0
            b = prev[i]
            c = prev[i - 4] if i >= 4 else 0
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(bytes(line))
        prev = line
    return width, height, rows


def to_argb(width, height, rows):
    """Xcursor erwartet vormultipliziertes ARGB, Little Endian."""
    out = bytearray()
    for row in rows:
        for i in range(0, width * 4, 4):
            r, g, b, a = row[i:i + 4]
            out += struct.pack("<I", (a << 24) | ((r * a // 255) << 16) | ((g * a // 255) << 8) | (b * a // 255))
    return bytes(out)


def write_xcursor(path, images):
    """images: [(Nennmaß, Breite, Höhe, xhot, yhot, Verzögerung ms, ARGB-Pixel)]"""
    header = struct.pack("<4sIII", b"Xcur", 16, 0x10000, len(images))
    toc_size = 12 * len(images)
    offset = 16 + toc_size
    toc, chunks = b"", b""
    for nominal, w, h, xh, yh, delay, pixels in images:
        toc += struct.pack("<III", 0xFFFD0002, nominal, offset + len(chunks))
        chunks += struct.pack("<IIIIIIIII", 36, 0xFFFD0002, nominal, 1, w, h, xh, yh, delay) + pixels
    with open(path, "wb") as f:
        f.write(header + toc + chunks)


def main():
    cursors = os.path.join(OUT, "cursors")
    os.makedirs(cursors, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for kind, hot in (("wait", (16, 16)), ("progress", (2, 1))):
            images = []
            for size in SIZES:
                scale = size / 32
                for k in range(FRAMES):
                    w, h, rows = render(frame_svg(kind, k), size, tmp)
                    images.append((size, w, h, round(hot[0] * scale), round(hot[1] * scale),
                                   DELAY_MS, to_argb(w, h, rows)))
            write_xcursor(os.path.join(cursors, kind), images)
            print(f"{kind}: {len(images)} Bilder")
    # Alle Namen, unter denen Programme die Lade-Zeiger anfordern
    aliases = {"wait": ["watch"],
               "progress": ["left_ptr_watch", "half-busy", "08e8e1c95fe2fc01f976f1e063a24ccd",
                            "3ecb610c1bf2410f44200f48c40d3599", "00000000000000020006000e7e9ffc3f"]}
    for target, names in aliases.items():
        for name in names:
            link = os.path.join(cursors, name)
            if os.path.lexists(link):
                os.remove(link)
            os.symlink(target, link)
    with open(os.path.join(OUT, "index.theme"), "w") as f:
        f.write("[Icon Theme]\nName=Frametide\nComment=Yaru-Zeiger mit Frametide-Wellen-Ladeanimation\n"
                "Inherits=Yaru\n")


if __name__ == "__main__":
    main()
