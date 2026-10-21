"""Síntese de áudio com numpy: efeitos sonoros e trilhas por fase (sem arquivos externos).

Filtros e reverberação usam FFT (sem SciPy). Os resultados são gravados como WAV no cache.
"""
import math
import wave

import numpy as np

SR = 22050


def t_axis(dur):
    return np.arange(int(SR * dur)) / SR


def env(n, a=0.005, d=0.1, s=0.0, r=0.1, total=None):
    """Envelope ADSR simples (em segundos)."""
    total = total or n / SR
    t = np.arange(n) / SR
    e = np.ones(n)
    ai = t < a
    e[ai] = t[ai] / max(a, 1e-4)
    di = (t >= a) & (t < a + d)
    e[di] = 1.0 - (1.0 - s) * (t[di] - a) / max(d, 1e-4)
    si = t >= a + d
    e[si] = s
    if s == 0.0:
        e[si] = 0.0
        e[di] = np.maximum(0, 1.0 - (t[di] - a) / max(d, 1e-4))
    rel = t > total - r
    e[rel] *= np.clip((total - t[rel]) / max(r, 1e-4), 0, 1)
    return e


def expdecay(n, k):
    return np.exp(-np.arange(n) / SR * k)


def noise(n, rng=None):
    rng = rng or np.random.default_rng(1)
    return rng.uniform(-1, 1, n)


def lowpass(x, cutoff, q=0.7):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    h = 1.0 / np.sqrt(1.0 + (f / max(cutoff, 1.0)) ** (4 * q + 1))
    return np.fft.irfft(X * h, len(x))


def highpass(x, cutoff):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    h = 1.0 - 1.0 / np.sqrt(1.0 + (f / max(cutoff, 1.0)) ** 4)
    return np.fft.irfft(X * h, len(x))


def bandpass(x, lo, hi):
    return highpass(lowpass(x, hi), lo)


