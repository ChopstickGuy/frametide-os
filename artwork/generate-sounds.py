#!/usr/bin/env python3
"""Erzeugt das Frametide-Sound-Theme im Synthwave-Stil (Stereo-WAV, 48 kHz) nach
artwork/sounds/ – ohne Abhängigkeiten außer Python 3.

Klangbausteine wie bei klassischen Analog-Synths der 80er:
verstimmte Sägezahn-Oszillatoren, resonanter Tiefpass mit Filter-Hüllkurve,
leichtes Band-Wobbeln, Stereo-Chorus, Echo und Hall.

  python3 artwork/generate-sounds.py
"""
import math
import os
import random
import struct
import wave

RATE = 48000
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")


def hz(note):
    """'A4' -> 440 Hz; Kreuz mit '#', z. B. 'F#3'."""
    names = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    semis = names[note[0]] + (1 if "#" in note else 0)
    octave = int(note.lstrip("ABCDEFG#"))
    return 440.0 * 2 ** ((semis + 12 * (octave - 4)) / 12)


# ------------------------------------------------------------------ Bausteine

class Voice:
    """Ein Synth-Ton: Oszillatoren -> Tiefpass (State-Variable) -> Hüllkurve."""

    def __init__(self, freq, start, dur, wave="saw", detune=0.12, voices=3, cutoff=(800, 4500, 2500),
                 res=0.35, attack=0.004, decay=0.25, sustain=0.0, release=0.12, gain=1.0,
                 glide_from=None, glide_time=0.0, vibrato=0.0, pan=0.0, sub=0.0):
        self.f, self.start, self.dur = freq, start, dur
        self.wave, self.detune, self.voices = wave, detune, voices
        self.cut0, self.cut_peak, self.cut_end = cutoff
        self.res, self.a, self.d, self.s, self.r = res, attack, decay, sustain, release
        self.gain, self.glide_from, self.glide_time = gain, glide_from, glide_time
        self.vibrato, self.pan, self.sub = vibrato, pan, sub
        self.phases = [random.random() for _ in range(voices)]
        self.sub_phase = 0.0
        self.low = self.band = 0.0

    def env(self, t):
        if t < self.a:
            return t / self.a
        if t < self.a + self.d:
            return 1 - (1 - self.s) * (t - self.a) / self.d
        if t < self.dur:
            return self.s
        return self.s * max(0.0, 1 - (t - self.dur) / self.r) if self.s else 0.0

    def length(self):
        return self.dur + (self.r if self.s else 0) + 0.01

    def render(self, out_l, out_r):
        n0 = int(self.start * RATE)
        n = int(self.length() * RATE)
        left, right = math.cos((self.pan + 1) * math.pi / 4), math.sin((self.pan + 1) * math.pi / 4)
        for i in range(n):
            t = i / RATE
            f = self.f
            if self.glide_from and t < self.glide_time:
                f = self.glide_from * (self.f / self.glide_from) ** (t / self.glide_time)
            f *= 1 + self.vibrato * math.sin(2 * math.pi * 5.2 * t) * min(1, t / 0.25)
            # Oszillatoren (leicht verstimmt = breiter Analog-Sound)
            x = 0.0
            for k in range(self.voices):
                spread = (k - (self.voices - 1) / 2) * self.detune / 100 * 12  # in Halbtönen*0.12
                fk = f * 2 ** (spread / 12)
                self.phases[k] = (self.phases[k] + fk / RATE) % 1.0
                p = self.phases[k]
                x += (2 * p - 1) if self.wave == "saw" else (1 if p < 0.5 else -1) if self.wave == "square" \
                    else math.sin(2 * math.pi * p)
            x /= self.voices
            if self.sub:
                self.sub_phase = (self.sub_phase + f / 2 / RATE) % 1.0
                x += self.sub * math.sin(2 * math.pi * self.sub_phase)
            # Filter-Hüllkurve: auf, dann zurück
            fe = math.exp(-t / max(self.d, 0.05))
            cutoff = self.cut_end + (self.cut_peak - self.cut_end) * fe if t > self.a else \
                self.cut0 + (self.cut_peak - self.cut0) * t / self.a
            fc = 2 * math.sin(math.pi * min(cutoff, RATE / 6) / RATE)
            q = 1 - self.res
            self.low += fc * self.band
            high = x - self.low - q * self.band
            self.band += fc * high
            y = self.low * self.env(t) * self.gain
            j = n0 + i
            if j < len(out_l):
                out_l[j] += y * left
                out_r[j] += y * right


