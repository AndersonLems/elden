"""Objetos do cenário: interativos, sinalizadores, perigos, plataformas e quebráveis.

Sinais: objetos como alavancas e placas enviam 'activate'/'deactivate' para outros objetos (targets),
como portas. O estado de cada objeto com 'pid' é salvo por fase (session.prop_state).
"""
import math

from ...core.data import DB
from ...core.mathutil import dir_of, angle_of
from ..entity import Entity
from ..combat.damage import Hit, apply_hit


class Prop(Entity):
    kind = "prop"
    is_prop = True
    interactable = False
    interact_radius = 1.2
    prompt = "Interagir"
    sprite = "crate"
    can_block = False
    is_platform = False
    team = "neutral"

    def __init__(self, spec):
        super().__init__(spec.get("x", 0.0), spec.get("z", 0.0), spec.get("y", 0.0))
        self.spec = spec
        self.pid = spec.get("id")
        self.targets = spec.get("targets", [])
        self.sprite = spec.get("sprite", self.sprite)
        self.facing = math.radians(spec.get("angle", -90))
        self.light = None
        self.state = spec.get("state", 0)
        self.half = spec.get("half", (0.5, 0.5))     # meia-extensão (x, z) do bloqueio
        self.top = spec.get("top", 2.0)

    def on_spawn(self):
        g = self.world.level.ground_at(self.x, self.z)
        if g is not None and "y" not in self.spec:
            self.y = g
        s = self.session
        if s is not None and self.pid:
            saved = s.prop_state(self.world.level.id, self.pid)
            if saved is not None:
                self.restore(saved)

    @property
    def session(self):
        return self.world.session if self.world is not None else None

    def save_state(self, value):
        self.state = value
        s = self.session
        if s is not None and self.pid:
            s.set_prop_state(self.world.level.id, self.pid, value)

    def restore(self, value):
        self.state = value

    def send(self, signal, targets=None):
        for pid in (targets if targets is not None else self.targets):
            p = self.world.find_prop(pid)
            if p is not None:
                p.on_signal(signal, self)
        self.world.bus.emit("prop_changed", prop=self)

    def on_signal(self, signal, sender):
        pass

    def can_interact(self, player):
        return self.interactable

    def interact(self, player):
        pass

    def receive_hit(self, hit):
        hit.result = "immune"

    # colisão de objetos sólidos (caixa alinhada aos eixos)
    def push_circle(self, x, z, r, y):
        if y >= self.y + self.top - 0.05:
            return x, z
        hx, hz = self.half
        px = min(max(x, self.x - hx), self.x + hx)
        pz = min(max(z, self.z - hz), self.z + hz)
        dx, dz = x - px, z - pz
        d2 = dx * dx + dz * dz
        if d2 >= r * r:
            return x, z
        if d2 > 1e-10:
            d = math.sqrt(d2)
            return x + dx / d * (r - d), z + dz / d * (r - d)
        opts = ((x - (self.x - hx), -1, 0), ((self.x + hx) - x, 1, 0), (z - (self.z - hz), 0, -1), ((self.z + hz) - z, 0, 1))
        dmin, sx, sz = min(opts, key=lambda o: o[0])
        return x + sx * (dmin + r), z + sz * (dmin + r)

    def contains_point(self, x, y, z):
        hx, hz = self.half
        return abs(x - self.x) <= hx and abs(z - self.z) <= hz and self.y <= y <= self.y + self.top

    def lights(self):
        return [self.light] if self.light is not None else []


# --------------------------------------------------------------------------- Graça (ponto de descanso)
class Grace(Prop):
    """Graça: checkpoint. Descansar restaura tudo, permite evoluir, trocar runas/armas e viajar."""
    interactable = True
    prompt = "Descansar na Graça"
    sprite = "grace"

    def __init__(self, spec):
        super().__init__(spec)
        self.name = spec.get("name", "Graça")
        self.discovered = False

    def on_spawn(self):
        super().on_spawn()
        s = self.session
        self.discovered = s is not None and s.grace_discovered(self.pid)

    def update(self, dt):
        super().update(dt)
        p = self.world.player
        if not self.discovered and p is not None and self.dist_to(p) < 3.0:
            self.discovered = True
            if self.session is not None:
                self.session.discover_grace(self.pid, self.name, self.world.level.id)
            self.world.fx.push("grace_found", x=self.x, y=self.y, z=self.z, name=self.name)

    def interact(self, player):
        if self.session is not None:
            self.session.request_rest(self, player)
        else:
            player.refill()


