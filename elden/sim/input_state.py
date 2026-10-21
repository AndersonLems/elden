"""Estado de entrada abstrato (independente de teclado/controle), com buffer de comandos."""

ACTIONS = ("light", "heavy", "dodge", "jump", "block", "art", "skill1", "skill2", "skill3", "ultimate",
           "interact", "lock", "flask", "flask_fp", "lock_next")

BUFFER_TIME = 0.28


class InputState:
    def __init__(self):
        self.move = (0.0, 0.0)       # vetor no plano XZ (x = leste, z = norte), comprimento <= 1
        self.held = set()
        self.pressed = set()
        self.released = set()
        self.buffer = []             # (ação, tempo)
        self.time = 0.0
        self.held_time = {}

    def begin_frame(self, dt):
        self.time += dt
        for k in list(self.held_time):
            if k in self.held:
                self.held_time[k] += dt
        self.buffer = [(a, t) for (a, t) in self.buffer if self.time - t <= BUFFER_TIME]

    def press(self, action):
        self.pressed.add(action)
        self.held.add(action)
        self.held_time[action] = 0.0
        self.buffer.append((action, self.time))

    def release(self, action):
        self.released.add(action)
        self.held.discard(action)

    def set_held(self, action, down):
        if down and action not in self.held:
            self.press(action)
        elif not down and action in self.held:
            self.release(action)

    def end_frame(self):
        self.pressed.clear()
        self.released.clear()

    def peek(self, *actions):
        """Ação mais recente no buffer entre as pedidas (sem consumir)."""
        for a, t in reversed(self.buffer):
            if a in actions:
                return a
        return None

    def consume(self, action):
        for i in range(len(self.buffer) - 1, -1, -1):
            if self.buffer[i][0] == action:
                del self.buffer[i]
                return True
        return False

    def holding(self, action):
        return action in self.held

    def hold_time(self, action):
        return self.held_time.get(action, 0.0) if action in self.held else 0.0

    def clear(self):
        self.held.clear()
        self.pressed.clear()
        self.released.clear()
        self.buffer.clear()
        self.move = (0.0, 0.0)
