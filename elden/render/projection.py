"""Matemática da câmera semi-isométrica, compartilhada por renderização e testes.

A simulação continua no plano X/Z. Esta camada transforma apenas apresentação e
entrada, evitando que câmera, hitboxes e alcance de golpes divirjam.
"""
import math


AZIMUTH = math.radians(45.0)
ELEVATION = math.radians(38.0)
RIGHT_X = math.cos(AZIMUTH)
RIGHT_Z = -math.sin(AZIMUTH)
FORWARD_X = math.sin(AZIMUTH) * math.sin(ELEVATION)
FORWARD_Z = math.cos(AZIMUTH) * math.sin(ELEVATION)
VERTICAL_Y = math.cos(ELEVATION)
DEPTH_X = math.sin(AZIMUTH) * math.cos(ELEVATION)
DEPTH_Z = math.cos(AZIMUTH) * math.cos(ELEVATION)
DEPTH_Y = -math.sin(ELEVATION)


def project_relative(x, y, z):
    """Projeta um deslocamento do mundo em (horizontal, vertical, profundidade)."""
    return (x * RIGHT_X + z * RIGHT_Z,
            x * FORWARD_X + z * FORWARD_Z + y * VERTICAL_Y,
            x * DEPTH_X + z * DEPTH_Z + y * DEPTH_Y)


def screen_move_to_world(right, up):
    """Converte WASD/analógico orientado à tela para o plano navegável X/Z."""
    x = right * RIGHT_X + up * math.sin(AZIMUTH)
    z = right * RIGHT_Z + up * math.cos(AZIMUTH)
    length = math.hypot(x, z)
    if length > 1.0:
        x, z = x / length, z / length
    return x, z
