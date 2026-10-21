"""Entidades da simulação: Entity (base) -> Actor (combatente com vida, postura, ações e status)."""
import math
import itertools

from ..core.mathutil import dir_of, angle_of, turn_towards, clamp
from .stats import Stats
from .combat.status import StatusSet

_ids = itertools.count(1)

GRAVITY = 30.0


class Entity:
    kind = "entity"
    radius = 0.3
    height = 1.0
    team = "neutral"
    solid = False             # bloqueia atores (ex.: portas fechadas, caixas)
    hittable = False          # pode receber golpes (ex.: barris, cristais)
    persistent_id = None      # id usado no save (baús, alavancas...)

    def __init__(self, x=0.0, z=0.0, y=0.0):
        self.id = next(_ids)
        self.x, self.y, self.z = float(x), float(y), float(z)
        self.vx = self.vy = self.vz = 0.0
        self.world = None
        self.alive = True
        self.t = 0.0
        self.facing = -math.pi / 2       # olhando para o sul (para a câmera)
        self.visible = True

    @property
    def pos(self):
        return (self.x, self.y, self.z)

    def attach(self, world):
        self.world = world

    def update(self, dt):
        self.t += dt

    def remove(self):
        self.alive = False

    def dist_to(self, other):
        return math.hypot(other.x - self.x, other.z - self.z)

    def dist_to_point(self, x, z):
        return math.hypot(x - self.x, z - self.z)

    def angle_to(self, other):
        return angle_of(other.x - self.x, other.z - self.z)

    def forward(self):
        return dir_of(self.facing)

    def on_removed(self):
        pass

    # para debug de hitbox/colisão na renderização
    def debug_shapes(self):
        return [("circle", self.x, self.z, self.radius, (0.3, 0.8, 1.0))]