# --------------------------------------------------------------------------- portas
class Door(Prop):
    """Portão/porta: aberto por sinais, chave ou evento. Fechado bloqueia passagem e projéteis."""
    sprite = "gate"
    can_block = True
    prompt = "Abrir"

    def __init__(self, spec):
        super().__init__(spec)
        self.need_signals = spec.get("need", 1)
        self.key = spec.get("key")                # item necessário
        self.open_flag = spec.get("open_flag")    # abre quando a flag existe (ex.: chefe derrotado)
        self.close_on = spec.get("close_on")      # evento que fecha (ex.: boss_start)
        self.open_on = spec.get("open_on")        # evento que abre (ex.: boss_defeated)
        self.signals = set()
        self.open = bool(spec.get("open", False))
        self.anim_open = 1.0 if self.open else 0.0
        self.interactable = self.key is not None or spec.get("manual", False)
        self.half = spec.get("half", (0.5, 0.5))
        self.top = spec.get("top", 3.0)
        self.message = spec.get("message")

    @property
    def solid(self):
        return not self.open

    def on_spawn(self):
        super().on_spawn()
        s = self.session
        if self.open_flag and s is not None and s.has_flag(self.open_flag):
            self.set_open(True, silent=True)
        if self.close_on:
            self.world.bus.on(self.close_on, lambda **k: self.set_open(False))
        if self.open_on:
            self.world.bus.on(self.open_on, lambda **k: self.set_open(True))

    def restore(self, value):
        self.state = value
        self.open = bool(value)
        self.anim_open = 1.0 if self.open else 0.0

    def set_open(self, value, silent=False):
        if value == self.open:
            return
        self.open = value
        if self.pid and not self.spec.get("transient"):
            self.save_state(1 if value else 0)
        if not silent and self.world:
            self.world.fx.push("door", prop=self.id, open=value, x=self.x, y=self.y, z=self.z)
            if value and self.message:
                self.world.message(self.message)

    def on_signal(self, signal, sender):
        if signal == "activate":
            self.signals.add(sender.id)
        elif signal == "deactivate":
            self.signals.discard(sender.id)
        elif signal == "open":
            self.set_open(True)
            return
        elif signal == "close":
            self.set_open(False)
            return
        if self.spec.get("toggle_with_signal", True) and self.key is None:
            self.set_open(len(self.signals) >= self.need_signals)

    def can_interact(self, player):
        return not self.open and self.interactable

    def interact(self, player):
        s = self.session
        if self.key:
            if s is not None and s.char.has_item(self.key):
                if self.spec.get("consume_key", True):
                    s.char.take_item(self.key)
                self.set_open(True)
                self.world.message(f"Usou: {DB.items[self.key]['name']}")
            else:
                name = DB.items[self.key]["name"] if self.key in DB.items else self.key
                self.world.message(f"Trancada. Requer: {name}", "warn")
        elif self.spec.get("manual"):
            self.set_open(True)

    def update(self, dt):
        super().update(dt)
        target = 1.0 if self.open else 0.0
        self.anim_open += (target - self.anim_open) * min(1.0, dt * 4)


# --------------------------------------------------------------------------- alavancas, placas, mostradores
class Lever(Prop):
    interactable = True
    prompt = "Puxar alavanca"
    sprite = "lever"

    def __init__(self, spec):
        super().__init__(spec)
        self.one_shot = spec.get("one_shot", False)

    def can_interact(self, player):
        return not (self.one_shot and self.state)

    def interact(self, player):
        self.save_state(0 if self.state else 1)
        self.world.fx.push("lever", prop=self.id, state=self.state, x=self.x, y=self.y, z=self.z)
        self.send("activate" if self.state else "deactivate")

    def restore(self, value):
        self.state = value

    def on_spawn(self):
        super().on_spawn()
        if self.state:
            self.send("activate")


class PressurePlate(Prop):
    sprite = "plate"

    def __init__(self, spec):
        super().__init__(spec)
        self.latch = spec.get("latch", False)
        self.pressed = False

    def update(self, dt):
        super().update(dt)
        w = self.world
        on = False
        for a in w.actors:
            if a.alive and not a.dead and abs(a.x - self.x) < 0.55 and abs(a.z - self.z) < 0.55 and abs(a.y - self.y) < 0.4:
                on = True
                break
        if not on:
            for p in w.props:
                if getattr(p, "heavy_object", False) and abs(p.x - self.x) < 0.5 and abs(p.z - self.z) < 0.5:
                    on = True
                    break
        if self.latch and self.state:
            on = True
        if on != self.pressed:
            self.pressed = on
            if on and self.latch:
                self.save_state(1)
            w.fx.push("plate", prop=self.id, on=on, x=self.x, y=self.y, z=self.z)
            self.send("activate" if on else "deactivate")

    def restore(self, value):
        self.state = value


