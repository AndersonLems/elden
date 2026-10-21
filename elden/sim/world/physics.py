"""Física simplificada: locomoção, empurrões, gravidade, degraus, rampas, abismos e plataformas móveis."""
import math

from ..entity import GRAVITY
from .level import STEP_HEIGHT

KNOCKBACK_FRICTION = 9.0


class Physics:
    def __init__(self, world):
        self.world = world

    def ground_under(self, actor, x, z, y):
        """Maior chão sob (x, z) que não esteja acima dos pés + degrau (inclui plataformas móveis)."""
        g = self.world.level.ground_at(x, z)
        for p in self.world.platforms:
            top = p.top_at(x, z, actor.radius * 0.6)
            if top is not None and top <= y + STEP_HEIGHT + 0.05 and (g is None or top > g):
                g = top
        return g

    def step(self, a, dt):
        w = self.world
        lvl = w.level
        # empurrão decai exponencialmente
        decay = math.exp(-KNOCKBACK_FRICTION * dt)
        a.kx *= decay
        a.kz *= decay
        slow = 1.0
        cell = lvl.cell_at(a.x, a.z)
        if cell is not None and cell.slow and a.grounded and not getattr(a, "flying", False):
            slow = 1.0 - cell.slow
        vx = a.move_x * slow + a.kx
        vz = a.move_z * slow + a.kz
        # plataforma móvel carrega quem está em cima
        carrier = getattr(a, "standing_on", None)
        if carrier is not None and a.grounded:
            vx += carrier.vx
            vz += carrier.vz
        nx = a.x + vx * dt
        nz = a.z + vz * dt
        flying = getattr(a, "flying", False)
        step = STEP_HEIGHT if not flying else 99.0
        if not getattr(a, "noclip", False):
            nx, nz, hit_wall = lvl.collide_circle(nx, nz, a.radius, a.y, step)
            a.hit_wall = hit_wall
            rr = a.radius + 0.1
            for c in w.solids:
                hx, hz = c.half
                if abs(c.x - nx) > hx + rr or abs(c.z - nz) > hz + rr:
                    continue
                if c is not a and c.solid and c.alive:
                    nx, nz = c.push_circle(nx, nz, a.radius, a.y)
            # IA não entra em abismos/líquidos perigosos por conta própria
            if getattr(a, "avoid_hazards", False) and a.grounded:
                if lvl.is_hazard(nx, nz) and not lvl.is_hazard(a.x, a.z):
                    nx, nz = a.x, a.z
        a.x, a.z = nx, nz
        if flying:
            return
        # vertical
        g = self.ground_under(a, a.x, a.z, a.y)
        gs = a.gravity_scale_override if a.gravity_scale_override is not None else a.gravity_scale
        if a.grounded:
            if g is None or g < a.y - STEP_HEIGHT:
                a.grounded = False
                a.standing_on = None
            else:
                a.y = g
                a.vy = 0.0
                a.standing_on = self._platform_at(a)
        if not a.grounded:
            a.vy -= GRAVITY * gs * dt
            a.vy = max(a.vy, -28.0)
            a.y += a.vy * dt
            a.air_time += dt
            if g is not None and a.y <= g and a.vy <= 0:
                fall = -a.vy
                a.y = g
                a.vy = 0.0
                a.grounded = True
                a.air_time = 0.0
                a.standing_on = self._platform_at(a)
                a.on_land(fall)
        # perigos do chão
        if a.grounded and cell is not None and cell.damage > 0 and not a.dead and not getattr(a, "hazard_immune", False):
            a.on_ground_hazard += dt
            if a.on_ground_hazard >= 0.4:
                a.on_ground_hazard = 0.0
                w.hazard_damage(a, cell)
        else:
            a.on_ground_hazard = 0.0
        # caiu no abismo
        if a.y < lvl.min_height - 4.0 and not a.dead:
            a.on_fall_void()
        # posição segura para reaparecer
        if a.grounded and not a.dead and cell is not None and cell.damage <= 0 and not cell.void:
            if all(lvl.ground_at(a.x + ox, a.z + oz) is not None for ox, oz in ((0.6, 0), (-0.6, 0), (0, 0.6), (0, -0.6))):
                a.last_safe = (a.x, a.y, a.z)

    def _platform_at(self, a):
        for p in self.world.platforms:
            top = p.top_at(a.x, a.z, a.radius * 0.6)
            if top is not None and abs(top - a.y) < 0.05:
                return p
        return None

    def separate(self, actors):
        """Afasta atores sobrepostos (exceto quem atravessa: esquiva, fantasmas)."""
        n = len(actors)
        for i in range(n):
            a = actors[i]
            if a.dead or getattr(a, "flying", False):
                continue
            ga = a.action is not None and a.action.ghost
            for j in range(i + 1, n):
                b = actors[j]
                if b.dead or getattr(b, "flying", False):
                    continue
                if ga or (b.action is not None and b.action.ghost):
                    continue
                if abs(a.y - b.y) > 1.2:
                    continue
                dx, dz = b.x - a.x, b.z - a.z
                d = math.hypot(dx, dz)
                m = a.radius + b.radius
                if 1e-5 < d < m:
                    push = (m - d)
                    wa = b.weight / (a.weight + b.weight)
                    nx, nz = dx / d, dz / d
                    a.x -= nx * push * wa
                    a.z -= nz * push * wa
                    b.x += nx * push * (1 - wa)
                    b.z += nz * push * (1 - wa)
