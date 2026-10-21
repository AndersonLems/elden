"""Tela da interface: superfície do pygame em resolução reduzida (pixels nítidos) enviada como textura."""
import os

import pygame

from . import theme

_FONT_CACHE = {}
_FONT_PATH = None


def _find_font():
    global _FONT_PATH
    if _FONT_PATH is not None:
        return _FONT_PATH
    cands = []
    try:
        for name in ("dejavusans", "dejavusanscondensed", "liberationsans", "arial", "verdana", "segoeui", "freesans"):
            p = pygame.font.match_font(name)
            if p:
                cands.append(p)
    except Exception:
        pass
    _FONT_PATH = cands[0] if cands else ""
    return _FONT_PATH


def font(size, bold=False):
    key = (size, bold)
    f = _FONT_CACHE.get(key)
    if f is None:
        path = _find_font()
        try:
            f = pygame.font.Font(path or None, size)
        except Exception:
            f = pygame.font.Font(None, size + 4)
        f.set_bold(bold)
        _FONT_CACHE[key] = f
    return f


class Canvas:
    def __init__(self):
        if not pygame.get_init():
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            pygame.init()
        pygame.font.init()
        self.surf = None
        self.w = self.h = 0
        self.scale = 2

    def begin(self, win_w, win_h):
        sc = max(1, round(win_h / 360))
        w, h = win_w // sc, win_h // sc
        if self.surf is None or (w, h) != (self.w, self.h):
            self.surf = pygame.Surface((w, h), pygame.SRCALPHA)
            self.w, self.h = w, h
        self.scale = sc
        self.surf.fill((0, 0, 0, 0))
        return self.surf

    def to_bytes(self):
        return pygame.image.tobytes(self.surf, "BGRA", True)

    def mouse_to_canvas(self, mx, my):
        """Coordenadas do mouse (-1..1) para pixels da tela da interface."""
        return (mx + 1) * 0.5 * self.w, (1 - my) * 0.5 * self.h