class SymbolDial(Prop):
    """Mostrador giratório com símbolos (lunar, religioso, rúnico). Cada interação avança um símbolo."""
    interactable = True
    prompt = "Girar símbolo"
    sprite = "dial"

    def __init__(self, spec):
        super().__init__(spec)
        self.symbols = spec.get("symbols", ["lua_nova", "crescente", "cheia", "minguante"])
        self.prompt = spec.get("prompt", self.prompt)
        self.locked = False

    def can_interact(self, player):
        return not self.locked

    def interact(self, player):
        self.save_state((self.state + 1) % len(self.symbols))
        self.world.fx.push("dial", prop=self.id, state=self.state, x=self.x, y=self.y, z=self.z)
        self.send("changed")

    @property
    def symbol(self):
        return self.symbols[self.state % len(self.symbols)]


class SequenceButton(Prop):
    """Botão de sequência (puzzles de ordem: sinos, símbolos religiosos, frascos alquímicos)."""
    interactable = True
    prompt = "Ativar"
    sprite = "button"

    def __init__(self, spec):
        super().__init__(spec)
        self.symbol = spec.get("symbol", "?")
        self.prompt = spec.get("prompt", "Ativar")
        self.lit = 0.0

    def interact(self, player):
        self.lit = 1.0
        self.world.fx.push("seq_press", prop=self.id, x=self.x, y=self.y, z=self.z, symbol=self.symbol)
        self.world.bus.emit("sequence_input", prop=self)

    def update(self, dt):
        super().update(dt)
        self.lit = max(0.0, self.lit - dt)


# --------------------------------------------------------------------------- luz: cristais, espelhos, feixes
class Crystal(Prop):
    """Cristal: aceso por golpe/magia ou por feixe de luz. Aceso, ativa os alvos."""
    hittable = True
    sprite = "crystal"
    radius = 0.4
    height = 1.4

    def __init__(self, spec):
        super().__init__(spec)
        self.receiver = spec.get("receiver", False)    # acende só com feixe de luz
        self.color = tuple(spec.get("color", (0.5, 0.8, 1.0)))
        self.beam_lit = False
        self.hold = spec.get("hold", 0.0)              # tempo aceso após golpe (0 = permanente)
        self.timer = 0.0
        from ...render_bridge import make_light
        self.light = make_light((self.x, self.y + 1.0, self.z), self.color, 0.0, 5.0)

    def receive_hit(self, hit):
        hit.result = "hit"
        if self.receiver:
            self.world.fx.push("spark", x=self.x, y=self.y + 1, z=self.z, material="crystal")
            return
        self.activate_crystal()

    def activate_crystal(self):
        if self.hold > 0:
            self.timer = self.hold
        if not self.state:
            self.save_state(1)
            self.world.fx.push("crystal", prop=self.id, on=True, x=self.x, y=self.y, z=self.z)
            self.send("activate")

    def update(self, dt):
        super().update(dt)
        if self.receiver:
            if self.beam_lit and not self.state:
                self.state = 1
                self.world.fx.push("crystal", prop=self.id, on=True, x=self.x, y=self.y, z=self.z)
                self.send("activate")
            elif not self.beam_lit and self.state and not self.spec.get("latch"):
                self.state = 0
                self.send("deactivate")
            self.beam_lit = False
        elif self.hold > 0 and self.state:
            self.timer -= dt
            if self.timer <= 0:
                self.state = 0
                self.send("deactivate")
        if self.light is not None:
            self.light.intensity = 1.8 if self.state else 0.25
        if self.light is not None:
            self.light.pos = [self.x, self.y + 1.0, self.z]

    def restore(self, value):
        if not self.receiver and not self.hold:
            self.state = value


