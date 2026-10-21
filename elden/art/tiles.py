"""Texturas de cenário em pixel art (16x16), geradas por código e reunidas num atlas por fase.

Cada receita é uma função (rng, rampa) -> imagem RGBA 16x16. Texels com alfa ~200 são emissivos
(o shader do cenário faz eles brilharem: vitrais, runas, brasas, lava).
"""
import zlib

import numpy as np

from .pixel import ramp, value_noise, fbm, quantize, rgba, shade_edges, BAYER4

T = 16
EMISSIVE_ALPHA = 200

# ----------------------------------------------------------------------------- rampas
RAMPS = {
    "stone": ramp("1b1a22", "2c2a35", "403d4b", "585566", "726f80", "8f8c9c"),
    "stone_warm": ramp("1f1a18", "352c27", "4d4038", "66574b", "807061", "9c8a78"),
    "stone_moss": ramp("141a14", "223024", "334632", "4a5d40", "65744f", "838d64"),
    "dirt": ramp("1a120e", "2b1f17", "3e2c1f", "543c29", "6b4e35", "856445"),
    "mud_red": ramp("1c0d0d", "2e1414", "451d1b", "5e2a24", "773a2f", "8f4c3a"),
    "grass": ramp("0f1712", "18261b", "223523", "2e472c", "3d5a33", "4f6e3d"),
    "grass_dead": ramp("17150f", "262216", "37311f", "4a4229", "5e5534", "746a42"),
    "wood": ramp("1a100b", "2c1b12", "422a1b", "5a3a25", "714b30", "8a603d"),
    "wood_dark": ramp("120b0a", "1f1310", "2e1d18", "3f2821", "51352b", "644236"),
    "metal": ramp("121315", "1f2226", "30343a", "454a52", "5e646d", "7e858f"),
    "rust": ramp("1a0e08", "2e170c", "472411", "623317", "7d461f", "9a5c2b"),
    "copper": ramp("1f0f08", "3a1d0e", "5a2f14", "7d461c", "a36127", "c98238"),
    "brass": ramp("1e1608", "36290e", "524015", "70591d", "917528", "b59634"),
    "marble": ramp("3a3634", "5a5550", "7c766e", "9d968c", "bdb6aa", "dcd6ca"),
    "marble_gold": ramp("3b2c14", "5c461d", "7f6226", "a6822f", "caa23d", "e6c460"),
    "flesh": ramp("1f0a0c", "3a1216", "561b20", "73272a", "903a37", "ad5248"),
    "bone": ramp("2a2620", "48423a", "6a6255", "8f8574", "b3a894", "d4cab4"),
    "carpet": ramp("1a0508", "2d080e", "450c15", "5f121c", "7a1a25", "962430"),
    "tile_dark": ramp("0e0e14", "17161f", "21202c", "2d2b3a", "3a3849", "484659"),
    "arcane": ramp("0d0a1c", "17112e", "231945", "32225e", "45307a", "5c4299"),
    "void": ramp("000000", "050308", "0a0610", "100a18", "160e20", "1c1228"),
    "lava": ramp("2a0400", "5c0d00", "9a2300", "d24a05", "f58a1c", "ffd060"),
    "water": ramp("050a12", "0a1420", "0f1f30", "152a40", "1d3852", "284866"),
    "blood": ramp("120203", "240406", "38070a", "4e0a0e", "650e13", "7e1419"),
    "glass_red": ramp("3a0610", "6a0a1c", "a01428", "d02c3a", "f05a50", "ff9a78"),
    "glass_blue": ramp("060c2a", "0c1c50", "14307a", "2050a6", "3a78cc", "6aa6ee"),
    "glass_gold": ramp("2a1a04", "50340a", "805612", "b07e1e", "dcaa36", "ffd868"),
    "rune_cyan": ramp("02161a", "063038", "0a5058", "12807e", "28b8a8", "70f0d8"),
}


def _rng(seed):
    return np.random.default_rng(seed)


def _final(rgb, alpha=255):
    return rgba(rgb, alpha)


