"""Navegação em grade (A*) com cache por fase. Considera alturas (degraus) e evita abismos e perigos."""
import heapq
import math

from ..world.level import STEP_HEIGHT

DIRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
        (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]


class NavGrid:
    def __init__(self, level):
        self.level = level
        self.w, self.d = level.width, level.depth
        self.ok = [[False] * self.w for _ in range(self.d)]
        self.h = [[0.0] * self.w for _ in range(self.d)]
        self.ramp = [[False] * self.w for _ in range(self.d)]
        for z in range(self.d):
            for x in range(self.w):
                c = level.cell(x, z)
                if c is None or c.void or c.solid or c.damage > 0:
                    continue
                self.ok[z][x] = True
                self.h[z][x] = c.height
                self.ramp[z][x] = c.kind == "ramp"
        self.blocked_dynamic = set()
        # vizinhos transitáveis pré-calculados (A* muito mais rápido)
        self.nbrs = {}
        for z in range(self.d):
            for x in range(self.w):
                if not self.ok[z][x]:
                    continue
                out = []
                for dx, dz, cost in DIRS:
                    nx, nz = x + dx, z + dz
                    if not self._pass(x, z, nx, nz):
                        continue
                    if dx and dz and (not self._pass(x, z, x + dx, z) or not self._pass(x, z, x, z + dz)):
                        continue
                    out.append((nx, nz, cost))
                self.nbrs[(x, z)] = out

    def _pass(self, ax, az, bx, bz):
        if not (0 <= bx < self.w and 0 <= bz < self.d) or not (0 <= ax < self.w and 0 <= az < self.d):
            return False
        if not self.ok[bz][bx]:
            return False
        ha, hb = self.h[az][ax], self.h[bz][bx]
        if self.ramp[az][ax] or self.ramp[bz][bx]:
            return abs(hb - ha) <= 1.05
        return abs(hb - ha) <= STEP_HEIGHT

    def passable(self, ax, az, bx, bz):
        return self._pass(ax, az, bx, bz) and (bx, bz) not in self.blocked_dynamic

    def find(self, sx, sz, tx, tz, max_nodes=900):
        sx, sz, tx, tz = int(sx), int(sz), int(tx), int(tz)
        if not (0 <= tx < self.w and 0 <= tz < self.d):
            return None
        if (sx, sz) == (tx, tz):
            return [(tx + 0.5, tz + 0.5)]
        openq = [(0.0, 0.0, sx, sz)]
        came = {(sx, sz): None}
        g = {(sx, sz): 0.0}
        n = 0
        best = (1e9, (sx, sz))
        while openq and n < max_nodes:
            _, gc, x, z = heapq.heappop(openq)
            n += 1
            hd = math.hypot(tx - x, tz - z)
            if hd < best[0]:
                best = (hd, (x, z))
            if (x, z) == (tx, tz):
                break
            for nx, nz, cost in self.nbrs.get((x, z), ()):
                ng = gc + cost
                if ng < g.get((nx, nz), 1e18):
                    g[(nx, nz)] = ng
                    came[(nx, nz)] = (x, z)
                    heapq.heappush(openq, (ng + math.hypot(tx - nx, tz - nz), ng, nx, nz))
        end = (tx, tz) if (tx, tz) in came else best[1]
        path = []
        cur = end
        while cur is not None:
            path.append((cur[0] + 0.5, cur[1] + 0.5))
            cur = came[cur]
        path.reverse()
        return self.smooth(path)

    def smooth(self, path):
        if len(path) <= 2:
            return path
        out = [path[0]]
        i = 0
        while i < len(path) - 1:
            j = len(path) - 1
            while j > i + 1 and not self.straight(path[i], path[j]):
                j -= 1
            out.append(path[j])
            i = j
        return out

    def straight(self, a, b):
        ax, az = a
        bx, bz = b
        d = math.hypot(bx - ax, bz - az)
        steps = max(2, int(d * 3))
        px, pz = int(ax), int(az)
        for i in range(1, steps + 1):
            t = i / steps
            x, z = int(ax + (bx - ax) * t), int(az + (bz - az) * t)
            if (x, z) != (px, pz):
                if not self.passable(px, pz, x, z):
                    return False
                px, pz = x, z
        return True


_cache = []


def nav_for(level):
    # compara o próprio objeto: id() pode ser reaproveitado por uma fase nova depois que a antiga é coletada
    if not _cache or _cache[0] is not level:
        _cache[:] = [level, NavGrid(level)]
    return _cache[1]
