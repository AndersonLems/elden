"""Constrói os módulos arquitetônicos do vertical slice gótico.

Os BAM resultantes são assets versionados e reutilizáveis. O script fica no
repositório para permitir ajustes de proporção sem depender do Blender.
"""
import math
import os
import sys

from panda3d.core import Filename

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, ROOT)

from elden.render.geom import MeshBuilder


OUT = os.path.join(ROOT, "assets", "models", "ato1")
FLOOR = ((0.01, 0.51), (0.49, 0.99))
WALL = ((0.51, 0.51), (0.99, 0.99))
MOSS = ((0.01, 0.01), (0.49, 0.49))
ORNATE = ((0.51, 0.01), (0.99, 0.49))


def box(mb, x0, y0, z0, x1, y1, z1, uv=WALL, color=(1, 1, 1, 0)):
    a, b = uv
    mb.quad((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (0, 0, -1), a, b, color)
    mb.quad((x1, y0, z1), (x0, y0, z1), (x0, y1, z1), (x1, y1, z1), (0, 0, 1), a, b, color)
    mb.quad((x0, y0, z1), (x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (-1, 0, 0), a, b, color)
    mb.quad((x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0), (1, 0, 0), a, b, color)
    mb.quad((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1), (0, 1, 0), a, b, color)
    mb.quad((x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0), (0, -1, 0), a, b, color)


def prism(mb, cx, y0, cz, radius, height, sides=8, uv=WALL, taper=1.0):
    a, b = uv
    for i in range(sides):
        q0 = i / sides * math.tau
        q1 = (i + 1) / sides * math.tau
        x0, z0 = cx + math.cos(q0) * radius, cz + math.sin(q0) * radius
        x1, z1 = cx + math.cos(q1) * radius, cz + math.sin(q1) * radius
        tx0, tz0 = cx + math.cos(q0) * radius * taper, cz + math.sin(q0) * radius * taper
        tx1, tz1 = cx + math.cos(q1) * radius * taper, cz + math.sin(q1) * radius * taper
        nx, nz = math.cos((q0 + q1) * 0.5), math.sin((q0 + q1) * 0.5)
        mb.quad((x0, y0, z0), (x1, y0, z1), (tx1, y0 + height, tz1), (tx0, y0 + height, tz0),
                (nx, 0, nz), a, b)


def column():
    mb = MeshBuilder()
    prism(mb, 0, 0, 0, 0.72, 0.28, uv=MOSS, taper=0.9)
    prism(mb, 0, 0.28, 0, 0.58, 0.22, uv=ORNATE, taper=0.82)
    prism(mb, 0, 0.5, 0, 0.42, 3.2, uv=WALL, taper=0.9)
    for y, r in ((0.65, 0.47), (3.45, 0.48), (3.7, 0.62)):
        prism(mb, 0, y, 0, r, 0.18, uv=ORNATE, taper=1.0)
    prism(mb, 0, 3.88, 0, 0.72, 0.3, uv=ORNATE, taper=0.78)
    # quatro pináculos tornam o capitel reconhecível na escala do jogo.
    for x in (-0.48, 0.48):
        for z in (-0.48, 0.48):
            prism(mb, x, 4.1, z, 0.13, 0.55, sides=6, uv=ORNATE, taper=0.05)
    return mb


def arch(gate=False):
    mb = MeshBuilder()
    # contrafortes, bases e molduras escalonadas
    for x in (-2.15, 1.35):
        box(mb, x, 0, -0.45, x + 0.8, 4.4, 0.45, WALL)
        box(mb, x - 0.15, 0, -0.6, x + 0.95, 0.35, 0.6, MOSS)
        box(mb, x - 0.08, 3.75, -0.58, x + 0.88, 4.05, 0.58, ORNATE)
    # arco ogival em duas sequências de aduelas inclinadas
    for side in (-1, 1):
        for i in range(7):
            t = i / 6
            cx = side * (1.55 - t * 1.38)
            cy = 3.75 + t * 1.55
            w = 0.54 - t * 0.12
            box(mb, cx - w / 2, cy - 0.28, -0.55, cx + w / 2, cy + 0.28, 0.55, ORNATE)
    box(mb, -2.35, 5.08, -0.62, 2.35, 5.45, 0.62, ORNATE)
    if gate:
        # grade de ferro profunda, com lanças e travessas.
        for x in (-1.25, -0.75, -0.25, 0.25, 0.75, 1.25):
            box(mb, x - 0.07, 0.25, -0.08, x + 0.07, 3.85, 0.08, ORNATE, (0.7, 0.72, 0.76, 0))
            prism(mb, x, 3.85, 0, 0.16, 0.55, sides=4, uv=ORNATE, taper=0.0)
        for y in (1.2, 2.6):
            box(mb, -1.55, y, -0.12, 1.55, y + 0.16, 0.12, ORNATE)
    return mb


def statue():
    mb = MeshBuilder()
    box(mb, -0.72, 0, -0.62, 0.72, 0.38, 0.62, MOSS)
    box(mb, -0.56, 0.38, -0.48, 0.56, 1.0, 0.48, ORNATE)
    prism(mb, 0, 1.0, 0, 0.55, 2.25, sides=7, uv=WALL, taper=0.48)
    prism(mb, 0, 3.18, 0, 0.34, 0.62, sides=8, uv=WALL, taper=0.88)
    # halo, espada e asas blocadas mantêm a silhueta em pixel art.
    for i in range(8):
        a = i / 8 * math.tau
        x, y = math.cos(a) * 0.52, 3.55 + math.sin(a) * 0.52
        box(mb, x - 0.09, y - 0.09, 0.12, x + 0.09, y + 0.09, 0.22, ORNATE)
    for side in (-1, 1):
        for i in range(4):
            x0 = side * (0.38 + i * 0.28)
            y0 = 2.85 - i * 0.28
            box(mb, min(x0, x0 + side * 0.48), y0, 0.05, max(x0, x0 + side * 0.48), y0 + 0.22, 0.24, WALL)
    box(mb, -0.06, 0.85, -0.7, 0.06, 3.0, -0.54, ORNATE)
    return mb


def stairs():
    mb = MeshBuilder()
    for i in range(6):
        y = i * 0.28
        z0 = -2.1 + i * 0.55
        box(mb, -2.1, 0, z0, 2.1, y + 0.28, z0 + 0.62, FLOOR if i % 2 else MOSS)
    for x0, x1 in ((-2.45, -2.08), (2.08, 2.45)):
        box(mb, x0, 0, -2.2, x1, 2.15, 1.4, ORNATE)
    return mb


def buttress():
    mb = MeshBuilder()
    box(mb, -0.75, 0, -0.7, 0.75, 0.42, 0.7, MOSS)
    for i in range(5):
        inset = i * 0.1
        box(mb, -0.62 + inset, 0.42 + i * 0.68, -0.58 + inset,
            0.62 - inset, 1.1 + i * 0.68, 0.58 - inset, WALL)
    prism(mb, 0, 3.82, 0, 0.42, 1.0, sides=6, uv=ORNATE, taper=0.0)
    return mb


def dais():
    """Piso cenográfico central: lajes autorais em um único mesh/draw call."""
    mb = MeshBuilder()
    for z in range(-6, 7):
        for x in range(-6, 7):
            if abs(x) + abs(z) > 10:
                continue
            edge = abs(x) + abs(z) >= 9
            center = abs(x) <= 2 and abs(z) <= 2
            uv = ORNATE if center else (MOSS if (x * 7 + z * 11) % 9 == 0 else FLOOR)
            h = 0.1 if center else (0.055 if edge else 0.035)
            gap = 0.055
            box(mb, x + gap, 0, z + gap, x + 1 - gap, h, z + 1 - gap, uv)
    for x in range(-5, 6):
        for z in (-5.15, 5.15):
            box(mb, x + 0.08, 0, z - 0.11, x + 0.92, 0.16, z + 0.11, ORNATE)
    for z in range(-5, 6):
        for x in (-5.15, 5.15):
            box(mb, x - 0.11, 0, z + 0.08, x + 0.11, 0.16, z + 0.92, ORNATE)
    return mb


def save(name, mb):
    os.makedirs(OUT, exist_ok=True)
    node = mb.build(name, omni=False)
    node.flatten_strong()
    path = os.path.join(OUT, name + ".bam")
    if not node.write_bam_file(Filename.from_os_specific(path)):
        raise RuntimeError(f"falha ao gravar {path}")
    print(path)


if __name__ == "__main__":
    save("gothic_column", column())
    save("gothic_arch", arch(False))
    save("gothic_gate", arch(True))
    save("gothic_statue", statue())
    save("gothic_stairs", stairs())
    save("gothic_buttress", buttress())
    save("gothic_dais", dais())
