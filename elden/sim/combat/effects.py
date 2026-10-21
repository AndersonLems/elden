"""Biblioteca de efeitos especiais disparados por golpes, habilidades, artes e runas.

Cada efeito é um dicionário {"type": ..., parâmetros}. Assim os dados (JSON) combinam efeitos sem
precisar de código novo para cada habilidade.
"""
import math

from ...core.mathutil import dir_of


def apply_effect(world, actor, eff, action=None):
    fn = EFFECTS.get(eff.get("type"))
    if fn is None:
        raise KeyError(f"efeito desconhecido: {eff.get('type')}")
    return fn(world, actor, eff, action)


def _heal(world, a, eff, action):
    amount = eff.get("amount", 0.2) * a.max_hp + eff.get("flat", 0.0)
    amount *= 1.0 + a.stats.get("heal_mult")
    a.heal(amount)
    if eff.get("allies_radius"):
        for ally in world.allies_of(a.team):
            if ally is not a and ally.dist_to(a) <= eff["allies_radius"]:
                ally.heal(amount * 0.6)


def _fp(world, a, eff, action):
    if hasattr(a, "fp"):
        a.fp = min(a.max_fp, a.fp + eff.get("amount", 20))


def _buff(world, a, eff, action):
    a.status.add_buff(eff["id"], eff.get("mods", {}), eff.get("time", 8.0), eff.get("tags", ()),
                      eff.get("max_stacks", 1))
    world.fx.push("buff", actor=a.id, id=eff["id"], color=eff.get("color", (1.0, 0.8, 0.3)), x=a.x, y=a.y, z=a.z)


def _cleanse(world, a, eff, action):
    a.status.clear_negative()
    a.status._sync()


def _barrier(world, a, eff, action):
    a.barrier = max(getattr(a, "barrier", 0.0), eff.get("amount", 0.25) * a.max_hp)
    a.barrier_time = eff.get("time", 8.0)
    world.fx.push("barrier", actor=a.id)


def _transform(world, a, eff, action):
    if hasattr(a, "set_transformed"):
        a.set_transformed(eff.get("on", True), eff.get("time", 20.0))


def _mist(world, a, eff, action):
    a.mist_time = eff.get("time", 1.2)
    a.iframes = max(a.iframes, eff.get("time", 1.2))
    world.fx.push("mist", actor=a.id, x=a.x, y=a.y, z=a.z)


def _fervor(world, a, eff, action):
    if hasattr(a, "fervor"):
        a.add_fervor(eff.get("amount", 20))


def _mark(world, a, eff, action):
    """Marca alvos próximos (Ninja/Vampiro): o próximo golpe em alvo marcado causa dano extra."""
    r = eff.get("radius", 6.0)
    for t in world.enemies_of(a):
        if t.dist_to(a) <= r:
            t.marked = eff.get("time", 6.0)
            t.mark_kind = eff.get("kind", "sombra")
            world.fx.push("mark", target=t.id, mark_kind=t.mark_kind)


def _summon(world, a, eff, action):
    if a.team == "player":
        return
    n = eff.get("count", 1)
    r = eff.get("radius", 2.5)
    for i in range(n):
        ang = a.facing + math.tau * i / max(1, n) + 0.4
        x, z = a.x + math.cos(ang) * r, a.z + math.sin(ang) * r
        if world.level.ground_at(x, z) is None:
            x, z = a.x, a.z
        world.spawn_enemy(eff["enemy"], x, z, summoned=True, aggro=True)


def _clone(world, a, eff, action):
    from ..clone import ShadowClone
    life = eff.get("time", 1.5)
    c = ShadowClone(a, life=life, mode=eff.get("mode", "strike"), power=eff.get("power", 0.5))
    world.spawn(c)


def _pull_enemies(world, a, eff, action):
    r = eff.get("radius", 5.0)
    for t in world.enemies_of(a):
        d = t.dist_to(a)
        if 0.6 < d <= r and t.stagger_resist < 2:
            k = eff.get("strength", 6.0) / max(0.5, t.weight)
            t.kx += (a.x - t.x) / d * k
            t.kz += (a.z - t.z) / d * k


def _leap(world, a, eff, action):
    a.vy = eff.get("vy", 9.0)
    a.grounded = False


def _self_damage(world, a, eff, action):
    a.hp = max(1.0, a.hp - a.max_hp * eff.get("amount", 0.05))


def _reload(world, a, eff, action):
    if hasattr(a, "ammo"):
        a.ammo = a.max_ammo
        world.fx.push("reload", actor=a.id)


def _ammo(world, a, eff, action):
    if hasattr(a, "ammo_kind"):
        a.ammo_kind = eff.get("kind", "normal")
        a.ammo_special = eff.get("count", 6)


def _trap(world, a, eff, action):
    fx, fz = dir_of(a.facing)
    d = eff.get("dist", 1.2)
    spec = dict(eff["zone"])
    world.spawn_zone(a, spec, a.x + fx * d, a.y, a.z + fz * d, a.facing, getattr(action, "power", 1.0))


def _boss_call(world, a, eff, action):
    """Chama um método do chefe (destruição de arena, invocações especiais...)."""
    fn = getattr(a, eff["method"], None)
    if fn:
        fn(**eff.get("args", {}))


def _invuln(world, a, eff, action):
    a.iframes = max(a.iframes, eff.get("time", 0.5))


def _dash_to_mark(world, a, eff, action):
    marked = [t for t in world.enemies_of(a) if getattr(t, "marked", 0) > 0]
    if not marked:
        return
    tgt = min(marked, key=lambda t: t.dist_to(a))
    ang = tgt.facing + math.pi
    x, z = tgt.x + math.cos(ang) * (tgt.radius + 0.6), tgt.z + math.sin(ang) * (tgt.radius + 0.6)
    if world.level.ground_at(x, z) is not None:
        world.fx.push("teleport", x0=a.x, y0=a.y, z0=a.z, x=x, y=tgt.y, z=z, actor=a.id)
        a.x, a.z = x, z
        a.face(a.angle_to(tgt))
        a.target = tgt


def _invisible(world, a, eff, action):
    a.invisible = eff.get("time", 3.0)
    world.fx.push("vanish", x=a.x, y=a.y, z=a.z, actor=a.id)


def _howl(world, a, eff, action):
    """Uivo do Lobisomem: com fúria suficiente, transforma."""
    if getattr(a, "fury", 0) >= eff.get("fury", 50) and hasattr(a, "set_transformed"):
        a.fury -= 20
        a.set_transformed(True, eff.get("time", 18.0))


EFFECTS = {
    "heal": _heal, "fp": _fp, "buff": _buff, "cleanse": _cleanse, "barrier": _barrier,
    "transform": _transform, "mist": _mist, "fervor": _fervor, "mark": _mark, "summon": _summon,
    "clone": _clone, "pull": _pull_enemies, "leap": _leap, "self_damage": _self_damage, "reload": _reload,
    "ammo": _ammo, "trap": _trap, "boss": _boss_call, "invuln": _invuln, "dash_to_mark": _dash_to_mark,
    "invisible": _invisible, "howl": _howl,
}
