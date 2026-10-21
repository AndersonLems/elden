"""Base dos chefes: fases por limiar de vida, transições, padrões de ataque e regras de ruptura.

Cada chefe define em data/bosses.json suas fases (ataques, velocidade, nome da fase) e o código da
subclasse cuida das mecânicas únicas (arena, partes vulneráveis, clones...).
"""
import math

from ....core.data import DB
from ....core.mathutil import angle_diff, dir_of
from ...combat.actions import MoveAction, TimedAction, StaggerAction, DodgeAction
from ...combat.moves import get_move
from ...entity import Actor
from ..enemies import Enemy


class Boss(Enemy):
    kind = "boss"
    is_boss = True

    def __init__(self, boss_id, x=0.0, z=0.0, **kw):
        bd = DB.bosses[boss_id]
        self.bd = bd
        super().__init__(boss_id if boss_id in DB.enemies else bd["base"], x, z, **kw)
        self.boss_id = boss_id
        self.name = bd["name"]
        self.title = bd.get("title", "")
        self.max_hp = self.hp = bd["hp"]
        self.max_posture = bd.get("posture", 200)
        self.stagger_resist = 2
        self.can_be_launched = False
        self.weight = bd.get("weight", 6.0)
        self.radius = bd.get("radius", 0.9)
        self.height = bd.get("height", 3.0)
        self.scale = bd.get("scale", 2.0)
        self.atk = dict(bd.get("atk", {"fisico": 18}))
        self.resist = dict(bd.get("resist", {}))
        self.base_speed = bd.get("speed", 4.0)
        self.break_time = bd.get("break_time", 3.2)
        self.phases = bd["phases"]
        self.phase = 0
        self.attacks = list(self.phases[0]["attacks"])
        self.grace_reward = bd.get("grace", 1000)
        self.brain.p.update({"pref": bd.get("pref", 2.2), "aggression": 0.95, "strafe": 0.6, "wait": tuple(bd.get("wait", (0.5, 1.1)))})
        self.brain.alerted = False
        self.awake = False
        self.transitioning = False
        self.parry_staggers = False
        self.aggro = 30.0
        self.leash = 999.0
        self.avoid_hazards = True
        self.status_resist = {"choque": 0.5, "congelamento": 0.4}
        self.status_duration_mult = 0.6
        self.combo_queue = []
        self.sprite = bd.get("sprite", self.sprite)

    # ------------------------------------------------------------------ ciclo
    def wake(self, player):
        if self.awake:
            return
        self.awake = True
        self.brain.alert(player)
        if self.world:
            self.world.fx.push("boss_start", boss=self.boss_id, name=self.name, title=self.title)
            self.world.bus.emit("boss_start", boss=self)
        intro = self.bd.get("intro_anim")
        if intro:
            self.set_action(TimedAction(intro, self.bd.get("intro_time", 1.6), invulnerable=True, name="intro"))

    def think(self, dt):
        if not self.awake:
            self.move_x = self.move_z = 0.0
            self.set_anim("idle")
            p = self.world.player
            if p is not None and not p.dead and self.dist_to(p) < self.bd.get("wake_radius", 9.0):
                self.wake(p)
            return
        if self.combo_queue:
            nxt = self.combo_queue.pop(0)
            self.start_boss_move(nxt)
            return
        self.boss_think(dt)
        self.brain.update(dt)

    def boss_think(self, dt):
        """Gancho por quadro para mecânicas especiais."""

    def start_boss_move(self, move_id, target=None):
        move = get_move(move_id)
        t = target or self.brain.target or (self.world.player if self.world else None)
        if t is not None:
            self.face(self.angle_to(t))
        self.set_action(MoveAction(move, target=t))
        if self.world:
            self.world.fx.push("enemy_windup", actor=self.id, move=move.id, x=self.x, y=self.y + self.height, z=self.z,
                               unblockable=any(h.get("unblockable") for h in move.hits),
                               time=move.hits[0]["t"][0] if move.hits else 0.3)

    def update(self, dt):
        super().update(dt)
        if self.dead or not self.awake:
            return
        # transição de fase
        nxt = self.phase + 1
        if nxt < len(self.phases) and not self.transitioning and self.hp <= self.max_hp * self.phases[nxt]["hp"]:
            self.begin_phase(nxt)

    def begin_phase(self, n):
        self.transitioning = True
        self.phase = n
        ph = self.phases[n]
        self.broken = 0.0
        self.posture = 0.0
        self.combo_queue = []

        def done():
            self.transitioning = False
            self.attacks = list(ph["attacks"])
            self.base_speed = ph.get("speed", self.base_speed)
            if "sprite" in ph:
                self.sprite = ph["sprite"]
            if "scale" in ph:
                self.scale = ph["scale"]
                self.radius = ph.get("radius", self.radius)
                self.height = ph.get("height", self.height)
            if "pref" in ph:
                self.brain.p["pref"] = ph["pref"]
            if "wait" in ph:
                self.brain.p["wait"] = tuple(ph["wait"])
            self.on_phase(n)

        self.set_action(TimedAction(ph.get("anim", "roar"), ph.get("transition", 2.2), done, at=0.6,
                                    invulnerable=True, name="phase"))
        if self.world:
            self.world.fx.push("boss_phase", boss=self.boss_id, phase=n, name=ph.get("name", ""),
                               x=self.x, y=self.y, z=self.z)
            self.world.fx.push("shake", amount=0.6, time=1.0)

    def on_phase(self, n):
        """Mudanças de arena e comportamento ao entrar numa fase (subclasses)."""

    def land_on_marker(self):
        """Saltos altos: o chefe reaparece no ponto marcado pelo aviso no chão."""
        m = getattr(self, "last_marker", None)
        if m is None or self.world is None:
            return
        g = self.world.level.ground_at(*m)
        if g is None:
            return
        self.world.fx.push("teleport", x0=self.x, y0=self.y, z0=self.z, x=m[0], y=g, z=m[1], actor=self.id, tkind="leap")
        self.x, self.z, self.y = m[0], m[1], g

    def on_death_rewards(self, world):
        self.brain.release_token()
        if world.session is not None:
            world.session.on_boss_defeated(self)
        world.bus.emit("boss_defeated", boss=self)

    # o chefe não é interrompido por golpes comuns, mas a ruptura de postura abre execução
    @property
    def executable(self):
        return True

    @executable.setter
    def executable(self, v):
        pass


