"""HUD do jogo: vida, Foco, postura, Fervor, frascos, habilidades, chefe, números de dano e mensagens."""
import math

import pygame

from ..core.data import DB
from .widgets import text, bar, panel, text_width, wrap
from . import icons
from . import theme as T


class Floating:
    __slots__ = ("x", "y", "z", "text", "color", "t", "life", "size", "vy")

    def __init__(self, x, y, z, s, color, life=0.9, size=11):
        self.x, self.y, self.z = x, y, z
        self.text = s
        self.color = color
        self.t = 0.0
        self.life = life
        self.size = size
        self.vy = 1.2


class HUD:
    def __init__(self, settings):
        self.settings = settings
        self.floats = []
        self.messages = []          # [texto, tipo, tempo]
        self.banner = None          # (texto, subtítulo, cor, tempo, duração)
        self.area = None            # (nome, tempo)
        self.hurt_time = {}
        self.alerts = {}
        self.windups = {}
        self.hp_ghost = 1.0
        self.boss_ghost = 1.0
        self.time = 0.0
        self.boss_name_t = 0.0

    # ------------------------------------------------------------------ eventos
    def handle(self, ev, world):
        k = ev["kind"]
        if k == "hit":
            if self.settings.get("damage_numbers", True) and ev.get("damage", 0) >= 0.5:
                col = (255, 230, 120) if ev.get("crit") else (240, 236, 226)
                if ev.get("team") == "player":
                    col = (255, 90, 80)
                s = str(int(round(ev["damage"])))
                if ev.get("crit"):
                    s += "!"
                self.floats.append(Floating(ev["x"], ev["y"] + 0.4, ev["z"], s, col, 0.8, 12 if ev.get("crit") else 10))
                if ev.get("combo"):
                    self.floats.append(Floating(ev["x"], ev["y"] + 1.0, ev["z"], ev["combo"].upper(), (150, 220, 255), 1.1, 10))
                if ev.get("backstab") and ev.get("team") != "player":
                    self.floats.append(Floating(ev["x"], ev["y"] + 0.8, ev["z"], "COSTAS", (255, 200, 120), 0.8, 8))
            self.hurt_time[ev.get("target")] = self.time
        elif k == "heal":
            if ev.get("amount", 0) >= 1:
                self.floats.append(Floating(ev["x"], ev["y"], ev["z"], f"+{int(ev['amount'])}", (130, 240, 130), 0.9, 10))
        elif k == "status_proc":
            names = {"sangramento": "SANGRAMENTO", "queimadura": "QUEIMADURA", "congelamento": "CONGELADO", "choque": "CHOQUE",
                     "maldicao": "AMALDIÇOADO"}
            col = icons.STATUS_ICON_COL.get(ev["status"], (220, 220, 220))
            self.floats.append(Floating(ev["x"], ev["y"] + 0.6, ev["z"], names.get(ev["status"], ev["status"]), col, 1.0, 9))
            if ev.get("damage"):
                self.floats.append(Floating(ev["x"], ev["y"] + 0.2, ev["z"], str(int(ev["damage"])), col, 0.9, 12))
        elif k == "parry":
            self.floats.append(Floating(ev["x"], ev["y"] + 0.6, ev["z"], "APARADO!", (255, 240, 160), 0.9, 11))
        elif k == "perfect_dodge":
            self.floats.append(Floating(ev["x"], ev["y"] + 2.0, ev["z"], "ESQUIVA PERFEITA", (150, 220, 255), 0.9, 9))
        elif k == "posture_break":
            self.floats.append(Floating(ev["x"], ev["y"] + 0.5, ev["z"], "POSTURA ROMPIDA", (255, 210, 90), 1.2, 10))
        elif k == "steal":
            self.floats.append(Floating(ev["x"], ev["y"], ev["z"], f"+{ev['amount']} Graça" if ev["amount"] else "Roubou!", (255, 220, 120), 1.0, 9))
        elif k == "alert":
            self.alerts[ev["actor"]] = self.time
        elif k == "enemy_windup":
            self.windups[ev["actor"]] = (self.time, ev.get("unblockable", False), ev.get("time", 0.3))
        elif k == "message":
            self.message(ev["text"], ev.get("style", "info"))
        elif k == "no_resource":
            txt = {"fp": "Foco insuficiente", "cooldown": "Recarregando...", "fervor": "Fervor insuficiente",
                   "locked": "Ainda não desbloqueado", "flask": "Sem frascos", "fury": "Fúria insuficiente"}.get(ev["what"], "")
            if txt:
                self.message(txt, "warn", 1.2)
        elif k == "boss_start":
            self.banner = (ev["name"], ev.get("title", ""), (230, 200, 140), 0.0, 3.0)
            self.boss_name_t = 0.0
        elif k == "boss_phase" and ev.get("name"):
            self.banner = (ev["name"].upper(), "", (240, 120, 100), 0.0, 2.2)
        elif k == "last_stand":
            self.banner = ("ÚLTIMO FÔLEGO", "", (255, 220, 140), 0.0, 1.6)

    def message(self, s, kind="info", dur=3.5):
        for m in self.messages:
            if m[0] == s:
                m[2] = 0.0
                return
        self.messages.append([s, kind, 0.0, dur])
        if len(self.messages) > 6:
            self.messages.pop(0)

    def show_area(self, name):
        self.area = (name, 0.0)

    def show_banner(self, title, sub="", color=(230, 200, 140), dur=3.0):
        self.banner = (title, sub, color, 0.0, dur)

    # ------------------------------------------------------------------ desenho
    def draw(self, surf, dt, world, player, session, to_screen, device, interact=None):
        self.time += dt
        W, H = surf.get_size()
        if player is not None:
            self._player_bars(surf, player, session)
            self._bottom(surf, player, session, device, W, H)
        boss = world.boss if world is not None else None
        if boss is not None and boss.awake and not boss.dead:
            self._boss_bar(surf, boss, W, H, dt)
        if world is not None:
            self._enemy_bars(surf, world, player, to_screen)
        self._floats(surf, dt, to_screen)
        self._messages(surf, dt, W)
        if interact is not None:
            label = getattr(interact, "prompt", "Interagir")
            key = "[E]" if device != "gamepad" else "[→]"
            s = f"{key} {label}"
            w = text_width(s, 11) + 16
            r = pygame.Rect(W // 2 - w // 2, H - 92, w, 18)
            panel(surf, r, "dark")
            text(surf, s, r.center, 11, T.PARCH, "center")
        if self.area:
            name, t = self.area
            t += dt
            self.area = (name, t) if t < 3.5 else None
            a = int(255 * min(1.0, t * 2, (3.5 - t) * 1.5))
            text(surf, name, (W // 2, 26), 16, T.GOLD, "midtop", alpha=max(0, a), bold=True)
            pygame.draw.line(surf, (*T.GOLD_DIM,), (W // 2 - 70, 46), (W // 2 + 70, 46))
        if self.banner:
            title, sub, col, t, dur = self.banner
            t += dt
            self.banner = (title, sub, col, t, dur) if t < dur else None
            a = int(255 * min(1.0, t * 3, (dur - t) * 2))
            band = pygame.Surface((W, 44), pygame.SRCALPHA)
            band.fill((0, 0, 0, int(140 * a / 255)))
            surf.blit(band, (0, H // 2 - 70))
            text(surf, title, (W // 2, H // 2 - 64), 20, col, "midtop", alpha=max(0, a), bold=True)
            if sub:
                text(surf, sub, (W // 2, H // 2 - 40), 11, T.PARCH, "midtop", alpha=max(0, a))

    def _player_bars(self, surf, p, session):
        x, y = 10, 10
        w = int(min(230, 100 + p.max_hp * 0.35))
        frac = max(0.0, p.hp / p.max_hp)
        self.hp_ghost = max(frac, self.hp_ghost - 0.25 * (1 / 60))
        bar(surf, (x, y, w, 9), frac, (176, 30, 40), ghost=self.hp_ghost, ghost_color=(240, 200, 150))
        if p.barrier > 0:
            bar(surf, (x, y - 3, int(w * min(1.0, p.barrier / p.max_hp)), 3), 1.0, (240, 220, 140), border=False, shine=False)
        fw = int(min(200, 80 + p.max_fp * 0.6))
        bar(surf, (x, y + 11, fw, 6), p.fp / max(1.0, p.max_fp), (60, 100, 210))
        if p.posture > 0.5:
            bar(surf, (x, y + 19, int(w * 0.6), 4), p.posture / max(1.0, p.max_posture), (230, 196, 70), border=False)
        # Fervor
        fx, fy = x + w + 10, y + 5
        frac = p.fervor / 100.0
        r = 9
        pts = [(fx, fy - r), (fx + r, fy), (fx, fy + r), (fx - r, fy)]
        pygame.draw.polygon(surf, (24, 18, 20), pts)
        if frac > 0:
            clip = surf.get_clip()
            hh = int(2 * r * frac)
            surf.set_clip(pygame.Rect(fx - r, fy + r - hh, 2 * r + 1, hh + 1))
            col = (240, 190, 80) if frac < 1 else (255, 230 + int(20 * math.sin(self.time * 8)), 150)
            pygame.draw.polygon(surf, col, pts)
            surf.set_clip(clip)
        pygame.draw.polygon(surf, T.GOLD, pts, 1)
        if frac >= 1:
            text(surf, "SUPREMA", (fx + 13, fy - 5), 8, (255, 230, 150), bold=True)
        # status acumulando e ativos
        sx = x
        sy = y + 26
        for st, v in p.status.buildup.items():
            if v > 1:
                surf.blit(icons.status_icon(st), (sx, sy))
                bar(surf, (sx + 12, sy + 3, 30, 4), v / 100.0, icons.STATUS_ICON_COL.get(st, (200, 200, 200)), border=False)
                sx += 46
        for st in p.status.active:
            surf.blit(icons.status_icon(st), (sx, sy))
            sx += 12
        # bônus ativos
        bx = x
        by = sy + 12
        for bid, b in list(p.status.buffs.items())[:8]:
            pygame.draw.rect(surf, (40, 34, 30), (bx, by, 10, 10))
            pygame.draw.rect(surf, T.GOLD_DIM, (bx, by, 10, 10), 1)
            k = min(1.0, b.time / 10.0)
            pygame.draw.rect(surf, (230, 200, 120), (bx + 2, by + 8 - int(6 * k), 6, int(6 * k)))
            bx += 12
        # corrupção
        c = session.char.corruption if session else 0
        if c > 0:
            tier = session.char.corruption_tier
            col = [(120, 100, 100), (170, 60, 70), (200, 30, 60), (240, 20, 50)][tier]
            cx = 10 + w + 30
            pygame.draw.circle(surf, (20, 10, 12), (cx + 18, 15), 6)
            pygame.draw.circle(surf, col, (cx + 18, 15), 6, 1)
            pygame.draw.circle(surf, col, (cx + 18, 15), max(1, int(5 * c / 100)))

    def _bottom(self, surf, p, session, device, W, H):
        # frascos
        y = H - 34
        surf.blit(icons.item_icon("flask_hp"), (10, y))
        text(surf, str(p.flasks_hp), (28, y + 3), 11, T.PARCH)
        surf.blit(icons.item_icon("flask_fp"), (44, y))
        text(surf, str(p.flasks_fp), (62, y + 3), 11, T.PARCH)
        # cargas de esquiva
        for i in range(p.max_dodges):
            col = (150, 210, 240) if i < p.dodge_charges else (50, 60, 70)
            pygame.draw.rect(surf, col, (10 + i * 8, y + 20, 6, 3))
        # recurso de classe
        rx = 80
        res = p.L.resource
        if p.char.class_id == "soldado":
            for i in range(p.max_ammo):
                col = (240, 120, 50) if i < p.ammo_special and i < p.ammo else ((230, 210, 160) if i < p.ammo else (60, 56, 50))
                pygame.draw.rect(surf, col, (rx + i * 5, y + 4, 3, 8))
            text(surf, "munição", (rx, y + 14), 8, T.MUTED)
        elif res == "fury":
            bar(surf, (rx, y + 4, 60, 6), p.fury / 100.0, (200, 120, 60) if not p.transformed else (150, 180, 255))
            text(surf, "Fúria" + (" — FERA" if p.transformed else ""), (rx, y + 12), 8, T.MUTED)
        if p.heat > 0:
            bar(surf, (rx, y - 8, 40, 4), p.heat, (255, 120, 40), border=False)
        # habilidades
        slots = []
        for i, (aid, unlocked) in enumerate(p.L.abilities):
            slots.append((aid, unlocked, str(i + 1) if device != "gamepad" else ["LT+X", "LT+Y", "LT+A"][i], "active"))
        uid, uok = p.L.ultimate
        slots.append((uid, uok, "R" if device != "gamepad" else "RT", "ultimate"))
        cx0 = W // 2 - (len(slots) + 1) * 13
        for i, (aid, ok, key, kind) in enumerate(slots):
            x = cx0 + i * 26
            yy = H - 30
            pygame.draw.rect(surf, (14, 10, 14), (x - 1, yy - 1, 20, 20))
            ic = icons.ability_icon(aid, p.char.class_id, kind)
            surf.blit(pygame.transform.scale(ic, (18, 18)) if ic.get_width() != 18 else ic, (x, yy))
            if not ok:
                sh = pygame.Surface((18, 18), pygame.SRCALPHA)
                sh.fill((0, 0, 0, 190))
                surf.blit(sh, (x, yy))
            elif kind == "ultimate":
                if p.fervor < 100:
                    sh = pygame.Surface((18, 18), pygame.SRCALPHA)
                    sh.fill((0, 0, 0, 150))
                    surf.blit(sh, (x, yy))
                    k = p.fervor / 100
                    pygame.draw.rect(surf, (240, 200, 90), (x, yy + 18 - int(18 * k), 18, int(18 * k)), 1)
            else:
                cd = p.cooldowns.get(aid, 0.0)
                if cd > 0:
                    full = DB.abilities[aid].get("cd", 6)
                    k = min(1.0, cd / full)
                    sh = pygame.Surface((18, int(18 * k) + 1), pygame.SRCALPHA)
                    sh.fill((0, 0, 0, 170))
                    surf.blit(sh, (x, yy + 18 - int(18 * k)))
                if p.fp < p.ability_cost(aid):
                    pygame.draw.rect(surf, (60, 90, 200), (x, yy, 18, 18), 1)
            pygame.draw.rect(surf, T.GOLD_DIM, (x - 1, yy - 1, 20, 20), 1)
            text(surf, key, (x + 9, yy + 20), 7, T.MUTED, "midtop")
        # arte
        art = p.L.art
        if art:
            x = cx0 + len(slots) * 26 + 6
            yy = H - 30
            pygame.draw.rect(surf, (14, 10, 14), (x - 1, yy - 1, 20, 20))
            surf.blit(pygame.transform.scale(icons.weapon_icon(p.L.family), (18, 18)), (x, yy))
            cd = p.cooldowns.get("art", 0)
            if cd > 0:
                sh = pygame.Surface((18, 18), pygame.SRCALPHA)
                sh.fill((0, 0, 0, 160))
                surf.blit(sh, (x, yy))
            pygame.draw.rect(surf, (200, 160, 220), (x - 1, yy - 1, 20, 20), 1)
            text(surf, "F" if device != "gamepad" else "RB", (x + 9, yy + 20), 7, T.MUTED, "midtop")
        # Graça
        g = session.char.grace if session else 0
        s = f"{g}"
        tw = text_width(s, 12, True)
        surf.blit(icons.item_icon("grace"), (W - tw - 30, H - 26))
        text(surf, s, (W - 10, H - 24), 12, (240, 210, 140), "topright", bold=True)
        if session:
            text(surf, f"Nível {session.char.level}", (W - 10, H - 38), 8, T.MUTED, "topright")
        # combo
        if p.combo_count >= 3:
            k = min(1.0, p.combo_timer / 2.2)
            text(surf, f"{p.combo_count} GOLPES", (W - 12, H // 2 - 30), 13, (255, 220, 150), "topright", alpha=int(255 * k), bold=True)

    def _boss_bar(self, surf, boss, W, H, dt):
        w = min(360, W - 120)
        x = W // 2 - w // 2
        y = H - 62
        self.boss_name_t += dt
        frac = boss.hp / boss.max_hp
        self.boss_ghost = max(frac, self.boss_ghost - dt * 0.12)
        text(surf, boss.name, (x, y - 12), 11, (230, 214, 190), bold=True)
        bar(surf, (x, y, w, 8), frac, (150, 20, 30), ghost=self.boss_ghost, ghost_color=(230, 190, 120))
        if boss.max_posture > 0:
            pf = boss.posture / boss.max_posture
            if boss.broken > 0:
                pf = 1.0
            bar(surf, (x + w // 4, y + 10, w // 2, 3), pf, (240, 200, 80) if boss.broken <= 0 else (255, 255, 200), border=False)

    def _enemy_bars(self, surf, world, player, to_screen):
        for e in world.actors:
            if e.kind not in ("enemy",) or e.dead or not e.alive or getattr(e, "is_part", False) and False:
                continue
            if getattr(e, "d", {}).get("dummy"):
                pass
            shown = self.time - self.hurt_time.get(e.id, -99) < 4.0 or (player is not None and player.locked is e) or e.elite or e.broken > 0
            sx, sy = to_screen(e.x, e.y + e.height * e.scale + 0.35, e.z)
            if shown:
                part = getattr(e, "is_part", False)   # braços do Serafim etc.: próximos demais para nomes
                w = 30 if not e.elite else (22 if part else 44)
                bar(surf, (sx - w // 2, sy - 2, w, 4), e.hp / e.max_hp, (190, 40, 40), border=False)
                if e.max_posture > 1 and e.posture > 0.5:
                    pygame.draw.line(surf, (230, 196, 70), (sx - w // 2, sy + 3), (sx - w // 2 + int(w * min(1, e.posture / e.max_posture)), sy + 3))
                if e.elite and not part:
                    text(surf, e.name, (sx, sy - 12), 8, (240, 160, 120), "midtop")
            if e.broken > 0:
                pulse = int(160 + 90 * math.sin(self.time * 10))
                text(surf, "EXECUTAR", (sx, sy - 22), 8, (255, 230, 120), "midtop", alpha=pulse, bold=True)
            if self.time - self.alerts.get(e.id, -99) < 1.0:
                text(surf, "!", (sx, sy - 18), 14, (255, 80, 60), "midtop", bold=True)
            w0 = self.windups.get(e.id)
            if w0 is not None and self.time - w0[0] < max(0.25, w0[2]):
                col = (255, 50, 40) if w0[1] else (255, 230, 140)
                k = (self.time - w0[0]) / max(0.25, w0[2])
                r = int(2 + 3 * (1 - k))
                pygame.draw.circle(surf, col, (int(sx + 6), int(sy - 8)), r)
                if w0[1]:
                    text(surf, "!", (sx + 6, sy - 22), 10, col, "midtop", bold=True)
        if player is not None and player.locked is not None and not player.locked.dead:
            t = player.locked
            sx, sy = to_screen(t.x, t.y + t.height * t.scale * 0.55, t.z)
            r = 8 + int(math.sin(self.time * 6))
            for a in range(4):
                ang = a * math.pi / 2 + self.time
                pygame.draw.line(surf, (255, 220, 140), (sx + math.cos(ang) * r, sy + math.sin(ang) * r),
                                 (sx + math.cos(ang) * (r + 4), sy + math.sin(ang) * (r + 4)))

    def _floats(self, surf, dt, to_screen):
        keep = []
        for f in self.floats:
            f.t += dt
            if f.t >= f.life:
                continue
            f.y += f.vy * dt
            f.vy *= 0.94
            sx, sy = to_screen(f.x, f.y, f.z)
            a = int(255 * min(1.0, (f.life - f.t) * 3))
            text(surf, f.text, (sx, sy), f.size, f.color, "midbottom", alpha=a, bold=True)
            keep.append(f)
        self.floats = keep[-60:]

    def _messages(self, surf, dt, W):
        y = 70
        keep = []
        for m in self.messages:
            m[2] += dt
            if m[2] > m[3]:
                continue
            a = int(255 * min(1.0, m[2] * 4, (m[3] - m[2]) * 2))
            col = {"warn": (240, 150, 120), "grace": (240, 210, 140), "item": (210, 230, 200), "rune": (190, 170, 250),
                   "story": (230, 220, 200), "boss": (255, 160, 120), "puzzle": (160, 220, 250), "quest": (250, 230, 150),
                   "secret": (200, 255, 200), "hint": (190, 190, 220)}.get(m[1], T.TEXT)
            lines = wrap(m[0], 10, 260)
            for l in lines:
                text(surf, l, (W - 12, y), 10, col, "topright", alpha=a)
                y += 12
            y += 2
            keep.append(m)
        self.messages = keep
