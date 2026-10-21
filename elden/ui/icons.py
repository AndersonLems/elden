"""Ícones procedurais em pixel art (runas, armas, habilidades, itens, status, nós da árvore)."""
import math
import zlib

import pygame

from . import theme as T

_cache = {}


def _surf(n=16):
    return pygame.Surface((n, n), pygame.SRCALPHA)


def _outline(s):
    w, h = s.get_size()
    out = s.copy()
    for y in range(h):
        for x in range(w):
            if s.get_at((x, y)).a == 0:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < w and 0 <= yy < h and s.get_at((xx, yy)).a > 0:
                        out.set_at((x, y), (10, 8, 10, 255))
                        break
    return out


def cached(key, fn):
    if key not in _cache:
        _cache[key] = _outline(fn())
    return _cache[key]


def weapon_icon(family):
    def make():
        s = _surf()
        steel, grip, gold = (210, 214, 222), (110, 74, 40), (210, 170, 70)
        if family in ("espada", "katana", "rapieira", "espadao"):
            L = {"espadao": 13, "katana": 12, "rapieira": 12}.get(family, 11)
            pygame.draw.line(s, steel, (3, 13), (3 + L * 0.75, 13 - L * 0.75), 2 if family == "espadao" else 1)
            pygame.draw.line(s, gold, (2, 10), (6, 14))
            pygame.draw.line(s, grip, (1, 15), (3, 13))
        elif family == "adagas":
            pygame.draw.line(s, steel, (2, 12), (8, 6))
            pygame.draw.line(s, steel, (8, 13), (14, 7))
        elif family == "machado":
            pygame.draw.line(s, grip, (3, 14), (11, 3), 2)
            pygame.draw.polygon(s, steel, [(9, 2), (15, 4), (13, 9)])
        elif family in ("martelo", "sagrada"):
            pygame.draw.line(s, grip, (3, 14), (10, 5), 2)
            pygame.draw.rect(s, steel if family == "martelo" else gold, (8, 1, 7, 6))
        elif family == "foice":
            pygame.draw.line(s, grip, (4, 15), (9, 1), 1)
            pygame.draw.arc(s, steel, (1, 0, 14, 10), 0.2, 2.6, 2)
        elif family == "corrente":
            for i in range(6):
                pygame.draw.circle(s, steel, (2 + i * 2, 13 - i * 2), 1)
        elif family == "cajado":
            pygame.draw.line(s, grip, (3, 15), (11, 4), 2)
            pygame.draw.circle(s, (160, 120, 255), (12, 3), 2)
        elif family == "grimorio":
            pygame.draw.rect(s, (90, 50, 110), (3, 3, 10, 11))
            pygame.draw.line(s, (220, 200, 160), (5, 5), (11, 5))
            pygame.draw.circle(s, (180, 140, 255), (8, 9), 2)
        elif family == "arma_fogo":
            pygame.draw.line(s, (70, 60, 56), (2, 9), (14, 6), 3)
            pygame.draw.line(s, grip, (3, 10), (5, 14), 2)
        elif family in ("garras", "fera"):
            for k in range(3):
                pygame.draw.line(s, steel, (3 + k * 3, 14), (6 + k * 3, 2))
        else:
            pygame.draw.circle(s, steel, (8, 8), 5)
        return s
    return cached(("w", family), make)


def rune_icon(category, rarity="comum"):
    def make():
        s = _surf()
        col = T.CATEGORY_COLORS.get(category, (200, 200, 200))
        pygame.draw.polygon(s, (70, 64, 70), [(8, 1), (14, 5), (13, 12), (8, 15), (3, 12), (2, 5)])
        pygame.draw.polygon(s, T.RARITY.get(rarity, (190, 186, 176)), [(8, 1), (14, 5), (13, 12), (8, 15), (3, 12), (2, 5)], 1)
        seed = zlib.crc32(category.encode())
        cx, cy = 8, 8
        for k in range(3):
            a = (seed >> (k * 3)) % 8 / 8 * math.tau
            pygame.draw.line(s, col, (cx, cy), (cx + math.cos(a) * 4, cy + math.sin(a) * 4))
        pygame.draw.circle(s, col, (cx, cy), 1)
        return s
    return cached(("r", category, rarity), make)


CLASS_COLORS = {"guerreiro": (200, 170, 110), "ninja": (120, 120, 160), "soldado": (150, 160, 110), "bandido": (200, 90, 70),
                "ladrao": (140, 120, 170), "mago": (140, 110, 240), "clerigo": (240, 220, 150), "vampiro": (200, 40, 70),
                "lobisomem": (170, 140, 110)}


