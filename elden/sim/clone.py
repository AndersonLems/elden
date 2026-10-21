"""Clone sombrio (Runa do Eclipse, Dança das Sombras): golpeia o inimigo mais próximo ou serve de isca."""
import math

from .entity import Entity
from .combat.damage import Hit, apply_hit


class ShadowClone(Entity):
    kind = "clone"

    def __init__(self, owner, life=1.5, mode="strike", power=0.5):
        super().__init__(owner.x, owner.z, owner.y)
        self.owner = owner
        self.life = life
        self.max_life = life
        self.mode = mode
        self.power = power
        self.facing = owner.facing
        self.team = owner.team
        self.anim = "idle"
        self.anim_p = None
        self.anim_t = 0.0
        self.struck = False
        self.target = None
        self.radius = owner.radius
        self.height = owner.height

    def update(self, dt):
        super().update(dt)
        self.anim_t += dt
        self.life -= dt
        w = self.world
        if self.life <= 0:
            w.fx.push("vanish", x=self.x, y=self.y, z=self.z)
            self.remove()
            return
        if self.mode == "decoy":
            self.anim = "idle"
            return
        if self.target is None or self.target.dead:
            enemies = [e for e in w.enemies_of(self.owner) if e.dist_to(self) < 7.0]
            self.target = min(enemies, key=lambda e: e.dist_to(self)) if enemies else None
        if self.target is not None and not self.struck and self.t > 0.15:
            t = self.target
            ang = t.angle_to(self)
            self.x, self.z = t.x + math.cos(ang) * (t.radius + 0.5), t.z + math.sin(ang) * (t.radius + 0.5)
            self.y = t.y
            self.facing = self.angle_to(t)
            self.anim = "slash_r"
            self.anim_p = 0.5
            base = sum(self.owner.attack_power(None, {}).values()) * self.power
            hit = Hit(self.owner, {"trevas": base}, posture=8, knockback=1.5, stun=0.3, tags=("rune", "shadow"),
                      move_type="rune", hitstop=0.03)
            apply_hit(t, hit)
            w.fx.push("shadow_strike", x=t.x, y=t.y + 1, z=t.z)
            self.struck = True
            self.life = min(self.life, 0.35)
        elif self.struck:
            self.anim_p = min(1.0, (self.anim_p or 0.5) + dt * 2.5)

    def is_decoy(self):
        return self.mode == "decoy" and self.alive
