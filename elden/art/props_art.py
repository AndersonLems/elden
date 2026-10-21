"""Sprites procedurais de cenário e objetos interativos (com estados: aberto/fechado, aceso/apagado...)."""
import math
import zlib

import numpy as np
from PIL import Image, ImageDraw

from .pixel import outline, hexc
from .rig import EMISSIVE_A


def _img(w, h):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def C(h, a=255):
    r, g, b = hexc(h) if isinstance(h, str) else h
    return (r, g, b, a)


def E(h):
    """Cor emissiva (alfa especial que o shader faz brilhar)."""
    return C(h, EMISSIVE_A)


def fin(im, outl=True):
    a = np.array(im)
    if outl:
        em = a[..., 3] == EMISSIVE_A
        a2 = a.copy()
        a2[em, 3] = 255
        a2 = outline(a2, (16, 12, 18))
        a2[em, 3] = EMISSIVE_A
        a = a2
    return a


def shade(im):
    """Sombreamento simples: escurece a metade inferior/direita de cada pixel opaco."""
    a = np.array(im).astype(np.float32)
    h, w = a.shape[:2]
    gy = np.linspace(1.12, 0.78, h)[:, None]
    gx = np.linspace(1.05, 0.9, w)[None, :]
    m = a[..., 3] == 255
    for c in range(3):
        a[..., c] = np.where(m, a[..., c] * gy * gx, a[..., c])
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")


def rng_for(name):
    return np.random.default_rng(zlib.crc32(name.encode()))