def ability_icon(ability_id, class_id, kind="active"):
    def make():
        s = _surf()
        col = CLASS_COLORS.get(class_id, (200, 200, 200))
        bg = tuple(c // 4 for c in col)
        pygame.draw.rect(s, bg, (1, 1, 14, 14))
        pygame.draw.rect(s, col, (1, 1, 14, 14), 1)
        h = zlib.crc32(ability_id.encode())
        shape = h % 5
        c2 = tuple(min(255, c + 40) for c in col)
        if kind == "ultimate":
            pts = [(8 + math.cos(a) * (6 if i % 2 == 0 else 3), 8 + math.sin(a) * (6 if i % 2 == 0 else 3))
                   for i, a in enumerate([j * math.tau / 10 - math.pi / 2 for j in range(10)])]
            pygame.draw.polygon(s, c2, pts)
        elif shape == 0:
            pygame.draw.line(s, c2, (4, 12), (12, 4), 2)
        elif shape == 1:
            pygame.draw.circle(s, c2, (8, 8), 4, 1)
            pygame.draw.circle(s, c2, (8, 8), 1)
        elif shape == 2:
            pygame.draw.polygon(s, c2, [(8, 3), (13, 12), (3, 12)], 1)
        elif shape == 3:
            for k in range(3):
                pygame.draw.line(s, c2, (4 + k * 3, 12), (6 + k * 3, 4))
        else:
            pygame.draw.arc(s, c2, (3, 3, 10, 10), 0.5, 5.5, 2)
        return s
    return cached(("a", ability_id, kind), make)


def item_icon(kind, item_id=""):
    def make():
        s = _surf()
        if kind == "flask_hp":
            pygame.draw.rect(s, (200, 200, 210), (6, 2, 4, 3))
            pygame.draw.circle(s, (220, 120, 40), (8, 10), 5)
            pygame.draw.circle(s, (255, 200, 90), (7, 9), 2)
        elif kind == "flask_fp":
            pygame.draw.rect(s, (200, 200, 210), (6, 2, 4, 3))
            pygame.draw.circle(s, (60, 110, 230), (8, 10), 5)
            pygame.draw.circle(s, (150, 190, 255), (7, 9), 2)
        elif kind == "chave":
            pygame.draw.circle(s, (210, 170, 70), (5, 5), 3, 1)
            pygame.draw.line(s, (210, 170, 70), (7, 7), (13, 13))
            pygame.draw.line(s, (210, 170, 70), (11, 13), (13, 11))
        elif kind == "reliquia":
            pygame.draw.polygon(s, (230, 200, 120), [(8, 1), (14, 8), (8, 15), (2, 8)])
            pygame.draw.circle(s, (255, 250, 220), (8, 8), 2)
        elif kind == "missao":
            pygame.draw.rect(s, (220, 210, 180), (3, 2, 10, 12))
            for y in (5, 8, 11):
                pygame.draw.line(s, (120, 100, 80), (5, y), (11, y))
        elif kind == "grace":
            pygame.draw.circle(s, (240, 190, 80), (8, 9), 4)
            pygame.draw.polygon(s, (255, 230, 150), [(6, 8), (8, 2), (10, 8)])
        elif kind == "material":
            pygame.draw.polygon(s, (170, 150, 130), [(3, 12), (8, 3), (13, 12)])
            pygame.draw.line(s, (230, 210, 180), (8, 4), (8, 11))
        else:
            pygame.draw.circle(s, (220, 200, 160), (8, 8), 5)
            pygame.draw.circle(s, (255, 240, 200), (7, 7), 2)
        return s
    return cached(("i", kind, item_id), make)


STATUS_ICON_COL = {"sangramento": (210, 30, 50), "queimadura": (240, 120, 40), "congelamento": (120, 190, 240),
                   "choque": (200, 210, 255), "maldicao": (150, 70, 200)}


def status_icon(st):
    def make():
        s = _surf(10)
        c = STATUS_ICON_COL.get(st, (200, 200, 200))
        pygame.draw.circle(s, c, (5, 5), 4)
        pygame.draw.circle(s, (255, 255, 255), (4, 4), 1)
        return s
    return cached(("s", st), make)


def node_icon(node, path_color, owned, available):
    key = ("n", node.get("name"), owned, available)

    def make():
        s = _surf(18)
        col = path_color if (owned or available) else (70, 64, 66)
        types = {e.get("type") for e in node.get("effects", [])}
        big = node.get("cost", 1) >= 3
        if big:
            pygame.draw.polygon(s, (24, 18, 22), [(9, 0), (17, 9), (9, 17), (0, 9)])
            pygame.draw.polygon(s, col, [(9, 0), (17, 9), (9, 17), (0, 9)], 1)
        else:
            pygame.draw.circle(s, (24, 18, 22), (9, 9), 8)
            pygame.draw.circle(s, col, (9, 9), 8, 1)
        if owned:
            pygame.draw.circle(s, col, (9, 9), 5)
        inner = (20, 16, 18) if owned else col
        if "attr" in types:
            pygame.draw.polygon(s, inner, [(9, 5), (12, 9), (10, 9), (10, 13), (8, 13), (8, 9), (6, 9)])
        elif types & {"replace_move", "add_transition", "add_start", "move_effect"}:
            pygame.draw.line(s, inner, (5, 13), (13, 5))
            pygame.draw.line(s, inner, (5, 5), (13, 13))
        elif "unlock" in types:
            pygame.draw.polygon(s, inner, [(9, 4), (13, 9), (9, 14), (5, 9)], 1)
        elif "rune_slot" in types:
            pygame.draw.polygon(s, inner, [(9, 4), (13, 7), (12, 12), (9, 14), (6, 12), (5, 7)], 1)
        elif "trigger" in types or "flag" in types:
            pygame.draw.polygon(s, inner, [(9, 4), (11, 8), (14, 9), (11, 10), (9, 14), (7, 10), (4, 9), (7, 8)])
        else:
            pygame.draw.circle(s, inner, (9, 9), 2)
        return s
    if key not in _cache:
        _cache[key] = make()
    return _cache[key]
