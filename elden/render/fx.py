"""Efeitos visuais: partículas em pixels (aditivas e opacas), marcas no chão, rastros e luzes temporárias.

Recebe os eventos da simulação (world.fx) e os traduz em partículas, luzes e tremores de câmera.
"""
import math
import random

import numpy as np
from panda3d.core import (Geom, GeomNode, GeomTriangles, GeomVertexData, LVecBase4f, NodePath, OmniBoundingVolume,
                          TransparencyAttrib)

from .geom import vertex_format, MeshBuilder
from .lights import PointLight
from . import shader_lib

MATERIAL_FX = {
    "flesh": dict(add=False, color=(0.55, 0.02, 0.04, 1.0), color2=(0.25, 0.0, 0.02, 0.0), n=10, speed=4.0, grav=14),
    "bone": dict(add=False, color=(0.85, 0.82, 0.72, 1.0), color2=(0.5, 0.48, 0.42, 0.0), n=8, speed=4.5, grav=16),
    "metal": dict(add=True, color=(3.0, 2.2, 0.8, 1.0), color2=(1.2, 0.3, 0.0, 0.0), n=12, speed=7.0, grav=12),
    "stone": dict(add=False, color=(0.5, 0.48, 0.5, 1.0), color2=(0.3, 0.3, 0.32, 0.0), n=9, speed=4.5, grav=16),
    "ether": dict(add=True, color=(1.2, 0.8, 2.6, 1.0), color2=(0.3, 0.1, 0.8, 0.0), n=12, speed=4.0, grav=0),
    "wood": dict(add=False, color=(0.45, 0.3, 0.16, 1.0), color2=(0.3, 0.2, 0.1, 0.0), n=8, speed=4.0, grav=16),
    "crystal": dict(add=True, color=(1.5, 2.2, 3.0, 1.0), color2=(0.2, 0.5, 1.0, 0.0), n=10, speed=4.0, grav=4),
}

ELEMENT_COLORS = {
    "fisico": (2.2, 2.0, 1.7), "fogo": (3.0, 1.2, 0.3), "gelo": (1.2, 2.2, 3.0), "raio": (2.2, 2.4, 3.2),
    "arcano": (1.6, 0.9, 3.2), "trevas": (0.9, 0.3, 1.6), "sagrado": (3.0, 2.6, 1.4), "sangue": (2.4, 0.15, 0.25),
}

VISUALS = {
    # nome: (cor aditiva, quantidade, velocidade, gravidade, cor de fumaça opaca ou None)
    "fire_burst": ((3.0, 1.1, 0.2), 40, 6.0, -2, (0.15, 0.1, 0.08)),
    "explosion": ((3.2, 1.4, 0.3), 60, 8.0, -1, (0.12, 0.1, 0.09)),
    "holy_burst": ((3.0, 2.6, 1.2), 40, 5.0, -2, None),
    "light_pillar": ((3.2, 2.8, 1.6), 50, 3.0, -12, None),
    "light_spear": ((3.2, 2.8, 1.6), 30, 3.0, -12, None),
    "arcane_burst": ((1.8, 0.9, 3.4), 40, 6.0, 0, None),
    "arcane_pillar": ((1.8, 0.9, 3.4), 40, 3.0, -12, None),
    "rune_pillar": ((0.6, 2.6, 2.2), 40, 3.0, -12, None),
    "rune_circle": ((0.8, 2.4, 2.4), 36, 4.0, -4, None),
    "blood_burst": ((2.4, 0.1, 0.2), 30, 5.0, 8, (0.35, 0.0, 0.02)),
    "frost_nova": ((1.4, 2.4, 3.2), 50, 7.0, 2, None),
    "lightning_strike": ((2.6, 2.8, 3.4), 30, 4.0, -16, None),
    "lightning_line": ((2.6, 2.8, 3.4), 40, 2.0, 0, None),
    "dust_burst": ((0.0, 0.0, 0.0), 0, 0, 0, (0.35, 0.3, 0.26)),
    "rock_spike": ((0.8, 0.6, 0.4), 10, 3.0, 12, (0.4, 0.34, 0.28)),
    "debris": ((0.0, 0.0, 0.0), 0, 0, 0, (0.4, 0.36, 0.34)),
    "silver_burst": ((2.6, 2.6, 3.0), 30, 6.0, 4, None),
    "metal_impact": ((3.0, 2.0, 0.8), 40, 7.0, 10, (0.3, 0.26, 0.22)),
    "tendril": ((2.0, 0.3, 0.3), 24, 3.0, -8, (0.4, 0.05, 0.08)),
    "moon_impact": ((2.6, 0.5, 0.4), 50, 7.0, 6, (0.3, 0.2, 0.2)),
    "divine_impact": ((3.4, 3.0, 2.0), 60, 8.0, 2, None),
    "meteor": ((3.2, 1.4, 0.6), 40, 6.0, 4, (0.2, 0.12, 0.1)),
    "astral_explosion": ((2.0, 1.4, 3.6), 90, 9.0, 0, None),
    "abyss_burst": ((1.0, 0.2, 1.8), 40, 5.0, -4, (0.1, 0.0, 0.15)),
    "curse_burst": ((1.2, 0.3, 1.8), 30, 4.0, -3, None),
    "grace_burst": ((3.0, 2.4, 1.4), 60, 7.0, 0, None),
    "corrupt_burst": ((2.6, 0.6, 1.6), 50, 6.0, 0, None),
    "judgement_aura": ((3.2, 2.8, 1.6), 70, 6.0, -4, None),
    "war_ring": ((2.6, 1.4, 0.5), 0, 0, 0, None),
    "howl_ring": ((1.6, 1.8, 2.6), 0, 0, 0, None),
    "ink_burst": ((0.8, 0.4, 1.4), 30, 5.0, 0, (0.05, 0.02, 0.08)),
    "sand_cloud": ((0.0, 0.0, 0.0), 0, 0, 0, (0.6, 0.55, 0.4)),
    "fire_field": ((3.0, 1.1, 0.2), 0, 0, 0, None),
}

