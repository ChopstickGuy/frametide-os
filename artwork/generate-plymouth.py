#!/usr/bin/env python3
"""Erzeugt die Grafiken des Frametide-Startbildschirms (Plymouth) nach
artwork/plymouth/: Hintergrund (Wallpaper), Logo, Wellen-Ladeanimation und den
Hinweis „basiert auf Ubuntu“.

  python3 artwork/generate-plymouth.py      (braucht resvg oder rsvg-convert)
"""
import importlib.util
import math
import os
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "plymouth")
FRAMES = 36
FONT = 'font-family="Inter, Liberation Sans, DejaVu Sans, sans-serif"'


def render(svg_path_or_text, png, width, height=None):
    with tempfile.TemporaryDirectory() as tmp:
        src = svg_path_or_text
        if not os.path.exists(str(svg_path_or_text)):
            src = os.path.join(tmp, "f.svg")
            open(src, "w").write(svg_path_or_text)
        if shutil.which("resvg"):
            cmd = ["resvg", "-w", str(width)] + (["-h", str(height)] if height else []) + [src, png]
        else:
            cmd = ["rsvg-convert", "-w", str(width)] + (["-h", str(height)] if height else []) + [src, "-o", png]
        subprocess.run(cmd, check=True)


def wave_frame(k, size=96):
    """Kreisende Welle mit Kometenschweif – wie der Lade-Mauszeiger, größer und feiner."""
    phase = 2 * math.pi * k / FRAMES
    cx = cy = size / 2
    radius, amp, width = size * 0.36, size * 0.03, size * 0.06
    paths = []
    segments, span = 18, 300
    for s in range(segments):
        pts = []
        for j in range(17):
            deg = s * span / segments + j * (span / segments) / 16
            a = math.radians(deg) + phase
            r = radius + amp * math.sin(math.radians(deg) * 7 - 3 * phase)
            pts.append(f"{cx + r * math.cos(a):.2f} {cy + r * math.sin(a):.2f}")
        alpha = ((s + 1) / segments) ** 1.6
        w = width * (0.55 + 0.45 * (s + 1) / segments)
        cap = "round" if s == segments - 1 else "butt"
        paths.append(f'<path d="M {" L ".join(pts)}" fill="none" stroke="url(#g)" stroke-opacity="{alpha:.2f}" '
                     f'stroke-width="{w:.2f}" stroke-linecap="{cap}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">'
            '<defs><linearGradient id="g" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="#22D3EE"/>'
            '<stop offset=".55" stop-color="#6D7CFF"/><stop offset="1" stop-color="#A855F7"/></linearGradient></defs>'
            + "".join(paths) + "</svg>")


def main():
    os.makedirs(OUT, exist_ok=True)
    render(os.path.join(HERE, "wallpapers", "frametide-tide-dark.svg"), os.path.join(OUT, "background.png"), 1920)
    render(os.path.join(HERE, "logo.svg"), os.path.join(OUT, "logo.png"), 200)
    render(f'<svg xmlns="http://www.w3.org/2000/svg" width="520" height="40"><text x="260" y="27" '
           f'text-anchor="middle" {FONT} font-size="20" fill="#C9D1E3" fill-opacity="0.75" letter-spacing="1">'
           f'basiert auf Ubuntu 26.04 LTS</text></svg>', os.path.join(OUT, "based-on.png"), 520)
    for k in range(FRAMES):
        render(wave_frame(k), os.path.join(OUT, f"wave-{k}.png"), 64)
    print(f"{len(os.listdir(OUT))} Dateien in {OUT}")


if __name__ == "__main__":
    main()
