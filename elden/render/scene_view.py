"""Cena renderizada de uma fase: cenário, decoração, vistas das entidades, efeitos, luzes e câmera."""
import math

from panda3d.core import LVecBase4f, NodePath

from ..core.data import DB
from ..core.mathutil import clamp, smooth_damp
from ..art import spritegen, characters
from ..art.tiles import Atlas
from ..sim.clone import ShadowClone
from ..sim.ai.bosses.base import BossPart
from .geom import MeshBuilder
from .level_mesh import build_level_mesh, occupancy_texture
from .lights import PointLight
from .textures import to_texture
from .views import ActorView, CloneView, PropView, PlatformView, BeamView, snap
from . import shader_lib

BOSS_EXTRA_SPAWNS = {"varkhan": ["lobo_corrompido"], "condessa_rubra": ["morcego_sanguineo"]}


class Environment:
    def __init__(self, d):
        self.amb_sky = tuple(d["amb_sky"])
        self.amb_ground = tuple(d["amb_ground"])
        self.dir_dir = tuple(d["dir_dir"])
        self.dir_col = tuple(d["dir_col"])
        self.fog_col = tuple(d["fog_col"])
        self.fog_amount = d["fog_amount"]
        self.lift = tuple(d["lift"])
        self.gain = tuple(d["gain"])
        self.exposure = d["exposure"]
        self.saturation = d["saturation"]
        self.vignette = d["vignette"]
        self.floor_y = 0.0
        self.light_bands = d.get("light_bands", 6)
        self.ambient = d.get("ambient")


class CameraRig:
    def __init__(self):
        self.x = self.z = 0.0
        self.shake_amt = 0.0
        self.shake_t = 0.0
        self.offset = (0.0, 0.0)
        self.lead_x = self.lead_z = 0.0
        self.strength = 1.0

    def snap_to(self, x, z):
        self.x, self.z = x, z

    def shake(self, amount, time):
        self.shake_amt = max(self.shake_amt, amount * self.strength)
        self.shake_t = max(self.shake_t, time)

    def update(self, dt, world, pipe, view_hw, view_hh):
        p = world.player
        if p is None:
            return self.x, self.z
        tx, tz = p.x, p.z
        # antecipação de movimento
        lx = clamp(p.move_x * 0.22, -1.6, 1.6)
        lz = clamp(p.move_z * 0.22, -1.2, 1.2)
        self.lead_x = smooth_damp(self.lead_x, lx, 3.0, dt)
        self.lead_z = smooth_damp(self.lead_z, lz, 3.0, dt)
        tx += self.lead_x
        tz += self.lead_z
        zoom = 1.0
        focus = p.locked if p.locked is not None else None
        boss = world.boss if world.boss is not None and world.boss.awake and not world.boss.dead else None
        if boss is not None:
            focus = boss
            d = math.hypot(boss.x - p.x, boss.z - p.z)
            zoom = clamp(1.0 + (d - 5.0) * 0.03, 1.0, 1.25)
        if focus is not None and not focus.dead:
            tx = tx * 0.68 + focus.x * 0.32
            tz = tz * 0.68 + focus.z * 0.32
        pipe.zoom_target = zoom
        self.x = smooth_damp(self.x, tx, 7.0, dt)
        self.z = smooth_damp(self.z, tz, 7.0, dt)
        # limites da fase
        lvl = world.level
        b = lvl.camera_bounds or [0, 0, lvl.width, lvl.depth + 3]
        x0, z0, x1, z1 = b
        if x1 - x0 > view_hw * 2:
            self.x = clamp(self.x, x0 + view_hw, x1 - view_hw)
        else:
            self.x = (x0 + x1) * 0.5
        if z1 - z0 > view_hh * 2:
            self.z = clamp(self.z, z0 + view_hh, z1 - view_hh)
        else:
            self.z = (z0 + z1) * 0.5
        ox = oz = 0.0
        if self.shake_t > 0:
            self.shake_t -= dt
            a = self.shake_amt * min(1.0, self.shake_t * 4)
            ox = (math.sin(self.shake_t * 91.0) + math.sin(self.shake_t * 53.0)) * 0.5 * a
            oz = (math.cos(self.shake_t * 77.0) + math.sin(self.shake_t * 61.0)) * 0.5 * a
            if self.shake_t <= 0:
                self.shake_amt = 0.0
        return self.x + ox, self.z + oz


