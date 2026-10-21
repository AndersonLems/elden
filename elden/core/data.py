"""Banco de dados do jogo: carrega e valida os arquivos JSON de /data.

Tudo que é conteúdo (classes, armas, golpes, runas, árvore de Graça, inimigos, fases, diálogos)
vive em JSON. O código do motor só interpreta essas definições.
"""
import glob
import json
import os

from .paths import DATA_DIR


class DataError(Exception):
    pass


def _load(path):
    with open(path, encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise DataError(f"{os.path.basename(path)}: JSON inválido ({e})") from e


def _require(obj, keys, where):
    for k in keys:
        if k not in obj:
            raise DataError(f"{where}: campo obrigatório '{k}' ausente")


class Database:
    """Acesso preguiçoso às coleções. Ex.: DB.classes['guerreiro']."""

    _FILES = {
        "themes": "themes.json",
        "classes": "classes.json",
        "weapons": "weapons.json",
        "families": "families.json",
        "arts": "arts.json",
        "abilities": "abilities.json",
        "runes": "runes.json",
        "tree": "grace_tree.json",
        "enemies": "enemies.json",
        "bosses": "bosses.json",
        "items": "items.json",
        "quests": "quests.json",
        "lore": "lore.json",
        "npcs": "npcs.json",
        "environments": "environments.json",
        "acts": "acts.json",
    }

    def __init__(self):
        self._cache = {}

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        if name in self._FILES:
            if name not in self._cache:
                self._cache[name] = _load(os.path.join(DATA_DIR, self._FILES[name]))
            return self._cache[name]
        if name == "moves":
            if "moves" not in self._cache:
                moves = {}
                for p in sorted(glob.glob(os.path.join(DATA_DIR, "moves", "*.json"))):
                    for mid, m in _load(p).items():
                        if mid in moves:
                            raise DataError(f"golpe duplicado: {mid}")
                        m["id"] = mid
                        moves[mid] = m
                self._cache["moves"] = moves
            return self._cache["moves"]
        if name == "levels":
            if "levels" not in self._cache:
                lv = {}
                for p in sorted(glob.glob(os.path.join(DATA_DIR, "levels", "*.json"))):
                    d = _load(p)
                    lv[d["id"]] = d
                self._cache["levels"] = lv
            return self._cache["levels"]
        if name == "dialogues":
            if "dialogues" not in self._cache:
                dl = {}
                for p in sorted(glob.glob(os.path.join(DATA_DIR, "dialogues", "*.json"))):
                    dl.update(_load(p))
                self._cache["dialogues"] = dl
            return self._cache["dialogues"]
        raise AttributeError(name)

    def reload(self):
        self._cache.clear()

    # ------------------------------------------------------------------ validação
    def validate(self):
        """Confere referências cruzadas. Devolve lista de problemas (vazia = tudo certo)."""
        problems = []

        def check(cond, msg):
            if not cond:
                problems.append(msg)

        moves = self.moves
        for mid, m in moves.items():
            for k in ("anim", "dur"):
                check(k in m, f"golpe {mid}: falta '{k}'")
            for inp, nxt in m.get("next", {}).items():
                check(nxt in moves, f"golpe {mid}: transição '{inp}' -> '{nxt}' inexistente")
            for alt in m.get("alts", {}).values():
                check(alt in moves, f"golpe {mid}: alternativa '{alt}' inexistente")
        for fid, fam in self.families.items():
            for inp, mid in fam.get("start", {}).items():
                check(mid in moves, f"família {fid}: início '{inp}' -> '{mid}' inexistente")
        for wid, w in self.weapons.items():
            check(w.get("family") in self.families, f"arma {wid}: família inválida")
        for cid, c in self.classes.items():
            _require(c, ("name", "weapon", "attributes", "abilities", "ultimate", "passives"), f"classe {cid}")
            check(c["weapon"] in self.weapons, f"classe {cid}: arma inicial inexistente")
            for a in c["abilities"] + [c["ultimate"]]:
                check(a in self.abilities, f"classe {cid}: habilidade {a} inexistente")
            for mid in c.get("moveset", {}).values():
                check(mid in moves, f"classe {cid}: golpe {mid} inexistente")
            check(len(c["abilities"]) >= 3, f"classe {cid}: precisa de 3 habilidades ativas")
            check(len(c["passives"]) >= 2, f"classe {cid}: precisa de 2 passivas")
        for aid, a in self.arts.items():
            check("move" in a and a["move"] in moves, f"arte {aid}: golpe inválido")
        for aid, a in self.abilities.items():
            if "move" in a:
                check(a["move"] in moves, f"habilidade {aid}: golpe {a['move']} inexistente")
        cats = {}
        for rid, r in self.runes.items():
            _require(r, ("name", "category", "rarity", "effects"), f"runa {rid}")
            cats.setdefault(r["category"], 0)
            cats[r["category"]] += 1
        for cat in ("ofensiva", "defensiva", "mobilidade", "arcana", "sangue", "sombras", "maquinas", "feras", "divina"):
            check(cats.get(cat, 0) >= 3, f"runas: categoria {cat} com menos de 3")
        for nid, n in self.tree["nodes"].items():
            for req in n.get("requires", []):
                check(req in self.tree["nodes"], f"árvore {nid}: requisito {req} inexistente")
            for eff in n.get("effects", []):
                if eff.get("type") in ("replace_move", "add_transition"):
                    for k in ("from", "to", "move"):
                        if k in eff:
                            check(eff[k] in moves, f"árvore {nid}: golpe {eff[k]} inexistente")
        for lid, lv in self.levels.items():
            check(lv.get("theme") in self.themes, f"fase {lid}: tema inválido")
        return problems


DB = Database()
