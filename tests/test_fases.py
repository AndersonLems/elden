"""Testes estruturais das fases: alcance a partir da entrada, saídas válidas e puzzles resolvíveis.

Rodar: python3 -m unittest tests.test_fases -v
"""
import itertools
import math
import unittest
from collections import deque

from util import new_session, world_for, step
from elden.core.data import DB
from elden.sim.ai.navigation import NavGrid, STEP_HEIGHT
from elden.sim.world.level import Level

# tipos que o jogador precisa alcançar (interagir ou passar)
ALCANCAVEIS = {"spawn", "grace", "exit", "npc", "document", "chest", "lever", "dial", "seq_button", "valve", "altar",
               "gear", "gear_socket", "mirror", "portal", "door", "breakable_wall", "boss", "power_node"}
# props que ficam em cima de chão bloqueado por eles mesmos ou em paredes de propósito
SEM_ALCANCE = {"decor", "hazard", "trigger", "breakable", "arena_pillar", "emitter", "crystal", "plate", "platform",
               "enemy", "pickup"}


def entrada(level_id):
    lv = DB.levels[level_id]
    for e in lv["entities"]:
        if e.get("type") == "spawn" and e.get("id") in ("inicio", "entrada"):
            return e["id"]
    return next(e["id"] for e in lv["entities"] if e.get("type") == "spawn")


class _Ligacao:
    """Atalho do alcance: tocar uma célula de `origem` torna alcançáveis as células de `destino`."""
    def __init__(self, origem, destino):
        self.origem, self.destino = origem, destino


PULO = 1.4   # pulo do jogador sobe ~1,54 (JUMP_SPEED² / 2·GRAVITY); margem para a borda


def celulas_da_porta(e):
    hx, hz = e.get("half", (0.5, 0.5))
    return {(x, z) for x in range(int(e["x"] - hx - 1), int(e["x"] + hx) + 2)
            for z in range(int(e["z"] - hz - 1), int(e["z"] + hz) + 2)
            if abs(x + 0.5 - e["x"]) < hx + 0.01 and abs(z + 0.5 - e["z"]) < hz + 0.01}


def alcance(level, bloqueadas=frozenset()):
    """Células alcançáveis a partir da entrada, ignorando portas (os puzzles as abrem). Plataformas móveis ficam fora."""
    nav = NavGrid(level)
    sx, sz = level.spawn_cell
    seen = {(sx, sz)}
    q = deque([(sx, sz)])
    # plataformas móveis: cada parada vira um conjunto de células de embarque/desembarque
    paradas = []
    for e in level.entities:
        if e.get("type") == "platform":
            hx, hz = e.get("half", (1.0, 1.0))
            celulas = set()
            for (px, py, pz) in e.get("points", []):
                for cx in range(int(px - hx) - 1, int(px + hx) + 2):
                    for cz in range(int(pz - hz) - 1, int(pz + hz) + 2):
                        if 0 <= cx < nav.w and 0 <= cz < nav.d and nav.ok[cz][cx] and nav.h[cz][cx] <= py + PULO:
                            celulas.add((cx, cz))
            paradas.append(celulas)
    # portais ligados: quem chega a um portal sai ao sul do portal ligado
    portais = {e.get("id"): e for e in level.entities if e.get("type") == "portal"}
    for e in portais.values():
        o = portais.get(e.get("link"))
        if o is None:
            continue
        perto = lambda p: {(int(p["x"]) + dx, int(p["z"]) + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1)}
        chegada = (int(o["x"]), int(o["z"] - 0.9))
        paradas.append(_Ligacao(perto(e), {chegada}))
    paradas = [p if isinstance(p, _Ligacao) else _Ligacao(p, p) for p in paradas]
    while q or any(p.origem & seen and not p.destino <= seen for p in paradas):
        if not q:
            for p in paradas:
                if p.origem & seen:
                    for cell in p.destino - seen:
                        seen.add(cell)
                        q.append(cell)
            continue
        x, z = q.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = x + dx, z + dz
            if (nx, nz) in seen or (nx, nz) in bloqueadas or not (0 <= nx < nav.w and 0 <= nz < nav.d) or not nav.ok[nz][nx]:
                continue
            subida = nav.h[nz][nx] - nav.h[z][x]
            rampa = nav.ramp[z][x] or nav.ramp[nz][nx]
            # anda (degrau/rampa), sobe pulando até PULO ou desce de qualquer altura
            if subida <= max(PULO, 1.05 if rampa else STEP_HEIGHT):
                seen.add((nx, nz))
                q.append((nx, nz))
    return seen