class SceneView:
    def __init__(self, pipe, bank, props_atlas, fx, assets=None):
        self.pipe = pipe
        self.bank = bank
        self.props = props_atlas
        self.fx = fx
        self.assets = assets
        self.world = None
        self.views = {}
        self.level_node = None
        self.static_node = None
        self.external_nodes = []
        self.camera = CameraRig()
        self.fx.shake = self.camera.shake
        self.static_lights = []
        self.env = None
        self.corruption_glow = 0.0
        self.player_light = PointLight((0, 0, 0), (1.0, 0.85, 0.65), 0.55, 4.5, shadows=False)
        self.show_hitboxes = False
        self.events_hook = None
        self.view_root = None

    # ------------------------------------------------------------------ sprites
    def sprite_for(self, a):
        if a.kind == "player":
            return characters.player_sprite_id(a.char.class_id, a.char.appearance, a.transformed)
        sid = getattr(a, "sprite", None) or "esqueleto"
        if getattr(a, "elite", False) and not getattr(a, "is_boss", False) and not getattr(a, "is_part", False):
            return f"{sid}@1.15"
        return sid

    def request_sprites(self, world):
        bank = self.bank
        for a in world.actors:
            self._request_actor(a)
        # invocações possíveis
        extra = set()
        for a in world.actors:
            if a.kind in ("enemy", "boss"):
                eid = getattr(a, "boss_id", getattr(a, "enemy_id", None))
                extra.update(BOSS_EXTRA_SPAWNS.get(eid, []))
                atks = list(a.attacks)
                if getattr(a, "is_boss", False):
                    for ph in a.phases:
                        atks += ph["attacks"]
                for atk in atks:
                    m = DB.moves.get(atk["move"], {})
                    for s in m.get("spawn", []):
                        if "summon" in s:
                            extra.add(s["summon"])
        for eid in extra:
            d = DB.enemies[eid]
            bank.request(d.get("sprite", eid), spritegen.enemy_anims(eid))

    def _request_actor(self, a):
        bank = self.bank
        if a.kind == "player":
            anims = spritegen.player_anims()
            bank.request(characters.player_sprite_id(a.char.class_id, a.char.appearance), anims)
            if a.L.beast_moveset is not None:
                bank.request(characters.player_sprite_id(a.char.class_id, a.char.appearance, True), anims)
        elif a.kind == "npc":
            bank.request(a.sprite, spritegen.NPC_ANIMS)
        elif getattr(a, "is_boss", False):
            anims = spritegen.boss_anims(a.boss_id)
            bank.request(a.sprite, anims)
            for ph in a.phases:
                if "sprite" in ph:
                    bank.request(ph["sprite"], anims)
        elif getattr(a, "is_part", False):
            bank.request(a.sprite, spritegen.BASE_ANIMS)
        elif a.kind == "enemy":
            bank.request(self.sprite_for(a), spritegen.enemy_anims(a.enemy_id))

    # ------------------------------------------------------------------ construção da fase
    def load(self, world, progress=None):
        self.unload()
        self.world = world
        lvl = world.level
        self.request_sprites(world)
        self.bank.load_pending(progress)
        # texturas do cenário
        names = set()
        for row in lvl.cells:
            for c in row:
                if c is not None and not c.void:
                    names.update([c.top_tex, c.wall_tex] + ([c.trim_tex] if c.trim_tex else []))
        theme_plat = {"ato2": "copper_plate", "ato4": "rune_floor", "ato5": "gold_trim"}.get(lvl.theme, "cobble")
        names.add(theme_plat)
        names.add("cobble")
        self.platform_tex = theme_plat
        self.level_atlas = Atlas(sorted(names), seed=lvl.act * 7 + 3)
        self.level_tex = to_texture(self.level_atlas.image, "level_atlas")
        self.level_node = build_level_mesh(lvl, self.level_atlas)
        self.level_node.reparent_to(self.pipe.world_root)
        self.level_node.set_texture(self.level_tex)
        if self.assets is not None:
            for spec in lvl.data.get("visual_assets", []):
                node = self.assets.instantiate_model(spec.get("asset"), self.pipe.world_root,
                                                     (spec.get("x", 0), spec.get("y", 0), spec.get("z", 0)),
                                                     spec.get("angle", 0), spec.get("scale", 1.0))
                if node is not None:
                    self.external_nodes.append(node)
        self.pipe.set_occupancy(occupancy_texture(lvl), 0, 0, lvl.width, lvl.depth)
        env = DB.environments.get(lvl.env) or DB.environments["santuario"]
        self.env = Environment(env)
        self.env.floor_y = 0.0
        self.pipe.set_environment(self.env)
        self._build_static_decor()
        self.static_lights = []
        for p in world.props:
            for L in p.lights():
                self.static_lights.append(L)
        self.camera.snap_to(world.player.x, world.player.z) if world.player else None

    def _build_static_decor(self):
        """Árvores, lápides e decoração sem animação viram um único mesh (poucas draw calls)."""
        lvl = self.world.level
        mb = MeshBuilder()
        atlas = self.props
        count = 0
        for z in range(lvl.depth):
            for x in range(lvl.width):
                c = lvl.cell(x, z)
                if c is None or not c.deco:
                    continue
                v = (x * 31 + z * 17) % max(1, atlas.variants(c.deco))
                self._decor_quad(mb, c.deco, v, x + 0.5 + ((x * 13 + z) % 3 - 1) * 0.12, 0.0 if c.height >= 0 else c.height, z + 0.45)
                count += 1
        for p in list(self.world.props):
            if p.spec.get("type") == "decor" and p.light is None and atlas.frames(p.sprite, 0) == 1:
                self._decor_quad(mb, p.sprite, (int(p.x * 3 + p.z)) % max(1, atlas.variants(p.sprite)), p.x, p.y, p.z)
                p.static_drawn = True
                count += 1
        if count:
            self.static_node = mb.build("decor")
            self.static_node.reparent_to(self.pipe.scene_root)
            self.static_node.set_shader(shader_lib.load("decor.vert", "sprite.frag"))
            self.static_node.set_texture(atlas.tex)
            self.static_node.set_two_sided(True)

    def _decor_quad(self, mb, name, variant, x, y, z):
        uv, w, h = self.props.info(name, variant, 0)
        x, y, z = snap(x, y, z)
        x0, x1 = x - w / 2, x + w / 2
        n = (x, y, z)
        mb.quad((x0, y, z), (x1, y, z), (x1, y + h, z), (x0, y + h, z), n, (uv[0], uv[1]), (uv[2], uv[3]))

    def shadow_card(self, r):
        mb = MeshBuilder()
        col = (0.0, 0.0, 0.0, 0.42)
        mb.quad((-r, 0, -r * 0.7), (r, 0, -r * 0.7), (r, 0, r * 0.7), (-r, 0, r * 0.7), (0, 1, 0), (0, 0), (1, 1), color=col)
        n = mb.build("shadow")
        n.reparent_to(self.pipe.shade_root)
        return n

    def unload(self):
        for v in self.views.values():
            if v is not None:
                v.remove()
        self.views.clear()
        for nd in (self.level_node, self.static_node, *self.external_nodes):
            if nd is not None:
                nd.remove_node()
        self.level_node = self.static_node = None
        self.external_nodes = []
        self.fx.clear()
        self.world = None

    # ------------------------------------------------------------------ sincronização
    def _view_for(self, e):
        k = e.kind
        if k in ("player", "enemy", "boss", "npc"):
            sid = self.sprite_for(e)
            if self.bank.get(sid) is None:
                self._request_actor(e)
                self.bank.load_pending()
            if self.bank.get(sid) is None:
                return None
            return ActorView(self, e, sid)
        if k == "clone":
            return CloneView(self, e)
        if k == "prop":
            t = e.spec.get("type")
            if t in ("spawn", "trigger"):
                return None
            if t == "platform":
                return PlatformView(self, e)
            if e.spec.get("asset") and self.assets is not None:
                node = self.assets.instantiate_model(e.spec["asset"], self.pipe.world_root,
                                                     scale=e.spec.get("asset_scale", 1.0))
                if node is not None:
                    return ExternalModelView(node, e)
            if t == "emitter":
                return _Multi(PropView(self, e), BeamView(self, e))
            if getattr(e, "static_drawn", False):
                return None
            if e.sprite is None:
                return None
            return PropView(self, e)
        if k == "pickup":
            class _PickupProp:
                pass
            return PickupView(self, e)
        return None

    def update(self, dt, events):
        w = self.world
        for ev in events:
            self.fx.handle(ev, w)
            if self.events_hook:
                self.events_hook(ev)
        alive = set()
        for group in (w.actors, w.props, w.pickups, w.misc):
            for e in group:
                if not e.alive:
                    continue
                alive.add(e.id)
                v = self.views.get(e.id)
                if v is None and e.id not in self.views:
                    v = self._view_for(e)
                    self.views[e.id] = v
                if v is not None:
                    v.update(dt)
        for eid in list(self.views):
            if eid not in alive:
                v = self.views.pop(eid)
                if v is not None:
                    v.remove()
        # projéteis e zonas contínuas
        for p in w.projectiles:
            self.fx.projectile_tick(p, dt)
        for z in w.zones:
            self.fx.zone_tick(z, dt)
        # rastros de lâmina
        from ..sim.combat.actions import MoveAction
        for a in w.actors:
            act = a.action
            if isinstance(act, MoveAction) and a.hitstop <= 0:
                for h in act.move.hits:
                    t0, t1 = h["t"]
                    if t0 <= act.t < t1:
                        frac = (act.t - t0) / max(1e-3, t1 - t0)
                        self.fx.trail(a, act.move, h, frac, self.trail_color(a, act))
        # câmera e luzes
        hw, hh = self.pipe.view_extent()
        cx, cz = self.camera.update(dt, w, self.pipe, hw, hh)
        self.pipe.update(dt, cx, cz)
        for L in self.static_lights:
            L.update(dt)
        lights = list(self.static_lights)
        for p in w.pickups:
            lights.extend(p.lights())
        for pr in w.props:
            if pr.light is not None and pr.light not in self.static_lights:
                lights.append(pr.light)
        for proj in w.projectiles:
            if proj.light:
                c = proj.light
                lights.append(PointLight((proj.x, proj.y, proj.z), (c[0], c[1], c[2]), c[3] if len(c) > 3 else 1.5, 4.0, shadows=False))
        lights.extend(self.fx.lights)
        pl = w.player
        if pl is not None:
            self.player_light.pos = [pl.x, pl.y + 1.6, pl.z - 0.4]
            lights.append(self.player_light)
        self.pipe.set_lights(lights, (cx, cz))
        self.fx.ambient(self.env.ambient, cx, cz, hw + 1, hh + 1, dt)
        self.fx.update(dt)
        self.fx.finish_frame()

    def trail_color(self, a, act):
        if a.kind != "player":
            return (2.2, 0.6, 0.5) if any(h.get("unblockable") for h in act.move.hits) else (2.0, 1.9, 1.7)
        buffs = a.status.buffs
        if "imbuir" in buffs:
            m = buffs["imbuir"].mods
            if "frost_add" in m:
                return (1.2, 2.2, 3.2)
            if "burn_add" in m:
                return (3.2, 1.2, 0.3)
            if "shock_add" in m:
                return (2.4, 2.6, 3.4)
            return (3.2, 2.8, 1.6)
        el = a.L.weapon.get("base", {})
        for k, c in (("sangue", (2.6, 0.2, 0.3)), ("trevas", (1.2, 0.4, 2.0)), ("sagrado", (3.2, 2.8, 1.6)), ("gelo", (1.2, 2.2, 3.2)),
                     ("fogo", (3.2, 1.2, 0.3))):
            if el.get(k):
                return c
        if a.transformed:
            return (1.4, 1.6, 2.6)
        return (2.4, 2.4, 2.6)


