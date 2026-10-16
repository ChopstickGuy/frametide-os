#!/usr/bin/env python3
"""Erzeugt die Frametide-Wallpaper als SVG (auflösungsunabhängig) nach
artwork/wallpapers/. Ohne Abhängigkeiten außer Python 3.

  python3 artwork/generate-wallpapers.py
"""
import math
import os
import random

W, H = 3840, 2160
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "wallpapers")


def wave_points(y0, amp, freq, phase, steps=160, drift=0.0):
    pts = []
    for i in range(steps + 1):
        x = -100 + (W + 200) * i / steps
        t = x / W
        y = (y0 + drift * t * H
             + amp * math.sin(2 * math.pi * (freq * t) + phase)
             + amp * 0.35 * math.sin(2 * math.pi * (freq * 2.3 * t) + phase * 1.7))
        pts.append((x, y))
    return pts


def poly(pts):
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)


def filled(pts):
    return poly(pts) + f" L{W + 100} {H + 100} L-100 {H + 100} Z"


def svg(defs, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="{W}" height="{H}">\n<defs>\n{defs}\n</defs>\n{body}\n</svg>\n')


def lin(id_, stops, x2=1, y2=0, x1=0, y1=0):
    s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
    return f'<linearGradient id="{id_}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{s}</linearGradient>'


def rad(id_, cx, cy, r, color, a):
    return (f'<radialGradient id="{id_}" cx="{cx}" cy="{cy}" r="{r}">'
            f'<stop offset="0" stop-color="{color}" stop-opacity="{a}"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')


def logo_mark(cx, cy, scale, frame="#E6EAF2", opacity=1.0):
    return f'''<g transform="translate({cx} {cy}) scale({scale}) translate(-128 -128)" opacity="{opacity}">
  <g fill="none" stroke="{frame}" stroke-width="14" stroke-linecap="round" stroke-linejoin="round">
    <path d="M22 76 V44 Q22 22 44 22 H76"/><path d="M234 180 V212 Q234 234 212 234 H180"/></g>
  <g stroke="#22D3EE" stroke-width="10" stroke-linecap="round">
    <path d="M30 150 H70" opacity=".55"/><path d="M44 176 H82" opacity=".8"/></g>
  <path fill="url(#ftWave)" d="M40 206 C86 206 100 176 112 144 C128 100 154 62 196 60 C232 58 246 92 232 116
    C220 136 190 134 184 114 C180 98 194 88 207 94 C184 80 160 98 150 132 C138 172 156 200 218 206 Z"/>
</g>'''


WAVE_GRAD = lin("ftWave", [(0, "#22D3EE", 1), (.55, "#6D7CFF", 1), (1, "#A855F7", 1)], x1=0, y1=1, x2=1, y2=0)


def layered_waves(colors, base_y, spacing, amp, freq, seed, fade_to):
    """Gestaffelte Wellen; jede Ebene läuft nach unten in die Grundfarbe aus."""
    rnd = random.Random(seed)
    defs, paths = [], []
    for i, (color, opacity) in enumerate(colors):
        top = base_y + i * spacing - amp
        defs.append(f'<linearGradient id="w{seed}_{i}" gradientUnits="userSpaceOnUse" x1="0" y1="{top:.0f}" '
                    f'x2="0" y2="{H}"><stop offset="0" stop-color="{color}" stop-opacity="{opacity}"/>'
                    f'<stop offset="1" stop-color="{fade_to}" stop-opacity="{opacity}"/></linearGradient>')
        pts = wave_points(base_y + i * spacing, amp * (1 - i * 0.08), freq + i * 0.15,
                          rnd.uniform(0, math.tau), drift=-0.05)
        paths.append(f'<path d="{filled(pts)}" fill="url(#w{seed}_{i})"/>')
    return "".join(defs), "\n".join(paths)


def tide(dark=True, branded=False):
    if dark:
        bg = lin("bg", [(0, "#0A0F24", 1), (1, "#05070F", 1)], x2=0, y2=1)
        glows = rad("g1", .82, .18, .7, "#8B5CF6", .35) + rad("g2", .15, .9, .6, "#22D3EE", .25)
        layers = [("#3B2A8C", .45), ("#4C3FD0", .45), ("#5B5BEA", .5), ("#4F7FF0", .55),
                  ("#2FA8E8", .6), ("#22D3EE", .7)]
    else:
        bg = lin("bg", [(0, "#F3F6FD", 1), (1, "#DFE7F7", 1)], x2=0, y2=1)
        glows = rad("g1", .82, .18, .7, "#C4B5FD", .55) + rad("g2", .15, .9, .6, "#A5F3FC", .55)
        layers = [("#DDD6FE", .7), ("#C7D2FE", .7), ("#A5B4FC", .7), ("#93C5FD", .75),
                  ("#7DD3FC", .8), ("#67E8F9", .9)]
    wdefs, waves = layered_waves(layers, H * 0.64, 62, 95, 1.1, 7, "#05070F" if dark else "#E8EEF9")
    body = ('<rect width="100%" height="100%" fill="url(#bg)"/>'
            '<rect width="100%" height="100%" fill="url(#g1)"/><rect width="100%" height="100%" fill="url(#g2)"/>\n'
            + waves)
    if branded:
        body += logo_mark(W / 2, H * 0.40, 2.0)
    return svg(bg + glows + WAVE_GRAD + wdefs, body)


def nightwave():
    defs = (lin("bg", [(0, "#060814", 1), (1, "#0B0E1E", 1)], x2=0, y2=1)
            + lin("ln", [(0, "#22D3EE", 0), (.25, "#22D3EE", 1), (.7, "#8B5CF6", 1), (1, "#EC4899", 0)])
            + rad("g1", .5, .55, .55, "#4F46E5", .25))
    lines = []
    for i in range(48):
        t = i / 47
        pts = wave_points(H * 0.38 + i * 18, 260 * (0.6 + 0.4 * math.sin(t * math.pi)), 0.9,
                          1.2 + t * 1.4, steps=220)
        lines.append(f'<path d="{poly(pts)}" fill="none" stroke="url(#ln)" '
                     f'stroke-width="{2 + 2 * math.sin(t * math.pi):.1f}" stroke-opacity="{0.25 + 0.6 * math.sin(t * math.pi):.2f}"/>')
    return svg(defs, '<rect width="100%" height="100%" fill="url(#bg)"/><rect width="100%" height="100%" fill="url(#g1)"/>\n'
               + "\n".join(lines))


def sunset_surge():
    defs = (lin("bg", [(0, "#1A0B2E", 1), (.6, "#3B0F4A", 1), (1, "#5E1A3D", 1)], x2=0, y2=1)
            + rad("sun", .5, .5, .22, "#FDBA74", .9) + rad("haze", .5, .55, .6, "#F472B6", .35))
    layers = [("#7C3AED", .5), ("#A21CAF", .55), ("#DB2777", .6), ("#F43F5E", .65),
              ("#FB7185", .7), ("#FDBA74", .8)]
    wdefs, waves = layered_waves(layers, H * 0.64, 60, 90, 1.3, 21, "#1A0B2E")
    body = ('<rect width="100%" height="100%" fill="url(#bg)"/><rect width="100%" height="100%" fill="url(#haze)"/>'
            f'<circle cx="{W / 2}" cy="{H * 0.6}" r="{H * 0.2}" fill="url(#sun)"/>\n'
            + waves)
    return svg(defs + wdefs, body)


def frames():
    defs = (lin("bg", [(0, "#05060C", 1), (1, "#0C1022", 1)], x2=0, y2=1)
            + lin("fr", [(0, "#22D3EE", 1), (1, "#A855F7", 1)], x1=0, y1=1, x2=1, y2=0)
            + rad("g1", .5, .5, .5, "#6D7CFF", .22))
    rects = []
    for i in range(22):
        k = 0.06 + (i / 21) ** 1.6 * 1.05
        w, h = W * k, H * k
        rects.append(f'<rect x="{(W - w) / 2:.1f}" y="{(H - h) / 2:.1f}" width="{w:.1f}" height="{h:.1f}" '
                     f'rx="{36 * k + 6:.1f}" fill="none" stroke="url(#fr)" '
                     f'stroke-width="{1.5 + 5 * k:.1f}" stroke-opacity="{0.9 - 0.75 * (i / 21):.2f}"/>')
    wave = wave_points(H * 0.62, 140, 0.8, 0.6, steps=200)
    body = ('<rect width="100%" height="100%" fill="url(#bg)"/><rect width="100%" height="100%" fill="url(#g1)"/>\n'
            + "\n".join(rects)
            + f'\n<path d="{poly(wave)}" fill="none" stroke="#22D3EE" stroke-width="10" stroke-opacity=".9"/>'
            + f'\n<path d="{poly(wave)}" fill="none" stroke="#22D3EE" stroke-width="40" stroke-opacity=".12"/>')
    return svg(defs, body)


def oled():
    defs = lin("ln", [(0, "#22D3EE", 0), (.3, "#22D3EE", 1), (.7, "#A855F7", 1), (1, "#A855F7", 0)])
    wave = poly(wave_points(H * 0.58, 180, 1.0, 2.2, steps=220))
    body = ('<rect width="100%" height="100%" fill="#000000"/>\n'
            f'<path d="{wave}" fill="none" stroke="url(#ln)" stroke-width="70" stroke-opacity=".10"/>\n'
            f'<path d="{wave}" fill="none" stroke="url(#ln)" stroke-width="24" stroke-opacity=".25"/>\n'
            f'<path d="{wave}" fill="none" stroke="url(#ln)" stroke-width="6"/>')
    return svg(defs, body)


WALLPAPERS = {
    # Dateiname: (Anzeigename, Inhalt)
    "frametide-tide-dark.svg": ("Tide (dunkel)", tide(dark=True)),
    "frametide-tide-light.svg": ("Tide (hell)", tide(dark=False)),
    "frametide-tide-logo.svg": ("Tide mit Logo", tide(dark=True, branded=True)),
    "frametide-nightwave.svg": ("Nightwave", nightwave()),
    "frametide-sunset-surge.svg": ("Sunset Surge", sunset_surge()),
    "frametide-frames.svg": ("Frames", frames()),
    "frametide-oled.svg": ("OLED Black", oled()),
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, (title, content) in WALLPAPERS.items():
        with open(os.path.join(OUT, name), "w") as f:
            f.write(content)
        print(f"{name:32} {title}")


if __name__ == "__main__":
    main()
