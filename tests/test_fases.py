"""Testes estruturais das fases: alcance a partir da entrada, saídas válidas e puzzles resolvíveis.

Rodar: python3 -m unittest tests.test_fases -v
"""
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


PULO = 1.4   # pulo do jogador sobe ~1,54 (JUMP_SPEED² / 2·GRAVITY); margem para a borda


def alcance(level):
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
    while q or any(c & seen and not c <= seen for c in paradas):
        if not q:
            for c in paradas:
                if c & seen:
                    for cell in c - seen:
                        seen.add(cell)
                        q.append(cell)
            continue
        x, z = q.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = x + dx, z + dz
            if (nx, nz) in seen or not (0 <= nx < nav.w and 0 <= nz < nav.d) or not nav.ok[nz][nx]:
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
        else:
            return False
        step(w, 3)
        return True

    def test_puzzles_resolviveis(self):
        for lid, lv in DB.levels.items():
            for pz in lv.get("puzzles", []):
                if pz["type"] in ("network", "beam", "gears"):
                    continue   # cobertos por testes específicos quando existirem
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