# ----------------------------------------------------------------------------- receitas
def flagstones(rng, pal, cracks=0.4, moss=None):
    """Lajotas irregulares de pedra com rejunte escuro e bordas iluminadas."""
    v = 0.45 + (fbm(rng, T, 3, 2) - 0.5) * 0.5
    mask = np.ones((T, T), bool)
    # rejuntes: duas linhas horizontais deslocadas e verticais alternadas
    y1 = rng.integers(5, 8)
    y2 = y1 + rng.integers(6, 9)
    for y in (y1 % T, y2 % T):
        mask[y, :] = False
    xs = [rng.integers(2, 14), rng.integers(2, 14), rng.integers(2, 14)]
    bands = [(0, y1), (y1, y2), (y2, T)]
    for (a, b), x in zip(bands, xs):
        mask[a:b, x] = False
    mask[:, 0] &= True
    rgb = quantize(v, pal, 0.8)
    rgb = shade_edges(rgb, mask, 1.15, 0.78)
    rgb[~mask] = pal[0]
    for _ in range(int(cracks * 3)):
        if rng.random() < cracks:
            x, y = rng.integers(1, T - 1, 2)
            for _ in range(rng.integers(2, 5)):
                rgb[y % T, x % T] = pal[1]
                x += rng.integers(-1, 2)
                y += 1
    if moss is not None:
        m = value_noise(rng, T, 4) > 0.62
        rgb[m & mask] = quantize(value_noise(rng, T, 8), moss, 0.9)[m & mask]
    return _final(rgb)


