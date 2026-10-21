"""Modelo de fase: grade de células com altura, rampas, abismos, líquidos e paredes.

Os mapas são escritos como texto (linhas de caracteres) em JSON. A primeira linha do texto é o
extremo norte (z máximo). Cada caractere é traduzido pela legenda do tema e pela legenda da fase.
Marcadores (letras definidas em "markers") viram entidades e recebem o piso padrão por baixo.
"""
import math

from ...core.data import DB

STEP_HEIGHT = 0.42      # degrau máximo vencido andando
VOID_DEPTH = -6.0


class Cell:
    __slots__ = ("kind", "height", "h0", "h1", "top_tex", "wall_tex", "trim_tex", "void", "solid", "liquid",
                 "emissive", "wall_emissive", "occluder_extra", "render", "deco", "slow", "damage", "element", "ch")

    def __init__(self, spec, ch="."):
        self.ch = ch
        self.kind = spec.get("t", "floor")
        self.height = float(spec.get("h", 0.0))
        self.h0 = float(spec.get("h0", self.height))      # rampas: altura na borda sul
        self.h1 = float(spec.get("h1", self.height))      # rampas: altura na borda norte
        if self.kind == "ramp":
            self.height = max(self.h0, self.h1)
        self.top_tex = spec.get("top", "cobble")
        self.wall_tex = spec.get("wall", "castle_wall")
        self.trim_tex = spec.get("trim")
        self.void = self.kind == "void"
        self.solid = bool(spec.get("solid", False))
        self.liquid = spec.get("liquid")                   # nome do líquido (sangue, lava, ácido...)
        self.emissive = float(spec.get("emissive", 0.0))
        self.wall_emissive = float(spec.get("wall_emissive", 0.0))
        self.occluder_extra = float(spec.get("occ", 0.0))
        self.render = spec.get("render", True)             # False: só o piso (ex.: árvores são sprites)
        self.deco = spec.get("deco")                       # sprite de decoração em cima da célula
        self.slow = float(spec.get("slow", 0.0))
        self.damage = float(spec.get("damage", 0.0))
        self.element = spec.get("element")
        if self.void:
            self.height = VOID_DEPTH

    def height_at(self, fz):
        """Altura dentro da célula (fz = fração 0..1 de sul para norte)."""
        if self.kind == "ramp":
            return self.h0 + (self.h1 - self.h0) * fz
        return self.height


