"""NPCs (personagens com diálogo e serviços) e coletáveis do chão."""
import math

from ..core.data import DB
from .entity import Actor, Entity


class NPC(Actor):
    kind = "npc"
    team = "neutral"
    interactable = True
    interact_radius = 1.5

    def __init__(self, npc_id, x=0.0, z=0.0):
        super().__init__(x, z)
        d = DB.npcs[npc_id]
        self.npc_id = npc_id
        self.d = d
        self.name = d["name"]
        self.sprite = d.get("sprite", npc_id)
        self.facing = math.radians(d.get("angle", -90))
        self.radius = d.get("radius", 0.4)
        self.untargetable = True
        self.invulnerable = True
        self.idle_anim = d.get("anim", "idle")
        self.hidden_unless = d.get("show_if")
        self.prompt = d.get("prompt", f"Falar com {self.name}")
        self.weight = 99.0

    def on_spawn(self):
        g = self.world.level.ground_at(self.x, self.z)
        if g is not None:
            self.y = g

    def can_interact(self, player):
        return True

    def interact(self, player):
        s = self.world.session
        p = player
        self.face(self.angle_to(p))
        if s is not None:
            dlg = self.pick_dialogue(s)
            s.events.append(("dialogue", dlg, self.npc_id))

    def pick_dialogue(self, session):
        for entry in self.d["dialogues"]:
            if session.check(entry.get("if")):
                return entry["id"]
        return self.d["dialogues"][-1]["id"]

    def think(self, dt):
        self.move_x = self.move_z = 0.0
        self.set_anim(self.idle_anim)
        p = self.world.player
        if p is not None and self.dist_to(p) < 3.0:
            self.face(self.angle_to(p), dt * 0.4)


class Pickup(Entity):
    kind = "pickup"
    interactable = True
    interact_radius = 1.0
    prompt = "Pegar"
    sprite = "item_glow"

    def __init__(self, x, z, y=0.0, entry=None, auto=False, pid=None, sprite=None):
        super().__init__(x, z, y)
        self.entry = entry or {}
        self.auto = auto
        self.pid = pid
        self.light = None
        if sprite:
            self.sprite = sprite
        from ..render_bridge import make_light
        self.light = make_light((x, y + 0.6, z), (1.0, 0.85, 0.5), 0.9, 3.0, pulse=0.4, shadows=False)

    def on_spawn(self):
        g = self.world.level.ground_at(self.x, self.z)
        if g is not None:
            self.y = g
        s = self.world.session
        if s is not None and self.pid and s.prop_state(self.world.level.id, self.pid):
            self.alive = False

    def can_interact(self, player):
        return True

    def lights(self):
        return [self.light]

    def update(self, dt):
        super().update(dt)
        self.light.update(dt)
        self.light.pos = [self.x, self.y + 0.6, self.z]
        p = self.world.player
        if self.auto and p is not None and not p.dead and math.hypot(p.x - self.x, p.z - self.z) < 0.8:
            self.interact(p)

    def interact(self, player):
        s = self.world.session
        if s is not None:
            if self.pid:
                s.set_prop_state(self.world.level.id, self.pid, 1)
            self.collect(s)
        self.world.fx.push("pickup", x=self.x, y=self.y, z=self.z, item=self.entry.get("item", "grace"))
        self.remove()

    def collect(self, s):
        s.grant(self.entry, (self.x, self.y, self.z))


class LostGrace(Pickup):
    """Graça perdida na última morte: toque para recuperar."""
    prompt = "Recuperar Graça"
    sprite = "lost_grace"

    def __init__(self, x, z, y, amount):
        super().__init__(x, z, y, {"grace": amount}, auto=True)
        self.amount = amount
        self.light.color = (0.9, 0.75, 0.3)
        self.light.intensity = 1.6

    def collect(self, s):
        s.recover_lost_grace()
