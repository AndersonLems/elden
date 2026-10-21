"""Estatísticas com modificadores empilháveis por fonte (classe, árvore de Graça, arma, runas, bônus)."""

ELEMENTS = ("fisico", "fogo", "gelo", "raio", "arcano", "trevas", "sagrado", "sangue")

ATTRIBUTES = ("vigor", "mente", "forca", "destreza", "intelecto", "fe")
ATTRIBUTE_NAMES = {
    "vigor": "Vigor", "mente": "Mente", "forca": "Força",
    "destreza": "Destreza", "intelecto": "Intelecto", "fe": "Fé",
}

# Chaves conhecidas de modificadores (somadas). As terminadas em _mult são percentuais (0.1 = +10%).
MOD_DEFAULTS = {
    "hp_max": 0.0, "fp_max": 0.0, "posture_max": 0.0,
    "atk_mult": 0.0, "light_mult": 0.0, "heavy_mult": 0.0, "air_mult": 0.0, "skill_mult": 0.0,
    "art_mult": 0.0, "magic_mult": 0.0, "holy_mult": 0.0, "ruin_mult": 0.0, "execution_mult": 0.0,
    "finisher_mult": 0.0, "ranged_mult": 0.0, "counter_mult": 0.0, "beast_mult": 0.0,
    "crit_chance": 0.0, "crit_mult": 0.0, "backstab_mult": 0.0,
    "vs_bleeding_mult": 0.0, "vs_broken_mult": 0.0, "vs_low_hp_mult": 0.0, "vs_undead_mult": 0.0,
    "posture_dmg_mult": 0.0, "status_mult": 0.0, "bleed_add": 0.0, "burn_add": 0.0, "frost_add": 0.0,
    "shock_add": 0.0, "curse_add": 0.0,
    "def_flat": 0.0, "dmg_taken_mult": 0.0, "posture_taken_mult": 0.0, "block_reduction": 0.0,
    "parry_window": 0.0, "speed_mult": 0.0, "attack_speed": 0.0, "dodge_iframes": 0.0, "dodge_charges": 0.0,
    "dodge_distance": 0.0, "lifesteal": 0.0, "fp_regen": 0.0, "hp_regen": 0.0, "fervor_gain": 0.0,
    "heal_mult": 0.0, "cooldown_mult": 0.0, "flask_heal": 0.0, "fp_cost_mult": 0.0, "grace_gain": 0.0,
    "jump_mult": 0.0, "poise": 0.0, "fp_on_hit": 0.0, "steal_chance": 0.0,
}
for _e in ELEMENTS:
    MOD_DEFAULTS["res_" + _e] = 0.0
    MOD_DEFAULTS["elem_" + _e] = 0.0


class Stats:
    """Base + modificadores por fonte. get(k) soma tudo."""

    def __init__(self, base=None):
        self.base = dict(base or {})
        self.sources = {}
        self._cache = None

    def set_source(self, name, mods):
        if mods:
            self.sources[name] = dict(mods)
        else:
            self.sources.pop(name, None)
        self._cache = None

    def remove_source(self, name):
        if name in self.sources:
            del self.sources[name]
            self._cache = None

    def _rebuild(self):
        c = dict(MOD_DEFAULTS)
        for k, v in self.base.items():
            c[k] = c.get(k, 0.0) + v
        for mods in self.sources.values():
            for k, v in mods.items():
                c[k] = c.get(k, 0.0) + v
        self._cache = c

    def get(self, key, default=0.0):
        if self._cache is None:
            self._rebuild()
        return self._cache.get(key, default)

    def __getitem__(self, key):
        return self.get(key)


def merge_mods(*mod_dicts):
    out = {}
    for d in mod_dicts:
        for k, v in (d or {}).items():
            out[k] = out.get(k, 0.0) + v
    return out
