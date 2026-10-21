"""Efeitos de status (acúmulo -> estouro) e bônus/penalidades temporários."""

# limiar de acúmulo, duração do efeito, decaimento do acúmulo por segundo
STATUS_DEFS = {
    "sangramento": {"threshold": 100.0, "duration": 6.0, "decay": 8.0, "name": "Sangramento", "color": (0.8, 0.05, 0.1)},
    "queimadura": {"threshold": 100.0, "duration": 4.0, "decay": 10.0, "name": "Queimadura", "color": (1.0, 0.45, 0.1)},
    "congelamento": {"threshold": 100.0, "duration": 3.5, "decay": 10.0, "name": "Congelamento", "color": (0.5, 0.8, 1.0)},
    "choque": {"threshold": 100.0, "duration": 0.9, "decay": 14.0, "name": "Choque", "color": (0.7, 0.75, 1.0)},
    "maldicao": {"threshold": 100.0, "duration": 8.0, "decay": 6.0, "name": "Maldição", "color": (0.45, 0.1, 0.6)},
}

ELEMENT_STATUS = {"fogo": "queimadura", "gelo": "congelamento", "raio": "choque", "trevas": "maldicao",
                  "sangue": "sangramento"}


class Buff:
    __slots__ = ("id", "mods", "time", "tags", "stacks", "max_stacks", "source")

    def __init__(self, id_, mods, time, tags=(), max_stacks=1, source=None):
        self.id = id_
        self.mods = dict(mods)
        self.time = time
        self.tags = set(tags)
        self.stacks = 1
        self.max_stacks = max_stacks
        self.source = source


class StatusSet:
    def __init__(self, owner):
        self.owner = owner
        self.buildup = {k: 0.0 for k in STATUS_DEFS}
        self.active = {}          # nome -> tempo restante
        self.buffs = {}
        self.dot_acc = 0.0

    # ------------------------------------------------------------------ acúmulos
    def add_buildup(self, status, amount):
        """Devolve True se o status estourou agora."""
        if status not in STATUS_DEFS or amount <= 0:
            return False
        o = self.owner
        resist = o.stats.get("res_status_" + status, 0.0) + getattr(o, "status_resist", {}).get(status, 0.0)
        amount *= max(0.0, 1.0 - resist)
        if amount <= 0:
            return False
        d = STATUS_DEFS[status]
        if status in self.active and status != "sangramento":
            # já ativo: renova parcialmente
            self.active[status] = max(self.active[status], d["duration"] * 0.5)
            return False
        self.buildup[status] += amount
        if self.buildup[status] >= d["threshold"]:
            self.buildup[status] = 0.0
            self.active[status] = d["duration"] * getattr(o, "status_duration_mult", 1.0)
            return True
        return False

    def has(self, status):
        return self.active.get(status, 0.0) > 0.0

    def clear_negative(self):
        self.active.clear()
        for k in self.buildup:
            self.buildup[k] = 0.0

    # ------------------------------------------------------------------ bônus
    def add_buff(self, id_, mods, time, tags=(), max_stacks=1, source=None):
        b = self.buffs.get(id_)
        if b:
            b.time = max(b.time, time)
            if b.stacks < max_stacks:
                b.stacks += 1
                for k, v in mods.items():
                    b.mods[k] = b.mods.get(k, 0.0) + v
        else:
            b = self.buffs[id_] = Buff(id_, mods, time, tags, max_stacks, source)
        self._sync()
        return b

    def remove_buff(self, id_):
        if id_ in self.buffs:
            del self.buffs[id_]
            self._sync()

    def has_buff(self, id_):
        return id_ in self.buffs

    def _sync(self):
        total = {}
        for b in self.buffs.values():
            for k, v in b.mods.items():
                total[k] = total.get(k, 0.0) + v
        if "maldicao" in self.active:
            total["dmg_taken_mult"] = total.get("dmg_taken_mult", 0.0) + 0.2
        if "congelamento" in self.active:
            total["speed_mult"] = total.get("speed_mult", 0.0) - 0.45
            total["posture_taken_mult"] = total.get("posture_taken_mult", 0.0) + 0.5
            total["attack_speed"] = total.get("attack_speed", 0.0) - 0.3
        self.owner.stats.set_source("_status", total)

    # ------------------------------------------------------------------ tempo
    def update(self, dt):
        o = self.owner
        changed = False
        for k, d in STATUS_DEFS.items():
            if self.buildup[k] > 0:
                self.buildup[k] = max(0.0, self.buildup[k] - d["decay"] * dt)
        for k in list(self.active):
            self.active[k] -= dt
            if self.active[k] <= 0:
                del self.active[k]
                changed = True
        # dano contínuo
        if "queimadura" in self.active and not o.dead:
            o.take_dot(o.max_hp * 0.025 * dt + 1.5 * dt, "fogo")
        if "sangramento" in self.active and not o.dead:
            o.take_dot(o.max_hp * 0.006 * dt, "sangue")
        for k in list(self.buffs):
            b = self.buffs[k]
            b.time -= dt
            if b.time <= 0:
                del self.buffs[k]
                changed = True
        if changed or "maldicao" in self.active or "congelamento" in self.active:
            self._sync()
