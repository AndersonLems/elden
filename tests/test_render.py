"""Regressões matemáticas do render sem abrir janela."""
import math
import os
import unittest

from panda3d.core import Filename, Loader, TexturePool

from elden.core.settings import Quality
from elden.art.spritegen import make_rig
from elden.render.assets import load_manifest, validate_manifest
from elden.render.projection import project_relative, screen_move_to_world
from elden.render.shader_lib import source


class TestProjecao(unittest.TestCase):
    def test_eixos_do_chao_aparecem_em_diagonais_opostas(self):
        x = project_relative(1, 0, 0)
        z = project_relative(0, 0, 1)
        self.assertGreater(x[0], 0)
        self.assertLess(z[0], 0)
        self.assertGreater(x[1], 0)
        self.assertGreater(z[1], 0)

    def test_altura_sobe_na_tela_e_aproxima(self):
        ground = project_relative(0, 0, 0)
        raised = project_relative(0, 2, 0)
        self.assertGreater(raised[1], ground[1])
        self.assertLess(raised[2], ground[2])

    def test_wasd_e_orientado_a_tela(self):
        wx, wz = screen_move_to_world(0, 1)
        sx, sy, _ = project_relative(wx, 0, wz)
        self.assertAlmostEqual(sx, 0, places=6)
        self.assertGreater(sy, 0)
        rx, rz = screen_move_to_world(1, 0)
        sx, sy, _ = project_relative(rx, 0, rz)
        self.assertGreater(sx, 0)
        self.assertAlmostEqual(sy, 0, places=6)

    def test_diagonal_nunca_acelera(self):
        x, z = screen_move_to_world(1, 1)
        self.assertLessEqual(math.hypot(x, z), 1.000001)


class TestPipeline(unittest.TestCase):
    def test_manifesto_externo_e_valido(self):
        self.assertEqual(validate_manifest(load_manifest()), [])

    def test_assets_goticos_carregam_com_geometria_e_textura(self):
        data = load_manifest()
        self.assertGreaterEqual(len(data["assets"]), 8)
        loader = Loader.get_global_ptr()
        root = os.path.join(os.path.dirname(__file__), "..")
        for item in data["assets"]:
            path = os.path.join(root, "assets", item["path"])
            if item["kind"] == "model":
                node = loader.load_sync(Filename.from_os_specific(path))
                self.assertIsNotNone(node, item["id"])
                self.assertGreater(node.get_num_geoms(), 0, item["id"])
        tex_item = next(a for a in data["assets"] if a["id"] == "ato1_pedra_gotica")
        tex = TexturePool.load_texture(Filename.from_os_specific(os.path.join(root, "assets", tex_item["path"])))
        self.assertIsNotNone(tex)
        self.assertEqual((tex.get_x_size(), tex.get_y_size()), (1024, 1024))

    def test_manifesto_rejeita_escape_e_duplicata(self):
        data = {"version": 1, "assets": [
            {"id": "x", "kind": "model", "path": "../fora.glb"},
            {"id": "x", "kind": "texture", "path": "textures/x.glb"},
        ]}
        errors = validate_manifest(data, require_files=False)
        self.assertTrue(any("sai de assets" in e for e in errors))
        self.assertTrue(any("duplicado" in e for e in errors))
        self.assertTrue(any("incompatível" in e for e in errors))

    def test_shaders_expandem_sem_include_residual(self):
        for vert, frag in (("world.vert", "world.frag"), ("sprite.vert", "sprite.frag"),
                           ("decor.vert", "sprite.frag"), ("fx.vert", "fx.frag")):
            self.assertNotIn("#include", source(vert))
            self.assertNotIn("#include", source(frag))

    def test_perfis_controlam_ao_e_bloom(self):
        self.assertEqual(Quality("baixa").ao, 0.0)
        self.assertGreater(Quality("alta").ao, 0.0)
        self.assertGreater(Quality("ultra").bloom, Quality("media").bloom)
        self.assertEqual(Quality("alta").internal_height, 360)

    def test_sprites_prioritarios_usam_quadro_refinado(self):
        self.assertGreaterEqual(make_rig("pl_guerreiro_2_0_0_0").frame, 64)
        self.assertGreaterEqual(make_rig("esqueleto").frame, 64)
        self.assertGreaterEqual(make_rig("varkhan").frame, 96)


if __name__ == "__main__":
    unittest.main()
