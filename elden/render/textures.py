"""Conversão de imagens numpy (RGBA, origem no topo) para texturas Panda3D com filtro de pixel."""
import numpy as np
from panda3d.core import Texture, SamplerState


def to_texture(img, name="tex", nearest=True):
    h, w = img.shape[:2]
    tex = Texture(name)
    tex.setup_2d_texture(w, h, Texture.T_unsigned_byte, Texture.F_rgba8)
    tex.set_ram_image_as(np.ascontiguousarray(np.flipud(img)).tobytes(), "RGBA")
    f = SamplerState.FT_nearest if nearest else SamplerState.FT_linear
    tex.set_minfilter(f)
    tex.set_magfilter(f)
    tex.set_wrap_u(SamplerState.WM_clamp)
    tex.set_wrap_v(SamplerState.WM_clamp)
    return tex


def frame_uv(cx, cy, size, W, H, fw=None, fh=None):
    """UV (u0, v0, u1, v1) de um quadro numa folha cuja origem está no topo."""
    fw = fw or size
    fh = fh or size
    u0 = cx / W
    u1 = (cx + fw) / W
    v1 = 1.0 - cy / H
    v0 = 1.0 - (cy + fh) / H
    e = 0.001 / max(W, H)
    return u0 + e, v0 + e, u1 - e, v1 - e
