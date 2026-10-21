"""SERAFIM-09, o Coração da Forja: braços destrutíveis, perigos da arena e sobrecarga do núcleo."""
import math

from .base import Boss, BossPart
from ...combat.actions import StaggerAction


class Serafim(Boss):
    def __init__(self, boss_id, x=0.0, z=0.0, **kw):
        super().__init__(boss_id, x, z, **kw)
        self.material = "metal"
        self.arms = {}
        self.vented = 0.0
        self.hazard_t = 3.0
        self.beam_angle = 0.0

    def on_spawn(self):
        w = self.world
        for side, name in ((-1.6, "braco_esq"), (1.6, "braco_dir")):
            part = BossPart(self, "Braço " + ("Esquerdo" if side < 0 else "Direito"), self.max_hp * 0.16,
                            (side, 0.4), radius=0.8, height=2.2, sprite="serafim_arm", material="metal")
            part.part_id = name
            part.resist = {"fisico": 0.1, "raio": -0.4}
            self.arms[name] = part
            w.spawn(part)

    def arm_alive(self, name):
        p = self.arms.get(name)
        return p is not None and not p.dead

    def armored(self):
        return any(self.arm_alive(n) for n in self.arms) and self.vented <= 0

    def absorb(self, dmg):
        # blindagem do núcleo enquanto houver braços (exceto durante a ventilação)
        return dmg * (0.35 if self.armored() else 1.0)

    def on_part_destroyed(self, part):
        w = self.world
        w.fx.push("explosion", x=part.x, y=part.y + 1, z=part.z, size=2.0)
        w.fx.push("shake", amount=0.7, time=0.6)
        self.attacks = [a for a in self.attacks if a.get("arm") != part.part_id]
        self.set_action(StaggerAction(2.6))
        self.broken = 2.6
        w.message(f"{part.name} destruído! O núcleo está exposto.", "boss")

    def on_move_end(self, action, interrupted):
        if not interrupted and "vent" in action.move.tags:
            self.vented = 3.2
            self.world.fx.push("vent_open", actor=self.id, x=self.x, y=self.y + 2, z=self.z)

    def boss_think(self, dt):
        w = self.world
        if self.vented > 0:
            self.vented -= dt
        # filtra ataques de braços destruídos
        self.attacks = [a for a in self.attacks if not a.get("arm") or self.arm_alive(a["arm"])]
        if self.phase >= 1:
            self.hazard_t -= dt
            if self.hazard_t <= 0:
                self.hazard_t = 3.4 if self.phase == 1 else 2.4
                vents = [p for p in w.props if (getattr(p, "pid", None) or "").startswith("forja_jato")]
                rng = w.rng
                for v in rng.sample(vents, min(len(vents), 2 + self.phase)) if vents else []:
                    w.spawn_zone(self, {"zone": "beam", "length": v.length, "width": 1.2, "delay": 1.0, "dur": 0.9,
                                        "tick": 0.3, "dmg": 0.35, "pure": {"fogo": 1.0}, "kb": 1, "stun": 0.2,
                                        "visual": "flame_jet", "unblockable": True, "status": {"queimadura": 25}},
                                 v.x, v.y, v.z, v.facing)

    def on_phase(self, n):
        w = self.world
        if n == 2:
            w.message("SOBRECARGA DO NÚCLEO", "boss")
            self.vented = 0.0