# ---------------------------------------------------------------------------- vegetação
def tree_twisted(seed="t"):
    rng = rng_for(seed)
    im, d = _img(48, 72)
    bark = [C("#2a1a14"), C("#3a2418"), C("#4a3020")]
    x = 24
    for y in range(70, 30, -1):
        x += rng.integers(-1, 2) * (1 if y < 60 else 0)
        w = 3 + (70 - y) * 0 + max(0, (y - 40) // 8)
        d.rectangle([x - w, y, x + w, y], fill=bark[(y // 3) % 2])
    # galhos retorcidos
    for k in range(6):
        sx, sy = x + rng.integers(-2, 3), 30 + rng.integers(0, 18)
        ang = rng.uniform(-2.6, -0.5) if k % 2 else rng.uniform(-2.6 + math.pi, -0.5 + math.pi)
        ang = rng.uniform(math.pi * 1.05, math.pi * 1.95)
        L = rng.integers(10, 20)
        px, py = sx, sy
        for i in range(L):
            ang += rng.uniform(-0.35, 0.35)
            nx, ny = px + math.cos(ang) * 1.2, py + math.sin(ang) * 1.2
            d.line([px, py, nx, ny], fill=bark[2 if i < 4 else 1], width=2 if i < L // 2 else 1)
            px, py = nx, ny
    # folhas mortas vermelhas esparsas
    for _ in range(60):
        lx, ly = x + rng.normal(0, 11), 22 + rng.normal(0, 9)
        c = C("#5a1018") if rng.random() < 0.6 else C("#7a1a22")
        d.point((lx, ly), fill=c)
        if rng.random() < 0.4:
            d.point((lx + 1, ly), fill=c)
    return [fin(shade(im))]


def tree_dead(seed="d"):
    rng = rng_for(seed)
    im, d = _img(40, 64)
    bark = [C("#3a3230"), C("#4a423c"), C("#5a524a")]
    x = 20
    for y in range(62, 24, -1):
        w = 2 + max(0, (y - 44) // 7)
        d.rectangle([x - w, y, x + w, y], fill=bark[(y // 4) % 2])
    for k in range(5):
        sy = 24 + k * 5
        sgn = 1 if k % 2 else -1
        d.line([x, sy, x + sgn * rng.integers(7, 14), sy - rng.integers(5, 12)], fill=bark[2], width=2)
        d.line([x + sgn * 6, sy - 4, x + sgn * 10, sy - 12], fill=bark[1], width=1)
    return [fin(shade(im))]


# ---------------------------------------------------------------------------- cemitério e castelo
def tombstone(seed="g"):
    rng = rng_for(seed)
    im, d = _img(16, 20)
    st = [C("#4a4858"), C("#5e5c6c"), C("#7a788a")]
    kind = rng.integers(0, 3)
    if kind == 0:
        d.rounded_rectangle([3, 4, 12, 19], 4, fill=st[1])
    elif kind == 1:
        d.rectangle([4, 6, 11, 19], fill=st[1])
        d.polygon([(4, 6), (11, 6), (7.5, 2)], fill=st[1])
    else:
        d.rectangle([2, 8, 13, 19], fill=st[0])
        d.rectangle([3, 9, 12, 18], fill=st[1])
    d.line([6, 9, 9, 9], fill=st[0])
    d.line([7, 8, 7, 12], fill=st[0])
    for _ in range(4):
        d.point((rng.integers(3, 12), rng.integers(10, 19)), fill=C("#3a5a3a"))
    return [fin(shade(im))]


def cross():
    im, d = _img(16, 24)
    d.rectangle([7, 3, 9, 23], fill=C("#4a3a30"))
    d.rectangle([3, 7, 13, 9], fill=C("#4a3a30"))
    return [fin(shade(im))]


def coffin():
    im, d = _img(20, 20)
    d.polygon([(6, 2), (14, 2), (17, 7), (14, 19), (6, 19), (3, 7)], fill=C("#3a2418"))
    d.line([10, 5, 10, 14], fill=C("#8a7040"))
    d.line([7, 8, 13, 8], fill=C("#8a7040"))
    return [fin(shade(im))]


def statue(color="#7a7882", seed="s", kind="knight"):
    im, d = _img(28, 48)
    c1, c2 = C(color), C("#5a5862")
    d.rectangle([6, 40, 21, 47], fill=c2)
    d.rectangle([9, 18, 18, 40], fill=c1)
    d.ellipse([10, 9, 17, 17], fill=c1)
    if kind == "knight":
        d.line([20, 10, 20, 40], fill=C("#9a98a2"), width=2)
        d.rectangle([5, 22, 9, 34], fill=c2)
    elif kind == "angel":
        d.polygon([(9, 20), (1, 8), (4, 26)], fill=c1)
        d.polygon([(18, 20), (26, 8), (23, 26)], fill=c1)
        d.arc([8, 4, 19, 10], 180, 360, fill=E("#ffe090"))
    elif kind == "king":
        d.polygon([(10, 9), (11, 5), (13, 8), (14, 4), (15, 8), (17, 5), (17, 9)], fill=C("#a08a40"))
    return [fin(shade(im))]


def king_statue_states():
    """Estátua de rei com 4 orientações (sul, leste, norte, oeste)."""
    frames = []
    for k in range(4):
        im, d = _img(28, 48)
        c1, c2 = C("#7a7882"), C("#5a5862")
        d.rectangle([6, 40, 21, 47], fill=c2)
        d.rectangle([9, 18, 18, 40], fill=c1)
        d.ellipse([10, 9, 17, 17], fill=c1)
        d.polygon([(10, 9), (11, 5), (13, 8), (14, 4), (15, 8), (17, 5), (17, 9)], fill=C("#a08a40"))
        # olhos indicam a direção
        if k == 0:
            d.point((12, 13), fill=E("#80c0ff"))
            d.point((15, 13), fill=E("#80c0ff"))
        elif k == 1:
            d.point((16, 13), fill=E("#80c0ff"))
            d.line([18, 24, 24, 24], fill=c1, width=2)
        elif k == 3:
            d.point((11, 13), fill=E("#80c0ff"))
            d.line([3, 24, 9, 24], fill=c1, width=2)
        else:
            d.rectangle([10, 20, 17, 30], fill=C("#6a6872"))
        frames.append(fin(shade(im)))
    return frames


def pillar(broken=False):
    im, d = _img(24, 64)
    c = [C("#4a4858"), C("#62606e"), C("#7c7a88")]
    d.rectangle([4, 56, 19, 63], fill=c[0])
    top = 24 if broken else 4
    d.rectangle([6, top, 17, 56], fill=c[1])
    for x in (8, 11, 14):
        d.line([x, top + 2, x, 54], fill=c[0])
    if broken:
        d.polygon([(6, top), (10, top - 5), (13, top - 1), (17, top - 6), (17, top)], fill=c[1])
    else:
        d.rectangle([4, 4, 19, 8], fill=c[2])
    return [fin(shade(im))]


def banner(color="#7a1a24"):
    im, d = _img(16, 40)
    d.line([1, 2, 14, 2], fill=C("#6a5030"), width=2)
    d.polygon([(3, 3), (12, 3), (12, 34), (7.5, 30), (3, 34)], fill=C(color))
    d.ellipse([5, 10, 10, 15], fill=C("#c0a040"))
    return [fin(shade(im))]


def armor_stand():
    im, d = _img(20, 32)
    d.line([10, 6, 10, 31], fill=C("#5a4030"), width=2)
    d.rectangle([5, 9, 15, 20], fill=C("#7a7e88"))
    d.ellipse([7, 2, 13, 8], fill=C("#8a8e98"))
    d.rectangle([4, 9, 6, 13], fill=C("#8a8e98"))
    d.rectangle([14, 9, 16, 13], fill=C("#8a8e98"))
    return [fin(shade(im))]


def urn():
    im, d = _img(14, 16)
    d.ellipse([2, 4, 11, 15], fill=C("#6a4a3a"))
    d.rectangle([4, 1, 9, 5], fill=C("#5a3a2a"))
    d.line([3, 9, 10, 9], fill=C("#a08050"))
    return [fin(shade(im))]


def barrel():
    im, d = _img(16, 18)
    d.rounded_rectangle([2, 1, 13, 17], 3, fill=C("#6a4426"))
    for y in (4, 13):
        d.line([2, y, 13, y], fill=C("#3a3a40"))
    d.line([7, 2, 7, 16], fill=C("#5a381e"))
    return [fin(shade(im))]


def crate():
    im, d = _img(16, 16)
    d.rectangle([1, 2, 14, 15], fill=C("#7a5a32"))
    d.rectangle([1, 2, 14, 15], outline=C("#4a3420"))
    d.line([1, 2, 14, 15], fill=C("#4a3420"))
    return [fin(shade(im))]


# ---------------------------------------------------------------------------- luzes
def brazier(color="#ff8030", base="#4a4048"):
    frames = []
    for k in range(4):
        im, d = _img(20, 28)
        d.polygon([(3, 12), (16, 12), (13, 18), (6, 18)], fill=C(base))
        d.rectangle([8, 18, 11, 26], fill=C(base))
        d.rectangle([5, 25, 14, 27], fill=C(base))
        flame(d, 9.5, 12, 8 + (k % 2), color, k)
        frames.append(fin(shade(im)))
    return frames


def flame(d, cx, by, h, color, k):
    cols = [E("#ffe8a0"), E(color), E("#c03010")]
    rng = np.random.default_rng(k + 7)
    for i, c in enumerate(reversed(cols)):
        w = (3 - i) * 1.4 + 1
        hh = h * (1.0 - i * 0.25)
        pts = [(cx - w, by), (cx + w, by), (cx + rng.uniform(-1.5, 1.5), by - hh)]
        d.polygon(pts, fill=c)


def candelabra(color="#ffd080"):
    frames = []
    for k in range(4):
        im, d = _img(20, 32)
        d.line([10, 10, 10, 31], fill=C("#8a7040"), width=1)
        d.line([4, 14, 16, 14], fill=C("#8a7040"))
        d.rectangle([7, 29, 13, 31], fill=C("#8a7040"))
        for x in (4, 10, 16):
            d.rectangle([x - 1, 10 if x == 10 else 12, x, 14], fill=C("#e8e0d0"))
            d.point((x - 0.5 + (k % 2) * 0.5, 8 if x == 10 else 10), fill=E(color))
            d.point((x - 0.5, 9 if x == 10 else 11), fill=E("#ffffff"))
        frames.append(fin(im))
    return frames


def lamp_post():
    frames = []
    for k in range(2):
        im, d = _img(16, 48)
        d.line([8, 10, 8, 47], fill=C("#2a2a30"), width=2)
        d.rectangle([4, 44, 12, 47], fill=C("#2a2a30"))
        d.polygon([(4, 4), (12, 4), (13, 12), (3, 12)], fill=C("#2a2a30"))
        d.rectangle([5, 5, 11, 11], fill=E("#ffc060" if k == 0 else "#ffd080"))
        frames.append(fin(im))
    return frames


def wall_torch():
    frames = []
    for k in range(4):
        im, d = _img(12, 28)
        d.line([6, 14, 6, 26], fill=C("#4a3020"), width=2)
        flame(d, 6, 14, 7 + (k % 2), "#ff8030", k)
        frames.append(fin(im))
    return frames


def campfire():
    frames = []
    for k in range(4):
        im, d = _img(24, 24)
        for a in (-0.5, 0.0, 0.5):
            d.line([12 - math.cos(a) * 9, 22, 12 + math.cos(a) * 9, 20], fill=C("#4a2a18"), width=2)
        flame(d, 12, 20, 12 + (k % 2) * 2, "#ff7020", k)
        frames.append(fin(im))
    return frames


def lantern():
    frames = []
    for k in range(2):
        im, d = _img(12, 20)
        d.line([6, 0, 6, 4], fill=C("#3a3030"))
        d.rectangle([3, 4, 8, 12], fill=C("#3a3030"))
        d.rectangle([4, 5, 7, 11], fill=E("#ffc060"))
        frames.append(fin(im))
    return frames


def blood_candle():
    frames = []
    for k in range(3):
        im, d = _img(10, 16)
        d.rectangle([3, 7, 6, 15], fill=C("#6a0a14"))
        d.polygon([(3, 7), (6, 7), (4.5, 3 - k % 2)], fill=E("#ff3040"))
        frames.append(fin(im))
    return frames


# ---------------------------------------------------------------------------- interativos
def grace_flame():
    """Graça: chama dourada sobre um altar de pedra (animada)."""
    frames = []
    for k in range(6):
        im, d = _img(32, 48)
        d.polygon([(6, 40), (26, 40), (23, 46), (9, 46)], fill=C("#5a5048"))
        d.rectangle([10, 34, 22, 40], fill=C("#6a6058"))
        rng = np.random.default_rng(k)
        for i, c in enumerate((E("#ffb040"), E("#ffd070"), E("#fff4c0"))):
            w = 7 - i * 2
            h = 26 - i * 6 + (k % 3)
            pts = [(16 - w, 35), (16 + w, 35)]
            for j in range(5):
                pts.append((16 + rng.uniform(-w, w) * (1 - j / 5), 35 - h * (j + 1) / 5))
            d.polygon(pts, fill=c)
        for _ in range(6):
            d.point((16 + rng.normal(0, 5), 30 - rng.uniform(0, 26)), fill=E("#ffe8a0"))
        frames.append(fin(im, outl=False))
    return frames


def chest():
    frames = []
    for opened in (0, 1):
        im, d = _img(20, 18)
        d.rectangle([2, 7, 17, 17], fill=C("#6a4422"))
        d.rectangle([2, 7, 17, 17], outline=C("#a08040"))
        if opened:
            d.polygon([(2, 7), (17, 7), (16, 1), (3, 1)], fill=C("#5a3a1e"))
            d.rectangle([4, 7, 15, 9], fill=E("#ffd070"))
        else:
            d.rectangle([1, 3, 18, 8], fill=C("#7a4e26"))
            d.rectangle([8, 7, 11, 10], fill=C("#c0a040"))
        frames.append(fin(shade(im)))
    return frames


def gate_iron(w=48, h=48, color="#3a3a42"):
    im, d = _img(w, h)
    c = C(color)
    d.rectangle([0, 0, w - 1, 3], fill=c)
    for x in range(2, w, 5):
        d.line([x, 0, x, h - 1], fill=c, width=2)
        d.polygon([(x - 1, h - 1), (x + 2, h - 1), (x + 0.5, h - 4)], fill=C("#5a5a62"))
    d.line([0, h // 2, w - 1, h // 2], fill=c, width=2)
    return [fin(shade(im))]


def door_red():
    im, d = _img(16, 48)
    d.rectangle([1, 4, 14, 47], fill=C("#5a0a14"))
    d.rectangle([1, 4, 14, 47], outline=C("#c0a040"))
    d.ellipse([10, 26, 12, 28], fill=C("#d0b050"))
    return [fin(shade(im))]


def secret_wall():
    im, d = _img(16, 48)
    rng = rng_for("sw")
    for y in range(0, 48, 4):
        off = 4 if (y // 4) % 2 else 0
        for x in range(-off, 16, 8):
            d.rectangle([x + 1, y + 1, x + 7, y + 3], fill=C("#62606e"))
    for _ in range(6):
        x, y = rng.integers(2, 14), rng.integers(4, 44)
        d.line([x, y, x + rng.integers(-3, 4), y + 4], fill=C("#2a2830"))
    return [fin(shade(im))]


def cracked_wall_brick():
    return secret_wall()


def fog_gate(w=48, h=48):
    frames = []
    for k in range(4):
        im, d = _img(w, h)
        rng = np.random.default_rng(k)
        for _ in range(220):
            x, y = rng.integers(0, w), rng.integers(0, h)
            if rng.random() < 0.5:
                d.point((x, y), fill=C("#d0c8e0", 120 if rng.random() < 0.4 else 255))
        frames.append(np.array(im))
    return frames


def blood_seal(w=16, h=48):
    frames = []
    for k in range(3):
        im, d = _img(w, h)
        rng = np.random.default_rng(k + 3)
        for _ in range(140):
            d.point((rng.integers(0, w), rng.integers(0, h)), fill=E("#c01020"))
        frames.append(np.array(im))
    return frames


def lever():
    frames = []
    for on in (0, 1):
        im, d = _img(16, 20)
        d.rectangle([3, 14, 12, 19], fill=C("#4a4048"))
        tip = (13, 4) if on else (3, 4)
        d.line([7.5, 15, tip[0], tip[1]], fill=C("#6a5040"), width=2)
        d.ellipse([tip[0] - 2, tip[1] - 2, tip[0] + 2, tip[1] + 2], fill=C("#a03030") if not on else E("#40e070"))
        frames.append(fin(shade(im)))
    return frames


def plate():
    frames = []
    for on in (0, 1):
        im, d = _img(16, 10)
        d.rectangle([1, 3 + on, 14, 9], fill=C("#6a6878"))
        d.rectangle([3, 4 + on, 12, 7 + on], fill=E("#60c0ff") if on else C("#4a4858"))
        frames.append(fin(im))
    return frames


MOON_SYMBOLS = ["lua_nova", "crescente", "cheia", "minguante"]


def moon_dial():
    frames = []
    for k in range(4):
        im, d = _img(20, 28)
        d.rectangle([4, 14, 15, 27], fill=C("#4a4858"))
        d.ellipse([2, 1, 17, 16], fill=C("#5e5c6c"))
        c = E("#d0d8ff")
        if k == 0:
            d.ellipse([6, 5, 13, 12], outline=c)
        elif k == 1:
            d.pieslice([6, 5, 13, 12], 270, 90, fill=c)
        elif k == 2:
            d.ellipse([6, 5, 13, 12], fill=c)
        else:
            d.pieslice([6, 5, 13, 12], 90, 270, fill=c)
        frames.append(fin(shade(im)))
    return frames


def symbol_dial(symbols, color="#c0a040"):
    """Mostrador genérico com N símbolos simples (formas)."""
    frames = []
    for k in range(len(symbols)):
        im, d = _img(20, 28)
        d.rectangle([4, 14, 15, 27], fill=C("#4a4858"))
        d.ellipse([2, 1, 17, 16], fill=C("#5e5c6c"))
        c = E(color)
        shape = k % 6
        if shape == 0:
            d.ellipse([6, 5, 13, 12], outline=c)
        elif shape == 1:
            d.polygon([(9.5, 4), (14, 12), (5, 12)], outline=c)
        elif shape == 2:
            d.rectangle([6, 5, 13, 12], outline=c)
        elif shape == 3:
            d.line([5, 8, 14, 8], fill=c)
            d.line([9.5, 4, 9.5, 13], fill=c)
        elif shape == 4:
            d.polygon([(9.5, 4), (14, 8.5), (9.5, 13), (5, 8.5)], outline=c)
        else:
            d.line([5, 5, 14, 12], fill=c)
            d.line([14, 5, 5, 12], fill=c)
        frames.append(fin(shade(im)))
    return frames


def mirror():
    frames = []
    for k in range(4):
        im, d = _img(20, 28)
        d.rectangle([8, 18, 11, 27], fill=C("#5a4a3a"))
        d.rectangle([4, 25, 15, 27], fill=C("#5a4a3a"))
        if k % 2 == 0:
            pts = [(3, 18), (6, 20), (16, 4), (13, 2)]
        else:
            pts = [(13, 18), (16, 16), (6, 2), (3, 4)]
        d.polygon(pts, fill=C("#a8c0d8"))
        d.line([pts[0], pts[2]], fill=E("#e0f0ff"))
        frames.append(fin(shade(im)))
    return frames


def crystal(color="#80c0ff"):
    frames = []
    for on in (0, 1):
        im, d = _img(16, 28)
        d.rectangle([3, 22, 12, 27], fill=C("#4a4858"))
        pts = [(8, 1), (13, 10), (11, 22), (5, 22), (3, 10)]
        d.polygon(pts, fill=E(color) if on else C("#4a5a6a"))
        d.line([8, 2, 8, 21], fill=E("#ffffff") if on else C("#6a7a8a"))
        frames.append(fin(im))
    return frames


def emitter(kind="moon_shaft"):
    frames = []
    for k in range(2):
        im, d = _img(20, 32)
        d.rectangle([4, 20, 15, 31], fill=C("#4a4858"))
        d.ellipse([3, 4, 16, 20], fill=C("#5e5c6c"))
        d.ellipse([6, 7, 13, 17], fill=E("#e0e8ff" if kind == "moon_shaft" else "#ffe8a0"))
        frames.append(fin(im))
    return frames


def portal_gate(color=(0.9, 0.2, 0.2)):
    frames = []
    col = tuple(int(c * 255) for c in color)
    for k in range(6):
        im, d = _img(40, 56)
        d.rectangle([2, 8, 7, 55], fill=C("#4a4858"))
        d.rectangle([32, 8, 37, 55], fill=C("#4a4858"))
        d.pieslice([2, 0, 37, 26], 180, 360, fill=C("#4a4858"))
        d.pieslice([7, 5, 32, 26], 180, 360, fill=(0, 0, 0, 0))
        d.rectangle([8, 13, 31, 55], fill=(0, 0, 0, 0))
        rng = np.random.default_rng(k)
        for _ in range(140):
            x, y = rng.integers(8, 32), rng.integers(10, 55)
            f = rng.random()
            c = (int(col[0] * (0.5 + f)), int(col[1] * (0.5 + f)), int(col[2] * (0.5 + f)))
            d.point((x, y), fill=(min(255, c[0]), min(255, c[1]), min(255, c[2]), EMISSIVE_A))
        frames.append(fin(im))
    return frames


def portal(color=(0.6, 0.4, 1.0)):
    frames = []
    col = tuple(int(c * 255) for c in color)
    for k in range(6):
        im, d = _img(32, 40)
        rng = np.random.default_rng(k + 11)
        for r in range(12, 2, -2):
            d.ellipse([16 - r, 20 - r * 1.4, 16 + r, 20 + r * 1.4], outline=(col[0], col[1], col[2], EMISSIVE_A))
        for _ in range(40):
            a = rng.uniform(0, math.tau)
            rr = rng.uniform(2, 12)
            d.point((16 + math.cos(a) * rr, 20 + math.sin(a) * rr * 1.4), fill=E("#ffffff"))
        frames.append(np.array(im))
    return frames


def stairs(up=True):
    im, d = _img(32, 24)
    for i in range(5):
        y = 20 - i * 4 if up else 4 + i * 4
        d.rectangle([2 + i, y, 29 - i, y + 3], fill=C("#5a5868") if i % 2 else C("#6a6878"))
    return [fin(shade(im))]


def lectern():
    im, d = _img(16, 24)
    d.rectangle([6, 10, 9, 23], fill=C("#4a3020"))
    d.polygon([(2, 6), (14, 8), (14, 11), (2, 9)], fill=C("#5a3a22"))
    d.rectangle([4, 5, 12, 8], fill=C("#e0d8c0"))
    return [fin(shade(im))]


def note():
    im, d = _img(12, 10)
    d.polygon([(1, 3), (10, 1), (11, 8), (2, 9)], fill=C("#e0d8b8"))
    d.line([3, 4, 8, 3], fill=C("#6a5a4a"))
    d.line([3, 6, 9, 5], fill=C("#6a5a4a"))
    return [fin(im)]


def stone_tablet():
    im, d = _img(16, 22)
    d.rounded_rectangle([2, 2, 13, 21], 3, fill=C("#6a6878"))
    for y in (6, 9, 12, 15):
        d.line([4, y, 11, y], fill=E("#a0b0d0"))
    return [fin(shade(im))]


def bone_shard():
    im, d = _img(14, 10)
    d.polygon([(1, 6), (11, 2), (13, 4), (3, 9)], fill=C("#d8d0b8"))
    d.point((7, 5), fill=E("#ffe090"))
    return [fin(im)]


def locket():
    im, d = _img(10, 10)
    d.ellipse([2, 2, 8, 8], fill=E("#d0d0e0"))
    d.line([5, 0, 5, 2], fill=C("#a0a0b0"))
    return [fin(im)]


def item_glow():
    frames = []
    for k in range(4):
        im, d = _img(12, 16)
        h = 3 + k % 2
        d.ellipse([3, 8 - h, 9, 14 - h], fill=E("#ffe8a0"))
        d.point((6, 11 - h), fill=E("#ffffff"))
        frames.append(np.array(im))
    return frames


def lost_grace():
    frames = []
    for k in range(4):
        im, d = _img(14, 20)
        rng = np.random.default_rng(k)
        for _ in range(20):
            d.point((7 + rng.normal(0, 2), 12 - rng.uniform(0, 10)), fill=E("#ffd060"))
        d.ellipse([4, 12, 10, 18], fill=E("#ffc040"))
        frames.append(np.array(im))
    return frames


# ---------------------------------------------------------------------------- forja
def gear(size=20, color="#a07a3a"):
    frames = []
    for k in range(4):
        im, d = _img(size, size)
        c = size / 2
        r = size * 0.38
        for t in range(10):
            a = t / 10 * math.tau + k * 0.15
            d.rectangle([c + math.cos(a) * r - 1.5, c + math.sin(a) * r - 1.5, c + math.cos(a) * r + 1.5, c + math.sin(a) * r + 1.5],
                        fill=C(color))
        d.ellipse([c - r + 1, c - r + 1, c + r - 1, c + r - 1], fill=C(color))
        d.ellipse([c - r * 0.35, c - r * 0.35, c + r * 0.35, c + r * 0.35], fill=C("#3a2a1a"))
        frames.append(fin(shade(im)))
    return frames


def gear_socket():
    frames = []
    for state in range(5):
        im, d = _img(24, 32)
        d.rectangle([2, 16, 21, 31], fill=C("#4a3e30"))
        d.rectangle([4, 2, 19, 18], fill=C("#5a4a38"))
        if state == 0:
            d.ellipse([7, 5, 16, 14], outline=C("#2a2018"))
        else:
            g = Image.fromarray(gear(16)[0])
            g = g.rotate(-(state - 1) * 90, resample=Image.NEAREST)
            im.alpha_composite(g, (4, 2))
            d = ImageDraw.Draw(im)
            ang = (state - 1) * math.pi / 2 - math.pi / 2
            d.line([12, 10, 12 + math.cos(ang) * 6, 10 + math.sin(ang) * 6], fill=E("#ffb040"), width=1)
        frames.append(fin(shade(im)))
    return frames


def valve():
    frames = []
    for k in range(4):
        im, d = _img(20, 24)
        d.rectangle([7, 12, 12, 23], fill=C("#5a4a38"))
        d.ellipse([2, 2, 17, 17], outline=C("#b04030"), width=2)
        a = k * math.pi / 2
        d.line([9.5 - math.cos(a) * 6, 9.5 - math.sin(a) * 6, 9.5 + math.cos(a) * 6, 9.5 + math.sin(a) * 6], fill=C("#b04030"), width=2)
        d.point((9.5 + math.cos(a) * 6, 9.5 + math.sin(a) * 6), fill=E("#ffd060"))
        frames.append(fin(shade(im)))
    return frames


def power_node():
    frames = []
    for state in range(4):      # off, on, off+energizado, on+energizado
        on, pw = state % 2, state // 2
        im, d = _img(20, 28)
        d.rectangle([4, 10, 15, 27], fill=C("#4a4a50"))
        d.rectangle([6, 2, 13, 11], fill=C("#6a6a70"))
        d.rectangle([7, 4, 12, 9], fill=E("#60e0ff") if pw else C("#2a3a4a"))
        d.line([9.5, 14, 9.5 + (4 if on else -4), 22], fill=E("#ffd060") if on else C("#8a6a40"), width=2)
        frames.append(fin(shade(im)))
    return frames


def pipe_vent():
    frames = []
    for k in range(3):
        im, d = _img(16, 12)
        d.rectangle([2, 4, 13, 11], fill=C("#5a4a38"))
        d.rectangle([4, 2, 11, 5], fill=C("#3a3028"))
        if k:
            d.rectangle([5, 0, 10, 3], fill=E("#ff8040"))
        frames.append(fin(im))
    return frames


def anvil():
    im, d = _img(24, 18)
    d.polygon([(2, 4), (21, 4), (17, 9), (6, 9)], fill=C("#3a3a42"))
    d.rectangle([8, 9, 15, 15], fill=C("#2e2e36"))
    d.rectangle([5, 15, 18, 17], fill=C("#3a3a42"))
    return [fin(shade(im))]


def forge():
    frames = []
    for k in range(4):
        im, d = _img(32, 32)
        d.rectangle([2, 8, 29, 31], fill=C("#5a3a2a"))
        d.rectangle([2, 8, 29, 31], outline=C("#3a2418"))
        d.rectangle([8, 16, 23, 28], fill=C("#1a0a08"))
        flame(d, 15.5, 28, 9 + (k % 2), "#ff6010", k)
        d.rectangle([12, 0, 19, 8], fill=C("#4a3024"))
        frames.append(fin(shade(im)))
    return frames


def cart():
    im, d = _img(40, 32)
    d.rectangle([2, 12, 37, 24], fill=C("#6a4a2a"))
    d.ellipse([4, 20, 14, 30], fill=C("#3a2a1a"))
    d.ellipse([26, 20, 36, 30], fill=C("#3a2a1a"))
    d.polygon([(2, 12), (37, 12), (32, 2), (7, 2)], fill=C("#8a3a3a"))
    for x in range(8, 33, 6):
        d.rectangle([x, 8, x + 3, 12], fill=C(("#c0a040", "#6a8aa0", "#a05050")[x % 3]))
    return [fin(shade(im))]


def shrine():
    im, d = _img(20, 28)
    d.rectangle([4, 12, 15, 27], fill=C("#4a4048"))
    d.polygon([(2, 12), (17, 12), (9.5, 3)], fill=C("#5a3030"))
    d.rectangle([8, 16, 11, 22], fill=E("#c02030"))
    return [fin(shade(im))]


def trophy(color):
    frames = []
    for k in range(2):
        im, d = _img(20, 32)
        d.rectangle([4, 24, 15, 31], fill=C("#5a5048"))
        d.rectangle([7, 12, 12, 24], fill=C("#6a6058"))
        d.ellipse([3, 2, 16, 15], fill=E(color))
        frames.append(fin(shade(im)))
    return frames


def platform_art():
    im, d = _img(32, 24)
    d.rectangle([0, 0, 31, 15], fill=C("#6a5a42"))
    d.rectangle([0, 16, 31, 23], fill=C("#4a3e30"))
    for x in (3, 28):
        d.ellipse([x - 1, 6, x + 1, 8], fill=C("#a08050"))
    return [fin(shade(im))]


def dummy_art():
    return statue("#b09060", kind="none")


def spikes():
    frames = []
    for state in range(3):     # off, warn, on
        im, d = _img(16, 16)
        d.rectangle([0, 8, 15, 15], fill=C("#3a3a42"))
        for x in range(1, 16, 4):
            if state == 2:
                d.polygon([(x, 12), (x + 3, 12), (x + 1.5, 1)], fill=C("#c0c4cc"))
            elif state == 1:
                d.polygon([(x, 12), (x + 3, 12), (x + 1.5, 9)], fill=C("#c04030"))
            else:
                d.rectangle([x, 10, x + 3, 11], fill=C("#2a2a30"))
        frames.append(fin(im))
    return frames


def flame_vent():
    frames = []
    for state in range(3):
        im, d = _img(16, 32)
        d.rectangle([3, 26, 12, 31], fill=C("#4a3e30"))
        if state == 1:
            d.rectangle([6, 22, 9, 26], fill=E("#ff6020"))
        if state == 2:
            flame(d, 8, 27, 24, "#ff7020", 1)
        frames.append(fin(im))
    return frames


def saw_art():
    frames = []
    for k in range(4):
        im, d = _img(24, 24)
        for t in range(12):
            a = t / 12 * math.tau + k * 0.13
            d.polygon([(12 + math.cos(a) * 9, 12 + math.sin(a) * 9), (12 + math.cos(a + 0.2) * 11, 12 + math.sin(a + 0.2) * 11),
                       (12 + math.cos(a + 0.4) * 9, 12 + math.sin(a + 0.4) * 9)], fill=C("#c0c4cc"))
        d.ellipse([3, 3, 20, 20], fill=C("#9a9ea8"))
        d.ellipse([9, 9, 14, 14], fill=C("#4a4a50"))
        frames.append(fin(im))
    return frames


def flesh_pod():
    im, d = _img(20, 28)
    d.ellipse([2, 6, 17, 27], fill=C("#8a3a3a"))
    d.ellipse([5, 10, 14, 22], fill=C("#a85050"))
    d.line([9, 4, 9, 10], fill=C("#6a2a2a"), width=2)
    d.point((9, 16), fill=E("#ffd060"))
    return [fin(shade(im))]


def alchemy_tube(color="#60ff80"):
    frames = []
    for k in range(3):
        im, d = _img(16, 36)
        d.rectangle([4, 30, 11, 35], fill=C("#5a5048"))
        d.rectangle([4, 2, 11, 30], fill=C("#a0b8b0"))
        lvl = 12 + k
        d.rectangle([5, lvl, 10, 29], fill=E(color))
        frames.append(fin(im))
    return frames


def bookpile():
    im, d = _img(20, 16)
    cols = ["#6a2a2a", "#2a3a6a", "#3a5a2a", "#6a5a2a"]
    for i in range(4):
        d.rectangle([2 + i % 2, 13 - i * 3, 17 - i % 2, 15 - i * 3], fill=C(cols[i]))
    return [fin(shade(im))]


def telescope():
    im, d = _img(32, 40)
    d.line([16, 20, 16, 39], fill=C("#5a4a3a"), width=2)
    d.line([10, 39, 16, 26], fill=C("#5a4a3a"))
    d.line([22, 39, 16, 26], fill=C("#5a4a3a"))
    d.line([4, 30, 28, 8], fill=C("#a08a40"), width=4)
    d.ellipse([26, 5, 30, 11], fill=E("#a0c0ff"))
    return [fin(shade(im))]


def orb_stand(color="#80a0ff"):
    frames = []
    for k in range(4):
        im, d = _img(16, 28)
        d.rectangle([6, 12, 9, 27], fill=C("#4a4458"))
        d.rectangle([3, 25, 12, 27], fill=C("#4a4458"))
        r = 4 + (k % 2) * 0.5
        d.ellipse([8 - r, 8 - r, 8 + r, 8 + r], fill=E(color))
        frames.append(fin(im))
    return frames


def angel_statue():
    return statue("#c8c0b0", kind="angel")


def column_broken():
    return pillar(True)


def crystal_cluster(color="#80a0ff"):
    im, d = _img(28, 32)
    rng = rng_for("cc" + color)
    for _ in range(5):
        x = rng.integers(6, 22)
        h = rng.integers(10, 26)
        d.polygon([(x - 3, 31), (x + 3, 31), (x + rng.integers(-2, 3), 31 - h)], fill=E(color))
    return [fin(im)]


def halo_broken():
    im, d = _img(32, 20)
    d.arc([2, 2, 29, 17], 200, 520, fill=E("#ffe090"), width=2)
    return [fin(im)]


PROP_SPRITES = {
    "tree_twisted": [lambda: tree_twisted("a"), lambda: tree_twisted("b"), lambda: tree_twisted("c")],
    "tree_dead": [lambda: tree_dead("a"), lambda: tree_dead("b")],
    "tombstone": [lambda: tombstone("a"), lambda: tombstone("b"), lambda: tombstone("c")],
    "cross": cross, "coffin": coffin, "statue_knight": lambda: statue(kind="knight"), "king_statue": king_statue_states,
    "pillar": lambda: pillar(False), "pillar_broken": lambda: pillar(True), "banner": banner, "armor_stand": armor_stand,
    "urn": urn, "barrel": barrel, "crate": crate, "brazier": brazier, "brazier_red": lambda: brazier("#ff3020", "#3a3038"),
    "brazier_blue": lambda: brazier("#60a0ff", "#3a3a50"), "brazier_gold": lambda: brazier("#ffd060", "#7a6a50"),
    "candelabra": candelabra, "lamp_post": lamp_post, "wall_torch": wall_torch, "campfire": campfire, "lantern": lantern,
    "blood_candle": blood_candle, "grace": grace_flame, "chest": chest, "gate_iron": lambda: gate_iron(48, 48),
    "gate_iron_small": lambda: gate_iron(16, 48), "gate": lambda: gate_iron(16, 48), "door_red": door_red, "secret_wall": secret_wall,
    "cracked_wall_brick": cracked_wall_brick, "cracked_wall": cracked_wall_brick, "fog_gate": fog_gate, "blood_seal": blood_seal,
    "lever": lever, "plate": plate, "moon_dial": moon_dial, "dial": lambda: symbol_dial(range(6)),
    "rune_dial": lambda: symbol_dial(range(6), "#60f0d0"), "holy_dial": lambda: symbol_dial(range(6), "#ffd070"),
    "mirror": mirror, "crystal": crystal, "crystal_gold": lambda: crystal("#ffd070"), "emitter": emitter, "moon_shaft": lambda: emitter("moon_shaft"),
    "sun_lens": lambda: emitter("sun"), "portal_gate": portal_gate, "portal": portal, "stairs_up": lambda: stairs(True),
    "stairs_down": lambda: stairs(False), "exit": lambda: stairs(False), "lectern": lectern, "note": note, "stone_tablet": stone_tablet,
    "bone_shard": bone_shard, "locket": locket, "item_glow": item_glow, "lost_grace": lost_grace, "gear": gear,
    "gear_socket": gear_socket, "valve": valve, "power_node": power_node, "pipe_vent": pipe_vent, "anvil": anvil, "forge": forge,
    "cart": cart, "shrine": shrine, "platform": platform_art, "spikes": spikes, "flame_vent": flame_vent, "saw_hazard": saw_art,
    "flesh_pod": flesh_pod, "alchemy_tube": alchemy_tube, "alchemy_tube_red": lambda: alchemy_tube("#ff4040"),
    "bookpile": bookpile, "telescope": telescope, "orb_stand": orb_stand, "angel_statue": angel_statue,
    "column_broken": column_broken, "crystal_cluster": crystal_cluster, "crystal_cluster_gold": lambda: crystal_cluster("#ffd070"),
    "halo_broken": halo_broken, "altar": lambda: shrine(), "button": lambda: symbol_dial(range(1), "#ffd070"),
    "trofeu_ato1": lambda: trophy("#c02030"), "trofeu_ato2": lambda: trophy("#ff8030"), "trofeu_ato3": lambda: trophy("#e0c090"),
    "trofeu_ato4": lambda: trophy("#8060ff"), "trofeu_ato5": lambda: trophy("#fff0b0"), "boneco": dummy_art,
}


def build_prop(name):
    """Devolve lista de variantes; cada variante é lista de quadros (arrays RGBA)."""
    spec = PROP_SPRITES.get(name)
    if spec is None:
        return [crate()]
    if isinstance(spec, list):
        return [fn() for fn in spec]
    return [spec()]
