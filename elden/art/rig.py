"""Esqueletos procedurais e rasterização em pixel art.

Um 'Rig' descreve proporções e aparência (cores, roupas, arma). Uma 'Pose' descreve ângulos das
articulações. O rasterizador projeta o esqueleto 3D na vista oblíqua do jogo para uma direção e
desenha as partes (membros como cápsulas, tronco, cabeça, capa, saia, arma, asas...) com
ordenação por profundidade, sombreamento de borda por parte e contorno escuro.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

from .pixel import hexc

DEPTH_K = 0.5          # quanto a profundidade (norte) sobe na tela no sprite
EMISSIVE_A = 120       # alfa que o shader de sprites trata como emissivo


def shade3(col, k_dark=0.62, k_light=1.25):
    c = np.array(col, dtype=np.float32)
    return (tuple(np.clip(c * k_dark, 0, 255).astype(int)), tuple(c.astype(int)),
            tuple(np.clip(c * k_light + 12, 0, 255).astype(int)))


def C(v):
    return hexc(v) if isinstance(v, str) else tuple(v)


# ---------------------------------------------------------------------------- matemática
def rot_x(v, a):
    x, y, z = v
    c, s = math.cos(a), math.sin(a)
    return (x, y * c - z * s, y * s + z * c)


def rot_y(v, a):
    x, y, z = v
    c, s = math.cos(a), math.sin(a)
    return (x * c + z * s, y, -x * s + z * c)


def rot_z(v, a):
    x, y, z = v
    c, s = math.cos(a), math.sin(a)
    return (x * c - y * s, x * s + y * c, z)


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def mul(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def norm3(a):
    l = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2) or 1.0
    return (a[0] / l, a[1] / l, a[2] / l)


D2R = math.pi / 180.0


# ---------------------------------------------------------------------------- pose
class Pose(dict):
    """Ângulos em graus. Chaves (com padrões):
    bob, lean, twist, head_tilt, head_turn,
    r_arm_p, r_arm_o, r_elbow, l_arm_p, l_arm_o, l_elbow,
    r_leg_p, r_knee, l_leg_p, l_knee, weapon (ângulo da arma em relação ao antebraço),
    weapon_roll, crouch, offset_y (salto), cape (balanço), wings, spin (giro do corpo), lift (braço levantado)
    """
    DEFAULTS = dict(bob=0.0, lean=0.0, twist=0.0, head_tilt=0.0, head_turn=0.0,
                    r_arm_p=8.0, r_arm_o=10.0, r_elbow=15.0, l_arm_p=8.0, l_arm_o=10.0, l_elbow=15.0,
                    r_leg_p=0.0, r_knee=0.0, l_leg_p=0.0, l_knee=0.0, weapon=70.0, weapon_roll=0.0,
                    crouch=0.0, offset_y=0.0, cape=0.0, wings=0.0, spin=0.0, sideways=0.0, squash=1.0,
                    jaw=0.0, glow=0.0, tail=0.0, flap=0.0)

    def __getitem__(self, k):
        if k in self:
            return dict.__getitem__(self, k)
        return self.DEFAULTS.get(k, 0.0)


def lerp_pose(a, b, t):
    out = Pose()
    for k in set(a) | set(b) | set(Pose.DEFAULTS):
        out[k] = a[k] + (b[k] - a[k]) * t
    return out


# ---------------------------------------------------------------------------- rig humanoide
class Rig:
    """Aparência + proporções. Valores em pixels (escala 1)."""

    def __init__(self, **kw):
        self.kind = kw.get("kind", "humanoid")
        self.scale = kw.get("scale", 1.0)
        s = self.scale
        self.leg = kw.get("leg", 11.0) * s
        self.torso = kw.get("torso", 9.0) * s
        self.shoulder = kw.get("shoulder", 7.0) * s
        self.hips = kw.get("hips", 4.5) * s
        self.arm = kw.get("arm", 9.0) * s
        self.head_r = kw.get("head_r", 3.4) * s
        self.neck = kw.get("neck", 1.0) * s
        self.limb_w = kw.get("limb_w", 2.6) * s
        self.leg_w = kw.get("leg_w", 3.0) * s
        self.torso_w = kw.get("torso_w", 6.5) * s
        self.torso_d = kw.get("torso_d", 4.0) * s
        self.colors = {k: C(v) for k, v in kw.get("colors", {}).items()}
        self.parts = kw.get("parts", {})          # acessórios: hood, helmet, hat, horns, ears, snout, hair, cape, skirt, wings, halo, tail
        self.weapon = kw.get("weapon")            # tipo de arma desenhada
        self.offhand = kw.get("offhand")          # shield, book, dagger, none
        self.eyes = C(kw.get("eyes", "#1a1414"))
        self.eyes_glow = kw.get("eyes_glow", False)
        self.extra_arms = kw.get("extra_arms", 0)
        self.hunch = kw.get("hunch", 0.0)
        self.frame = kw.get("frame", 48)
        self.anchor_y = kw.get("anchor_y", 0.9)
        self.blocky = kw.get("blocky", False)      # autômatos: membros quadrados
        self.translucent = kw.get("translucent", False)
        self.glow_parts = set(kw.get("glow_parts", []))

    def col(self, key, default="#808080"):
        return self.colors.get(key, C(default))


class Part:
    __slots__ = ("kind", "pts", "w", "color", "depth", "emissive", "extra")

    def __init__(self, kind, pts, w, color, depth, emissive=False, extra=None):
        self.kind = kind
        self.pts = pts
        self.w = w
        self.color = color
        self.depth = depth
        self.emissive = emissive
        self.extra = extra


def build_humanoid(rig, pose, facing_deg):
    """Calcula as partes 3D do humanoide para uma pose e direção. Devolve lista de Part (pontos 3D)."""
    p = pose
    s = rig.scale
    face = (90.0 - facing_deg + p["spin"]) * D2R
    lean = (p["lean"] + rig.hunch) * D2R
    twist = p["twist"] * D2R
    crouch = p["crouch"] * s
    hip_y = rig.leg - crouch + p["bob"] * s + p["offset_y"] * s

    def W(v):
        """Local (personagem olhando +Z) -> mundo (rotação de direção)."""
        return rot_y(v, face)

    pelvis = (0.0, hip_y, 0.0)
    up = rot_x((0.0, 1.0, 0.0), lean)
    up = rot_y(up, twist * 0.3)
    chest = add(pelvis, mul(up, rig.torso))
    neck_top = add(chest, mul(up, rig.neck + rig.head_r * 0.9))
    head_c = rot_x(add(neck_top, (0, 0, 0)), 0)
    side = rot_y((1.0, 0.0, 0.0), twist)
    parts = []
    skin = rig.col("skin", "#c89878")
    cloth = rig.col("cloth", "#6a5a50")
    cloth2 = rig.col("cloth2", "#3a3238")
    metal = rig.col("metal", "#9aa0aa")
    legc = rig.col("legs", cloth2)
    boots = rig.col("boots", "#2a2020")
    armc = rig.col("arms", cloth)
    handc = rig.col("hands", skin)

    # ---- pernas
    for sgn, lp, kn in ((1, p["r_leg_p"], p["r_knee"]), (-1, p["l_leg_p"], p["l_knee"])):
        hip = add(pelvis, mul(side, sgn * rig.hips * 0.5))
        thigh = rot_x((0.0, -1.0, 0.0), -lp * D2R)
        thigh = rot_y(thigh, twist * 0.2)
        knee = add(hip, mul(thigh, rig.leg * 0.52))
        shin = rot_x((0.0, -1.0, 0.0), (-lp + kn) * D2R)
        shin = rot_y(shin, twist * 0.2)
        foot = add(knee, mul(shin, rig.leg * 0.5))
        toe = add(foot, rot_y((0.0, 0.0, 1.6 * s), twist * 0.2))
        parts.append(Part("limb", [W(hip), W(knee)], rig.leg_w, legc, 0))
        parts.append(Part("limb", [W(knee), W(foot)], rig.leg_w * 0.9, legc, 0))
        parts.append(Part("limb", [W(foot), W(toe)], rig.leg_w * 0.9, boots, 0))
    # ---- saia/manto (cobre pernas)
    sk = rig.parts.get("skirt")
    if sk:
        length = sk.get("len", 0.9) * rig.leg
        flare = sk.get("flare", 1.6)
        top_c = add(pelvis, mul(up, 1.0 * s))
        ring_top = []
        ring_bot = []
        for i in range(8):
            a = i / 8 * math.tau
            ring_top.append(add(top_c, (math.cos(a) * rig.torso_w * 0.55, 0.0, math.sin(a) * rig.torso_d * 0.6)))
            ring_bot.append(add(top_c, (math.cos(a) * rig.torso_w * 0.55 * flare, -length,
                                        math.sin(a) * rig.torso_d * 0.6 * flare + (p["r_leg_p"] - p["l_leg_p"]) * 0.02)))
        parts.append(Part("hull", [W(v) for v in ring_top + ring_bot], 0, rig.col("skirt", cloth), 0))
    # ---- tronco
    tw, td = rig.torso_w, rig.torso_d
    corners = []
    for (cx, base, wmul) in ((1, pelvis, 0.42), (-1, pelvis, 0.42), (1, chest, 0.5), (-1, chest, 0.5)):
        for dz in (-1, 1):
            corners.append(add(add(base, mul(side, cx * tw * wmul)), rot_y((0, 0, dz * td * 0.5), twist)))
    torso_col = rig.col("torso", cloth)
    parts.append(Part("hull", [W(v) for v in corners], 0, torso_col, 0,
                      extra={"belt": rig.col("belt", "#3a2a1a"), "accent": rig.col("accent", torso_col),
                             "pelvis": W(pelvis), "chest": W(chest)}))
    # peitoral/armadura
    if rig.parts.get("chestplate"):
        cp = rig.parts["chestplate"]
        c1 = add(chest, mul(up, -1.0 * s))
        c2 = add(pelvis, mul(up, rig.torso * 0.45))
        parts.append(Part("limb", [W(add(c1, rot_y((0, 0, td * 0.45), twist))), W(add(c2, rot_y((0, 0, td * 0.45), twist)))],
                          tw * 0.75, C(cp.get("color", "#8890a0")), 0.3))
    # ---- capa
    cape = rig.parts.get("cape")
    if cape:
        swing = p["cape"] * D2R
        back = rot_y((0, 0, -td * 0.6), twist)
        top_l = add(add(chest, mul(side, tw * 0.45)), back)
        top_r = add(add(chest, mul(side, -tw * 0.45)), back)
        clen = cape.get("len", 1.1) * (rig.torso + rig.leg * 0.6)
        down = rot_x((0, -1, -0.25 - swing * 0.6), 0)
        bot_l = add(top_l, add(mul(norm3(down), clen), mul(side, tw * 0.25)))
        bot_r = add(top_r, add(mul(norm3(down), clen), mul(side, -tw * 0.25)))
        parts.append(Part("poly", [W(top_l), W(top_r), W(bot_r), W(bot_l)], 0, C(cape.get("color", "#5a1a20")), -0.6))
    # ---- asas
    wings = rig.parts.get("wings")
    if wings:
        flap = (p["wings"] + math.sin(p["flap"] * D2R) * 20) * D2R
        span = wings.get("span", 14.0) * s
        for sgn in (1, -1):
            root = add(add(chest, mul(side, sgn * tw * 0.3)), rot_y((0, 0, -td * 0.6), twist))
            tip = add(root, rot_y((sgn * span * math.cos(flap * 0.5), span * (0.35 + math.sin(flap) * 0.5), -span * 0.35), twist))
            mid = add(root, rot_y((sgn * span * 0.55, -span * 0.25, -span * 0.25), twist))
            parts.append(Part("poly", [W(root), W(tip), W(mid)], 0, C(wings.get("color", "#e8e0d0")), -0.8,
                              emissive=wings.get("glow", False)))
    # ---- cabeça
    head = add(chest, mul(up, rig.neck + rig.head_r))
    head = add(head, rot_y((0, 0, p["head_tilt"] * 0.05 * s), twist))
    parts.append(Part("head", [W(head)], rig.head_r, rig.col("head", skin), 0.2,
                      extra={"face_dir": W(rot_y((0, 0, 1), twist + p["head_turn"] * D2R)), "rig": rig, "jaw": p["jaw"]}))
    # ---- braços (direito empunha a arma)
    shoulder_y = add(chest, mul(up, -1.0 * s))
    hands = {}
    arm_sets = [(1, p["r_arm_p"], p["r_arm_o"], p["r_elbow"]), (-1, p["l_arm_p"], p["l_arm_o"], p["l_elbow"])]
    for k in range(rig.extra_arms):
        o = 25 + k * 15
        arm_sets.append((1 if k % 2 == 0 else -1, p["r_arm_p"] * (0.6 + 0.2 * k) + 30, o, p["r_elbow"] + 20))
    for idx, (sgn, ap, ao, el) in enumerate(arm_sets):
        sh = add(shoulder_y, mul(side, sgn * rig.shoulder * 0.5 + (0 if idx < 2 else -sgn * 0.5 * s)))
        if idx >= 2:
            sh = add(sh, mul(up, -2.5 * s * (idx - 1)))
        d1 = rot_x((0.0, -1.0, 0.0), -ap * D2R)
        d1 = rot_z(d1, sgn * ao * D2R)
        d1 = rot_y(d1, twist)
        elbow = add(sh, mul(d1, rig.arm * 0.5))
        d2 = rot_x((0.0, -1.0, 0.0), -(ap + el) * D2R)
        d2 = rot_z(d2, sgn * ao * D2R * 0.6)
        d2 = rot_y(d2, twist)
        hand = add(elbow, mul(d2, rig.arm * 0.5))
        col = armc if idx < 2 else rig.col("extra_arm", "#9a5a50")
        parts.append(Part("limb", [W(sh), W(elbow)], rig.limb_w, col, 0.1))
        parts.append(Part("limb", [W(elbow), W(hand)], rig.limb_w * 0.9, col, 0.1))
        parts.append(Part("ball", [W(hand)], rig.limb_w * 0.65, handc, 0.15))
        if rig.parts.get("pauldrons") and idx < 2:
            parts.append(Part("ball", [W(sh)], rig.limb_w * 1.05, C(rig.parts["pauldrons"]), 0.12))
        if idx < 2:
            hands[sgn] = (hand, d2)
    # ---- arma e mão secundária
    if rig.weapon and 1 in hands:
        hand, fdir = hands[1]
        add_weapon(parts, rig, rig.weapon, hand, fdir, p, W, side, twist)
    if rig.offhand and -1 in hands:
        hand, fdir = hands[-1]
        add_offhand(parts, rig, rig.offhand, hand, fdir, p, W, side, twist)
    # ---- cauda
    tail = rig.parts.get("tail")
    if tail:
        base = add(pelvis, rot_y((0, 0.5 * s, -td * 0.6), twist))
        sw = math.sin(p["tail"] * D2R) * 0.6
        tip = add(base, rot_y((sw * 4 * s, -3 * s, -tail.get("len", 7) * s), twist))
        parts.append(Part("limb", [W(base), W(tip)], tail.get("w", 2.2) * s, C(tail.get("color", "#4a3a3a")), -0.2))
    # ---- auréola
    halo = rig.parts.get("halo")
    if halo:
        hc = add(head, (0, rig.head_r * 1.6, -rig.head_r * 0.6))
        parts.append(Part("ring", [W(hc)], halo.get("r", 5.0) * s, C(halo.get("color", "#ffe08a")), 0.25, emissive=True,
                          extra={"broken": halo.get("broken", False)}))
    return parts


def add_weapon(parts, rig, kind, hand, fdir, p, W, side, twist):
    s = rig.scale
    wa = p["weapon"] * D2R
    # direção da arma: a partir do antebraço, girada em torno do eixo lateral
    axis_dir = norm3(rot_x(fdir, -wa))
    if abs(axis_dir[1]) > 0.999:
        axis_dir = norm3(add(axis_dir, (0.0, 0.0, 0.01)))
    metal = rig.col("blade", "#c8ccd4")
    grip = rig.col("grip", "#4a3020")
    accent = rig.col("accent", "#b08a3a")
    glow = rig.col("glow", "#9a7aff")

    def seg(a_len, b_len, w, col, emissive=False, depth=0.35):
        a = add(hand, mul(axis_dir, a_len * s))
        b = add(hand, mul(axis_dir, b_len * s))
        parts.append(Part("limb", [W(a), W(b)], w * s, col, depth, emissive=emissive))
        return a, b

    if kind in ("sword", "rapier", "katana"):
        L = {"sword": 13, "rapier": 14, "katana": 13}[kind]
        wdt = {"sword": 1.6, "rapier": 0.9, "katana": 1.2}[kind]
        seg(-2, 1.0, 1.3, grip)
        a, _ = seg(0.6, 1.0, 3.8 if kind == "sword" else 2.4, accent, depth=0.36)
        seg(1.0, L, wdt, metal, emissive=rig.parts.get("weapon_glow", False))
    elif kind == "greatsword":
        seg(-3, 1.5, 1.5, grip)
        seg(1.0, 1.6, 5.0, accent, depth=0.36)
        seg(1.5, 19, 2.6, metal)
    elif kind == "daggers":
        seg(-1, 0.8, 1.2, grip)
        seg(0.8, 6.5, 1.3, metal)
    elif kind == "axe":
        _, b = seg(-3, 11, 1.4, grip)
        head_c = add(hand, mul(axis_dir, 9.5 * s))
        perp = norm3(rot_x(axis_dir, -math.pi / 2))
        parts.append(Part("limb", [W(head_c), W(add(head_c, mul(perp, 3.5 * s)))], 4.0 * s, metal, 0.36))
    elif kind == "hammer" or kind == "holy":
        seg(-3, 10, 1.4, grip)
        head_c = add(hand, mul(axis_dir, 10 * s))
        perp = norm3(rot_x(axis_dir, -math.pi / 2))
        col = rig.col("hammer", "#8a8a90" if kind == "hammer" else "#d8c27a")
        parts.append(Part("limb", [W(add(head_c, mul(perp, -2.5 * s))), W(add(head_c, mul(perp, 2.5 * s)))], 4.2 * s, col, 0.36,
                          emissive=(kind == "holy" and p["glow"] > 0.5)))
    elif kind == "scythe":
        seg(-6, 14, 1.3, grip)
        top = add(hand, mul(axis_dir, 14 * s))
        perp = norm3(rot_x(axis_dir, -math.pi / 2))
        mid = add(top, add(mul(perp, 6 * s), mul(axis_dir, -1.5 * s)))
        tip = add(top, add(mul(perp, 9 * s), mul(axis_dir, -5 * s)))
        parts.append(Part("limb", [W(top), W(mid)], 2.0 * s, metal, 0.36))
        parts.append(Part("limb", [W(mid), W(tip)], 1.4 * s, metal, 0.36))
    elif kind == "chain":
        n = 7
        reach = 4 + 10 * max(0.0, min(1.0, p["glow"]))
        prev = hand
        for i in range(1, n + 1):
            t = i / n
            pt = add(hand, add(mul(axis_dir, reach * t * s), (0, -math.sin(t * math.pi) * 2.5 * s * (1 - p["glow"]), 0)))
            parts.append(Part("ball", [W(pt)], 0.9 * s, metal, 0.36))
            prev = pt
        parts.append(Part("ball", [W(prev)], 1.6 * s, rig.col("hook", "#a0a4ac"), 0.37))
    elif kind == "staff":
        seg(-7, 12, 1.4, grip)
        orb = add(hand, mul(axis_dir, 13 * s))
        parts.append(Part("ball", [W(orb)], 2.2 * s, glow, 0.37, emissive=True))
    elif kind == "gun":
        # sabre na mão direita
        seg(-1.5, 1.0, 1.3, grip)
        seg(1.0, 11, 1.2, metal)
    elif kind == "claws":
        perp = norm3(rot_x(axis_dir, -math.pi / 2))
        for k in (-1, 0, 1):
            a = add(hand, mul(perp, k * 0.8 * s))
            b = add(a, mul(axis_dir, 4.5 * s))
            parts.append(Part("limb", [W(a), W(b)], 0.8 * s, metal, 0.36))
    elif kind == "book":
        pass
    elif kind == "scalpel":
        seg(0, 4, 0.9, metal)
    elif kind == "flail":
        seg(-1, 4, 1.2, grip)
        ball = add(hand, mul(axis_dir, 8 * s))
        parts.append(Part("ball", [W(ball)], 2.0 * s, metal, 0.36))
    elif kind == "crossbow":
        seg(-2, 6, 1.6, grip)
        perp = norm3(rot_x(axis_dir, -math.pi / 2))
        c = add(hand, mul(axis_dir, 5 * s))
        parts.append(Part("limb", [W(add(c, mul(side, -3 * s))), W(add(c, mul(side, 3 * s)))], 1.0 * s, grip, 0.36))
    elif kind == "lance":
        seg(-6, 16, 1.3, grip)
        seg(14, 18, 2.0, metal)


def add_offhand(parts, rig, kind, hand, fdir, p, W, side, twist):
    s = rig.scale
    if kind == "shield":
        out = rot_y((0, 0, 1.2 * s), twist)
        c = add(hand, out)
        parts.append(Part("shield", [W(c)], 4.2 * s, rig.col("shield", "#5a4a3a"), 0.4,
                          extra={"rim": rig.col("shield_rim", "#a8a8b0"), "emblem": rig.col("emblem", "#c8a040")}))
    elif kind == "book":
        c = add(hand, rot_y((0, 1.0 * s, 1.2 * s), twist))
        parts.append(Part("ball", [W(c)], 2.4 * s, rig.col("book", "#4a2a5a"), 0.38))
        parts.append(Part("ball", [W(add(c, (0, 0.8 * s, 0)))], 1.0 * s, rig.col("glow", "#b090ff"), 0.39, emissive=True))
    elif kind == "dagger":
        axis_dir = norm3(rot_x(fdir, -70 * D2R))
        a = add(hand, mul(axis_dir, 0.8 * s))
        b = add(hand, mul(axis_dir, 6.5 * s))
        parts.append(Part("limb", [W(a), W(b)], 1.3 * s, rig.col("blade", "#c8ccd4"), 0.35))
    elif kind == "rifle":
        axis_dir = norm3(rot_x(fdir, -p["weapon"] * D2R * 0.2 - 80 * D2R))
        a = add(hand, mul(axis_dir, -3 * s))
        b = add(hand, mul(axis_dir, 12 * s))
        parts.append(Part("limb", [W(a), W(b)], 1.8 * s, rig.col("gun", "#3a3230"), 0.34))
        parts.append(Part("limb", [W(add(hand, mul(axis_dir, 4 * s))), W(b)], 1.0 * s, rig.col("barrel", "#8a7a60"), 0.35))
    elif kind == "claws":
        axis_dir = norm3(rot_x(fdir, -70 * D2R))
        for k in (-1, 0, 1):
            a = add(hand, mul(side, k * 0.8 * s))
            parts.append(Part("limb", [W(a), W(add(a, mul(axis_dir, 4.5 * s)))], 0.8 * s, rig.col("blade", "#c8ccd4"), 0.36))
    elif kind == "orb":
        c = add(hand, rot_y((0, 1.5 * s, 1.0 * s), twist))
        parts.append(Part("ball", [W(c)], 1.8 * s, rig.col("glow", "#9a7aff"), 0.39, emissive=True))


# ---------------------------------------------------------------------------- quadrúpedes e outros corpos
def build_quadruped(rig, pose, facing_deg):
    p = pose
    s = rig.scale
    face = (90.0 - facing_deg + p["spin"]) * D2R

    def W(v):
        return rot_y(v, face)

    body_len = rig.parts.get("body_len", 10.0) * s
    body_h = rig.leg * 0.9 + p["bob"] * s + p["offset_y"] * s - p["crouch"] * s
    pitch = p["lean"] * D2R
    front = (0.0, body_h + math.sin(pitch) * body_len * 0.5, body_len * 0.5)
    back = (0.0, body_h - math.sin(pitch) * body_len * 0.5, -body_len * 0.5)
    parts = []
    fur = rig.col("cloth", "#5a4a40")
    fur2 = rig.col("cloth2", "#3a2e28")
    for (anchor, lp, kn, sx) in ((front, p["r_arm_p"], p["r_elbow"], 1), (front, p["l_arm_p"], p["l_elbow"], -1),
                                 (back, p["r_leg_p"], p["r_knee"], 1), (back, p["l_leg_p"], p["l_knee"], -1)):
        hip = add(anchor, (sx * rig.torso_w * 0.35, 0, 0))
        d1 = rot_x((0, -1, 0), -lp * D2R)
        knee = add(hip, mul(d1, rig.leg * 0.5))
        d2 = rot_x((0, -1, 0), (-lp + kn) * D2R)
        foot = add(knee, mul(d2, rig.leg * 0.5))
        parts.append(Part("limb", [W(hip), W(knee)], rig.leg_w, fur2, 0))
        parts.append(Part("limb", [W(knee), W(foot)], rig.leg_w * 0.85, fur2, 0))
    parts.append(Part("limb", [W(back), W(front)], rig.torso_w, fur, 0.1))
    # pescoço e cabeça
    neck = add(front, (0, rig.head_r * 0.8, rig.head_r * 0.6))
    head = add(neck, (0, rig.head_r * 0.4 + p["head_tilt"] * 0.06 * s, rig.head_r * 0.9))
    parts.append(Part("limb", [W(front), W(neck)], rig.torso_w * 0.7, fur, 0.15))
    parts.append(Part("head", [W(head)], rig.head_r, rig.col("head", fur), 0.2,
                      extra={"face_dir": W((0, 0, 1)), "rig": rig, "jaw": p["jaw"], "beast": True}))
    tail = rig.parts.get("tail")
    if tail:
        tb = add(back, (0, 1 * s, -1 * s))
        sw = math.sin(p["tail"] * D2R) * 3 * s
        tt = add(tb, (sw, 1.5 * s, -tail.get("len", 6) * s))
        parts.append(Part("limb", [W(tb), W(tt)], tail.get("w", 2.0) * s, C(tail.get("color", "#4a3a30")), 0.05))
    return parts


def build_blob(rig, pose, facing_deg):
    """Corpos amorfos/voadores: livros, sombras, orbes, morcegos, serras, sentinelas, fragmentos."""
    p = pose
    s = rig.scale
    face = (90.0 - facing_deg + p["spin"]) * D2R

    def W(v):
        return rot_y(v, face)

    shape = rig.parts.get("shape", "orb")
    parts = []
    y0 = rig.leg + p["bob"] * s + p["offset_y"] * s
    col = rig.col("cloth", "#5a4a60")
    if shape == "bat":
        flap = math.sin(p["flap"] * D2R) * 0.9
        c = (0, y0, 0)
        parts.append(Part("ball", [W(c)], 2.6 * s, col, 0.1))
        for sgn in (1, -1):
            tip = (sgn * 7 * s, y0 + flap * 4 * s, -1 * s)
            mid = (sgn * 4 * s, y0 - 2 * s + flap * 2 * s, 0)
            parts.append(Part("poly", [W(c), W(tip), W(mid)], 0, rig.col("wing", "#3a1a22"), 0.0))
        parts.append(Part("head", [W(add(c, (0, 1.5 * s, 1.0 * s)))], 1.8 * s, col, 0.2,
                          extra={"face_dir": W((0, 0, 1)), "rig": rig, "jaw": 0, "beast": True}))
    elif shape == "book":
        flap = math.sin(p["flap"] * D2R) * 25 * D2R
        c = (0, y0, 0)
        for sgn in (1, -1):
            a = rot_z((sgn * 4 * s, 0, 0), sgn * (0.5 + flap))
            parts.append(Part("poly", [W(c), W(add(c, a)), W(add(add(c, a), (0, 0, 5 * s))), W(add(c, (0, 0, 5 * s)))], 0,
                              rig.col("cover", "#5a2a3a"), 0.1))
        parts.append(Part("ball", [W(add(c, (0, 1 * s, 2.5 * s)))], 1.4 * s, rig.col("glow", "#a080ff"), 0.2, emissive=True))
    elif shape == "orb":
        c = (0, y0, 0)
        parts.append(Part("ball", [W(c)], rig.torso_w * 0.6, col, 0.1))
        parts.append(Part("ball", [W(add(c, (0, 0, rig.torso_w * 0.35)))], rig.torso_w * 0.25, rig.col("glow", "#ff6040"), 0.2,
                          emissive=True))
    elif shape == "shadow":
        c = (0, y0, 0)
        wob = math.sin(p["flap"] * D2R) * s
        parts.append(Part("ball", [W(add(c, (0, -2 * s, 0)))], 3.6 * s + wob, col, 0.0))
        parts.append(Part("ball", [W(add(c, (0, 2 * s, 0)))], 3.0 * s - wob * 0.5, col, 0.05))
        parts.append(Part("ball", [W(add(c, (0, -5.5 * s, 0)))], 2.0 * s, col, 0.0))
        for sgn in (1, -1):
            parts.append(Part("ball", [W(add(c, (sgn * 1.2 * s, 3 * s, 2.6 * s)))], 0.8 * s, rig.col("glow", "#c0a0ff"), 0.3, emissive=True))
    elif shape == "saw":
        c = (0, y0, 0)
        parts.append(Part("limb", [W((0, y0 * 0.5, -3 * s)), W((0, y0 * 0.5, 3 * s))], 6 * s, rig.col("body", "#5a4a3a"), 0.0))
        parts.append(Part("ring", [W(add(c, (0, 2 * s, 3.5 * s)))], 4.5 * s, rig.col("blade", "#c0c4cc"), 0.2,
                          extra={"teeth": True, "spin": p["spin"]}))
        parts.append(Part("ball", [W(add(c, (0, 3 * s, 0)))], 1.5 * s, rig.col("glow", "#ff7030"), 0.25, emissive=True))
    elif shape == "turret":
        base = (0, 0, 0)
        top = (0, y0, 0)
        parts.append(Part("limb", [W(base), W(top)], 4.5 * s, rig.col("body", "#4a4038"), 0.0))
        parts.append(Part("ball", [W(top)], 3.4 * s, rig.col("head", "#7a6a50"), 0.1))
        parts.append(Part("limb", [W(top), W(add(top, (0, 0, 5 * s)))], 1.6 * s, rig.col("barrel", "#3a3230"), 0.2))
        parts.append(Part("ball", [W(add(top, (0, 0.8 * s, 1.6 * s)))], 0.9 * s, rig.col("glow", "#ff5020"), 0.3, emissive=True))
    elif shape == "crystal":
        c = (0, y0, 0)
        pts = [W(add(c, (0, 5 * s, 0))), W(add(c, (2.5 * s, 0, 0))), W(add(c, (0, -5 * s, 0))), W(add(c, (-2.5 * s, 0, 0)))]
        parts.append(Part("poly", pts, 0, rig.col("cloth", "#fff0b0"), 0.1, emissive=True))
    elif shape == "rune_pillar":
        base = (0, 0, 0)
        top = (0, y0, 0)
        parts.append(Part("limb", [W(base), W(top)], 5 * s, rig.col("body", "#3a3458"), 0.0))
        for k in range(3):
            parts.append(Part("ball", [W(add(base, (0, y0 * (0.3 + 0.25 * k), 2.4 * s)))], 0.9 * s, rig.col("glow", "#60f0d0"), 0.2,
                              emissive=True))
        parts.append(Part("ball", [W(add(top, (0, 2 * s, 0)))], 2.4 * s, rig.col("glow", "#60f0d0"), 0.25, emissive=True))
    elif shape == "dummy":
        parts.append(Part("limb", [W((0, 0, 0)), W((0, y0 + 6 * s, 0))], 1.5 * s, rig.col("pole", "#5a4030"), 0.0))
        parts.append(Part("limb", [W((0, y0, 0)), W((0, y0 + 7 * s, 0))], 5 * s, rig.col("cloth", "#b09060"), 0.1))
        parts.append(Part("limb", [W((-4 * s, y0 + 5 * s, 0)), W((4 * s, y0 + 5 * s, 0))], 1.6 * s, rig.col("cloth", "#b09060"), 0.1))
        parts.append(Part("ball", [W((0, y0 + 9.5 * s, 0))], 2.6 * s, rig.col("cloth", "#b09060"), 0.2))
    return parts


BUILDERS = {"humanoid": build_humanoid, "quadruped": build_quadruped, "blob": build_blob}


# ---------------------------------------------------------------------------- rasterização
def project(v, ox, oy):
    """Mundo (x, y, z) -> pixel (x, y) com a profundidade (z norte) subindo na tela."""
    return ox + v[0], oy - (v[1] + v[2] * DEPTH_K)


def render_frame(rig, pose, facing_deg, size=None):
    size = size or rig.frame
    parts = BUILDERS[rig.kind](rig, pose, facing_deg)
    W = H = size
    ox, oy = W / 2.0, H * rig.anchor_y
    # ordena: mais ao norte (z maior) primeiro; depois pela prioridade da parte
    parts.sort(key=lambda pt: (-(sum(v[2] for v in pt.pts) / len(pt.pts)) + pt.depth * 0.8))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ids = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(img)
    di = ImageDraw.Draw(ids)
    emis = Image.new("L", (W, H), 0)
    de = ImageDraw.Draw(emis)
    pid = 0
    for part in parts:
        pid = pid % 250 + 1
        col = part.color
        rgba = (int(col[0]), int(col[1]), int(col[2]), 255)
        pts2 = [project(v, ox, oy) for v in part.pts]
        k = part.kind
        if k == "limb":
            (x0, y0), (x1, y1) = pts2
            w = max(1, int(round(part.w)))
            r = part.w / 2.0
            for d in (dr, di, de if part.emissive else None):
                if d is None:
                    continue
                fill = rgba if d is dr else (pid if d is di else 255)
                d.line([(x0, y0), (x1, y1)], fill=fill, width=w)
                if r >= 1.0:
                    d.ellipse([x0 - r + 0.5, y0 - r + 0.5, x0 + r - 0.5, y0 + r - 0.5], fill=fill)
                    d.ellipse([x1 - r + 0.5, y1 - r + 0.5, x1 + r - 0.5, y1 + r - 0.5], fill=fill)
        elif k in ("ball", "head"):
            (x0, y0), = pts2
            r = part.w
            for d in (dr, di, de if part.emissive else None):
                if d is None:
                    continue
                fill = rgba if d is dr else (pid if d is di else 255)
                if k == "head" and part.extra and part.extra.get("beast"):
                    d.ellipse([x0 - r, y0 - r * 0.85, x0 + r, y0 + r * 0.85], fill=fill)
                else:
                    d.ellipse([x0 - r + 0.3, y0 - r + 0.3, x0 + r - 0.3, y0 + r - 0.3], fill=fill)
            if k == "head":
                draw_head_details(dr, de, rig, part, x0, y0, pose)
        elif k in ("hull", "poly"):
            pts = pts2
            if k == "hull":
                pts = convex_hull(pts2)
            if len(pts) >= 3:
                dr.polygon(pts, fill=rgba)
                di.polygon(pts, fill=pid)
                if part.emissive:
                    de.polygon(pts, fill=255)
            if k == "hull" and part.extra and "belt" in part.extra:
                pv = project(part.extra["pelvis"], ox, oy)
                cv = project(part.extra["chest"], ox, oy)
                b = part.extra["belt"]
                dr.line([(pv[0] - rig.torso_w * 0.42, pv[1] - 1.5 * rig.scale), (pv[0] + rig.torso_w * 0.42, pv[1] - 1.5 * rig.scale)],
                        fill=(b[0], b[1], b[2], 255), width=max(1, int(rig.scale)))
                # Costura/ornamento vertical cria leitura de peitoral sem ruído aleatório.
                accent = part.extra["accent"]
                dr.line([(cv[0], cv[1] + 1.2 * rig.scale), (pv[0], pv[1] - 2.0 * rig.scale)],
                        fill=(accent[0], accent[1], accent[2], 255), width=max(1, int(rig.scale)))
        elif k == "shield":
            (x0, y0), = pts2
            r = part.w
            dr.ellipse([x0 - r * 0.8, y0 - r, x0 + r * 0.8, y0 + r], fill=rgba)
            di.ellipse([x0 - r * 0.8, y0 - r, x0 + r * 0.8, y0 + r], fill=pid)
            rim = part.extra["rim"]
            dr.ellipse([x0 - r * 0.8, y0 - r, x0 + r * 0.8, y0 + r], outline=(rim[0], rim[1], rim[2], 255))
            em = part.extra["emblem"]
            dr.rectangle([x0 - 0.5, y0 - r * 0.6, x0 + 0.5, y0 + r * 0.6], fill=(em[0], em[1], em[2], 255))
            dr.rectangle([x0 - r * 0.45, y0 - 1, x0 + r * 0.45, y0], fill=(em[0], em[1], em[2], 255))
        elif k == "ring":
            (x0, y0), = pts2
            r = part.w
            box = [x0 - r, y0 - r * 0.45, x0 + r, y0 + r * 0.45]
            if part.extra and part.extra.get("teeth"):
                box = [x0 - r, y0 - r, x0 + r, y0 + r]
                dr.ellipse(box, fill=rgba)
                di.ellipse(box, fill=pid)
                for t in range(10):
                    a = t / 10 * math.tau + part.extra.get("spin", 0) * D2R
                    tx, ty = x0 + math.cos(a) * (r + 1), y0 + math.sin(a) * (r + 1)
                    dr.point((tx, ty), fill=rgba)
                dr.ellipse([x0 - r * 0.35, y0 - r * 0.35, x0 + r * 0.35, y0 + r * 0.35], fill=(60, 50, 40, 255))
            else:
                width = max(1, int(rig.scale))
                if part.extra and part.extra.get("broken"):
                    dr.arc(box, 200, 520, fill=rgba, width=width)
                    de.arc(box, 200, 520, fill=255, width=width)
                else:
                    dr.ellipse(box, outline=rgba, width=width)
                    de.ellipse(box, outline=255, width=width)
    arr = np.array(img).astype(np.float32)
    idb = np.array(ids)
    em = np.array(emis) > 0
    arr = shade_parts(arr, idb)
    # contorno escuro
    a = arr[..., 3] > 0
    pad = np.pad(a, 1)
    neigh = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
    edge = neigh & ~a
    oc = C(rig.colors.get("outline", "#120c14")) if rig.colors.get("outline") else (18, 12, 20)
    arr[edge, 0:3] = oc
    arr[edge, 3] = 255
    out = arr.clip(0, 255).astype(np.uint8)
    out[em & a, 3] = EMISSIVE_A
    if rig.translucent:
        # pontilhado: metade dos pixels some (fantasmas)
        yy, xx = np.mgrid[0:H, 0:W]
        holes = ((xx + yy) % 2 == 0) & (out[..., 3] == 255) & ~edge
        out[holes, 3] = 0
    return out


def draw_head_details(dr, de, rig, part, x0, y0, pose):
    """Rosto, cabelo, capuz, elmo, chifres, orelhas, focinho."""
    s = rig.scale
    r = part.w
    fd = part.extra["face_dir"]
    toward = -fd[2]          # 1 = olhando para a câmera (sul)
    side = fd[0]
    P = rig.parts
    hair = P.get("hair")
    if hair:
        hc = C(hair.get("color", "#3a2a20"))
        st = hair.get("style", "short")
        hc4 = (hc[0], hc[1], hc[2], 255)
        if st in ("short", "long", "tied", "spiky"):
            dr.pieslice([x0 - r, y0 - r - 0.6 * s, x0 + r, y0 + r * 0.6], 180, 360, fill=hc4)
            if toward < 0.3:
                dr.ellipse([x0 - r + 0.3, y0 - r + 0.3, x0 + r - 0.3, y0 + r - 0.3], fill=hc4)
            if st == "long":
                dr.rectangle([x0 - r, y0 - 0.5 * s, x0 - r + 1.6 * s, y0 + r + 3 * s], fill=hc4)
                dr.rectangle([x0 + r - 1.6 * s, y0 - 0.5 * s, x0 + r, y0 + r + 3 * s], fill=hc4)
            if st == "spiky":
                for k in (-1, 0, 1):
                    dr.polygon([(x0 + k * r * 0.6 - 1.2 * s, y0 - r * 0.6), (x0 + k * r * 0.6 + 1.2 * s, y0 - r * 0.6),
                                (x0 + k * r * 0.8, y0 - r - 2.2 * s)], fill=hc4)
            if st == "tied" and toward < 0.6:
                dr.ellipse([x0 - side * r - 1.4 * s, y0 - r * 0.2, x0 - side * r + 1.4 * s, y0 + r * 0.6], fill=hc4)
    hood = P.get("hood")
    if hood:
        hcol = C(hood.get("color", "#2a2830"))
        h4 = (hcol[0], hcol[1], hcol[2], 255)
        dr.pieslice([x0 - r - 1 * s, y0 - r - 1.4 * s, x0 + r + 1 * s, y0 + r + 1.0 * s], 160, 380, fill=h4)
        if hood.get("peak", True):
            dr.polygon([(x0 - r * 0.6, y0 - r - 0.8 * s), (x0 + r * 0.6, y0 - r - 0.8 * s), (x0 - side * 2 * s, y0 - r - 3.5 * s)], fill=h4)
        if toward < 0.25:
            dr.ellipse([x0 - r - 0.5 * s, y0 - r - 0.5 * s, x0 + r + 0.5 * s, y0 + r + 0.5 * s], fill=h4)
    helm = P.get("helmet")
    if helm:
        mc = C(helm.get("color", "#8a8e98"))
        m4 = (mc[0], mc[1], mc[2], 255)
        dr.pieslice([x0 - r - 0.4 * s, y0 - r - 0.6 * s, x0 + r + 0.4 * s, y0 + r + 0.6 * s], 170, 370, fill=m4)
        if helm.get("full"):
            dr.ellipse([x0 - r, y0 - r, x0 + r, y0 + r], fill=m4)
            if toward > 0.2:
                dr.line([(x0 - r * 0.6 + side * r * 0.3, y0 - 0.2 * s), (x0 + r * 0.6 + side * r * 0.3, y0 - 0.2 * s)],
                        fill=(20, 16, 22, 255), width=max(1, int(s)))
        if helm.get("crest"):
            cc = C(helm["crest"])
            dr.rectangle([x0 - 0.6 * s, y0 - r - 3 * s, x0 + 0.6 * s, y0 - r], fill=(cc[0], cc[1], cc[2], 255))
    hat = P.get("hat")
    if hat:
        tc = C(hat.get("color", "#2a2038"))
        t4 = (tc[0], tc[1], tc[2], 255)
        dr.ellipse([x0 - r - 2.5 * s, y0 - r * 0.6 - 1 * s, x0 + r + 2.5 * s, y0 - r * 0.6 + 1 * s], fill=t4)
        dr.polygon([(x0 - r * 0.8, y0 - r * 0.6), (x0 + r * 0.8, y0 - r * 0.6), (x0 + side * 2 * s, y0 - r - 6 * s)], fill=t4)
    for key in ("horns", "ears"):
        hp = P.get(key)
        if hp:
            hcc = C(hp.get("color", "#d8d0c0"))
            h4 = (hcc[0], hcc[1], hcc[2], 255)
            L = hp.get("len", 3.0) * s
            for sgn in (1, -1):
                bx = x0 + sgn * r * 0.6
                dr.polygon([(bx - 0.9 * s, y0 - r * 0.6), (bx + 0.9 * s, y0 - r * 0.6), (bx + sgn * L * 0.4, y0 - r - L)], fill=h4)
    snout = P.get("snout")
    if snout and toward > -0.6:
        sc_ = C(snout.get("color", "#5a4a40"))
        L = snout.get("len", 3.0) * s
        sx = x0 + side * (r * 0.7 + L * 0.5)
        sy = y0 + r * 0.25 + toward * 1.0 * s
        dr.ellipse([sx - L * 0.6, sy - 1.2 * s, sx + L * 0.6, sy + 1.4 * s + part.extra.get("jaw", 0) * 0.05 * s],
                   fill=(sc_[0], sc_[1], sc_[2], 255))
        dr.point((sx + side * L * 0.5, sy - 0.4 * s), fill=(20, 14, 14, 255))
    # olhos
    if toward > -0.15 and not P.get("faceless"):
        ec = rig.eyes
        e4 = (ec[0], ec[1], ec[2], 255)
        ex = x0 + side * r * 0.45
        ey = y0 + (0.2 if not hood else 0.4) * s
        spread = r * 0.42 * max(0.25, toward + 0.3)
        pts = [(ex - spread, ey), (ex + spread, ey)] if toward > 0.35 else [(ex + side * spread * 0.6, ey)]
        for (px, py) in pts:
            dr.rectangle([px - 0.5, py - 0.5, px + 0.4 * s, py + 0.4 * s], fill=e4)
            if rig.eyes_glow:
                de.rectangle([px - 0.5, py - 0.5, px + 0.4 * s, py + 0.4 * s], fill=255)
    mask = P.get("mask")
    if mask and toward > 0.1:
        mc = C(mask.get("color", "#d8d0c8"))
        dr.rectangle([x0 - r * 0.7 + side * r * 0.3, y0 + 0.6 * s, x0 + r * 0.7 + side * r * 0.3, y0 + r * 0.9],
                     fill=(mc[0], mc[1], mc[2], 255))


def convex_hull(pts):
    pts = sorted(set((round(x, 2), round(y, 2)) for x, y in pts))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def shade_parts(arr, idb):
    """Ilumina a borda superior/esquerda e escurece a inferior/direita de cada parte (por id)."""
    rgb = arr[..., :3]
    a = arr[..., 3] > 0
    up = np.roll(idb, 1, 0)
    left = np.roll(idb, 1, 1)
    down = np.roll(idb, -1, 0)
    right = np.roll(idb, -1, 1)
    up2 = np.roll(idb, 2, 0)
    hi = a & (idb > 0) & ((up != idb) | (left != idb))
    lo = a & (idb > 0) & ((down != idb) | (right != idb)) & ~hi
    mid_lo = a & (idb > 0) & (np.roll(idb, -2, 0) != idb) & ~hi & ~lo
    rgb[hi] = rgb[hi] * 1.22 + 10
    rgb[lo] = rgb[lo] * 0.62
    rgb[mid_lo] = rgb[mid_lo] * 0.82
    # leve gradiente vertical (luz de cima)
    h = arr.shape[0]
    grad = np.linspace(1.08, 0.88, h)[:, None, None]
    arr[..., :3] = rgb * grad
    return arr
