"""Geração e cache de folhas de sprites (personagens) em disco.

Cada folha contém, para cada animação e direção (5 desenhadas; as outras 3 são espelhadas), uma
sequência de quadros. As folhas ficam em cache (PNG + JSON) e são geradas em paralelo quando
uma fase precisa delas.
"""
import hashlib
import json
import math
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image

from ..core.paths import cache_dir
from ..core.data import DB
from . import characters
from .anims import FRAMES, DEFAULT_FRAMES, pose_for
from .rig import render_frame

GEN_VERSION = 7
DIR_ANGLES = [-90, -45, 0, 45, 90]       # S, SE, E, NE, N

BASE_ANIMS = ["idle", "walk", "run", "hurt", "launched", "down", "getup", "stagger", "death", "dodge", "block", "block_hit",
              "jump", "fall"]
PLAYER_ANIMS = BASE_ANIMS + ["sprint", "strafe", "charge", "drink", "interact", "sit", "execute", "roar", "transform", "mist",
                             "pray", "throw", "reload"]


def _sprite_dir():
    d = os.path.join(cache_dir(), "sprites")
    os.makedirs(d, exist_ok=True)
    return d


def anims_for_moves(move_ids):
    out = set()
    moves = DB.moves
    for m in move_ids:
        if m in moves:
            out.add(moves[m].get("anim", "slash_r"))
    return out


def player_anims():
    """Todas as animações que qualquer golpe de jogador pode usar."""
    out = set(PLAYER_ANIMS)
    for mid, m in DB.moves.items():
        if not mid.startswith(("esq_", "lobo_", "licano_", "vamp_", "guarda_", "cacador_", "morcego_", "auto_", "cao_", "operario_",
                               "sentinela_", "serra_", "guardiao_", "monge_", "exp_", "cirurgiao_", "aberracao_", "mutante_",
                               "fanatico_", "bruxa_", "bruxo_", "armadura_", "invocacao_", "sombra_", "runica_", "livro_",
                               "ilusao_", "cav_", "anjo_", "espirito_", "celestial_", "vk_", "condessa_", "sf_", "santo_", "ml_",
                               "malachar_", "au_")):
            out.add(m.get("anim", "slash_r"))
    return sorted(out)


def enemy_anims(enemy_id):
    d = DB.enemies[enemy_id]
    out = set(BASE_ANIMS) | {"fly"}
    out |= anims_for_moves([a["move"] for a in d.get("attacks", [])] + [a["move"] for a in d.get("elite", {}).get("attacks", [])])
    return sorted(out)


def boss_anims(boss_id):
    b = DB.bosses[boss_id]
    out = set(BASE_ANIMS) | {"roar", "transform", "howl", "pray", "cast_up", "core_pulse"}
    for ph in b["phases"]:
        out |= anims_for_moves([a["move"] for a in ph["attacks"]])
        out.add(ph.get("anim", "roar"))
    if b.get("intro_anim"):
        out.add(b["intro_anim"])
    return sorted(out)


NPC_ANIMS = ["idle", "walk", "interact", "hammer", "read", "pray", "sit"]


# ---------------------------------------------------------------------------- especificações
def make_rig(sprite_id):
    """sprite_id: 'pl_...' (jogador), 'nome' ou 'nome@escala' (variante de escala, ex.: elites)."""
    base, _, sc = sprite_id.partition("@")
    if base.startswith("pl_"):
        parts = base.split("_")
        cls = parts[1]
        app = {"skin": int(parts[2]), "hair": int(parts[3]), "hair_color": int(parts[4]), "variant": int(parts[5])}
        rig = characters.player_rig(cls, app, transformed=base.endswith("_besta"))
    else:
        rig = characters.rig_for(base)
    if sc:
        k = float(sc)
        spec_scale = rig.scale * k
        rig = rescale(rig, k)
        rig.scale = spec_scale
    return rig


def rescale(rig, k):
    from .rig import Rig
    for attr in ("leg", "torso", "shoulder", "hips", "arm", "head_r", "neck", "limb_w", "leg_w", "torso_w", "torso_d"):
        setattr(rig, attr, getattr(rig, attr) * k)
    rig.frame = int(math.ceil(rig.frame * k / 8.0) * 8)
    return rig


