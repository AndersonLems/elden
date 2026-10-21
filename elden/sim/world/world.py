"""World: estado completo de uma fase em execução (atores, projéteis, zonas, objetos) e regras globais.

Não depende de renderização: a camada visual lê o estado e consome a fila de efeitos (fx).
"""
import math
import random

from ...core.events import EventBus, FxQueue
from ...core.mathutil import dir_of
from ..entity import Actor
from ..combat.projectiles import Projectile, Zone
from ..combat.damage import Hit, apply_hit
from ..combat import effects as effects_mod
from .physics import Physics
from .level import Level


class World:
    def __init__(self, level, session=None, seed=None):
        self.level = level if isinstance(level, Level) else Level(level)
        self.session = session
        self.rng = random.Random(seed)
        self.fx = FxQueue()
        self.bus = EventBus()
        self.physics = Physics(self)
        self.time = 0.0
        self.time_scale = 1.0
        self._slowmo = 0.0
        self.player = None
        self.actors = []
        self.projectiles = []
        self.zones = []
        self.props = []
        self.pickups = []
        self.misc = []
        self.platforms = []
        self.solids = []
        self.boss = None
        self.current_region = None
        self.paused_ai = False
        self.messages = []          # mensagens curtas para a interface (ex.: "Porta destrancada")
        self.combat_heat = 0.0      # > 0 quando há combate recente (música, Fervor)
        self.puzzles = []
        self.night = False
        self.arena_center = (0.0, 0.0)
        self.arena_rift = None

    # ------------------------------------------------------------------ entidades
    def spawn(self, e):
        e.attach(self)
        k = e.kind
        if k in ("actor", "player", "enemy", "boss", "npc"):
            self.actors.append(e)
            if k == "player":
                self.player = e
            if k == "boss":
                self.boss = e
        elif k == "projectile":
            self.projectiles.append(e)
        elif k == "zone":
            self.zones.append(e)
        elif k == "prop":
            self.props.append(e)
            if getattr(e, "is_platform", False):
                self.platforms.append(e)
            if getattr(e, "can_block", False):
                self.solids.append(e)
        elif k == "pickup":
            self.pickups.append(e)
        else:
            self.misc.append(e)
        if hasattr(e, "on_spawn"):
            e.on_spawn()
        return e

    def spawn_enemy(self, enemy_id, x, z, summoned=False, aggro=False, **kw):
        from ..ai.enemies import create_enemy
        e = create_enemy(enemy_id, x, z, **kw)
        g = self.level.ground_at(x, z)
        if g is not None:
            e.y = g
        e.summoned = summoned
        self.spawn(e)
        if aggro and self.player is not None:
            e.brain.alert(self.player)
        self.fx.push("spawn", x=e.x, y=e.y, z=e.z, actor=e.id, summoned=summoned)
        return e

    def all_entities(self):
        return self.actors + self.props + self.pickups + self.projectiles + self.zones + self.misc

    def find_prop(self, pid):
        for p in self.props:
            if getattr(p, "pid", None) == pid:
                return p
        return None

    def enemies(self):
        return [a for a in self.actors if a.kind in ("enemy", "boss") and not a.dead]

    def enemies_of(self, actor):
        return [a for a in self.actors if not a.dead and a.alive and actor.is_hostile_to(a) and not a.untargetable]

    def allies_of(self, team):
        return [a for a in self.actors if not a.dead and a.alive and a.team == team]

    def hit_candidates(self, attacker):
        out = [a for a in self.actors if a.alive and not a.dead and not a.untargetable and attacker.is_hostile_to(a)]
        if attacker.team == "player":
            out.extend(p for p in self.props if p.alive and p.hittable)
        return out

    def projectile_targets(self, proj):
        out = [a for a in self.actors if a.alive and not a.dead and not a.untargetable
               and a.team not in (proj.team, "neutral")]
        if proj.team == "player":
            out.extend(p for p in self.props if p.alive and p.hittable)
        return out

    def zone_targets(self, zone):
        out = [a for a in self.actors if a.alive and not a.dead and not a.untargetable
               and a.team not in (zone.team, "neutral")]
        if zone.team == "player":
            out.extend(p for p in self.props if p.alive and p.hittable)
        return out

    # ------------------------------------------------------------------ geração a partir de dados
    def spawn_from_spec(self, actor, spec, action=None):
        power = getattr(action, "power", 1.0)
        if action is not None and hasattr(action, "move") and action.move.magic and "scale" not in spec:
            spec = dict(spec, scale=action.move.magic)
        mt = action.move.type if action is not None and hasattr(action, "move") else "skill"
        tags = action.move.tags if action is not None and hasattr(action, "move") else ()
        if "proj" in spec:
            self.spawn_projectiles(actor, spec, power, mt, tags)
        elif "zone" in spec:
            fx, fz = dir_of(actor.facing)
            at = spec.get("at", "forward")
            off = spec.get("offset", 1.5) * actor.scale
            if at == "self":
                x, z = actor.x, actor.z
            elif at == "target" and actor.target is not None and getattr(actor.target, "alive", False):
                t = actor.target
                x, z = t.x, t.z
                if spec.get("lead"):
                    x += t.move_x * spec["lead"]
                    z += t.move_z * spec["lead"]
                actor.last_marker = (x, z)
            else:
                x, z = actor.x + fx * off, actor.z + fz * off
            count = spec.get("count", 1)
            for i in range(count):
                xi, zi = x, z
                if count > 1:
                    if spec.get("pattern") == "line":
                        step = spec.get("step", 1.6)
                        xi, zi = actor.x + fx * (off + step * i), actor.z + fz * (off + step * i)
                    else:
                        ang = math.tau * i / count + self.rng.random() * 0.3
                        rr = spec.get("spread_radius", 3.0) * (0.4 + 0.6 * self.rng.random())
                        xi, zi = x + math.cos(ang) * rr, z + math.sin(ang) * rr
                g = self.level.ground_at(xi, zi)
                y = g if g is not None else actor.y
                s = dict(spec)
                if count > 1 and spec.get("stagger_delay"):
                    s["delay"] = spec.get("delay", 0.0) + spec["stagger_delay"] * i
                self.spawn_zone(actor, s, xi, y, zi, actor.facing, power, move_type=mt, tags=tags)
        elif "summon" in spec:
            effects_mod.apply_effect(self, actor, {"type": "summon", "enemy": spec["summon"],
                                                   "count": spec.get("count", 1), "radius": spec.get("radius", 2.5)}, action)
        elif "effect" in spec:
            effects_mod.apply_effect(self, actor, spec["effect"], action)

    def spawn_projectiles(self, actor, spec, power=1.0, move_type="skill", tags=()):
        n = spec.get("count", 1)
        spread = math.radians(spec.get("spread", 0.0))
        fwd, up = spec.get("offset", [0.6, 1.0])
        base = actor.facing + math.radians(spec.get("angle_offset", 0.0))
        tgt = actor.target if actor.target is not None and getattr(actor.target, "alive", False) else None
        if spec.get("aim", "target") == "target" and tgt is not None and actor.dist_to(tgt) < spec.get("range", 14) * 1.3:
            base = actor.angle_to(tgt) + math.radians(spec.get("angle_offset", 0.0))
        projs = []
        for i in range(n):
            a = base + (spread * (i / (n - 1) - 0.5) if n > 1 else 0.0)
            fx, fz = dir_of(a)
            p = Projectile(actor, actor.x + fx * fwd, actor.y + up * actor.scale, actor.z + fz * fwd, a, spec, power,
                           move_type, tags, target=tgt)
            projs.append(self.spawn(p))
        self.fx.push("shoot", actor=actor.id, visual=spec.get("visual", "bolt"), x=actor.x, y=actor.y + up, z=actor.z)
        return projs

    def spawn_zone(self, owner, spec, x, y, z, angle, power=1.0, team=None, move_type="skill", tags=()):
        zn = Zone(owner, x, y, z, angle, spec, power, team, move_type, tags)
        self.spawn(zn)
        if zn.delay > 0:
            self.fx.push("telegraph", zone=zn.id, x=x, y=y, z=z, radius=zn.max_radius, shape=zn.shape,
                         angle=angle, length=zn.length, width=zn.width, time=zn.delay, team=zn.team)
        return zn

    def apply_move_effect(self, actor, eff, action):
        effects_mod.apply_effect(self, actor, eff, action)

    # ------------------------------------------------------------------ passo de simulação
    def slowmo(self, scale, duration):
        self.time_scale = min(self.time_scale, scale)
        self._slowmo = max(self._slowmo, duration)

    def step(self, dt):
        if self._slowmo > 0:
            self._slowmo -= dt
            if self._slowmo <= 0:
                self.time_scale = 1.0
        dt *= self.time_scale
        self.time += dt
        if self.combat_heat > 0:
            self.combat_heat -= dt
        for group in (self.actors, self.props, self.pickups, self.projectiles, self.zones, self.misc):
            for e in list(group):
                if e.alive:
                    if self.paused_ai and e.kind in ("enemy", "boss"):
                        continue
                    e.update(dt)
        for pz in self.puzzles:
            pz.update(dt)
        alive_actors = [a for a in self.actors if a.alive and not a.dead]
        self.physics.separate(alive_actors)
        for a in alive_actors:
            if not getattr(a, "flying", False) and not getattr(a, "noclip", False):
                a.x, a.z, _ = self.level.collide_circle(a.x, a.z, a.radius, a.y)
        self._regions()
        self._cleanup()

    def _regions(self):
        p = self.player
        if p is None:
            return
        r = self.level.region_at(p.x, p.z)
        if r is not self.current_region:
            old = self.current_region
            self.current_region = r
            self.bus.emit("region", old=old, new=r)

    def _cleanup(self):
        def keep(e):
            if not e.alive:
                e.on_removed()
                return False
            return True
        for name in ("projectiles", "zones", "pickups", "misc"):
            setattr(self, name, [e for e in getattr(self, name) if keep(e)])
        new_actors = []
        for a in self.actors:
            if a.dead and a.kind in ("enemy",) and a.death_time > 3.0:
                a.alive = False
            if a.alive:
                new_actors.append(a)
            else:
                a.on_removed()
        self.actors = new_actors
        if any(not p.alive for p in self.props):
            self.props = [p for p in self.props if keep(p)]
            self.solids = [p for p in self.solids if p.alive]
            self.platforms = [p for p in self.platforms if p.alive]

    # ------------------------------------------------------------------ ganchos de regras
    def on_hit(self, att, tgt, hit):
        if hit.result in ("hit", "killed"):
            self.combat_heat = 6.0
        if att is not None and hasattr(att, "on_dealt_hit"):
            att.on_dealt_hit(tgt, hit)
        if hasattr(tgt, "on_took_hit"):
            tgt.on_took_hit(att, hit)
        self.bus.emit("hit", attacker=att, target=tgt, hit=hit)

    def on_projectile_hit(self, proj, tgt, hit):
        pass

    def on_zone_hit(self, zone, tgt, hit):
        pass

    def on_parry(self, defender, attacker, hit):
        self.combat_heat = 6.0
        self.bus.emit("parry", defender=defender, attacker=attacker, hit=hit)

    def on_posture_break(self, tgt, att, hit):
        if att is not None and hasattr(att, "on_broke_posture"):
            att.on_broke_posture(tgt, hit)
        self.bus.emit("posture_break", target=tgt, attacker=att)

    def on_status_proc(self, tgt, att, name):
        if att is not None and hasattr(att, "on_status_proc"):
            att.on_status_proc(tgt, name)

    def on_execution(self, att, victim, hit):
        if hasattr(att, "on_executed"):
            att.on_executed(victim, hit)

    def on_launch(self, actor):
        if self.player is not None:
            self.player.on_enemy_launched(actor) if hasattr(self.player, "on_enemy_launched") else None

    def on_move_start(self, actor, action):
        if actor.team == "player":
            for e in self.actors:
                if e.kind in ("enemy", "boss") and not e.dead and hasattr(e, "brain") and e.dist_to(actor) < 3.6:
                    e.brain.on_player_attack(actor, action)

    def on_move_end(self, actor, action, interrupted):
        if hasattr(actor, "on_move_end"):
            actor.on_move_end(action, interrupted)

    def on_dodge_end(self, actor, action):
        if hasattr(actor, "on_dodge_end"):
            actor.on_dodge_end(action)

    def on_actor_died(self, actor, killer):
        self.fx.push("death", actor=actor.id, x=actor.x, y=actor.y, z=actor.z, actor_kind=actor.kind,
                     material=actor.material)
        if killer is not None and hasattr(killer, "on_killed"):
            killer.on_killed(actor)
        if actor.kind in ("enemy", "boss") and hasattr(actor, "on_death_rewards"):
            actor.on_death_rewards(self)
        self.bus.emit("died", actor=actor, killer=killer)

    def hazard_damage(self, actor, cell):
        el = cell.element or "fogo"
        amount = actor.max_hp * cell.damage
        hit = Hit(None, {el: amount}, posture=0, knockback=0, stun=0.0, can_crit=False, no_reaction=True,
                  pos=(actor.x, actor.y - 1, actor.z), move_type="hazard")
        if actor.iframes > 0:
            return
        before = actor.iframes
        apply_hit(actor, hit)
        actor.iframes = before
        self.fx.push("hazard", x=actor.x, y=actor.y, z=actor.z, element=el)

    def message(self, text, kind="info"):
        self.messages.append((text, kind))
        self.fx.push("message", text=text, style=kind)
