"""Calcula o 'loadout' efetivo do personagem: atributos, modificadores, arma, combos, habilidades e gatilhos.

É recalculado sempre que algo muda (equipar runa/arma/arte, desbloquear nó, subir de nível).
"""
from ...core.data import DB
from ..combat.moves import build_moveset
from ..stats import ATTRIBUTES, merge_mods
from . import grace_tree

CORRUPTION_TIERS = [
    {},
    {"ruin_mult": 0.08, "heal_mult": -0.05, "lifesteal": 0.005},
    {"ruin_mult": 0.16, "heal_mult": -0.1, "lifesteal": 0.01, "holy_mult": -0.08, "atk_mult": 0.04},
    {"ruin_mult": 0.28, "heal_mult": -0.18, "lifesteal": 0.02, "holy_mult": -0.18, "atk_mult": 0.08,
     "dmg_taken_mult": 0.06},
]


class Loadout:
    pass


def attribute_values(char, agg=None):
    agg = agg or grace_tree.aggregate(char)
    base = DB.classes[char.class_id]["attributes"]
    return {a: base.get(a, 10) + agg["attrs"].get(a, 0) for a in ATTRIBUTES}


def weapon_power(wdef, attrs, level):
    up = 1.0 + 0.09 * level
    scal = 1.0
    for a, k in wdef.get("scaling", {}).items():
        scal += k * (attrs.get(a, 10) - 10) / 30.0
    return {el: v * up * max(0.5, scal) for el, v in wdef.get("base", {"fisico": 10}).items()}


def spell_power(wdef, attrs, level, school):
    base = wdef.get("spell_base", 8.0) * (1.0 + 0.09 * level)
    attr = {"intelecto": "intelecto", "fe": "fe"}.get(school, "intelecto")
    return base * (1.0 + (attrs.get(attr, 10) - 10) / 22.0)


def compute(char):
    L = Loadout()
    cdef = DB.classes[char.class_id]
    agg = grace_tree.aggregate(char)
    attrs = attribute_values(char, agg)
    L.attrs = attrs
    L.cls = cdef
    wdef = DB.weapons[char.weapon]
    L.weapon_id = char.weapon
    L.weapon = wdef
    L.family = wdef["family"]
    fam = DB.families[L.family]
    L.weapon_level = char.weapon_level()
    L.weapon_power = weapon_power(wdef, attrs, L.weapon_level)
    L.spell_power = {s: spell_power(wdef, attrs, L.weapon_level, s) for s in ("intelecto", "fe")}
    L.block_reduction = cdef.get("block_reduction", wdef.get("block", fam.get("block", 0.55)))
    L.block_posture = cdef.get("block_posture", fam.get("block_posture", 1.0))
    # passivas da classe
    passive_mods, passive_triggers, flags = [], [], set(cdef.get("flags", []))
    for pid in cdef["passives"]:
        p = DB.abilities[pid]
        passive_mods.append(p.get("mods", {}))
        passive_triggers.extend(p.get("triggers", []))
        flags |= set(p.get("flags", []))
    # runas
    rune_mods, rune_triggers, rune_moves = [], [], []
    for rid in char.runes_equipped:
        r = DB.runes[rid]
        rune_mods.append(r.get("mods", {}))
        for e in r["effects"]:
            if e.get("type") in ("move_effect", "replace_move", "add_transition"):
                rune_moves.append(e)
            elif e.get("type") == "flag":
                flags.add(e["flag"])
            else:
                t = dict(e)
                t.setdefault("source", rid)
                rune_triggers.append(t)
    flags |= agg["flags"]
    L.flags = flags
    corr = CORRUPTION_TIERS[char.corruption_tier]
    L.mods = merge_mods(agg["mods"], wdef.get("mods", {}), corr, *passive_mods, *rune_mods)
    L.mods["crit_chance"] = L.mods.get("crit_chance", 0.0) + wdef.get("crit", 0.0)
    L.mods["fp_cost_mult"] = L.mods.get("fp_cost_mult", 0.0)
    # recursos
    # cada nível também dá +6 de vida: só com vigor, a vida mal crescia (200 → 256 até o Ato V)
    L.hp_max = 80 + attrs["vigor"] * 8 + (char.level - 1) * 6 + L.mods.get("hp_max", 0.0)
    L.fp_max = 40 + attrs["mente"] * 5 + L.mods.get("fp_max", 0.0)
    L.posture_max = 55 + attrs["vigor"] * 1.5 + attrs["forca"] * 1.5 + L.mods.get("posture_max", 0.0)
    L.def_flat = attrs["vigor"] * 0.15 + attrs["forca"] * 0.1
    L.dodge_charges = 2 + int(L.mods.get("dodge_charges", 0)) + cdef.get("dodge_charges_bonus", 0)
    L.flask_heal = 0.4 + 0.06 * char.flask_level + L.mods.get("flask_heal", 0.0)
    # combos
    overrides = dict(cdef.get("moveset", {}))
    L.moveset = build_moveset(L.family, overrides, agg["move_effects"] + rune_moves)
    beast = cdef.get("beast_moveset")
    if beast:
        L.beast_moveset = build_moveset(beast["family"], beast.get("overrides", {}), agg["move_effects"] + rune_moves)
    else:
        L.beast_moveset = None
    # habilidades
    unlocks = agg["unlocks"] | set(char.nodes)
    L.abilities = []
    for aid in cdef["abilities"]:
        a = DB.abilities[aid]
        req = a.get("unlock")
        L.abilities.append((aid, req is None or req in unlocks))
    u = DB.abilities[cdef["ultimate"]]
    L.ultimate = (cdef["ultimate"], u.get("unlock") is None or u.get("unlock") in unlocks)
    art = char.art_for()
    L.art = art if art and art in DB.arts and char.art_compatible(art) else None
    L.triggers = agg["triggers"] + passive_triggers + rune_triggers
    L.resource = cdef.get("resource")
    return L
