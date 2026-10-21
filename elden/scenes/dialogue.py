"""Diálogos, leitura de documentos, escolhas de chefe e de final, e serviços dos NPCs (loja, ferreiro, biblioteca)."""
import pygame

from ..core.data import DB
from ..core import saves
from ..sim.narrative.dialogue import DialogueRunner
from ..sim.progression import grace_tree
from ..ui.widgets import text, panel, wrap, text_block, ListView, divider, bar
from ..ui import icons
from ..ui import theme as T
from .menus import Overlay, MenuOverlay, weapon_desc


class DialogueOverlay(Overlay):
    def __init__(self, app, game, dlg_id, npc_id=None):
        super().__init__(app)
        self.game = game
        self.runner = DialogueRunner(game.session, dlg_id, npc_id)
        self.npc_id = npc_id
        if npc_id:
            game.session.npc_seen.add(npc_id)
        self.chars = 0.0
        self.choice_list = ListView([], 14, 5)
        self._sync()

    def _sync(self):
        self.chars = 0.0
        self.choice_list.set_items(self.runner.choices(), keep=False)

    def update(self, dt):
        super().update(dt)
        inp = self.inp
        full = len(self.runner.text)
        self.chars = min(full, self.chars + dt * 70)
        choices = self.runner.choices()
        if choices and self.chars >= full:
            dx, dy = inp.ui_nav(dt)
            if dy:
                self.choice_list.move(dy)
                self.sfx("ui_move", 0.4)
            mx, my = self.mouse()
            if inp.mouse_moved or self.clicked():
                self.choice_list.mouse(mx, my)
        if inp.ui("confirm") or self.clicked() or "left mouse" in inp.pressed:
            if self.chars < full:
                self.chars = full
                return
            if choices:
                idx = self.choice_list.current()[0]
                self.runner.advance(idx)
            else:
                self.runner.advance()
            self.sfx("ui_confirm", 0.4)
            self._handle_outputs()
            if self.runner.done:
                self.close()
                return
            self._sync()
        elif inp.ui("cancel") and not choices:
            self.runner.advance()
            if self.runner.done:
                self._handle_outputs()
                self.close()
            else:
                self._sync()

    def _handle_outputs(self):
        app = self.app
        for out in self.runner.take_outputs():
            if out[0] == "service":
                self.close()
                open_service(app, self.game, out[1], self.npc_id)
                self.runner.done = True
            elif out[0] == "ending":
                self.close()
                from .ending import EndingScene
                self.game.session.ending = out[1]
                saves.save_session(self.game.session)
                app.transition(lambda: app.replace(EndingScene(app, self.game.session, out[1])), 0.8)
                self.runner.done = True
            elif out[0] == "travel":
                self.close()
                self.game.travel(out[1], out[2])
                self.runner.done = True
        if self.game.world and self.game.world.player:
            self.game.world.player.apply_loadout()

    def draw_ui(self, surf, dt):
        W, H = surf.get_size()
        r = pygame.Rect(30, H - 108, W - 60, 96)
        panel(surf, r)
        who = self.runner.who
        if who:
            nr = pygame.Rect(r.left + 10, r.top - 12, len(who) * 7 + 20, 16)
            panel(surf, nr, "dark")
            text(surf, who, nr.center, 10, T.GOLD, "center", bold=True)
        txt = self.runner.text[:int(self.chars)]
        choices = self.runner.choices()
        text_block(surf, txt, r.left + 12, r.top + 10, r.w - 24, 11, T.PARCH, line_h=14, max_lines=4 if not choices else 3)
        if choices and self.chars >= len(self.runner.text):
            cr = pygame.Rect(r.right - 260, r.top - 18 - 14 * min(5, len(choices)), 250, 14 * min(5, len(choices)) + 10)
            panel(surf, cr, "dark")

            def row(s, item, x, y, w, sel):
                text(s, item[1], (x + 4, y + 2), 9, T.WHITE if sel else T.TEXT)
            self.choice_list.draw(surf, cr.left + 10, cr.top + 5, cr.w - 20, row)
        elif self.chars >= len(self.runner.text):
            if int(self.time * 2) % 2 == 0:
                text(surf, "▼", (r.right - 14, r.bottom - 16), 10, T.GOLD)


