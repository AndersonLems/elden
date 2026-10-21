"""Mapeamento de teclado, mouse e controle para ações de jogo e de interface."""
import math

GAME_BINDINGS = {
    "light": ["j", "left mouse", "gamepad x"],
    "heavy": ["k", "right mouse", "gamepad y"],
    "dodge": ["left shift", "right shift", "gamepad b"],
    "jump": ["space", "gamepad a"],
    "block": ["q", "l", "gamepad left shoulder"],
    "art": ["f", "gamepad right shoulder"],
    "skill1": ["1", "u"],
    "skill2": ["2", "i"],
    "skill3": ["3", "o"],
    "ultimate": ["r", "gamepad right trigger"],
    "interact": ["e", "gamepad dpad right"],
    "lock": ["tab", "middle mouse", "gamepad right stick"],
    "lock_next": ["c", "gamepad dpad left"],
    "flask": ["z", "4", "gamepad dpad up"],
    "flask_fp": ["x", "5", "gamepad dpad down"],
}
MOVE_KEYS = {"up": ["w", "up arrow"], "down": ["s", "down arrow"], "left": ["a", "left arrow"], "right": ["d", "right arrow"]}

UI_BINDINGS = {
    "up": ["w", "up arrow", "gamepad dpad up"], "down": ["s", "down arrow", "gamepad dpad down"],
    "left": ["a", "left arrow", "gamepad dpad left"], "right": ["d", "right arrow", "gamepad dpad right"],
    "confirm": ["enter", "space", "e", "gamepad a"], "cancel": ["escape", "backspace", "gamepad b"],
    "prev_tab": ["q", "page up", "gamepad left shoulder"], "next_tab": ["page down", "gamepad right shoulder", "tab"],
    "extra": ["x", "delete", "gamepad x"], "extra2": ["c", "gamepad y"], "menu": ["escape", "gamepad start"],
}
CONTROLS_HELP = [
    ("WASD / Setas", "Mover"), ("J / Botão esq.", "Ataque leve (combos)"), ("K / Botão dir.", "Ataque pesado (segure: carregado)"),
    ("Shift", "Esquiva (segure: correr)"), ("Espaço", "Pular"), ("Q", "Bloquear (toque no tempo certo: aparar)"),
    ("F", "Arte de combate"), ("1  2  3", "Habilidades da classe"), ("R", "Habilidade suprema (Fervor cheio)"),
    ("E", "Interagir / descansar na Graça"), ("Tab / C", "Travar alvo / trocar alvo"), ("Z / X", "Frasco de Brasa / de Éter"),
    ("Esc", "Pausa"), ("F3", "Mostrar hitboxes"), ("F11", "Tela cheia"),
    ("Combos", "L L L • L L H • H segurado • Esquiva+L • Corrida+L"),
    ("Aéreo", "Lançador (L→H ou Trás+H) • Pule • L L L no ar • H = mergulho"),
    ("Execução", "Rompa a postura (barra amarela) e aperte Leve perto do inimigo"),
]
GAMEPAD_HELP = [("A", "Pular"), ("B", "Esquiva/correr"), ("X / Y", "Leve / Pesado"), ("LB", "Bloquear/aparar"), ("RB", "Arte"),
                ("LT + X/Y/A", "Habilidades 1/2/3"), ("RT", "Suprema"), ("R3", "Travar alvo"), ("Direcional", "Frascos, trocar alvo, interagir")]