class TestFases(unittest.TestCase):
    def test_saidas_apontam_para_spawns(self):
        for lid, lv in DB.levels.items():
            for e in lv["entities"]:
                if e.get("type") != "exit" or e["to"] not in DB.levels:
                    continue
                alvo = DB.levels[e["to"]]
                ids = {x.get("id") for x in alvo["entities"] if x.get("type") in ("spawn", "grace")}
                self.assertIn(e.get("spawn", "start"), ids, f"{lid}: saída {e.get('id')} → {e['to']}")

    def test_puzzles_referenciam_props(self):
        for lid, lv in DB.levels.items():
            ids = {e.get("id") for e in lv["entities"]}
            for pz in lv.get("puzzles", []):
                for key in ("props", "open", "activate", "lock"):
                    for pid in pz.get(key, []):
                        self.assertIn(pid, ids, f"{lid}: puzzle {pz['id']} cita {pid} em {key}")
                for e in pz.get("edges", []):
                    if len(e) > 2:
                        self.assertIn(e[2], ids, f"{lid}: puzzle {pz['id']} cita {e[2]}")

    def test_tudo_alcancavel_da_entrada(self):
        falhas = []
        for lid in DB.levels:
            sp = entrada(lid)
            lv = Level(DB.levels[lid])
            e0 = next(e for e in lv.entities if e.get("id") == sp)
            lv.spawn_cell = (int(e0["x"]), int(e0["z"]))
            ok = alcance(lv)
            for e in lv.entities:
                t = e.get("type")
                if t not in ALCANCAVEIS:
                    continue
                cx, cz = int(e["x"]), int(e["z"])
                vizinhos = {(cx + dx, cz + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1)}
                if not vizinhos & ok:
                    falhas.append(f"{lid}: {t} {e.get('id') or e.get('doc') or e.get('npc')} em ({cx},{cz})")
            paredes = sorted((x, z) for (x, z) in ok if lv.cell(x, z).kind == "wall" and lv.cell(x, z).height >= 2)
            if paredes:
                falhas.append(f"{lid}: topo de parede alcançável em {paredes[:6]}{'...' if len(paredes) > 6 else ''}")
        self.assertEqual(falhas, [], "inalcançáveis a partir da entrada")


    def test_portas_de_puzzle_e_chave_bloqueiam_algo(self):
        """Fechada, a porta precisa separar alguma coisa; senão ela pode ser contornada."""
        falhas = []
        for lid in DB.levels:
            data = DB.levels[lid]
            abertas_por_puzzle = {pid for pz in data.get("puzzles", []) for pid in pz.get("open", [])}
            lv = Level(data)
            e0 = next(e for e in lv.entities if e.get("id") == entrada(lid))
            lv.spawn_cell = (int(e0["x"]), int(e0["z"]))
            livre = alcance(lv)
            for e in lv.entities:
                if e.get("type") != "door" or e.get("transient") or e.get("open"):
                    continue
                if e.get("id") not in abertas_por_puzzle and not e.get("key"):
                    continue
                fechado = alcance(lv, frozenset(celulas_da_porta(e)))
                if len(livre - fechado) <= len(celulas_da_porta(e)):
                    falhas.append(f"{lid}: porta {e['id']} não bloqueia nada")
        self.assertEqual(falhas, [])


class TestCampanha(unittest.TestCase):
    def test_todas_as_fases_ligadas_ao_santuario(self):
        """Seguindo saídas (ida e volta) a partir do Santuário, todas as fases existentes são visitáveis."""
        vistos, fila = {"santuario"}, deque(["santuario"])
        while fila:
            lid = fila.popleft()
            for e in DB.levels[lid]["entities"]:
                if e.get("type") == "exit" and e["to"] in DB.levels and e["to"] not in vistos:
                    vistos.add(e["to"])
                    fila.append(e["to"])
        self.assertEqual(sorted(set(DB.levels) - vistos), [])

    def test_chaves_obteniveis(self):
        """Toda porta com chave tem a chave em algum baú, saque de inimigo, recompensa ou diálogo do jogo."""
        import json, os
        fontes = json.dumps([DB.levels, DB.bosses, DB.quests, DB.lore], ensure_ascii=False)
        pasta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "dialogues")
        for f in os.listdir(pasta):
            fontes += open(os.path.join(pasta, f), encoding="utf-8").read()
        for lid, lv in DB.levels.items():
            for e in lv["entities"]:
                if e.get("type") == "door" and e.get("key"):
                    k = e["key"]
                    concede = (f'"item": "{k}"' in fontes) or (f'"give": "{k}"' in fontes) or (f'"give": ["{k}"' in fontes)
                    self.assertTrue(concede, f"{lid}: chave {k} da porta {e['id']} não é obtida em lugar nenhum")

    def test_cada_ato_tem_chefe_e_volta_ao_santuario(self):
        for aid, ato in DB.acts.items():
            arenas = [lid for lid, lv in DB.levels.items()
                      if any(e.get("type") == "boss" and e.get("boss") == ato["boss"] for e in lv["entities"])]
            self.assertEqual(len(arenas), 1, aid)
            volta = [e for e in DB.levels[arenas[0]]["entities"] if e.get("type") == "exit" and e["to"] == "santuario"]
            self.assertTrue(volta, f"{aid}: arena sem portal de volta")


