"""Dados persistentes do personagem: classe, aparência, nível, Graça, árvore, equipamentos, inventário."""
from ...core.data import DB

BASE_RUNE_SLOTS = 3
MAX_RUNE_SLOTS = 5


def level_cost(level):
    """Graça necessária para ir do nível 'level' ao seguinte."""
    return int(70 * (1.115 ** (level - 1)) + 25 * (level - 1))


class Character:
    def __init__(self, name="Portador", class_id="guerreiro", appearance=None):
        self.name = name
        self.class_id = class_id
        self.appearance = appearance or {"skin": 2, "hair": 0, "hair_color": 0, "variant": 0}
        self.level = 1
        self.grace = 0                 # Graça acumulada não gasta (moeda de evolução)
        self.grace_total = 0
        self.bonus_points = 0          # pontos extras (relíquias, chefes)
        self.nodes = []                # nós da árvore desbloqueados (ordem importa para respec)
        cdef = DB.classes[class_id]
        self.weapon = cdef["weapon"]
        self.weapons = [cdef["weapon"]]
        self.weapon_levels = {cdef["weapon"]: 0}
        self.arts = list(cdef.get("arts", []))
        default_art = DB.weapons[self.weapon].get("art")
        if default_art and default_art not in self.arts:
            self.arts.append(default_art)
        self.art_equipped = {self.weapon: default_art} if default_art else {}
        self.runes = list(cdef.get("runes", []))
        self.runes_equipped = []
        self.rune_slots = BASE_RUNE_SLOTS
        self.items = {"frasco_brasa": 0}
        self.flasks_hp = 3
        self.flasks_fp = 2
        self.flask_level = 0
        self.materials = 0             # Fragmentos de Forja
        self.corruption = 0.0
        self.purified = []
        self.absorbed = []
        self.cycle_fragments = []
        self.respecs = 0
        self._flags = set()

    # ------------------------------------------------------------------ evolução
    @property
    def points_total(self):
        return self.level - 1 + self.bonus_points + DB.classes[self.class_id].get("start_points", 0)

    @property
    def points_spent(self):
        nodes = DB.tree["nodes"]
        return sum(nodes[n].get("cost", 1) for n in self.nodes if not nodes[n].get("free"))

    @property
    def points_available(self):
        return self.points_total - self.points_spent

    def next_level_cost(self):
        return level_cost(self.level)

    def can_level_up(self):
        return self.grace >= self.next_level_cost()

    def level_up(self):
        cost = self.next_level_cost()
        if self.grace < cost:
            return False
        self.grace -= cost
        self.level += 1
        return True

    def add_grace(self, amount):
        amount = int(round(amount))
        self.grace += amount
        self.grace_total += amount
        return amount

    def weapon_level(self, wid=None):
        return self.weapon_levels.get(wid or self.weapon, 0)

    # ------------------------------------------------------------------ itens
    def add_item(self, item_id, n=1):
        self.items[item_id] = self.items.get(item_id, 0) + n

    def take_item(self, item_id, n=1):
        if self.items.get(item_id, 0) < n:
            return False
        self.items[item_id] -= n
        if self.items[item_id] <= 0:
            del self.items[item_id]
        return True

    def has_item(self, item_id, n=1):
        return self.items.get(item_id, 0) >= n

    def add_weapon(self, wid):
        if wid not in self.weapons:
            self.weapons.append(wid)
            self.weapon_levels.setdefault(wid, 0)
            art = DB.weapons[wid].get("art")
            if art and art not in self.arts:
                self.arts.append(art)
            if art:
                self.art_equipped.setdefault(wid, art)
            return True
        return False

    def add_rune(self, rid):
        if rid not in self.runes:
            self.runes.append(rid)
            return True
        return False

    def add_art(self, aid):
        if aid not in self.arts:
            self.arts.append(aid)
            return True
        return False

    # ------------------------------------------------------------------ runas
    def rune_problem(self, rid, replacing=None):
        """Motivo para não poder equipar (None = pode)."""
        if rid not in self.runes:
            return "Runa não obtida."
        eq = [r for r in self.runes_equipped if r != replacing]
        if rid in eq:
            return "Já equipada."
        rd = DB.runes[rid]
        if len(eq) >= self.rune_slots:
            return "Sem espaços livres."
        if rd["rarity"] == "lendaria" and any(DB.runes[r]["rarity"] == "lendaria" for r in eq):
            return "Apenas uma runa lendária por vez."
        group = rd.get("exclusive")
        if group and any(DB.runes[r].get("exclusive") == group for r in eq):
            return "Conflita com outra runa equipada (mesmo grupo)."
        req = rd.get("requires_class")
        if req and self.class_id not in req:
            return "Classe incompatível."
        return None

    def equip_rune(self, rid, replacing=None):
        if self.rune_problem(rid, replacing):
            return False
        if replacing in self.runes_equipped:
            self.runes_equipped[self.runes_equipped.index(replacing)] = rid
        else:
            self.runes_equipped.append(rid)
        return True

    def unequip_rune(self, rid):
        if rid in self.runes_equipped:
            self.runes_equipped.remove(rid)
            return True
        return False

    def art_for(self, wid=None):
        return self.art_equipped.get(wid or self.weapon)

    def art_compatible(self, aid, wid=None):
        fam = DB.weapons[wid or self.weapon]["family"]
        return fam in DB.arts[aid].get("families", []) or "*" in DB.arts[aid].get("families", [])

    def equip_art(self, aid, wid=None):
        wid = wid or self.weapon
        if aid not in self.arts or not self.art_compatible(aid, wid):
            return False
        self.art_equipped[wid] = aid
        return True

    def equip_weapon(self, wid):
        if wid not in self.weapons:
            return False
        self.weapon = wid
        return True

    # ------------------------------------------------------------------ corrupção
    @property
    def corruption_tier(self):
        c = self.corruption
        return 0 if c < 25 else 1 if c < 50 else 2 if c < 75 else 3

    def add_corruption(self, amount):
        self.corruption = max(0.0, min(100.0, self.corruption + amount))

    # ------------------------------------------------------------------ serialização
    FIELDS = ("name", "class_id", "appearance", "level", "grace", "grace_total", "bonus_points", "nodes", "weapon",
              "weapons", "weapon_levels", "arts", "art_equipped", "runes", "runes_equipped", "rune_slots", "items",
              "flasks_hp", "flasks_fp", "flask_level", "materials", "corruption", "purified", "absorbed",
              "cycle_fragments", "respecs")

    def to_dict(self):
        import copy
        return {k: copy.deepcopy(getattr(self, k)) for k in self.FIELDS}

    @classmethod
    def from_dict(cls, d):
        c = cls(d.get("name", "Portador"), d.get("class_id", "guerreiro"), d.get("appearance"))
        import copy
        for k in cls.FIELDS:
            if k in d:
                setattr(c, k, copy.deepcopy(d[k]))
        return c
