"""Golpes e grafo de combos.

Um golpe (Move) é um dicionário de dados (ver data/moves/*.json). O MoveSet de um personagem é
montado a partir da família da arma + golpes da classe + modificações da árvore de Graça:

  - "start": entradas iniciais (L, H, DL, DH, RL, AL, AH, BH, C, X ...);
  - "next" de cada golpe: transições por entrada (L/H) dentro da janela de cancelamento;
  - substituições (replace_move): trocam um golpe por uma versão alternativa;
  - transições extras (add_transition): criam extensões de combo;
  - efeitos por golpe/etiqueta (move_effect): adicionam elementos, status ou explosões.
"""
from ...core.data import DB

INPUT_NAMES = {
    "L": "Leve", "H": "Pesado", "DL": "Esquiva + Leve", "DH": "Esquiva + Pesado", "RL": "Corrida + Leve",
    "RH": "Corrida + Pesado", "AL": "Aéreo Leve", "AH": "Aéreo Pesado", "BH": "Trás + Pesado",
    "FH": "Frente + Pesado", "C": "Contra-ataque", "X": "Execução",
}


class Move:
    __slots__ = ("id", "d", "anim", "dur", "type", "hits", "moves", "cancel", "dodge_cancel", "free", "next",
                 "charge", "spawns", "iframes", "armor", "fp", "track", "teleport", "tags", "jump", "hang",
                 "shake", "sound", "air", "name", "aim", "lock_move", "land", "magic", "alts", "effects",
                 "hold_loop", "anim_speed")

    def __init__(self, d):
        self.d = d
        self.id = d["id"]
        self.name = d.get("name", self.id)
        self.anim = d.get("anim", "slash_r")
        self.dur = float(d.get("dur", 0.5))
        self.type = d.get("type", "light")
        self.hits = d.get("hits", [])
        self.moves = d.get("move", [])
        self.cancel = float(d.get("cancel", self.dur * 0.6))
        self.dodge_cancel = float(d.get("dodge_cancel", self.cancel * 0.7))
        self.free = float(d.get("free", self.dur * 0.85))
        self.next = dict(d.get("next", {}))
        self.charge = d.get("charge")
        self.spawns = d.get("spawn", [])
        self.iframes = d.get("iframes")
        self.armor = d.get("armor")
        self.fp = float(d.get("fp", 0.0))
        self.track = float(d.get("track", 0.35))
        self.teleport = d.get("teleport")
        self.tags = set(d.get("tags", []))
        self.jump = d.get("jump")
        self.hang = d.get("hang", False)
        self.shake = d.get("shake", 0.0)
        self.sound = d.get("sound")
        self.air = d.get("air", False) or self.type in ("air",)
        self.aim = d.get("aim", True)
        self.lock_move = d.get("lock_move", True)
        self.land = d.get("land")            # golpe disparado ao tocar o chão (golpes de mergulho)
        self.magic = d.get("magic")          # "intelecto" / "fe": escala com feitiçaria
        self.alts = d.get("alts", {})
        self.effects = d.get("effects", [])  # efeitos especiais (cura, bônus, transformação...)
        self.hold_loop = d.get("hold_loop")
        self.anim_speed = d.get("anim_speed", 1.0)

    def __repr__(self):
        return f"<Move {self.id}>"


_move_cache = {}


def get_move(mid):
    m = _move_cache.get(mid)
    if m is None:
        m = _move_cache[mid] = Move(DB.moves[mid])
    return m


def clear_cache():
    _move_cache.clear()


class MoveSet:
    def __init__(self, starts, replacements=None, transitions=None, effects=None):
        self.starts = dict(starts)
        self.replacements = dict(replacements or {})
        self.transitions = {k: dict(v) for k, v in (transitions or {}).items()}
        self.effects = list(effects or [])

    def resolve(self, mid):
        seen = set()
        while mid in self.replacements and mid not in seen:
            seen.add(mid)
            mid = self.replacements[mid]
        return mid

    def get(self, mid):
        if mid is None or mid not in DB.moves:
            return None
        return get_move(self.resolve(mid))

    def start(self, inp):
        return self.get(self.starts.get(inp))

    def next(self, move, inp):
        extra = self.transitions.get(move.id, {})
        if inp in extra:
            return self.get(extra[inp])
        return self.get(move.next.get(inp))

    def has_start(self, inp):
        return self.starts.get(inp) in DB.moves

    def effects_for(self, move):
        """Efeitos extras (árvore/runas) aplicáveis a este golpe."""
        out = []
        for e in self.effects:
            if "move" in e and e["move"] != move.id:
                continue
            if "tag" in e and e["tag"] not in move.tags and e["tag"] != move.type:
                continue
            out.append(e)
        return out

    def routes(self, max_len=6):
        """Lista as rotas de combo a partir de cada entrada inicial (para a tela de técnicas e testes)."""
        out = []

        def walk(move, path, depth):
            path = path + [move.id]
            nxt = dict(move.next)
            nxt.update(self.transitions.get(move.id, {}))
            ends = True
            if depth < max_len:
                for inp, mid in nxt.items():
                    m2 = self.get(mid)
                    if m2 is not None and m2.id not in path:
                        ends = False
                        walk(m2, path, depth + 1)
            if ends:
                out.append(path)

        for inp, mid in self.starts.items():
            m = self.get(mid)
            if m is not None:
                walk(m, [f"[{inp}]"], 1)
        return out


def build_moveset(family_id, class_overrides=None, tree_effects=(), transformed=False):
    fam = DB.families[family_id]
    starts = dict(fam.get("start", {}))
    if class_overrides:
        starts.update(class_overrides)
    replacements, transitions, effects = {}, {}, []
    for eff in tree_effects:
        t = eff.get("type")
        if t == "replace_move":
            replacements[eff["from"]] = eff["to"]
        elif t == "add_transition":
            transitions.setdefault(eff["move"], {})[eff["input"]] = eff["to"]
        elif t == "add_start":
            if eff.get("family") in (None, family_id):
                starts[eff["input"]] = eff["to"]
        elif t == "move_effect":
            effects.append(eff)
    return MoveSet(starts, replacements, transitions, effects)
