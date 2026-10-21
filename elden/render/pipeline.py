"""Pipeline de renderização pixel art 2.5D.

Passes por quadro:
  1. cena (cenário, sprites, sombras de contato, partículas) num buffer HDR de baixa resolução
     com projeção oblíqua 3/4 (1 unidade = PPU pixels);
  2. bloom: extração de brilho em 1/2 resolução + desfoque separável em 1/2 e 1/4;
  3. composição na janela com escala inteira (vizinho mais próximo), deslocamento subpixel
     para rolagem suave, tonemapping, gradação de cor, vinheta e efeitos de tela;
  4. interface (superfície do pygame enviada como textura).
"""
import math

from panda3d.core import (Camera as PandaCamera, ColorBlendAttrib, FrameBufferProperties, GraphicsOutput,
                          GraphicsPipe, LVecBase4f, NodePath, OrthographicLens, PTA_LVecBase4f, SamplerState,
                          Texture, TransparencyAttrib, WindowProperties)

from . import shader_lib
from .geom import fullscreen_quad

PPU = 16            # pixels por unidade de mundo
MAX_LIGHTS = 16
DEPTH_RANGE = 400.0


def _tex(nearest=True, name="t"):
    t = Texture(name)
    f = SamplerState.FT_nearest if nearest else SamplerState.FT_linear
    t.set_minfilter(f)
    t.set_magfilter(f)
    t.set_wrap_u(SamplerState.WM_clamp)
    t.set_wrap_v(SamplerState.WM_clamp)
    return t


class Pass:
    """Um passe de tela cheia: buffer próprio + quad com shader."""

    def __init__(self, pipe, name, size, frag, hdr=True, nearest=False):
        self.name = name
        self.size = size
        self.tex = _tex(nearest, name)
        self.buffer = pipe.make_buffer(name, size, self.tex, hdr=hdr, depth=False)
        self.root = NodePath(name + "_root")
        self.root.set_two_sided(True)
        self.quad = fullscreen_quad(name + "_q")
        self.quad.reparent_to(self.root)
        self.quad.set_shader(shader_lib.load("post.vert", frag))
        self.quad.set_shader_input("u_rect", LVecBase4f(1, 1, 0, 0))
        self.quad.set_depth_test(False)
        self.quad.set_depth_write(False)
        cam = pipe.make_flat_camera(name + "_cam", self.root)
        self.dr = self.buffer.make_display_region()
        self.dr.set_camera(cam)

    def destroy(self, engine):
        engine.remove_window(self.buffer)


