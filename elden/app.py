"""Aplicação: janela Ursina/Panda3D, pipeline de renderização, interface, áudio, entrada e pilha de cenas."""
import sys
import time as _time

from panda3d.core import loadPrcFileData

from .core.settings import Settings, Quality


def configure_panda(settings):
    loadPrcFileData("", "textures-auto-power-2 #f")
    loadPrcFileData("", "textures-power-2 none")
    loadPrcFileData("", "notify-level-glgsg warning")
    loadPrcFileData("", "notify-level-display error")
    loadPrcFileData("", "audio-library-name p3openal_audio")
    loadPrcFileData("", "framebuffer-srgb #f")
    loadPrcFileData("", "sync-video #t" if settings.get("vsync", True) else "sync-video #f")


class App:
    def __init__(self, args=None):
        args = args or {}
        self.settings = Settings.load()
        if args.get("fullscreen") is not None:
            self.settings["fullscreen"] = args["fullscreen"]
        if args.get("quality"):
            self.settings["quality"] = args["quality"]
        if args.get("novsync"):
            self.settings["vsync"] = False
        configure_panda(self.settings)
        from ursina import Ursina, Entity, application, window, held_keys, time as utime
        self.ursina_time = utime
        self.held_keys = held_keys
        size = tuple(args.get("size") or self.settings.get("window", [1280, 720]))
        self.ursina = Ursina(title="ELDEN — Graça Profana", size=size, fullscreen=bool(self.settings.get("fullscreen")),
                             borderless=False, development_mode=False, vsync=self.settings.get("vsync", True),
                             show_ursina_splash=False)
        loadPrcFileData("", "textures-auto-power-2 #f")
        loadPrcFileData("", "textures-power-2 none")
        self.base = application.base
        self.base.camNode.set_active(False)
        try:
            from ursina import camera
            camera.ui.enabled = False
        except Exception:
            pass
        window.color = (0, 0, 0, 1)
        try:
            window.exit_button.enabled = False
            window.fps_counter.enabled = False
            window.entity_counter.enabled = False
            window.collider_counter.enabled = False
        except Exception:
            pass
        self.window = window
        self.quality = Quality(self.settings.get("quality", "alta"))
        from .render.pipeline import PixelPipeline
        from .render.sprite_bank import SpriteBank, PropAtlas
        from .render.fx import FxManager
        from .render.scene_view import SceneView
        from .ui.canvas import Canvas
        from .input_map import InputManager
        from .audio.manager import AudioManager
        self.pipe = PixelPipeline(self.base, self.quality)
        self.canvas = Canvas()
        self.input = InputManager()
        self.audio = AudioManager(self.base, self.settings)
        self.bank = SpriteBank()
        self._props = None
        self.fx = FxManager(self.pipe)
        self.scene_view = None
        self.SceneView = SceneView
        self.stack = []
        self.fade = 0.0
        self.fade_dir = 0
        self.fade_cb = None
        self.fps = 60.0
        self.quit_requested = False
        self.time = 0.0
        self.frame = 0
        self.test_hook = None
        app = self

        class _Driver(Entity):
            def update(self_):
                app._update()

            def input(self_, key):
                app._key(key)

            def text_input(self_, key):
                app.input.on_text(key)

        self.driver = _Driver(eternal=True)

    @property
    def props(self):
        if self._props is None:
            from .render.sprite_bank import PropAtlas
            self._props = PropAtlas()
        return self._props

    def get_scene_view(self):
        if self.scene_view is None:
            self.scene_view = self.SceneView(self.pipe, self.bank, self.props, self.fx)
        return self.scene_view

    # ------------------------------------------------------------------ pilha de cenas
    @property
    def top(self):
        return self.stack[-1] if self.stack else None

    def push(self, scene):
        self.stack.append(scene)
        scene.enter()

    def pop(self, scene=None):
        if not self.stack:
            return
        if scene is not None and scene in self.stack:
            idx = self.stack.index(scene)
            removed = self.stack[idx:]
            self.stack = self.stack[:idx]
        else:
            removed = [self.stack.pop()]
        for s in reversed(removed):
            s.exit()
        if self.top is not None:
            self.top.resume()

    def replace(self, scene):
        while self.stack:
            self.stack.pop().exit()
        self.push(scene)

    def transition(self, cb, speed=3.0):
        """Escurece a tela, executa cb e clareia."""
        if self.fade_dir == 1:
            return
        self.fade_dir = 1
        self.fade_cb = cb
        self.fade_speed = speed

    def apply_quality(self, name):
        self.settings["quality"] = name
        self.quality.set(name)
        self.pipe.apply_quality()

    def set_fullscreen(self, on):
        self.settings["fullscreen"] = on
        self.window.fullscreen = on

    def quit(self):
        self.quit_requested = True

    # ------------------------------------------------------------------ laço
    def _key(self, key):
        if key == "f11":
            self.set_fullscreen(not self.window.fullscreen)
            self.settings.save()
            return
        if key == "f3":
            self.settings["hitboxes"] = not self.settings.get("hitboxes", False)
            return
        if key == "f2":
            self.settings["show_fps"] = not self.settings.get("show_fps", False)
            return
        self.input.on_key(key)

    def _update(self):
        raw_dt = self.ursina_time.dt
        dt = min(0.05, max(0.0, raw_dt))
        self.time += dt
        self.frame += 1
        if raw_dt > 0:
            self.fps = self.fps * 0.95 + (1.0 / raw_dt) * 0.05
        self.input.poll(self.base, self.held_keys)
        if self.test_hook is not None:
            self.test_hook(self, dt)
        top = self.top
        # atualiza a cena do topo; sobreposições que não pausam deixam a de baixo correr
        for s in list(self.stack):
            if s is top:
                s.update(dt)
            elif not any(o.pauses_below for o in self.stack[self.stack.index(s) + 1:]):
                s.update(dt)
        # transição
        if self.fade_dir == 1:
            self.fade = min(1.0, self.fade + dt * self.fade_speed)
            if self.fade >= 1.0:
                cb, self.fade_cb = self.fade_cb, None
                self.fade_dir = -1
                if cb:
                    cb()
        elif self.fade_dir == -1:
            self.fade = max(0.0, self.fade - dt * self.fade_speed)
            if self.fade <= 0:
                self.fade_dir = 0
        self.pipe.fx["fade"] = self.fade
        # interface
        W, H = self.pipe.window_size()
        surf = self.canvas.begin(W, H)
        start = 0
        for i, s in enumerate(self.stack):
            if s.full:
                start = i
        for s in self.stack[start:]:
            s.draw_ui(surf, dt)
        if self.settings.get("show_fps"):
            from .ui.widgets import text
            text(surf, f"{self.fps:.0f} FPS", (surf.get_width() - 4, 2), 9, (200, 220, 200), "topright")
        if self.fade > 0:
            import pygame
            sh = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            sh.fill((0, 0, 0, int(255 * self.fade)))
            surf.blit(sh, (0, 0))
        self.pipe.upload_ui(self.canvas.to_bytes(), self.canvas.w, self.canvas.h)
        self.audio.update(dt)
        self.input.end_frame()
        if self.quit_requested:
            self.settings.save()
            from ursina import application
            application.quit()
            sys.exit(0)

    def run(self, first_scene):
        self.push(first_scene)
        self.ursina.run()


def run(args):
    app = App(args)
    from .scenes.title import TitleScene
    app.run(TitleScene(app))
