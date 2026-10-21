"""Formas de acerto relativas ao atacante: arco, círculo, linha (estocada/feixe) e anel (onda de choque)."""
import math

from ...core.mathutil import dir_of


class HitShape:
    def __init__(self, spec, owner_scale=1.0):
        self.shape = spec.get("shape", "arc")
        s = owner_scale
        self.range = spec.get("range", 1.6) * s
        self.angle = math.radians(spec.get("angle", 120))
        self.radius = spec.get("radius", 1.0) * s
        self.offset = spec.get("offset", 0.0) * s
        self.length = spec.get("length", 2.5) * s
        self.width = spec.get("width", 0.8) * s
        self.inner = spec.get("inner", 0.0) * s
        y = spec.get("y", [-0.6, 2.2])
        self.y0, self.y1 = y[0] * s, y[1] * s

    def test(self, ox, oy, oz, facing, target):
        """O alvo (círculo com raio/altura) é atingido por esta forma a partir de (ox, oz) olhando 'facing'?"""
        ty = target.y - oy
        if ty > self.y1 or ty + target.height < self.y0:
            return False
        tr = target.radius
        dx, dz = target.x - ox, target.z - oz
        fx, fz = dir_of(facing)
        if self.shape == "arc":
            d = math.hypot(dx, dz)
            if d > self.range + tr:
                return False
            if d < tr + 0.25:
                return True
            a = math.atan2(dz, dx)
            diff = abs((a - facing + math.pi) % math.tau - math.pi)
            slack = math.atan2(tr, max(d, 0.01))
            return diff <= self.angle * 0.5 + slack
        if self.shape == "circle":
            cx, cz = ox + fx * self.offset, oz + fz * self.offset
            return math.hypot(target.x - cx, target.z - cz) <= self.radius + tr
        if self.shape == "line":
            # retângulo à frente: comprimento ao longo de facing, largura perpendicular
            along = dx * fx + dz * fz
            across = abs(-dx * fz + dz * fx)
            return -tr <= along - self.offset <= self.length + tr and across <= self.width * 0.5 + tr
        if self.shape == "ring":
            d = math.hypot(dx, dz)
            return self.inner - tr <= d <= self.radius + tr
        return False

    def debug(self, ox, oz, facing):
        fx, fz = dir_of(facing)
        if self.shape == "arc":
            return ("arc", ox, oz, self.range, facing, self.angle)
        if self.shape == "circle":
            return ("circle", ox + fx * self.offset, oz + fz * self.offset, self.radius, (1, 0.3, 0.2))
        if self.shape == "line":
            return ("line", ox + fx * self.offset, oz + fz * self.offset, facing, self.length, self.width)
        return ("circle", ox, oz, self.radius, (1, 0.5, 0.2))
