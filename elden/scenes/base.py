"""Cenas (telas) e sobreposições. A aplicação mantém uma pilha; sobreposições pausam a cena de baixo."""


class Scene:
    overlay = False          # desenha por cima da cena anterior
    pauses_below = True      # congela a simulação da cena de baixo
    full = False             # cobre a tela: as interfaces das cenas de baixo não são desenhadas

    def __init__(self, app):
        self.app = app
        self.time = 0.0

    def enter(self):
        pass

    def exit(self):
        pass

    def resume(self):
        """Volta a ser a cena do topo (uma sobreposição foi fechada)."""

    def update(self, dt):
        self.time += dt

    def draw_ui(self, surf, dt):
        pass

    # atalhos
    @property
    def inp(self):
        return self.app.input

    def sfx(self, name, vol=1.0):
        self.app.audio.play(name, vol)

    def close(self):
        self.app.pop(self)
