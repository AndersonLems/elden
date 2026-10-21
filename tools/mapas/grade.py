"""Grade de edição para desenhar mapas com retângulos/linhas e marcadores (r = linha do texto, 0 = norte)."""


class Grade:
    def __init__(self, w, d, fill="."):
        self.w, self.d = w, d
        self.g = [[fill] * w for _ in range(d)]
        self.markers = {}
        self.entities = []

    def put(self, x, r, ch):
        if 0 <= x < self.w and 0 <= r < self.d:
            self.g[r][x] = ch

    def rect(self, x0, r0, x1, r1, ch):
        for r in range(r0, r1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, r, ch)

    def frame(self, x0, r0, x1, r1, ch):
        for x in range(x0, x1 + 1):
            self.put(x, r0, ch)
            self.put(x, r1, ch)
        for r in range(r0, r1 + 1):
            self.put(x0, r, ch)
            self.put(x1, r, ch)

    def border(self, ch="#", north="H"):
        self.frame(0, 0, self.w - 1, self.d - 1, ch)
        for x in range(self.w):
            self.put(x, 0, north)

    def text(self, x, r, s):
        for i, c in enumerate(s):
            self.put(x + i, r, c)

    def get(self, x, r):
        return self.g[r][x]

    def pos(self, x, r):
        """Centro da célula em coordenadas de mundo."""
        return x + 0.5, self.d - 1 - r + 0.5

    def ent(self, x, r, **spec):
        """Entidade em coordenadas de grade (convertidas para mundo)."""
        wx, wz = self.pos(x, r)
        spec.setdefault("x", wx)
        spec.setdefault("z", wz)
        self.entities.append(spec)
        return spec

    def rows(self):
        return ["".join(row) for row in self.g]

    def rect_world(self, x0, r0, x1, r1):
        """Retângulo [x0, z0, x1, z1] em coordenadas de mundo a partir de células da grade."""
        ax, az = x0, self.d - 1 - r1
        bx, bz = x1 + 1, self.d - r0
        return [ax, az, bx, bz]


def carve(g, pts, ch, radius=1):
    """Abre um caminho (polilinha de pontos x, r) com largura 2*radius+1."""
    for (x0, r0), (x1, r1) in zip(pts, pts[1:]):
        n = max(abs(x1 - x0), abs(r1 - r0), 1)
        for i in range(n + 1):
            x = round(x0 + (x1 - x0) * i / n)
            r = round(r0 + (r1 - r0) * i / n)
            for dx in range(-radius, radius + 1):
                for dr in range(-radius, radius + 1):
                    g.put(x + dx, r + dr, ch)


def scatter(g, chars, density, x0, r0, x1, r1, keep=".,:;_-=", seed=1, avoid=None):
    """Espalha decorações sólidas (árvores, lápides) sobre pisos livres, sem bloquear caminhos protegidos."""
    import random
    rng = random.Random(seed)
    avoid = avoid or set()
    for r in range(r0, r1 + 1):
        for x in range(x0, x1 + 1):
            if (x, r) in avoid or g.get(x, r) not in keep:
                continue
            if rng.random() < density:
                g.put(x, r, rng.choice(chars))


def protect(pts, radius=1):
    """Conjunto de células protegidas ao longo de um caminho."""
    out = set()
    for (x0, r0), (x1, r1) in zip(pts, pts[1:]):
        n = max(abs(x1 - x0), abs(r1 - r0), 1)
        for i in range(n + 1):
            x = round(x0 + (x1 - x0) * i / n)
            r = round(r0 + (r1 - r0) * i / n)
            for dx in range(-radius, radius + 1):
                for dr in range(-radius, radius + 1):
                    out.add((x + dx, r + dr))
    return out
