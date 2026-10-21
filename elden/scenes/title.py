"""Tela-título (com o Santuário renderizado ao fundo), seleção de espaço de salvamento, introdução e créditos."""
import math
import time

import pygame

from ..core import saves
from ..core.data import DB
from ..sim.world.loader import build_world
from ..ui.widgets import text, panel, text_block, ListView, divider
from ..ui import theme as T
from .base import Scene
from .menus import Overlay, MenuOverlay, SettingsScreen, ControlsScreen


class TitleScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.list = ListView([], 18, 8)
        self.world = None
        self.ready = False
        self._first = True

    def enter(self):
        self.app.audio.play_music("titulo")
        self._build_menu()

    def resume(self):
        self._build_menu()

    def _build_menu(self):
        app = self.app
        infos = [saves.slot_info(i) for i in range(saves.SLOTS)]
        latest = None
        for i, inf in enumerate(infos):
            if inf and not inf.get("corrupt") and (latest is None or inf["saved_at"] > infos[latest]["saved_at"]):
                latest = i
        opts = []
        if latest is not None:
            opts.append(("Continuar", lambda: self._load(latest)))
        opts += [("Novo Jogo", lambda: app.push(SlotScene(app, "novo"))),
                 ("Carregar", lambda: app.push(SlotScene(app, "carregar"))),
                 ("Configurações", lambda: app.push(SettingsScreen(app))),
                 ("Controles", lambda: app.push(ControlsScreen(app))),
                 ("Créditos", lambda: app.push(CreditsScene(app))),
                 ("Sair", app.quit)]
        self.list.set_items(opts, keep=False)

    def _load(self, slot):
        app = self.app
        s = saves.load_session(slot)
        if s is None:
            return
        from .gameplay import GameplayScene
        lvl, spawn = s.level, s.spawn
        if s.last_grace:
            lvl, spawn = s.last_grace
        app.transition(lambda: app.replace(GameplayScene(app, s, lvl, spawn)))

    def _setup_world(self):
        try:
            self.world = build_world(None, "santuario", "inicio", seed=1)
            sv = self.app.get_scene_view()
            sv.load(self.world)
            sv.camera.snap_to(20, 15)
            self.ready = True
        except Exception as e:      # o título funciona mesmo sem o cenário
            print("aviso: fundo do título indisponível:", e)
            self.ready = False

    def exit(self):
        if self.app.scene_view is not None and self.world is not None and self.app.scene_view.world is self.world:
            self.app.scene_view.unload()
        self.world = None

    def update(self, dt):
        super().update(dt)
        if self._first:
            self._first = False
            return
        if self.world is None and not getattr(self, "_tried", False):
            self._tried = True
            self._setup_world()
        if self.ready and self.app.top is self or (self.ready and self.app.top.overlay):
            w = self.world
            w.step(dt)
            sv = self.app.get_scene_view()
            sv.camera.x = 20 + math.sin(self.time * 0.07) * 6
            sv.camera.z = 16 + math.cos(self.time * 0.05) * 2
            sv.update(dt, w.fx.drain())
            self.app.pipe.fx["dim"] = 0.25
        if self.app.top is not self:
            return
        inp = self.inp
        dx, dy = inp.ui_nav(dt)
        if dy and self.list.move(dy):
            self.sfx("ui_move", 0.5)
        mx, my = self.app.canvas.mouse_to_canvas(*inp.mouse_pos)
        hov = self.list.mouse(mx, my) if (inp.mouse_moved or "left mouse" in inp.pressed) else None
        if inp.ui("confirm") or ("left mouse" in inp.pressed and hov is not None):
            item = self.list.current()
            if item:
                self.sfx("ui_confirm")
                item[1]()

    def draw_ui(self, surf, dt):
        W, H = surf.get_size()
        if not self.ready:
            surf.fill((8, 6, 10, 255))
        a = min(1.0, self.time * 0.6)
        # título
        y = int(H * 0.16)
        for k, (dx, dy) in enumerate(((2, 2), (0, 0))):
            col = (40, 10, 14) if k == 0 else (232, 200, 130)
            text(surf, "ELDEN", (W // 2 + dx, y + dy), 46, col, "midtop", shadow=False, bold=True, alpha=int(255 * a))
        text(surf, "GRAÇA PROFANA  •  O CREPÚSCULO DOS DEUSES", (W // 2, y + 54), 10, (200, 160, 120), "midtop", alpha=int(255 * a))
        divider(surf, W // 2 - 120, W // 2 + 120, y + 70)
        if self.app.top is not self:
            return
        n = len(self.list.items)
        r = pygame.Rect(W // 2 - 90, int(H * 0.5), 180, n * 18 + 12)
        panel(surf, r, "dark", 170)

        def row(s, item, x, yy, w, sel):
            text(s, item[0], (x + w // 2, yy + 3), 11, T.WHITE if sel else T.TEXT, "midtop", bold=sel)
        self.list.draw(surf, r.left + 8, r.top + 6, r.w - 16, row)
        text(surf, "Um jogo de ação e RPG em pixel art 2.5D feito em Python", (W // 2, H - 16), 8, T.MUTED, "midtop")


class SlotScene(MenuOverlay):
    def __init__(self, app, mode):
        self.mode = mode
        self.title = "NOVO JOGO — ESCOLHA UM ESPAÇO" if mode == "novo" else "CARREGAR"
        super().__init__(app, [], 340)
        self.confirm_slot = None
        self._build()

    def _build(self):
        opts = []
        for i in range(saves.SLOTS):
            inf = saves.slot_info(i)
            if inf is None:
                label = f"Espaço {i + 1}: vazio"
                enabled = self.mode == "novo"
            elif inf.get("corrupt"):
                label = f"Espaço {i + 1}: arquivo danificado"
                enabled = self.mode == "novo"
            else:
                cls = DB.classes.get(inf["class_id"], {}).get("name", "?")
                hrs = int(inf["playtime"] // 3600)
                mins = int(inf["playtime"] % 3600 // 60)
                loc = DB.levels.get(inf["location"], {}).get("name", "")
                label = f"{i + 1}: {inf['name']} — {cls} nv {inf['level']} — {loc} — {hrs}h{mins:02d}"
                enabled = True
            opts.append((label, lambda i=i: self._pick(i), enabled))
        opts.append(("Voltar", self.close))
        self.list.set_items(opts)

    def _pick(self, slot):
        app = self.app
        if self.mode == "novo":
            if saves.slot_info(slot) is not None and self.confirm_slot != slot:
                self.confirm_slot = slot
                return
            from .creation import CreationScene
            app.transition(lambda: app.replace(CreationScene(app, slot)))
        else:
            s = saves.load_session(slot)
            if s is None:
                return
            from .gameplay import GameplayScene
            lvl, spawn = s.level, s.spawn
            if s.last_grace:
                lvl, spawn = s.last_grace
            app.transition(lambda: app.replace(GameplayScene(app, s, lvl, spawn)))

    def draw_ui(self, surf, dt):
        super().draw_ui(surf, dt)
        if self.confirm_slot is not None:
            W, H = surf.get_size()
            text(surf, f"O espaço {self.confirm_slot + 1} será sobrescrito. Confirme novamente.", (W // 2, H - 30), 10, (240, 150, 130), "midtop")


INTRO = [
    "Antes do tempo dos reis, o Deus da Luz se partiu em mil estrelas. Os homens chamaram de Graça o brilho que tocaram.",
    "Com a Graça vieram os milagres: feras que pensavam, máquinas que respiravam, santos que não morriam.",
    "Mas toda dádiva cobra seu preço. A Graça apodreceu nas veias de quem a tomou, e o mundo começou a sangrar.",
    "Agora, quando a última chama do Santuário está prestes a se apagar, um Portador desperta.",
    "Você.",
]


class IntroScene(Scene):
    def __init__(self, app, session):
        super().__init__(app)
        self.session = session
        self.page = 0
        self.t = 0.0
        self.embers = [(i * 37 % 640, i * 71 % 360, 0.2 + (i % 7) / 10) for i in range(60)]

    def enter(self):
        self.app.audio.play_music("titulo")

    def update(self, dt):
        super().update(dt)
        self.t += dt
        inp = self.inp
        if (inp.ui("confirm") or "left mouse" in inp.pressed) and self.t > 0.4:
            self.page += 1
            self.t = 0.0
            self.sfx("ui_confirm", 0.4)
        if inp.ui("cancel"):
            self.page = len(INTRO)
        if self.page >= len(INTRO) and not getattr(self, "_go", False):
            self._go = True
            from .gameplay import GameplayScene
            app = self.app
            app.transition(lambda: app.replace(GameplayScene(app, self.session, "santuario", "inicio")), 1.2)

    def draw_ui(self, surf, dt):
        W, H = surf.get_size()
        surf.fill((6, 4, 8, 255))
        for i, (x, y, sp) in enumerate(self.embers):
            yy = (y - self.time * 12 * sp) % H
            xx = x + math.sin(self.time * sp + i) * 4
            surf.set_at((int(xx) % W, int(yy)), (255, 140 + i % 80, 60))
        if self.page < len(INTRO):
            a = int(255 * min(1.0, self.t * 1.2))
            text_block(surf, INTRO[self.page], W // 2 - 220, H // 2 - 30, 440, 13, (230, 214, 190), line_h=18, align="center")
            text(surf, "Enter para continuar • Esc para pular", (W // 2, H - 22), 8, T.MUTED, "midtop", alpha=a)


class CreditsScene(Overlay):
    LINES = ["ELDEN — Graça Profana: O Crepúsculo dos Deuses", "", "Direção, design, código, arte procedural, música e som:",
             "gerados por código em Python", "", "Motor: Ursina + Panda3D • Pixel art por esqueletos procedurais",
             "Interface: pygame • Áudio sintetizado com NumPy", "", "Obrigado por jogar."]

    def update(self, dt):
        super().update(dt)
        if self.time > 0.5 and (self.inp.ui("confirm") or self.back() or self.clicked()):
            self.close()

    def draw_ui(self, surf, dt):
        self.dim(surf, 210)
        W, H = surf.get_size()
        y = H // 2 - len(self.LINES) * 8
        for l in self.LINES:
            text(surf, l, (W // 2, y), 11, T.GOLD if l.startswith("ELDEN") else T.PARCH, "midtop")
            y += 16