RING_VISUALS = {"shock_ring": (2.4, 2.0, 1.4), "holy_ring": (3.0, 2.6, 1.4), "war_ring": (2.6, 1.4, 0.5), "howl_ring": (1.6, 1.8, 2.6),
                "shock_ring_blue": (1.6, 2.2, 3.4), "steam_ring": (2.4, 2.2, 2.0), "dust_ring": (1.2, 1.0, 0.8),
                "flesh_ring": (2.6, 0.4, 0.5), "rune_ring": (0.8, 2.4, 2.4), "ghost_ring": (1.2, 1.6, 2.4)}

FIELD_VISUALS = {"fire_field": (3.0, 1.1, 0.2), "frost_field": (1.4, 2.2, 3.0), "rune_prison": (0.8, 2.6, 2.4),
                 "black_hole": (1.0, 0.4, 2.0), "spectral_trap": (0.8, 0.6, 2.0), "acid_pool": (0.6, 2.4, 0.4),
                 "gravity_well": (1.4, 0.8, 3.0), "blood_moon_field": (2.4, 0.15, 0.3), "rune_field": (1.0, 0.4, 2.0),
                 "grace_vortex": (3.0, 2.6, 1.6), "hex_circle": (1.4, 0.3, 1.8)}

BEAM_VISUALS = {"arcane_beam": (1.6, 0.9, 3.4), "dark_beam": (1.0, 0.2, 1.8), "laser": (3.4, 1.2, 0.4), "rune_beam": (0.6, 2.6, 2.2),
                "holy_beam": (3.4, 3.0, 2.0), "grace_beam": (3.2, 2.4, 1.6), "core_laser": (3.6, 1.6, 0.4), "blood_beam": (2.6, 0.2, 0.3),
                "flame_jet": (3.2, 1.2, 0.3), "lightning_line": (2.6, 2.8, 3.4)}

PROJ_VISUALS = {
    "fire_bolt": ((3.0, 1.2, 0.3), 3), "ice_shard": ((1.4, 2.4, 3.2), 2), "lightning_bolt": ((2.6, 2.8, 3.4), 3),
    "arcane_lance": ((1.8, 1.0, 3.4), 3), "arcane_lance_big": ((2.0, 1.2, 3.6), 4), "arcane_bolt": ((1.6, 1.0, 3.0), 2),
    "page_bolt": ((1.8, 1.4, 3.0), 2), "bullet": ((3.0, 2.6, 1.6), 2), "bullet_big": ((3.2, 2.6, 1.4), 3),
    "pellet": ((3.0, 2.4, 1.2), 1), "fire_bullet": ((3.2, 1.4, 0.3), 3), "kunai": ((2.0, 2.0, 2.2), 2), "shuriken": ((2.0, 2.0, 2.2), 2),
    "grenade": ((1.4, 1.2, 0.8), 3), "missile": ((3.0, 1.6, 0.6), 3), "holy_bolt": ((3.0, 2.8, 1.8), 3), "holy_lance": ((3.2, 3.0, 2.0), 3),
    "curse_bolt": ((1.4, 0.4, 2.0), 3), "blood_spear": ((2.6, 0.2, 0.3), 3), "acid_glob": ((0.8, 2.6, 0.4), 3),
    "fire_flask": ((3.0, 1.6, 0.4), 3), "steam_ball": ((2.4, 2.2, 2.0), 3), "hot_rivet": ((3.0, 1.4, 0.4), 2),
    "bolt_arrow": ((1.6, 1.4, 1.2), 2), "wind_slash": ((2.0, 2.6, 2.4), 4), "spinning_dagger": ((2.2, 2.2, 2.4), 2),
    "star_bolt": ((2.4, 2.4, 3.2), 2), "bolt": ((2.0, 2.0, 2.0), 2),
}


