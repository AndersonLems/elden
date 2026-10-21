"""MALACHAR, o Arquiteto das Runas: projéteis e zonas -> clones e distorção do espaço -> arena transformada."""
import math

from .base import Boss


class Malachar(Boss):
    def __init__(self, boss_id, x=0.0, z=0.0, **kw):
        super().__init__(boss_id, x, z, **kw)
        self.material = "ether"
        self.brain.behavior = "summoner"
        self.brain.p["blink"] = True
        self.brain.p["pref"] = 6.0
        self.clone_t = 0.0
        self.well_t = 6.0
        self.rift = False
        self.rift_t = 0.0

    def boss_think(self, dt):
        w = self.world
        p = w.player
        if p is None:
            return
        if self.phase >= 1:
            self.clone_t -= dt
            clones = [e for e in w.enemies() if getattr(e, "enemy_id", "") == "malachar_ilusao"]
            if self.clone_t <= 0 and len(clones) < 2 + self.phase:
                self.clone_t = 9.0
                self.combo_queue.append("malachar_clones")
            self.well_t -= dt
            if self.well_t <= 0:
                self.well_t = 8.0
                x, z = p.x + (w.rng.random() - 0.5) * 4, p.z + (w.rng.random() - 0.5) * 4
                g = w.level.ground_at(x, z)
                if g is not None:
                    w.spawn_zone(self, {"zone": "field", "radius": 2.6, "delay": 0.8, "dur": 3.5, "tick": 0.5,
                                        "dmg": 0.12, "pure": {"arcano": 1.0}, "pull": 3.5, "visual": "gravity_well",
                                        "kb": 0, "stun": 0.0, "no_reaction": True}, x, g, z, 0.0)
        if self.rift:
            self.rift_t -= dt
            if self.rift_t <= 0:
                self.rift_t = 1.0
                cx, cz = self.arena_center
                # o anel externo da arena vira fenda astral (dano contínuo, com aviso visual permanente)
                if p.dist_to_point(cx, cz) > self.safe_radius:
                    w.spawn_zone(self, {"zone": "burst", "radius": 0.8, "dur": 0.1, "dmg": 0.25,
                                        "pure": {"arcano": 1.0}, "visual": "rift_spark", "no_reaction": True},
                                 p.x, p.y, p.z, 0.0)

    def shuffle_with_clones(self):
        w = self.world
        clones = [e for e in w.enemies() if getattr(e, "enemy_id", "") == "malachar_ilusao"]
        if not clones:
            return
        c = w.rng.choice(clones)
        w.fx.push("teleport", x0=self.x, y0=self.y, z0=self.z, x=c.x, y=c.y, z=c.z, actor=self.id)
        self.x, c.x = c.x, self.x
        self.z, c.z = c.z, self.z

    def on_phase(self, n):
        w = self.world
        if n == 2:
            self.rift = True
            self.arena_center = getattr(w, "arena_center", (self.x, self.z))
            self.safe_radius = 6.5
            w.fx.push("arena_rift", x=self.arena_center[0], z=self.arena_center[1], radius=self.safe_radius)
            w.arena_rift = (self.arena_center[0], self.arena_center[1], self.safe_radius)
            w.message("O observatório se desfaz: fique dentro do círculo!", "boss")

    def on_death_rewards(self, world):
        for e in world.enemies():
            if getattr(e, "enemy_id", "") == "malachar_ilusao":
                e.die(None)
        world.arena_rift = None
        super().on_death_rewards(world)
