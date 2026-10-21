"""Finais (Purificação, Domínio, Ruptura) com narrativa, estatísticas e créditos."""
import math

import pygame

from ..core.data import DB
from ..ui.widgets import text, text_block, divider
from ..ui import theme as T
from .base import Scene

ENDING_TEXT = {
    "purificacao": dict(title="PURIFICAÇÃO DA GRAÇA", color=(250, 230, 170), bg=(30, 26, 18), particles=(255, 220, 140),
        pages=["Você devolve cada fragmento ao Trono. A luz sobe pelas colunas partidas e o deus volta a respirar.",
               "Nas terras de Elden, as feras dormem, as máquinas silenciam e a carne cicatriza. Por cem anos, há paz.",
               "Na Última Chama, uma nova vela arde com o seu nome. Os Portadores do futuro rezarão diante dela...",
               "...sem saber que um dia, quando a luz apodrecer de novo, um deles despertará. O ciclo continua."]),
    "dominio": dict(title="DOMÍNIO DA GRAÇA", color=(240, 70, 90), bg=(26, 6, 10), particles=(255, 60, 80),
        pages=["Você se senta no Trono. A Graça corre para você como um rio que encontrou o mar.",
               "Aurelion se desfaz em cinzas douradas. Seu nome é o novo hino dos anjos.",
               "Os povos de Elden se ajoelham. Alguns por amor. A maioria por medo.",
               "Um deus novo, faminto e eterno. Talvez, desta vez, ninguém suba para destroná-lo."]),
    "ruptura": dict(title="RUPTURA DO CICLO", color=(170, 200, 255), bg=(10, 12, 24), particles=(180, 210, 255),
        pages=["Com os cinco Fragmentos do Ciclo, você golpeia o Trono. A pedra divina se parte como vidro.",
               "A Graça explode em milhões de faíscas e cai sobre Elden como neve. Fraca. Livre. De todos.",
               "Não haverá mais santos imortais, nem feras divinas, nem deuses famintos.",
               "O amanhecer é frio e incerto. Mas, pela primeira vez, pertence aos vivos."]),
}


class EndingScene(Scene):
    def __init__(self, app, session, ending):
        super().__init__(app)
        self.s = session
        self.e = ending
        self.page = 0
        self.t = 0.0
        self.credits = False

    def enter(self):
        self.app.audio.play_music("final")
        self.app.pipe.fx["dim"] = 0.0

    def update(self, dt):
        super().update(dt)
        self.t += dt
        inp = self.inp
        if (inp.ui("confirm") or "left mouse" in inp.pressed) and self.t > 0.6:
            self.t = 0.0
            if self.credits:
                from .title import TitleScene
                app = self.app
                app.transition(lambda: app.replace(TitleScene(app)), 0.8)
                return
            self.page += 1
            if self.page >= len(ENDING_TEXT[self.e]["pages"]):
                self.credits = True

    def draw_ui(self, surf, dt):
        W, H = surf.get_size()
        d = ENDING_TEXT[self.e]
        surf.fill((*d["bg"], 255))
        for i in range(90):
            sp = 0.3 + (i % 7) / 10
            x = (i * 47 + math.sin(self.time * sp + i) * 20) % W
            y = (i * 29 - self.time * 14 * sp) % H if self.e != "ruptura" else (i * 29 + self.time * 10 * sp) % H
            surf.set_at((int(x), int(y)), d["particles"])
        a = int(255 * min(1.0, self.t * 1.2))
        text(surf, d["title"], (W // 2, 40), 20, d["color"], "midtop", bold=True)
        divider(surf, W // 2 - 120, W // 2 + 120, 68)
        if not self.credits:
            text_block(surf, d["pages"][self.page], W // 2 - 220, H // 2 - 30, 440, 12, T.PARCH, line_h=17, align="center")
        else:
            c = self.s.char
            lines = [f"{c.name}, {DB.classes[c.class_id]['name']} de nível {c.level}",
                     f"Tempo de jogo: {int(self.s.playtime // 3600)}h{int(self.s.playtime % 3600 // 60):02d}   Mortes: {self.s.deaths}",
                     f"Chefes derrotados: {len(self.s.bosses)}   Segredos: {len(self.s.secrets)}   Documentos: {len(self.s.docs)}",
                     f"Corrupção final: {int(c.corruption)}%   Purificados: {len(c.purified)}   Absorvidos: {len(c.absorbed)}",
                     "", "ELDEN — Graça Profana: O Crepúsculo dos Deuses", "Obrigado por jogar.",
                     "Os outros finais esperam por escolhas diferentes."]
            y = H // 2 - 50
            for l in lines:
                text(surf, l, (W // 2, y), 10, T.PARCH if l else T.PARCH, "midtop")
                y += 15
        text(surf, "Enter", (W // 2, H - 18), 8, T.MUTED, "midtop", alpha=a)
