"""Fim de jogo: fragmentos do ciclo no mundo, altar do Trono depois de Aurelion e as condições dos três finais.

Rodar: python3 -m unittest tests.test_finais -v
"""
import unittest

from util import new_session, world_for, step
from elden.core.data import DB
from elden.sim.ai.bosses.base import Boss


class TestFinais(unittest.TestCase):
    def test_cinco_fragmentos_no_mundo(self):
        docs = {k for k, v in DB.lore.items() for g in v.get("grants", []) if "fragment" in g}
        colocados = {e.get("doc") for lv in DB.levels.values() for e in lv["entities"]}
        altares = {e.get("fragment") for lv in DB.levels.values() for e in lv["entities"] if e.get("altar") == "ciclo"}
        frags = {g["fragment"] for k in docs & colocados for g in DB.lore[k]["grants"] if "fragment" in g} | altares
        self.assertGreaterEqual(len(frags), 5, f"fragmentos alcançáveis: {sorted(frags)}")

    def test_altar_do_trono_apos_aurelion(self):
        s = new_session()
        w = world_for(s, "ato5_arena", "entrada")
        self.assertIsNone(w.find_prop("altar_trono"), "o altar não deve existir antes da vitória")
        boss = next(e for e in w.enemies() if isinstance(e, Boss))
        boss.hp = 0
        boss.die(w.player)
        step(w, 240)
        altar = w.find_prop("altar_trono")
        self.assertIsNotNone(altar, "o altar do Trono não apareceu depois de Aurelion")
        self.assertIsNotNone(w.find_prop("portal_vitoria"))
        self.assertTrue(s.has_flag("aurelion_derrotado"))
        s.events.clear()
        altar.interact(w.player)
        self.assertIn(("ending_choice", None), s.events)

    def test_condicoes_dos_finais(self):
        s = new_session()
        c = s.char
        c.corruption = 10
        self.assertEqual(s.ending_options(), ["purificacao"])
        c.corruption = 80
        self.assertEqual(s.ending_options(), ["dominio"])
        c.corruption = 45
        self.assertEqual(s.ending_options(), ["purificacao", "dominio"])
        c.cycle_fragments = [f"ciclo_{i}" for i in range(1, 6)]
        self.assertIn("ruptura", s.ending_options())


if __name__ == "__main__":
    unittest.main()
