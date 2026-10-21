"""Monta um World a partir dos dados da fase e do progresso da sessão."""
import math

from ...core.data import DB
from ..player import Player
from ..npc import NPC, Pickup, LostGrace
from .level import Level
from .props import PROP_TYPES
from .puzzles import Puzzle
from .world import World


def spawn_position(level, spawn_id):
    for e in level.entities:
        if e.get("id") == spawn_id and e.get("type") in ("spawn", "grace"):
            off = e.get("offset", (0.0, -1.0) if e.get("type") == "grace" else (0.0, 0.0))
            return e["x"] + off[0], e["z"] + off[1], math.radians(e.get("angle", -90))
    for e in level.entities:
        if e.get("type") == "spawn":
            return e["x"], e["z"], math.radians(e.get("angle", -90))
    raise KeyError(f"{level.id}: ponto de entrada '{spawn_id}' não encontrado")


def build_world(session, level_id, spawn_id="inicio", seed=None, player=None):
    level = Level(DB.levels[level_id])
    w = World(level, session, seed=seed)
    if session is not None:
        session.world = w
        session.level = level_id
        session.spawn = spawn_id
    env = DB.environments.get(level.env, {})
    w.night = env.get("night", False)
    w.arena_center = tuple(level.data.get("arena_center", (level.width / 2, level.depth / 2)))
    w.puzzles = []
    w._groups_spawned = set()
    deferred = {}
    condicionais = []   # props/NPCs com "if" ainda falso: reavaliados quando um chefe cai
    for spec in level.entities:
        t = spec.get("type")
        if t == "enemy":
            if spec.get("spawn_on"):
                deferred.setdefault(spec["spawn_on"], []).append(spec)
                continue
            _spawn_enemy(w, spec)
        elif t == "boss":
            if session is not None and session.has_flag(f"boss:{spec['boss']}"):
                continue
            b = w.spawn_enemy(spec["boss"], spec["x"], spec["z"])
            b.facing = math.radians(spec.get("angle", -90))
        elif t == "npc":
            if session is not None and not session.check(spec.get("if")):
                condicionais.append(spec)
                continue
            _spawn_npc(w, spec)
        elif t == "pickup":
            w.spawn(Pickup(spec["x"], spec["z"], 0.0, spec.get("loot", {}), auto=spec.get("auto", False),
                           pid=spec.get("id"), sprite=spec.get("sprite")))
        elif t in PROP_TYPES:
            if spec.get("if") and session is not None and not session.check(spec["if"]):
                condicionais.append(spec)
                continue
            w.spawn(PROP_TYPES[t](spec))
        elif t in (None, "note"):
            continue
        else:
            raise KeyError(f"{level_id}: tipo de entidade desconhecido '{t}'")
    for ev, specs in deferred.items():
        def make(specs=specs):
            def handler(**kw):
                for s in specs:
                    _spawn_enemy(w, s, aggro=True)
            return handler
        w.bus.on(ev, make())
    if condicionais and session is not None:
        def revelar(**kw):
            # portal de volta, Graça e altar pós-chefe aparecem na hora, sem precisar recarregar a fase
            for spec in [c for c in condicionais if session.check(c.get("if"))]:
                condicionais.remove(spec)
                if spec["type"] == "npc":
                    _spawn_npc(w, spec)
                else:
                    w.spawn(PROP_TYPES[spec["type"]](spec))
                w.fx.push("reveal", x=spec["x"], y=w.level.ground_at(spec["x"], spec["z"]) or 0.0, z=spec["z"])
        w.bus.on("boss_defeated", revelar)
    for ps in level.data.get("puzzles", []):
        w.puzzles.append(Puzzle(w, ps))
    # jogador
    if session is not None:
        x, z, ang = spawn_position(level, spawn_id)
        p = player or Player(session.char, x, z)
        p.x, p.z = x, z
        g = level.ground_at(x, z)
        p.y = g if g is not None else 0.0
        p.facing = ang
        p.last_safe = (p.x, p.y, p.z)
        w.spawn(p)
        lg = session.lost_grace
        if lg and lg["level"] == level_id:
            w.spawn(LostGrace(lg["x"], lg["z"], lg["y"], lg["amount"]))
    return w


def _spawn_npc(w, spec):
    n = NPC(spec["npc"], spec["x"], spec["z"])
    if "angle" in spec:
        n.facing = math.radians(spec["angle"])
    w.spawn(n)
    return n


def _spawn_enemy(w, spec, aggro=False):
    s = w.session
    uniq = spec.get("unique")
    if uniq and s is not None and s.has_flag(f"unique:{uniq}"):
        return None
    e = w.spawn_enemy(spec["enemy"], spec["x"], spec["z"], elite=spec.get("elite", False), unique=uniq,
                      aggro=aggro)
    e.group = spec.get("group")
    e.loot = spec.get("loot", [])     # saque fixo deste inimigo no mapa (ex.: a manivela do Capataz)
    if e.group:
        w._groups_spawned.add(e.group)
    if "angle" in spec:
        e.facing = math.radians(spec["angle"])
    if spec.get("patrol"):
        e.brain.patrol_points = [tuple(p) for p in spec["patrol"]]
    return e