def sheet_key(sprite_id, anims):
    h = hashlib.sha1(json.dumps([GEN_VERSION, sprite_id, sorted(anims), _spec_fingerprint(sprite_id)]).encode()).hexdigest()[:12]
    return f"{sprite_id.replace('@', '_x')}_{h}"


def _spec_fingerprint(sprite_id):
    base = sprite_id.partition("@")[0]
    if base.startswith("pl_"):
        return base
    return json.dumps(characters.SPECS.get(base, {}), sort_keys=True, default=str)


def generate_sheet(sprite_id, anims):
    rig = make_rig(sprite_id)
    two = characters.is_two_handed(rig)
    size = rig.frame
    frames = []
    meta = {"frame": size, "scale": rig.scale, "anims": {}}
    for anim in anims:
        n, loop = FRAMES.get(anim, DEFAULT_FRAMES)
        entry = {"n": n, "loop": loop, "dirs": []}
        for d in DIR_ANGLES:
            idxs = []
            for i in range(n):
                t = (i / n) if loop else (i / max(1, n - 1)) * 0.999
                if not loop and n > 1:
                    # amostra a parte "interessante" de golpes: mais quadros perto do impacto
                    t = (i + 0.5) / n
                img = render_frame(rig, pose_for(anim, t, two), d, size)
                idxs.append(len(frames))
                frames.append(img)
            entry["dirs"].append(idxs)
        meta["anims"][anim] = entry
    cols = max(1, int(math.ceil(math.sqrt(len(frames)))))
    rows = int(math.ceil(len(frames) / cols))
    sheet = np.zeros((rows * size, cols * size, 4), np.uint8)
    rects = []
    for i, f in enumerate(frames):
        cx, cy = i % cols, i // cols
        sheet[cy * size:(cy + 1) * size, cx * size:(cx + 1) * size] = f
        rects.append((cx, cy))
    meta["cols"], meta["rows"] = cols, rows
    meta["rects"] = rects
    return sheet, meta


def _build_and_save(args):
    sprite_id, anims, path_png, path_json = args
    sheet, meta = generate_sheet(sprite_id, anims)
    Image.fromarray(sheet, "RGBA").save(path_png, optimize=False, compress_level=1)
    with open(path_json, "w") as f:
        json.dump(meta, f)
    return sprite_id


def ensure_sheets(requests, progress=None, parallel=True):
    """requests: lista de (sprite_id, anims). Gera os que faltam (em paralelo). Devolve {id: (png, json)}."""
    d = _sprite_dir()
    out, todo = {}, []
    for sid, anims in requests:
        key = sheet_key(sid, anims)
        png, js = os.path.join(d, key + ".png"), os.path.join(d, key + ".json")
        out[sid] = (png, js)
        if not (os.path.exists(png) and os.path.exists(js)):
            todo.append((sid, list(anims), png, js))
    if todo:
        if parallel and len(todo) > 1:
            try:
                workers = max(1, min(len(todo), (os.cpu_count() or 2) - 1))
                with ProcessPoolExecutor(max_workers=workers) as ex:
                    for i, sid in enumerate(ex.map(_build_and_save, todo)):
                        if progress:
                            progress(i + 1, len(todo), sid)
            except Exception:
                for i, t in enumerate(todo):
                    if not os.path.exists(t[2]):
                        _build_and_save(t)
                    if progress:
                        progress(i + 1, len(todo), t[0])
        else:
            for i, t in enumerate(todo):
                _build_and_save(t)
                if progress:
                    progress(i + 1, len(todo), t[0])
    return out


def load_sheet(png, js):
    img = np.array(Image.open(png).convert("RGBA"))
    with open(js) as f:
        meta = json.load(f)
    return img, meta


DIR_MAP = {0: (2, False), 1: (3, False), 2: (4, False), 3: (3, True), 4: (2, True), 5: (1, True), 6: (0, False), 7: (1, False)}


def dir_index(facing_rad):
    """Ângulo de mundo -> (índice de direção desenhada, espelhar)."""
    k = int(round(facing_rad / (math.pi / 4))) % 8
    return DIR_MAP[k]
