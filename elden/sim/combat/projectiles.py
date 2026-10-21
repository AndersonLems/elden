"""Projéteis e zonas de efeito (área), definidos por especificações de dados."""
import math

from ...core.mathutil import dir_of, angle_of, turn_towards
from ..entity import Entity
from .damage import Hit, apply_hit


def _hit_from(owner, spec, power, move_type, tags=()):
    """Monta um pacote de dano a partir da especificação (dmg multiplica o poder de ataque do dono)."""
    if owner is not None and hasattr(owner, "attack_power"):
        base = owner.attack_power(None, spec)
    else:
        base = {"fisico": spec.get("base", 10.0)}
    mult = spec.get("dmg", 1.0) * power
    elements = {el: v * mult for el, v in base.items()}
    if spec.get("pure"):
        elements = {}
        total = sum(base.values()) * mult
        for el, frac in spec["pure"].items():
            elements[el] = total * frac
    total = sum(elements.values())
    for el, frac in spec.get("elem", {}).items():
        elements[el] = elements.get(el, 0.0) + total * frac
    return dict(elements=elements, posture=spec.get("posture", 6.0) * power, knockback=spec.get("kb", 1.5),
                launch=spec.get("launch", 0.0), stun=spec.get("stun", 0.25), heavy=spec.get("heavy", False),
                unblockable=spec.get("unblockable", False), unparryable=spec.get("unparryable", True),
                status=dict(spec.get("status", {})), tags=set(tags) | set(spec.get("tags", [])),
                move_type=spec.get("move_type", move_type), crit_bonus=spec.get("crit", 0.0),
                hitstop=spec.get("hitstop", 0.04), lifesteal=spec.get("lifesteal", 0.0),
                no_reaction=spec.get("no_reaction", False))