def reverb(x, seconds=1.6, mix=0.3, damp=3000, seed=3):
    n = int(SR * seconds)
    rng = np.random.default_rng(seed)
    ir = rng.normal(0, 1, n) * np.exp(-np.arange(n) / SR * (6.9 / seconds))
    ir = lowpass(ir, damp)
    ir[0] = 0
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    L = len(x) + n
    nfft = 1 << (L - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[:len(x) + n]
    out = np.zeros(len(x) + n)
    out[:len(x)] += x * (1 - mix)
    out += y * mix * 0.7
    return out


def sweep(f0, f1, dur, wave_="sine"):
    t = t_axis(dur)
    f = f0 * (f1 / f0) ** (t / dur) if f0 > 0 and f1 > 0 else f0 + (f1 - f0) * t / dur
    ph = np.cumsum(f) / SR * 2 * np.pi
    if wave_ == "square":
        return np.sign(np.sin(ph))
    if wave_ == "saw":
        return 2 * ((ph / (2 * np.pi)) % 1.0) - 1
    if wave_ == "tri":
        return 2 * np.abs(2 * ((ph / (2 * np.pi)) % 1.0) - 1) - 1
    return np.sin(ph)


def tone(freq, dur, wave_="sine", detune=0.0):
    t = t_axis(dur)
    ph = 2 * np.pi * freq * (1 + detune) * t
    if wave_ == "saw":
        return 2 * ((freq * (1 + detune) * t) % 1.0) - 1
    if wave_ == "square":
        return np.sign(np.sin(ph))
    if wave_ == "tri":
        return 2 * np.abs(2 * ((freq * t) % 1.0) - 1) - 1
    return np.sin(ph)


def normalize(x, peak=0.9):
    m = np.max(np.abs(x)) + 1e-9
    return x / m * peak


def mixdown(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p
    return out


def pad_to(x, n):
    if len(x) >= n:
        return x[:n]
    return np.concatenate([x, np.zeros(n - len(x))])


def write_wav(path, x, stereo=False):
    x = np.clip(x, -1, 1)
    data = (x * 32000).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


# ---------------------------------------------------------------------------- efeitos
def _swing(pitch=1.0, dur=0.22, weight=1.0, seed=1):
    n = int(SR * dur)
    x = noise(n, np.random.default_rng(seed))
    x = bandpass(x, 300 * pitch, 3000 * pitch)
    e = np.sin(np.linspace(0, np.pi, n)) ** (1.5 / weight)
    return normalize(x * e, 0.6 * weight)


def _impact(freq=90, dur=0.3, crunch=0.5, seed=2):
    n = int(SR * dur)
    body = sweep(freq * 2.2, freq * 0.6, dur) * expdecay(n, 18)
    crack = lowpass(noise(n, np.random.default_rng(seed)), 4000) * expdecay(n, 45) * crunch
    return normalize(body + crack, 0.9)


def _metal(freq=900, dur=0.5, seed=3):
    n = int(SR * dur)
    x = np.zeros(n)
    for k, (m, a) in enumerate(((1.0, 1.0), (2.76, 0.5), (5.4, 0.3), (8.9, 0.2))):
        x += tone(freq * m, dur) * a * expdecay(n, 8 + k * 6)
    x += highpass(noise(n, np.random.default_rng(seed)), 3000) * expdecay(n, 60) * 0.6
    return normalize(x, 0.7)


def _flesh(seed=4):
    n = int(SR * 0.25)
    x = lowpass(noise(n, np.random.default_rng(seed)), 900) * expdecay(n, 20)
    x += sweep(160, 60, 0.25) * expdecay(n, 25) * 0.6
    return normalize(x, 0.85)


def _magic(f0, f1, dur, color="sine", sparkle=True, seed=5):
    n = int(SR * dur)
    x = sweep(f0, f1, dur, color) * env(n, 0.01, dur * 0.4, 0.4, dur * 0.4)
    x += sweep(f0 * 1.5, f1 * 1.5, dur) * 0.4 * env(n, 0.02, dur * 0.4, 0.3, dur * 0.4)
    if sparkle:
        rng = np.random.default_rng(seed)
        x += highpass(noise(n, rng), 5000) * 0.25 * env(n, 0.01, dur * 0.5, 0.2, dur * 0.4)
    return normalize(reverb(x, 0.6, 0.35)[:int(n * 1.6)], 0.7)


def _whoosh(dur=0.5, lo=200, hi=2500, seed=6):
    n = int(SR * dur)
    x = bandpass(noise(n, np.random.default_rng(seed)), lo, hi)
    return normalize(x * np.sin(np.linspace(0, np.pi, n)) ** 2, 0.6)


def _explosion(dur=1.2, seed=7):
    n = int(SR * dur)
    x = lowpass(noise(n, np.random.default_rng(seed)), 600) * expdecay(n, 3.5)
    x += sweep(80, 30, dur) * expdecay(n, 4) * 0.8
    return normalize(reverb(x, 1.0, 0.3), 0.95)


def _howl(dur=1.4, base=300, seed=8):
    t = t_axis(dur)
    f = base * (1 + 0.5 * np.sin(np.pi * t / dur) - 0.1 * t) + 6 * np.sin(2 * np.pi * 6 * t)
    ph = np.cumsum(f) / SR * 2 * np.pi
    x = np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph)
    x *= env(len(t), 0.15, 0.3, 0.8, 0.4)
    x += bandpass(noise(len(t), np.random.default_rng(seed)), 800, 3000) * 0.15 * env(len(t), 0.1, 0.4, 0.5, 0.4)
    return normalize(reverb(x, 1.2, 0.35), 0.8)


def _ui(f, dur=0.06, w="square"):
    n = int(SR * dur)
    return normalize(tone(f, dur, w) * env(n, 0.002, dur * 0.8, 0.0, 0.01) * 0.6, 0.35)


def _chord(freqs, dur, w="sine", decay=2.0):
    n = int(SR * dur)
    x = sum(tone(f, dur, w) for f in freqs) * expdecay(n, decay)
    return normalize(reverb(x, 1.2, 0.35), 0.6)


def _gun(dur=0.4, seed=9, big=False):
    n = int(SR * dur)
    x = noise(n, np.random.default_rng(seed)) * expdecay(n, 30 if not big else 18)
    x = lowpass(x, 3500)
    x += sweep(200, 40, dur) * expdecay(n, 22) * (1.2 if big else 0.8)
    return normalize(reverb(x, 0.5, 0.2), 0.95)


def _blood(seed=10):
    n = int(SR * 0.5)
    x = lowpass(noise(n, np.random.default_rng(seed)), 700) * env(n, 0.02, 0.3, 0.2, 0.15)
    x += sweep(300, 120, 0.5) * 0.3 * expdecay(n, 6)
    return normalize(x, 0.6)


def build_sfx():
    S = {}
    S["swing_light"] = _swing(1.2, 0.18, 0.8)
    S["swing_heavy"] = _swing(0.8, 0.3, 1.1, 2)
    S["swing_charged"] = mixdown(_swing(0.6, 0.38, 1.2, 3), _magic(200, 600, 0.3, sparkle=False) * 0.4)
    S["metal_swing"] = mixdown(_swing(0.7, 0.3, 1.1, 4), _metal(500, 0.3) * 0.2)
    S["holy_swing"] = mixdown(_swing(1.0, 0.25, 1.0, 5), _chord([660, 880], 0.4) * 0.3)
    S["impact"] = _impact(70, 0.45)
    S["bash"] = _impact(110, 0.25, 0.8, 3)
    S["hit_flesh"] = _flesh()
    S["hit_bone"] = mixdown(_impact(300, 0.15, 1.2, 5), highpass(noise(int(SR * 0.12)), 2000) * expdecay(int(SR * 0.12), 30) * 0.5)
    S["hit_metal"] = _metal(1200, 0.4)
    S["hit_stone"] = _impact(140, 0.25, 1.0, 6)
    S["hit_ether"] = _magic(900, 300, 0.25, sparkle=True)
    S["hit_wood"] = _impact(220, 0.18, 0.9, 7)
    S["crit"] = mixdown(_impact(60, 0.4, 1.0, 8), _metal(1800, 0.25) * 0.4)
    S["block"] = _metal(700, 0.35, 9)
    S["parry"] = mixdown(_metal(1500, 0.8, 10), _chord([1320, 1760, 2640], 0.6) * 0.5)
    S["perfect_dodge"] = _magic(400, 1600, 0.35)
    S["posture_break"] = mixdown(_impact(50, 0.6, 0.8, 11), _metal(400, 0.6, 12) * 0.5)
    S["execution"] = mixdown(_flesh(13), _impact(40, 0.7, 1.0, 14), _chord([110, 165], 0.8) * 0.4)
    S["dodge"] = _whoosh(0.25, 300, 2500)
    S["jump"] = _whoosh(0.18, 500, 3000, 7)
    S["land"] = _impact(80, 0.2, 0.4, 15)
    S["death"] = mixdown(_flesh(16), lowpass(noise(int(SR * 0.6)), 400) * expdecay(int(SR * 0.6), 5) * 0.5)
    S["heal"] = _magic(500, 1000, 0.6)
    S["flask"] = mixdown(_ui(880, 0.08, "sine"), _magic(400, 800, 0.4) * 0.6)
    S["buff"] = _magic(300, 900, 0.5)
    S["chest"] = mixdown(_impact(200, 0.2, 0.5), _chord([523, 659, 784, 1046], 1.0) * 0.7)
    S["door"] = normalize(lowpass(noise(int(SR * 1.0)), 300) * env(int(SR * 1.0), 0.1, 0.6, 0.3, 0.3), 0.6)
    S["lever"] = _impact(400, 0.15, 1.0, 17)
    S["dial"] = _impact(500, 0.12, 1.0, 18)
    S["puzzle_solved"] = _chord([392, 494, 587, 784], 1.6, "tri", 1.2)
    S["puzzle_fail"] = _chord([220, 233], 0.6, "square", 4)
    S["grace_found"] = _chord([440, 554, 659, 880, 1108], 2.2, "sine", 0.9)
    S["rest"] = _chord([330, 440, 554], 2.0, "sine", 0.8)
    S["level_up"] = _chord([523, 659, 784, 1046, 1318], 1.5, "tri", 1.2)
    S["item"] = _chord([784, 1046], 0.5, "tri", 4)
    S["ui_move"] = _ui(660, 0.03)
    S["ui_confirm"] = _ui(990, 0.07)
    S["ui_cancel"] = _ui(440, 0.07)
    S["ui_error"] = _ui(180, 0.12, "square")
    S["boss_start"] = _chord([55, 82, 110], 2.5, "saw", 1.0)
    S["boss_defeated"] = _chord([196, 247, 294, 392, 494], 4.0, "sine", 0.5)
    S["player_hurt"] = mixdown(_flesh(19), _impact(90, 0.2, 0.5, 20) * 0.5)
    S["player_death"] = _chord([110, 104, 98], 3.0, "saw", 0.8)
    S["cast_fire"] = mixdown(_whoosh(0.4, 200, 2000, 21), _magic(300, 150, 0.4, sparkle=False) * 0.5)
    S["cast_ice"] = _magic(1600, 2400, 0.4, "tri")
    S["cast_lightning"] = normalize(highpass(noise(int(SR * 0.4)), 1500) * expdecay(int(SR * 0.4), 9) + sweep(800, 100, 0.4, "square") * 0.3 * expdecay(int(SR * 0.4), 8), 0.8)
    S["thunder"] = mixdown(S["cast_lightning"], _explosion(1.0, 22) * 0.6)
    S["cast_arcane"] = _magic(500, 1500, 0.45, "tri")
    S["cast_dark"] = _magic(300, 120, 0.5, "saw")
    S["blink"] = _magic(2000, 400, 0.25)
    S["beam"] = normalize(reverb(sweep(400, 420, 1.2, "saw") * env(int(SR * 1.2), 0.1, 0.5, 0.6, 0.3) * 0.5 + bandpass(noise(int(SR * 1.2)), 800, 3000) * 0.3, 0.8, 0.3), 0.6)
    S["gunshot"] = _gun()
    S["rifle"] = _gun(0.6, 23, True)
    S["reload"] = mixdown(_impact(900, 0.08, 1.0, 24), pad_to(np.zeros(int(SR * 0.25)), int(SR * 0.25)), _impact(700, 0.1, 1.0, 25))
    S["throw"] = _whoosh(0.22, 600, 4000, 26)
    S["claw"] = _swing(1.5, 0.15, 0.7, 27)
    S["claw_heavy"] = mixdown(_swing(1.0, 0.25, 1.0, 28), _flesh(29) * 0.4)
    S["bite"] = mixdown(_flesh(30), _impact(300, 0.1, 1.0, 31) * 0.5)
    S["howl"] = _howl()
    S["growl"] = normalize(lowpass(noise(int(SR * 0.7)), 300) * (0.6 + 0.4 * np.sin(np.arange(int(SR * 0.7)) / SR * 2 * np.pi * 30)) * env(int(SR * 0.7), 0.05, 0.3, 0.5, 0.2), 0.6)
    S["warcry"] = mixdown(_howl(0.9, 160, 32) * 0.7, _impact(50, 0.6, 0.3) * 0.5)
    S["shadow"] = _magic(250, 80, 0.5, "saw")
    S["trap"] = _impact(600, 0.15, 1.0, 33)
    S["storm"] = mixdown(_explosion(1.5, 34) * 0.6, S["cast_lightning"])
    S["blood"] = _blood()
    S["mist"] = _whoosh(0.6, 200, 1500, 35)
    S["whirlwind"] = _whoosh(1.0, 300, 2500, 36)
    S["wind"] = _whoosh(0.5, 500, 4000, 37)
    S["stance"] = _metal(900, 0.4, 38)
    S["ultimate"] = mixdown(_chord([110, 165, 220, 330], 2.0, "saw", 1.5) * 0.6, _explosion(1.2, 39) * 0.5)
    S["explosion"] = _explosion()
    S["bat"] = normalize(sweep(3000, 2200, 0.15, "square") * expdecay(int(SR * 0.15), 20), 0.3)
    S["gears"] = normalize(sum(_impact(800 + i * 40, 0.05, 1.0, 40 + i) for i in range(1)) * 0.5, 0.5)
    S["metal_bite"] = mixdown(_metal(900, 0.2, 41), _impact(200, 0.1))
    S["saw"] = normalize(sweep(900, 1200, 1.0, "saw") * 0.4 * env(int(SR * 1.0), 0.05, 0.3, 0.7, 0.2) + highpass(noise(int(SR * 1.0)), 2000) * 0.2, 0.5)
    S["steam_shot"] = _whoosh(0.35, 800, 5000, 42)
    S["steam"] = normalize(highpass(noise(int(SR * 1.2)), 1200) * env(int(SR * 1.2), 0.05, 0.6, 0.4, 0.4), 0.6)
    S["missiles"] = mixdown(_whoosh(0.8, 300, 3000, 43), _gun(0.3, 44) * 0.4)
    S["pulse"] = normalize(reverb(sweep(80, 200, 0.6, "square") * env(int(SR * 0.6), 0.02, 0.4, 0.2, 0.2), 0.8, 0.3), 0.7)
    S["imp"] = normalize(sweep(800, 1600, 0.2, "square") * expdecay(int(SR * 0.2), 10), 0.3)
    S["pages"] = _whoosh(0.3, 1500, 6000, 45)
    S["summon"] = _magic(150, 500, 0.9, "saw")
    S["ghost"] = _howl(1.0, 520, 46)
    S["scream"] = normalize(bandpass(noise(int(SR * 0.7)), 800, 2500) * env(int(SR * 0.7), 0.05, 0.4, 0.3, 0.2) + sweep(700, 400, 0.7, "saw") * 0.3, 0.6)
    S["spit"] = _whoosh(0.25, 400, 2000, 47)
    S["flesh"] = _blood(48)
    S["flesh_slam"] = mixdown(_impact(60, 0.5, 0.6, 49), _flesh(50))
    S["fuse"] = normalize(highpass(noise(int(SR * 1.6)), 3000) * 0.3, 0.3)
    S["grace"] = _chord([440, 660, 880], 1.5)
    S["holy"] = _chord([523, 784, 1046], 0.9, "tri", 2.5)
    S["wings"] = _whoosh(0.5, 150, 1200, 51)
    S["crossbow"] = mixdown(_impact(700, 0.08, 1.0, 52), _whoosh(0.2, 1000, 5000, 53) * 0.6)
    S["chain"] = mixdown(_metal(1400, 0.2, 54) * 0.5, _swing(1.3, 0.2, 0.8, 55))
    S["warn"] = _ui(1200, 0.08, "square")
    S["alert"] = _ui(700, 0.1, "tri")
    return S


# ---------------------------------------------------------------------------- música
NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def chord_notes(root, kind="m"):
    third = 3 if kind in ("m", "dim") else 4
    fifth = 6 if kind == "dim" else 7
    return [root, root + third, root + fifth]


TRACKS = {
    # tônica (midi), progressão (graus relativos, tipo), bpm, instrumentos, compassos por acorde, caráter
    "titulo": dict(root=50, prog=[(0, "m"), (8, "M"), (3, "M"), (10, "M")], bpm=60, voices=["choir", "pad", "bell", "bass"], bars=2),
    "santuario": dict(root=52, prog=[(0, "m"), (5, "m"), (8, "M"), (7, "M")], bpm=56, voices=["organ", "pad", "bell"], bars=2),
    "ato1": dict(root=45, prog=[(0, "m"), (8, "M"), (5, "m"), (7, "M")], bpm=84, voices=["pad", "harpsi", "bass", "choir"], bars=1, waltz=True),
    "ato2": dict(root=40, prog=[(0, "m"), (1, "M"), (0, "m"), (10, "M")], bpm=96, voices=["bass", "anvil", "pad", "drone"], bars=1),
    "ato3": dict(root=47, prog=[(0, "m"), (1, "M"), (6, "dim"), (0, "m")], bpm=60, voices=["choir", "organ", "drone"], bars=2),
    "ato4": dict(root=54, prog=[(0, "m"), (9, "M"), (5, "M"), (7, "m")], bpm=78, voices=["arp", "pad", "bell", "bass"], bars=1),
    "ato5": dict(root=50, prog=[(0, "m"), (10, "M"), (8, "M"), (7, "M")], bpm=66, voices=["choir", "organ", "bell", "bass"], bars=2),
    "chefe1": dict(root=45, prog=[(0, "m"), (1, "M"), (0, "m"), (7, "M")], bpm=150, voices=["bass", "drums", "pad", "stab"], bars=1),
    "chefe2": dict(root=40, prog=[(0, "m"), (6, "dim"), (0, "m"), (8, "M")], bpm=140, voices=["bass", "drums", "anvil", "stab"], bars=1),
    "chefe3": dict(root=47, prog=[(0, "m"), (1, "M"), (8, "M"), (7, "M")], bpm=132, voices=["choir", "drums", "bass", "stab"], bars=1),
    "chefe4": dict(root=54, prog=[(0, "m"), (8, "M"), (1, "M"), (7, "M")], bpm=144, voices=["arp", "drums", "bass", "stab"], bars=1),
    "chefe5": dict(root=50, prog=[(0, "m"), (8, "M"), (10, "M"), (7, "M"), (0, "m"), (1, "M"), (3, "M"), (7, "M")], bpm=138,
                   voices=["choir", "drums", "bass", "stab", "organ"], bars=1),
    "final": dict(root=48, prog=[(0, "M"), (9, "m"), (5, "M"), (7, "M")], bpm=60, voices=["choir", "pad", "bell", "organ"], bars=2),
    "morte": dict(root=45, prog=[(0, "m"), (8, "M")], bpm=50, voices=["pad", "drone"], bars=2),
}


def _voice(kind, freqs, dur, rng):
    n = int(SR * dur)
    t = np.arange(n) / SR
    out = np.zeros(n)
    if kind == "pad":
        for f in freqs:
            for d in (-0.004, 0.0, 0.005):
                out += (2 * ((f * (1 + d) * t) % 1.0) - 1) * 0.15
        out = lowpass(out, 1200) * env(n, dur * 0.3, dur * 0.3, 0.8, dur * 0.3)
    elif kind == "choir":
        vib = 1 + 0.006 * np.sin(2 * np.pi * 5.0 * t)
        for f in freqs:
            for h, a in ((1, 1.0), (2, 0.5), (3, 0.3), (4, 0.15)):
                out += np.sin(2 * np.pi * f * h * np.cumsum(vib) / SR) * a * 0.12
        out = bandpass(out, 200, 2600) * env(n, dur * 0.35, dur * 0.2, 0.85, dur * 0.35)
    elif kind == "organ":
        for f in freqs:
            for h, a in ((0.5, 0.5), (1, 1.0), (2, 0.6), (3, 0.25), (4, 0.2)):
                out += np.sin(2 * np.pi * f * h * t) * a * 0.08
        out *= env(n, 0.08, 0.2, 0.85, 0.25)
    elif kind == "drone":
        f = freqs[0] / 2
        out = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.5 * t)) * 0.25 * env(n, 0.5, 0.5, 0.9, 0.5)
    elif kind == "bass":
        f = freqs[0] / 2
        out = lowpass((2 * ((f * t) % 1.0) - 1) * 0.4, 400) * env(n, 0.01, 0.4, 0.6, 0.2)
    return out