def bricks(rng, pal, h=4, w=8, mortar=0, rough=0.5):
    """Tijolos/blocos de parede (face vertical)."""
    v = 0.5 + (fbm(rng, T, 3, 2) - 0.5) * rough
    mask = np.ones((T, T), bool)
    tone = np.zeros((T, T), np.float32)
    for row in range(T // h):
        y0 = row * h
        mask[y0, :] = False
        off = (w // 2) * (row % 2)
        for k in range(-1, T // w + 1):
            x = k * w + off
            if 0 <= x < T:
                mask[y0:y0 + h, x] = False
            tone[y0:y0 + h, max(0, x):min(T, x + w)] = rng.random() * 0.25 - 0.12
    rgb = quantize(np.clip(v + tone, 0, 1), pal, 0.7)
    rgb = shade_edges(rgb, mask, 1.2, 0.75)
    rgb[~mask] = pal[mortar]
    return _final(rgb)


def voronoi_stones(rng, pal, n=5, gap=1, moss=None, cracks=0.3, flat=False):
    """Pedras irregulares (células de Voronoi repetíveis) com rejunte escuro: lê como chão, não como parede."""
    pts = rng.random((n, 2)) * T
    yy, xx = np.mgrid[0:T, 0:T]
    best = np.full((T, T), 1e9)
    second = np.full((T, T), 1e9)
    owner = np.zeros((T, T), int)
    for i, (px, py) in enumerate(pts):
        for ox in (-T, 0, T):
            for oy in (-T, 0, T):
                d = np.hypot(xx - (px + ox), yy - (py + oy))
                closer = d < best
                second = np.where(closer, best, np.minimum(second, d))
                owner = np.where(closer, i, owner)
                best = np.where(closer, d, best)
    edge = (second - best) < gap
    tone = rng.random(n) * 0.3 - 0.15
    v = 0.42 + tone[owner] + (fbm(rng, T, 2, 2) - 0.5) * 0.18
    if not flat:
        # cada pedra mais clara no alto/esquerda
        v = v + np.clip((second - best) / 8.0, 0, 0.12)
    rgb = quantize(np.clip(v, 0, 1), pal, 0.6)
    mask = ~edge
    rgb = shade_edges(rgb, mask, 1.1, 0.82)
    rgb[edge] = pal[0]
    if moss is not None:
        m = (value_noise(rng, T, 4) > 0.6) & (edge | (rng.random((T, T)) < 0.25))
        rgb[m] = quantize(value_noise(rng, T, 8), moss, 0.9)[m]
    for _ in range(int(cracks * 3)):
        if rng.random() < cracks:
            x, y = rng.integers(1, T - 1, 2)
            for _ in range(rng.integers(2, 4)):
                rgb[y % T, x % T] = pal[1]
                x += rng.integers(-1, 2)
                y += 1
    return _final(rgb)


def roof(rng, pal):
    """Telhado de telhas (casas vistas de cima)."""
    rgb = np.zeros((T, T, 3), np.float32)
    for row in range(T // 4):
        off = 2 * (row % 2)
        for x in range(T):
            k = (x + off) % 4
            v = 0.55 - (0.25 if k == 3 else 0.0) + rng.random() * 0.08
            for y in range(row * 4, row * 4 + 4):
                yy = y - row * 4
                vv = v + (0.15 if yy == 0 else -0.12 if yy == 3 else 0.0)
                rgb[y, x] = pal[int(np.clip(vv, 0, 0.999) * len(pal))]
    return _final(rgb)


def ashlar(rng, pal):
    """Blocos grandes de cantaria (castelos, templos)."""
    return bricks(rng, pal, h=8, w=16, mortar=0, rough=0.45)


def wall_top(rng, pal):
    """Topo de muro visto de cima: blocos largos com aresta clara e contorno sul escuro (lê como altura)."""
    v = 0.62 + (fbm(rng, T, 3, 2) - 0.5) * 0.3
    rgb = quantize(v, pal, 0.5)
    mask = np.ones((T, T), bool)
    mask[:, 8] = False
    rgb = shade_edges(rgb, mask, 1.08, 0.9)
    rgb[:, 8] = pal[2]
    rgb[0, :] = pal[-1]
    rgb[1, :] = pal[-2]
    rgb[-2, :] = pal[2]
    rgb[-1, :] = pal[0]
    return _final(rgb)


def dirt(rng, pal, pebbles=6):
    v = 0.35 + (fbm(rng, T, 3, 2) - 0.5) * 0.6
    rgb = quantize(v, pal, 1.0)
    for _ in range(pebbles):
        x, y = rng.integers(0, T, 2)
        rgb[y, x] = pal[min(len(pal) - 1, 4)]
        rgb[(y + 1) % T, x] = pal[1]
    return _final(rgb)


def grass(rng, pal, flowers=0, flower_col=(170, 40, 50)):
    v = 0.4 + (fbm(rng, T, 3, 4) - 0.5) * 0.6
    rgb = quantize(v, pal, 0.9)
    for _ in range(18):
        x, y = rng.integers(0, T, 2)
        rgb[y, x] = pal[-1]
        rgb[(y + 1) % T, x] = pal[2]
    for _ in range(flowers):
        x, y = rng.integers(1, T - 1, 2)
        rgb[y, x] = flower_col
    return _final(rgb)


def planks(rng, pal, vertical=False, w=4):
    v = np.zeros((T, T), np.float32)
    mask = np.ones((T, T), bool)
    for k in range(T // w):
        tone = 0.35 + rng.random() * 0.35
        grain = value_noise(rng, T, 2)
        v[:, k * w:(k + 1) * w] = tone + (grain[:, k * w:(k + 1) * w] - 0.5) * 0.25
        mask[:, k * w] = False
        cut = rng.integers(0, T)
        mask[cut, k * w:(k + 1) * w] = False
    stripes = (np.sin(np.arange(T)[:, None] * 1.7 + np.arange(T)[None, :] * 0.2) * 0.06)
    rgb = quantize(np.clip(v + stripes, 0, 1), pal, 0.6)
    rgb = shade_edges(rgb, mask, 1.12, 0.8)
    rgb[~mask] = pal[0]
    for _ in range(2):
        x, y = rng.integers(1, T - 1, 2)
        rgb[y, x] = pal[1]
    if vertical:
        rgb = np.transpose(rgb, (1, 0, 2))
    return _final(rgb)


def metal_plate(rng, pal, rivets=True, rust=None):
    v = 0.5 + (value_noise(rng, T, 2) - 0.5) * 0.3 + np.linspace(0.08, -0.08, T)[:, None]
    rgb = quantize(np.clip(v, 0, 1), pal, 0.5)
    mask = np.ones((T, T), bool)
    mask[0, :] = mask[:, 0] = False
    rgb = shade_edges(rgb, mask, 1.2, 0.7)
    rgb[~mask] = pal[0]
    if rivets:
        for (x, y) in ((3, 3), (12, 3), (3, 12), (12, 12)):
            rgb[y, x] = pal[-1]
            rgb[y + 1, x + 1] = pal[1]
    if rust is not None:
        m = fbm(rng, T, 3, 2) > 0.58
        rgb[m] = quantize(value_noise(rng, T, 8), rust, 0.8)[m]
    return _final(rgb)


def grate(rng, pal):
    rgb = np.tile(pal[0], (T, T, 1)).astype(np.float32)
    a = np.full((T, T), 255, np.float32)
    for k in range(0, T, 4):
        rgb[:, k:k + 1] = pal[3]
        rgb[:, k + 1:k + 2] = pal[2]
        rgb[k:k + 1, :] = pal[4]
    return rgba(rgb, a)


def gears_floor(rng, pal):
    v = 0.4 + (fbm(rng, T, 2, 2) - 0.5) * 0.3
    rgb = quantize(v, pal, 0.5)
    yy, xx = np.mgrid[0:T, 0:T]
    r = np.hypot(xx - 7.5, yy - 7.5)
    ring = (r > 4.5) & (r < 6.5)
    ang = np.arctan2(yy - 7.5, xx - 7.5)
    teeth = (r >= 6.5) & (r < 7.6) & (np.sin(ang * 8) > 0.2)
    rgb[ring | teeth] = pal[4]
    rgb[(r < 1.6)] = pal[1]
    return _final(rgb)


def marble(rng, pal, veins=True, gold=None):
    v = 0.62 + (fbm(rng, T, 3, 2) - 0.5) * 0.35
    rgb = quantize(v, pal, 0.5)
    if veins:
        x = rng.integers(0, T)
        for y in range(T):
            x = (x + rng.integers(-1, 2)) % T
            rgb[y, x] = pal[2]
    mask = np.ones((T, T), bool)
    mask[0, :] = mask[:, 0] = False
    rgb = shade_edges(rgb, mask, 1.06, 0.88)
    rgb[~mask] = pal[1]
    if gold is not None:
        rgb[0, :] = gold[3]
        rgb[:, 0] = gold[2]
    return _final(rgb)


def checker(rng, pal_a, pal_b):
    v = 0.5 + (fbm(rng, T, 2, 2) - 0.5) * 0.3
    a = quantize(v, pal_a, 0.6)
    b = quantize(v, pal_b, 0.6)
    yy, xx = np.mgrid[0:T, 0:T]
    m = ((xx // 8) + (yy // 8)) % 2 == 0
    rgb = np.where(m[..., None], a, b)
    rgb[0, :] = pal_a[0]
    rgb[:, 0] = pal_a[0]
    return _final(rgb)


def carpet(rng, pal, trim=None):
    v = 0.45 + (fbm(rng, T, 2, 4) - 0.5) * 0.25
    rgb = quantize(v, pal, 0.8)
    yy, xx = np.mgrid[0:T, 0:T]
    diamond = (np.abs(xx - 7.5) + np.abs(yy - 7.5)) % 6 < 1
    rgb[diamond] = pal[-1]
    if trim is not None:
        rgb[0:1, :] = trim[3]
        rgb[-1:, :] = trim[3]
    return _final(rgb)


def flesh(rng, pal):
    v = fbm(rng, T, 3, 2)
    cells = value_noise(rng, T, 4)
    v = 0.45 + (v - 0.5) * 0.6 + (np.sin(cells * 20) * 0.08)
    rgb = quantize(np.clip(v, 0, 1), pal, 1.0)
    # veias
    x = rng.integers(0, T)
    for y in range(T):
        x = (x + rng.integers(-1, 2)) % T
        rgb[y, x] = pal[1]
    for _ in range(3):
        x, y = rng.integers(0, T, 2)
        rgb[y, x] = pal[-1]
    return _final(rgb)


def bones(rng, pal, ground):
    rgb = quantize(0.3 + (fbm(rng, T, 3, 2) - 0.5) * 0.4, ground, 1.0)
    for _ in range(5):
        x, y = rng.integers(1, T - 3, 2)
        L = rng.integers(3, 6)
        horiz = rng.random() < 0.5
        for k in range(L):
            xx, yy = (x + k, y) if horiz else (x, y + k)
            if xx < T and yy < T:
                rgb[yy, xx] = pal[4]
                if yy + 1 < T:
                    rgb[yy + 1, xx] = pal[2]
        rgb[y, x] = pal[5]
    return _final(rgb)


def liquid(rng, pal, emissive=False, bright=0.5):
    """Base estática de líquido (o brilho animado vem do shader de líquidos)."""
    v = bright + (fbm(rng, T, 3, 2) - 0.5) * 0.5
    rgb = quantize(np.clip(v, 0, 1), pal, 1.0)
    return _final(rgb, EMISSIVE_ALPHA if emissive else 255)


def stained_glass(rng, pal, frame):
    """Vitral emissivo: chumbo escuro + células coloridas."""
    yy, xx = np.mgrid[0:T, 0:T]
    v = 0.55 + (value_noise(rng, T, 3) - 0.5) * 0.7
    rgb = quantize(np.clip(v, 0, 1), pal, 0.4)
    alpha = np.full((T, T), EMISSIVE_ALPHA, np.float32)
    lead = (xx % 5 == 0) | (yy % 6 == 0) | ((xx + yy) % 9 == 0)
    rgb[lead] = frame[0]
    alpha[lead] = 255
    return rgba(rgb, alpha)


def rune_stone(rng, pal, glow):
    rgb = flagstones(rng, pal, cracks=0.1)[..., :3].astype(np.float32)
    alpha = np.full((T, T), 255, np.float32)
    # símbolo simples: círculo + traços
    yy, xx = np.mgrid[0:T, 0:T]
    r = np.hypot(xx - 7.5, yy - 7.5)
    sym = (np.abs(r - 5) < 0.55) | ((np.abs(xx - 7.5) < 0.5) & (r < 3)) | ((np.abs(yy - 7.5) < 0.5) & (r < 2))
    rgb[sym] = glow[2]
    alpha[sym] = EMISSIVE_ALPHA
    return rgba(rgb, alpha)


def roots(rng, pal, ground):
    rgb = quantize(0.35 + (fbm(rng, T, 3, 2) - 0.5) * 0.5, ground, 1.0)
    for _ in range(3):
        x = rng.integers(0, T)
        w = rng.integers(1, 3)
        for y in range(T):
            x = (x + rng.integers(-1, 2)) % T
            rgb[y, x:x + w] = pal[3]
            rgb[y, (x + w) % T] = pal[1]
    return _final(rgb)


def pipes(rng, pal):
    rgb = quantize(np.full((T, T), 0.3), pal, 0.0)
    for x0 in (2, 9):
        rgb[:, x0:x0 + 5] = pal[3]
        rgb[:, x0] = pal[5]
        rgb[:, x0 + 1] = pal[4]
        rgb[:, x0 + 4] = pal[1]
        for y in (3, 11):
            rgb[y, x0:x0 + 5] = pal[2]
    return _final(rgb)


def books(rng, pal_wood):
    """Estante de livros (face vertical)."""
    rgb = quantize(np.full((T, T), 0.2), pal_wood, 0.0)
    cols = [(110, 30, 40), (40, 60, 110), (40, 90, 60), (120, 90, 40), (80, 40, 100), (140, 120, 90)]
    for shelf in (0, 8):
        rgb[shelf:shelf + 1, :] = pal_wood[4]
        x = 0
        while x < T:
            w = rng.integers(1, 3)
            h = rng.integers(5, 8)
            c = np.array(cols[rng.integers(0, len(cols))], np.float32)
            rgb[shelf + 8 - h:shelf + 8, x:x + w] = c
            rgb[shelf + 8 - h, x:x + w] = c * 1.3
            x += w
            if rng.random() < 0.3:
                x += 1
    return _final(rgb)


def void_tile(rng, pal):
    v = fbm(rng, T, 2, 2) * 0.4
    rgb = quantize(v, pal, 1.0)
    for _ in range(2):
        x, y = rng.integers(0, T, 2)
        rgb[y, x] = (90, 70, 140)
    return _final(rgb)


def stars(rng, pal):
    rgb = quantize(fbm(rng, T, 2, 2) * 0.5, pal, 1.0)
    alpha = np.full((T, T), 255, np.float32)
    for _ in range(3):
        x, y = rng.integers(0, T, 2)
        rgb[y, x] = (230, 220, 255)
        alpha[y, x] = EMISSIVE_ALPHA
    return rgba(rgb, alpha)


def gold_trim(rng, pal):
    v = 0.6 + (value_noise(rng, T, 2) - 0.5) * 0.3
    rgb = quantize(v, pal, 0.5)
    rgb[0:2, :] = pal[5]
    rgb[-2:, :] = pal[1]
    rgb[7:9, ::4] = pal[5]
    return _final(rgb)


def tombstone_ground(rng, pal):
    return dirt(rng, pal, pebbles=10)


def lab_tiles(rng, pal):
    v = 0.55 + (fbm(rng, T, 2, 2) - 0.5) * 0.25
    rgb = quantize(v, pal, 0.4)
    mask = np.ones((T, T), bool)
    mask[::8, :] = False
    mask[:, ::8] = False
    rgb = shade_edges(rgb, mask, 1.1, 0.85)
    rgb[~mask] = pal[1]
    # manchas
    m = fbm(rng, T, 3, 2) > 0.66
    rgb[m] = RAMPS["blood"][3]
    return _final(rgb)


# ----------------------------------------------------------------------------- catálogo
R = RAMPS
RECIPES = {
    # genéricos
    "void": lambda g: void_tile(g, R["void"]),
    "stars": lambda g: stars(g, R["void"]),
    # Ato I — Lua Sangrenta
    "forest_floor": lambda g: grass(g, R["grass_dead"], flowers=0),
    "forest_grass": lambda g: grass(g, R["grass"], flowers=1, flower_col=(150, 30, 40)),
    "forest_dirt": lambda g: dirt(g, R["dirt"]),
    "forest_roots": lambda g: roots(g, R["wood_dark"], R["dirt"]),
    "cobble": lambda g: voronoi_stones(g, R["stone"], 6, cracks=0.4),
    "cobble_moss": lambda g: voronoi_stones(g, R["stone"], 6, moss=R["stone_moss"]),
    "castle_wall": lambda g: ashlar(g, R["stone"]),
    "castle_brick": lambda g: bricks(g, R["stone"]),
    "castle_top": lambda g: wall_top(g, R["stone"]),
    "roof_red": lambda g: roof(g, R["mud_red"]),
    "roof_slate": lambda g: roof(g, R["tile_dark"]),
    "rock_wall": lambda g: bricks(g, R["stone_warm"], h=8, w=8, rough=0.9),
    "rock_top": lambda g: wall_top(g, R["stone_warm"]),
    "crypt_floor": lambda g: voronoi_stones(g, R["tile_dark"], 4, cracks=0.8),
    "grave_dirt": lambda g: tombstone_ground(g, R["mud_red"]),
    "carpet_red": lambda g: carpet(g, R["carpet"], trim=R["marble_gold"]),
    "wood_floor": lambda g: planks(g, R["wood"]),
    "wood_wall": lambda g: planks(g, R["wood_dark"], vertical=True),
    "glass_red": lambda g: stained_glass(g, R["glass_red"], R["tile_dark"]),
    "blood_pool": lambda g: liquid(g, R["blood"], bright=0.45),
    "water": lambda g: liquid(g, R["water"], bright=0.5),
    "acid": lambda g: liquid(g, ramp("0a1a08", "12300e", "1e4a14", "2e6a1c", "46902a", "68b83c"), emissive=True, bright=0.5),
    "bones": lambda g: bones(g, R["bone"], R["dirt"]),
    # Ato II — Forja
    "forge_plate": lambda g: metal_plate(g, R["metal"], rust=R["rust"]),
    "forge_wall": lambda g: bricks(g, R["rust"], h=4, w=8),
    "forge_brick": lambda g: bricks(g, R["mud_red"], h=4, w=6),
    "forge_top": lambda g: metal_plate(g, R["metal"], rivets=False),
    "grate": lambda g: grate(g, R["metal"]),
    "gear_floor": lambda g: gears_floor(g, R["brass"]),
    "copper_plate": lambda g: metal_plate(g, R["copper"]),
    "pipes": lambda g: pipes(g, R["copper"]),
    "lava": lambda g: liquid(g, R["lava"], emissive=True, bright=0.6),
    "soot_floor": lambda g: voronoi_stones(g, R["tile_dark"], 5, cracks=0.3),
    # Ato III — Catedral da Carne
    "cathedral_floor": lambda g: checker(g, R["marble"], R["tile_dark"]),
    "cathedral_wall": lambda g: ashlar(g, R["stone_warm"]),
    "cathedral_top": lambda g: wall_top(g, R["stone_warm"]),
    "flesh": lambda g: flesh(g, R["flesh"]),
    "flesh_wall": lambda g: flesh(g, R["flesh"]),
    "lab_tiles": lambda g: lab_tiles(g, R["marble"]),
    "glass_gold": lambda g: stained_glass(g, R["glass_gold"], R["tile_dark"]),
    "bookshelf": lambda g: books(g, R["wood_dark"]),
    # Ato IV — Observatório do Abismo
    "arcane_floor": lambda g: voronoi_stones(g, R["arcane"], 4, cracks=0.2, flat=True),
    "arcane_wall": lambda g: ashlar(g, R["arcane"]),
    "arcane_top": lambda g: wall_top(g, R["arcane"]),
    "rune_floor": lambda g: rune_stone(g, R["arcane"], R["rune_cyan"]),
    "glass_blue": lambda g: stained_glass(g, R["glass_blue"], R["void"]),
    "library_floor": lambda g: planks(g, R["wood_dark"], w=8),
    "astral": lambda g: stars(g, R["arcane"]),
    # Ato V — Trono da Graça
    "marble_floor": lambda g: marble(g, R["marble"], gold=R["marble_gold"]),
    "marble_wall": lambda g: ashlar(g, R["marble"]),
    "marble_top": lambda g: wall_top(g, R["marble"]),
    "gold_trim": lambda g: gold_trim(g, R["marble_gold"]),
    "marble_cracked": lambda g: voronoi_stones(g, R["marble"], 4, cracks=1.0, flat=True),
    "glass_white": lambda g: stained_glass(g, R["glass_gold"], R["marble"]),
    # Santuário
    "sanctuary_floor": lambda g: voronoi_stones(g, R["stone_warm"], 4, cracks=0.2),
    "sanctuary_wall": lambda g: ashlar(g, R["stone_warm"]),
    "sanctuary_top": lambda g: wall_top(g, R["stone_warm"]),
    "rune_gold": lambda g: rune_stone(g, R["stone_warm"], R["glass_gold"]),
}

VARIANTS = 4


class Atlas:
    """Atlas de texturas: cada nome tem VARIANTS variações (16x16) em uma textura 256x256/512x512."""

    def __init__(self, names, seed=7):
        names = list(dict.fromkeys(names))
        slots = len(names) * VARIANTS
        side = 256
        while (side // T) ** 2 < slots:
            side *= 2
        self.side = side
        per_row = side // T
        self.image = np.zeros((side, side, 4), np.uint8)
        self.rects = {}
        k = 0
        for n in names:
            recipe = RECIPES[n]
            for v in range(VARIANTS):
                rng = _rng(zlib.crc32(f"{seed}:{n}:{v}".encode()))
                tile = recipe(rng)
                cx, cy = k % per_row, k // per_row
                self.image[cy * T:(cy + 1) * T, cx * T:(cx + 1) * T] = tile
                self.rects.setdefault(n, []).append((cx, cy))
                k += 1

    def uv(self, name, variant=0):
        """(u0, v0, u1, v1) com origem embaixo (convenção do Panda3D)."""
        cx, cy = self.rects[name][variant % VARIANTS]
        s = self.side
        eps = 0.01 / s
        u0 = cx * T / s + eps
        u1 = (cx + 1) * T / s - eps
        v1 = 1.0 - cy * T / s - eps
        v0 = 1.0 - (cy + 1) * T / s + eps
        return u0, v0, u1, v1
