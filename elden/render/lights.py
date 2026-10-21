"""Luzes pontuais com cintilação (tochas, brasas, magia)."""
import math
import random


class PointLight:
    def __init__(self, pos, color=(1.0, 0.7, 0.4), intensity=1.5, radius=6.0, flicker=0.0, shadows=True,
                 pulse=0.0, pulse_speed=2.0):
        self.pos = list(pos)
        self.color = color
        self.intensity = intensity
        self.radius = radius
        self.flicker = flicker
        self.shadows = shadows
        self.pulse = pulse
        self.pulse_speed = pulse_speed
        self.phase = random.random() * 100
        self.t = 0.0
        self.enabled = True

    def update(self, dt):
        self.t += dt

    def current_color(self):
        k = self.intensity if self.enabled else 0.0
        t = self.t + self.phase
        if self.flicker:
            n = (math.sin(t * 13.1) * 0.5 + math.sin(t * 7.3 + 1.7) * 0.3 + math.sin(t * 23.7) * 0.2)
            k *= 1.0 + n * self.flicker
        if self.pulse:
            k *= 1.0 + math.sin(t * self.pulse_speed) * self.pulse
        c = self.color
        return (c[0] * k, c[1] * k, c[2] * k)
