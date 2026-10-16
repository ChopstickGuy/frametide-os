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


# --------------------------------------------------------------------- Sounds

def startup():
    """Startklang (ca. 3 s): Pad schwillt an, Arpeggio steigt auf, glitzernder Schluss."""
    voices = []
    # Pad: Am(add9) mit langsamem Filter-Sweep und Band-Wobbeln
    for note, pan in (("A2", 0), ("E3", -0.5), ("A3", 0.5), ("C4", -0.3), ("B4", 0.3)):
        voices.append(Voice(hz(note), 0.0, 2.2, voices=4, detune=0.18, cutoff=(250, 1800, 1100),
                            res=0.25, attack=0.9, decay=1.6, sustain=0.75, release=1.1,
                            gain=0.28, vibrato=0.0025, pan=pan))
    # Bass mit Sub
    voices.append(Voice(hz("A2"), 0.0, 2.4, voices=2, detune=0.05, cutoff=(200, 900, 400), res=0.2,
                        attack=0.25, decay=1.2, sustain=0.6, release=0.9, gain=0.45, sub=0.25))
    # Arpeggio (Sechzehntel bei 112 BPM), Ping-Pong im Panorama
    arp = ["A3", "C4", "E4", "A4", "B4", "C5", "E5", "A5"]
    step = 60 / 112 / 4
    for i, note in enumerate(arp):
        voices.append(pluck(note, 0.35 + i * step, dur=0.12, pan=-0.6 if i % 2 else 0.6,
                            gain=1.0, bright=4500 + i * 400, res=0.45))
    # Schluss: heller Lead-Ton mit Glide
    voices.append(Voice(hz("E5"), 0.35 + 8 * step, 0.9, voices=3, detune=0.1, cutoff=(1200, 5200, 2600),
                        res=0.3, attack=0.02, decay=0.6, sustain=0.45, release=0.9, gain=0.45,
                        glide_from=hz("C5"), glide_time=0.08, vibrato=0.006))
    make("desktop-login", 3.6, voices, peak_db=-12, fx_echo=True, room=0.3)


def main():
    random.seed(42)
    os.makedirs(os.path.join(OUT, "stereo"), exist_ok=True)
    for old in os.listdir(os.path.join(OUT, "stereo")):
        os.remove(os.path.join(OUT, "stereo", old))
    with open(os.path.join(OUT, "index.theme"), "w") as f:
        f.write("[Sound Theme]\nName=Frametide\nComment=Synthwave-Systemklänge\n"
                "Inherits=freedesktop\nDirectories=stereo\n\n[stereo]\nOutputProfile=stereo\n")

    startup()
    make("bell", 0.6, [pluck("E5", 0, 0.12, gain=0.9)], fx_echo=True)
    make("message-new-instant", 0.75, [pluck("A4", 0, 0.1, pan=-0.4), pluck("E5", 0.09, 0.16, pan=0.4)],
         fx_echo=True)
    make("complete", 0.9, [pluck("A4", 0.0, 0.1, pan=-0.5), pluck("C5", 0.08, 0.1),
                           pluck("E5", 0.16, 0.1, pan=0.5), pluck("A5", 0.24, 0.2, bright=5200)],
         fx_echo=True)
    make("dialog-warning", 0.7, [pluck("E4", 0, 0.12, wave="square", gain=0.7),
                                 pluck("C4", 0.12, 0.2, wave="square", gain=0.7)])
    make("dialog-error", 0.65, [Voice(hz("A2"), 0, 0.12, voices=3, detune=0.4, cutoff=(400, 2200, 500),
                                      decay=0.12, release=0.05, gain=0.9),
                                Voice(hz("A2"), 0.16, 0.18, voices=3, detune=0.4, cutoff=(400, 2200, 500),
                                      decay=0.18, release=0.05, gain=0.9)])
    make("audio-volume-change", 0.12, [pluck("A5", 0, 0.035, bright=3000, gain=0.6)], room=0.08)
    make("device-added", 0.7, [Voice(hz("A4"), 0, 0.25, cutoff=(500, 4800, 1500), decay=0.25,
                                     glide_from=hz("A3"), glide_time=0.12, gain=0.8)], fx_echo=True)
    make("device-removed", 0.7, [Voice(hz("A3"), 0, 0.25, cutoff=(500, 3600, 700), decay=0.25,
                                       glide_from=hz("A4"), glide_time=0.12, gain=0.8)], fx_echo=True)
    make("power-plug", 0.6, [pluck("E4", 0, 0.08), pluck("B4", 0.07, 0.15)])
    make("power-unplug", 0.6, [pluck("B4", 0, 0.08), pluck("E4", 0.07, 0.15)])
    make("screen-capture", 0.35, noises=[(0, 0.08, 6000, 1500, 0.9)], room=0.12)
    make("trash-empty", 0.7, noises=[(0, 0.45, 7000, 300, 0.7, 9)], room=0.2)


if __name__ == "__main__":
    main()
