"""Testes de chefes com bot: cada chefe com fase existente precisa ser vencível, passar por todas as fases,
fechar/reabrir a arena e gravar as flags de vitória.

Rodar: python3 -m unittest tests.test_chefes -v   (ou junto com discover)
"""
import math
import unittest

from bot import Luta
from elden.core.data import DB

# fase, ponto de entrada, distância inicial (None = começa no ponto de entrada)
CHEFES = {"varkhan": ("ato1_arena", "entrada", None),
          "condessa_rubra": ("ato1_castelo", "salao", 5),
          "serafim_09": ("ato2_arena", "entrada", None),
          "santo_imperfeito": ("ato3_arena", "entrada", None),
          "malachar": ("ato4_arena", "entrada", None),
          "aurelion": ("ato5_arena", "entrada", None)}


class TestChefes(unittest.TestCase):
    def lutar(self, boss_id, seeds=(1, 2, 3)):
        level, spawn, perto = CHEFES[boss_id]
        if level not in DB.levels:
            self.skipTest(f"fase {level} não existe")
        for seed in seeds:
            luta = self._uma(boss_id, level, spawn, perto, seed)
        return luta

    def _uma(self, boss_id, level, spawn, perto, seed):
        luta = Luta(level, spawn, seed=seed, perto=perto, ato=DB.bosses[boss_id]["act"]).lutar(limite=900)
        self.assertTrue(luta.boss.dead, f"{boss_id} (seed {seed}) não foi vencido em {luta.time:.0f}s")
        self.assertEqual(luta.boss_na_parede, 0, f"{boss_id} (seed {seed}) saiu da arena")
        self.assertEqual(luta.separados, 0, f"{boss_id} (seed {seed}) atravessou a névoa")
        self.assertEqual(len(luta.phases), len(DB.bosses[boss_id]["phases"]), f"{boss_id}: fases vistas {luta.phases}")
        self.assertTrue(luta.door_closed, f"{boss_id}: a arena não fechou")
        self.assertTrue(luta.door.open, f"{boss_id}: a arena não reabriu")
        self.assertIn(f"boss:{boss_id}", luta.session.flags)
        return luta

    def test_varkhan(self):
        self.lutar("varkhan")

    def test_condessa(self):
        self.lutar("condessa_rubra")

    def test_santo(self):
        self.lutar("santo_imperfeito")

    def test_malachar(self):
        self.lutar("malachar")

    def test_aurelion(self):
        self.lutar("aurelion")

    def test_serafim(self):
        luta = self.lutar("serafim_09")
        self.assertIn("ato2_concluido", luta.session.flags)
        jatos = [z for z in luta.zones_seen.values() if z.spec.get("visual") == "flame_jet"]
        self.assertGreater(len(jatos), 0, "os jatos da forja nunca dispararam")
        lv = luta.world.level
        for z in jatos:
            # o jato termina dentro da arena, sobre chão
            ex, ez = z.x + math.cos(z.facing) * z.length, z.z + math.sin(z.facing) * z.length
            self.assertIsNotNone(lv.ground_at(ex, ez), (z.x, z.z, z.facing))


if __name__ == "__main__":
    unittest.main()
