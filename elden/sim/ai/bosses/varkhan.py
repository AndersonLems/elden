"""VARKHAN, o Primeiro Licano: humanoide bestial -> transformação completa -> frenesi lunar."""
import math

from .base import Boss


class Varkhan(Boss):
    def __init__(self, boss_id, x=0.0, z=0.0, **kw):
        super().__init__(boss_id, x, z, **kw)
        self.debris_t = 0.0
        self.howled = False
        self.material = "flesh"

    def on_phase(self, n):
        w = self.world
        if n == 1:
            # transformação: invoca a matilha uma vez
            if not self.howled:
                self.howled = True
                for i in range(2):
                    ang = self.facing + math.pi * (0.5 + i)
                    x, z = self.x + math.cos(ang) * 3, self.z + math.sin(ang) * 3
                    if w.level.ground_at(x, z) is not None:
                        w.spawn_enemy("lobo_corrompido", x, z, summoned=True, aggro=True)
        if n == 2:
            # frenesi: os pilares da arena desabam
            for p in list(w.props):
                if getattr(p, "pid", "") and p.pid.startswith("arena_pilar"):
                    p.shatter()
            w.night_red = True

    def boss_think(self, dt):
        if self.phase < 2:
            return
        self.debris_t -= dt
        if self.debris_t <= 0:
            self.debris_t = 2.6
            w = self.world
            p = w.player
            if p is None:
                return
            # pedaços do teto caem em volta do jogador (com aviso)
            for k in range(3):
                ang = w.rng.random() * math.tau
                r = 1.0 + w.rng.random() * 3.5
                x, z = p.x + math.cos(ang) * r, p.z + math.sin(ang) * r
                if w.level.ground_at(x, z) is None:
                    continue
                w.spawn_zone(self, {"zone": "burst", "radius": 1.3, "delay": 1.1 + k * 0.15, "dur": 0.15, "dmg": 0.7,
                                    "kb": 3, "posture": 15, "stun": 0.5, "visual": "debris", "unblockable": True},
                             x, w.level.ground_at(x, z), z, 0.0)
