"""Matemática 2D/3D leve (sem dependências) usada pela simulação."""
import math

TAU = math.tau


def clamp(v, a, b):
    return a if v < a else b if v > b else v


def lerp(a, b, t):
    return a + (b - a) * t


def approach(v, target, step):
    if v < target:
        return min(target, v + step)
    return max(target, v - step)


def length(x, z):
    return math.hypot(x, z)


def norm(x, z):
    d = math.hypot(x, z)
    if d < 1e-9:
        return 0.0, 0.0
    return x / d, z / d


def dist2(ax, az, bx, bz):
    return math.hypot(ax - bx, az - bz)


def angle_of(x, z):
    """Ângulo do vetor no plano XZ (0 = +X/leste, pi/2 = +Z/norte)."""
    return math.atan2(z, x)


def dir_of(angle):
    return math.cos(angle), math.sin(angle)


def angle_diff(a, b):
    """Menor diferença assinada b - a em radianos."""
    d = (b - a + math.pi) % TAU - math.pi
    return d


def turn_towards(a, target, max_step):
    d = angle_diff(a, target)
    if abs(d) <= max_step:
        return target
    return a + math.copysign(max_step, d)


def dir8(angle):
    """Índice de 8 direções: 0=leste, 1=nordeste, 2=norte, ... (sentido anti-horário)."""
    return int(round(angle / (TAU / 8))) % 8


def smooth_damp(cur, target, rate, dt):
    return target + (cur - target) * math.exp(-rate * dt)