class _Multi:
    def __init__(self, *views):
        self.views = views

    def update(self, dt):
        for v in self.views:
            v.update(dt)

    def remove(self):
        for v in self.views:
            v.remove()


class ExternalModelView:
    """Sincroniza um modelo artístico; o chamador usa PropView se o asset faltar."""

    def __init__(self, node, entity):
        self.node = node
        self.entity = entity

    def update(self, dt):
        e = self.entity
        self.node.set_pos(e.x, e.y, e.z)
        self.node.set_r(e.spec.get("angle", 0))
        self.node.show() if getattr(e, "visible", True) and e.alive else self.node.hide()

    def remove(self):
        self.node.remove_node()


class PickupView:
    def __init__(self, scene, p):
        self.scene = scene
        self.p = p
        name = p.sprite if scene.props.has(p.sprite) else "item_glow"
        self.name = name
        uv, w, h = scene.props.info(name, 0, 0)
        from .views import get_card
        self.node = get_card(w, h, 0.0).copy_to(scene.pipe.sprite_root)
        self.node.set_texture(scene.props.tex)
        for k, v in (("u_sprite", (0.05, 0, 0, 0)), ("u_flash", (0, 0, 0, 0)), ("u_glow", (0.2, 0.15, 0.05, 0)), ("u_tint", (1, 1, 1, 1))):
            self.node.set_shader_input(k, LVecBase4f(*v))
        self.t = 0.0
        self.n = scene.props.frames(name, 0)

    def update(self, dt):
        self.t += dt
        uv, w, h = self.scene.props.info(self.name, 0, int(self.t * 6) % self.n)
        x, y, z = snap(self.p.x, self.p.y + 0.1 + math.sin(self.t * 3) * 0.06, self.p.z)
        self.node.set_pos(x, y, z)
        self.node.set_shader_input("u_frame", LVecBase4f(*uv))

    def remove(self):
        self.node.remove_node()
