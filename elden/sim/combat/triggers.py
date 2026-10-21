"""Motor de gatilhos: runas, nós da árvore e passivas reagem a eventos de combate.

Exemplo de gatilho (JSON):
  {"on": "crit", "do": "heal", "amount": 0.02, "cd": 0.4}
  {"on": "finisher_hit", "do": "chain", "chance": 0.35, "jumps": 3, "dmg": 0.5}

Proteções contra explosões infinitas: um gatilho nunca dispara outro (sem recursão), cada gatilho tem
tempo de recarga interno e os acúmulos (calor, marcas) têm limites.
"""
import math

from ...core.mathutil import dir_of
from .damage import Hit, apply_hit


class TriggerEngine:
    def __init__(self, owner, triggers):
        self.owner = owner
        self.triggers = list(triggers)
        self.cooldowns = {}
        self.counters = {}
        self.busy = False
        self.fired = []          # histórico recente (para testes e interface)

    def update(self, dt):
        for k in list(self.cooldowns):
            self.cooldowns[k] -= dt
            if self.cooldowns[k] <= 0:
                del self.cooldowns[k]

    def _cond_ok(self, trig, ctx):
        c = trig.get("cond")
        if not c:
            return True
        o = self.owner
        tgt = ctx.get("target")
        hit = ctx.get("hit")
        if "target_status" in c and (tgt is None or not tgt.status.has(c["target_status"])):
            return False
        if "transformed" in c and bool(getattr(o, "transformed", False)) != c["transformed"]:
            return False
        if "hp_below" in c and o.hp / max(1, o.max_hp) >= c["hp_below"]:
            return False
        if "hp_above" in c and o.hp / max(1, o.max_hp) <= c["hp_above"]:
            return False
        if "move_type" in c and (hit is None or hit.move_type not in c["move_type"]):
            return False
        if "move_tag" in c and (hit is None or c["move_tag"] not in hit.tags):
            return False
        if "element" in c and (hit is None or hit.elements.get(c["element"], 0) <= 0):
            return False
        if "target_broken" in c and (tgt is None or (tgt.broken > 0) != c["target_broken"]):
            return False
        if "airborne_target" in c and (tgt is None or tgt.grounded == c["airborne_target"]):
            return False
        if "night" in c and getattr(o.world, "night", False) != c["night"]:
            return False
        return True

    def emit(self, event, **ctx):
        if self.busy or self.owner.world is None:
            return
        self.busy = True
        try:
            for i, trig in enumerate(self.triggers):
                if trig.get("on") != event:
                    continue
                key = (i, trig.get("source"))
                if key in self.cooldowns:
                    continue
                if not self._cond_ok(trig, ctx):
                    continue
                chance = trig.get("chance", 1.0)
                if chance < 1.0 and self.owner.world.rng.random() > chance:
                    continue
                self.cooldowns[key] = trig.get("cd", 0.1)
                self._do(trig, ctx)
                self.fired.append((event, trig.get("do"), trig.get("source")))
                if len(self.fired) > 50:
                    self.fired = self.fired[-50:]
        finally:
            self.busy = False

    # ------------------------------------------------------------------ ações
    def _do(self, trig, ctx):
        actions = trig["do"] if isinstance(trig["do"], list) else [trig["do"]]
        for act in actions:
            getattr(self, "_a_" + act)(trig, ctx)

    def _a_heal(self, t, ctx):
        o = self.owner
        hit = ctx.get("hit")
        if "of_damage" in t and hit is not None:
            o.heal(hit.damage * t["of_damage"])
        else:
            o.heal(o.max_hp * t.get("amount", 0.03))

    def _a_fp(self, t, ctx):
        o = self.owner
        o.fp = min(o.max_fp, o.fp + t.get("amount", 5))

    def _a_fervor(self, t, ctx):
        self.owner.add_fervor(t.get("amount", 5))

    def _a_buff(self, t, ctx):
        b = t["buff"]
        self.owner.status.add_buff(b["id"], b.get("mods", {}), b.get("time", 4.0), (), b.get("max_stacks", 1))
        self.owner.world.fx.push("buff", actor=self.owner.id, id=b["id"], color=b.get("color", (1, 0.8, 0.3)),
                                 x=self.owner.x, y=self.owner.y, z=self.owner.z)

    def _pos(self, t, ctx):
        where = t.get("at", "target")
        tgt = ctx.get("target")
        o = self.owner
        if where == "target" and tgt is not None:
            return tgt.x, tgt.y, tgt.z
        if where == "attacker" and ctx.get("attacker") is not None:
            a = ctx["attacker"]
            return a.x, a.y, a.z
        return o.x, o.y, o.z

    def _a_zone(self, t, ctx):
        o = self.owner
        x, y, z = self._pos(t, ctx)
        spec = dict(t["zone"])
        o.world.spawn_zone(o, spec, x, y, z, o.facing, t.get("power", 1.0), move_type="rune", tags=("rune",))

    def _a_proj(self, t, ctx):
        o = self.owner
        o.world.spawn_projectiles(o, t["proj"], t.get("power", 1.0), "rune", ("rune",))

    def _a_chain(self, t, ctx):
        """Descarga elétrica que salta entre inimigos próximos."""
        o = self.owner
        w = o.world
        tgt = ctx.get("target")
        if tgt is None:
            return
        hit_ids = {tgt.id}
        cur = tgt
        base = sum(o.attack_power(None, {}).values()) * t.get("dmg", 0.4)
        el = t.get("element", "raio")
        for _ in range(t.get("jumps", 3)):
            cands = [e for e in w.enemies_of(o) if e.id not in hit_ids and e.dist_to(cur) <= t.get("radius", 5.0)]
            if not cands:
                break
            nxt = min(cands, key=lambda e: e.dist_to(cur))
            w.fx.push("lightning", x0=cur.x, y0=cur.y + 1.0, z0=cur.z, x=nxt.x, y=nxt.y + 1.0, z=nxt.z)
            h = Hit(o, {el: base}, posture=6, knockback=0.5, stun=0.3, tags=("rune",), move_type="rune",
                    hitstop=0.02, status={"choque": 25}, can_crit=False)
            apply_hit(nxt, h)
            hit_ids.add(nxt.id)
            cur = nxt
        if len(hit_ids) == 1:
            w.fx.push("lightning", x0=tgt.x, y0=tgt.y + 2.5, z0=tgt.z, x=tgt.x, y=tgt.y + 0.8, z=tgt.z)
            h = Hit(o, {el: base * 0.6}, posture=4, knockback=0.2, stun=0.2, tags=("rune",), move_type="rune",
                    hitstop=0.02, status={"choque": 25}, can_crit=False)
            apply_hit(tgt, h)

    def _a_clone(self, t, ctx):
        from ..clone import ShadowClone
        o = self.owner
        o.world.spawn(ShadowClone(o, life=t.get("time", 1.6), mode=t.get("mode", "strike"), power=t.get("power", 0.6)))

    def _a_cooldown(self, t, ctx):
        o = self.owner
        if hasattr(o, "cooldowns"):
            for k in o.cooldowns:
                o.cooldowns[k] = max(0.0, o.cooldowns[k] - t.get("amount", 1.0))

    def _a_status(self, t, ctx):
        tgt = ctx.get("target")
        if tgt is None or tgt.dead:
            return
        for st, v in t["status"].items():
            tgt.status.add_buildup(st, v)

    def _a_heat(self, t, ctx):
        """Runa da Forja: golpes pesados acumulam calor; ao encher, explosão de fogo (com recarga)."""
        o = self.owner
        key = t.get("source", "heat")
        self.counters[key] = self.counters.get(key, 0) + 1
        o.heat = self.counters[key] / t.get("needed", 4)
        if self.counters[key] >= t.get("needed", 4):
            self.counters[key] = 0
            o.heat = 0.0
            tgt = ctx.get("target")
            x, y, z = (tgt.x, tgt.y, tgt.z) if tgt is not None else (o.x, o.y, o.z)
            o.world.spawn_zone(o, {"zone": "burst", "radius": 2.6, "dmg": t.get("dmg", 1.2), "pure": {"fogo": 1.0},
                                   "kb": 4, "posture": 20, "stun": 0.4, "visual": "fire_burst",
                                   "status": {"queimadura": 40}}, x, y, z, o.facing, 1.0, move_type="rune",
                               tags=("rune",))

    def _a_teleport_window(self, t, ctx):
        o = self.owner
        tgt = ctx.get("target")
        if tgt is not None:
            o.teleport_target = tgt
            o.teleport_window = t.get("time", 0.8)

    def _a_bonus_damage(self, t, ctx):
        o = self.owner
        tgt = ctx.get("target")
        if tgt is None or tgt.dead:
            return
        base = sum(o.attack_power(None, {}).values()) * t.get("dmg", 0.3)
        el = t.get("element", "fisico")
        apply_hit(tgt, Hit(o, {el: base}, posture=t.get("posture", 2), knockback=0, stun=0, no_reaction=True,
                           tags=("rune",), move_type="rune", can_crit=False, hitstop=0.0))

    def _a_mark(self, t, ctx):
        tgt = ctx.get("target")
        if tgt is not None:
            tgt.marked = t.get("time", 5.0)
            tgt.mark_kind = t.get("kind", "sangue")
            self.owner.world.fx.push("mark", target=tgt.id, mark_kind=tgt.mark_kind)

    def _a_refund_dodge(self, t, ctx):
        o = self.owner
        if hasattr(o, "dodge_charges"):
            o.dodge_charges = min(o.max_dodges, o.dodge_charges + 1)

    def _a_barrier(self, t, ctx):
        o = self.owner
        o.barrier = max(getattr(o, "barrier", 0.0), o.max_hp * t.get("amount", 0.1))
        o.barrier_time = t.get("time", 5.0)
        o.world.fx.push("barrier", actor=o.id)

    def _a_steal(self, t, ctx):
        o = self.owner
        if hasattr(o, "on_steal"):
            o.on_steal(ctx.get("target"), t)

    def _a_fury(self, t, ctx):
        o = self.owner
        if hasattr(o, "fury"):
            o.fury = min(100.0, o.fury + t.get("amount", 5))
