"""O SANTO IMPERFEITO: espadachim técnico -> mutação com membros extras -> híbrido de carne e Graça."""
import math

from .base import Boss


class Santo(Boss):
    def __init__(self, boss_id, x=0.0, z=0.0, **kw):
        super().__init__(boss_id, x, z, **kw)
        self.brain.p["parry"] = 0.3
        self.brain.p["block"] = 0.2
        self.tendril_t = 4.0
        self.material = "flesh"

    def on_phase(self, n):
        if n == 1:
            self.brain.p["parry"] = 0.15
            self.extra_arms = True
        if n == 2:
            self.brain.p["parry"] = 0.0
            self.brain.p["block"] = 0.0
            self.world.message("A Graça consome o que restava do homem.", "boss")

    def boss_think(self, dt):
        if self.phase < 1:
            return
        self.tendril_t -= dt
        if self.tendril_t <= 0:
            w = self.world
            p = w.player
            if p is None:
                return
            self.tendril_t = 4.5 if self.phase == 1 else 3.0
            for k in range(2 + self.phase):
                x = p.x + (w.rng.random() - 0.5) * 3.0
                z = p.z + (w.rng.random() - 0.5) * 3.0
                g = w.level.ground_at(x, z)
                if g is None:
                    continue
                w.spawn_zone(self, {"zone": "pillar", "radius": 0.9, "delay": 0.9 + k * 0.2, "dur": 0.35, "dmg": 0.6,
                                    "launch": 6, "posture": 12, "visual": "tendril", "pure": {"sangue": 0.5, "fisico": 0.5}},
                             x, g, z, 0.0)
