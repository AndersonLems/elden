"""Menus sobrepostos: pausa, morte, Graça (evolução, árvore, runas, armas/artes, viagem), status, missões,
documentos, técnicas, configurações e controles."""
import math

import pygame

from ..core.data import DB
from ..core import saves
from ..core.settings import QUALITY_NAMES
from ..sim.progression import grace_tree, loadout as loadout_mod
from ..sim.progression.character import Character
from ..sim.stats import ATTRIBUTE_NAMES
from ..sim.combat.moves import INPUT_NAMES
from ..input_map import CONTROLS_HELP, GAMEPAD_HELP
from ..ui.widgets import text, panel, wrap, text_block, bar, ListView, tabs, divider, text_width
from ..ui import icons
from ..ui import theme as T
from .base import Scene


class Overlay(Scene):
    overlay = True
    pauses_below = True

    def dim(self, surf, a=150):
        sh = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        sh.fill((0, 0, 0, a))
        surf.blit(sh, (0, 0))

    def mouse(self):
        m = self.app.input.mouse_pos
        return self.app.canvas.mouse_to_canvas(*m)

    def clicked(self):
        return "left mouse" in self.app.input.pressed

    def back(self):
        return self.inp.ui("cancel") or "right mouse" in self.app.input.pressed


class MenuOverlay(Overlay):
    """Menu vertical simples (opções com rótulo e ação)."""
    title = ""

    def __init__(self, app, options=None, width=200):
        super().__init__(app)
        self.list = ListView(options or [], row_h=16, visible=12)
        self.width = width

    def options(self):
        return self.list.items

    def update(self, dt):
        super().update(dt)
        inp = self.inp
        dx, dy = inp.ui_nav(dt)
        if dy and self.list.move(dy):
            self.sfx("ui_move", 0.5)
        mx, my = self.mouse()
        hov = self.list.mouse(mx, my, inp.scroll) if inp.mouse_moved or self.clicked() else None
        if inp.ui("confirm") or (self.clicked() and hov is not None):
            item = self.list.current()
            enabled = item is not None and item[1] is not None and (len(item) < 3 or item[2])
            if enabled:
                self.sfx("ui_confirm", 0.6)
                item[1]()
            else:
                self.sfx("ui_error", 0.6)
        elif self.back():
            self.sfx("ui_cancel", 0.6)
            self.on_back()

    def on_back(self):
        self.close()

    def draw_ui(self, surf, dt):
        self.dim(surf)
        W, H = surf.get_size()
        n = min(len(self.list.items), self.list.visible)
        h = n * self.list.row_h + 46
        r = pygame.Rect(W // 2 - self.width // 2, H // 2 - h // 2, self.width, h)
        panel(surf, r)
        text(surf, self.title, (r.centerx, r.top + 8), 14, T.GOLD, "midtop", bold=True)
        divider(surf, r.left + 12, r.right - 12, r.top + 28)

        def row(s, item, x, y, w, sel):
            enabled = len(item) < 3 or item[2]
            text(s, item[0], (x + w // 2, y + 2), 11, (T.PARCH if sel else T.TEXT) if enabled else (90, 84, 80), "midtop")
        self.list.draw(surf, r.left + 14, r.top + 36, r.w - 28, row)


# ---------------------------------------------------------------------------- pausa e morte
class PauseMenu(MenuOverlay):
    title = "PAUSA"

    def __init__(self, app, game):
        self.game = game
        opts = [("Continuar", self.close), ("Status do Personagem", lambda: app.push(StatusScreen(app, game.session, game.world.player))),
                ("Técnicas e Combos", lambda: app.push(CombosScreen(app, game.world.player))),
                ("Missões", lambda: app.push(QuestScreen(app, game.session))),
                ("Documentos", lambda: app.push(DocsScreen(app, game.session))),
                ("Controles", lambda: app.push(ControlsScreen(app))),
                ("Configurações", lambda: app.push(SettingsScreen(app))),
                ("Salvar e voltar ao título", self._quit_title), ("Salvar e sair do jogo", self._quit_game)]
        super().__init__(app, opts, 230)

    def _quit_title(self):
        saves.save_session(self.game.session)
        from .title import TitleScene
        app = self.app
        app.transition(lambda: (app.get_scene_view().unload(), app.replace(TitleScene(app))))

    def _quit_game(self):
        saves.save_session(self.game.session)
        self.app.quit()

    def draw_ui(self, surf, dt):
        super().draw_ui(surf, dt)
        s = self.game.session
        W, H = surf.get_size()
        hrs = int(s.playtime // 3600)
        mins = int(s.playtime % 3600 // 60)
        text(surf, f"{s.char.name} — {DB.classes[s.char.class_id]['name']} nível {s.char.level}    Tempo: {hrs}h{mins:02d}    Mortes: {s.deaths}",
             (W // 2, H - 20), 9, T.MUTED, "midtop")


class DeathOverlay(Overlay):
    def __init__(self, app, game):
        super().__init__(app)
        self.game = game

    def update(self, dt):
        super().update(dt)
        if self.time > 4.0 or (self.time > 1.2 and (self.inp.ui("confirm") or self.clicked())):
            self.close()
            self.game.respawn()

    def draw_ui(self, surf, dt):
        W, H = surf.get_size()
        a = min(1.0, self.time * 0.8)
        band = pygame.Surface((W, 60), pygame.SRCALPHA)
        band.fill((0, 0, 0, int(170 * a)))
        surf.blit(band, (0, H // 2 - 34))
        text(surf, "VOCÊ PERECEU", (W // 2, H // 2 - 16), 26, (170, 20, 26), "midtop", alpha=int(255 * a), bold=True)
        lg = self.game.session.char.grace
        if lg > 0 and self.time > 1.0:
            text(surf, f"{lg} de Graça ficaram onde você caiu.", (W // 2, H // 2 + 20), 10, T.PARCH, "midtop", alpha=int(255 * min(1, self.time - 1)))


# ---------------------------------------------------------------------------- Graça
class GraceMenu(MenuOverlay):
    def __init__(self, app, game, grace_pid):
        self.game = game
        self.grace_pid = grace_pid
        self.session = game.session
        g = self.session.graces.get(grace_pid, {})
        self.title = g.get("name", "Graça")
        super().__init__(app, [], 250)
        self._build()

    def _build(self):
        c = self.session.char
        cost = c.next_level_cost()
        app = self.app
        p = self.game.world.player
        opts = [(f"Evoluir: nível {c.level + 1}  (custo {cost} Graça)", self._level_up, c.grace >= cost),
                (f"Árvore da Graça  ({c.points_available} pontos)", lambda: app.push(TreeScreen(app, self.session, p))),
                ("Runas", lambda: app.push(RunesScreen(app, self.session, p))),
                ("Armas e Artes de Combate", lambda: app.push(EquipScreen(app, self.session, p))),
                ("Viajar", lambda: app.push(TravelScreen(app, self))),
                ("Técnicas e Combos", lambda: app.push(CombosScreen(app, p))),
                ("Status", lambda: app.push(StatusScreen(app, self.session, p))),
                ("Levantar-se", self._leave)]
        self.list.set_items(opts)

    def resume(self):
        self._build()

    def _level_up(self):
        c = self.session.char
        if c.level_up():
            self.sfx("level_up")
            self.game.world.player.apply_loadout()
            self.game.world.player.refill()
        self._build()

    def _leave(self, travel=None):
        self.close()
        self.game.end_rest(self.grace_pid, travel)

    def on_back(self):
        self._leave()

    def draw_ui(self, surf, dt):
        super().draw_ui(surf, dt)
        W, H = surf.get_size()
        c = self.session.char
        r = pygame.Rect(12, H - 70, 190, 58)
        panel(surf, r, "dark")
        text(surf, f"Nível {c.level}", (r.left + 8, r.top + 6), 11, T.GOLD, bold=True)
        text(surf, f"Graça: {c.grace}", (r.left + 8, r.top + 20), 10, (240, 210, 140))
        text(surf, f"Próximo nível: {c.next_level_cost()}", (r.left + 8, r.top + 32), 9, T.MUTED)
        text(surf, f"Pontos de Graça livres: {c.points_available}", (r.left + 8, r.top + 43), 9, T.PARCH)


class TravelScreen(MenuOverlay):
    title = "VIAJAR"

    def __init__(self, app, grace_menu):
        self.gm = grace_menu
        s = grace_menu.session
        opts = []
        for pid, g in s.graces.items():
            lvl = DB.levels.get(g["level"], {}).get("name", g["level"])
            opts.append((f"{g['name']}  ({lvl})", lambda pid=pid, lv=g["level"]: self._go(lv, pid)))
        opts.append(("Santuário da Última Chama", lambda: self._go("santuario", "graca_santuario")))
        super().__init__(app, opts, 320)

    def _go(self, level, pid):
        self.close()
        self.gm._leave((level, pid))


class TreeScreen(Overlay):
    full = True

    PATHS = ["corpo", "espirito", "ruina", "classe"]

    def __init__(self, app, session, player):
        super().__init__(app)
        self.s = session
        self.p = player
        self.tab = 0
        self.cur = None
        self.confirming = None
        self.msg = ""
        self.msg_t = 0.0
        self._select_first()

    def nodes_in_tab(self):
        path = self.PATHS[self.tab]
        out = []
        for nid, n in DB.tree["nodes"].items():
            if n.get("path") != path:
                continue
            if not grace_tree.node_visible(self.s.char, nid):
                continue
            out.append(nid)
        return out

    def _select_first(self):
        ns = self.nodes_in_tab()
        self.cur = min(ns, key=lambda n: (DB.tree["nodes"][n]["pos"][1], DB.tree["nodes"][n]["pos"][0])) if ns else None

    def _move(self, dx, dy):
        ns = self.nodes_in_tab()
        if not ns or self.cur is None:
            return
        cx, cy = DB.tree["nodes"][self.cur]["pos"]
        best, bd = None, 1e9
        for n in ns:
            if n == self.cur:
                continue
            x, y = DB.tree["nodes"][n]["pos"]
            vx, vy = x - cx, y - cy
            if dx and (vx * dx <= 0):
                continue
            if dy and (vy * dy <= 0):
                continue
            d = abs(vx) + abs(vy) * 1.2 + (abs(vy) * 3 if dx else abs(vx) * 3)
            if d < bd:
                best, bd = n, d
        if best:
            self.cur = best
            self.sfx("ui_move", 0.5)

    def update(self, dt):
        super().update(dt)
        inp = self.inp
        self.msg_t -= dt
        if self.confirming:
            if inp.ui("confirm") or self.clicked():
                self._unlock(self.confirming)
                self.confirming = None
            elif self.back():
                self.confirming = None
            return
        if inp.ui("prev_tab"):
            self.tab = (self.tab - 1) % 4
            self._select_first()
            self.sfx("ui_move", 0.6)
        if inp.ui("next_tab"):
            self.tab = (self.tab + 1) % 4
            self._select_first()
            self.sfx("ui_move", 0.6)
        dx, dy = inp.ui_nav(dt)
        if dx or dy:
            self._move(dx, dy)
        mx, my = self.mouse()
        for r, nid in getattr(self, "_hit", []):
            if r.collidepoint(mx, my) and (inp.mouse_moved or self.clicked()):
                self.cur = nid
                if self.clicked():
                    self._try(nid)
        for i, r in enumerate(getattr(self, "_tabs", [])):
            if r.collidepoint(mx, my) and self.clicked():
                self.tab = i
                self._select_first()
        if inp.ui("confirm") and self.cur:
            self._try(self.cur)
        elif self.back():
            self.p.apply_loadout()
            self.close()

    def _try(self, nid):
        prob = grace_tree.unlock_problem(self.s.char, nid)
        if prob:
            self.msg, self.msg_t = prob, 2.0
            self.sfx("ui_error")
            return
        n = DB.tree["nodes"][nid]
        if any(e.get("type") == "corruption" for e in n.get("effects", [])) or n.get("exclusive"):
            self.confirming = nid
            return
        self._unlock(nid)

    def _unlock(self, nid):
        if grace_tree.unlock(self.s.char, nid):
            self.sfx("level_up", 0.8)
            self.p.apply_loadout()
            self.msg, self.msg_t = f"Desbloqueado: {DB.tree['nodes'][nid]['name']}", 2.0

    def draw_ui(self, surf, dt):
        self.dim(surf, 190)
        W, H = surf.get_size()
        c = self.s.char
        paths = DB.tree["paths"]
        labels = [paths[p]["name"] for p in self.PATHS]
        cols = [tuple(int(v * 255) for v in paths[p]["color"]) for p in self.PATHS]
        text(surf, "ÁRVORE DA GRAÇA", (W // 2, 8), 15, T.GOLD, "midtop", bold=True)
        self._tabs = tabs(surf, 16, 30, labels, self.tab, 10, cols)
        text(surf, f"Pontos livres: {c.points_available}", (W - 16, 32), 11, T.PARCH, "topright", bold=True)
        # corrupção
        text(surf, f"Corrupção: {int(c.corruption)}%", (W - 16, 46), 9, (220, 90, 110), "topright")
        bar(surf, (W - 116, 58, 100, 4), c.corruption / 100, (180, 30, 60), border=False)
        area = pygame.Rect(16, 64, int(W * 0.55), H - 84)
        panel(surf, area, "dark")
        col = cols[self.tab]
        ns = self.nodes_in_tab()
        nodes = DB.tree["nodes"]
        cw = area.w / 3
        rh = (area.h - 20) / 6
        pos = {}
        for nid in ns:
            x, y = nodes[nid]["pos"]
            pos[nid] = (int(area.left + cw * (x + 0.5)), int(area.top + 14 + rh * (y + 0.5)))
        for nid in ns:
            for req in nodes[nid].get("requires", []):
                if req in pos:
                    a, b = pos[req], pos[nid]
                    lc = col if req in c.nodes else (60, 54, 56)
                    pygame.draw.line(surf, lc, a, b, 1)
        self._hit = []
        for nid in ns:
            owned = nid in c.nodes
            avail = grace_tree.unlock_problem(c, nid) is None
            ic = icons.node_icon(nodes[nid], col, owned, avail)
            x, y = pos[nid]
            surf.blit(ic, (x - 9, y - 9))
            r = pygame.Rect(x - 10, y - 10, 20, 20)
            self._hit.append((r, nid))
            if nid == self.cur:
                pygame.draw.rect(surf, T.WHITE, r.inflate(4, 4), 1)
        # detalhes
        info = pygame.Rect(area.right + 8, 64, W - area.right - 24, H - 84)
        panel(surf, info)
        if self.cur:
            n = nodes[self.cur]
            y = info.top + 8
            text(surf, n["name"], (info.left + 8, y), 11, col, bold=True)
            y += 16
            prob = grace_tree.unlock_problem(c, self.cur)
            st = "DESBLOQUEADO" if self.cur in c.nodes else ("Disponível" if prob is None else prob)
            text(surf, f"Custo: {n.get('cost', 1)}   {st}", (info.left + 8, y), 9,
                 (150, 230, 150) if self.cur in c.nodes else (T.PARCH if prob is None else (220, 140, 120)))
            y += 14
            y += text_block(surf, n.get("desc", ""), info.left + 8, y, info.w - 16, 10, T.TEXT)
            reqs = [nodes[r]["name"] for r in n.get("requires", [])]
            if reqs:
                y += 4
                text_block(surf, "Requer: " + ", ".join(reqs), info.left + 8, y, info.w - 16, 9, T.MUTED)
            corr = sum(e.get("amount", 0) for e in n.get("effects", []) if e.get("type") == "corruption")
            if corr:
                text(surf, f"+{corr} de corrupção", (info.left + 8, info.bottom - 30), 9, (230, 90, 110))
        text(surf, "Q/PgDn: trocar caminho  •  Enter: desbloquear  •  Esc: voltar", (W // 2, H - 14), 8, T.MUTED, "midtop")
        if self.msg_t > 0:
            text(surf, self.msg, (W // 2, H - 26), 10, (240, 200, 140), "midtop")
        if self.confirming:
            n = nodes[self.confirming]
            r = pygame.Rect(W // 2 - 150, H // 2 - 34, 300, 68)
            panel(surf, r, "red")
            text_block(surf, f"Desbloquear {n['name']}?", r.left + 10, r.top + 8, r.w - 20, 11, T.PARCH, align="center")
            warn = "Este caminho aumenta sua corrupção." if any(e.get("type") == "corruption" for e in n.get("effects", [])) else \
                "Só é possível escolher uma especialização."
            text_block(surf, warn, r.left + 10, r.top + 26, r.w - 20, 9, (240, 160, 150), align="center")
            text(surf, "Enter: confirmar   Esc: cancelar", (r.centerx, r.bottom - 14), 8, T.MUTED, "midtop")


STAT_ROWS = [("hp_max", "Vida", 0), ("fp_max", "Foco", 0), ("posture_max", "Postura", 0), ("atk", "Poder de ataque", 0),
             ("crit_chance", "Crítico", 1), ("lifesteal", "Roubo de vida", 1), ("def_flat", "Defesa", 0),
             ("dodge_charges", "Esquivas", 0), ("speed_mult", "Velocidade", 1), ("attack_speed", "Vel. de ataque", 1)]


def short_rune(name):
    for pre in ("Runa do ", "Runa da ", "Runa dos ", "Runa das ", "Runa de ", "Runa "):
        if name.startswith(pre):
            return name[len(pre):]
    return name


def stat_snapshot(char):
    L = loadout_mod.compute(char)
    m = L.mods
    return {"hp_max": L.hp_max, "fp_max": L.fp_max, "posture_max": L.posture_max, "atk": sum(L.weapon_power.values()),
            "crit_chance": 0.05 + m.get("crit_chance", 0), "lifesteal": m.get("lifesteal", 0), "def_flat": L.def_flat + m.get("def_flat", 0),
            "dodge_charges": L.dodge_charges, "speed_mult": m.get("speed_mult", 0), "attack_speed": m.get("attack_speed", 0)}


def draw_diff(surf, x, y, before, after):
    for key, name, pct in STAT_ROWS:
        a, b = before[key], after[key]
        if abs(a - b) < 1e-6:
            continue
        fmt = (lambda v: f"{v * 100:.0f}%") if pct else (lambda v: f"{v:.0f}")
        col = (140, 230, 140) if b > a else (230, 120, 110)
        text(surf, f"{name}: {fmt(a)} → {fmt(b)}", (x, y), 9, col)
        y += 11
    return y


class RunesScreen(Overlay):
    full = True

    def __init__(self, app, session, player):
        super().__init__(app)
        self.s = session
        self.p = player
        self.cat = 0
        self.cats = ["todas"] + list(T.CATEGORY_NAMES)
        self.focus = 1           # 0 = espaços equipados, 1 = coleção
        self.slots = ListView([], 18, 5)
        self.coll = ListView([], 16, 12)
        self.msg = ""
        self.msg_t = 0
        self._refresh()

    def _refresh(self):
        c = self.s.char
        self.slots.set_items([c.runes_equipped[i] if i < len(c.runes_equipped) else None for i in range(c.rune_slots)])
        cat = self.cats[self.cat]
        items = [r for r in c.runes if cat == "todas" or DB.runes[r]["category"] == cat]
        items.sort(key=lambda r: (DB.runes[r]["category"], {"comum": 0, "rara": 1, "lendaria": 2}[DB.runes[r]["rarity"]]))
        self.coll.set_items(items)

    def update(self, dt):
        super().update(dt)
        inp = self.inp
        self.msg_t -= dt
        if inp.ui("prev_tab"):
            self.cat = (self.cat - 1) % len(self.cats)
            self._refresh()
        if inp.ui("next_tab"):
            self.cat = (self.cat + 1) % len(self.cats)
            self._refresh()
        dx, dy = inp.ui_nav(dt)
        if dx:
            self.focus = 0 if dx < 0 else 1
            self.sfx("ui_move", 0.4)
        lst = self.slots if self.focus == 0 else self.coll
        if dy:
            lst.move(dy)
            self.sfx("ui_move", 0.4)
        mx, my = self.mouse()
        if inp.mouse_moved or self.clicked() or inp.scroll:
            if self.slots.mouse(mx, my) is not None:
                self.focus = 0
            elif self.coll.mouse(mx, my, inp.scroll) is not None:
                self.focus = 1
        c = self.s.char
        if inp.ui("confirm") or self.clicked():
            if self.focus == 1:
                rid = self.coll.current()
                if rid:
                    if rid in c.runes_equipped:
                        c.unequip_rune(rid)
                    else:
                        repl = self.slots.current() if len(c.runes_equipped) >= c.rune_slots else None
                        prob = c.rune_problem(rid, repl)
                        if prob:
                            self.msg, self.msg_t = prob, 2.0
                            self.sfx("ui_error")
                        else:
                            c.equip_rune(rid, repl)
                            self.sfx("ui_confirm")
            else:
                rid = self.slots.current()
                if rid:
                    c.unequip_rune(rid)
                    self.sfx("ui_cancel")
            self.p.apply_loadout()
            self._refresh()
        elif inp.ui("extra") and self.focus == 0 and self.slots.current():
            c.unequip_rune(self.slots.current())
            self.p.apply_loadout()
            self._refresh()
        elif self.back():
            self.close()

    def draw_ui(self, surf, dt):
        self.dim(surf, 190)
        W, H = surf.get_size()
        c = self.s.char
        text(surf, "RUNAS", (W // 2, 8), 15, T.GOLD, "midtop", bold=True)
        labels = ["Todas"] + [T.CATEGORY_NAMES[k] for k in list(T.CATEGORY_NAMES)]
        tabs(surf, 12, 28, labels, self.cat, 8)
        left = pygame.Rect(12, 48, 170, H - 66)
        panel(surf, left, "dark")
        text(surf, f"Equipadas ({len(c.runes_equipped)}/{c.rune_slots})", (left.left + 8, left.top + 6), 10, T.PARCH, bold=True)

        def slot_row(s, rid, x, y, w, sel):
            if rid:
                rd = DB.runes[rid]
                s.blit(icons.rune_icon(rd["category"], rd["rarity"]), (x + 2, y + 1))
                text(s, short_rune(rd["name"]), (x + 22, y + 4), 9, T.RARITY[rd["rarity"]])
            else:
                text(s, "— vazio —", (x + 22, y + 4), 9, T.MUTED)
        self.slots.draw(surf, left.left + 8, left.top + 22, left.w - 16, slot_row)
        if self.focus == 0:
            pygame.draw.rect(surf, T.GOLD, left, 1)
        mid = pygame.Rect(left.right + 6, 48, 190, H - 66)
        panel(surf, mid, "dark")

        def coll_row(s, rid, x, y, w, sel):
            rd = DB.runes[rid]
            s.blit(icons.rune_icon(rd["category"], rd["rarity"]), (x + 2, y))
            col = T.RARITY[rd["rarity"]]
            text(s, short_rune(rd["name"]), (x + 22, y + 3), 9, col)
            if rid in c.runes_equipped:
                text(s, "E", (x + w - 4, y + 3), 9, (150, 230, 150), "topright", bold=True)
        self.coll.draw(surf, mid.left + 8, mid.top + 8, mid.w - 16, coll_row)
        if self.focus == 1:
            pygame.draw.rect(surf, T.GOLD, mid, 1)
        info = pygame.Rect(mid.right + 6, 48, W - mid.right - 18, H - 66)
        panel(surf, info)
        rid = (self.slots.current() if self.focus == 0 else self.coll.current())
        if rid:
            rd = DB.runes[rid]
            y = info.top + 8
            text(surf, rd["name"], (info.left + 8, y), 11, T.RARITY[rd["rarity"]], bold=True)
            y += 15
            text(surf, f"{T.CATEGORY_NAMES[rd['category']]} • {T.RARITY_NAMES[rd['rarity']]}", (info.left + 8, y), 9,
                 T.CATEGORY_COLORS[rd["category"]])
            y += 14
            y += text_block(surf, rd["desc"], info.left + 8, y, info.w - 16, 10, T.TEXT) + 6
            if rd.get("exclusive"):
                y += text_block(surf, "Exclusiva: não combina com outras runas do mesmo pacto.", info.left + 8, y, info.w - 16, 8, T.MUTED)
            # comparação
            before = stat_snapshot(c)
            test = Character.from_dict(c.to_dict())
            test._flags = c._flags
            if rid in test.runes_equipped:
                test.unequip_rune(rid)
                label = "Ao remover:"
            else:
                repl = self.slots.current() if len(test.runes_equipped) >= test.rune_slots else None
                test.equip_rune(rid, repl)
                label = "Ao equipar:"
            after = stat_snapshot(test)
            text(surf, label, (info.left + 8, y + 4), 9, T.GOLD_DIM)
            yy = draw_diff(surf, info.left + 8, y + 16, before, after)
            if yy == y + 16:
                text(surf, "(efeito de gatilho, sem mudança direta)", (info.left + 8, yy), 8, T.MUTED)
        text(surf, "Q/PgDn: categoria • ←/→: espaços/coleção • Enter: equipar/remover • Esc: voltar", (W // 2, H - 14), 8, T.MUTED, "midtop")
        if self.msg_t > 0:
            text(surf, self.msg, (W // 2, H - 26), 10, (240, 160, 140), "midtop")


def weapon_desc(wid, level=0):
    w = DB.weapons[wid]
    parts = [f"{T.ELEMENT_NAMES[k]} {v * (1 + 0.09 * level):.0f}" for k, v in w.get("base", {}).items()]
    sc = []
    for a, k in w.get("scaling", {}).items():
        letter = "S" if k >= 0.8 else "A" if k >= 0.6 else "B" if k >= 0.4 else "C" if k >= 0.25 else "D"
        sc.append(f"{ATTRIBUTE_NAMES[a][:3]} {letter}")
    return ", ".join(parts), " ".join(sc)


class EquipScreen(Overlay):
    full = True

    def __init__(self, app, session, player):
        super().__init__(app)
        self.s = session
        self.p = player
        self.focus = 0
        self.weapons = ListView([], 16, 10)
        self.arts = ListView([], 16, 10)
        self._refresh()

    def _refresh(self):
        c = self.s.char
        self.weapons.set_items(list(c.weapons))
        self.arts.set_items([a for a in c.arts if c.art_compatible(a)])

    def update(self, dt):
        super().update(dt)
        inp = self.inp
        dx, dy = inp.ui_nav(dt)
        if dx:
            self.focus = 0 if dx < 0 else 1
        lst = self.weapons if self.focus == 0 else self.arts
        if dy:
            lst.move(dy)
            self.sfx("ui_move", 0.4)
        mx, my = self.mouse()
        if inp.mouse_moved or self.clicked():
            if self.weapons.mouse(mx, my) is not None:
                self.focus = 0
            elif self.arts.mouse(mx, my) is not None:
                self.focus = 1
        c = self.s.char
        if inp.ui("confirm") or self.clicked():
            if self.focus == 0 and self.weapons.current():
                c.equip_weapon(self.weapons.current())
                self.sfx("ui_confirm")
            elif self.focus == 1 and self.arts.current():
                c.equip_art(self.arts.current())
                self.sfx("ui_confirm")
            self.p.apply_loadout()
            self._refresh()
        elif self.back():
            self.close()

    def draw_ui(self, surf, dt):
        self.dim(surf, 190)
        W, H = surf.get_size()
        c = self.s.char
        text(surf, "ARMAS E ARTES DE COMBATE", (W // 2, 8), 15, T.GOLD, "midtop", bold=True)
        l = pygame.Rect(12, 30, 200, H - 48)
        panel(surf, l, "dark")
        text(surf, "Armas", (l.left + 8, l.top + 6), 10, T.PARCH, bold=True)

        def wrow(s, wid, x, y, w, sel):
            wd = DB.weapons[wid]
            s.blit(icons.weapon_icon(wd["family"]), (x + 1, y))
            lv = c.weapon_level(wid)
            text(s, wd["name"] + (f" +{lv}" if lv else ""), (x + 20, y + 3), 9, T.RARITY.get(wd.get("rarity", "comum")))
            if wid == c.weapon:
                text(s, "E", (x + w - 4, y + 3), 9, (150, 230, 150), "topright", bold=True)
        self.weapons.draw(surf, l.left + 8, l.top + 22, l.w - 16, wrow)
        if self.focus == 0:
            pygame.draw.rect(surf, T.GOLD, l, 1)
        m = pygame.Rect(l.right + 6, 30, 180, H - 48)
        panel(surf, m, "dark")
        text(surf, "Artes compatíveis", (m.left + 8, m.top + 6), 10, T.PARCH, bold=True)

        def arow(s, aid, x, y, w, sel):
            text(s, DB.arts[aid]["name"], (x + 4, y + 3), 9, (210, 180, 240))
            if aid == c.art_for():
                text(s, "E", (x + w - 4, y + 3), 9, (150, 230, 150), "topright", bold=True)
        self.arts.draw(surf, m.left + 8, m.top + 22, m.w - 16, arow)
        if self.focus == 1:
            pygame.draw.rect(surf, T.GOLD, m, 1)
        info = pygame.Rect(m.right + 6, 30, W - m.right - 18, H - 48)
        panel(surf, info)
        y = info.top + 8
        if self.focus == 0 and self.weapons.current():
            wid = self.weapons.current()
            wd = DB.weapons[wid]
            fam = DB.families[wd["family"]]
            text(surf, wd["name"], (info.left + 8, y), 11, T.RARITY.get(wd.get("rarity", "comum")), bold=True)
            y += 15
            text(surf, fam["name"], (info.left + 8, y), 9, T.GOLD_DIM)
            y += 13
            dmg, sc = weapon_desc(wid, c.weapon_level(wid))
            text(surf, "Dano: " + dmg, (info.left + 8, y), 9, T.TEXT)
            y += 11
            text(surf, "Escala: " + sc, (info.left + 8, y), 9, T.TEXT)
            y += 14
            y += text_block(surf, wd.get("desc", ""), info.left + 8, y, info.w - 16, 9, T.PARCH) + 4
            y += text_block(surf, fam.get("desc", ""), info.left + 8, y, info.w - 16, 9, T.MUTED) + 4
            if wd.get("art"):
                text(surf, "Arte padrão: " + DB.arts[wd["art"]]["name"], (info.left + 8, y), 9, (210, 180, 240))
        elif self.focus == 1 and self.arts.current():
            ad = DB.arts[self.arts.current()]
            text(surf, ad["name"], (info.left + 8, y), 11, (210, 180, 240), bold=True)
            y += 16
            text(surf, f"Foco: {ad['fp']}   Recarga: {ad['cd']}s", (info.left + 8, y), 9, T.TEXT)
            y += 14
            text_block(surf, ad["desc"], info.left + 8, y, info.w - 16, 10, T.PARCH)
        text(surf, "←/→: lista • Enter: equipar • Esc: voltar", (W // 2, H - 14), 8, T.MUTED, "midtop")


# ---------------------------------------------------------------------------- consulta
class StatusScreen(Overlay):
    full = True

    def __init__(self, app, session, player):
        super().__init__(app)
        self.s = session
        self.p = player

    def update(self, dt):
        super().update(dt)
        if self.back() or self.inp.ui("confirm"):
            self.close()

    def draw_ui(self, surf, dt):
        self.dim(surf, 190)
        W, H = surf.get_size()
        c = self.s.char
        p = self.p
        L = p.L
        r = pygame.Rect(20, 16, W - 40, H - 32)
        panel(surf, r)
        text(surf, f"{c.name}", (r.left + 12, r.top + 8), 14, T.GOLD, bold=True)
        text(surf, f"{DB.classes[c.class_id]['name']} • Nível {c.level} • Graça {c.grace} (total {c.grace_total})", (r.left + 12, r.top + 26), 9, T.PARCH)
        y = r.top + 44
        text(surf, "Atributos", (r.left + 12, y), 10, T.GOLD_DIM, bold=True)
        y += 14
        for a, v in L.attrs.items():
            text(surf, ATTRIBUTE_NAMES[a], (r.left + 14, y), 10, T.TEXT)
            text(surf, str(v), (r.left + 110, y), 10, T.PARCH, "topright")
            y += 12
        x2 = r.left + 140
        y = r.top + 44
        text(surf, "Combate", (x2, y), 10, T.GOLD_DIM, bold=True)
        y += 14
        st = p.stats
        rows = [("Vida", f"{p.hp:.0f}/{p.max_hp:.0f}"), ("Foco", f"{p.fp:.0f}/{p.max_fp:.0f}"), ("Postura", f"{p.max_posture:.0f}"),
                ("Ataque (arma)", " + ".join(f"{v:.0f}" for v in L.weapon_power.values())),
                ("Magia (Int/Fé)", f"{L.spell_power['intelecto']:.0f} / {L.spell_power['fe']:.0f}"),
                ("Defesa", f"{st.get('def_flat'):.1f}"), ("Crítico", f"{(0.05 + st.get('crit_chance')) * 100:.0f}%"),
                ("Roubo de vida", f"{st.get('lifesteal') * 100:.1f}%"), ("Cargas de esquiva", str(p.max_dodges)),
                ("Frascos", f"{c.flasks_hp} Brasa / {c.flasks_fp} Éter"), ("Cura do frasco", f"{L.flask_heal * 100:.0f}%")]
        for k, v in rows:
            text(surf, k, (x2, y), 9, T.TEXT)
            text(surf, v, (x2 + 160, y), 9, T.PARCH, "topright")
            y += 11
        x3 = x2 + 180
        y = r.top + 44
        text(surf, "Resistências", (x3, y), 10, T.GOLD_DIM, bold=True)
        y += 14
        for el, name in T.ELEMENT_NAMES.items():
            v = st.get("res_" + el)
            text(surf, name, (x3, y), 9, T.ELEMENT_COLORS[el])
            text(surf, f"{v * 100:+.0f}%", (x3 + 90, y), 9, T.PARCH, "topright")
            y += 11
        y += 6
        text(surf, "Corrupção", (x3, y), 10, (220, 90, 110), bold=True)
        y += 13
        bar(surf, (x3, y, 120, 5), c.corruption / 100, (180, 30, 60))
        y += 9
        tier_desc = ["Pura: a Graça arde limpa.", "Manchada: a Ruína sussurra.", "Profana: dano de Ruína maior, curas mais fracas.",
                     "Abismal: poder enorme, corpo à beira do colapso."][c.corruption_tier]
        text_block(surf, tier_desc, x3, y, W - x3 - 30, 9, T.MUTED)
        y = r.bottom - 52
        text(surf, f"Purificados: {len(c.purified)}   Absorvidos: {len(c.absorbed)}   Fragmentos do Ciclo: {len(c.cycle_fragments)}/5",
             (r.left + 12, y), 9, T.PARCH)
        text(surf, "Passivas: " + ", ".join(DB.abilities[a]["name"] for a in DB.classes[c.class_id]["passives"]), (r.left + 12, y + 12), 9, T.TEXT)
        text(surf, "Runas: " + (", ".join(DB.runes[x]["name"] for x in c.runes_equipped) or "nenhuma"), (r.left + 12, y + 24), 9, T.TEXT)


class QuestScreen(Overlay):
    full = True

    def __init__(self, app, session):
        super().__init__(app)
        self.s = session

    def update(self, dt):
        super().update(dt)
        if self.back() or self.inp.ui("confirm"):
            self.close()

    def draw_ui(self, surf, dt):
        self.dim(surf, 190)
        W, H = surf.get_size()
        r = pygame.Rect(40, 20, W - 80, H - 40)
        panel(surf, r)
        text(surf, "MISSÕES", (r.centerx, r.top + 8), 14, T.GOLD, "midtop", bold=True)
        y = r.top + 32
        for qid, name, stage, done in self.s.active_quests():
            text(surf, name, (r.left + 14, y), 11, (150, 220, 150) if done else T.GOLD, bold=True)
            y += 13
            y += text_block(surf, stage, r.left + 20, y, r.w - 40, 9, T.MUTED if done else T.TEXT) + 6
            if y > r.bottom - 20:
                break


class DocsScreen(Overlay):
    full = True

    def __init__(self, app, session):
        super().__init__(app)
        self.s = session
        self.list = ListView(list(session.docs), 14, 16)
        self.reading = False

    def update(self, dt):
        super().update(dt)
        inp = self.inp
        dx, dy = inp.ui_nav(dt)
        if dy:
            self.list.move(dy)
        mx, my = self.mouse()
        if inp.mouse_moved or inp.scroll:
            self.list.mouse(mx, my, inp.scroll)
        if self.back():
            self.close()

    def draw_ui(self, surf, dt):
        self.dim(surf, 190)
        W, H = surf.get_size()
        l = pygame.Rect(16, 16, 190, H - 32)
        panel(surf, l, "dark")
        text(surf, "DOCUMENTOS", (l.centerx, l.top + 6), 11, T.GOLD, "midtop", bold=True)

        def row(s, did, x, y, w, sel):
            text(s, DB.lore[did]["title"][:30], (x + 4, y + 2), 9, T.PARCH if sel else T.TEXT)
        self.list.draw(surf, l.left + 8, l.top + 24, l.w - 16, row)
        r = pygame.Rect(l.right + 8, 16, W - l.right - 24, H - 32)
        panel(surf, r)
        did = self.list.current()
        if did:
            d = DB.lore[did]
            text_block(surf, d["title"], r.left + 10, r.top + 10, r.w - 20, 11, T.GOLD)
            text_block(surf, d["text"], r.left + 10, r.top + 34, r.w - 20, 10, T.PARCH, line_h=13)
        else:
            text(surf, "Nenhum documento encontrado ainda.", (r.centerx, r.centery), 10, T.MUTED, "center")


class CombosScreen(Overlay):
    full = True

    def __init__(self, app, player):
        super().__init__(app)
        self.p = player
        ms = player.active_moveset
        routes = ms.routes(6)
        self.rows = []
        for r in routes:
            start = r[0].strip("[]")
            names = [DB.moves[m].get("name", m) for m in r[1:]]
            self.rows.append((INPUT_NAMES.get(start, start), names))
        self.list = ListView(self.rows, 13, 18)

    def update(self, dt):
        super().update(dt)
        dx, dy = self.inp.ui_nav(dt)
        if dy:
            self.list.move(dy)
        mx, my = self.mouse()
        if self.inp.mouse_moved or self.inp.scroll:
            self.list.mouse(mx, my, self.inp.scroll)
        if self.back():
            self.close()

    def draw_ui(self, surf, dt):
        self.dim(surf, 190)
        W, H = surf.get_size()
        r = pygame.Rect(16, 16, W - 32, H - 32)
        panel(surf, r)
        text(surf, "TÉCNICAS E COMBOS", (r.centerx, r.top + 6), 13, T.GOLD, "midtop", bold=True)
        fam = DB.families[self.p.L.family]["name"]
        text(surf, f"{fam}" + ("  (forma bestial)" if self.p.transformed else ""), (r.centerx, r.top + 22), 9, T.MUTED, "midtop")

        def row(s, item, x, y, w, sel):
            start, names = item
            text(s, start, (x + 4, y + 1), 9, T.GOLD_DIM)
            text(s, " → ".join(names)[:110], (x + 110, y + 1), 9, T.PARCH if sel else T.TEXT)
        self.list.draw(surf, r.left + 12, r.top + 38, r.w - 30, row)
        text(surf, "Combos mudam com a árvore de Graça (TÉCNICAS) e com runas.", (r.centerx, r.bottom - 14), 8, T.MUTED, "midtop")


class SettingsScreen(MenuOverlay):
    title = "CONFIGURAÇÕES"

    def __init__(self, app):
        super().__init__(app, [], 300)
        self._build()

    def _build(self):
        s = self.app.settings
        q = s.get("quality", "alta")
        opts = [(f"Qualidade gráfica: {QUALITY_NAMES[q]}", self._quality),
                (f"Tela cheia: {'Sim' if s.get('fullscreen') else 'Não'}", self._fullscreen),
                (f"Volume geral: {int(s.get('master', 0.8) * 100)}%", lambda: self._vol("master")),
                (f"Música: {int(s.get('music', 0.6) * 100)}%", lambda: self._vol("music")),
                (f"Efeitos: {int(s.get('sfx', 0.8) * 100)}%", lambda: self._vol("sfx")),
                (f"Tremor de câmera: {int(s.get('shake', 1.0) * 100)}%", self._shake),
                (f"Números de dano: {'Sim' if s.get('damage_numbers', True) else 'Não'}", lambda: self._toggle("damage_numbers")),
                (f"Mostrar FPS: {'Sim' if s.get('show_fps') else 'Não'}", lambda: self._toggle("show_fps")),
                (f"Hitboxes (depuração): {'Sim' if s.get('hitboxes') else 'Não'}", lambda: self._toggle("hitboxes")),
                ("Voltar", self.close)]
        sel = self.list.sel
        self.list.set_items(opts)
        self.list.sel = sel

    def _quality(self):
        order = ["baixa", "media", "alta", "ultra"]
        q = self.app.settings.get("quality", "alta")
        self.app.apply_quality(order[(order.index(q) + 1) % 4])
        self._build()

    def _fullscreen(self):
        self.app.set_fullscreen(not self.app.settings.get("fullscreen"))
        self._build()

    def _vol(self, k):
        v = self.app.settings.get(k, 0.8)
        v = round((v + 0.1) % 1.1, 2)
        self.app.settings[k] = v
        self._build()

    def _shake(self):
        v = self.app.settings.get("shake", 1.0)
        v = {1.0: 0.5, 0.5: 0.0, 0.0: 1.0}.get(v, 1.0)
        self.app.settings["shake"] = v
        if self.app.scene_view:
            self.app.scene_view.camera.strength = v
        self._build()

    def _toggle(self, k):
        self.app.settings[k] = not self.app.settings.get(k, False)
        self._build()

    def exit(self):
        self.app.settings.save()


class ControlsScreen(Overlay):
    full = True

    def update(self, dt):
        super().update(dt)
        if self.back() or self.inp.ui("confirm"):
            self.close()

    def draw_ui(self, surf, dt):
        self.dim(surf, 200)
        W, H = surf.get_size()
        r = pygame.Rect(30, 14, W - 60, H - 28)
        panel(surf, r)
        text(surf, "CONTROLES", (r.centerx, r.top + 6), 13, T.GOLD, "midtop", bold=True)
        y = r.top + 26
        for k, v in CONTROLS_HELP:
            text(surf, k, (r.left + 120, y), 9, T.GOLD, "topright")
            text(surf, v, (r.left + 130, y), 9, T.TEXT)
            y += 12
        y += 4
        text(surf, "Controle (gamepad)", (r.left + 14, y), 10, T.GOLD_DIM, bold=True)
        y += 13
        for k, v in GAMEPAD_HELP:
            text(surf, k, (r.left + 120, y), 9, T.GOLD, "topright")
            text(surf, v, (r.left + 130, y), 9, T.TEXT)
            y += 11