def build_track(name, seconds=48):
    spec = TRACKS[name]
    import zlib
    rng = np.random.default_rng(zlib.crc32(name.encode()))
    beat = 60.0 / spec["bpm"]
    beats_per_bar = 3 if spec.get("waltz") else 4
    bar = beat * beats_per_bar
    chord_dur = bar * spec["bars"]
    n_chords = max(len(spec["prog"]), int(seconds / chord_dur))
    total = int(SR * chord_dur * n_chords)
    out = np.zeros(total + SR * 2)
    voices = spec["voices"]
    root = spec["root"]
    for ci in range(n_chords):
        deg, kind = spec["prog"][ci % len(spec["prog"])]
        notes = chord_notes(root + deg, "m" if kind == "m" else ("dim" if kind == "dim" else "M"))
        freqs = [midi(n) for n in notes]
        start = int(SR * chord_dur * ci)
        for v in voices:
            if v in ("pad", "choir", "organ", "drone", "bass"):
                seg = _voice(v, [f * (2 if v in ("choir",) else 1) for f in freqs], chord_dur + 0.3, rng)
                if v == "bass" and spec["bpm"] > 120:
                    seg = np.zeros(int(SR * (chord_dur + 0.3)))
                    for b in range(int(chord_dur / (beat / 2))):
                        s = int(SR * b * beat / 2)
                        nb = _voice("bass", freqs, beat / 2, rng)
                        seg[s:s + len(nb)] += nb[:len(seg) - s]
                vol = {"pad": 0.5, "choir": 0.55, "organ": 0.45, "drone": 0.4, "bass": 0.6}[v]
                out[start:start + len(seg)] += seg[:len(out) - start] * vol
            elif v in ("bell", "harpsi", "arp", "stab", "anvil"):
                steps = {"bell": 2, "harpsi": beats_per_bar * spec["bars"] * 2, "arp": beats_per_bar * spec["bars"] * 4,
                         "stab": beats_per_bar * spec["bars"], "anvil": beats_per_bar * spec["bars"]}[v]
                step_dur = chord_dur / steps
                pattern = notes + [notes[0] + 12, notes[1] + 12]
                for s in range(steps):
                    if v == "bell" and rng.random() < 0.3:
                        continue
                    if v == "stab" and s % 2 == 1 and rng.random() < 0.5:
                        continue
                    nn = pattern[(s * (2 if v == "arp" else 1) + ci) % len(pattern)] + (12 if v in ("bell", "arp") else 0)
                    f = midi(nn)
                    d = min(1.5, step_dur * (3 if v == "bell" else 1.2))
                    m = int(SR * d)
                    tt = np.arange(m) / SR
                    if v == "bell":
                        x = (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * f * 2.76 * tt)) * np.exp(-tt * 2.5) * 0.25
                    elif v == "harpsi":
                        x = (2 * ((f * tt) % 1.0) - 1) * np.exp(-tt * 9) * 0.18
                        x = lowpass(x, 3000)
                    elif v == "arp":
                        x = (2 * np.abs(2 * ((f * tt) % 1.0) - 1) - 1) * np.exp(-tt * 7) * 0.2
                    elif v == "stab":
                        x = sum((2 * ((ff * tt) % 1.0) - 1) for ff in freqs) * np.exp(-tt * 10) * 0.12
                        x = lowpass(x, 2200)
                    else:
                        x = (np.sin(2 * np.pi * 1200 * tt) * 0.5 + np.sin(2 * np.pi * 2950 * tt) * 0.3) * np.exp(-tt * 14) * 0.2
                    p = start + int(SR * s * step_dur)
                    out[p:p + m] += x[:max(0, len(out) - p)]
            elif v == "drums":
                steps = beats_per_bar * spec["bars"] * 2
                step_dur = chord_dur / steps
                for s in range(steps):
                    p = start + int(SR * s * step_dur)
                    if s % 4 == 0 or (s % 4 == 3 and rng.random() < 0.4):
                        m = int(SR * 0.3)
                        tt = np.arange(m) / SR
                        k = np.sin(2 * np.pi * np.cumsum(60 + 120 * np.exp(-tt * 30)) / SR) * np.exp(-tt * 10) * 0.7
                        out[p:p + m] += k[:max(0, len(out) - p)]
                    if s % 4 == 2:
                        m = int(SR * 0.2)
                        sn = bandpass(rng.uniform(-1, 1, m), 600, 5000) * np.exp(-np.arange(m) / SR * 18) * 0.35
                        out[p:p + m] += sn[:max(0, len(out) - p)]
                    m = int(SR * 0.05)
                    hh = highpass(rng.uniform(-1, 1, m), 6000) * np.exp(-np.arange(m) / SR * 60) * 0.12
                    out[p:p + m] += hh[:max(0, len(out) - p)]
    out = reverb(out, 2.2 if spec["bpm"] < 100 else 1.2, 0.3 if spec["bpm"] < 100 else 0.18)
    out = out[:total]
    # cruzamento suave no ponto de laço
    fade = int(SR * 1.0)
    out[-fade:] *= np.linspace(1, 0, fade)
    out[:fade] *= np.linspace(0, 1, fade) * 0.5 + 0.5
    return normalize(out, 0.75)