class TestPuzzles(unittest.TestCase):
    """Resolve cada puzzle do jeito que a dica descreve e confere o efeito (portas abertas, flags)."""

    def mundo(self, lid):
        s = new_session()
        return s, world_for(s, lid, entrada(lid))

    def interagir_ate(self, w, prop, cond, limite=12):
        for _ in range(limite):
            if cond(prop):
                return
            prop.interact(w.player)
        self.assertTrue(cond(prop), prop.pid)

    def resolver(self, w, pz):
        t = pz["type"]
        if t == "combination":
            for pid, want in zip(pz["props"], pz["solution"]):
                p = w.find_prop(pid)
                if isinstance(want, str):
                    self.interagir_ate(w, p, lambda p, want=want: p.symbol == want)
                else:
                    self.interagir_ate(w, p, lambda p, want=want: p.state == want)
        elif t == "sequence":
            pmap = {w.find_prop(pid).symbol: w.find_prop(pid) for pid in pz["props"]}
            for sym in pz["solution"]:
                pmap[sym].interact(w.player)
        elif t == "kill":
            for e in list(w.enemies()):
                if getattr(e, "group", None) == pz["group"]:
                    e.hp = 0
                    e.die(w.player)
        elif t == "all_on":
            for pid in pz["props"]:
                p = w.find_prop(pid)
                if hasattr(p, "activate_crystal"):
                    p.activate_crystal()
                elif p.spec.get("type") == "plate":
                    p.save_state(1) if p.latch else None
                    p.pressed = True
                    p.send("activate")
                else:
                    if not p.state:
                        p.interact(w.player)
        elif t == "gears":
            # pega todas as engrenagens soltas, encaixa e gira até a solução
            for g in [p for p in w.props if p.spec.get("type") == "gear" and not p.state]:
                g.interact(w.player)
            for i, pid in enumerate(pz["props"]):
                sock = w.find_prop(pid)
                if not sock.has_gear:
                    sock.interact(w.player)
                self.assertTrue(sock.has_gear, f"faltou engrenagem para {pid}")
                if pz.get("solution") is not None:
                    self.interagir_ate(w, sock, lambda p, want=pz["solution"][i]: p.rotation == want)
        elif t == "network":
            # procura uma combinação de chaves que leve aos destinos sem tocar nos proibidos e aplica pelo jogador
            chaves = sorted({e[2] for e in pz["edges"] if len(e) > 2})
            props = [w.find_prop(c) for c in chaves]
            posicoes = [getattr(p, "positions", 2) for p in props]
            puz = next(x for x in w.puzzles if x.id == pz["id"])
            for estados in itertools.product(*[range(n) for n in posicoes]):
                for p, e in zip(props, estados):
                    p.state = e
                if puz.network_ok():
                    break
            else:
                self.fail(f"{pz['id']}: nenhuma combinação de chaves resolve a rede")
            alvo = [p.state for p in props]
            for p in props:
                p.state = 0
            for p, e in zip(props, alvo):
                self.interagir_ate(w, p, lambda p, e=e: p.state == e)
            # gira os espelhos da fase por todas as orientações ('/' e '\\'); os cristais com latch acumulam
            espelhos = [p for p in w.props if p.spec.get("type") == "mirror"]
            for estados in itertools.product(range(2), repeat=len(espelhos)):
                for m, e in zip(espelhos, estados):
                    m.state = e
                step(w, 2)
        else:
            return False
        step(w, 3)
        return True

    def test_puzzles_resolviveis(self):
        for lid, lv in DB.levels.items():
            for pz in lv.get("puzzles", []):
                s, w = self.mundo(lid)
                if not self.resolver(w, pz):
                    continue
                self.assertTrue(s.has_flag(f"puzzle:{pz['id']}"), f"{lid}: {pz['id']} não resolveu")
                for pid in pz.get("open", []):
                    self.assertTrue(w.find_prop(pid).open, f"{lid}: {pz['id']} não abriu {pid}")

    def test_sequencia_errada_reinicia(self):
        for lid, lv in DB.levels.items():
            for pz in lv.get("puzzles", []):
                if pz["type"] != "sequence":
                    continue
                s, w = self.mundo(lid)
                pmap = {w.find_prop(pid).symbol: w.find_prop(pid) for pid in pz["props"]}
                sol = pz["solution"]
                pmap[sol[1]].interact(w.player)          # começa errado
                for sym in sol[:-1]:
                    pmap[sym].interact(w.player)
                step(w, 2)
                self.assertFalse(s.has_flag(f"puzzle:{pz['id']}"), f"{lid}: {pz['id']} resolveu sem a sequência")


if __name__ == "__main__":
    unittest.main()
