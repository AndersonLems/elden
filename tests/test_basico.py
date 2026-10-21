"""Testes sem janela: dados, carregamento das fases, combate básico, progressão e salvamento.

Rodar: python3 -m unittest discover -s tests -v
"""
import math
import os
import unittest

from util import new_session, world_for, step, nearest_enemy, DT   # noqa: F401
from elden.core.data import DB
from elden.sim.combat.moves import build_moveset
from elden.sim.progression import grace_tree
from elden.sim.session import Session

LEVELS = {"santuario": "inicio", "ato1_floresta": "inicio", "ato1_castelo": "cripta", "ato1_arena": "entrada",
          "ato2_cidade": "inicio", "ato2_fabrica": "entrada"}


class TestDados(unittest.TestCase):
    def test_validacao(self):
        self.assertEqual(DB.validate(), [])

    def test_classes_tem_rotas(self):
        for cid, c in DB.classes.items():
            fam = DB.weapons[c["weapon"]]["family"]
            ms = build_moveset(fam)
            self.assertGreaterEqual(len(ms.routes()), 4, cid)


class TestFases(unittest.TestCase):
    def test_carregar_e_simular(self):
        for lvl, sp in LEVELS.items():
            if lvl not in DB.levels:
                continue
            w = world_for(new_session(), lvl, sp)
            step(w, 60, move=(0.3, 1.0))
            self.assertFalse(w.player.dead, lvl)


class TestCombate(unittest.TestCase):
    def test_matar_inimigo(self):
        for cls in DB.classes:
            s = new_session(cls)
            w = world_for(s, "ato1_floresta")
            p = w.player
            e = nearest_enemy(w)
            p.x, p.z = e.x - 1.0, e.z
            for i in range(900):
                e = nearest_enemy(w)
                if e is None or p.stats_log["kills"] >= 1:
                    break
                ang = math.atan2(e.z - p.z, e.x - p.x)
                d = e.dist_to(p)
                p.hp = p.max_hp
                step(w, 1, press="light" if i % 10 == 0 and d < 3 else None,
                     move=(math.cos(ang), math.sin(ang)) if d > 1.5 else (0, 0))
            self.assertGreaterEqual(p.stats_log["kills"], 1, cls)


class TestProgressao(unittest.TestCase):
    def test_arvore_e_save(self):
        s = new_session()
        c = s.char
        c.grace = 10 ** 6
        while c.level_up():
            if c.level > 10:
                break
        self.assertTrue(grace_tree.unlock(c, "c_forca1"))
        self.assertTrue(grace_tree.unlock(c, "gue_hab2"))
        d = s.to_dict()
        s2 = Session.from_dict(d)
        self.assertEqual(s2.char.nodes, c.nodes)
        grace_tree.respec(c)
        self.assertEqual(c.nodes, [])


if __name__ == "__main__":
    unittest.main()
