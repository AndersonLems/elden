"""Vistas: sincronizam o estado da simulação com nós Panda3D (sprites, sombras, objetos, cenário)."""
import math

from panda3d.core import LVecBase4f, NodePath, TransparencyAttrib, DepthTestAttrib, RenderAttrib

from ..core.data import DB
from ..art import spritegen
from ..art.spritegen import dir_index
from .geom import card, MeshBuilder
from . import shader_lib

PX = 16.0
_cards = {}


def get_card(w, h, ay):
    key = (round(w, 4), round(h, 4), round(ay, 4))
    if key not in _cards:
        _cards[key] = card(w, h, (0.5, ay))
    return _cards[key]


def snap(x, y, z):
    # O centro da câmera já é estabilizado em pixels; preservar coordenadas do
    # mundo evita deformar relações espaciais na projeção rotacionada.
    return x, y, z


STATUS_TINT = {"congelamento": (0.6, 0.85, 1.3), "queimadura": (1.25, 0.85, 0.7), "maldicao": (0.85, 0.7, 1.15),
               "choque": (1.1, 1.1, 1.3), "sangramento": (1.15, 0.8, 0.8)}


class ActorView:
    def __init__(self, scene, actor, sprite_id):
        self.scene = scene
        self.actor = actor
        self.sprite_id = sprite_id
        self.sheet = scene.bank.get(sprite_id)
        self.node = None
        self.sil = None
        self.shadow = None
        self._make()

    def _make(self):
        sh = self.sheet
        ws = sh.world_size
        ay = 1.0 - 0.9
        base = get_card(ws, ws, ay)
        self.node = base.copy_to(self.scene.pipe.sprite_root)
        self.node.set_texture(sh.tex)
        self.visual_scale = 1.18 if self.actor.kind == "player" else (1.12 if getattr(self.actor, "is_boss", False) else 1.0)
        self.node.set_scale(self.visual_scale)
        self.node.set_shader_input("u_sheet", LVecBase4f(1.0 / sh.W, 1.0 / sh.H, 1.0,
                                                          1.0 if self.actor.kind == "player" else 0.0))
        self.node.set_shader_input("u_sprite", LVecBase4f(0.02, 0, 0, 0))
        r = max(0.25, self.actor.radius * 1.25)
        self.shadow = self.scene.shadow_card(r)
        if self.actor.kind == "player":
            self.sil = base.copy_to(self.scene.pipe.sprite_root)
            self.sil.set_texture(sh.tex)
            self.sil.set_scale(self.visual_scale)
            self.sil.set_shader(shader_lib.load("sprite.vert", "silhouette.frag"))
            self.sil.set_attrib(DepthTestAttrib.make(RenderAttrib.M_greater))
            self.sil.set_depth_write(False)
            self.sil.set_bin("fixed", 30)
            self.sil.set_shader_input("u_tint", LVecBase4f(0.9, 0.75, 0.4, 1))

    def set_sprite(self, sprite_id):
        if sprite_id == self.sprite_id:
            return
        sheet = self.scene.bank.get(sprite_id)
        if sheet is None:
            return
        self.remove()
        self.sprite_id = sprite_id
        self.sheet = sheet
        self._make()

    def update(self, dt):
        a = self.actor
        sid = self.scene.sprite_for(a)
        if sid != self.sprite_id:
            self.set_sprite(sid)
        sh = self.sheet
        di, mirror = dir_index(a.facing)
        anim = a.anim
        if a.anim_p is not None:
            uv = sh.frame(anim, di, a.anim_p, loop_time=False)
        else:
            fps = 10.0
            if anim in ("run", "sprint"):
                fps = 12.0 * max(0.6, min(1.6, math.hypot(a.move_x, a.move_z) / max(1.0, a.base_speed)))
            uv = sh.frame(anim, di, a.anim_t, loop_time=True, fps=fps)
        x, y, z = snap(a.x, a.y, a.z)
        n = self.node
        n.set_pos(x, y, z)
        n.set_shader_input("u_frame", LVecBase4f(*uv))
        n.set_shader_input("u_sprite", LVecBase4f(0.02, 1.0 if mirror else 0.0, 0, 0))
        # cor: flash de dano, tinta de status, aura de elite, invisibilidade
        tint = [1.0, 1.0, 1.0, 1.0]
        for st, c in STATUS_TINT.items():
            if a.status.has(st):
                tint = [tint[0] * c[0], tint[1] * c[1], tint[2] * c[2], 1.0]
                break
        if getattr(a, "invisible", 0) > 0 or getattr(a, "mist_time", 0) > 0:
            tint[3] = 0.35
        if a.dead and a.kind == "enemy" and a.death_time > 1.8:
            tint[3] = max(0.0, 1.0 - (a.death_time - 1.8) / 1.0)
        n.set_shader_input("u_tint", LVecBase4f(*tint))
        fl = a.flash
        fc = a.flash_color
        if a.broken > 0:
            fl = max(fl, 0.35 + 0.25 * math.sin(a.t * 18))
            fc = (1.0, 0.85, 0.3)
        n.set_shader_input("u_flash", LVecBase4f(fc[0] * 2.5, fc[1] * 2.5, fc[2] * 2.5, min(0.85, fl)))
        glow = (0, 0, 0, 0)
        aura = getattr(a, "aura", None)
        if aura:
            pulse = 0.18 + 0.08 * math.sin(a.t * 4)
            glow = (aura[0] * pulse, aura[1] * pulse, aura[2] * pulse, 0)
        if a.kind == "player":
            corr = self.scene.corruption_glow
            if corr > 0:
                glow = (glow[0] + 0.25 * corr, glow[1], glow[2] + 0.05 * corr, 0)
            if a.transformed:
                glow = (glow[0] + 0.04, glow[1] + 0.05, glow[2] + 0.1, 0)
        n.set_shader_input("u_glow", LVecBase4f(*glow))
        if self.sil is not None:
            self.sil.set_pos(x, y, z)
            self.sil.set_shader_input("u_frame", LVecBase4f(*uv))
            self.sil.set_shader_input("u_sprite", LVecBase4f(0.02, 1.0 if mirror else 0.0, 0, 0))
        # sombra no chão
        g = self.scene.world.level.ground_at(a.x, a.z)
        if g is None or getattr(a, "flying", False) and g is None:
            self.shadow.hide()
        else:
            self.shadow.show()
            hgt = max(0.0, a.y - g)
            k = max(0.3, 1.0 - hgt * 0.15)
            self.shadow.set_pos(a.x, g + 0.02, a.z)
            self.shadow.set_scale(k)
        n.show() if a.visible else n.hide()

    def remove(self):
        for nd in (self.node, self.sil, self.shadow):
            if nd is not None:
                nd.remove_node()
        self.node = self.sil = self.shadow = None