class Mirror(Prop):
    """Espelho giratório (90° por interação): reflete feixes de luz."""
    interactable = True
    prompt = "Girar espelho"
    sprite = "mirror"
    can_block = True

    def __init__(self, spec):
        super().__init__(spec)
        self.half = (0.35, 0.35)
        self.top = 1.6
        self.locked = spec.get("locked", False)

    def can_interact(self, player):
        return not self.locked

    def interact(self, player):
        self.save_state((self.state + 1) % 4)
        self.world.fx.push("mirror", prop=self.id, state=self.state, x=self.x, y=self.y, z=self.z)

    @property
    def solid(self):
        return True

    def reflect(self, dx, dz):
        """Orientações 0..3: '/', '\\', '/', '\\' com faces espelhadas (estado par = '/', ímpar = '\\')."""
        if self.state % 2 == 0:      # '/'
            return dz, dx
        return -dz, -dx              # '\'


class LightEmitter(Prop):
    """Fonte de feixe de luz (vitral, lua, lente). Propaga em linha reta pela grade."""
    sprite = "emitter"

    def __init__(self, spec):
        super().__init__(spec)
        d = spec.get("dir", "N")
        self.dir = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}[d]
        self.active = spec.get("active", True)
        self.beam = []        # segmentos (x0, z0, x1, z1) para desenhar
        self.color = tuple(spec.get("color", (1.0, 0.9, 0.6)))

    def on_signal(self, signal, sender):
        if signal == "activate":
            self.active = True
        elif signal == "deactivate":
            self.active = False

    def update(self, dt):
        super().update(dt)
        self.beam = []
        if not self.active:
            return
        w = self.world
        x, z = math.floor(self.x) + 0.5, math.floor(self.z) + 0.5
        dx, dz = self.dir
        sx, sz = x, z
        mirrors = {(int(math.floor(p.x)), int(math.floor(p.z))): p for p in w.props if isinstance(p, Mirror)}
        receivers = {(int(math.floor(p.x)), int(math.floor(p.z))): p for p in w.props
                     if isinstance(p, Crystal) and p.receiver}
        visited = set()
        for _ in range(80):
            x += dx
            z += dz
            cx, cz = int(math.floor(x)), int(math.floor(z))
            key = (cx, cz, dx, dz)
            if key in visited:
                break
            visited.add(key)
            if (cx, cz) in receivers:
                receivers[(cx, cz)].beam_lit = True
                self.beam.append((sx, sz, x, z))
                return
            if (cx, cz) in mirrors:
                self.beam.append((sx, sz, x, z))
                dx, dz = mirrors[(cx, cz)].reflect(dx, dz)
                sx, sz = x, z
                continue
            c = w.level.cell(cx, cz)
            blocked = c is None or (not c.void and (c.solid or c.height > self.y + 1.2))
            if not blocked:
                for s in w.solids:
                    if s is not self and s.solid and not isinstance(s, Mirror) and s.contains_point(x, self.y + 1.0, z):
                        blocked = True
                        break
            if blocked:
                self.beam.append((sx, sz, x - dx * 0.5, z - dz * 0.5))
                return
            # o jogador pode bloquear o feixe com o corpo
            p = w.player
            if p is not None and abs(p.x - x) < 0.45 and abs(p.z - z) < 0.45:
                self.beam.append((sx, sz, p.x, p.z))
                return
        self.beam.append((sx, sz, x, z))


# --------------------------------------------------------------------------- forja: engrenagens, válvulas, energia
class Valve(Prop):
    """Válvula com N posições: direciona vapor/energia. Lida pelos controladores de puzzle."""
    interactable = True
    prompt = "Girar válvula"
    sprite = "valve"

    def __init__(self, spec):
        super().__init__(spec)
        self.positions = spec.get("positions", 2)

    def interact(self, player):
        self.save_state((self.state + 1) % self.positions)
        self.world.fx.push("valve", prop=self.id, state=self.state, x=self.x, y=self.y, z=self.z)
        self.send("changed")