def noise_burst(out_l, out_r, start, dur, cutoff_from, cutoff_to, gain=0.5, seed=3):
    rnd = random.Random(seed)
    low = band = 0.0
    n0, n = int(start * RATE), int(dur * RATE)
    for i in range(n):
        t = i / n
        cutoff = cutoff_from * (cutoff_to / cutoff_from) ** t
        fc = 2 * math.sin(math.pi * cutoff / RATE)
        low += fc * band
        high = rnd.uniform(-1, 1) - low - 0.5 * band
        band += fc * high
        env = min(1, i / (0.004 * RATE)) * (1 - t) ** 2
        y = band * env * gain
        if n0 + i < len(out_l):
            out_l[n0 + i] += y
            out_r[n0 + i] += y


def echo(l, r, delay=0.19, feedback=0.32, mix=0.28):
    """Ping-Pong-Echo – typisch für Synthwave."""
    d = int(delay * RATE)
    bl, br = [0.0] * len(l), [0.0] * len(r)
    for i in range(len(l)):
        if i >= d:
            bl[i] = r[i - d] * 0.9 + br[i - d] * feedback
            br[i] = l[i - d] * 0.9 + bl[i - d] * feedback
    return [a + mix * b for a, b in zip(l, bl)], [a + mix * b for a, b in zip(r, br)]


def reverb(sig, size=1.0, mix=0.25, seed=0, damp=0.35, feedback=0.78):
    """Gedämpfter Hall nach Freeverb-Art (6 Kamm- + 2 Allpassfilter) – warm statt metallisch."""
    combs = [int((x + seed * 23) * size) for x in (1116, 1188, 1277, 1356, 1422, 1491)]
    out = [0.0] * len(sig)
    for c in combs:
        buf, idx, store = [0.0] * c, 0, 0.0
        for i, x in enumerate(sig):
            y = buf[idx]
            store = y * (1 - damp) + store * damp
            buf[idx] = x + store * feedback
            idx = (idx + 1) % c
            out[i] += y / len(combs)
    for c in (225 + seed * 7, 556 + seed * 11):
        buf, idx = [0.0] * c, 0
        for i, x in enumerate(out):
            b = buf[idx]
            buf[idx] = x + b * 0.5
            out[i] = b - x
            idx = (idx + 1) % c
    return [a * (1 - mix) + b * mix for a, b in zip(sig, out)]


