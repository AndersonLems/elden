"""Solucionador lógico da campanha: para cada ato, partindo do portal do Santuário, expande o que é alcançável
(baús, saques de inimigos, documentos, puzzles, alavancas, chaves, saídas) até chegar ao chefe. Pega travamentos
de progressão que os testes por fase não veem (ex.: uma chave que nenhum baú ou inimigo entrega).

Rodar: python3 -m unittest tests.test_campanha -v
"""
import unittest

from util import new_session
from elden.core.data import DB
from elden.sim.world.level import Level
from test_fases import alcance, celulas_da_porta


def vizinhos(e):
    cx, cz = int(e["x"]), int(e["z"])
    return {(cx + dx, cz + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1)}


class Campanha:
    def __init__(self, ato):
        self.ato = ato
        self.s = new_session()
        for a in range(1, ato):             # atos anteriores concluídos
            self.s.set_flag(f"ato{a}_concluido")
            self.s.set_flag(f"boss:{DB.acts[f'ato{a}']['boss']}")
        self.s.set_flag("intro_velaria")
        self.fases = {lid for lid, lv in DB.levels.items() if lv.get("act") == ato}
        self.niveis = {lid: Level(DB.levels[lid]) for lid in self.fases}
        self.entradas = {lid: set() for lid in self.fases}
        ini = DB.acts[f"ato{ato}"]
        self.entradas[ini["level"]].add(ini["spawn"])
        self.feito = set()                  # entidades já usadas (baús, inimigos, documentos)
        self.puxadas = set()                # alavancas/placas acionadas (ids)
        self.log = []

    def porta_aberta(self, lid, e):
        if e.get("open") or e.get("transient"):
            return True
        if e.get("key") and self.s.char.has_item(e["key"]):
            return True
        if e.get("open_flag") and self.s.has_flag(e["open_flag"]):
            return True
        pid = e.get("id")
        for pz in DB.levels[lid].get("puzzles", []):
            if pid in pz.get("open", []) and self.s.has_flag(f"puzzle:{pz['id']}"):
                return True
        # portas abertas por sinal de alavanca/placa
        alvos = [x for x in DB.levels[lid]["entities"] if pid in x.get("targets", []) and x.get("id") in self.puxadas]
        return bool(alvos) and len(alvos) >= e.get("need", 1)

    def plataforma_ativa(self, lid, e):
        if e.get("active", True):
            return True
        pid = e.get("id")
        for pz in DB.levels[lid].get("puzzles", []):
            if pid in pz.get("activate", []) and self.s.has_flag(f"puzzle:{pz['id']}"):
                return True
        return any(pid in x.get("targets", []) and x.get("id") in self.puxadas for x in DB.levels[lid]["entities"])

    def alcancaveis(self, lid):
        lv = self.niveis[lid]
        lv.entities = [e for e in DB.levels[lid]["entities"]
                       if e.get("type") != "platform" or self.plataforma_ativa(lid, e)]
        ok = set()
        bloq = set()
        for e in lv.entities:
            if e.get("type") == "door" and not self.porta_aberta(lid, e):
                bloq |= celulas_da_porta(e)
        for sp in self.entradas[lid]:
            e0 = next((e for e in lv.entities if e.get("id") == sp), None)
            if e0 is None:
                continue
            lv.spawn_cell = (int(e0["x"]), int(e0["z"]))
            ok |= alcance(lv, frozenset(bloq))
        return ok

    def passo(self):
        progresso = False
        for lid in sorted(self.fases):
            if not self.entradas[lid]:
                continue
            ok = self.alcancaveis(lid)
            data = DB.levels[lid]
            ents = data["entities"]
            perto = lambda e: bool(vizinhos(e) & ok)
            for i, e in enumerate(ents):
                chave = (lid, i)
                if chave in self.feito or not perto(e):
                    continue
                t = e.get("type")
                if e.get("if") and not self.s.check(e["if"]):
                    continue
                if t == "chest":
                    for entry in e.get("loot", []):
                        self.s.grant(entry, None)
                elif t == "enemy":
                    for entry in e.get("loot", []):
                        self.s.grant(entry, None)
                    if e.get("unique"):
                        self.s.set_flag(f"unique:{e['unique']}")
                elif t == "document":
                    self.s.read_document(e["doc"], silent=True)
                elif t in ("lever", "plate"):
                    self.puxadas.add(e.get("id"))
                elif t == "exit":
                    if e["to"] in self.fases and (not e.get("require_flag") or self.s.has_flag(e["require_flag"])):
                        if e.get("spawn") not in self.entradas[e["to"]]:
                            self.entradas[e["to"]].add(e.get("spawn"))
                            self.log.append(f"{lid} → {e['to']}")
                            progresso = True
                    continue        # saídas podem ser reavaliadas (require_flag)
                elif t == "boss":
                    self.s.set_flag("chefe_alcancado")
                else:
                    continue
                self.feito.add(chave)
                progresso = True
            # puzzles cujas peças estão todas ao alcance são resolvidos (a solução foi testada em test_fases)
            ids_ok = {e.get("id") for e in ents if perto(e)}
            for pz in data.get("puzzles", []):
                flag = f"puzzle:{pz['id']}"
                if self.s.has_flag(flag):
                    continue
                if pz["type"] == "kill":
                    pecas = {e.get("id") or f"g{i}" for i, e in enumerate(ents) if e.get("group") == pz["group"]}
                    alcance_ok = all(perto(e) for e in ents if e.get("group") == pz["group"])
                else:
                    pecas = set(pz.get("props", [])) | {x[2] for x in pz.get("edges", []) if len(x) > 2}
                    alcance_ok = pecas <= ids_ok
                if pecas and alcance_ok:
                    self.s.set_flag(flag)
                    self.puxadas |= set(pz.get("props", []))   # cristais/alavancas do puzzle sinalizam seus alvos
                    for entry in pz.get("reward", []):
                        self.s.grant(entry, None)
                    self.log.append(f"{lid}: puzzle {pz['id']}")
                    progresso = True
        return progresso

    def resolver(self):
        for _ in range(60):
            if not self.passo():
                break
        return self.s.has_flag("chefe_alcancado")


class TestCampanha(unittest.TestCase):
    def test_cada_ato_chega_ao_chefe(self):
        for aid in DB.acts:
            ato = int(aid[3:])
            c = Campanha(ato)
            self.assertTrue(c.resolver(), f"{aid}: chefe inalcançável. Caminho: {c.log}")


if __name__ == "__main__":
    unittest.main()
