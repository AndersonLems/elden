"""AURELION, o Deus Despedaçado: forma divina -> forma celestial -> forma fragmentada."""
import math

from .base import Boss, BossPart


class Aurelion(Boss):
    def __init__(self, boss_id, x=0.0, z=0.0, **kw):
        super().__init__(boss_id, x, z, **kw)
        self.material = "ether"
        self.brain.p["parry"] = 0.25
        self.fragments = []
        self.judgement_t = 7.0
        self.orbit = 0.0

    def absorb(self, dmg):
        alive = [f for f in self.fragments if not f.dead]
        return dmg * (0.5 if alive else 1.0)

    def on_phase(self, n):
        w = self.world
        if n == 1:
            self.brain.p["parry"] = 0.1
        if n == 2:
            self.brain.p["parry"] = 0.0
            for i in range(3):
                f = BossPart(self, "Fragmento Divino", self.max_hp * 0.07, (0, 0), radius=0.6, height=1.4,
                             sprite="aurelion_fragment", material="ether")
                f.orbit_i = i
                f.flying = True
                f.part_id = f"frag{i}"
                f.shoot_t = 2.0 + i
                self.fragments.append(f)
                w.spawn(f)
            w.message("O deus se parte em pedaços de luz.", "boss")

    def on_part_destroyed(self, part):
        self.world.fx.push("explosion", x=part.x, y=part.y + 1, z=part.z, size=1.5, color=(1, 0.9, 0.6))
        alive = [f for f in self.fragments if not f.dead]
        if not alive:
            from ...combat.actions import StaggerAction
            self.set_action(StaggerAction(3.0))
            self.broken = 3.0

    def boss_think(self, dt):
        w = self.world
        p = w.player
        self.orbit += dt * 1.2
        for f in self.fragments:
            if f.dead:
                continue
            a = self.orbit + f.orbit_i * math.tau / 3
            f.offset = (math.cos(a) * 3.0, math.sin(a) * 3.0)
            f.shoot_t -= dt
            if f.shoot_t <= 0 and p is not None and not p.dead:
                f.shoot_t = 3.5
                f.face(f.angle_to(p))
                f.target = p
                f.atk = dict(self.atk)
                w.spawn_projectiles(f, {"proj": "luz", "speed": 11, "dmg": 0.35, "radius": 0.3, "visual": "holy_bolt",
                                        "pure": {"sagrado": 1.0}, "range": 16, "light": [1.0, 0.9, 0.6, 1.5],
                                        "reflectable": True, "offset": [0.3, 1.0]})
        if self.phase >= 1 and p is not None:
            self.judgement_t -= dt
            if self.judgement_t <= 0:
                self.judgement_t = 7.5 if self.phase == 1 else 5.5
                for k in range(5 + self.phase * 2):
                    x = p.x + (w.rng.random() - 0.5) * 9
                    z = p.z + (w.rng.random() - 0.5) * 9
                    g = w.level.ground_at(x, z)
                    if g is None:
                        continue
                    w.spawn_zone(self, {"zone": "pillar", "radius": 1.2, "delay": 1.2 + k * 0.08, "dur": 0.4,
                                        "dmg": 0.45, "pure": {"sagrado": 1.0}, "kb": 2, "posture": 15,
                                        "visual": "light_pillar", "unblockable": True}, x, g, z, 0.0)