class CloneView:
    def __init__(self, scene, clone):
        self.scene = scene
        self.clone = clone
        sid = scene.sprite_for(clone.owner)
        self.sheet = scene.bank.get(sid)
        ws = self.sheet.world_size
        self.node = get_card(ws, ws, 0.1).copy_to(scene.pipe.sprite_root)
        self.node.set_texture(self.sheet.tex)

    def update(self, dt):
        c = self.clone
        di, mirror = dir_index(c.facing)
        uv = self.sheet.frame(c.anim, di, c.anim_p if c.anim_p is not None else c.anim_t, loop_time=c.anim_p is None)
        x, y, z = snap(c.x, c.y, c.z)
        self.node.set_pos(x, y, z)
        self.node.set_shader_input("u_frame", LVecBase4f(*uv))
        self.node.set_shader_input("u_sprite", LVecBase4f(0.03, 1.0 if mirror else 0.0, 0, 0))
        a = max(0.0, min(1.0, c.life / max(0.01, c.max_life))) * 0.8
        self.node.set_shader_input("u_tint", LVecBase4f(0.2, 0.1, 0.35, a))
        self.node.set_shader_input("u_glow", LVecBase4f(0.15, 0.05, 0.3, 0))
        self.node.set_shader_input("u_flash", LVecBase4f(0, 0, 0, 0))

    def remove(self):
        self.node.remove_node()


PROP_SPRITE_DEFAULT = {"grace": "grace", "door": "gate_iron", "lever": "lever", "plate": "plate", "dial": "dial",
                       "chest": "chest", "crystal": "crystal", "mirror": "mirror", "emitter": "emitter", "valve": "valve",
                       "gear_socket": "gear_socket", "gear": "gear", "power_node": "power_node", "portal": "portal",
                       "exit": "stairs_down", "document": "note", "altar": "altar", "breakable": "barrel",
                       "breakable_wall": "cracked_wall", "arena_pillar": "pillar", "hazard": "spikes", "decor": "crate",
                       "seq_button": "button"}