def finish(name, l, r, peak_db=-16.0, fx_echo=False, room=0.22):
    if fx_echo:
        l, r = echo(l, r)
    l, r = reverb(l, mix=room, seed=0), reverb(r, mix=room, seed=1)
    # sanftes Ausblenden der letzten 30 ms, damit nichts knackt
    fade = int(0.03 * RATE)
    for i in range(fade):
        l[-1 - i] *= i / fade
        r[-1 - i] *= i / fade
    peak = max(max(abs(x) for x in l), max(abs(x) for x in r)) or 1.0
    scale = 10 ** (peak_db / 20) / peak
    frames = b"".join(struct.pack("<hh", int(a * scale * 32767), int(b * scale * 32767)) for a, b in zip(l, r))
    with wave.open(os.path.join(OUT, "stereo", f"{name}.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(frames)
    print(f"{name:24} {len(l) / RATE:.2f}s")


def make(name, length, voices=(), noises=(), **kw):
    n = int(length * RATE)
    l, r = [0.0] * n, [0.0] * n
    for v in voices:
        v.render(l, r)
    for args in noises:
        noise_burst(l, r, *args)
    finish(name, l, r, **kw)


def pluck(note, start, dur=0.14, pan=0.0, gain=1.0, bright=4200, **kw):
    return Voice(hz(note), start, dur, cutoff=(900, bright, 900), decay=dur, release=0.05,
                 pan=pan, gain=gain, **kw)


# ------------------------------------------------------- weiche Klangbausteine

def soft_tone(out_l, out_r, freq, start, dur, gain=1.0, pan=0.0, attack=0.012, cutoff=1400.0,
              partials=((1.0, 1.0), (2.0, 0.18), (3.9, 0.06)), glide_to=None):
    """Weicher, marimbaartiger Ton: Sinus + wenige leise Obertöne, sanfter Einsatz,
    exponentielles Ausklingen, Tiefpass gegen jede Schärfe."""
    n0, n = int(start * RATE), int(dur * RATE)
    left, right = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    phases = [0.0] * len(partials)
    low = 0.0
    a = 1 - math.exp(-2 * math.pi * cutoff / RATE)
    for i in range(n):
        t = i / RATE
        f = freq if glide_to is None else freq * (glide_to / freq) ** min(1.0, t / (dur * 0.6))
        x = 0.0
        for k, (mult, amp) in enumerate(partials):
            phases[k] += 2 * math.pi * f * mult / RATE
            # höhere Teiltöne klingen schneller aus → warm statt klirrend
            x += amp * math.sin(phases[k]) * math.exp(-t * (3.5 + 6 * (mult - 1)))
        env = min(1.0, t / attack) * math.exp(-t * 4.0 / dur) * min(1.0, (dur - t) / 0.03)
        low += a * (x * env - low)
        y = low * gain
        if n0 + i < len(out_l):
            out_l[n0 + i] += y * left
            out_r[n0 + i] += y * right


def pad(out_l, out_r, freqs, start, dur, gain=0.5, attack=1.2, release=1.6, cutoff=700.0):
    """Warmer Flächenklang aus leicht verstimmten Sinus-/Dreieckswellen."""
    n0, n = int(start * RATE), int((dur + release) * RATE)
    a = 1 - math.exp(-2 * math.pi * cutoff / RATE)
    for idx, f0 in enumerate(freqs):
        pan = (idx / max(1, len(freqs) - 1)) * 1.2 - 0.6
        left, right = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        p1 = p2 = 0.0
        low = 0.0
        for i in range(n):
            t = i / RATE
            p1 += 2 * math.pi * f0 * 1.0015 / RATE
            p2 += 2 * math.pi * f0 * 0.9985 / RATE
            tri = 2 / math.pi * math.asin(math.sin(p2))
            x = 0.6 * math.sin(p1) + 0.4 * tri
            env = min(1.0, t / attack) if t < dur else max(0.0, 1 - (t - dur) / release)
            low += a * (x * env - low)
            y = low * gain / len(freqs)
            if n0 + i < len(out_l):
                out_l[n0 + i] += y * left
                out_r[n0 + i] += y * right


def ocean_wave(out_l, out_r, start, dur, gain=0.6, seed=11, low_hz=180.0, high_hz=1100.0):
    """Meereswelle: rosa Rauschen, dessen Lautstärke und Helligkeit an- und abschwillt."""
    rnd = random.Random(seed)
    n0, n = int(start * RATE), int(dur * RATE)
    b = [0.0] * 3
    lows = [0.0, 0.0]
    for i in range(n):
        t = i / n
        w = rnd.uniform(-1, 1)
        # einfaches Rosa-Rauschen (Paul Kellet, gekürzt)
        b[0] = 0.997 * b[0] + 0.029591 * w
        b[1] = 0.985 * b[1] + 0.032534 * w
        b[2] = 0.950 * b[2] + 0.048056 * w
        pink = b[0] + b[1] + b[2] + 0.05 * w
        swell = math.sin(math.pi * min(1.0, t * 1.15)) ** 2           # anrollen, brechen, auslaufen
        cutoff = low_hz + (high_hz - low_hz) * swell
        a = 1 - math.exp(-2 * math.pi * cutoff / RATE)
        for ch in (0, 1):
            lows[ch] += a * (pink * (0.92 if ch else 1.0) - lows[ch])
        if n0 + i < len(out_l):
            out_l[n0 + i] += lows[0] * swell * gain
            out_r[n0 + i] += lows[1] * swell * gain


def make_soft(name, length, parts, peak_db=-18.0, room=0.30, fx_echo=False):
    n = int(length * RATE)
    l, r = [0.0] * n, [0.0] * n
    for fn, args, kw in parts:
        fn(l, r, *args, **kw)
    finish(name, l, r, peak_db=peak_db, fx_echo=fx_echo, room=room)


def T(*args, **kw):
    return (soft_tone, args, kw)


# --------------------------------------------------------------------- Sounds

def main():
    random.seed(42)
    os.makedirs(os.path.join(OUT, "stereo"), exist_ok=True)
    for old in os.listdir(os.path.join(OUT, "stereo")):
        os.remove(os.path.join(OUT, "stereo", old))
    with open(os.path.join(OUT, "index.theme"), "w") as f:
        f.write("[Sound Theme]\nName=Frametide\nComment=Ruhige Systemklänge mit Meereswelle\n"
                "Inherits=freedesktop\nDirectories=stereo\n\n[stereo]\nOutputProfile=stereo\n")

    # Startklang (ca. 4,5 s): Welle rollt heran, darüber ein warmer, tiefer Akkord und drei weiche Töne
    make_soft("desktop-login", 4.6, [
        (ocean_wave, (0.0, 4.4), {"gain": 0.55}),
        (pad, ([hz("F2"), hz("C3"), hz("A3"), hz("E4")], 0.3, 2.4), {"gain": 0.9, "attack": 1.4, "release": 1.8}),
        T(hz("A3"), 0.9, 1.6, gain=0.55, pan=-0.3),
        T(hz("C4"), 1.25, 1.6, gain=0.5, pan=0.3),
        T(hz("E4"), 1.6, 2.2, gain=0.45, cutoff=1200),
    ], peak_db=-14, room=0.38)

    # Kurz, tief, leise – nichts davon soll „im Ohr wehtun“ (alle Grundtöne unter 400 Hz)
    make_soft("audio-volume-change", 0.16, [T(hz("A3"), 0, 0.12, cutoff=1000,
                                             partials=((1.0, 1.0), (2.0, 0.25)))], peak_db=-21, room=0.10)
    make_soft("bell", 0.45, [T(hz("A3"), 0, 0.35, cutoff=800)], peak_db=-24, room=0.2)
    make_soft("message-new-instant", 1.0, [T(hz("C4"), 0, 0.5, pan=-0.3), T(hz("G3"), 0.14, 0.7, pan=0.3,
                                                                          cutoff=1100)], peak_db=-18)
    make_soft("complete", 1.3, [T(hz("F3"), 0, 0.6, pan=-0.4), T(hz("A3"), 0.12, 0.6),
                                T(hz("C4"), 0.24, 0.9, pan=0.4)], peak_db=-18)
    make_soft("dialog-warning", 1.0, [T(hz("A3"), 0, 0.5), T(hz("F3"), 0.16, 0.7)], peak_db=-18)
    make_soft("dialog-error", 0.9, [T(hz("D3"), 0, 0.4, cutoff=700), T(hz("D3"), 0.2, 0.6, cutoff=700)],
              peak_db=-17)
    make_soft("device-added", 1.0, [T(hz("G3"), 0, 0.8, glide_to=hz("D4"), cutoff=1000)], peak_db=-18)
    make_soft("device-removed", 1.0, [T(hz("D4"), 0, 0.8, glide_to=hz("G3"), cutoff=1000)], peak_db=-18)
    make_soft("power-plug", 0.9, [T(hz("C3"), 0, 0.4), T(hz("G3"), 0.12, 0.6)], peak_db=-18)
    make_soft("power-unplug", 0.9, [T(hz("G3"), 0, 0.4), T(hz("C3"), 0.12, 0.6)], peak_db=-18)
    make_soft("screen-capture", 0.5, [(ocean_wave, (0.0, 0.25), {"gain": 0.9, "low_hz": 400, "high_hz": 1600})],
              peak_db=-20, room=0.15)
    make_soft("trash-empty", 1.2, [(ocean_wave, (0.0, 1.0), {"gain": 0.9, "seed": 5})], peak_db=-18)


if __name__ == "__main__":
    main()
