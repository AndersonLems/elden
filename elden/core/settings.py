"""Configurações do jogo (qualidade gráfica, áudio, acessibilidade) salvas em JSON."""
import json
import os

from .paths import user_dir

QUALITY = {
    "baixa": dict(internal_height=200, point_shadow_steps=0, dir_shadow_steps=0, max_lights=6, bloom=0.0, grain=0.0, ao=0.0),
    "media": dict(internal_height=240, point_shadow_steps=6, dir_shadow_steps=6, max_lights=10, bloom=0.65, grain=1.0, ao=0.65),
    "alta": dict(internal_height=240, point_shadow_steps=12, dir_shadow_steps=10, max_lights=16, bloom=0.9, grain=1.0, ao=0.85),
    "ultra": dict(internal_height=270, point_shadow_steps=20, dir_shadow_steps=16, max_lights=16, bloom=1.05, grain=1.0, ao=1.0),
}
QUALITY_NAMES = {"baixa": "Baixa", "media": "Média", "alta": "Alta", "ultra": "Ultra"}

DEFAULTS = {
    "quality": "alta", "fullscreen": False, "window": [1280, 720], "master": 0.8, "music": 0.55, "sfx": 0.8,
    "shake": 1.0, "damage_numbers": True, "show_fps": False, "hitboxes": False, "vsync": True,
}


class Quality:
    def __init__(self, name):
        self.set(name)

    def set(self, name):
        self.name = name if name in QUALITY else "alta"
        for k, v in QUALITY[self.name].items():
            setattr(self, k, v)


class Settings(dict):
    path = None

    @classmethod
    def load(cls):
        s = cls(DEFAULTS)
        cls.path = os.path.join(user_dir(), "config.json")
        try:
            with open(cls.path, encoding="utf-8") as f:
                s.update(json.load(f))
        except (OSError, ValueError):
            pass
        return s

    def save(self):
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(dict(self), f, indent=1)
            os.replace(tmp, self.path)
        except OSError:
            pass