class PropView:
    """Objeto do cenário com quadros por estado/animação a partir do atlas de objetos."""

    def __init__(self, scene, prop):
        self.scene = scene
        self.prop = prop
        t = prop.spec.get("type")
        self.type = t
        name = prop.sprite or PROP_SPRITE_DEFAULT.get(t, "crate")
        if t == "hazard":
            name = {"spikes": "spikes", "steam": "pipe_vent", "flame": "flame_vent", "saw": "saw_hazard"}.get(prop.hz_kind, "spikes")
        if t == "exit" and prop.sprite in (None, "exit"):
            name = "stairs_down"
        if not scene.props.has(name):
            name = PROP_SPRITE_DEFAULT.get(t, "crate")
        self.name = name
        self.variant = (int(prop.x * 7 + prop.z * 3)) % max(1, scene.props.variants(name))
        self.nframes = scene.props.frames(name, self.variant)
        uv, w, h = scene.props.info(name, self.variant, 0)
        self.w, self.h = w, h
        self.node = get_card(w, h, 0.0).copy_to(scene.pipe.sprite_root)
        self.node.set_texture(scene.props.tex)
        self.node.set_shader_input("u_sprite", LVecBase4f(0.05, 0, 0, 0))
        self.node.set_shader_input("u_flash", LVecBase4f(0, 0, 0, 0))
        self.node.set_shader_input("u_glow", LVecBase4f(0, 0, 0, 0))
        self.node.set_shader_input("u_tint", LVecBase4f(1, 1, 1, 1))
        self.t = 0.0
        self.shadow = None
        if t in ("breakable", "chest", "decor", "arena_pillar", "dial", "mirror", "crystal", "lever", "valve", "power_node",
                 "gear_socket", "grace", "altar"):
            self.shadow = scene.shadow_card(min(0.6, w * 0.35))

    def frame_index(self):
        p = self.prop
        t = self.type
        n = self.nframes
        if t in ("chest", "lever", "crystal"):
            return 1 if p.state else 0
        if t in ("dial", "mirror", "valve"):
            return p.state % n
        if t == "plate":
            return 1 if getattr(p, "pressed", False) else 0
        if t == "gear_socket":
            return 0 if not p.has_gear else 1 + p.rotation % 4
        if t == "power_node":
            return (1 if p.state else 0) + (2 if getattr(p, "powered", False) else 0)
        if t == "hazard":
            return {"off": 0, "warn": 1, "on": 2}.get(p.phase, 0) % n
        if n > 1:
            return int(self.t * 8) % n
        return 0

    def update(self, dt):
        self.t += dt
        p = self.prop
        uv, w, h = self.scene.props.info(self.name, self.variant, self.frame_index())
        x, y, z = snap(p.x, p.y, p.z)
        yoff = 0.0
        if self.type == "door":
            yoff = p.anim_open * (self.h - 0.15)
            if p.anim_open > 0.98:
                self.node.hide()
            else:
                self.node.show()
        self.node.set_pos(x, y + yoff, z)
        self.node.set_shader_input("u_frame", LVecBase4f(*uv))
        if self.type in ("seq_button",):
            self.node.set_shader_input("u_glow", LVecBase4f(p.lit * 0.8, p.lit * 0.7, p.lit * 0.3, 0))
        if self.type == "portal" or (self.type == "exit" and self.name == "portal_gate"):
            avail = p.active if self.type == "portal" else p.available()
            self.node.set_shader_input("u_tint", LVecBase4f(1, 1, 1, 1.0 if avail else 0.55))
        if self.type == "grace" and not p.discovered:
            self.node.set_shader_input("u_tint", LVecBase4f(0.6, 0.6, 0.6, 1.0))
        elif self.type == "grace":
            self.node.set_shader_input("u_tint", LVecBase4f(1, 1, 1, 1))
        if self.shadow is not None:
            self.shadow.set_pos(p.x, p.y + 0.02, p.z)
        vis = getattr(p, "visible", True) and p.alive
        if not vis:
            self.node.hide()

    def remove(self):
        self.node.remove_node()
        if self.shadow is not None:
            self.shadow.remove_node()


class PlatformView:
    def __init__(self, scene, plat):
        self.scene = scene
        self.plat = plat
        hx, hz = plat.half
        t = plat.thick
        atlas = scene.level_atlas
        tex = plat.spec.get("tex", scene.platform_tex)
        u0, v0, u1, v1 = atlas.uv(tex, 0)
        mb = MeshBuilder()
        mb.quad((-hx, 0, -hz), (hx, 0, -hz), (hx, 0, hz), (-hx, 0, hz), (0, 1, 0), (u0, v0), (u1, v1))
        mb.quad((-hx, -t, -hz), (hx, -t, -hz), (hx, 0, -hz), (-hx, 0, -hz), (0, 0, -1), (u0, v0), (u1, v1),
                color=(0.7, 0.7, 0.7, 0.0))
        self.node = mb.build("platform")
        self.node.reparent_to(scene.pipe.world_root)
        self.node.set_texture(scene.level_tex)

    def update(self, dt):
        p = self.plat
        self.node.set_pos(p.x, p.y, p.z)

    def remove(self):
        self.node.remove_node()


class BeamView:
    """Feixes de luz dos emissores (puzzles de espelhos)."""

    def __init__(self, scene, emitter):
        self.scene = scene
        self.e = emitter

    def update(self, dt):
        e = self.e
        fx = self.scene.fx
        col = tuple(c * 3.0 for c in e.color)
        for (x0, z0, x1, z1) in e.beam:
            L = math.hypot(x1 - x0, z1 - z0)
            n = max(2, int(L * 4 * dt * 60 / 6))
            for _ in range(n):
                t = fx.rng.random()
                p = (x0 + (x1 - x0) * t, e.y + 1.0 + fx.rng.uniform(-0.05, 0.05), z0 + (z1 - z0) * t)
                fx.add.emit(p, 1, 0.1, (0.05, 0.12), (2, 1), (*col, 1.0), None, 0, 1.0)
        if e.beam:
            x1, z1 = e.beam[-1][2], e.beam[-1][3]
            fx.light((x1, e.y + 1.0, z1), e.color, 1.2, 3.0, 0.05)

    def remove(self):
        pass