class DocumentOverlay(Overlay):
    def __init__(self, app, doc_id):
        super().__init__(app)
        self.doc = DB.lore[doc_id]
        app.audio.play("item", 0.6)

    def update(self, dt):
        super().update(dt)
        if self.time > 0.3 and (self.inp.ui("confirm") or self.back() or self.clicked()):
            self.close()

    def draw_ui(self, surf, dt):
        self.dim(surf, 170)
        W, H = surf.get_size()
        r = pygame.Rect(W // 2 - 190, 30, 380, H - 60)
        pygame.draw.rect(surf, (214, 198, 160), r)
        pygame.draw.rect(surf, (120, 96, 60), r, 2)
        for y in range(r.top + 4, r.bottom - 4, 3):
            pygame.draw.line(surf, (205, 188, 150), (r.left + 3, y), (r.right - 4, y))
        text_block(surf, self.doc["title"], r.left + 16, r.top + 14, r.w - 32, 12, (70, 40, 20), align="center")
        divider(surf, r.left + 40, r.right - 40, r.top + 40, (140, 110, 70))
        text_block(surf, self.doc["text"], r.left + 18, r.top + 50, r.w - 36, 11, (50, 34, 22), line_h=15)
        text(surf, "Enter / Esc", (r.centerx, r.bottom - 16), 8, (110, 90, 60), "midtop", shadow=False)


class BossChoiceOverlay(Overlay):
    full = True

    """Após um chefe: purificar (sagrado) ou absorver (profano) o resquício de Graça."""

    def __init__(self, app, game, boss_id):
        super().__init__(app)
        self.game = game
        self.boss_id = boss_id
        self.sel = 0

    def update(self, dt):
        super().update(dt)
        inp = self.inp
        dx, dy = inp.ui_nav(dt)
        if dx or dy:
            self.sel = 1 - self.sel
            self.sfx("ui_move", 0.5)
        mx, my = self.mouse()
        for i, r in enumerate(getattr(self, "_rects", [])):
            if r.collidepoint(mx, my) and (inp.mouse_moved or self.clicked()):
                self.sel = i
        if self.time > 0.6 and (inp.ui("confirm") or self.clicked()):
            choice = "purificar" if self.sel == 0 else "absorver"
            self.game.session.boss_choice(self.boss_id, choice)
            self.game.world.player.apply_loadout()
            self.sfx("grace_found" if choice == "purificar" else "shadow")
            saves.save_session(self.game.session)
            self.close()

    def draw_ui(self, surf, dt):
        self.dim(surf, 180)
        W, H = surf.get_size()
        bd = DB.bosses[self.boss_id]
        text(surf, "O RESQUÍCIO DE GRAÇA", (W // 2, 40), 16, T.GOLD, "midtop", bold=True)
        text_block(surf, f"A Graça que habitava {bd['name']} paira diante de você, pulsando. O que fará com ela?",
                   W // 2 - 200, 64, 400, 10, T.PARCH, align="center")
        opts = [("PURIFICAR", "Devolver a luz à chama. Reduz a corrupção.", bd.get("purify_reward", []), (230, 210, 150)),
                ("ABSORVER", "Tomar o poder para si. Aumenta a corrupção.", bd.get("absorb_reward", []), (220, 60, 80))]
        self._rects = []
        for i, (title, desc, rew, col) in enumerate(opts):
            r = pygame.Rect(W // 2 - 210 + i * 220, 110, 200, 150)
            panel(surf, r, "red" if i == 1 else "normal")
            if i == self.sel:
                pygame.draw.rect(surf, col, r.inflate(4, 4), 2)
            text(surf, title, (r.centerx, r.top + 10), 14, col, "midtop", bold=True)
            y = r.top + 32 + text_block(surf, desc, r.left + 10, r.top + 32, r.w - 20, 9, T.TEXT, align="center")
            y += 6
            for entry in rew:
                text(surf, "• " + reward_name(entry), (r.left + 12, y), 9, T.PARCH)
                y += 12
            self._rects.append(r)


def reward_name(entry):
    if "rune" in entry:
        return DB.runes[entry["rune"]]["name"]
    if "art" in entry:
        return "Arte: " + DB.arts[entry["art"]]["name"]
    if "weapon" in entry:
        return DB.weapons[entry["weapon"]]["name"]
    if "item" in entry:
        return DB.items[entry["item"]]["name"]
    if "grace" in entry:
        return f"{entry['grace']} Graça"
    if "materials" in entry:
        return f"{entry['materials']} Fragmentos de Forja"
    if "points" in entry:
        return f"{entry['points']} Ponto de Graça"
    return "?"


ENDINGS = {
    "purificacao": ("PURIFICAÇÃO DA GRAÇA", "Devolver os fragmentos ao deus e reacender a luz. O mundo cura-se... por uma era."),
    "dominio": ("DOMÍNIO DA GRAÇA", "Sentar-se no Trono e tomar a Graça para si. Tornar-se o novo deus de Elden."),
    "ruptura": ("RUPTURA DO CICLO", "Partir o Trono com os Fragmentos do Ciclo. A Graça se espalha, fraca e livre. Os deuses acabam."),
}


class EndingChoiceOverlay(Overlay):
    full = True

    def __init__(self, app, game):
        super().__init__(app)
        self.game = game
        self.opts = game.session.ending_options()
        self.sel = 0

    def update(self, dt):
        super().update(dt)
        inp = self.inp
        dx, dy = inp.ui_nav(dt)
        if dy:
            self.sel = (self.sel + dy) % len(self.opts)
            self.sfx("ui_move", 0.5)
        if self.back():
            self.close()
            return
        if self.time > 0.6 and (inp.ui("confirm") or self.clicked()):
            from .ending import EndingScene
            end = self.opts[self.sel]
            s = self.game.session
            s.ending = end
            s.set_flag("final:" + end)
            saves.save_session(s)
            app = self.app
            app.transition(lambda: (app.get_scene_view().unload(), app.replace(EndingScene(app, s, end))), 0.6)

    def draw_ui(self, surf, dt):
        self.dim(surf, 200)
        W, H = surf.get_size()
        text(surf, "O TRONO DA GRAÇA", (W // 2, 30), 18, T.GOLD, "midtop", bold=True)
        text_block(surf, "O deus despedaçado jaz aos seus pés. O Trono espera uma escolha.", W // 2 - 200, 56, 400, 10, T.PARCH, align="center")
        for i, e in enumerate(self.opts):
            title, desc = ENDINGS[e]
            r = pygame.Rect(W // 2 - 200, 90 + i * 70, 400, 60)
            panel(surf, r, "red" if e == "dominio" else "normal")
            if i == self.sel:
                pygame.draw.rect(surf, T.GOLD, r.inflate(4, 4), 2)
            text(surf, title, (r.centerx, r.top + 8), 13, T.GOLD if e != "dominio" else (230, 80, 90), "midtop", bold=True)
            text_block(surf, desc, r.left + 12, r.top + 26, r.w - 24, 9, T.TEXT, align="center")
        if "ruptura" not in self.opts:
            text(surf, "(Há rumores de uma terceira escolha para quem reunir os cinco Fragmentos do Ciclo.)", (W // 2, H - 30), 8, T.MUTED, "midtop")


# ---------------------------------------------------------------------------- serviços
def open_service(app, game, service, npc_id):
    if service == "mercador":
        app.push(ShopScreen(app, game, "oriana", "MERCADORA ORIANA"))
    elif service == "treinador":
        app.push(ShopScreen(app, game, "kaelen", "TREINO DE KAELEN — ARTES DE COMBATE"))
    elif service == "ferreiro":
        app.push(BlacksmithScreen(app, game))
    elif service == "biblioteca":
        app.push(LibraryScreen(app, game))
    elif service == "respec":
        app.push(LibraryScreen(app, game, respec=True))


def shop_label(entry):
    if "rune" in entry:
        return DB.runes[entry["rune"]]["name"], T.RARITY[DB.runes[entry["rune"]]["rarity"]]
    if "art" in entry:
        return "Arte: " + DB.arts[entry["art"]]["name"], (210, 180, 240)
    if "item" in entry:
        return DB.items[entry["item"]]["name"], T.PARCH
    if "materials" in entry:
        return "Fragmento de Forja", T.TEXT
    return "?", T.TEXT


class ShopScreen(Overlay):
    full = True

    def __init__(self, app, game, npc_id, title):
        super().__init__(app)
        self.game = game
        self.s = game.session
        self.npc = npc_id
        self.title = title
        self.list = ListView([], 15, 14)
        self.msg = ""
        self.msg_t = 0
        self._refresh()

    def _owned(self, e):
        c = self.s.char
        if "rune" in e:
            return e["rune"] in c.runes
        if "art" in e:
            return e["art"] in c.arts
        return False

    def _bought(self, e):
        key = f"comprado:{self.npc}:{e.get('item', e.get('rune', e.get('art', 'mat')))}"
        return self.s.props.get("_loja", {}).get(key, 0)

    def _refresh(self):
        items = []
        for e in DB.npcs[self.npc].get("shop", []):
            if not self.s.check(e.get("if")):
                continue
            if self._owned(e):
                continue
            if "stock" in e and self._bought(e) >= e["stock"]:
                continue
            items.append(e)
        self.list.set_items(items)

    def update(self, dt):
        super().update(dt)
        inp = self.inp
        self.msg_t -= dt
        dx, dy = inp.ui_nav(dt)
        if dy:
            self.list.move(dy)
            self.sfx("ui_move", 0.4)
        mx, my = self.mouse()
        hov = self.list.mouse(mx, my, inp.scroll) if (inp.mouse_moved or self.clicked() or inp.scroll) else None
        if (inp.ui("confirm") or (self.clicked() and hov is not None)) and self.list.current():
            self._buy(self.list.current())
        elif self.back():
            self.close()

    def _buy(self, e):
        c = self.s.char
        if c.grace < e["price"]:
            self.msg, self.msg_t = "Graça insuficiente.", 1.5
            self.sfx("ui_error")
            return
        c.grace -= e["price"]
        entry = {k: v for k, v in e.items() if k in ("rune", "art", "item", "materials")}
        if "item" in entry:
            entry["n"] = 1
        self.s.grant(entry, None)
        key = f"comprado:{self.npc}:{e.get('item', e.get('rune', e.get('art', 'mat')))}"
        d = self.s.props.setdefault("_loja", {})
        d[key] = d.get(key, 0) + 1
        self.sfx("item")
        self.msg, self.msg_t = "Comprado!", 1.2
        self.game.world.player.apply_loadout()
        self._refresh()

    def draw_ui(self, surf, dt):
        self.dim(surf, 180)
        W, H = surf.get_size()
        r = pygame.Rect(30, 20, W - 60, H - 40)
        panel(surf, r)
        text(surf, self.title, (r.centerx, r.top + 8), 13, T.GOLD, "midtop", bold=True)
        text(surf, f"Graça: {self.s.char.grace}", (r.right - 12, r.top + 10), 10, (240, 210, 140), "topright")
        lw = r.w // 2

        def row(s, e, x, y, w, sel):
            name, col = shop_label(e)
            text(s, name, (x + 4, y + 2), 9, col)
            text(s, str(e["price"]), (x + w - 4, y + 2), 9, (240, 210, 140) if self.s.char.grace >= e["price"] else (200, 90, 90), "topright")
        self.list.draw(surf, r.left + 14, r.top + 32, lw - 20, row)
        e = self.list.current()
        ir = pygame.Rect(r.left + lw + 4, r.top + 30, lw - 16, r.h - 44)
        panel(surf, ir, "dark")
        if e:
            if "rune" in e:
                rd = DB.runes[e["rune"]]
                text(surf, rd["name"], (ir.left + 8, ir.top + 8), 11, T.RARITY[rd["rarity"]], bold=True)
                text(surf, T.CATEGORY_NAMES[rd["category"]], (ir.left + 8, ir.top + 22), 9, T.CATEGORY_COLORS[rd["category"]])
                text_block(surf, rd["desc"], ir.left + 8, ir.top + 36, ir.w - 16, 10, T.TEXT)
            elif "art" in e:
                ad = DB.arts[e["art"]]
                text(surf, ad["name"], (ir.left + 8, ir.top + 8), 11, (210, 180, 240), bold=True)
                fams = ", ".join(DB.families[f]["name"] for f in ad["families"] if f in DB.families) or "Todas as armas"
                text_block(surf, "Armas: " + fams, ir.left + 8, ir.top + 22, ir.w - 16, 8, T.MUTED)
                text_block(surf, ad["desc"], ir.left + 8, ir.top + 46, ir.w - 16, 10, T.TEXT)
            elif "item" in e:
                it = DB.items[e["item"]]
                text(surf, it["name"], (ir.left + 8, ir.top + 8), 11, T.PARCH, bold=True)
                text_block(surf, it["desc"], ir.left + 8, ir.top + 26, ir.w - 16, 10, T.TEXT)
            else:
                text_block(surf, "Material usado pelo ferreiro para fortalecer armas.", ir.left + 8, ir.top + 8, ir.w - 16, 10, T.TEXT)
        if self.msg_t > 0:
            text(surf, self.msg, (r.centerx, r.bottom - 16), 10, T.PARCH, "midtop")


class BlacksmithScreen(Overlay):
    full = True

    MAX = 5

    def __init__(self, app, game):
        super().__init__(app)
        self.game = game
        self.s = game.session
        self.list = ListView(list(self.s.char.weapons), 15, 12)
        self.msg = ""
        self.msg_t = 0

    def cost(self, lvl):
        return (lvl + 1) * 2, 200 * (lvl + 1) + 100 * lvl * lvl

    def limit(self):
        s = self.s
        return 1 + sum(1 for f in ("ato1_concluido", "ato2_concluido", "ato3_concluido", "ato4_concluido") if s.has_flag(f))

    def update(self, dt):
        super().update(dt)
        inp = self.inp
        self.msg_t -= dt
        dx, dy = inp.ui_nav(dt)
        if dy:
            self.list.move(dy)
        mx, my = self.mouse()
        if inp.mouse_moved or self.clicked():
            self.list.mouse(mx, my)
        if (inp.ui("confirm") or self.clicked()) and self.list.current():
            wid = self.list.current()
            c = self.s.char
            lvl = c.weapon_level(wid)
            mats, grace = self.cost(lvl)
            if lvl >= self.MAX:
                self.msg = "Esta arma já está no máximo."
            elif lvl >= self.limit():
                self.msg = "Ferrus precisa de brasas mais fortes (derrote o próximo chefe)."
            elif c.materials < mats or c.grace < grace:
                self.msg = "Faltam Fragmentos de Forja ou Graça."
            else:
                c.materials -= mats
                c.grace -= grace
                c.weapon_levels[wid] = lvl + 1
                self.msg = f"{DB.weapons[wid]['name']} agora é +{lvl + 1}!"
                self.sfx("level_up")
                self.game.world.player.apply_loadout()
            self.msg_t = 2.0
        elif self.back():
            self.close()

    def draw_ui(self, surf, dt):
        self.dim(surf, 180)
        W, H = surf.get_size()
        r = pygame.Rect(30, 20, W - 60, H - 40)
        panel(surf, r)
        c = self.s.char
        text(surf, "FORJA DE FERRUS", (r.centerx, r.top + 8), 13, T.GOLD, "midtop", bold=True)
        text(surf, f"Fragmentos de Forja: {c.materials}    Graça: {c.grace}    Limite atual: +{self.limit()}", (r.centerx, r.top + 24), 9, T.PARCH, "midtop")

        def row(s, wid, x, y, w, sel):
            lvl = c.weapon_level(wid)
            text(s, f"{DB.weapons[wid]['name']} +{lvl}", (x + 4, y + 2), 9, T.PARCH if sel else T.TEXT)
            if lvl < self.MAX:
                m, g = self.cost(lvl)
                text(s, f"{m} frag. • {g} Graça", (x + w - 4, y + 2), 9, T.MUTED, "topright")
            else:
                text(s, "MÁX", (x + w - 4, y + 2), 9, T.GOLD, "topright")
        self.list.draw(surf, r.left + 16, r.top + 42, r.w - 40, row)
        wid = self.list.current()
        if wid:
            lvl = c.weapon_level(wid)
            a, _ = weapon_desc(wid, lvl)
            b, _ = weapon_desc(wid, min(self.MAX, lvl + 1))
            text(surf, f"Dano: {a}  →  {b}", (r.left + 16, r.bottom - 40), 10, T.PARCH)
        if self.msg_t > 0:
            text(surf, self.msg, (r.centerx, r.bottom - 22), 10, (240, 210, 150), "midtop")


class LibraryScreen(MenuOverlay):
    title = "BIBLIOTECA DE THEODRIC"

    def __init__(self, app, game, respec=False):
        self.game = game
        self.s = game.session
        super().__init__(app, [], 300)
        self._build()

    def _build(self):
        app = self.app
        from .menus import DocsScreen
        n_spent = self.s.char.points_spent
        opts = [("Ler documentos encontrados", lambda: app.push(DocsScreen(app, self.s))),
                (f"Redistribuir pontos de Graça (Lágrima do Esquecimento: {self.s.char.items.get('lagrima_esquecimento', 0)})",
                 self._respec, self.s.char.has_item("lagrima_esquecimento") and n_spent > 0),
                ("Voltar", self.close)]
        self.list.set_items(opts)

    def _respec(self):
        c = self.s.char
        if c.take_item("lagrima_esquecimento"):
            n = grace_tree.respec(c)
            self.game.world.player.apply_loadout()
            self.game.hud.message(f"{n} nós esquecidos. Seus pontos de Graça estão livres.", "grace")
            self.sfx("rest")
        self._build()
