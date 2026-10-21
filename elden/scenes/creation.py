"""Criação de personagem: nome, classe (com atributos, estilo, arma e habilidades) e aparência com prévia animada."""
import math

import numpy as np
import pygame

from ..core.data import DB
from ..art import characters
from ..art.anims import pose_for
from ..art.rig import render_frame
from ..sim.progression.character import Character
from ..sim.session import Session
from ..sim.stats import ATTRIBUTES, ATTRIBUTE_NAMES
from ..ui.widgets import text, panel, text_block, bar, divider, text_width
from ..ui import icons
from ..ui import theme as T
from .base import Scene

CLASS_ORDER = ["guerreiro", "ninja", "soldado", "bandido", "ladrao", "mago", "clerigo", "vampiro", "lobisomem"]
FIELDS = ["nome", "classe", "pele", "cabelo", "cor", "variante", "comecar"]
SKIN_NAMES = ["Clara", "Rosada", "Morena clara", "Morena", "Escura", "Retinta"]
HAIR_NAMES = ["Curto", "Longo", "Preso", "Espetado", "Sem cabelo"]
HAIR_COLOR_NAMES = ["Negro", "Castanho", "Ruivo escuro", "Loiro", "Grisalho", "Vermelho", "Azulado"]


class CreationScene(Scene):
    def __init__(self, app, slot):
        super().__init__(app)
        self.slot = slot
        self.name = "Portador"
        self.cls = 0
        self.app_ = {"skin": 2, "hair": 0, "hair_color": 0, "variant": 0}
        self.field = 1
        self.preview_cache = {}
        self.anim_i = 0

    def enter(self):
        self.app.audio.play_music("santuario")

    @property
    def class_id(self):
        return CLASS_ORDER[self.cls]

    def _preview(self, anim, t, facing):
        key = (self.class_id, tuple(sorted(self.app_.items())), anim, round(t, 2), facing)
        img = self.preview_cache.get(key)
        if img is None:
            rig = characters.player_rig(self.class_id, self.app_)
            arr = render_frame(rig, pose_for(anim, t, characters.is_two_handed(rig)), facing, rig.frame)
            img = pygame.image.frombuffer(np.ascontiguousarray(arr).tobytes(), (arr.shape[1], arr.shape[0]), "RGBA").copy()
            if len(self.preview_cache) > 400:
                self.preview_cache.clear()
            self.preview_cache[key] = img
        return img

    def update(self, dt):
        super().update(dt)
        inp = self.inp
        f = FIELDS[self.field]
        if f == "nome":
            for ch in inp.text:
                if len(self.name) < 16 and (ch.isalnum() or ch in " -'"):
                    self.name += ch
            if "backspace" in inp.pressed and self.name:
                self.name = self.name[:-1]
        dx, dy = inp.ui_nav(dt)
        if f == "nome":
            dx = 0 if any(k in inp.pressed for k in ("a", "d")) else (-1 if "left arrow" in inp.pressed else 1 if "right arrow" in inp.pressed else 0)
            if any(k in inp.pressed for k in ("w", "s")):
                dy = 0
                if "up arrow" in inp.pressed:
                    dy = -1
                if "down arrow" in inp.pressed:
                    dy = 1
        if dy:
            self.field = (self.field + dy) % len(FIELDS)
            self.sfx("ui_move", 0.5)
        if dx:
            self._change(f, dx)
        mx, my = self.app.canvas.mouse_to_canvas(*inp.mouse_pos)
        for i, r in enumerate(getattr(self, "_rects", [])):
            if r.collidepoint(mx, my):
                if inp.mouse_moved:
                    self.field = i
                if "left mouse" in inp.pressed:
                    self.field = i
                    if FIELDS[i] == "comecar":
                        self._start()
                    elif FIELDS[i] != "nome":
                        self._change(FIELDS[i], 1)
        for i, r in enumerate(getattr(self, "_class_rects", [])):
            if r.collidepoint(mx, my) and "left mouse" in inp.pressed:
                self.cls = i
                self.field = 1
        confirm = inp.ui("confirm") if f != "nome" else ("enter" in inp.pressed or "gamepad a" in inp.pressed)
        if confirm:
            if f == "comecar":
                self._start()
            else:
                self.field = min(len(FIELDS) - 1, self.field + 1)
        if "escape" in inp.pressed or "gamepad b" in inp.pressed:
            from .title import TitleScene
            app = self.app
            app.transition(lambda: app.replace(TitleScene(app)))

    def _change(self, f, d):
        self.sfx("ui_move", 0.5)
        if f == "classe":
            self.cls = (self.cls + d) % len(CLASS_ORDER)
        elif f == "pele":
            self.app_["skin"] = (self.app_["skin"] + d) % len(SKIN_NAMES)
        elif f == "cabelo":
            self.app_["hair"] = (self.app_["hair"] + d) % len(HAIR_NAMES)
        elif f == "cor":
            self.app_["hair_color"] = (self.app_["hair_color"] + d) % len(HAIR_COLOR_NAMES)
        elif f == "variante":
            self.app_["variant"] = (self.app_["variant"] + d) % 3

    def _start(self):
        name = self.name.strip() or "Portador"
        char = Character(name, self.class_id, dict(self.app_))
        for r in list(char.runes)[:1]:
            char.equip_rune(r)
        s = Session(char)
        s.slot = self.slot
        s.level, s.spawn = "santuario", "inicio"
        s.quests["q_principal"] = 0
        self.sfx("grace_found")
        from .title import IntroScene
        app = self.app
        app.transition(lambda: app.replace(IntroScene(app, s)), 1.5)

    def draw_ui(self, surf, dt):
        W, H = surf.get_size()
        surf.fill((10, 8, 12, 255))
        for i in range(40):
            x = (i * 53 + int(self.time * 6 * (1 + i % 3))) % W
            y = (H - (i * 31 + int(self.time * 10 * (1 + i % 4))) % H)
            surf.set_at((x, y), (200, 120, 60))
        text(surf, "CRIAÇÃO DO PORTADOR", (W // 2, 8), 15, T.GOLD, "midtop", bold=True)
        cid = self.class_id
        cd = DB.classes[cid]
        # lista de classes
        self._class_rects = []
        lx = 12
        for i, c in enumerate(CLASS_ORDER):
            r = pygame.Rect(lx, 30 + i * 20, 92, 18)
            sel = i == self.cls
            pygame.draw.rect(surf, (40, 30, 30) if sel else (18, 14, 18), r)
            pygame.draw.rect(surf, T.GOLD if sel else (60, 52, 50), r, 1)
            surf.blit(icons.weapon_icon(DB.weapons[DB.classes[c]["weapon"]]["family"]), (r.left + 2, r.top + 1))
            text(surf, DB.classes[c]["name"], (r.left + 20, r.top + 4), 9, T.WHITE if sel else T.TEXT)
            self._class_rects.append(r)
        # prévia
        pv = pygame.Rect(112, 30, 150, 170)
        panel(surf, pv, "dark")
        anims = ["idle", "run", "slash_r", "slash_down", "thrust", "spin", "cast_up"]
        cyc = self.time % 14
        anim = anims[int(cyc / 2) % len(anims)]
        t = (cyc % 2) / 2
        facing = [-90, -45, 0, 45, 90, -90, -45][int(self.time / 2.5) % 7]
        img = self._preview(anim, t if anim not in ("idle", "run") else (self.time * 0.8) % 1.0, facing)
        big = pygame.transform.scale(img, (img.get_width() * 3, img.get_height() * 3))
        surf.blit(big, (pv.centerx - big.get_width() // 2, pv.bottom - big.get_height() - 4))
        # campos
        fx = pv.left
        fy = pv.bottom + 6
        self._rects = []
        labels = [("Nome", self.name + ("_" if FIELDS[self.field] == "nome" and int(self.time * 2) % 2 else "")),
                  ("Classe", cd["name"]), ("Pele", SKIN_NAMES[self.app_["skin"]]), ("Cabelo", HAIR_NAMES[self.app_["hair"]]),
                  ("Cor do cabelo", HAIR_COLOR_NAMES[self.app_["hair_color"]]), ("Variação", f"Estilo {self.app_['variant'] + 1}"),
                  ("", "COMEÇAR A JORNADA")]
        for i, (k, v) in enumerate(labels):
            r = pygame.Rect(fx, fy + i * 16, 150, 15)
            sel = i == self.field
            if sel:
                pygame.draw.rect(surf, (50, 38, 34), r)
                pygame.draw.rect(surf, T.GOLD, r, 1)
            if k:
                text(surf, k, (r.left + 4, r.top + 3), 9, T.MUTED)
                text(surf, ("‹ " + v + " ›") if sel and i > 0 else v, (r.right - 4, r.top + 3), 9, T.WHITE if sel else T.PARCH, "topright")
            else:
                text(surf, v, r.center, 10, T.GOLD if sel else T.PARCH, "center", bold=True)
            self._rects.append(r)
        # informações da classe
        ir = pygame.Rect(pv.right + 8, 30, W - pv.right - 20, H - 50)
        panel(surf, ir)
        y = ir.top + 8
        text(surf, cd["name"], (ir.left + 10, y), 14, T.GOLD, bold=True)
        y += 18
        y += text_block(surf, cd["desc"], ir.left + 10, y, ir.w - 20, 9, T.PARCH) + 2
        y += text_block(surf, "Estilo: " + cd["style"], ir.left + 10, y, ir.w - 20, 9, T.MUTED) + 4
        wd = DB.weapons[cd["weapon"]]
        text(surf, "Arma inicial: " + wd["name"], (ir.left + 10, y), 9, T.TEXT)
        y += 12
        # atributos
        for a in ATTRIBUTES:
            v = cd["attributes"][a]
            text(surf, ATTRIBUTE_NAMES[a], (ir.left + 10, y), 9, T.TEXT)
            bar(surf, (ir.left + 70, y + 2, 80, 5), v / 20.0, (200, 160, 90), border=False)
            text(surf, str(v), (ir.left + 156, y), 9, T.PARCH)
            y += 10
        y += 4
        text(surf, "Habilidades", (ir.left + 10, y), 9, T.GOLD_DIM, bold=True)
        y += 11
        for aid in cd["abilities"] + [cd["ultimate"]]:
            ab = DB.abilities[aid]
            surf.blit(icons.ability_icon(aid, cid, ab["kind"]), (ir.left + 10, y))
            text(surf, ab["name"] + ("  (suprema)" if ab["kind"] == "ultimate" else ""), (ir.left + 30, y + 3), 9, T.PARCH)
            y += 17
        text(surf, "Passivas: " + ", ".join(DB.abilities[p]["name"] for p in cd["passives"]), (ir.left + 10, y), 8, T.MUTED)
        y += 11
        text_block(surf, "Especializações: " + ", ".join(cd.get("specializations", [])), ir.left + 10, y, ir.w - 20, 8, T.MUTED)
        text(surf, "↑/↓ campo • ←/→ alterar • digite o nome • Enter confirmar • Esc voltar", (W // 2, H - 14), 8, T.MUTED, "midtop")