class GearSocket(Prop):
    """Encaixe de engrenagem: precisa de uma engrenagem carregada pelo jogador; depois gira para alinhar."""
    interactable = True
    sprite = "gear_socket"

    def __init__(self, spec):
        super().__init__(spec)
        self.has_gear = bool(spec.get("has_gear", False))
        self.teeth = spec.get("positions", 4)
        self.rotation = 0

    @property
    def prompt(self):
        return "Girar engrenagem" if self.has_gear else "Encaixar engrenagem"

    def restore(self, value):
        self.state = value
        if isinstance(value, dict):
            self.has_gear = value.get("gear", False)
            self.rotation = value.get("rot", 0)

    def interact(self, player):
        if not self.has_gear:
            s = self.session
            has = s.char.has_item("engrenagem") if s is not None else getattr(player, "carrying", None) == "engrenagem"
            if has:
                if s is not None:
                    s.char.take_item("engrenagem")
                player.carrying = None
                self.has_gear = True
                self.world.fx.push("gear_place", prop=self.id, x=self.x, y=self.y, z=self.z)
            else:
                self.world.message("Falta uma engrenagem aqui.", "warn")
                return
        else:
            self.rotation = (self.rotation + 1) % self.teeth
            self.world.fx.push("gear_turn", prop=self.id, x=self.x, y=self.y, z=self.z)
        self.save_state({"gear": self.has_gear, "rot": self.rotation})
        self.send("changed")


class GearPickup(Prop):
    """Engrenagem solta que o jogador pode carregar até um encaixe."""
    interactable = True
    prompt = "Pegar engrenagem"
    sprite = "gear"

    def can_interact(self, player):
        return not self.state

    def interact(self, player):
        player.carrying = "engrenagem"
        if self.session is not None:
            self.session.char.add_item("engrenagem")
            self.session.notify("Pegou uma engrenagem.", "item")
        self.save_state(1)
        self.visible = False
        self.world.fx.push("pickup", x=self.x, y=self.y, z=self.z, item="engrenagem")

    def restore(self, value):
        self.state = value
        if value:
            self.visible = False
            self.interactable = False


class PowerNode(Prop):
    """Nó de energia: chave liga/desliga conexões de uma rede (distribuição de energia)."""
    interactable = True
    prompt = "Alternar conexão"
    sprite = "power_node"

    def __init__(self, spec):
        super().__init__(spec)
        self.powered = False

    def interact(self, player):
        self.save_state(0 if self.state else 1)
        self.world.fx.push("switch", prop=self.id, state=self.state, x=self.x, y=self.y, z=self.z)
        self.send("changed")


class MovingPlatform(Prop):
    """Plataforma móvel (trilhos, elevadores): percorre pontos; pode depender de energia/sinal."""
    is_platform = True
    sprite = "platform"

    def __init__(self, spec):
        super().__init__(spec)
        self.points = [tuple(p) for p in spec.get("points", [(self.x, self.y, self.z)])]
        self.speed = spec.get("speed", 2.0)
        self.wait = spec.get("wait", 1.0)
        self.half = tuple(spec.get("half", (1.0, 1.0)))
        self.active = spec.get("active", True)
        self.seg = 0
        self.wait_t = 0.0
        self.dir = 1
        self.thick = spec.get("thick", 0.5)
        self.x, self.y, self.z = self.points[0]

    def on_spawn(self):
        s = self.session
        if s is not None and self.pid:
            saved = s.prop_state(self.world.level.id, self.pid)
            if saved is not None:
                self.active = bool(saved)

    def on_signal(self, signal, sender):
        if signal in ("activate", "deactivate"):
            self.active = signal == "activate"
            self.save_state(1 if self.active else 0)

    def top_at(self, x, z, margin=0.0):
        hx, hz = self.half
        if abs(x - self.x) <= hx + margin and abs(z - self.z) <= hz + margin:
            return self.y
        return None

    def update(self, dt):
        super().update(dt)
        self.vx = self.vz = 0.0
        if not self.active or len(self.points) < 2:
            return
        if self.wait_t > 0:
            self.wait_t -= dt
            return
        nxt = self.seg + self.dir
        if nxt >= len(self.points) or nxt < 0:
            self.dir = -self.dir
            nxt = self.seg + self.dir
        tx, ty, tz = self.points[nxt]
        dx, dy, dz = tx - self.x, ty - self.y, tz - self.z
        d = math.sqrt(dx * dx + dy * dy + dz * dz)
        step = self.speed * dt
        if d <= step:
            self.vx, self.vz = dx / dt if dt > 0 else 0, dz / dt if dt > 0 else 0
            self.x, self.y, self.z = tx, ty, tz
            self.seg = nxt
            self.wait_t = self.wait
            dyp = dy
        else:
            self.vx, self.vz = dx / d * self.speed, dz / d * self.speed
            self.x += dx / d * step
            self.y += dy / d * step
            self.z += dz / d * step
            dyp = dy / d * step
        # quem está em cima acompanha a altura
        for a in self.world.actors:
            if getattr(a, "standing_on", None) is self and a.grounded:
                a.y = self.y


