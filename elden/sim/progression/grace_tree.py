"""Árvore de Graça: caminhos CORPO, ESPÍRITO e RUÍNA + árvores de técnicas de cada classe.

Cada nó tem custo em pontos, requisitos e efeitos:
  attr (atributo), mods (modificadores), replace_move / add_transition / add_start / move_effect
  (alteram o grafo de combos), trigger (gatilhos como os das runas), unlock (habilidades, espaços de
  runa), flag (comportamentos especiais) e corruption.
"""
from ...core.data import DB

PATHS = ("corpo", "espirito", "ruina")
PATH_NAMES = {"corpo": "CORPO", "espirito": "ESPÍRITO", "ruina": "RUÍNA"}


def nodes():
    return DB.tree["nodes"]


def node_visible(char, nid):
    n = nodes()[nid]
    cls = n.get("class")
    return cls is None or cls == char.class_id


def unlock_problem(char, nid):
    n = nodes().get(nid)
    if n is None:
        return "Nó inexistente."
    if nid in char.nodes:
        return "Já desbloqueado."
    if not node_visible(char, nid):
        return "Pertence a outra classe."
    reqs = n.get("requires", [])
    mode = n.get("requires_mode", "all")
    if reqs:
        ok = [r in char.nodes for r in reqs]
        if (mode == "all" and not all(ok)) or (mode == "any" and not any(ok)):
            return "Requisitos não cumpridos."
    grp = n.get("exclusive")
    if grp and any(nodes()[o].get("exclusive") == grp for o in char.nodes):
        return "Especialização já escolhida."
    if n.get("min_level", 0) > char.level:
        return f"Requer nível {n['min_level']}."
    flag = n.get("requires_flag")
    if flag and flag not in getattr(char, "_flags", set()):
        return "Ainda bloqueado pela história."
    if char.points_available < n.get("cost", 1):
        return "Pontos de Graça insuficientes."
    return None


def unlock(char, nid):
    if unlock_problem(char, nid):
        return False
    char.nodes.append(nid)
    n = nodes()[nid]
    for eff in n.get("effects", []):
        if eff.get("type") == "corruption":
            char.add_corruption(eff.get("amount", 0))
        if eff.get("type") == "rune_slot":
            char.rune_slots = min(5, char.rune_slots + 1)
    return True


def respec(char):
    """Devolve todos os pontos (nós iniciais gratuitos da classe permanecem)."""
    keep = [n for n in char.nodes if nodes()[n].get("free")]
    removed = [n for n in char.nodes if n not in keep]
    for nid in removed:
        for eff in nodes()[nid].get("effects", []):
            if eff.get("type") == "corruption":
                char.add_corruption(-eff.get("amount", 0) * 0.5)   # metade da corrupção permanece
            if eff.get("type") == "rune_slot":
                char.rune_slots = max(3, char.rune_slots - 1)
    char.nodes = keep
    while len(char.runes_equipped) > char.rune_slots:
        char.runes_equipped.pop()
    char.respecs += 1
    return len(removed)


def aggregate(char):
    """Soma os efeitos dos nós desbloqueados."""
    out = {"attrs": {}, "mods": {}, "move_effects": [], "triggers": [], "unlocks": set(), "flags": set()}
    for nid in char.nodes:
        for eff in nodes()[nid].get("effects", []):
            t = eff.get("type")
            if t == "attr":
                out["attrs"][eff["attr"]] = out["attrs"].get(eff["attr"], 0) + eff.get("amount", 1)
            elif t == "mods":
                for k, v in eff["mods"].items():
                    out["mods"][k] = out["mods"].get(k, 0.0) + v
            elif t in ("replace_move", "add_transition", "add_start", "move_effect"):
                out["move_effects"].append(eff)
            elif t == "trigger":
                out["triggers"].append(eff)
            elif t == "unlock":
                out["unlocks"].add(eff["what"])
            elif t == "flag":
                out["flags"].add(eff["flag"])
    return out
