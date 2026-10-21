"""Ponte mínima entre simulação e apresentação: luzes são dados simples que a renderização lê."""
from .render.lights import PointLight


def make_light(pos, color, intensity, radius, flicker=0.0, shadows=True, pulse=0.0):
    return PointLight(pos, color, intensity, radius, flicker=flicker, shadows=shadows, pulse=pulse)