# --------------------------------------------------------------------------- portais e saídas
class Portal(Prop):
    """Portal conectado a outro portal da mesma fase (pares) — some temporariamente após o uso."""
    interactable = True
    prompt = "Atravessar portal"
    sprite = "portal"

    def __init__(self, spec):
        super().__init__(spec)
        self.link = spec.get("link")
        self.active = spec.get("active", True)
        self.color = tuple(spec.get("color", (0.6, 0.4, 1.0)))
        from ...render_bridge import make_light
        self.light = make_light((self.x, self.y + 1.2, self.z), self.color, 1.6, 5.0)

    def can_interact(self, player):
        return self.active and self.link is not None

    def on_signal(self, signal, sender):
        if signal == "activate":
            self.active = True
        elif signal == "deactivate":
            self.active = False

    def interact(self, player):
        other = self.world.find_prop(self.link)
        if other is None:
            return
        self.world.fx.push("teleport", x0=player.x, y0=player.y, z0=player.z, x=other.x, y=other.y, z=other.z - 0.9,
                           actor=player.id)
        player.x, player.y, player.z = other.x, other.y, other.z - 0.9
        player.set_action(None)
        player.iframes = 0.5

    def update(self, dt):
        super().update(dt)
        self.light.intensity = 1.6 if self.active else 0.0


class Exit(Prop):
    """Passagem para outra fase (ou outra região)."""
    interactable = True
    sprite = "exit"
    interact_radius = 1.4

    def __init__(self, spec):
        super().__init__(spec)
        self.to = spec["to"]
        self.spawn = spec.get("spawn", "start")
        self.require_flag = spec.get("require_flag")
        self.auto = spec.get("auto", True)
        self.label = spec.get("label", "Seguir")
        self.cool = 1.0

    @property
    def prompt(self):
        return self.label

    def available(self):
        s = self.session
        return self.require_flag is None or (s is not None and s.has_flag(self.require_flag))

    def update(self, dt):
        super().update(dt)
        if self.cool > 0:
            self.cool -= dt
            return
        p = self.world.player
        if self.auto and p is not None and not p.dead and abs(p.x - self.x) < 0.7 and abs(p.z - self.z) < 0.7:
            self.use(p)

    def can_interact(self, player):
        return not self.auto

    def interact(self, player):
        self.use(player)

    def use(self, player):
        if self.to not in DB.levels:
            if self.cool <= 0:
                self.world.message("Esta região ainda está em construção.", "warn")
                self.cool = 2.0
            return
        if not self.available():
            if self.cool <= 0:
                self.world.message(self.spec.get("locked_text", "O caminho está bloqueado."), "warn")
                self.cool = 2.0
            return
        self.cool = 3.0
        if self.session is not None:
            self.session.request_travel(self.to, self.spawn)


class SpawnPoint(Prop):
    sprite = None


# --------------------------------------------------------------------------- recompensas e leitura
class Chest(Prop):
    interactable = True
    prompt = "Abrir baú"
    sprite = "chest"
    can_block = True

    def __init__(self, spec):
        super().__init__(spec)
        self.loot = spec.get("loot", [])
        self.half = (0.4, 0.3)
        self.top = 0.9

    @property
    def solid(self):
        return True

    def can_interact(self, player):
        return not self.state

    def interact(self, player):
        self.save_state(1)
        self.world.fx.push("chest", prop=self.id, x=self.x, y=self.y, z=self.z)
        s = self.session
        if s is not None:
            for entry in self.loot:
                s.grant(entry, (self.x, self.y, self.z))


class Document(Prop):
    """Fragmento de história (carta, diário, inscrição)."""
    interactable = True
    prompt = "Ler"
    sprite = "note"

    def __init__(self, spec):
        super().__init__(spec)
        self.doc = spec["doc"]

    def interact(self, player):
        s = self.session
        if s is not None:
            s.read_document(self.doc)


class Altar(Prop):
    """Altar de escolha (purificar/absorver), oração ou oferenda."""
    interactable = True
    sprite = "altar"

    def __init__(self, spec):
        super().__init__(spec)
        self.altar_kind = spec.get("altar", "oracao")
        self.prompt = spec.get("prompt", "Rezar no altar")

    def can_interact(self, player):
        return not (self.state and self.spec.get("once", True))

    def interact(self, player):
        s = self.session
        if s is not None:
            s.use_altar(self, player)


