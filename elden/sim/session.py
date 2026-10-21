"""Sessão de jogo: progresso persistente (flags, objetos, Graças, missões, corrupção, chefes) e a ponte
entre a simulação e as telas. A simulação faz pedidos (descansar, viajar, dialogar, escolher) que a
camada de cenas consome em 'events'. Sem janela, os testes atendem esses pedidos diretamente.
"""
import time

from ..core.data import DB
from .progression.character import Character

ACT_ORDER = ["ato1", "ato2", "ato3", "ato4", "ato5"]


class Session:
    def __init__(self, character=None):
        self.char = character or Character()
        self.flags = set()
        self.props = {}                 # level -> pid -> estado
        self.graces = {}                # pid -> {"name", "level"}
        self.last_grace = None          # (level, pid)
        self.level = "santuario"
        self.spawn = "inicio"
        self.lost_grace = None          # {"level", "x", "y", "z", "amount"}
        self.docs = []
        self.secrets = []
        self.quests = {}
        self.bosses = []
        self.deaths = 0
        self.playtime = 0.0
        self.created = time.time()
        self.ending = None
        self.events = []                # pedidos para a camada de cenas
        self.notifications = []         # (texto, tipo) para a interface
        self.kills = {}
        self.slot = 0
        self.npc_seen = set()
        self.world = None

    # ------------------------------------------------------------------ flags e estados
    def has_flag(self, f):
        return f in self.flags

    def set_flag(self, f):
        if f not in self.flags:
            self.flags.add(f)
            self.char._flags = self.flags
            self._check_quests(f)

    def prop_state(self, level, pid):
        return self.props.get(level, {}).get(pid)

    def set_prop_state(self, level, pid, value):
        self.props.setdefault(level, {})[pid] = value

    def notify(self, text, kind="info"):
        self.notifications.append((text, kind))

    # ------------------------------------------------------------------ Graças
    def grace_discovered(self, pid):
        return pid in self.graces

    def discover_grace(self, pid, name, level):
        self.graces[pid] = {"name": name, "level": level}
        self.last_grace = (level, pid)
        self.notify(f"Graça descoberta: {name}", "grace")

    def request_rest(self, grace, player):
        self.last_grace = (grace.world.level.id, grace.pid)
        self.events.append(("rest", grace.pid))

    def request_travel(self, to, spawn):
        self.events.append(("travel", to, spawn))

    # ------------------------------------------------------------------ recompensas
    def grant(self, entry, pos):
        c = self.char
        if "grace" in entry:
            n = c.add_grace(entry["grace"] * (1.0 + 0.0))
            self.notify(f"+{n} Graça", "grace")
        if "item" in entry:
            n = entry.get("n", 1)
            c.add_item(entry["item"], n)
            it = DB.items.get(entry["item"], {"name": entry["item"]})
            self.notify(f"Obteve: {it['name']}" + (f" x{n}" if n > 1 else ""), "item")
            on_get = it.get("on_get")
            if on_get:
                c.take_item(entry["item"], n)
                self.grant(on_get, pos)
            if entry["item"] == "frasco_brasa":
                c.flasks_hp += 1
                c.take_item("frasco_brasa")
                self.notify("Frasco de Brasa aumentado!", "item")
            if entry["item"] == "lagrima_eter":
                c.flasks_fp += 1
                c.take_item("lagrima_eter")
                self.notify("Frasco de Éter aumentado!", "item")
            if entry["item"] == "semente_dourada":
                c.flask_level += 1
                c.take_item("semente_dourada")
                self.notify("Os frascos curam mais!", "item")
        if "rune" in entry:
            if c.add_rune(entry["rune"]):
                self.notify(f"Runa obtida: {DB.runes[entry['rune']]['name']}", "rune")
        if "weapon" in entry:
            if c.add_weapon(entry["weapon"]):
                self.notify(f"Arma obtida: {DB.weapons[entry['weapon']]['name']}", "item")
        if "art" in entry:
            if c.add_art(entry["art"]):
                self.notify(f"Arte de combate: {DB.arts[entry['art']]['name']}", "item")
        if "materials" in entry:
            c.materials += entry["materials"]
            self.notify(f"+{entry['materials']} Fragmentos de Forja", "item")
        if "points" in entry:
            c.bonus_points += entry["points"]
            self.notify(f"+{entry['points']} Ponto de Graça", "grace")
        if "doc" in entry:
            self.read_document(entry["doc"], silent=True)
        if "fragment" in entry:
            if entry["fragment"] not in c.cycle_fragments:
                c.cycle_fragments.append(entry["fragment"])
                self.notify(f"Fragmento do Ciclo ({len(c.cycle_fragments)}/5)", "rune")
                if len(c.cycle_fragments) >= 5:
                    self.set_flag("ciclo_completo")
        if "rune_slot" in entry:
            c.rune_slots = min(5, c.rune_slots + 1)
            self.notify("Novo espaço de runa!", "rune")
        if "flag" in entry:
            self.set_flag(entry["flag"])
        if self.world is not None and self.world.player is not None:
            self.world.player.apply_loadout()

    def read_document(self, doc_id, silent=False):
        if doc_id not in self.docs:
            self.docs.append(doc_id)
            lore = DB.lore.get(doc_id, {})
            for g in lore.get("grants", []):
                self.grant(g, None)
            if lore.get("flag"):
                self.set_flag(lore["flag"])
        if not silent:
            self.events.append(("document", doc_id))

    def found_secret(self, pid):
        if pid and pid not in self.secrets:
            self.secrets.append(pid)
            self.notify("Passagem secreta descoberta!", "secret")

    def on_break(self, prop):
        w = prop.world
        drop = prop.drop
        if drop:
            self.grant(drop, (prop.x, prop.y, prop.z))
        elif w is not None and w.rng.random() < 0.35:
            self.char.add_grace(w.rng.randint(2, 6) * (1 + DB.levels[w.level.id].get("act", 1)))

    def on_puzzle_solved(self, puzzle):
        g = puzzle.spec.get("grace", 80)
        self.char.add_grace(g)
        self.notify(f"Enigma resolvido! +{g} Graça", "puzzle")

    def on_trigger(self, event, trig):
        if event.startswith("flag:"):
            self.set_flag(event[5:])
        if event.startswith("dialogue:"):
            self.events.append(("dialogue", event[9:], None))

    # ------------------------------------------------------------------ combate
    def on_enemy_killed(self, enemy):
        c = self.char
        p = enemy.world.player if enemy.world else None
        mult = 1.0 + (p.stats.get("grace_gain") if p is not None else 0.0)
        if not getattr(enemy, "summoned", False):
            c.add_grace(enemy.grace_reward * mult)
        self.kills[enemy.enemy_id] = self.kills.get(enemy.enemy_id, 0) + 1
        if enemy.unique:
            self.set_flag(f"unique:{enemy.unique}")
        rng = enemy.world.rng if enemy.world else None
        for item, chance in enemy.d.get("drops", []):
            if rng is not None and rng.random() < chance * (2.0 if enemy.elite else 1.0):
                self.grant({"item": item} if item in DB.items else {"materials": 1}, None)
        if enemy.elite and enemy.d.get("elite", {}).get("reward"):
            for entry in enemy.d["elite"]["reward"]:
                self.grant(entry, None)
        self._check_quests(f"kill:{enemy.enemy_id}")

    def on_boss_defeated(self, boss):
        bd = DB.bosses[boss.boss_id]
        self.set_flag(f"boss:{boss.boss_id}")
        if boss.boss_id not in self.bosses:
            self.bosses.append(boss.boss_id)
        self.char.add_grace(bd.get("grace", 1000))
        self.notify(f"{bd['name']} derrotado. +{bd.get('grace', 1000)} Graça", "boss")
        for entry in bd.get("rewards", []):
            self.grant(entry, None)
        for f in bd.get("flags", []):
            self.set_flag(f)
        if bd.get("choice"):
            self.events.append(("boss_choice", boss.boss_id))
        self.events.append(("boss_defeated", boss.boss_id))

    def boss_choice(self, boss_id, choice):
        """Purificar (reduz corrupção, recompensa sagrada) ou absorver (poder profano, +corrupção)."""
        bd = DB.bosses[boss_id]
        c = self.char
        if choice == "purificar":
            c.add_corruption(-12)
            c.purified.append(boss_id)
            for entry in bd.get("purify_reward", []):
                self.grant(entry, None)
            self.notify("Você purificou o resquício. A chama arde mais clara.", "story")
        else:
            c.add_corruption(18)
            c.absorbed.append(boss_id)
            for entry in bd.get("absorb_reward", []):
                self.grant(entry, None)
            self.notify("Você absorveu o resquício. Algo sombrio desperta em você.", "story")
        self.set_flag(f"choice:{boss_id}:{choice}")

    def on_steal(self, player, tgt):
        w = player.world
        if w.rng.random() < 0.5:
            n = self.char.add_grace(w.rng.randint(4, 12))
            w.fx.push("steal", x=tgt.x, y=tgt.y + 1.4, z=tgt.z, amount=n)
        else:
            self.char.add_item("pedra_de_afiar")
            w.fx.push("steal", x=tgt.x, y=tgt.y + 1.4, z=tgt.z, amount=0)

    def on_player_death(self, player, level_id):
        self.deaths += 1
        c = self.char
        if c.grace > 0:
            self.lost_grace = {"level": level_id, "x": player.last_safe[0], "y": player.last_safe[1],
                               "z": player.last_safe[2], "amount": c.grace}
            c.grace = 0
        else:
            self.lost_grace = None

    def recover_lost_grace(self):
        if self.lost_grace:
            n = self.char.add_grace(self.lost_grace["amount"])
            self.char.grace_total -= n
            self.lost_grace = None
            self.notify(f"Graça recuperada: +{n}", "grace")

    # ------------------------------------------------------------------ altares, finais
    def use_altar(self, altar, player):
        kind = altar.altar_kind
        c = self.char
        if kind == "oracao":
            c.add_corruption(-8)
            altar.save_state(1)
            player.heal(player.max_hp)
            self.notify("Você reza. A corrupção recua um pouco.", "story")
        elif kind == "profano":
            c.add_corruption(10)
            altar.save_state(1)
            for entry in altar.spec.get("reward", []):
                self.grant(entry, None)
            self.notify("O altar bebe seu sangue e devolve poder.", "story")
        elif kind == "ciclo":
            frag = altar.spec.get("fragment")
            altar.save_state(1)
            self.grant({"fragment": frag}, None)
        elif kind == "trono":
            self.events.append(("ending_choice", None))
        elif kind == "escolha":
            self.events.append(("dialogue", altar.spec.get("dialogue"), None))

    def ending_options(self):
        c = self.char
        opts = []
        if c.corruption < 50 or len(c.purified) >= 3:
            opts.append("purificacao")
        if c.corruption >= 40 or len(c.absorbed) >= 3:
            opts.append("dominio")
        if len(c.cycle_fragments) >= 5:
            opts.append("ruptura")
        if not opts:
            opts.append("purificacao")
        return opts

    # ------------------------------------------------------------------ missões
    def quest_stage(self, qid):
        return self.quests.get(qid, 0)

    def set_quest(self, qid, stage):
        old = self.quests.get(qid, 0)
        self.quests[qid] = stage
        q = DB.quests.get(qid)
        if q and stage != old:
            if stage == "done":
                self.notify(f"Missão concluída: {q['name']}", "quest")
                for entry in q.get("reward", []):
                    self.grant(entry, None)
            else:
                self.notify(f"Missão atualizada: {q['name']}", "quest")

    def _check_quests(self, event):
        for qid, q in DB.quests.items():
            stage = self.quests.get(qid, 0)
            if stage == "done":
                continue
            for adv in q.get("advance", []):
                if adv.get("stage", 0) != stage:
                    continue
                if "on_all" in adv and all(self.has_flag(f) for f in adv["on_all"]):
                    self.set_quest(qid, adv["to"])
                    break
                if adv.get("on") == event:
                    self.set_quest(qid, adv["to"])
                    break

    def active_quests(self):
        out = []
        for qid, q in DB.quests.items():
            st = self.quests.get(qid, 0)
            if st == "done":
                out.append((qid, q["name"], "Concluída", True))
            elif str(st) in q.get("stages", {}) and (st != 0 or q.get("auto_start")):
                out.append((qid, q["name"], q["stages"][str(st)], False))
        return out

    # ------------------------------------------------------------------ condições (diálogos, nós)
    def check(self, cond):
        if not cond:
            return True
        c = self.char
        if "flag" in cond and not self.has_flag(cond["flag"]):
            return False
        if "not_flag" in cond and self.has_flag(cond["not_flag"]):
            return False
        if "flags" in cond and not all(self.has_flag(f) for f in cond["flags"]):
            return False
        if "corruption_min" in cond and c.corruption < cond["corruption_min"]:
            return False
        if "corruption_max" in cond and c.corruption > cond["corruption_max"]:
            return False
        if "has_item" in cond and not c.has_item(cond["has_item"]):
            return False
        if "class" in cond and c.class_id not in (cond["class"] if isinstance(cond["class"], list) else [cond["class"]]):
            return False
        if "quest" in cond:
            qid, st = cond["quest"]
            if self.quests.get(qid, 0) != st:
                return False
        if "bosses_min" in cond and len(self.bosses) < cond["bosses_min"]:
            return False
        if "fragments_min" in cond and len(c.cycle_fragments) < cond["fragments_min"]:
            return False
        if "grace_min" in cond and c.grace < cond["grace_min"]:
            return False
        return True

    def apply_effects(self, effects):
        out = []
        c = self.char
        for e in effects or []:
            if "set_flag" in e:
                self.set_flag(e["set_flag"])
            if "give" in e:
                self.grant(e["give"], None)
            if "take_item" in e:
                c.take_item(e["take_item"], e.get("n", 1))
            if "take_grace" in e:
                c.grace = max(0, c.grace - e["take_grace"])
            if "quest" in e:
                self.set_quest(e["quest"][0], e["quest"][1])
            if "corruption" in e:
                c.add_corruption(e["corruption"])
            if "pray" in e:
                key = f"rezou:{len(self.bosses)}"
                if not self.has_flag(key):
                    self.set_flag(key)
                    c.add_corruption(-e["pray"])
                    self.notify("A chama aceita sua prece. A corrupção recua.", "story")
                else:
                    self.notify("A chama já ouviu sua prece. Volte após derrotar outro senhor.", "hint")
            if "service" in e:
                out.append(("service", e["service"]))
            if "ending" in e:
                out.append(("ending", e["ending"]))
            if "travel" in e:
                out.append(("travel", e["travel"][0], e["travel"][1]))
        if self.world is not None and self.world.player is not None:
            self.world.player.apply_loadout()
        return out

    # ------------------------------------------------------------------ atos
    def act_unlocked(self, act_id):
        a = DB.acts[act_id]
        req = a.get("requires")
        return req is None or self.has_flag(req)

    # ------------------------------------------------------------------ serialização
    def to_dict(self):
        return {
            "version": 1, "char": self.char.to_dict(), "flags": sorted(self.flags), "props": self.props,
            "graces": self.graces, "last_grace": list(self.last_grace) if self.last_grace else None,
            "level": self.level, "spawn": self.spawn, "lost_grace": self.lost_grace, "docs": self.docs,
            "secrets": self.secrets, "quests": self.quests, "bosses": self.bosses, "deaths": self.deaths,
            "playtime": self.playtime, "created": self.created, "ending": self.ending, "kills": self.kills,
            "npc_seen": sorted(self.npc_seen),
        }

    @classmethod
    def from_dict(cls, d):
        s = cls(Character.from_dict(d["char"]))
        s.flags = set(d.get("flags", []))
        s.char._flags = s.flags
        s.props = d.get("props", {})
        s.graces = d.get("graces", {})
        lg = d.get("last_grace")
        s.last_grace = tuple(lg) if lg else None
        s.level = d.get("level", "santuario")
        s.spawn = d.get("spawn", "inicio")
        s.lost_grace = d.get("lost_grace")
        s.docs = d.get("docs", [])
        s.secrets = d.get("secrets", [])
        s.quests = d.get("quests", {})
        s.bosses = d.get("bosses", [])
        s.deaths = d.get("deaths", 0)
        s.playtime = d.get("playtime", 0.0)
        s.created = d.get("created", time.time())
        s.ending = d.get("ending")
        s.kills = d.get("kills", {})
        s.npc_seen = set(d.get("npc_seen", []))
        return s
