"""Cena de jogo: simulação da fase, renderização, HUD e fluxo (descanso, viagem, morte, diálogos, chefes)."""
import math

import pygame

from ..core.data import DB
from ..core import saves
from ..sim.world.loader import build_world
from ..sim.combat.actions import TimedAction
from ..ui.hud import HUD
from ..ui.widgets import text, panel
from ..ui import theme as T
from .base import Scene


class GameplayScene(Scene):
    pauses_below = True

    def __init__(self, app, session, level_id=None, spawn=None):
        super().__init__(app)
        self.session = session
        self.world = None
        self.sv = app.get_scene_view()
        self.hud = HUD(app.settings)
        self.sv.events_hook = None
        self.pending = (level_id or session.level, spawn or session.spawn)
        self.dead_t = None
        self.area_name = None
        self.loading = True
        self.load_progress = (0, 1, "")
        self.resting = False
        self.queue = []

    # ------------------------------------------------------------------ carregamento
    def enter(self):
        self._schedule_load(*self.pending, fade=False)

    def _schedule_load(self, level_id, spawn, fade=True, after=None):
        def do():
            self.loading = True
            self.load_progress = (0, 1, "")
            self._load_now = (level_id, spawn, after)
        if fade:
            self.app.transition(do, 3.0)
        else:
            do()

    def _do_load(self):
        level_id, spawn, after = self._load_now
        self._load_now = None
        old_player = None
        self.world = build_world(self.session, level_id, spawn, seed=None)
        w = self.world
        app = self.app

        def prog(i, n, sid):
            self.load_progress = (i, n, sid)
        self.sv.load(w, prog)
        self.sv.camera.strength = app.settings.get("shake", 1.0)
        w.bus.on("region", self._on_region)
        self.hud.show_area(w.level.name)
        self.area_name = w.level.name
        env = DB.environments.get(w.level.env, {})
        app.audio.play_music(w.level.music or env.get("music"))
        self.loading = False
        self.dead_t = None
        if after:
            after()
        saves.save_session(self.session)

    def _on_region(self, old, new):
        if new is not None and new.get("name") and new.get("name") != self.area_name:
            self.area_name = new["name"]
            self.hud.show_area(new["name"])

    # ------------------------------------------------------------------ laço
    def update(self, dt):
        super().update(dt)
        app = self.app
        if getattr(self, "_load_now", None):
            if self.loading and self.load_progress == (0, 1, "") and not getattr(self, "_drawn_loading", False):
                self._drawn_loading = True
                return
            self._drawn_loading = False
            self._do_load()
            return
        if self.world is None:
            return
        w = self.world
        p = w.player
        self.session.playtime += dt
        inp = app.input
        if inp.ui("menu") and p is not None and not p.dead:
            from .menus import PauseMenu
            app.push(PauseMenu(app, self))
            return
        if p is not None:
            if p.dead:
                p.input.clear()
                p.input.begin_frame(dt)
            else:
                inp.fill_game_state(p.input, dt)
        w.step(dt)
        events = w.fx.drain()
        listener = (p.x, p.z) if p is not None else None
        for ev in events:
            self.hud.handle(ev, w)
            app.audio.handle_event(ev, listener)
            if ev["kind"] == "player_hurt":
                app.pipe.fx["hurt"] = 0.8
            if ev["kind"] == "boss_start":
                env = DB.environments.get(w.level.env, {})
                bd = DB.bosses.get(getattr(w.boss, "boss_id", ""), {})
                app.audio.play_music(DB.environments.get(w.level.env, {}).get("music", "chefe1") if "chefe" in env.get("music", "") else
                                     {1: "chefe1", 2: "chefe2", 3: "chefe3", 4: "chefe4", 5: "chefe5"}.get(bd.get("act", 1), "chefe1"))
        self.sv.corruption_glow = self.session.char.corruption_tier / 3.0
        self.sv.update(dt, events)
        # efeitos de tela
        fxs = app.pipe.fx
        fxs["hurt"] = max(0.0, fxs["hurt"] - dt * 1.5)
        if p is not None and not p.dead and p.hp < p.max_hp * 0.25:
            fxs["hurt"] = max(fxs["hurt"], 0.25 + 0.15 * math.sin(self.time * 6))
        fxs["hurt"] = max(fxs["hurt"], 0.06 * self.session.char.corruption_tier)
        fxs["desat"] = 0.5 if p is not None and p.dead else 0.0
        fxs["aberration"] = 1.5 if w.time_scale < 0.9 else 0.0
        for msg, kind in self.session.notifications:
            self.hud.message(msg, kind)
        self.session.notifications.clear()
        self._process_events()
        # morte do jogador
        if p is not None and p.dead:
            if self.dead_t is None:
                self.dead_t = 0.0
                app.audio.play("player_death")
                app.audio.play_music("morte")
            self.dead_t += dt
            if self.dead_t > 2.2:
                from .menus import DeathOverlay
                self.dead_t = -999
                app.push(DeathOverlay(app, self))

    def _process_events(self):
        s = self.session
        app = self.app
        while s.events:
            ev = s.events.pop(0)
            kind = ev[0]
            if kind == "rest":
                self._rest(ev[1])
            elif kind == "travel":
                self.travel(ev[1], ev[2])
            elif kind == "dialogue":
                from .dialogue import DialogueOverlay
                if ev[1] in DB.dialogues:
                    app.push(DialogueOverlay(app, self, ev[1], ev[2]))
            elif kind == "document":
                from .dialogue import DocumentOverlay
                app.push(DocumentOverlay(app, ev[1]))
            elif kind == "boss_defeated":
                bd = DB.bosses[ev[1]]
                self.hud.show_banner("LENDA ABATIDA" if not bd.get("optional") else "INIMIGO FORMIDÁVEL ABATIDO", bd["name"],
                                     (240, 200, 120), 4.5)
                app.audio.play("boss_defeated")
                env = DB.environments.get(self.world.level.env, {})
                app.audio.play_music(self.world.level.music if "chefe" not in (self.world.level.music or "") else "santuario")
                saves.save_session(s)
                if ev[1] == "aurelion":
                    s.set_flag("aurelion_derrotado")
            elif kind == "boss_choice":
                from .dialogue import BossChoiceOverlay
                self.queue.append(lambda bid=ev[1]: app.push(BossChoiceOverlay(app, self, bid)))
            elif kind == "ending_choice":
                from .dialogue import EndingChoiceOverlay
                app.push(EndingChoiceOverlay(app, self))
        if self.queue and self.hud.banner is None and app.top is self:
            fn = self.queue.pop(0)
            fn()

    # ------------------------------------------------------------------ fluxo
    def _rest(self, grace_pid):
        app = self.app
        p = self.world.player
        p.refill()
        p.set_action(TimedAction("sit", 999, loop=True, name="rest", invulnerable=True))
        app.audio.play("rest")
        saves.save_session(self.session)
        from .menus import GraceMenu
        app.push(GraceMenu(app, self, grace_pid))

    def end_rest(self, grace_pid, travel_to=None):
        """Ao sair do menu da Graça: os inimigos renascem (recarrega a fase na Graça)."""
        if travel_to is not None:
            lvl, pid = travel_to
            self._schedule_load(lvl, pid)
        else:
            self._schedule_load(self.world.level.id, grace_pid)

    def travel(self, level_id, spawn):
        self._schedule_load(level_id, spawn)

    def respawn(self):
        s = self.session
        p = self.world.player
        s.on_player_death(p, self.world.level.id)
        if s.last_grace:
            lvl, pid = s.last_grace
        else:
            lvl, pid = "santuario", "inicio"
        self._schedule_load(lvl, pid)

    # ------------------------------------------------------------------ interface
    def to_screen(self, x, y, z):
        sx, sy = self.app.pipe.world_to_screen(x, y, z)
        sc = self.app.canvas.scale
        return sx / sc, sy / sc

    def draw_ui(self, surf, dt):
        if getattr(self, "_load_now", None) or self.world is None:
            self._draw_loading(surf)
            return
        w = self.world
        p = w.player
        interact = None
        if p is not None and not p.dead and (p.action is None or p.action.interruptible_by_input()):
            interact = p.find_interactable()
        top_is_me = self.app.top is self
        if top_is_me:
            self.hud.draw(surf, dt, w, p, self.session, self.to_screen, self.app.input.last_device, interact)
        if self.app.settings.get("hitboxes"):
            self._draw_debug(surf)

    def _draw_loading(self, surf):
        W, H = surf.get_size()
        surf.fill((6, 4, 8, 255))
        i, n, sid = self.load_progress
        text(surf, "Carregando...", (W // 2, H // 2 - 20), 16, T.GOLD, "center", bold=True)
        if n > 1:
            from ..ui.widgets import bar
            bar(surf, (W // 2 - 100, H // 2 + 4, 200, 6), i / n, T.GOLD)
            text(surf, "Forjando sprites (apenas na primeira vez)", (W // 2, H // 2 + 16), 9, T.MUTED, "midtop")
        tips = ["Aparar no instante certo abre contra-ataques devastadores.", "Rompa a postura e aperte Leve para executar.",
                "Descansar numa Graça restaura tudo — e traz os inimigos de volta.",
                "Golpes leves seguidos de um pesado costumam lançar o inimigo ao ar.",
                "Segure Esquiva para correr; ataque correndo para uma investida.",
                "Runas mudam a forma de lutar: combine-as com a árvore de Graça.",
                "Ao morrer, sua Graça fica onde você caiu. Volte para buscá-la."]
        text(surf, tips[int(self.time / 4) % len(tips)], (W // 2, H - 40), 10, T.PARCH, "midtop")

    def _draw_debug(self, surf):
        w = self.world
        for e in w.actors + w.zones + w.props:
            if not e.alive:
                continue
            for sh in e.debug_shapes():
                kind = sh[0]
                if kind == "circle":
                    _, x, z, r, col = sh
                    cx, cy = self.to_screen(x, e.y, z)
                    pts = [self.to_screen(x + math.cos(a) * r, e.y, z + math.sin(a) * r) for a in [i * math.tau / 16 for i in range(16)]]
                    pygame.draw.lines(surf, tuple(int(c * 255) for c in col), True, pts, 1)
                elif kind == "arc":
                    _, x, z, rng, face, ang = sh
                    pts = [self.to_screen(x, e.y + 0.1, z)]
                    for i in range(9):
                        a = face - ang / 2 + ang * i / 8
                        pts.append(self.to_screen(x + math.cos(a) * rng, e.y + 0.1, z + math.sin(a) * rng))
                    pygame.draw.lines(surf, (255, 80, 60), True, pts, 1)
                elif kind == "line":
                    _, x, z, face, L, wd = sh
                    fx, fz = math.cos(face), math.sin(face)
                    px, pz = -fz * wd / 2, fx * wd / 2
                    corners = [(x + px, z + pz), (x + fx * L + px, z + fz * L + pz), (x + fx * L - px, z + fz * L - pz), (x - px, z - pz)]
                    pygame.draw.lines(surf, (255, 80, 60), True, [self.to_screen(a, e.y + 0.1, b) for a, b in corners], 1)
            if e.kind in ("enemy", "boss") and hasattr(e, "brain"):
                sx, sy = self.to_screen(e.x, e.y + 2.4 * e.scale, e.z)
                text(surf, e.brain.state, (sx, sy), 8, (180, 255, 180), "midbottom")