class Breakable(Prop):
    """Barris, caixas, urnas e caixões: quebram com golpes e podem soltar Graça ou itens."""
    hittable = True
    sprite = "barrel"
    can_block = True
    radius = 0.4
    height = 1.0

    def __init__(self, spec):
        super().__init__(spec)
        self.hp = spec.get("hp", 1)
        self.half = (0.35, 0.35)
        self.top = 1.0
        self.drop = spec.get("drop")

    @property
    def solid(self):
        return self.alive

    def receive_hit(self, hit):
        hit.result = "hit"
        self.hp -= 1
        self.world.fx.push("break_hit", x=self.x, y=self.y + 0.5, z=self.z, material=self.spec.get("material", "wood"))
        if self.hp <= 0:
            self.world.fx.push("break", x=self.x, y=self.y + 0.5, z=self.z, sprite=self.sprite,
                               material=self.spec.get("material", "wood"))
            s = self.session
            if s is not None:
                s.on_break(self)
                if self.pid:
                    self.save_state(1)
            self.remove()

    def restore(self, value):
        if value:
            self.alive = False


class BreakableWall(Breakable):
    """Parede falsa (passagem secreta): quebra com golpes pesados."""
    sprite = "cracked_wall"

    def __init__(self, spec):
        super().__init__(spec)
        self.hp = spec.get("hp", 3)
        self.half = (0.5, 0.5)
        self.top = 3.0

    def receive_hit(self, hit):
        if not hit.heavy and hit.move_type not in ("skill", "art", "charged"):
            hit.result = "blocked"
            self.world.fx.push("spark", x=self.x, y=self.y + 1, z=self.z, material="stone")
            if self.world:
                self.world.message("A parede parece frágil... um golpe pesado talvez a derrube.", "hint")
            return
        super().receive_hit(hit)
        if not self.alive and self.session is not None:
            self.session.found_secret(self.pid)


class ArenaPillar(Breakable):
    sprite = "pillar"

    def __init__(self, spec):
        super().__init__(spec)
        self.hp = 999
        self.hittable = False
        self.top = 3.5

    def receive_hit(self, hit):
        hit.result = "immune"

    def shatter(self):
        self.world.fx.push("break", x=self.x, y=self.y + 1.5, z=self.z, sprite="pillar", material="stone", big=True)
        self.world.spawn_zone(None, {"zone": "burst", "radius": 1.8, "dur": 0.15, "base": 25, "kb": 5, "stun": 0.5,
                                     "visual": "debris"}, self.x, self.y, self.z, 0.0, team="enemy")
        self.remove()


# --------------------------------------------------------------------------- perigos
class Hazard(Prop):
    """Espinhos, jatos de vapor, serras, chamas: dano periódico com aviso. Podem ser desligados por sinal."""
    sprite = "spikes"

    def __init__(self, spec):
        super().__init__(spec)
        self.hz_kind = spec.get("hazard", "spikes")
        self.period = spec.get("period", 2.4)
        self.on_time = spec.get("on_time", 0.8)
        self.warn = spec.get("warn", 0.6)
        self.offset = spec.get("offset", 0.0)
        self.active = spec.get("active", True)
        self.radius_hz = spec.get("radius", 0.6)
        self.dmg = spec.get("dmg", 0.12)
        self.element = spec.get("element", "fisico")
        self.length = spec.get("length", 0.0)
        self.points = [tuple(p) for p in spec.get("points", [])]
        self.speed = spec.get("speed", 2.0)
        self.hit_cd = {}
        self.phase = "off"
        self.seg = 0

    def on_signal(self, signal, sender):
        if signal == "activate":
            self.active = not self.spec.get("signal_disables", True)
        elif signal == "deactivate":
            self.active = self.spec.get("signal_disables", True)
        elif signal == "changed":
            pass

    def cycle_phase(self):
        if not self.active:
            return "off"
        if self.period <= 0:
            return "on"
        t = (self.t + self.offset) % self.period
        if t < self.warn:
            return "warn"
        if t < self.warn + self.on_time:
            return "on"
        return "off"

    def update(self, dt):
        super().update(dt)
        # serras se movem entre pontos
        if self.hz_kind == "saw" and len(self.points) >= 2 and self.active:
            tx, tz = self.points[(self.seg + 1) % len(self.points)]
            dx, dz = tx - self.x, tz - self.z
            d = math.hypot(dx, dz)
            if d < self.speed * dt:
                self.seg = (self.seg + 1) % len(self.points)
            else:
                self.x += dx / d * self.speed * dt
                self.z += dz / d * self.speed * dt
        self.phase = self.cycle_phase()
        for k in list(self.hit_cd):
            self.hit_cd[k] -= dt
            if self.hit_cd[k] <= 0:
                del self.hit_cd[k]
        if self.phase != "on":
            return
        w = self.world
        for a in w.actors:
            if a.dead or not a.alive or a.id in self.hit_cd or getattr(a, "flying", False):
                continue
            if not self._touches(a):
                continue
            self.hit_cd[a.id] = 0.6
            amount = a.max_hp * self.dmg + 4
            hit = Hit(None, {self.element: amount}, posture=10, knockback=3.0, stun=0.3, can_crit=False,
                      pos=(self.x, self.y, self.z), move_type="hazard",
                      status={"queimadura": 30} if self.element == "fogo" else {})
            apply_hit(a, hit)

    def _touches(self, a):
        if abs(a.y - self.y) > 1.2:
            return False
        if self.length > 0:
            fx, fz = dir_of(self.facing)
            dx, dz = a.x - self.x, a.z - self.z
            along = dx * fx + dz * fz
            across = abs(-dx * fz + dz * fx)
            return 0 <= along <= self.length and across <= 0.6 + a.radius
        return math.hypot(a.x - self.x, a.z - self.z) <= self.radius_hz + a.radius


