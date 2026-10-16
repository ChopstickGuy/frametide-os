#!/usr/bin/env python3
"""Erzeugt das minimalistische Frametide-Sound-Theme (WAV, 48 kHz) nach
artwork/sounds/. Weiche Sinustöne mit sanftem Ein-/Ausklang, leise gemischt
(Spitze -18 dBFS), damit Systemklänge nie aufdringlich wirken.

  python3 artwork/generate-sounds.py
"""
import math
import os
import random
import struct
import wave

RATE = 48000
PEAK = 10 ** (-18 / 20)  # -18 dBFS
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")


def note(name):
    names = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    return 440.0 * 2 ** ((names[name[0]] + 12 * (int(name[1:]) - 4)) / 12)


def tone(freq, dur, start=0.0, decay=6.0, attack=0.006):
    """Sinus mit leichtem Oberton, weichem Einschwingen und exponentiellem Ausklang."""
    def sample(t):
        if t < start or t > start + dur:
            return 0.0
        x = t - start
        env = min(1.0, x / attack) * math.exp(-decay * x) * min(1.0, (start + dur - t) / 0.02)
        return env * (math.sin(2 * math.pi * freq * x) + 0.12 * math.sin(4 * math.pi * freq * x))
    return sample


def noise(dur, start=0.0, decay=30.0, smooth=0.85, seed=1):
    rnd = random.Random(seed)
    state = {"y": 0.0}

    def sample(t):
        if t < start or t > start + dur:
            return 0.0
        state["y"] = smooth * state["y"] + (1 - smooth) * rnd.uniform(-1, 1)
        x = t - start
        return 3.0 * state["y"] * min(1.0, x / 0.003) * math.exp(-decay * x)
    return sample


def render(name, parts, length):
    n = int(RATE * length)
    data = [sum(p(i / RATE) for p in parts) for i in range(n)]
    peak = max(abs(v) for v in data) or 1.0
    frames = b"".join(struct.pack("<h", int(v / peak * PEAK * 32767)) for v in data)
    with wave.open(os.path.join(OUT, "stereo", f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(frames)
    print(f"{name:24} {length:.2f}s")


SOUNDS = {
    # Ereignisname (freedesktop Sound Naming Spec): (Teile, Länge in s)
    "bell":                 ([tone(note("E6"), .25, decay=14)], .28),
    "message-new-instant":  ([tone(note("C6"), .18, decay=12), tone(note("G6"), .3, .09, decay=10)], .42),
    "complete":             ([tone(note("C6"), .16, decay=14), tone(note("E6"), .16, .07, decay=14),
                              tone(note("G6"), .32, .14, decay=9)], .48),
    "dialog-warning":       ([tone(note("G5"), .18, decay=10), tone(note("D5"), .3, .11, decay=8)], .44),
    "dialog-error":         ([tone(note("D5"), .14, decay=14), tone(note("D5"), .22, .14, decay=10)], .38),
    "audio-volume-change":  ([tone(note("A6"), .05, decay=60)], .06),
    "device-added":         ([tone(note("A5"), .16, decay=12), tone(note("E6"), .26, .08, decay=10)], .36),
    "device-removed":       ([tone(note("E6"), .16, decay=12), tone(note("A5"), .26, .08, decay=10)], .36),
    "power-plug":           ([tone(note("G5"), .14, decay=14), tone(note("D6"), .24, .07, decay=10)], .32),
    "power-unplug":         ([tone(note("D6"), .14, decay=14), tone(note("G5"), .24, .07, decay=10)], .32),
    "screen-capture":       ([noise(.07, decay=60, smooth=.6)], .08),
    "trash-empty":          ([noise(.35, decay=9, smooth=.93, seed=7)], .36),
    "desktop-login":        ([tone(note("C5"), 1.1, 0, decay=3), tone(note("E5"), 1.0, .08, decay=3),
                              tone(note("G5"), .95, .16, decay=3), tone(note("B5"), .9, .24, decay=3)], 1.2),
}

INDEX = """[Sound Theme]
Name=Frametide
Comment=Leise, minimalistische Systemklänge
Inherits=freedesktop
Directories=stereo

[stereo]
OutputProfile=stereo
"""


def main():
    os.makedirs(os.path.join(OUT, "stereo"), exist_ok=True)
    with open(os.path.join(OUT, "index.theme"), "w") as f:
        f.write(INDEX)
    for name, (parts, length) in SOUNDS.items():
        render(name, parts, length)


if __name__ == "__main__":
    main()
