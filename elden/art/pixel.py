"""Ferramentas de pixel art procedural: rampas de cor, ruído repetível e pontilhado ordenado."""
import numpy as np

BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16.0


def hexc(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def ramp(*hexes):
    return np.array([hexc(h) for h in hexes], dtype=np.float32)


def lerp_ramp(a, b, t):
    return a * (1 - t) + b * t


def value_noise(rng, size, cells, wrap=True):
    """Ruído de valor suave e repetível (size x size) com 'cells' células por lado."""
    g = rng.random((cells + 1, cells + 1)).astype(np.float32)
    if wrap:
        g[-1, :] = g[0, :]
        g[:, -1] = g[:, 0]
    ys = np.linspace(0, cells, size, endpoint=False)
    y0 = np.floor(ys).astype(int)
    fy = ys - y0
    fy = fy * fy * (3 - 2 * fy)
    rows = g[y0] * (1 - fy)[:, None] + g[y0 + 1] * fy[:, None]
    x0 = y0
    fx = fy
    return rows[:, x0] * (1 - fx)[None, :] + rows[:, x0 + 1] * fx[None, :]


def fbm(rng, size, octaves=3, base=2):
    out = np.zeros((size, size), np.float32)
    amp, tot = 1.0, 0.0
    c = base
    for _ in range(octaves):
        if c > size:
            break
        out += value_noise(rng, size, c) * amp
        tot += amp
        amp *= 0.5
        c *= 2
    return out / tot


def quantize(values, pal, dither=0.6, offset=(0, 0)):
    """values em 0..1 -> índices da rampa com pontilhado de Bayer -> rgb uint8."""
    h, w = values.shape
    oy, ox = offset
    by = BAYER4[(np.arange(h)[:, None] + oy) % 4, (np.arange(w)[None, :] + ox) % 4]
    n = len(pal)
    idx = np.clip(np.floor(values * (n - 1) + 0.5 + (by - 0.5) * dither), 0, n - 1).astype(int)
    return pal[idx]


def rgba(rgb, alpha=255):
    h, w = rgb.shape[:2]
    a = np.full((h, w, 1), alpha, np.float32) if np.isscalar(alpha) else alpha[..., None].astype(np.float32)
    return np.concatenate([rgb.astype(np.float32), a], axis=2).clip(0, 255).astype(np.uint8)


def outline(img, color=(16, 12, 18), alpha_thresh=1):
    """Contorno de 1 pixel em volta das áreas opacas (sprites)."""
    a = img[..., 3] >= alpha_thresh
    pad = np.pad(a, 1)
    neigh = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
    edge = neigh & ~a
    out = img.copy()
    out[edge, 0:3] = color
    out[edge, 3] = 255
    return out


def shade_edges(rgb, mask, light=1.18, dark=0.72):
    """Destaca a borda superior/esquerda e escurece a inferior/direita de cada região da máscara."""
    m = mask.astype(bool)
    up = np.roll(m, 1, 0)
    left = np.roll(m, 1, 1)
    down = np.roll(m, -1, 0)
    right = np.roll(m, -1, 1)
    out = rgb.copy()
    hi = m & (~up | ~left)
    lo = m & (~down | ~right)
    out[hi] = out[hi] * light
    out[lo] = out[lo] * dark
    return out