class InputManager:
    """Coleta eventos do Ursina e expõe estado de jogo (InputState) e navegação de UI."""

    def __init__(self):
        self.down = set()
        self.pressed = set()
        self.released = set()
        self.text = []
        self.mouse_pos = (0.0, 0.0)       # -1..1
        self.mouse_moved = False
        self.scroll = 0
        self._last_mouse = None
        self.gamepad_axes = {"lx": 0.0, "ly": 0.0, "lt": 0.0, "rt": 0.0}
        self.ui_repeat = {}
        self.last_device = "keyboard"

    # ------------------------------------------------------------------ eventos crus
    def on_key(self, key):
        if key.endswith(" up"):
            k = key[:-3]
            if k.endswith(" mouse"):
                pass
            self.down.discard(k)
            self.released.add(k)
            return
        if key in ("scroll up", "scroll down"):
            self.scroll += 1 if key == "scroll up" else -1
            return
        k = key
        if k.endswith(" mouse down"):
            k = k[:-5]
        if k.endswith(" mouse up"):
            k = k[:-3]
            self.down.discard(k)
            self.released.add(k)
            return
        if k.endswith(" hold"):
            return
        self.down.add(k)
        self.pressed.add(k)
        self.last_device = "gamepad" if k.startswith("gamepad") else "keyboard"

    def on_text(self, ch):
        self.text.append(ch)

    def poll(self, base, held_keys):
        """Lê eixos do controle e a posição do mouse."""
        lx = held_keys.get("gamepad left stick x", 0.0) if hasattr(held_keys, "get") else 0.0
        ly = held_keys.get("gamepad left stick y", 0.0) if hasattr(held_keys, "get") else 0.0
        self.gamepad_axes["lx"], self.gamepad_axes["ly"] = lx, ly
        try:
            from panda3d.core import InputDevice
            for dev in base.devices.getDevices(InputDevice.DeviceClass.gamepad):
                for name, ax in (("lt", InputDevice.Axis.left_trigger), ("rt", InputDevice.Axis.right_trigger)):
                    a = dev.findAxis(ax)
                    v = a.value if a else 0.0
                    key = "gamepad " + ("left" if name == "lt" else "right") + " trigger"
                    if v > 0.5 and key not in self.down:
                        self.on_key(key)
                    elif v < 0.3 and key in self.down:
                        self.on_key(key + " up")
                    self.gamepad_axes[name] = v
                break
        except Exception:
            pass
        mw = base.mouseWatcherNode
        if mw is not None and mw.has_mouse():
            m = mw.get_mouse()
            pos = (m.x, m.y)
            if self._last_mouse is not None and (abs(pos[0] - self._last_mouse[0]) > 1e-4 or abs(pos[1] - self._last_mouse[1]) > 1e-4):
                self.mouse_moved = True
                self.last_device = "mouse"
            self._last_mouse = pos
            self.mouse_pos = pos

    def end_frame(self):
        self.pressed.clear()
        self.released.clear()
        self.text.clear()
        self.mouse_moved = False
        self.scroll = 0

    # ------------------------------------------------------------------ consultas
    def any_pressed(self, keys):
        return any(k in self.pressed for k in keys)

    def any_down(self, keys):
        return any(k in self.down for k in keys)

    def ui(self, action):
        return self.any_pressed(UI_BINDINGS[action])

    def ui_nav(self, dt):
        """Navegação com repetição ao segurar: devolve (dx, dy) com y positivo para baixo."""
        dx = dy = 0
        ax = self.gamepad_axes
        stick = {"up": ax["ly"] > 0.6, "down": ax["ly"] < -0.6, "left": ax["lx"] < -0.6, "right": ax["lx"] > 0.6}
        for name, (vx, vy) in (("up", (0, -1)), ("down", (0, 1)), ("left", (-1, 0)), ("right", (1, 0))):
            keys = UI_BINDINGS[name]
            held = self.any_down(keys) or stick[name]
            prev = self.ui_repeat.get(name)
            fire = False
            if held:
                if prev is None:
                    fire = True
                    self.ui_repeat[name] = 0.38
                else:
                    t = prev - dt
                    if t <= 0:
                        fire = True
                        t = 0.075
                    self.ui_repeat[name] = t
            else:
                self.ui_repeat.pop(name, None)
            if self.any_pressed(keys) and not fire:
                fire = True
            if fire:
                dx += vx
                dy += vy
        return max(-1, min(1, dx)), max(-1, min(1, dy))

    def fill_game_state(self, st, dt):
        """Converte o estado dos dispositivos num InputState do jogador."""
        st.begin_frame(dt)
        mx = mz = 0.0
        if self.any_down(MOVE_KEYS["right"]):
            mx += 1
        if self.any_down(MOVE_KEYS["left"]):
            mx -= 1
        if self.any_down(MOVE_KEYS["up"]):
            mz += 1
        if self.any_down(MOVE_KEYS["down"]):
            mz -= 1
        gx, gy = self.gamepad_axes["lx"], self.gamepad_axes["ly"]
        if abs(gx) > 0.15 or abs(gy) > 0.15:
            mx, mz = gx, gy
        d = math.hypot(mx, mz)
        if d > 1.0:
            mx, mz = mx / d, mz / d
        from .render.projection import screen_move_to_world
        st.move = screen_move_to_world(mx, mz)
        lt_held = "gamepad left trigger" in self.down
        for action, keys in GAME_BINDINGS.items():
            ks = list(keys)
            if lt_held and action in ("light", "heavy", "jump"):
                continue
            down = self.any_down(ks)
            pressed = self.any_pressed(ks)
            if pressed:
                st.press(action)
            elif down and action not in st.held:
                st.held.add(action)
                st.held_time[action] = 0.0
            elif not down and action in st.held:
                st.release(action)
        if lt_held:
            for action, key in (("skill1", "gamepad x"), ("skill2", "gamepad y"), ("skill3", "gamepad a")):
                if key in self.pressed:
                    st.press(action)
