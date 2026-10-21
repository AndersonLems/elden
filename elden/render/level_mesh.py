"""Gera a malha do cenário a partir da grade de células do mapa.

Na projeção oblíqua 3/4 só são visíveis os topos (planos horizontais e rampas) e as faces voltadas
para o sul (para a câmera); as demais nem são geradas. A oclusão ambiente é feita por vértice e
líquidos são marcados na cor do vértice (alfa >= 2) para o shader animar.
"""
import numpy as np
from panda3d.core import Texture, SamplerState

from .geom import MeshBuilder


def _top_h(c):
    if c is None:
        return None
    if c.void:
        return None
    if c.kind == "ramp":
        return max(c.h0, c.h1)
    return c.height if c.render else min(c.height, 0.0) if c.solid else c.height


def _ao(level, x, z, h):
    occl = 0
    for dx in (-1, 0):
        for dz in (-1, 0):
            c = level.cell(x + dx, z + dz)
            if c is not None and not c.void and c.render and c.kind != "ramp" and c.height > h + 0.01:
                occl += 1
    return (1.0, 0.82, 0.68, 0.58, 0.5)[occl]


def _floor_height(c):
    """Altura visual do topo (células sólidas não renderizadas, como árvores, mostram o piso)."""
    if not c.render:
        return 0.0 if c.height >= 0 else c.height
    return c.height


def build_level_mesh(level, atlas):
    mb = MeshBuilder()
    W, D = level.width, level.depth
    for z in range(D):
        for x in range(W):
            c = level.cell(x, z)
            if c is None or c.void:
                continue
            var = (x * 7 + z * 13 + (x * z) % 5) % 4
            u0, v0, u1, v1 = atlas.uv(c.top_tex, var)
            em = c.emissive + (2.0 if c.liquid else 0.0)
            if c.kind == "ramp":
                h0, h1 = c.h0, c.h1
                ao = [_ao(level, x, z, h0), _ao(level, x + 1, z, h0), _ao(level, x + 1, z + 1, h1), _ao(level, x, z + 1, h1)]
                cols = [(a, a, a, em) for a in ao]
                n = (0.0, 1.0, -(h1 - h0))
                mb.quad((x, h0, z), (x + 1, h0, z), (x + 1, h1, z + 1), (x, h1, z + 1), n, (u0, v0), (u1, v1), colors=cols)
                h = h0
            else:
                h = _floor_height(c)
                ao = [_ao(level, x, z, h), _ao(level, x + 1, z, h), _ao(level, x + 1, z + 1, h), _ao(level, x, z + 1, h)]
                cols = [(a, a, a, em) for a in ao]
                mb.quad((x, h, z), (x + 1, h, z), (x + 1, h, z + 1), (x, h, z + 1), (0, 1, 0), (u0, v0), (u1, v1), colors=cols)
            # face sul: do topo desta célula até o topo da vizinha ao sul
            s = level.cell(x, z - 1)
            if s is None or s.void:
                low = level.min_height - 3.0
            elif s.kind == "ramp":
                low = s.h1
            else:
                low = _floor_height(s)
            if low < h - 0.001:
                y = h
                k = 0
                while y > low + 0.001:
                    y0 = max(low, y - 1.0)
                    frac = y - y0
                    tex = c.wall_tex if (k > 0 or not c.trim_tex) else c.trim_tex
                    if c.liquid:
                        tex = c.top_tex
                    tu0, tv0, tu1, tv1 = atlas.uv(tex, (var + k) % 4)
                    vb = tv1 - (tv1 - tv0) * frac
                    shade_top = 1.0 if k == 0 else 0.92
                    shade_bot = 0.92 if y0 > low + 0.001 else 0.62
                    if y0 <= low + 0.001 and (s is None or s.void):
                        shade_bot = 0.15
                    we = c.wall_emissive if not c.trim_tex or k > 0 else 0.0
                    cs = [(shade_bot,) * 3 + (we,), (shade_bot,) * 3 + (we,), (shade_top,) * 3 + (we,), (shade_top,) * 3 + (we,)]
                    mb.quad((x, y0, z), (x + 1, y0, z), (x + 1, y, z), (x, y, z), (0, 0, -1), (tu0, vb), (tu1, tv1), colors=cs)
                    y = y0
                    k += 1
    return mb.build("level")


def occupancy_texture(level):
    """Altura de cada célula (para as sombras projetadas por raymarching no shader)."""
    W, D = level.width, level.depth
    arr = np.zeros((D, W), np.uint8)
    for z in range(D):
        for x in range(W):
            c = level.cell(x, z)
            if c is None or c.void:
                continue
            h = c.height if c.render or c.solid else 0.0
            if c.kind == "ramp":
                h = min(c.h0, c.h1)
            h = max(0.0, h + (c.occluder_extra or 0.0))
            arr[z, x] = int(np.clip(h / 8.0 * 255, 0, 255))
    tex = Texture("occupancy")
    tex.setup_2d_texture(W, D, Texture.T_unsigned_byte, Texture.F_red)
    tex.set_ram_image(arr.tobytes())
    tex.set_minfilter(SamplerState.FT_nearest)
    tex.set_magfilter(SamplerState.FT_nearest)
    tex.set_wrap_u(SamplerState.WM_clamp)
    tex.set_wrap_v(SamplerState.WM_clamp)
    return tex