class ParticleSystem:
    def __init__(self, parent, additive, capacity=3000):
        self.cap = capacity
        self.n = 0
        self.pos = np.zeros((capacity, 3), np.float32)
        self.vel = np.zeros((capacity, 3), np.float32)
        self.life = np.zeros(capacity, np.float32)
        self.max_life = np.ones(capacity, np.float32)
        self.size0 = np.ones(capacity, np.float32)
        self.size1 = np.ones(capacity, np.float32)
        self.col0 = np.zeros((capacity, 4), np.float32)
        self.col1 = np.zeros((capacity, 4), np.float32)
        self.grav = np.zeros(capacity, np.float32)
        self.drag = np.zeros(capacity, np.float32)
        self.additive = additive
        self.node = GeomNode("particles")
        self.node.set_bounds(OmniBoundingVolume())
        self.node.set_final(True)
        self.np = parent.attach_new_node(self.node)
        self.vdata = GeomVertexData("p", vertex_format(), Geom.UH_dynamic)
        self.prim = GeomTriangles(Geom.UH_dynamic)
        self.prim.set_index_type(Geom.NT_uint32)
        g = Geom(self.vdata)
        g.add_primitive(self.prim)
        self.node.add_geom(g)
        self.geom = g

    def emit(self, pos, n=10, speed=3.0, life=(0.3, 0.7), size=(2, 1), color=(1, 1, 1, 1), color_end=None, gravity=0.0,
             drag=2.0, up=0.0, spread=None, direction=None, cone=math.pi, ring=None, box=None):
        n = int(n)
        if n <= 0:
            return
        free = self.cap - self.n
        if n > free:
            n = free
        if n <= 0:
            return
        i0, i1 = self.n, self.n + n
        self.n += n
        rng = np.random.default_rng()
        p = np.array(pos, np.float32)
        if box is not None:
            off = (rng.random((n, 3)) - 0.5) * np.array(box, np.float32)
            self.pos[i0:i1] = p + off
        else:
            self.pos[i0:i1] = p
        if ring is not None:
            ang = rng.random(n) * math.tau
            r = ring
            self.pos[i0:i1, 0] += np.cos(ang) * r
            self.pos[i0:i1, 2] += np.sin(ang) * r
            v = np.stack([np.cos(ang), np.zeros(n), np.sin(ang)], 1) * speed * (0.6 + rng.random((n, 1)) * 0.4)
        elif direction is not None:
            base = math.atan2(direction[1], direction[0])
            ang = base + (rng.random(n) - 0.5) * cone
            sp = speed * (0.4 + rng.random(n) * 0.6)
            v = np.stack([np.cos(ang) * sp, (rng.random(n) - 0.3) * speed * 0.6, np.sin(ang) * sp], 1)
        else:
            d = rng.normal(size=(n, 3)).astype(np.float32)
            d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-6
            v = d * (speed * (0.3 + rng.random((n, 1)) * 0.7))
        v[:, 1] += up
        self.vel[i0:i1] = v
        lo, hi = life
        self.max_life[i0:i1] = lo + rng.random(n) * (hi - lo)
        self.life[i0:i1] = self.max_life[i0:i1]
        self.size0[i0:i1] = size[0]
        self.size1[i0:i1] = size[1]
        c0 = np.array(color if len(color) == 4 else (*color, 1.0), np.float32)
        ce = color_end if color_end is not None else (c0[0] * 0.5, c0[1] * 0.5, c0[2] * 0.5, 0.0)
        c1 = np.array(ce if len(ce) == 4 else (*ce, 0.0), np.float32)
        self.col0[i0:i1] = c0
        self.col1[i0:i1] = c1
        self.grav[i0:i1] = gravity
        self.drag[i0:i1] = drag

    def update(self, dt):
        n = self.n
        if n == 0:
            self.prim.clear_vertices()
            return
        self.life[:n] -= dt
        alive = self.life[:n] > 0
        if not alive.all():
            idx = np.nonzero(alive)[0]
            m = len(idx)
            for arr in (self.pos, self.vel, self.life, self.max_life, self.size0, self.size1, self.col0, self.col1, self.grav, self.drag):
                arr[:m] = arr[idx]
            self.n = n = m
        if n == 0:
            self.prim.clear_vertices()
            return
        self.vel[:n, 1] -= self.grav[:n] * dt
        self.vel[:n] *= np.exp(-self.drag[:n] * dt)[:, None]
        self.pos[:n] += self.vel[:n] * dt

    def rebuild(self):
        n = self.n
        if n == 0:
            self.prim.clear_vertices()
            return
        t = 1.0 - self.life[:n] / self.max_life[:n]
        size = np.maximum(1.0, np.round(self.size0[:n] + (self.size1[:n] - self.size0[:n]) * t)) / 16.0
        col = self.col0[:n] + (self.col1[:n] - self.col0[:n]) * t[:, None]
        # posições alinhadas à grade de pixels
        px = np.round(self.pos[:n] * 16.0) / 16.0
        verts = np.zeros((n, 4, 12), np.float32)
        hs = size[:, None] * 0.5
        offs = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]], np.float32)
        verts[:, :, 0] = px[:, None, 0] + offs[None, :, 0] * hs
        verts[:, :, 1] = px[:, None, 1] + offs[None, :, 1] * hs
        verts[:, :, 2] = px[:, None, 2]
        verts[:, :, 5] = -1.0
        verts[:, :, 6] = (offs[None, :, 0] + 1) * 0.5
        verts[:, :, 7] = (offs[None, :, 1] + 1) * 0.5
        verts[:, :, 8:12] = col[:, None, :]
        flat = verts.reshape(-1, 12)
        self.vdata.unclean_set_num_rows(len(flat))
        memoryview(self.vdata.modify_array(0)).cast("B")[:] = flat.tobytes()
        base = (np.arange(n, dtype=np.uint32) * 4)[:, None]
        idx = (base + np.array([0, 1, 2, 0, 2, 3], np.uint32)[None, :]).reshape(-1)
        self.prim.set_index_type(Geom.NT_uint32)
        arr = self.prim.modify_vertices()
        arr.unclean_set_num_rows(len(idx))
        memoryview(arr).cast("B")[:] = idx.tobytes()

    def clear(self):
        self.n = 0
        self.prim.clear_vertices()


class Decal:
    def __init__(self, parent, x, y, z, shape, radius, angle=0.0, length=0.0, width=0.0, color=(1, 0.2, 0.1),
                 time=1.0, inner=0.0, pulse=1.5):
        mb = MeshBuilder()
        if shape == 2:
            hw = width * 0.5
            ca, sa = math.cos(angle), math.sin(angle)
            px, pz = -sa, ca
            pts = []
            for (al, ac) in ((0, -hw), (length, -hw), (length, hw), (0, hw)):
                pts.append((x + ca * al + px * ac, y + 0.03, z + sa * al + pz * ac))
            mb.quad(pts[0], pts[1], pts[2], pts[3], (0, 1, 0), (0, 0), (1, 1))
        else:
            r = radius
            mb.quad((x - r, y + 0.03, z - r), (x + r, y + 0.03, z - r), (x + r, y + 0.03, z + r), (x - r, y + 0.03, z + r),
                    (0, 1, 0), (0, 0), (1, 1))
        self.np = mb.build("decal")
        self.np.reparent_to(parent)
        self.shape = shape
        self.inner = inner
        self.pulse = pulse
        self.color = color
        self.time = time
        self.t = 0.0
        self.alpha = 0.85
        self._apply(0.0)

    def _apply(self, progress):
        self.np.set_shader_input("u_decal", LVecBase4f(self.shape, self.inner, progress, self.pulse))
        self.np.set_shader_input("u_decal_col", LVecBase4f(*self.color, self.alpha))

    def update(self, dt):
        self.t += dt
        self._apply(min(1.0, self.t / max(0.01, self.time)))
        return self.t < self.time

    def remove(self):
        self.np.remove_node()


class FxLight(PointLight):
    def __init__(self, pos, color, intensity, radius, life):
        super().__init__(pos, color, intensity, radius, shadows=False)
        self.life = life
        self.max_life = life
        self.base = intensity

    def update(self, dt):
        super().update(dt)
        self.life -= dt
        self.intensity = self.base * max(0.0, self.life / self.max_life)
        return self.life > 0