class Decor(Prop):
    """Decoração (árvores, lápides, estátuas, engrenagens, livros): só visual, opcionalmente sólida."""
    sprite = "tree"

    def __init__(self, spec):
        super().__init__(spec)
        self.blocks = spec.get("solid", False)
        self.half = tuple(spec.get("half", (0.3, 0.3)))
        self.top = spec.get("top", 2.0)
        self.can_block = self.blocks
        self.light_spec = spec.get("light")
        if self.light_spec:
            from ...render_bridge import make_light
            ls = self.light_spec
            self.light = make_light((self.x + ls.get("dx", 0), self.y + ls.get("h", 1.5), self.z + ls.get("dz", 0)),
                                    tuple(ls.get("color", (1.0, 0.6, 0.3))), ls.get("intensity", 1.8),
                                    ls.get("radius", 6.0), flicker=ls.get("flicker", 0.2), shadows=ls.get("shadows", True))

    @property
    def solid(self):
        return self.blocks

    def on_spawn(self):
        g = self.world.level.ground_at(self.x, self.z)
        if g is not None and "y" not in self.spec:
            self.y = g
        if self.light is not None:
            self.light.pos[1] = self.y + self.light_spec.get("h", 1.5)

    def update(self, dt):
        if self.light is not None:
            self.light.update(dt)


class TriggerZone(Prop):
    """Gatilho invisível: dispara evento ao entrar (acordar chefe, diálogo, mensagem, fechar arena)."""
    sprite = None

    def __init__(self, spec):
        super().__init__(spec)
        self.rect = spec.get("rect")
        self.event = spec.get("event")
        self.once = spec.get("once", True)
        self.fired = False
        self.text = spec.get("text")

    def update(self, dt):
        super().update(dt)
        if self.fired and self.once:
            return
        p = self.world.player
        if p is None or p.dead:
            return
        x0, z0, x1, z1 = self.rect
        if x0 <= p.x <= x1 and z0 <= p.z <= z1:
            if self.once and self.pid and self.session is not None and self.session.prop_state(self.world.level.id, self.pid):
                self.fired = True
                return
            self.fired = True
            if self.once and self.pid:
                self.save_state(1)
            if self.text:
                self.world.message(self.text, self.spec.get("style", "story"))
            if self.event:
                self.world.bus.emit(self.event, trigger=self)
                if self.session is not None:
                    self.session.on_trigger(self.event, self)


PROP_TYPES = {
    "grace": Grace, "door": Door, "lever": Lever, "plate": PressurePlate, "dial": SymbolDial,
    "seq_button": SequenceButton, "crystal": Crystal, "mirror": Mirror, "emitter": LightEmitter,
    "valve": Valve, "gear_socket": GearSocket, "gear": GearPickup, "power_node": PowerNode,
    "platform": MovingPlatform, "portal": Portal, "exit": Exit, "spawn": SpawnPoint, "chest": Chest,
    "document": Document, "altar": Altar, "breakable": Breakable, "breakable_wall": BreakableWall,
    "arena_pillar": ArenaPillar, "hazard": Hazard, "decor": Decor, "trigger": TriggerZone,
}