class Projectile(Entity):
    kind = "projectile"

    def __init__(self, owner, x, y, z, angle, spec, power=1.0, move_type="skill", tags=(), target=None):
        super().__init__(x, z, y)
        self.owner = owner
        self.team = owner.team if owner is not None else "enemy"
        self.spec = spec
        self.speed = spec.get("speed", 14.0)
        self.facing = angle
        self.vy = spec.get("vy", 0.0)
        self.gravity = spec.get("gravity", 0.0)
        self.radius = spec.get("radius", 0.22)
        self.height = self.radius * 2
        self.life = spec.get("life", spec.get("range", 14.0) / max(1.0, self.speed))
        self.pierce = spec.get("pierce", 0)
        self.homing = math.radians(spec.get("homing", 0.0))
        self.target = target
        self.visual = spec.get("visual", "bolt")
        self.light = spec.get("light")
        self.explode = spec.get("explode")
        self.bounces = spec.get("bounce", 0)
        self.hitpack = _hit_from(owner, spec, power, move_type, tags)
        self.hitpack["tags"].add("ranged")
        self.already = set()
        self.reflectable = spec.get("reflectable", True)
        self.reflected = False
        self.power = power

    def update(self, dt):
        super().update(dt)
        self.life -= dt
        if self.life <= 0:
            self.impact(None, expire=True)
            return
        w = self.world
        if self.homing and self.target is not None and getattr(self.target, "alive", False) and not self.target.dead:
            want = self.angle_to(self.target)
            self.facing = turn_towards(self.facing, want, self.homing * dt)
        fx, fz = dir_of(self.facing)
        self.vy -= self.gravity * dt
        nx = self.x + fx * self.speed * dt
        nz = self.z + fz * self.speed * dt
        ny = self.y + self.vy * dt
        lvl = w.level
        cx, cz = int(math.floor(nx)), int(math.floor(nz))
        c = lvl.cell(cx, cz)
        blocked = c is None or (not c.void and (c.solid or c.height > ny))
        if not blocked:
            for s in w.solids:
                if s.alive and s.solid and s.contains_point(nx, ny, nz):
                    blocked = True
                    break
        if blocked:
            if self.bounces > 0:
                self.bounces -= 1
                # reflete no eixo de maior penetração
                ox, oz = int(math.floor(self.x)), int(math.floor(self.z))
                if cx != ox:
                    fx = -fx
                if cz != oz:
                    fz = -fz
                self.facing = angle_of(fx, fz)
                return
            self.x, self.y, self.z = nx, ny, nz
            self.impact(None)
            return
        self.x, self.y, self.z = nx, ny, nz
        g = lvl.ground_at(nx, nz)
        if self.gravity > 0 and g is not None and self.y <= g:
            self.y = g
            self.impact(None)
            return
        for tgt in w.projectile_targets(self):
            if tgt.id in self.already:
                continue
            dy = self.y - tgt.y
            if dy < -self.radius or dy > tgt.height + self.radius:
                continue
            if math.hypot(tgt.x - self.x, tgt.z - self.z) > tgt.radius + self.radius:
                continue
            self.already.add(tgt.id)
            hit = Hit(self.owner, dict(self.hitpack["elements"]), **{k: v for k, v in self.hitpack.items() if k != "elements"},
                      source=self, pos=(self.x - fx, self.y, self.z - fz), dir_angle=self.facing)
            if getattr(tgt, "is_prop", False):
                tgt.receive_hit(hit)
            else:
                apply_hit(tgt, hit)
            if w is not None:
                w.on_projectile_hit(self, tgt, hit)
            if hit.result == "parried" and self.reflectable:
                self.reflect(tgt)
                return
            if hit.result == "evaded":
                continue
            if self.pierce > 0:
                self.pierce -= 1
            else:
                self.impact(tgt)
                return

    def reflect(self, by):
        """Projétil aparado: volta contra quem atirou."""
        self.team = by.team
        self.owner_original = self.owner
        self.owner = by
        self.facing += math.pi
        if self.owner_original is not None and getattr(self.owner_original, "alive", False):
            self.facing = self.angle_to(self.owner_original)
            self.target = self.owner_original
            self.homing = math.radians(360)
        self.speed *= 1.3
        self.life = 2.0
        self.already.clear()
        self.reflected = True
        self.hitpack["elements"] = {k: v * 2.0 for k, v in self.hitpack["elements"].items()}
        self.hitpack["posture"] *= 3.0
        if self.world:
            self.world.fx.push("reflect", x=self.x, y=self.y, z=self.z)

    def impact(self, target, expire=False):
        if not self.alive:
            return
        w = self.world
        if self.explode and w is not None and (not expire or self.spec.get("explode_on_expire", False)):
            spec = dict(self.explode)
            spec.setdefault("at", "point")
            w.spawn_zone(self.owner, spec, self.x, self.y, self.z, self.facing, self.power, team=self.team)
        if w is not None and not expire:
            w.fx.push("proj_impact", x=self.x, y=self.y, z=self.z, visual=self.visual)
        self.remove()