class Actor(Entity):
    """Combatente genérico (jogador, inimigos, chefes)."""
    kind = "actor"
    radius = 0.35
    height = 1.7
    team = "enemy"
    material = "flesh"        # som/partícula de impacto: flesh, bone, metal, stone, ether, wood
    stagger_resist = 0        # 0 = qualquer golpe interrompe; 1 = só golpes pesados; 2 = só ruptura de postura
    weight = 1.0              # resistência a empurrões e lançamentos
    can_be_launched = True
    gravity_scale = 1.0
    base_speed = 4.0
    turn_speed = 14.0
    tags = ()

    def __init__(self, x=0.0, z=0.0, y=0.0):
        super().__init__(x, z, y)
        self.stats = Stats()
        self.status = StatusSet(self)
        self.max_hp = 100.0
        self.hp = 100.0
        self.max_fp = 0.0
        self.fp = 0.0
        self.max_posture = 50.0
        self.posture = 0.0
        self.posture_delay = 0.0
        self.posture_regen = 18.0
        self.action = None
        self.grounded = True
        self.air_time = 0.0
        self.juggle = 0            # golpes aéreos recebidos seguidos (decai a gravidade reduzida)
        self.kx = self.kz = 0.0    # empurrão (knockback)
        self.move_x = self.move_z = 0.0   # velocidade de locomoção desejada (controle/IA)
        self.hitstop = 0.0
        self.iframes = 0.0
        self.flash = 0.0
        self.flash_color = (1.0, 1.0, 1.0)
        self.dead = False
        self.death_time = 0.0
        self.anim = "idle"
        self.anim_t = 0.0
        self.anim_p = None         # progresso 0..1 para animações de ação (None = usa anim_t em laço)
        self.last_hit_by = None
        self.last_safe = (self.x, self.y, self.z)
        self.broken = 0.0          # tempo restante de postura rompida (vulnerável a execução)
        self.target = None
        self.mirror_anim = False
        self.scale = 1.0
        self.speed_mult_extra = 1.0
        self.status_resist = {}
        self.status_duration_mult = 1.0
        self.dmg_numbers = True
        self.on_ground_hazard = 0.0
        self.invulnerable = False   # cutscenes, transições de fase de chefe
        self.untargetable = False
        self.super_armor = 0.0      # tempo de super armadura (não é interrompido)
        self.hurt_timer = 0.0
        self.gravity_scale_override = None
        self.atk = {"fisico": 10.0}
        self.resist = {}

    # ------------------------------------------------------------------ propriedades derivadas
    @property
    def speed(self):
        return self.base_speed * max(0.2, 1.0 + self.stats.get("speed_mult")) * self.speed_mult_extra

    def is_hostile_to(self, other):
        return other is not self and getattr(other, "team", "neutral") not in (self.team, "neutral") and self.team != "neutral"

    def alive_and_active(self):
        return self.alive and not self.dead

    def facing_towards(self, other, max_angle=math.radians(100)):
        a = self.angle_to(other)
        d = (a - self.facing + math.pi) % math.tau - math.pi
        return abs(d) <= max_angle * 0.5 + 1e-6

    def is_behind(self, attacker, cone=math.radians(110)):
        """O atacante está nas costas deste ator?"""
        back = self.facing + math.pi
        a = self.angle_to(attacker)
        d = (a - back + math.pi) % math.tau - math.pi
        return abs(d) <= cone * 0.5

    def face(self, angle, dt=None):
        if dt is None:
            self.facing = angle
        else:
            self.facing = turn_towards(self.facing, angle, self.turn_speed * dt)

    def face_target(self, other, dt=None):
        self.face(self.angle_to(other), dt)

    # ------------------------------------------------------------------ ações
    def set_action(self, action):
        if self.action is not None:
            self.action.exit(interrupted=True)
        self.action = action
        if action is not None:
            action.start(self)

    def can_act(self):
        return not self.dead and (self.action is None or self.action.interruptible_by_input())

    # ------------------------------------------------------------------ dano
    def take_dot(self, amount, element):
        if self.dead or self.invulnerable:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.die(None)

    def absorb(self, dmg):
        """Barreiras/escudos absorvem dano antes da vida (sobrescrito pelo jogador)."""
        return dmg

    def heal(self, amount):
        if self.dead:
            return 0.0
        before = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        got = self.hp - before
        if got > 0.5 and self.world:
            self.world.fx.push("heal", x=self.x, y=self.y + self.height, z=self.z, amount=got, actor=self.id)
        return got

    def add_posture(self, amount):
        if self.max_posture <= 0 or self.broken > 0:
            return False
        self.posture += amount * max(0.1, 1.0 + self.stats.get("posture_taken_mult"))
        self.posture_delay = 1.6
        if self.posture >= self.max_posture:
            self.posture = self.max_posture
            return True
        return False

    def die(self, killer):
        if self.dead:
            return
        self.dead = True
        self.hp = 0
        self.death_time = 0.0
        from .combat.actions import DeathAction
        self.set_action(DeathAction())
        if self.world:
            self.world.on_actor_died(self, killer)

    # ------------------------------------------------------------------ tempo
    def update(self, dt):
        if self.hitstop > 0:
            self.hitstop -= dt
            return
        super().update(dt)
        self.anim_t += dt
        self.status.update(dt)
        if self.iframes > 0:
            self.iframes -= dt
        if self.flash > 0:
            self.flash = max(0.0, self.flash - dt * 6)
        if self.super_armor > 0:
            self.super_armor -= dt
        if self.broken > 0:
            self.broken -= dt
            if self.broken <= 0:
                self.posture = 0.0
        elif self.posture > 0:
            if self.posture_delay > 0:
                self.posture_delay -= dt
            else:
                rate = self.posture_regen * (1.6 if self.action is None else 0.8)
                self.posture = max(0.0, self.posture - rate * dt)
        regen = self.stats.get("hp_regen")
        if regen and not self.dead:
            self.hp = min(self.max_hp, self.hp + regen * dt)
        if self.dead:
            self.death_time += dt
        if self.action is not None:
            keep = self.action.update(dt)
            if not keep and self.action is not None:
                a = self.action
                self.action = None
                a.exit(interrupted=False)
                if a.chain is not None and not self.dead:
                    self.set_action(a.chain)
        if self.action is None and not self.dead:
            self.think(dt)
        if self.world is not None:
            self.world.physics.step(self, dt)

    def think(self, dt):
        """Locomoção/IA quando não há ação em curso (sobrescrito por Player e Enemy)."""
        self.move_x = self.move_z = 0.0
        self.set_anim("idle")

    def set_anim(self, name, progress=None):
        if name != self.anim:
            self.anim = name
            self.anim_t = 0.0
        self.anim_p = progress

    # ------------------------------------------------------------------ ataque
    HEAVY_TYPES = ("heavy", "charged", "launcher", "slam", "finisher", "execution", "counter")

    def attack_power(self, move, spec):
        """Dano base por elemento antes do multiplicador do golpe (sobrescrito pelo jogador)."""
        return dict(self.atk)

    def build_hit(self, move, spec, action):
        from .combat.damage import Hit
        base = self.attack_power(move, spec)
        mult = spec.get("dmg", 1.0) * action.power
        elements = {el: v * mult for el, v in base.items()}
        total = sum(elements.values())
        for el, frac in spec.get("elem", {}).items():
            elements[el] = elements.get(el, 0.0) + total * frac
        tags = set(move.tags) | set(spec.get("tags", []))
        status = dict(spec.get("status", {}))
        extra_lifesteal = 0.0
        launch = spec.get("launch", 0.0)
        posture = spec.get("posture", 8.0) * action.power
        ms = getattr(action, "moveset", None)
        if ms is not None:
            for eff in ms.effects_for(move):
                for el, frac in eff.get("elem", {}).items():
                    elements[el] = elements.get(el, 0.0) + total * frac
                for st, v in eff.get("status", {}).items():
                    status[st] = status.get(st, 0.0) + v
                tags |= set(eff.get("tags", []))
                extra_lifesteal += eff.get("lifesteal", 0.0)
                launch = max(launch, eff.get("launch", 0.0))
                posture *= eff.get("posture_mult", 1.0)
                if eff.get("dmg_mult"):
                    elements = {k: v * eff["dmg_mult"] for k, v in elements.items()}
        heavy = spec.get("heavy", move.type in self.HEAVY_TYPES)
        return Hit(self, elements, posture=posture, knockback=spec.get("kb", 2.0),
                   launch=launch, stun=spec.get("stun", 0.3), heavy=heavy,
                   unblockable=spec.get("unblockable", False), unparryable=spec.get("unparryable", False),
                   status=status, tags=tags, source=move.id, crit_bonus=spec.get("crit", 0.0),
                   hitstop=spec.get("hitstop"), move_type=move.type, lifesteal=extra_lifesteal,
                   dir_angle=(self.facing if spec.get("kb_dir") == "forward" else None))

    def on_land(self, fall_speed):
        self.juggle = 0

    def on_fall_void(self):
        self.die(None)

    def debug_shapes(self):
        out = [("circle", self.x, self.z, self.radius, (0.3, 1.0, 0.4))]
        if self.action is not None:
            out.extend(self.action.debug_shapes())
        return out
