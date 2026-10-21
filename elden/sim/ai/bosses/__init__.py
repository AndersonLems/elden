"""Registro dos chefes (bosses.json -> 'class')."""
from .base import Boss, BossPart
from .varkhan import Varkhan
from .condessa import Condessa
from .serafim import Serafim
from .santo import Santo
from .malachar import Malachar
from .aurelion import Aurelion

BOSS_CLASSES = {
    "boss": Boss,
    "varkhan": Varkhan,
    "condessa": Condessa,
    "serafim": Serafim,
    "santo": Santo,
    "malachar": Malachar,
    "aurelion": Aurelion,
}