class Zone(Entity):
    """Área de efeito: explosões, campos persistentes, ondas de choque em anel, feixes, pilares.

    Fases: aviso (delay, mostra o telegráfico) -> ativo (dur) com acertos únicos ou periódicos (tick).
    """
    kind = "zone"

    def __init__(self, owner, x, y, z, angle, spec, power=1.0, team=None, move_type="skill", tags=()):
        super().__init__(x, z, y)
        self.owner = owner
        self.team = team or (owner.team if owner is not None else "enemy")
        self.spec = spec
        self.shape = spec.get("zone", "burst")
        self.radius = spec.get("radius", 2.0)
        self.inner = 0.0
        self.delay = spec.get("delay", 0.0)
        self.dur = spec.get("dur", 0.15)
        self.tick = spec.get("tick", 0.0)
        self.tick_timer = 0.0
        self.facing = angle
        self.length = spec.get("length", 6.0)
        self.width = spec.get("width", 1.0)
        self.ring_speed = spec.get("ring_speed", 8.0)
        self.ring_width = spec.get("ring_width", 0.9)
        self.pull = spec.get("pull", 0.0)
        self.visual = spec.get("visual", "burst")
        self.light = spec.get("light")
        self.hitpack = _hit_from(owner, spec, power, move_type, tags)
        self.already = set()
        self.follow = spec.get("follow", False)
        self.heal_team = spec.get("heal", 0.0)
        self.buff = spec.get("buff")
        self.y0 = spec.get("y", [-0.5, 3.0])
        self.active_started = False
        self.max_radius = self.radius
        self.spin = spec.get("spin", 0.0)
        self.facing += math.radians(spec.get("angle_offset", 0.0))
        if self.shape == "ring":
            self.inner = 0.0
            self.radius = 0.2

    @property
    def telegraphing(self):
        return self.t < self.delay

    def update(self, dt):
        super().update(dt)
        w = self.world
        if self.follow and self.owner is not None and getattr(self.owner, "alive", False):
            self.x, self.z = self.owner.x, self.owner.z
            self.y = self.owner.y
        if self.spin and self.t >= self.delay:
            self.facing += self.spin * dt
        if self.t < self.delay:
            return
        if not self.active_started:
            self.active_started = True
            if w is not None:
                w.fx.push("zone_active", zone=self.id, visual=self.visual, x=self.x, y=self.y, z=self.z,
                          radius=self.max_radius, shape=self.shape, angle=self.facing, length=self.length)
        at = self.t - self.delay
        if at > self.dur:
            self.remove()
            return
        if self.shape == "ring":
            self.radius = min(self.max_radius, 0.2 + at * self.ring_speed)
            self.inner = max(0.0, self.radius - self.ring_width)
        if self.tick > 0:
            self.tick_timer -= dt
            if self.tick_timer <= 0:
                self.tick_timer = self.tick
                self.already.clear()
            else:
                if self.pull:
                    self._pull(dt)
                return
        if self.pull:
            self._pull(dt)
        self._apply()

    def _pull(self, dt):
        for tgt in self.world.zone_targets(self):
            d = math.hypot(self.x - tgt.x, self.z - tgt.z)
            if 0.3 < d < self.max_radius * 1.5:
                k = self.pull * dt / max(0.5, tgt.weight)
                tgt.x += (self.x - tgt.x) / d * k
                tgt.z += (self.z - tgt.z) / d * k

    def contains(self, tgt):
        dy = tgt.y - self.y
        if dy > self.y0[1] or dy + tgt.height < self.y0[0]:
            return False
        dx, dz = tgt.x - self.x, tgt.z - self.z
        d = math.hypot(dx, dz)
        if self.shape in ("burst", "field", "pillar"):
            return d <= self.radius + tgt.radius
        if self.shape == "ring":
            return self.inner - tgt.radius <= d <= self.radius + tgt.radius
        if self.shape == "beam":
            fx, fz = dir_of(self.facing)
            along = dx * fx + dz * fz
            across = abs(-dx * fz + dz * fx)
            return -tgt.radius <= along <= self.length + tgt.radius and across <= self.width * 0.5 + tgt.radius
        if self.shape == "cone":
            if d > self.radius + tgt.radius:
                return False
            a = math.atan2(dz, dx)
            diff = abs((a - self.facing + math.pi) % math.tau - math.pi)
            return diff <= math.radians(self.spec.get("angle", 90)) * 0.5
        return False

    def _apply(self):
        w = self.world
        if self.heal_team:
            for ally in w.allies_of(self.team):
                if ally.id not in self.already and self.contains(ally):
                    self.already.add(ally.id)
                    ally.heal(ally.max_hp * self.heal_team)
            return
        if self.buff:
            for ally in w.allies_of(self.team):
                if self.contains(ally):
                    ally.status.add_buff(self.buff["id"], self.buff.get("mods", {}), self.buff.get("time", 1.0))
        if not self.hitpack["elements"] and not self.hitpack["status"]:
            return
        for tgt in w.zone_targets(self):
            if tgt.id in self.already:
                continue
            if not self.contains(tgt):
                continue
            self.already.add(tgt.id)
            hp = self.hitpack
            ang = math.atan2(tgt.z - self.z, tgt.x - self.x)
            hit = Hit(self.owner, dict(hp["elements"]), **{k: v for k, v in hp.items() if k != "elements"},
                      source=self, pos=(self.x, self.y, self.z), dir_angle=ang)
            if getattr(tgt, "is_prop", False):
                tgt.receive_hit(hit)
            else:
                apply_hit(tgt, hit)
            w.on_zone_hit(self, tgt, hit)

    def debug_shapes(self):
        if self.shape == "beam":
            return [("line", self.x, self.z, self.facing, self.length, self.width)]
        return [("circle", self.x, self.z, self.radius, (1.0, 0.6, 0.1) if not self.telegraphing else (1, 0.1, 0.1))]
