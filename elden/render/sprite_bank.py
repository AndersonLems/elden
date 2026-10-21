"""Banco de folhas de sprites carregadas como texturas (personagens) e atlas de objetos de cenário."""
import json
import os

import numpy as np
from PIL import Image

from ..core.paths import cache_dir
from ..art import spritegen, props_art
from .textures import to_texture, frame_uv

PROP_ATLAS_VERSION = 5


class Sheet:
    def __init__(self, sprite_id, img, meta):
        self.id = sprite_id
        self.meta = meta
        self.size = meta["frame"]
        self.H, self.W = img.shape[:2]
        self.tex = to_texture(img, "sheet_" + sprite_id)
        self.anims = meta["anims"]
        rects = meta["rects"]
        self.uvs = [frame_uv(cx * self.size, cy * self.size, self.size, self.W, self.H) for cx, cy in rects]
        self.world_size = self.size / 16.0

    def resolve(self, anim):
        if anim in self.anims:
            return anim
        for alt in (spritegen_alias(anim), "idle"):
            if alt in self.anims:
                return alt
        return next(iter(self.anims))

    def frame(self, anim, dir_idx, t_or_p, loop_time=True, fps=10.0):
        a = self.anims[self.resolve(anim)]
        n = a["n"]
        if a["loop"] and loop_time:
            i = int(t_or_p * fps) % n
        else:
            i = min(n - 1, max(0, int(t_or_p * n)))
        return self.uvs[a["dirs"][dir_idx][i]]


def spritegen_alias(anim):
    from ..art.anims import ALIASES
    return ALIASES.get(anim, "slash_r")


class SpriteBank:
    def __init__(self):
        self.sheets = {}
        self.pending = {}

    def request(self, sprite_id, anims):
        if sprite_id in self.sheets:
            return
        cur = self.pending.setdefault(sprite_id, set())
        cur.update(anims)

    def load_pending(self, progress=None):
        if not self.pending:
            return
        reqs = [(sid, sorted(a)) for sid, a in self.pending.items()]
        paths = spritegen.ensure_sheets(reqs, progress)
        for sid, (png, js) in paths.items():
            img, meta = spritegen.load_sheet(png, js)
            self.sheets[sid] = Sheet(sid, img, meta)
        self.pending.clear()

    def get(self, sprite_id):
        return self.sheets.get(sprite_id)


class PropAtlas:
    """Todas as artes de objetos/decoração empacotadas numa textura (gerada uma vez e mantida em cache)."""

    def __init__(self):
        d = os.path.join(cache_dir(), "props")
        os.makedirs(d, exist_ok=True)
        png = os.path.join(d, f"props_v{PROP_ATLAS_VERSION}.png")
        js = os.path.join(d, f"props_v{PROP_ATLAS_VERSION}.json")
        if os.path.exists(png) and os.path.exists(js):
            img = np.array(Image.open(png).convert("RGBA"))
            with open(js) as f:
                self.entries = json.load(f)
        else:
            img, self.entries = self._build()
            Image.fromarray(img, "RGBA").save(png)
            with open(js, "w") as f:
                json.dump(self.entries, f)
        self.H, self.W = img.shape[:2]
        self.tex = to_texture(img, "props")
        self.uv_cache = {}

    def _build(self):
        items = []
        for name in props_art.PROP_SPRITES:
            for vi, frames in enumerate(props_art.build_prop(name)):
                for fi, f in enumerate(frames):
                    items.append((name, vi, fi, f))
        items.sort(key=lambda it: -it[3].shape[0])
        W = 1024
        x = y = row_h = 0
        placed = []
        for name, vi, fi, f in items:
            h, w = f.shape[:2]
            if x + w > W:
                x = 0
                y += row_h + 1
                row_h = 0
            placed.append((name, vi, fi, x, y, w, h, f))
            x += w + 1
            row_h = max(row_h, h)
        H = 1
        while H < y + row_h + 1:
            H *= 2
        img = np.zeros((H, W, 4), np.uint8)
        entries = {}
        for name, vi, fi, x, y, w, h, f in placed:
            img[y:y + h, x:x + w] = f
            entries.setdefault(name, {}).setdefault(str(vi), {})[str(fi)] = [x, y, w, h]
        return img, entries

    def has(self, name):
        return name in self.entries

    def variants(self, name):
        return len(self.entries.get(name, {"0": 0}))

    def frames(self, name, variant=0):
        v = self.entries.get(name) or self.entries["crate"]
        fr = v.get(str(variant % len(v))) or v["0"]
        return len(fr)

    def info(self, name, variant=0, frame=0):
        """(uv, largura_mundo, altura_mundo)."""
        key = (name, variant, frame)
        if key in self.uv_cache:
            return self.uv_cache[key]
        v = self.entries.get(name) or self.entries["crate"]
        fr = v.get(str(variant % len(v))) or v["0"]
        x, y, w, h = fr.get(str(frame % len(fr)))
        uv = frame_uv(x, y, None, self.W, self.H, w, h)
        out = (uv, w / 16.0, h / 16.0)
        self.uv_cache[key] = out
        return out