class Level:
    def __init__(self, data):
        self.data = data
        self.id = data["id"]
        self.name = data.get("name", self.id)
        self.act = data.get("act", 0)
        self.theme = data.get("theme", "act1")
        self.env = data.get("env", self.theme)
        self.music = data.get("music")
        rows = data["rows"]
        self.depth = len(rows)
        self.width = max(len(r) for r in rows)
        theme = DB.themes[self.theme]
        legend = dict(theme["legend"])
        legend.update(data.get("legend", {}))
        markers = data.get("markers", {})
        default_floor = legend[data.get("marker_floor", theme.get("marker_floor", "."))]
        self.cells = [[None] * self.width for _ in range(self.depth)]
        self.entities = []
        self.min_height = 0.0
        for r, row in enumerate(rows):
            z = self.depth - 1 - r
            for x in range(self.width):
                ch = row[x] if x < len(row) else " "
                if ch == " ":
                    continue
                if ch in markers:
                    m = dict(markers[ch])
                    floor_ch = m.pop("floor", None)
                    spec = legend[floor_ch] if floor_ch else default_floor
                    self.cells[z][x] = Cell(spec, floor_ch or ".")
                    m.setdefault("x", x + 0.5)
                    m.setdefault("z", z + 0.5)
                    m["_cell"] = (x, z)
                    self.entities.append(m)
                    continue
                if ch not in legend:
                    raise KeyError(f"{self.id}: caractere '{ch}' sem legenda (linha {r}, coluna {x})")
                self.cells[z][x] = Cell(legend[ch], ch)
        for e in data.get("entities", []):
            self.entities.append(dict(e))
        for zrow in self.cells:
            for c in zrow:
                if c is not None and not c.void:
                    self.min_height = min(self.min_height, c.height)
        self.regions = data.get("regions", [])
        self.camera_bounds = data.get("camera_bounds")      # [x0, z0, x1, z1] opcional

    # ------------------------------------------------------------------ consultas
    def cell(self, x, z):
        if 0 <= x < self.width and 0 <= z < self.depth:
            return self.cells[z][x]
        return None

    def cell_at(self, x, z):
        return self.cell(int(math.floor(x)), int(math.floor(z)))

    def ground_at(self, x, z):
        """Altura do chão no ponto (None = fora do mapa/abismo)."""
        c = self.cell_at(x, z)
        if c is None or c.void:
            return None
        if c.solid:
            return c.height + c.occluder_extra
        return c.height_at(z - math.floor(z))

    def blocks(self, x, z, y, step=STEP_HEIGHT):
        """A célula bloqueia a passagem de quem está na altura y?"""
        c = self.cell(x, z)
        if c is None:
            return True
        if c.void:
            return False
        if c.solid:
            return True
        if c.kind == "ramp":
            return min(c.h0, c.h1) > y + step + 1.0
        return c.height > y + step

    def is_hazard(self, x, z):
        c = self.cell_at(x, z)
        return c is None or c.void or (c.liquid is not None and c.damage > 0)

    def collide_circle(self, x, z, r, y, step=STEP_HEIGHT):
        """Empurra um círculo para fora das células bloqueantes. Devolve (x, z, bateu)."""
        hit = False
        for _ in range(2):
            cx0, cx1 = int(math.floor(x - r)), int(math.floor(x + r))
            cz0, cz1 = int(math.floor(z - r)), int(math.floor(z + r))
            for cz in range(cz0, cz1 + 1):
                for cx in range(cx0, cx1 + 1):
                    if not self.blocks(cx, cz, y, step):
                        continue
                    # ponto mais próximo do quadrado da célula
                    px = min(max(x, cx), cx + 1)
                    pz = min(max(z, cz), cz + 1)
                    dx, dz = x - px, z - pz
                    d2 = dx * dx + dz * dz
                    if d2 >= r * r:
                        continue
                    hit = True
                    if d2 > 1e-10:
                        d = math.sqrt(d2)
                        push = (r - d)
                        x += dx / d * push
                        z += dz / d * push
                    else:
                        # centro dentro da célula: sai pelo lado mais próximo
                        opts = ((x - cx, -1, 0), (cx + 1 - x, 1, 0), (z - cz, 0, -1), (cz + 1 - z, 0, 1))
                        dmin, sx, sz = min(opts, key=lambda o: o[0])
                        x += sx * (dmin + r)
                        z += sz * (dmin + r)
        return x, z, hit

    def line_clear(self, ax, az, bx, bz, y=0.8):
        """Linha de visão no plano, a uma altura y (paredes mais altas bloqueiam)."""
        d = math.hypot(bx - ax, bz - az)
        steps = max(2, int(d * 3))
        for i in range(1, steps):
            t = i / steps
            x = ax + (bx - ax) * t
            z = az + (bz - az) * t
            c = self.cell_at(x, z)
            if c is None:
                return False
            if c.solid or (not c.void and c.height > y + 0.2):
                return False
        return True

    def walkable(self, x, z):
        c = self.cell(x, z)
        return c is not None and not c.void and not c.solid and c.damage <= 0

    def find_entities(self, type_):
        return [e for e in self.entities if e.get("type") == type_]

    def region_at(self, x, z):
        for r in self.regions:
            x0, z0, x1, z1 = r["rect"]
            if x0 <= x <= x1 and z0 <= z <= z1:
                return r
        return None
