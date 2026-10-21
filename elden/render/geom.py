"""Construção rápida de geometria Panda3D a partir de arrays numpy.

Todo o cenário é montado em poucos GeomNodes grandes (um por pedaço do mapa),
o que mantém o número de draw calls baixo mesmo em fases grandes.
"""
import numpy as np
from panda3d.core import (Geom, GeomNode, GeomTriangles, GeomVertexArrayFormat, GeomVertexData,
                          GeomVertexFormat, InternalName, NodePath, OmniBoundingVolume)

_FORMAT = None


def vertex_format():
    """vertex(3) normal(3) texcoord(2) color(4): cor.rgb = tinta/oclusão, cor.a = emissivo."""
    global _FORMAT
    if _FORMAT is None:
        arr = GeomVertexArrayFormat()
        arr.add_column(InternalName.get_vertex(), 3, Geom.NT_float32, Geom.C_point)
        arr.add_column(InternalName.get_normal(), 3, Geom.NT_float32, Geom.C_normal)
        arr.add_column(InternalName.get_texcoord(), 2, Geom.NT_float32, Geom.C_texcoord)
        arr.add_column(InternalName.get_color(), 4, Geom.NT_float32, Geom.C_color)
        _FORMAT = GeomVertexFormat.register_format(GeomVertexFormat(arr))
    return _FORMAT


class MeshBuilder:
    """Acumula quads/triângulos e gera um GeomNode de uma vez."""

    def __init__(self):
        self.v = []      # listas de arrays (n, 12)
        self.i = []
        self.count = 0

    def quad(self, p0, p1, p2, p3, normal, uv0, uv1, color=(1, 1, 1, 0), colors=None):
        """p0..p3 em sentido anti-horário visto de fora. uv0/uv1 = canto inferior esquerdo / superior direito."""
        n = normal
        (u0, v0), (u1, v1) = uv0, uv1
        cs = colors or (color, color, color, color)
        rows = np.array([
            [*p0, *n, u0, v0, *cs[0]],
            [*p1, *n, u1, v0, *cs[1]],
            [*p2, *n, u1, v1, *cs[2]],
            [*p3, *n, u0, v1, *cs[3]],
        ], dtype=np.float32)
        b = self.count
        self.v.append(rows)
        self.i.append(np.array([b, b + 1, b + 2, b, b + 2, b + 3], dtype=np.uint32))
        self.count += 4

    def extend(self, verts, idx):
        verts = np.asarray(verts, dtype=np.float32)
        self.v.append(verts)
        self.i.append(np.asarray(idx, dtype=np.uint32) + self.count)
        self.count += len(verts)

    def empty(self):
        return self.count == 0

    def build(self, name="mesh", omni=True):
        node = GeomNode(name)
        if self.count:
            verts = np.concatenate(self.v).astype(np.float32)
            idx = np.concatenate(self.i).astype(np.uint32)
            node.add_geom(make_geom(verts, idx))
        if omni:
            node.set_bounds(OmniBoundingVolume())
            node.set_final(True)
        return NodePath(node)


def make_geom(verts, idx):
    vdata = GeomVertexData("v", vertex_format(), Geom.UH_static)
    vdata.unclean_set_num_rows(len(verts))
    view = memoryview(vdata.modify_array(0)).cast("B")
    view[:] = verts.tobytes()
    tris = GeomTriangles(Geom.UH_static)
    tris.set_index_type(Geom.NT_uint32)
    iarr = tris.modify_vertices()
    iarr.unclean_set_num_rows(len(idx))
    memoryview(iarr).cast("B")[:] = idx.tobytes()
    geom = Geom(vdata)
    geom.add_primitive(tris)
    return geom


def card(width, height, anchor=(0.5, 0.0), name="card", uv=(0, 0, 1, 1)):
    """Retângulo vertical (plano XY, virado para -Z) usado por sprites."""
    ax, ay = anchor
    x0, x1 = -width * ax, width * (1 - ax)
    y0, y1 = -height * ay, height * (1 - ay)
    mb = MeshBuilder()
    mb.quad((x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0), (0, 0, -1), (uv[0], uv[1]), (uv[2], uv[3]))
    return mb.build(name)


def fullscreen_quad(name="fsq"):
    mb = MeshBuilder()
    mb.quad((-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0), (0, 0, 1), (0, 0), (1, 1))
    return mb.build(name)
