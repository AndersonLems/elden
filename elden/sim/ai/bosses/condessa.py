"""A CONDESSA RUBRA (chefe opcional): teletransporte, rapieira e magia de sangue."""
import math

from .base import Boss


class Condessa(Boss):
    def __init__(self, boss_id, x=0.0, z=0.0, **kw):
        super().__init__(boss_id, x, z, **kw)
        self.blink_t = 4.0
        self.material = "flesh"
        self.brain.p["dodge"] = 0.35

    def boss_think(self, dt):
        self.blink_t -= dt
        p = self.world.player
        if p is None or p.dead:
            return
        if self.blink_t <= 0 and self.dist_to(p) > 6.0:
            self.blink_t = 5.0 if self.phase == 0 else 3.5
            self.combo_queue.append("condessa_blink_thrust")

    def on_phase(self, n):
        if n == 1:
            w = self.world
            for i in range(2):
                ang = math.tau * i / 2
                x, z = self.x + math.cos(ang) * 2.5, self.z + math.sin(ang) * 2.5
                if w.level.ground_at(x, z) is not None:
                    w.spawn_enemy("morcego_sanguineo", x, z, summoned=True, aggro=True)