class PixelPipeline:
    def __init__(self, base, quality):
        self.base = base
        self.quality = quality
        self.engine = base.graphicsEngine
        self.scene_root = NodePath("scene_root")
        self.world_root = self.scene_root.attach_new_node("world")
        self.sprite_root = self.scene_root.attach_new_node("sprites")
        self.shade_root = self.scene_root.attach_new_node("shades")
        self.fx_root = self.scene_root.attach_new_node("fx")
        self._setup_roots()
        self.zoom = 1.0
        self.zoom_target = 1.0
        self.cam_x = 0.0
        self.cam_z = 0.0
        self.time = 0.0
        self.passes = []
        self.ui_tex = _tex(True, "ui")
        self.ui_tex.setup_2d_texture(1, 1, Texture.T_unsigned_byte, Texture.F_rgba8)
        self.ui_tex.set_ram_image_as(b"\x00\x00\x00\x00", "RGBA")
        self.fx = dict(vignette=0.28, grain=0.012, aberration=0.0, fade=0.0, desat=0.0, bloom=0.72,
                       hurt=0.0, flash=0.0, dim=0.0)
        self.grade = dict(lift=(0.02, 0.015, 0.03), gain=(1.0, 1.0, 1.0), exposure=1.0, saturation=1.0)
        self._built_for = None
        self._final_np = None
        self._build()

    # ------------------------------------------------------------------ montagem
    def _setup_roots(self):
        lp = self.lpos = PTA_LVecBase4f.empty_array(MAX_LIGHTS)
        lc = self.lcol = PTA_LVecBase4f.empty_array(MAX_LIGHTS)
        r = self.scene_root
        r.set_shader_input("u_lpos", lp)
        r.set_shader_input("u_lcol", lc)
        r.set_shader_input("u_nlights", 0)
        r.set_shader_input("u_view", LVecBase4f(0, 0, 10, 10))
        r.set_shader_input("u_depth", LVecBase4f(-DEPTH_RANGE * 0.5, 1.0 / DEPTH_RANGE, 0, 0))
        r.set_shader_input("u_amb_sky", (0.3, 0.3, 0.35))
        r.set_shader_input("u_amb_ground", (0.12, 0.1, 0.12))
        r.set_shader_input("u_dir_dir", (0.3, 0.8, -0.5))
        r.set_shader_input("u_dir_col", (0.3, 0.3, 0.4))
        r.set_shader_input("u_fog", LVecBase4f(0.1, 0.1, 0.12, 0.3))
        r.set_shader_input("u_misc", LVecBase4f(0, 6, 1, 0))
        r.set_shader_input("u_shadow_q", LVecBase4f(self.quality.point_shadow_steps, self.quality.dir_shadow_steps, 0, 0))
        r.set_shader_input("u_render_q", LVecBase4f(self.quality.ao, self.quality.bloom, 0, 0))
        occ = Texture("occ_dummy")
        occ.setup_2d_texture(1, 1, Texture.T_unsigned_byte, Texture.F_red)
        occ.set_ram_image(b"\x00")
        r.set_shader_input("u_occ", occ)
        r.set_shader_input("u_occ_info", LVecBase4f(0, 0, 1, 1))
        # sprites: entradas padrão (cada sprite sobrescreve as suas)
        r.set_shader_input("u_frame", LVecBase4f(0, 0, 1, 1))
        r.set_shader_input("u_sprite", LVecBase4f(0.02, 0, 0, 0))
        r.set_shader_input("u_flash", LVecBase4f(1, 1, 1, 0))
        r.set_shader_input("u_tint", LVecBase4f(1, 1, 1, 1))
        r.set_shader_input("u_glow", LVecBase4f(0, 0, 0, 0))
        r.set_shader_input("u_sheet", LVecBase4f(1, 1, 0, 0))
        self.world_root.set_shader(shader_lib.load("world.vert", "world.frag"))
        self.sprite_root.set_shader(shader_lib.load("sprite.vert", "sprite.frag"))
        self.shade_root.set_shader(shader_lib.load("fx.vert", "shade.frag"))
        self.shade_root.set_transparency(TransparencyAttrib.M_alpha)
        self.shade_root.set_depth_write(False)
        self.shade_root.set_bin("fixed", 5)
        self.fx_root.set_shader(shader_lib.load("fx.vert", "fx.frag"))
        self.fx_root.set_attrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add, ColorBlendAttrib.O_one, ColorBlendAttrib.O_one))
        self.fx_root.set_depth_write(False)
        self.fx_root.set_bin("fixed", 20)
        for np_ in (self.world_root, self.sprite_root, self.shade_root, self.fx_root):
            np_.set_two_sided(True)

    def make_buffer(self, name, size, tex, hdr=True, depth=True):
        fbp = FrameBufferProperties()
        if hdr:
            fbp.set_rgba_bits(16, 16, 16, 16)
            fbp.set_float_color(True)
        else:
            fbp.set_rgba_bits(8, 8, 8, 8)
        fbp.set_depth_bits(24 if depth else 0)
        props = WindowProperties.size(*size)
        buf = self.engine.make_output(self.base.pipe, name, -10 + len(self.passes), fbp, props,
                                      GraphicsPipe.BF_refuse_window, self.base.win.get_gsg(), self.base.win)
        if buf is None:
            raise RuntimeError(f"não foi possível criar o buffer {name}")
        buf.add_render_texture(tex, GraphicsOutput.RTM_bind_or_copy, GraphicsOutput.RTP_color)
        buf.set_clear_color_active(True)
        buf.set_clear_color((0, 0, 0, 1))
        return buf

    def make_flat_camera(self, name, scene):
        cam = NodePath(PandaCamera(name))
        lens = OrthographicLens()
        lens.set_film_size(2, 2)
        lens.set_near_far(-100, 100)
        cam.node().set_lens(lens)
        cam.node().set_scene(scene)
        cam.reparent_to(scene)
        return cam

    def window_size(self):
        w = self.base.win
        return max(64, w.get_x_size()), max(64, w.get_y_size())

    def _compute_sizes(self):
        W, H = self.window_size()
        target_h = self.quality.internal_height
        scale = max(1, round(H / target_h))
        iw, ih = W // scale, H // scale
        return W, H, scale, iw, ih

    def _build(self):
        W, H, scale, iw, ih = self._compute_sizes()
        self._built_for = (W, H, self.quality.internal_height)
        self.scale, self.iw, self.ih = scale, iw, ih
        # buffer da cena com 1 pixel de margem de cada lado (para a rolagem subpixel)
        self.bw, self.bh = iw + 2, ih + 2
        self.scene_tex = _tex(True, "scene")
        self.scene_buf = self.make_buffer("scene", (self.bw, self.bh), self.scene_tex, hdr=True, depth=True)
        self.scene_buf.set_clear_color((0, 0, 0, 1))
        self.scene_cam = NodePath(PandaCamera("scene_cam"))
        lens = OrthographicLens()
        lens.set_film_size(10000, 10000)
        lens.set_near_far(-10000, 10000)
        self.scene_cam.node().set_lens(lens)
        self.scene_cam.node().set_scene(self.scene_root)
        self.scene_cam.reparent_to(self.scene_root)
        dr = self.scene_buf.make_display_region()
        dr.set_camera(self.scene_cam)
        self.passes = []
        hw, hh = max(8, self.bw // 2), max(8, self.bh // 2)
        qw, qh = max(4, self.bw // 4), max(4, self.bh // 4)
        bright = Pass(self, "bright", (hw, hh), "bright.frag")
        bright.quad.set_shader_input("u_src", self.scene_tex)
        bright.quad.set_shader_input("u_texel", LVecBase4f(1 / self.bw, 1 / self.bh, 0.9, 0.8))
        self.passes.append(bright)
        blur1h = Pass(self, "blur1h", (hw, hh), "blur.frag")
        blur1h.quad.set_shader_input("u_src", bright.tex)
        blur1h.quad.set_shader_input("u_dir", LVecBase4f(1.0 / hw, 0, 0, 0))
        self.passes.append(blur1h)
        blur1v = Pass(self, "blur1v", (hw, hh), "blur.frag")
        blur1v.quad.set_shader_input("u_src", blur1h.tex)
        blur1v.quad.set_shader_input("u_dir", LVecBase4f(0, 1.0 / hh, 0, 0))
        self.passes.append(blur1v)
        blur2h = Pass(self, "blur2h", (qw, qh), "blur.frag")
        blur2h.quad.set_shader_input("u_src", blur1v.tex)
        blur2h.quad.set_shader_input("u_dir", LVecBase4f(1.5 / qw, 0, 0, 0))
        self.passes.append(blur2h)
        blur2v = Pass(self, "blur2v", (qw, qh), "blur.frag")
        blur2v.quad.set_shader_input("u_src", blur2h.tex)
        blur2v.quad.set_shader_input("u_dir", LVecBase4f(0, 1.5 / qh, 0, 0))
        self.passes.append(blur2v)
        self.bloom1, self.bloom2 = blur1v.tex, blur2v.tex
        # composição na janela
        self.final_root = NodePath("final_root")
        self.final_root.set_two_sided(True)
        self.final_root.set_depth_test(False)
        self.final_root.set_depth_write(False)
        comp = fullscreen_quad("composite")
        comp.reparent_to(self.final_root)
        comp.set_shader(shader_lib.load("post.vert", "composite.frag"))
        comp.set_shader_input("u_scene", self.scene_tex)
        comp.set_shader_input("u_bloom1", self.bloom1)
        comp.set_shader_input("u_bloom2", self.bloom2)
        sx, sy = iw * scale / W, ih * scale / H
        comp.set_shader_input("u_rect", LVecBase4f(sx, sy, 0, 0))
        self.comp = comp
        ui = fullscreen_quad("ui")
        ui.reparent_to(self.final_root)
        ui.set_shader(shader_lib.load("post.vert", "ui.frag"))
        ui.set_shader_input("u_rect", LVecBase4f(1, 1, 0, 0))
        ui.set_shader_input("u_ui", self.ui_tex)
        ui.set_transparency(TransparencyAttrib.M_alpha)
        ui.set_bin("fixed", 10)
        self.ui_card = ui
        self.final_cam = self.make_flat_camera("final_cam", self.final_root)
        self.final_dr = self.base.win.make_display_region()
        self.final_dr.set_sort(5)
        self.final_dr.set_camera(self.final_cam)
        self.final_dr.set_clear_color_active(True)
        self.final_dr.set_clear_color((0, 0, 0, 1))
        self._apply_composite_inputs()

    def _teardown(self):
        for p in self.passes:
            p.destroy(self.engine)
        self.passes = []
        self.engine.remove_window(self.scene_buf)
        self.base.win.remove_display_region(self.final_dr)
        self.scene_cam.remove_node()
        self.final_root.remove_node()

    def rebuild_if_needed(self):
        W, H = self.window_size()
        if (W, H, self.quality.internal_height) != self._built_for:
            self._teardown()
            self._build()
            return True
        return False

    def apply_quality(self):
        self.scene_root.set_shader_input("u_shadow_q", LVecBase4f(self.quality.point_shadow_steps,
                                                                  self.quality.dir_shadow_steps, 0, 0))
        self.scene_root.set_shader_input("u_render_q", LVecBase4f(self.quality.ao, self.quality.bloom, 0, 0))
        self.rebuild_if_needed()

    # ------------------------------------------------------------------ por quadro
    def set_environment(self, env):
        r = self.scene_root
        r.set_shader_input("u_amb_sky", env.amb_sky)
        r.set_shader_input("u_amb_ground", env.amb_ground)
        r.set_shader_input("u_dir_dir", env.dir_dir)
        r.set_shader_input("u_dir_col", env.dir_col)
        r.set_shader_input("u_fog", LVecBase4f(*env.fog_col, env.fog_amount))
        self.grade.update(lift=env.lift, gain=env.gain, exposure=env.exposure, saturation=env.saturation)
        self.fx["vignette"] = env.vignette
        self.base_floor = env.floor_y
        self.light_bands = env.light_bands

    def set_occupancy(self, tex, origin_x, origin_z, w, h):
        self.scene_root.set_shader_input("u_occ", tex)
        self.scene_root.set_shader_input("u_occ_info", LVecBase4f(origin_x, origin_z, 1.0 / w, 1.0 / h))

    def set_lights(self, lights, focus):
        """lights: objetos com pos, color, intensity, radius, shadows. Escolhe as mais relevantes."""
        fx, fz = focus
        ranked = []
        hw = self.bw / PPU * 0.5 * self.zoom + 4
        hh = self.bh / PPU * 0.5 * self.zoom + 4
        for L in lights:
            if L.intensity <= 0.001:
                continue
            dx = abs(L.pos[0] - fx) - hw
            dz = abs(L.pos[2] + L.pos[1] - fz) - hh
            if dx > L.radius or dz > L.radius:
                continue
            ranked.append((max(dx, dz, 0) - L.intensity * L.radius * 0.1, L))
        ranked.sort(key=lambda t: t[0])
        n = min(len(ranked), self.quality.max_lights)
        for i in range(n):
            L = ranked[i][1]
            self.lpos[i] = LVecBase4f(L.pos[0], L.pos[1], L.pos[2], L.radius)
            c = L.current_color()
            self.lpos[i] = LVecBase4f(L.pos[0], L.pos[1], L.pos[2], L.radius)
            self.lcol[i] = LVecBase4f(c[0], c[1], c[2], 1.0 if (L.shadows and self.quality.point_shadow_steps > 0) else 0.0)
        self.scene_root.set_shader_input("u_nlights", n)

    def view_extent(self):
        """Meia largura/altura visível em unidades de mundo (já com zoom)."""
        return self.iw / PPU * 0.5 * self.zoom, self.ih / PPU * 0.5 * self.zoom

    def update(self, dt, cam_x, cam_z):
        self.time += dt
        self.rebuild_if_needed()
        self.zoom += (self.zoom_target - self.zoom) * min(1.0, dt * 3.0)
        z = self.zoom
        # o zoom altera a quantidade de mundo dentro do buffer (pixels continuam definidos)
        unit = 1.0 / PPU * z
        sx = round(cam_x / unit)
        sz = round(cam_z / unit)
        from .projection import project_relative
        dx, dz = cam_x - sx * unit, cam_z - sz * unit
        fx, fz, _ = project_relative(dx / unit, 0.0, dz / unit)
        self.cam_x, self.cam_z = cam_x, cam_z
        cx, cz = sx * unit, sz * unit
        hw, hh = self.bw * 0.5 * unit, self.bh * 0.5 * unit
        r = self.scene_root
        r.set_shader_input("u_view", LVecBase4f(cx, cz, hw, hh))
        r.set_shader_input("u_misc", LVecBase4f(self.time, getattr(self, "light_bands", 6), 1.0,
                                                getattr(self, "base_floor", 0.0)))
        # deslocamento subpixel: amostra o buffer interno com 1 pixel de margem
        u0 = (1.0 + fx) / self.bw
        v0 = (1.0 + fz) / self.bh
        self.comp.set_shader_input("u_scene_uv", LVecBase4f(u0, v0, self.iw / self.bw, self.ih / self.bh))
        self._apply_composite_inputs()
        return cx, cz

    def _apply_composite_inputs(self):
        g, f = self.grade, self.fx
        c = self.comp
        c.set_shader_input("u_grade_lift", LVecBase4f(*g["lift"], g["exposure"]))
        c.set_shader_input("u_grade_gain", LVecBase4f(*g["gain"], g["saturation"]))
        c.set_shader_input("u_fx", LVecBase4f(f["vignette"], f["grain"] * self.quality.grain, f["aberration"], self.time % 100))
        c.set_shader_input("u_fx2", LVecBase4f(f["fade"], f["desat"], f["bloom"] * self.quality.bloom, f["hurt"]))
        c.set_shader_input("u_fx3", LVecBase4f(f["flash"], f["dim"], 0, 0))
        if not hasattr(self, "_scene_uv_set"):
            c.set_shader_input("u_scene_uv", LVecBase4f(1 / self.bw, 1 / self.bh, self.iw / self.bw, self.ih / self.bh))
            self._scene_uv_set = True

    def upload_ui(self, rgba_bytes, w, h):
        t = self.ui_tex
        if t.get_x_size() != w or t.get_y_size() != h:
            t.setup_2d_texture(w, h, Texture.T_unsigned_byte, Texture.F_rgba8)
            t.set_minfilter(SamplerState.FT_nearest)
            t.set_magfilter(SamplerState.FT_nearest)
        t.set_ram_image(rgba_bytes)

    def world_to_screen(self, x, y, z):
        """Posição em pixels da janela (origem no canto superior esquerdo) de um ponto do mundo."""
        W, H = self.window_size()
        unit = 1.0 / PPU * self.zoom
        from .projection import project_relative
        px, py, _ = project_relative(x - self.cam_x, y, z - self.cam_z)
        px, py = px / unit, py / unit
        ox = (W - self.iw * self.scale) * 0.5
        oy = (H - self.ih * self.scale) * 0.5
        return ox + (self.iw * 0.5 + px) * self.scale, oy + (self.ih * 0.5 - py) * self.scale