class FxManager:
    def __init__(self, pipeline):
        self.pipe = pipeline
        self.add = ParticleSystem(pipeline.fx_root, True, 4000)
        self.alpha_root = pipeline.scene_root.attach_new_node("fx_alpha")
        self.alpha_root.set_shader(shader_lib.load("fx.vert", "particle_alpha.frag"))
        self.alpha_root.set_two_sided(True)
        self.alpha_root.set_bin("fixed", 15)
        self.alpha_root.set_depth_write(False)
        self.dust = ParticleSystem(self.alpha_root, False, 2500)
        self.decal_root = pipeline.scene_root.attach_new_node("decals")
        self.decal_root.set_shader(shader_lib.load("fx.vert", "decal.frag"))
        self.decal_root.set_transparency(TransparencyAttrib.M_alpha)
        self.decal_root.set_depth_write(False)
        self.decal_root.set_two_sided(True)
        self.decal_root.set_bin("fixed", 6)
        self.decals = {}
        self.lights = []
        self.shake = None          # callback (amount, time)
        self.rng = random.Random(4)

    # ------------------------------------------------------------------ utilitários
    def light(self, pos, color, intensity=2.0, radius=5.0, life=0.25):
        self.lights.append(FxLight(list(pos), color, intensity, radius, life))
        if len(self.lights) > 24:
            self.lights.pop(0)

    def sparks(self, pos, color, n=12, speed=5.0, gravity=8.0, life=(0.2, 0.5), size=(2, 1)):
        self.add.emit(pos, n, speed, life, size, (*color, 1.0), (color[0] * 0.3, color[1] * 0.2, color[2] * 0.2, 0.0), gravity, 2.5)

    def smoke(self, pos, color=(0.3, 0.28, 0.26), n=10, speed=1.5, up=1.0, life=(0.5, 1.2), size=(3, 5)):
        self.dust.emit(pos, n, speed, life, size, (*color, 0.9), (*color, 0.0), -0.5, 1.5, up=up)

    def line(self, a, b, color, n=20, life=(0.1, 0.25), size=(2, 1), jitter=0.15):
        for i in range(n):
            t = i / max(1, n - 1)
            p = (a[0] + (b[0] - a[0]) * t + self.rng.uniform(-jitter, jitter), a[1] + (b[1] - a[1]) * t + self.rng.uniform(-jitter, jitter),
                 a[2] + (b[2] - a[2]) * t)
            self.add.emit(p, 1, 0.3, life, size, (*color, 1.0), None, 0.0, 1.0)

    def ring(self, pos, radius, color, n=40, speed=0.5, life=(0.25, 0.45)):
        self.add.emit((pos[0], pos[1] + 0.1, pos[2]), n, speed, life, (2, 1), (*color, 1.0), None, 0.0, 1.0, ring=radius)

    # ------------------------------------------------------------------ eventos da simulação
    def handle(self, ev, world):
        k = ev["kind"]
        fn = getattr(self, "ev_" + k, None)
        if fn is not None:
            fn(ev, world)

    def ev_hit(self, ev, world):
        p = (ev["x"], ev["y"], ev["z"])
        mat = MATERIAL_FX.get(ev.get("material", "flesh"), MATERIAL_FX["flesh"])
        dx, dz = math.cos(ev["angle"]), math.sin(ev["angle"])
        n = mat["n"] * (2 if ev.get("heavy") else 1) * (1.5 if ev.get("crit") else 1)
        sysm = self.add if mat["add"] else self.dust
        sysm.emit(p, n, mat["speed"], (0.25, 0.6), (2, 1), mat["color"], mat["color2"], mat["grav"], 1.5, up=2.0,
                  direction=(dx, dz), cone=1.6)
        flash = (3.0, 2.8, 2.4) if not ev.get("crit") else (3.4, 2.6, 0.8)
        self.add.emit(p, 6 if not ev.get("heavy") else 12, 6.0, (0.05, 0.15), (3, 1), (*flash, 1.0), None, 0, 6.0,
                      direction=(dx, dz), cone=2.4)
        for el in ev.get("elements", []):
            if el != "fisico" and el in ELEMENT_COLORS:
                self.sparks(p, ELEMENT_COLORS[el], 10, 4.0, 2.0)
        self.light(p, (1.0, 0.9, 0.7), 2.0 if ev.get("heavy") else 1.0, 4.0, 0.12)
        if ev.get("combo"):
            self.add.emit(p, 40, 7.0, (0.3, 0.6), (3, 1), (3.0, 3.0, 3.2, 1.0), (0.4, 0.6, 1.0, 0.0), 2.0, 2.0)
            self.light(p, (0.8, 0.9, 1.0), 3.0, 6.0, 0.3)

    def ev_block(self, ev, world):
        p = (ev["x"], ev["y"], ev["z"])
        dx, dz = math.cos(ev["angle"]), math.sin(ev["angle"])
        self.add.emit(p, 16, 7.0, (0.15, 0.35), (2, 1), (3.0, 2.4, 1.0, 1.0), (1.0, 0.3, 0.0, 0.0), 10, 2.0, direction=(dx, dz), cone=1.8)
        self.light(p, (1.0, 0.8, 0.4), 1.5, 4.0, 0.1)

    def ev_parry(self, ev, world):
        p = (ev["x"], ev["y"], ev["z"])
        self.add.emit(p, 40, 9.0, (0.2, 0.5), (3, 1), (3.4, 3.0, 2.0, 1.0), (1.0, 0.6, 0.2, 0.0), 4, 2.0)
        self.ring((p[0], p[1] - 1.0, p[2]), 1.2, (3.0, 2.8, 2.0), 30, 6.0)
        self.light(p, (1.0, 0.95, 0.7), 4.0, 7.0, 0.3)
        if self.shake:
            self.shake(0.2, 0.15)

    def ev_posture_break(self, ev, world):
        p = (ev["x"], ev["y"], ev["z"])
        self.add.emit(p, 30, 6.0, (0.3, 0.6), (3, 1), (3.2, 2.6, 0.8, 1.0), (1.0, 0.5, 0.0, 0.0), 2, 2.0)
        self.ring((p[0], p[1] - 1.5, p[2]), 1.4, (3.0, 2.4, 0.6), 36, 5.0)
        self.light(p, (1.0, 0.85, 0.4), 3.0, 6.0, 0.4)

    def ev_execution_hit(self, ev, world):
        p = (ev["x"], ev["y"], ev["z"])
        self.dust.emit(p, 50, 7.0, (0.4, 0.9), (3, 1), (0.6, 0.02, 0.04, 1.0), (0.3, 0.0, 0.02, 0.0), 14, 1.5, up=3.0)
        self.add.emit(p, 40, 9.0, (0.1, 0.3), (3, 1), (3.4, 3.0, 2.6, 1.0), None, 0, 4.0)
        self.light(p, (1.0, 0.4, 0.3), 4.0, 7.0, 0.4)

    def ev_perfect_dodge(self, ev, world):
        p = (ev["x"], ev["y"] + 0.9, ev["z"])
        self.add.emit(p, 24, 3.0, (0.3, 0.6), (2, 1), (0.8, 2.4, 3.2, 1.0), (0.2, 0.4, 1.0, 0.0), -1, 2.0)
        self.light(p, (0.5, 0.8, 1.0), 2.0, 5.0, 0.3)

    def ev_dodge(self, ev, world):
        self.smoke((ev["x"], ev["y"] + 0.1, ev["z"]), (0.35, 0.3, 0.28), 5, 1.0, 0.5, (0.25, 0.5), (2, 3))

    def ev_jump(self, ev, world):
        self.smoke((ev["x"], ev["y"] + 0.05, ev["z"]), (0.35, 0.3, 0.28), 6, 1.5, 0.2, (0.2, 0.4), (2, 3))

    def ev_land(self, ev, world):
        self.dust.emit((ev["x"], ev["y"] + 0.05, ev["z"]), 12, 2.5, (0.25, 0.5), (2, 3), (0.4, 0.36, 0.32, 0.9),
                       (0.3, 0.28, 0.25, 0.0), 0, 3.0, ring=0.2)

    ev_land_heavy = ev_land

    def ev_death(self, ev, world):
        p = (ev["x"], ev["y"] + 0.5, ev["z"])
        mat = ev.get("material", "flesh")
        if mat == "ether":
            self.add.emit(p, 40, 3.0, (0.6, 1.2), (3, 1), (1.6, 1.2, 3.0, 1.0), None, -3, 1.0)
        elif mat in ("bone", "metal", "stone"):
            self.smoke(p, (0.4, 0.38, 0.36), 16, 2.0, 1.0)
            self.sparks(p, (2.0, 1.6, 1.0), 10, 4.0, 10)
        else:
            self.dust.emit(p, 24, 4.0, (0.4, 0.8), (3, 1), (0.5, 0.02, 0.04, 1.0), (0.2, 0.0, 0.02, 0.0), 12, 1.5, up=2.0)
            self.smoke(p, (0.25, 0.2, 0.2), 8, 1.0, 1.0)

    def ev_heal(self, ev, world):
        p = (ev["x"], ev["y"] - 0.8, ev["z"])
        self.add.emit(p, 16, 1.0, (0.5, 0.9), (2, 1), (1.2, 2.8, 1.0, 1.0), (0.4, 1.0, 0.3, 0.0), -3, 1.0, box=(0.8, 0.2, 0.3))

    def ev_buff(self, ev, world):
        c = ev.get("color", (1, 0.8, 0.3))
        self.ring((ev["x"], ev["y"] + 0.1, ev["z"]), 0.9, (c[0] * 3, c[1] * 3, c[2] * 3), 30, 0.2, (0.4, 0.8))
        self.add.emit((ev["x"], ev["y"] + 0.2, ev["z"]), 16, 1.0, (0.4, 0.8), (2, 1), (c[0] * 3, c[1] * 3, c[2] * 3, 1.0), None, -4, 1.0,
                      box=(1.0, 0.1, 0.4))

    def ev_barrier(self, ev, world):
        a = world_actor(world, ev.get("actor"))
        if a:
            self.ring((a.x, a.y + 0.2, a.z), 0.8, (3.0, 2.6, 1.4), 40, 0.1, (0.5, 0.9))

    def ev_status_proc(self, ev, world):
        cols = {"sangramento": (2.6, 0.1, 0.2), "queimadura": (3.0, 1.2, 0.2), "congelamento": (1.4, 2.4, 3.2),
                "choque": (2.6, 2.8, 3.4), "maldicao": (1.4, 0.3, 2.0)}
        c = cols.get(ev["status"], (2, 2, 2))
        p = (ev["x"], ev["y"], ev["z"])
        self.add.emit(p, 30, 5.0, (0.3, 0.7), (3, 1), (*c, 1.0), None, 4, 2.0)
        self.light(p, tuple(min(1.0, v / 3) for v in c), 2.5, 5.0, 0.3)

    def ev_lightning(self, ev, world):
        a = (ev["x0"], ev["y0"], ev["z0"])
        b = (ev["x"], ev["y"], ev["z"])
        self.line(a, b, (2.6, 2.8, 3.4), 24, (0.08, 0.2), (2, 1), 0.25)
        self.light(b, (0.7, 0.8, 1.0), 3.0, 5.0, 0.2)

    def ev_teleport(self, ev, world):
        for p in ((ev["x0"], ev["y0"] + 0.8, ev["z0"]), (ev["x"], ev["y"] + 0.8, ev["z"])):
            col = (1.2, 0.6, 2.4) if ev.get("tkind") != "leap" else (2.4, 2.0, 1.2)
            self.add.emit(p, 20, 3.0, (0.3, 0.6), (2, 1), (*col, 1.0), None, 0, 2.0)
            self.smoke(p, (0.15, 0.1, 0.2), 8, 1.0, 1.0)

    def ev_mist(self, ev, world):
        self.dust.emit((ev["x"], ev["y"] + 0.6, ev["z"]), 30, 2.0, (0.4, 0.9), (3, 5), (0.5, 0.05, 0.1, 0.8), (0.3, 0.0, 0.05, 0.0), -1, 2.0)

    ev_vanish = lambda self, ev, world: self.smoke((ev["x"], ev["y"] + 0.6, ev["z"]), (0.12, 0.1, 0.16), 16, 1.5, 0.8)

    def ev_transform(self, ev, world):
        p = (ev["x"], ev["y"] + 0.8, ev["z"])
        self.dust.emit(p, 40, 5.0, (0.4, 0.9), (3, 1), (0.3, 0.25, 0.25, 1.0), None, 4, 2.0)
        self.add.emit(p, 30, 6.0, (0.3, 0.6), (2, 1), (1.6, 1.8, 2.6, 1.0), None, 0, 2.0)
        self.light(p, (0.6, 0.7, 1.0), 3.0, 6.0, 0.5)

    def ev_explosion(self, ev, world):
        p = (ev["x"], ev["y"], ev["z"])
        col = ev.get("color", (1.0, 0.5, 0.2))
        self.add.emit(p, 60, 8.0, (0.3, 0.8), (3, 1), (col[0] * 3, col[1] * 3, col[2] * 3, 1.0), None, 4, 2.0)
        self.smoke(p, (0.15, 0.12, 0.1), 20, 3.0, 2.0, (0.6, 1.4), (3, 6))
        self.light(p, col, 5.0, 8.0, 0.5)

    def ev_proj_impact(self, ev, world):
        v = PROJ_VISUALS.get(ev.get("visual"), ((2, 2, 2), 2))
        p = (ev["x"], ev["y"], ev["z"])
        self.add.emit(p, 14, 4.0, (0.15, 0.35), (2, 1), (*v[0], 1.0), None, 4, 2.0)
        self.light(p, tuple(min(1.0, c / 3) for c in v[0]), 1.5, 4.0, 0.15)

    def ev_shoot(self, ev, world):
        v = PROJ_VISUALS.get(ev.get("visual"), ((2, 2, 2), 2))
        self.light((ev["x"], ev["y"], ev["z"]), tuple(min(1.0, c / 3) for c in v[0]), 1.6, 4.0, 0.1)

    def ev_telegraph(self, ev, world):
        shape = {"ring": 1, "beam": 2}.get(ev["shape"], 0)
        hostile = ev.get("team", "enemy") != "player"
        col = (1.0, 0.15, 0.08) if hostile else (0.4, 0.8, 1.0)
        d = Decal(self.decal_root, ev["x"], ev["y"], ev["z"], shape, ev["radius"], ev.get("angle", 0.0), ev.get("length", 0.0),
                  ev.get("width", 1.0), col, ev["time"], inner=0.75 if shape == 1 else 0.0)
        self.decals[ev["zone"]] = d

    def ev_zone_active(self, ev, world):
        vis = ev.get("visual", "burst")
        p = (ev["x"], ev["y"] + 0.2, ev["z"])
        r = ev.get("radius", 1.5)
        dec = self.decals.pop(ev.get("zone"), None)
        if dec:
            dec.remove()
        if vis in VISUALS:
            col, n, sp, grav, smoke = VISUALS[vis]
            if n:
                self.add.emit(p, n * min(2.0, max(0.6, r / 1.5)), sp, (0.3, 0.7), (3, 1), (*col, 1.0), None, grav, 2.0,
                              box=(r, 0.3, r))
            if smoke:
                self.smoke(p, smoke, 14 * max(1, int(r)), 2.0, 1.0, (0.5, 1.1), (3, 5))
            self.light((p[0], p[1] + 1.0, p[2]), tuple(min(1.0, c / 3) for c in col), 3.0, r * 2.5 + 2, 0.35)
        if vis in VISUALS and vis in ("light_pillar", "arcane_pillar", "rune_pillar", "tendril", "lightning_strike", "light_spear"):
            col = VISUALS[vis][0]
            self.add.emit((p[0], p[1] + 1.5, p[2]), 30, 0.6, (0.15, 0.35), (3, 2), (*col, 1.0), None, 0, 1.0, box=(r * 0.6, 3.0, r * 0.3))
        if self.shake and vis in ("explosion", "meteor", "moon_impact", "divine_impact", "metal_impact", "astral_explosion"):
            self.shake(0.35, 0.3)

    def ev_shake(self, ev, world):
        if self.shake:
            self.shake(ev.get("amount", 0.2), ev.get("time", 0.2))

    def ev_break(self, ev, world):
        p = (ev["x"], ev["y"], ev["z"])
        mat = ev.get("material", "wood")
        m = MATERIAL_FX.get(mat, MATERIAL_FX["wood"])
        self.dust.emit(p, 20 if not ev.get("big") else 50, 5.0, (0.4, 0.9), (3, 1), m["color"], m["color2"], 16, 1.0, up=3.0)
        self.smoke(p, (0.35, 0.32, 0.3), 10 if not ev.get("big") else 30, 2.0, 1.0)

    def ev_break_hit(self, ev, world):
        m = MATERIAL_FX.get(ev.get("material", "wood"), MATERIAL_FX["wood"])
        self.dust.emit((ev["x"], ev["y"], ev["z"]), 6, 3.0, (0.2, 0.4), (2, 1), m["color"], m["color2"], 14, 1.0, up=2.0)

    def ev_spark(self, ev, world):
        m = MATERIAL_FX.get(ev.get("material", "metal"), MATERIAL_FX["metal"])
        (self.add if m["add"] else self.dust).emit((ev["x"], ev["y"], ev["z"]), 10, 4.0, (0.15, 0.35), (2, 1), m["color"], m["color2"], 10, 2.0)

    def ev_chest(self, ev, world):
        p = (ev["x"], ev["y"] + 0.6, ev["z"])
        self.add.emit(p, 30, 2.0, (0.5, 1.0), (2, 1), (3.0, 2.6, 1.2, 1.0), None, -2, 1.0)
        self.light(p, (1.0, 0.85, 0.5), 2.5, 5.0, 0.8)

    def ev_pickup(self, ev, world):
        p = (ev["x"], ev["y"] + 0.4, ev["z"])
        self.add.emit(p, 16, 2.0, (0.3, 0.6), (2, 1), (3.0, 2.6, 1.4, 1.0), None, -3, 1.0)

    def ev_grace_found(self, ev, world):
        p = (ev["x"], ev["y"] + 1.0, ev["z"])
        self.add.emit(p, 60, 3.0, (0.6, 1.4), (2, 1), (3.0, 2.4, 1.2, 1.0), (1.0, 0.6, 0.2, 0.0), -2, 1.0)
        self.ring((ev["x"], ev["y"] + 0.1, ev["z"]), 2.0, (3.0, 2.4, 1.2), 50, 0.3, (0.6, 1.2))
        self.light(p, (1.0, 0.8, 0.4), 4.0, 8.0, 1.2)

    def ev_puzzle_solved(self, ev, world):
        pl = world.player
        if pl is not None:
            self.add.emit((pl.x, pl.y + 1.6, pl.z), 40, 3.0, (0.5, 1.0), (2, 1), (3.0, 2.6, 1.4, 1.0), None, -2, 1.0)

    def ev_puzzle_fail(self, ev, world):
        self.sparks((ev["x"], ev["y"] + 1, ev["z"]), (2.6, 0.4, 0.3), 16, 3.0, 4.0)

    def ev_door(self, ev, world):
        self.smoke((ev["x"], ev["y"] + 0.4, ev["z"]), (0.4, 0.38, 0.36), 14, 2.0, 0.5)

    def ev_crystal(self, ev, world):
        p = (ev["x"], ev["y"] + 1.0, ev["z"])
        self.add.emit(p, 24, 3.0, (0.3, 0.7), (2, 1), (1.4, 2.4, 3.2, 1.0), None, 0, 2.0)

    def _small(self, ev, world):
        self.sparks((ev["x"], ev["y"] + 0.8, ev["z"]), (2.6, 2.2, 1.2), 6, 2.0, 6.0)

    ev_lever = ev_dial = ev_mirror = ev_valve = ev_gear_turn = ev_gear_place = ev_switch = ev_plate = ev_seq_press = _small

    def ev_spawn(self, ev, world):
        p = (ev["x"], ev["y"] + 0.4, ev["z"])
        if ev.get("summoned"):
            self.add.emit(p, 30, 3.0, (0.3, 0.7), (2, 1), (1.4, 0.6, 2.4, 1.0), None, -2, 2.0)
            self.smoke(p, (0.12, 0.08, 0.16), 10, 1.5, 1.0)

    def ev_boss_phase(self, ev, world):
        p = (ev["x"], ev["y"] + 1.5, ev["z"])
        self.ring((ev["x"], ev["y"] + 0.1, ev["z"]), 3.0, (3.0, 2.2, 1.2), 80, 9.0, (0.4, 0.8))
        self.add.emit(p, 60, 6.0, (0.5, 1.0), (3, 1), (3.0, 2.4, 1.6, 1.0), None, 0, 1.5)
        self.light(p, (1.0, 0.8, 0.6), 5.0, 10.0, 1.0)

    def ev_wall_crash(self, ev, world):
        self.sparks((ev["x"], ev["y"], ev["z"]), (3.0, 2.2, 0.8), 30, 6.0, 10)
        self.smoke((ev["x"], ev["y"], ev["z"]), (0.4, 0.36, 0.32), 12, 2.0, 1.0)

    def ev_charge_full(self, ev, world):
        self.add.emit((ev["x"], ev["y"], ev["z"]), 20, 3.0, (0.2, 0.4), (2, 1), (3.0, 2.8, 2.0, 1.0), None, 0, 3.0)

    def ev_ultimate(self, ev, world):
        p = (ev["x"], ev["y"] + 1.0, ev["z"])
        self.ring((ev["x"], ev["y"] + 0.1, ev["z"]), 1.8, (3.0, 2.4, 1.0), 60, 4.0, (0.4, 0.8))
        self.light(p, (1.0, 0.85, 0.5), 5.0, 9.0, 0.8)

    def ev_reflect(self, ev, world):
        self.sparks((ev["x"], ev["y"], ev["z"]), (3.0, 3.0, 2.0), 20, 5.0, 2.0)

    def ev_last_stand(self, ev, world):
        a = world_actor(world, ev.get("actor"))
        if a:
            self.ring((a.x, a.y + 0.2, a.z), 1.4, (3.0, 2.6, 1.2), 50, 3.0, (0.5, 1.0))

    def ev_fall_void(self, ev, world):
        pass

    def ev_steal(self, ev, world):
        self.add.emit((ev["x"], ev["y"], ev["z"]), 12, 2.0, (0.4, 0.8), (2, 1), (3.0, 2.6, 0.8, 1.0), None, -2, 1.0)

    def ev_vent_open(self, ev, world):
        self.smoke((ev["x"], ev["y"], ev["z"]), (0.7, 0.68, 0.66), 40, 3.0, 3.0, (0.8, 1.5), (4, 7))
        self.light((ev["x"], ev["y"], ev["z"]), (1.0, 0.5, 0.2), 4.0, 8.0, 3.0)

    def ev_arena_rift(self, ev, world):
        pass

    # ------------------------------------------------------------------ por quadro
    def update(self, dt):
        self.add.update(dt)
        self.dust.update(dt)
        self.lights = [l for l in self.lights if l.update(dt)]
        for zid in list(self.decals):
            if not self.decals[zid].update(dt):
                self.decals.pop(zid).remove()

    def finish_frame(self):
        self.add.rebuild()
        self.dust.rebuild()

    def clear(self):
        self.add.clear()
        self.dust.clear()
        for d in self.decals.values():
            d.remove()
        self.decals.clear()
        self.lights.clear()

    # ------------------------------------------------------------------ efeitos contínuos
    def zone_tick(self, zone, dt):
        """Campos, feixes e anéis ativos emitem partículas continuamente."""
        if zone.telegraphing:
            return
        rng = self.rng
        vis = zone.visual
        if zone.shape == "beam":
            col = BEAM_VISUALS.get(vis, (2.4, 2.0, 2.0))
            fx_, fz_ = math.cos(zone.facing), math.sin(zone.facing)
            for _ in range(int(zone.length * 3)):
                t = rng.random() * zone.length
                w = (rng.random() - 0.5) * zone.width
                p = (zone.x + fx_ * t - fz_ * w, zone.y + 0.9 + rng.uniform(-0.2, 0.2), zone.z + fz_ * t + fx_ * w)
                self.add.emit(p, 1, 0.5, (0.06, 0.16), (3, 1), (*col, 1.0), None, 0, 1.0)
            mid = (zone.x + fx_ * zone.length * 0.5, zone.y + 1.0, zone.z + fz_ * zone.length * 0.5)
            self.light(mid, tuple(min(1.0, c / 3) for c in col), 2.5, zone.length * 0.6 + 2, 0.06)
        elif zone.shape == "ring":
            col = RING_VISUALS.get(vis, (2.4, 2.0, 1.4))
            self.add.emit((zone.x, zone.y + 0.15, zone.z), int(zone.radius * 6) + 4, 0.2, (0.06, 0.14), (2, 1), (*col, 1.0), None, 0, 1.0,
                          ring=zone.radius)
        elif zone.shape in ("field",):
            col = FIELD_VISUALS.get(vis, (1.6, 1.0, 2.4))
            n = int(zone.radius * zone.radius * 2 * dt * 30) + 1
            self.add.emit((zone.x, zone.y + 0.15, zone.z), n, 0.3, (0.3, 0.7), (2, 1), (*col, 1.0), None, -2, 1.0,
                          box=(zone.radius * 1.6, 0.1, zone.radius * 1.6))
            if zone.pull:
                self.add.emit((zone.x, zone.y + 0.3, zone.z), 3, -3.0, (0.3, 0.6), (2, 1), (*col, 1.0), None, 0, 0.5, ring=zone.radius)

    def projectile_tick(self, proj, dt):
        v = PROJ_VISUALS.get(proj.visual, ((2.4, 2.4, 2.4), 2))
        col, size = v
        p = (proj.x, proj.y, proj.z)
        self.add.emit(p, 1, 0.0, (0.03, 0.05), (size + 1, size), (*col, 1.0), (*col, 1.0), 0, 0)
        self.add.emit(p, 2, 0.4, (0.1, 0.25), (size, 1), (col[0] * 0.7, col[1] * 0.7, col[2] * 0.7, 1.0), None, 0, 2.0)

    def trail(self, actor, move, spec, frac, color):
        """Rastro da lâmina: pontos ao longo do arco do golpe (só durante a janela ativa)."""
        sc = actor.scale
        if actor.kind == "player" and color[0] > color[1] * 1.6:
            self.light((actor.x, actor.y + 1.0, actor.z), (1.0, 0.34, 0.08), 1.35, 3.8, 0.07)
        if spec.get("shape", "arc") == "arc":
            rng_ = spec.get("range", 1.6) * sc * 0.85
            ang = math.radians(spec.get("angle", 120))
            if ang >= math.tau - 0.01:
                a0 = actor.facing + frac * math.tau
                steps = 6
                for i in range(steps):
                    a = a0 - i * 0.18
                    p = (actor.x + math.cos(a) * rng_, actor.y + 0.9 * sc, actor.z + math.sin(a) * rng_)
                    self.add.emit(p, 1, 0.2, (0.06, 0.14), (3, 1), (*color, 1.0), None, 0, 1.0)
                return
            side = 1 if "slash_l" not in move.anim else -1
            a = actor.facing + side * (ang * 0.5 - ang * frac)
            for k in range(3):
                aa = a + side * k * 0.12
                for rr in (rng_, rng_ * 0.75):
                    p = (actor.x + math.cos(aa) * rr, actor.y + (0.9 + (0.4 - frac * 0.6) * (1 if "down" in move.anim else 0.2)) * sc,
                         actor.z + math.sin(aa) * rr)
                    self.add.emit(p, 1, 0.2, (0.06, 0.16), (3 if k == 0 else 2, 1), (*color, 1.0), None, 0, 1.0)
        elif spec.get("shape") == "line":
            L = spec.get("length", 2.0) * sc
            fx_, fz_ = math.cos(actor.facing), math.sin(actor.facing)
            for i in range(4):
                t = L * (0.3 + 0.7 * self.rng.random())
                p = (actor.x + fx_ * t, actor.y + 1.0 * sc, actor.z + fz_ * t)
                self.add.emit(p, 1, 0.3, (0.05, 0.12), (2, 1), (*color, 1.0), None, 0, 1.0)

    def ambient(self, kind, cx, cz, hw, hh, dt, ground_y=0.0):
        if not kind:
            return
        rng = self.rng
        rate = {"embers": 14, "fireflies_red": 6, "dust": 10, "ash_red": 18, "moon_mist": 3,
                "sparks": 16, "incense": 8, "spores": 10, "stars": 10, "light_motes": 12}.get(kind, 0)
        n = int(rate * dt * 4) + (1 if rng.random() < (rate * dt * 4) % 1 else 0)
        for _ in range(n):
            x = cx + rng.uniform(-hw, hw)
            z = cz + rng.uniform(-hh, hh)
            y = ground_y + rng.uniform(0.2, 2.5)
            if kind == "embers":
                self.add.emit((x, y, z), 1, 0.4, (1.5, 3.0), (1, 1), (2.8, 1.2, 0.3, 1.0), (1.0, 0.2, 0.0, 0.0), -0.6, 0.3)
            elif kind == "fireflies_red":
                self.add.emit((x, y, z), 1, 0.3, (2.0, 4.0), (1, 1), (2.6, 0.4, 0.4, 1.0), (1.0, 0.1, 0.1, 0.0), 0.0, 0.1)
            elif kind == "dust":
                self.dust.emit((x, y, z), 1, 0.1, (2.0, 4.0), (1, 1), (0.6, 0.58, 0.55, 0.6), (0.6, 0.58, 0.55, 0.0), -0.05, 0.1)
            elif kind == "ash_red":
                self.add.emit((x, y + 2, z), 1, 0.3, (2.0, 3.5), (1, 1), (2.0, 0.4, 0.3, 1.0), (0.4, 0.1, 0.1, 0.0), 0.3, 0.5)
            elif kind == "moon_mist":
                self.dust.emit((x, ground_y + 0.35, z), 1, 0.12, (3.0, 5.0), (10, 18),
                               (0.16, 0.2, 0.3, 0.13), (0.1, 0.12, 0.2, 0.0), 0.0, 0.06,
                               direction=(1.0, 0.25), cone=0.2)
            elif kind == "sparks":
                self.add.emit((x, y, z), 1, 1.0, (0.6, 1.4), (1, 1), (3.0, 1.6, 0.4, 1.0), (1.0, 0.3, 0.0, 0.0), -1.5, 0.5)
            elif kind == "incense":
                self.dust.emit((x, y - 1, z), 1, 0.2, (2.5, 4.0), (2, 4), (0.55, 0.5, 0.48, 0.5), (0.5, 0.48, 0.45, 0.0), -0.3, 0.2)
            elif kind == "spores":
                self.add.emit((x, y, z), 1, 0.2, (2.0, 4.0), (1, 1), (0.8, 2.0, 0.6, 1.0), (0.2, 0.6, 0.2, 0.0), -0.1, 0.2)
            elif kind == "stars":
                self.add.emit((x, y + 1, z), 1, 0.05, (0.6, 1.6), (1, 1), (2.2, 2.4, 3.2, 1.0), (0.4, 0.5, 1.0, 0.0), 0.0, 0.0)
            elif kind == "light_motes":
                self.add.emit((x, y, z), 1, 0.2, (2.0, 4.0), (1, 1), (3.0, 2.6, 1.6, 1.0), (1.0, 0.8, 0.4, 0.0), -0.2, 0.2)


def world_actor(world, aid):
    if aid is None:
        return None
    for a in world.actors:
        if a.id == aid:
            return a
    return None
