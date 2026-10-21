"""Desenho de elementos de interface em pixel art (texto, painéis ornamentados, barras, listas, abas)."""
import pygame

from .canvas import font
from . import theme as T


def text(surf, s, pos, size=11, color=T.TEXT, align="topleft", shadow=True, bold=False, alpha=255):
    s = str(s)
    f = font(size, bold)
    img = f.render(s, False, color)
    if alpha < 255:
        img.set_alpha(alpha)
    r = img.get_rect(**{align: (int(pos[0]), int(pos[1]))})
    if shadow:
        sh = f.render(s, False, (8, 6, 8))
        if alpha < 255:
            sh.set_alpha(alpha)
        surf.blit(sh, r.move(1, 1))
    surf.blit(img, r)
    return r


def text_width(s, size=11, bold=False):
    return font(size, bold).size(str(s))[0]


def wrap(s, size, width, bold=False):
    f = font(size, bold)
    out = []
    for para in str(s).split("\n"):
        words = para.split(" ")
        line = ""
        for w in words:
            test = (line + " " + w).strip()
            if f.size(test)[0] <= width:
                line = test
            else:
                if line:
                    out.append(line)
                line = w
        out.append(line)
    return out


def text_block(surf, s, x, y, width, size=11, color=T.TEXT, line_h=None, max_lines=None, align="left"):
    lines = wrap(s, size, width)
    lh = line_h or size + 3
    if max_lines:
        lines = lines[:max_lines]
    for i, l in enumerate(lines):
        if align == "center":
            text(surf, l, (x + width // 2, y + i * lh), size, color, "midtop")
        else:
            text(surf, l, (x, y + i * lh), size, color)
    return len(lines) * lh


def panel(surf, rect, style="normal", alpha=None):
    r = pygame.Rect(rect)
    fill = {"normal": T.PANEL, "dark": (10, 8, 10, 235), "light": T.PANEL2, "red": (40, 10, 14, 230)}.get(style, T.PANEL)
    if alpha is not None:
        fill = (*fill[:3], alpha)
    s = pygame.Surface(r.size, pygame.SRCALPHA)
    s.fill(fill)
    # textura sutil de pontos
    for y in range(2, r.h - 2, 4):
        for x in range((y // 4) % 2 * 2 + 2, r.w - 2, 6):
            s.set_at((x, y), (fill[0] + 6, fill[1] + 5, fill[2] + 6, fill[3]))
    surf.blit(s, r.topleft)
    edge = T.GOLD_DIM if style != "red" else (150, 60, 60)
    pygame.draw.rect(surf, (6, 4, 6), r, 1)
    pygame.draw.rect(surf, edge, r.inflate(-2, -2), 1)
    pygame.draw.rect(surf, (edge[0] // 2, edge[1] // 2, edge[2] // 2), r.inflate(-4, -4), 1)
    # cantos ornamentados
    for (cx, cy, sx, sy) in ((r.left + 1, r.top + 1, 1, 1), (r.right - 2, r.top + 1, -1, 1), (r.left + 1, r.bottom - 2, 1, -1),
                             (r.right - 2, r.bottom - 2, -1, -1)):
        for i in range(4):
            surf.set_at((cx + sx * i, cy), T.GOLD)
            surf.set_at((cx, cy + sy * i), T.GOLD)
        surf.set_at((cx + sx * 2, cy + sy * 2), T.GOLD)
    return r


def divider(surf, x0, x1, y, color=T.GOLD_DIM):
    pygame.draw.line(surf, color, (x0, y), (x1, y))
    mid = (x0 + x1) // 2
    pygame.draw.polygon(surf, T.GOLD, [(mid - 3, y), (mid, y - 3), (mid + 3, y), (mid, y + 3)])


def bar(surf, rect, frac, color, back=(30, 22, 26), ghost=None, ghost_color=(240, 230, 200), border=True, segments=0, shine=True):
    r = pygame.Rect(rect)
    pygame.draw.rect(surf, (6, 4, 6), r)
    inner = r.inflate(-2, -2)
    pygame.draw.rect(surf, back, inner)
    if ghost is not None and ghost > frac:
        g = inner.copy()
        g.w = int(inner.w * max(0.0, min(1.0, ghost)))
        pygame.draw.rect(surf, ghost_color, g)
    f = inner.copy()
    f.w = int(inner.w * max(0.0, min(1.0, frac)))
    if f.w > 0:
        pygame.draw.rect(surf, color, f)
        if shine and f.h >= 3:
            light = tuple(min(255, c + 45) for c in color)
            pygame.draw.line(surf, light, (f.left, f.top), (f.right - 1, f.top))
            dark = tuple(c * 2 // 3 for c in color)
            pygame.draw.line(surf, dark, (f.left, f.bottom - 1), (f.right - 1, f.bottom - 1))
    if segments:
        for i in range(1, segments):
            x = inner.left + inner.w * i // segments
            pygame.draw.line(surf, (6, 4, 6), (x, inner.top), (x, inner.bottom - 1))
    if border:
        pygame.draw.rect(surf, T.GOLD_DIM, r, 1)
    return r


def key_hint(device, keyboard, gamepad):
    return gamepad if device == "gamepad" else keyboard


class ListView:
    """Lista rolável com seleção (teclado, controle e mouse)."""

    def __init__(self, items=None, row_h=14, visible=10):
        self.items = items or []
        self.sel = 0
        self.scroll = 0
        self.row_h = row_h
        self.visible = visible
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.hover = None

    def set_items(self, items, keep=True):
        self.items = items
        if not keep:
            self.sel = 0
            self.scroll = 0
        self.sel = max(0, min(self.sel, len(items) - 1))

    def current(self):
        if 0 <= self.sel < len(self.items):
            return self.items[self.sel]
        return None

    def move(self, d):
        if not self.items:
            return False
        old = self.sel
        self.sel = (self.sel + d) % len(self.items)
        self._fix_scroll()
        return old != self.sel

    def _fix_scroll(self):
        if self.sel < self.scroll:
            self.scroll = self.sel
        if self.sel >= self.scroll + self.visible:
            self.scroll = self.sel - self.visible + 1

    def mouse(self, mx, my, scroll=0):
        """Atualiza seleção pelo mouse; devolve índice sob o cursor (ou None)."""
        if scroll and self.rect.collidepoint(mx, my):
            self.scroll = max(0, min(max(0, len(self.items) - self.visible), self.scroll - scroll))
        if not self.rect.collidepoint(mx, my):
            return None
        i = self.scroll + int((my - self.rect.top) // self.row_h)
        if 0 <= i < len(self.items):
            self.sel = i
            return i
        return None

    def draw(self, surf, x, y, w, render_row):
        self.rect = pygame.Rect(x, y, w, self.row_h * self.visible)
        end = min(len(self.items), self.scroll + self.visible)
        for i in range(self.scroll, end):
            ry = y + (i - self.scroll) * self.row_h
            sel = i == self.sel
            if sel:
                hl = pygame.Surface((w, self.row_h), pygame.SRCALPHA)
                hl.fill((222, 190, 120, 40))
                surf.blit(hl, (x, ry))
                pygame.draw.rect(surf, T.GOLD_DIM, (x, ry, w, self.row_h), 1)
                pygame.draw.polygon(surf, T.GOLD, [(x - 5, ry + self.row_h // 2 - 3), (x - 2, ry + self.row_h // 2), (x - 5, ry + self.row_h // 2 + 3)])
            render_row(surf, self.items[i], x, ry, w, sel)
        if len(self.items) > self.visible:
            th = self.row_h * self.visible
            pygame.draw.rect(surf, (40, 32, 36), (x + w + 2, y, 2, th))
            hh = max(6, th * self.visible // len(self.items))
            hy = y + (th - hh) * self.scroll // max(1, len(self.items) - self.visible)
            pygame.draw.rect(surf, T.GOLD_DIM, (x + w + 2, hy, 2, hh))


def tabs(surf, x, y, labels, active, size=11, colors=None):
    rects = []
    cx = x
    for i, l in enumerate(labels):
        w = text_width(l, size, True) + 14
        r = pygame.Rect(cx, y, w, size + 8)
        col = colors[i] if colors else T.GOLD
        if i == active:
            pygame.draw.rect(surf, (40, 30, 30), r)
            pygame.draw.rect(surf, col, r, 1)
            text(surf, l, r.center, size, col, "center", bold=True)
        else:
            pygame.draw.rect(surf, (20, 16, 18), r)
            pygame.draw.rect(surf, (70, 60, 56), r, 1)
            text(surf, l, r.center, size, T.MUTED, "center", bold=True)
        rects.append(r)
        cx += w + 3
    return rects
