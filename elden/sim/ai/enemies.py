"""Inimigos definidos por dados (data/enemies.json) + variantes de elite."""
import math

from ...core.data import DB
from ..entity import Actor
from ..combat.actions import BlockAction
from .brain import Brain


class Enemy(Actor):
    kind = "enemy"
    team = "enemy"

    def __init__(self, enemy_id, x=0.0, z=0.0, elite=False, unique=None, level_scale=1.0, **kw):
        super().__init__(x, z)
        d = DB.enemies[enemy_id]
        self.enemy_id = enemy_id
        self.d = d
        self.elite = elite
        self.unique = unique
        self.name = d["name"]
        mult_hp = mult_atk = mult_posture = 1.0
        attacks = list(d.get("attacks", []))
        self.scale = d.get("scale", 1.0)
        self.aura = None
        if elite:
            el = d.get("elite", {})
            self.name = el.get("name", d["name"] + " de Elite")
            mult_hp = el.get("hp_mult", 2.4)
            mult_atk = el.get("atk_mult", 1.35)
            mult_posture = el.get("posture_mult", 1.8)
            attacks += el.get("attacks", [])
            self.scale *= el.get("scale", 1.15)
            self.aura = el.get("aura", (0.9, 0.2, 0.15))
        self.max_hp = self.hp = d["hp"] * mult_hp * level_scale
        self.max_posture = d.get("posture", 40) * mult_posture
        self.posture_regen = d.get("posture_regen", 14.0)
        self.atk = {k: v * mult_atk * (0.85 + 0.15 * level_scale) for k, v in d.get("atk", {"fisico": 8}).items()}
        self.resist = dict(d.get("resist", {}))
        self.base_speed = d.get("speed", 3.5)
        self.radius = d.get("radius", 0.38) * (self.scale / d.get("scale", 1.0)) ** 0.5
        self.height = d.get("height", 1.7) * self.scale / max(0.01, d.get("scale", 1.0)) if elite else d.get("height", 1.7)
        self.weight = d.get("weight", 1.0) * (1.4 if elite else 1.0)
        self.stagger_resist = d.get("stagger_resist", 0) + (1 if elite and d.get("stagger_resist", 0) == 0 else 0)
        self.can_be_launched = d.get("launchable", True) and not elite
        self.tags = tuple(d.get("tags", []))
        self.material = d.get("material", "flesh")
        self.aggro = d.get("aggro", 8.0)
        self.leash = d.get("leash", 22.0)
        self.attacks = attacks
        self.sprite = d.get("sprite", enemy_id)
        self.flying = d.get("flying", False)
        self.hover = d.get("hover", 1.3)
        self.weak_back = d.get("weak_back", 0.0)
        self.break_time = d.get("break_time", 2.4)
        self.grace_reward = d.get("grace", 15) * (3.0 if elite else 1.0) * level_scale
        self.avoid_hazards = True
        self.status_resist = dict(d.get("status_resist", {}))
        self.turn_speed = d.get("turn_speed", 10.0)
        self.marked = 0.0
        self.mark_kind = None
        self.block_timer = 0.0
        self.summoned = False
        self.executable = d.get("executable", True)
        self.parry_staggers = d.get("parry_staggers", True)
        self.brain = Brain(self, d.get("behavior", "grunt"), d.get("ai", {}))
        if self.flying:
            self.can_be_launched = False

    def think(self, dt):
        self.brain.update(dt)

    def update(self, dt):
        if self.d.get("dummy") and self.hp < self.max_hp and self.t - getattr(self, "_last_hurt", 0) > 2.5:
            self.hp = min(self.max_hp, self.hp + self.max_hp * 0.4 * dt)
        if self.marked > 0:
            self.marked = max(0.0, self.marked - dt)
        if isinstance(self.action, BlockAction):
            self.block_timer -= dt
            if self.block_timer <= 0:
                self.action.holding = False
        if self.flying and not self.dead and self.world is not None:
            g = self.world.level.ground_at(self.x, self.z)
            target_y = (g if g is not None else self.y - self.hover) + self.hover
            self.y += (target_y - self.y) * min(1.0, dt * 4)
        super().update(dt)
        if self.flying and self.dead and self.world is not None:
            g = self.world.level.ground_at(self.x, self.z)
            if g is not None and self.y > g:
                self.y = max(g, self.y - dt * 6)

    def on_took_hit(self, att, hit):
        self._last_hurt = self.t
        if att is not None and not self.dead:
            if not self.brain.alerted:
                # golpe furtivo/de longe: alerta
                self.brain.alert(att if getattr(att, "team", "") == "player" else self.world.player)

    def die(self, killer):
        if self.d.get("dummy"):
            # boneco de treino nunca morre: reergue-se
            self.hp = self.max_hp
            if self.world:
                self.world.fx.push("dummy_reset", actor=self.id)
            return
        super().die(killer)

    def on_death_rewards(self, world):
        self.brain.release_token()
        s = world.session
        if s is not None:
            s.on_enemy_killed(self)

    def on_fall_void(self):
        self.die(None)

    def debug_label(self):
        return f"{self.name} [{self.brain.state}]"


def create_enemy(enemy_id, x, z, **kw):
    if enemy_id in DB.bosses:
        from .bosses import BOSS_CLASSES
        bd = DB.bosses[enemy_id]
        cls = BOSS_CLASSES[bd["class"]]
        return cls(enemy_id, x, z, **kw)
    return Enemy(enemy_id, x, z, **kw)