class BossPart(Actor):
    """Parte destrutível de um chefe (braços do Serafim, fragmentos de Aurelion)."""
    kind = "enemy"
    team = "enemy"
    material = "metal"
    stagger_resist = 2
    can_be_launched = False

    def __init__(self, boss, name, hp, offset, radius=0.7, height=1.6, sprite="part", material="metal"):
        super().__init__(boss.x, boss.z, boss.y)
        self.boss = boss
        self.name = name
        self.max_hp = self.hp = hp
        self.offset = offset            # (lateral, frente)
        self.radius = radius
        self.height = height
        self.sprite = sprite
        self.material = material
        self.max_posture = 0
        self.weight = 99
        self.resist = dict(boss.resist)
        self.attacks = []
        self.noclip = True
        self.elite = True
        self.summoned = False
        self.marked = 0.0
        self.is_part = True
        self.grace_reward = 0
        self.executable = False

    def update(self, dt):
        b = self.boss
        if b.dead and not self.dead:
            self.die(None)
        if not self.dead:
            side, fwd = self.offset
            f = b.facing
            fx, fz = dir_of(f)
            sx, sz = -fz, fx
            self.x = b.x + fx * fwd + sx * side
            self.z = b.z + fz * fwd + sz * side
            self.y = b.y + 0.2
            self.facing = f
            self.anim_p = None
        super().update(dt)

    def think(self, dt):
        self.move_x = self.move_z = 0.0

    def die(self, killer):
        if self.dead:
            return
        super().die(killer)
        if hasattr(self.boss, "on_part_destroyed"):
            self.boss.on_part_destroyed(self)

    def on_death_rewards(self, world):
        pass

    @property
    def brain(self):
        return _NullBrain


class _NullBrainType:
    alerted = True

    def aware(self):
        return True

    def on_player_attack(self, *a):
        pass

    def release_token(self):
        pass

    def alert(self, *a):
        pass


_NullBrain = _NullBrainType()
