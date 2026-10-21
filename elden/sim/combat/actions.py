"""Ações de combate: o que um ator está fazendo agora (golpe, esquiva, bloqueio, reação...).

Cada ação controla animação, movimento, janelas de acerto, invencibilidade e cancelamento.
O controle do jogador e a IA apenas escolhem qual ação iniciar e quando.
"""
import math

from ...core.mathutil import dir_of, turn_towards, angle_of, clamp
from .hitbox import HitShape
from .damage import apply_hit


class Action:
    name = "action"
    anim = "idle"
    ghost = False             # atravessa outros atores (esquiva)

    def __init__(self):
        self.t = 0.0
        self.actor = None
        self.chain = None     # ação seguinte ao terminar naturalmente

    def start(self, actor):
        self.actor = actor
        self.t = 0.0
        actor.set_anim(self.anim, 0.0)

    def update(self, dt):
        self.t += dt
        return True

    def exit(self, interrupted):
        pass

    def interruptible_by_input(self):
        return False

    def can_dodge(self):
        return False

    def can_chain(self):
        return False

    def armor_active(self):
        return False

    def debug_shapes(self):
        return []


# --------------------------------------------------------------------------- golpe
class MoveAction(Action):
    name = "move"

    def __init__(self, move, inp=None, power=1.0, target=None, moveset=None, from_air=False, extra=None):
        super().__init__()
        self.move = move
        self.inp = inp
        self.power = power
        self.target = target
        self.moveset = moveset
        self.extra = extra or {}
        self.hit_sets = []
        self.rehit_timers = []
        self.spawned = set()
        self.hits_landed = 0
        self.landed_targets = []
        self.speed = 1.0
        self.started_air = from_air
        self.landed = False
        self.queued = None     # próxima entrada (buffer) aceita pelo controle

    def start(self, actor):
        super().start(actor)
        m = self.move
        self.speed = max(0.35, 1.0 + actor.stats.get("attack_speed")) * m.anim_speed
        self.hit_sets = [set() for _ in m.hits]
        self.rehit_timers = [0.0 for _ in m.hits]
        self.started_air = self.started_air or not actor.grounded
        tgt = self.target or actor.target
        if m.aim and tgt is not None and getattr(tgt, "alive", False) and not getattr(tgt, "dead", False):
            if actor.dist_to(tgt) < 7.0:
                actor.face(actor.angle_to(tgt))
        actor.set_anim(m.anim, 0.0)
        actor.move_x = actor.move_z = 0.0
        if self.started_air and m.hang:
            actor.vy = max(actor.vy, 0.5)
        if actor.world:
            actor.world.fx.push("swing_start", actor=actor.id, move=m.id, anim=m.anim, sound=m.sound, type=m.type)
            actor.world.on_move_start(actor, self)

    def _in(self, win):
        return win is not None and win[0] <= self.t < win[1]

    def update(self, dt):
        a = self.actor
        m = self.move
        t0 = self.t
        self.t += dt * self.speed
        t = self.t
        # rastreio do alvo antes do primeiro quadro ativo
        tgt = self.target or a.target
        first_active = m.hits[0]["t"][0] if m.hits else m.dur * 0.3
        if tgt is not None and getattr(tgt, "alive", False) and t < first_active and m.track > 0:
            a.face(turn_towards(a.facing, a.angle_to(tgt), a.turn_speed * m.track * dt * 3))
        # deslocamento
        moving = False
        for w in m.moves:
            if w["t"][0] <= t < w["t"][1]:
                sp = w.get("speed", 0.0)
                if w.get("to_target") and tgt is not None and getattr(tgt, "alive", False):
                    d = a.dist_to(tgt) - (a.radius + tgt.radius + 0.35)
                    remaining = max(1e-3, (w["t"][1] - t) / self.speed)
                    sp = clamp(d / remaining, 0.0, abs(sp)) * (1 if sp >= 0 else -1)
                fx, fz = dir_of(a.facing)
                a.move_x, a.move_z = fx * sp, fz * sp
                moving = True
        if not moving:
            a.move_x *= 0.6
            a.move_z *= 0.6
        elif m.d.get("wall_stun") and getattr(a, "hit_wall", False) and t > 0.1:
            # investida contra a parede: atordoa o próprio atacante (contra-ataque para o jogador)
            if a.world:
                a.world.fx.push("wall_crash", x=a.x, y=a.y + 1, z=a.z)
                a.world.fx.push("shake", amount=0.3, time=0.3)
            self.chain = HurtAction(1.8)
            return False
        if m.jump and t0 <= m.jump["t"] < t:
            a.vy = m.jump["vy"]
            a.grounded = False
        if m.hang and not a.grounded:
            a.gravity_scale_override = 0.12
            if a.vy < -1.0:
                a.vy = -1.0
        else:
            a.gravity_scale_override = None
        if m.iframes and self._in(m.iframes):
            a.iframes = max(a.iframes, 0.05)
        if m.armor and self._in(m.armor):
            a.super_armor = max(a.super_armor, 0.05)
        if m.teleport and t0 <= m.teleport.get("t", 0.0) < t + 1e-9 and "tp" not in self.spawned:
            self.spawned.add("tp")
            self._teleport(m.teleport)
        # acertos
        for i, h in enumerate(m.hits):
            w0, w1 = h["t"]
            if t >= w0 and t0 < w1:
                rehit = h.get("rehit")
                if rehit:
                    self.rehit_timers[i] -= dt
                    if self.rehit_timers[i] <= 0:
                        self.rehit_timers[i] = rehit
                        self.hit_sets[i].clear()
                self._do_hits(i, h)
                if self.actor.action is not self:
                    return True     # fomos aparados/interrompidos durante a resolução
        for k, s in enumerate(m.spawns):
            ts = s.get("t", 0.0)
            if t0 <= ts < t + 1e-9 and k not in self.spawned:
                self.spawned.add(k)
                if a.world:
                    a.world.spawn_from_spec(a, s, self)
        for k, eff in enumerate(m.effects):
            te = eff.get("t", 0.0)
            key = ("eff", k)
            if t0 <= te < t + 1e-9 and key not in self.spawned:
                self.spawned.add(key)
                if a.world:
                    a.world.apply_move_effect(a, eff, self)
        a.set_anim(m.anim, min(1.0, t / m.dur))
        # golpes de mergulho: continuam até tocar o chão
        if m.land:
            if self.started_air and not a.grounded:
                if t >= m.dur * 0.5:
                    self.t = min(self.t, m.dur * 0.55)
                    a.vy = min(a.vy, -16.0)
                return True
            if self.started_air and a.grounded and not self.landed:
                self.landed = True
                if self.moveset is not None:
                    nxt = self.moveset.get(m.land)
                else:
                    from .moves import get_move
                    nxt = get_move(m.land)
                if nxt is not None:
                    self.chain = MoveAction(nxt, moveset=self.moveset, power=self.power, extra=self.extra)
                return False
        return t < m.dur

    def _teleport(self, spec):
        a = self.actor
        w = a.world
        tgt = self.target or a.target
        mode = spec.get("to", "forward")
        dist = spec.get("dist", 3.0)
        if mode in ("behind", "front", "target") and tgt is not None and getattr(tgt, "alive", False):
            if a.dist_to(tgt) > spec.get("range", 8.0):
                return
            if mode == "behind":
                ang = tgt.facing + math.pi
                d = tgt.radius + a.radius + 0.4
            elif mode == "front":
                ang = tgt.angle_to(a)
                d = tgt.radius + a.radius + 0.5
            else:
                ang = tgt.angle_to(a)
                d = tgt.radius + a.radius + 0.3
            nx, nz = tgt.x + math.cos(ang) * d, tgt.z + math.sin(ang) * d
            ny = tgt.y if mode == "target" else None
        else:
            fx, fz = dir_of(a.facing)
            nx, nz, ny = a.x + fx * dist, a.z + fz * dist, None
        if w is None:
            a.x, a.z = nx, nz
            return
        g = w.level.ground_at(nx, nz)
        if g is None or w.level.blocks(int(math.floor(nx)), int(math.floor(nz)), (ny if ny is not None else a.y)):
            # tenta metade do caminho
            nx, nz = (a.x + nx) * 0.5, (a.z + nz) * 0.5
            g = w.level.ground_at(nx, nz)
            if g is None or w.level.blocks(int(math.floor(nx)), int(math.floor(nz)), a.y):
                return
        w.fx.push("teleport", x0=a.x, y0=a.y, z0=a.z, x=nx, y=(ny if ny is not None else g), z=nz, actor=a.id)
        a.x, a.z = nx, nz
        if ny is not None:
            a.y = ny
            a.grounded = False
        else:
            a.y = max(a.y, g)
        if tgt is not None and getattr(tgt, "alive", False):
            a.face(a.angle_to(tgt))

    def _do_hits(self, i, spec):
        a = self.actor
        w = a.world
        if w is None:
            return
        reach = a.scale
        if "beast" in self.move.tags and getattr(a, "transformed", False) and "beast_reach" in getattr(a, "flags", ()):
            reach *= 1.3
        shape = HitShape(spec, reach)
        for tgt in w.hit_candidates(a):
            if tgt.id in self.hit_sets[i]:
                continue
            if not shape.test(a.x, a.y, a.z, a.facing, tgt):
                continue
            if not w.level.line_clear(a.x, a.z, tgt.x, tgt.z, a.y + 0.9):
                continue
            self.hit_sets[i].add(tgt.id)
            hit = a.build_hit(self.move, spec, self)
            apply_hit(tgt, hit) if not getattr(tgt, "is_prop", False) else tgt.receive_hit(hit)
            self.on_hit_result(tgt, hit)
            if a.action is not self:
                return

    def on_hit_result(self, tgt, hit):
        a = self.actor
        if hit.result in ("hit",) and hit.launch > 0 and "launcher_jump" in getattr(a, "flags", ()) \
                and a.grounded and not self.extra.get("jumped") and not getattr(tgt, "is_prop", False):
            self.extra["jumped"] = True
            a.vy = 8.8
            a.grounded = False
            a.y += 0.02
            self.t = max(self.t, self.move.cancel)
        if hit.result in ("hit", "killed", "blocked", "guardbreak"):
            self.hits_landed += 1
            self.landed_targets.append(tgt)
            if self.hits_landed == 1 and self.actor.world:
                shake = self.move.shake or (0.25 if hit.heavy else 0.08)
                self.actor.world.fx.push("shake", amount=shake, time=0.15 + shake * 0.3)

    def interruptible_by_input(self):
        return self.t >= self.move.free

    def can_dodge(self):
        return self.t >= self.move.dodge_cancel or (self.hits_landed > 0 and self.t >= self.move.dodge_cancel * 0.6)

    def can_chain(self):
        return self.t >= self.move.cancel

    def armor_active(self):
        return self.move.armor is not None and self._in(self.move.armor)

    def exit(self, interrupted):
        a = self.actor
        a.gravity_scale_override = None
        if a.world:
            a.world.on_move_end(a, self, interrupted)

    def debug_shapes(self):
        a = self.actor
        out = []
        for h in self.move.hits:
            if h["t"][0] <= self.t < h["t"][1]:
                out.append(HitShape(h, a.scale).debug(a.x, a.z, a.facing))
        return out


class ChargeAction(Action):
    """Segurar o pesado: acumula carga e solta um golpe mais forte."""
    name = "charge"
    anim = "charge"

    def __init__(self, base_move, release_move, cmin=0.35, cmax=1.1, moveset=None):
        super().__init__()
        self.base_move = base_move
        self.release_move = release_move
        self.cmin = cmin
        self.cmax = cmax
        self.moveset = moveset
        self.released = False
        self.level = 0.0

    def start(self, actor):
        super().start(actor)
        actor.move_x = actor.move_z = 0.0
        if actor.world:
            actor.world.fx.push("charge_start", actor=actor.id)

    def update(self, dt):
        self.t += dt
        a = self.actor
        self.level = clamp((self.t - self.cmin) / max(0.01, self.cmax - self.cmin), 0.0, 1.0) if self.t >= self.cmin else 0.0
        a.set_anim("charge", min(1.0, self.t / self.cmax))
        if a.world and self.t >= self.cmax and not getattr(self, "_full", False):
            self._full = True
            a.world.fx.push("charge_full", actor=a.id, x=a.x, y=a.y + 1.2, z=a.z)
        if self.t > self.cmax + 0.6:
            self.release()
        if self.released:
            return False
        return True

    def release(self):
        if self.released:
            return
        self.released = True
        a = self.actor
        if self.t >= self.cmin and self.release_move is not None:
            self.chain = MoveAction(self.release_move, power=1.0 + self.level * 0.9, moveset=self.moveset,
                                    extra={"charged": self.level})
        else:
            self.chain = MoveAction(self.base_move, moveset=self.moveset)


# --------------------------------------------------------------------------- defesa e mobilidade
class DodgeAction(Action):
    name = "dodge"
    anim = "dodge"
    ghost = True

    def __init__(self, angle, distance=4.0, dur=0.34, iframes=0.24, anim="dodge"):
        super().__init__()
        self.angle = angle
        self.distance = distance
        self.dur = dur
        self.iframe_time = iframes
        self.anim = anim
        self.perfect_triggered = False

    def start(self, actor):
        super().start(actor)
        actor.face(self.angle)
        actor.iframes = max(actor.iframes, self.iframe_time + actor.stats.get("dodge_iframes"))
        self.dist = self.distance * (1.0 + actor.stats.get("dodge_distance"))
        if actor.world:
            actor.world.fx.push("dodge", actor=actor.id, x=actor.x, y=actor.y, z=actor.z, angle=self.angle)

    def update(self, dt):
        self.t += dt
        a = self.actor
        p = self.t / self.dur
        # perfil: rápido no início, freia no fim
        sp = self.dist / self.dur * (1.6 if p < 0.55 else 0.35)
        fx, fz = dir_of(self.angle)
        a.move_x, a.move_z = fx * sp, fz * sp
        a.set_anim(self.anim, min(1.0, p))
        return self.t < self.dur

    def exit(self, interrupted):
        a = self.actor
        a.move_x *= 0.3
        a.move_z *= 0.3
        if a.world:
            a.world.on_dodge_end(a, self)

    def can_chain(self):
        return self.t >= self.dur * 0.45

    def can_dodge(self):
        return self.t >= self.dur * 0.8

    def interruptible_by_input(self):
        return self.t >= self.dur * 0.8


class BlockAction(Action):
    name = "block"
    anim = "block"

    def __init__(self, reduction=0.6, posture_mult=1.0):
        super().__init__()
        self.reduction = reduction
        self.posture_mult = posture_mult
        self.holding = True
        self.parried = 0

    def update(self, dt):
        self.t += dt
        a = self.actor
        a.set_anim("block")
        return self.holding

    def on_parry(self, hit):
        self.parried += 1
        a = self.actor
        if hasattr(a, "on_parry_success"):
            a.on_parry_success(hit)

    def on_block(self, hit):
        a = self.actor
        a.set_anim("block_hit")
        a.anim_t = 0.0

    def interruptible_by_input(self):
        return True

    def can_dodge(self):
        return True

    def can_chain(self):
        return True


# --------------------------------------------------------------------------- reações
class HurtAction(Action):
    name = "hurt"
    anim = "hurt"

    def __init__(self, stun=0.3, parried=False):
        super().__init__()
        self.stun = stun
        self.parried = parried

    def start(self, actor):
        super().start(actor)
        actor.move_x = actor.move_z = 0.0
        actor.hurt_timer = self.stun

    def update(self, dt):
        self.t += dt
        self.actor.set_anim("hurt", min(1.0, self.t / max(0.01, self.stun)))
        return self.t < self.stun

    def can_dodge(self):
        return self.t >= self.stun * 0.45 and not self.parried


class LaunchedAction(Action):
    """Lançado ao ar: indefeso até cair. Golpes aéreos mantêm o alvo no ar (com limite)."""
    name = "launched"
    anim = "launched"

    def __init__(self, vy):
        super().__init__()
        self.vy = vy

    def start(self, actor):
        super().start(actor)
        actor.vy = self.vy
        actor.grounded = False
        actor.y += 0.05
        actor.move_x = actor.move_z = 0.0
        actor.gravity_scale_override = 0.75
        if actor.world:
            actor.world.on_launch(actor)

    def juggle_hit(self, hit):
        a = self.actor
        a.juggle += 1
        up = 3.4 - a.juggle * 0.28 + hit.launch * 0.25
        if a.juggle < 9:
            a.vy = max(a.vy, up)
            a.gravity_scale_override = 0.5
        else:
            a.gravity_scale_override = 1.2
        a.kx *= 0.3
        a.kz *= 0.3

    def update(self, dt):
        self.t += dt
        a = self.actor
        a.set_anim("launched")
        if a.grounded and self.t > 0.12:
            self.chain = KnockdownAction(0.75 if a.juggle < 4 else 0.95)
            return False
        if self.t > 6.0:
            return False
        return True

    def exit(self, interrupted):
        self.actor.gravity_scale_override = None


class KnockdownAction(Action):
    name = "down"
    anim = "down"

    def __init__(self, dur=0.8):
        super().__init__()
        self.dur = dur

    def start(self, actor):
        super().start(actor)
        actor.juggle = 0
        actor.move_x = actor.move_z = 0.0
        if actor.world:
            actor.world.fx.push("land_heavy", x=actor.x, y=actor.y, z=actor.z, size=actor.radius)

    def update(self, dt):
        self.t += dt
        p = self.t / self.dur
        self.actor.set_anim("down" if p < 0.65 else "getup", min(1.0, p))
        return self.t < self.dur

    def can_dodge(self):
        return self.t >= self.dur * 0.6


class StaggerAction(Action):
    """Postura rompida: vulnerável, pode receber execução."""
    name = "stagger"
    anim = "stagger"

    def __init__(self, dur=2.5):
        super().__init__()
        self.dur = dur

    def start(self, actor):
        super().start(actor)
        actor.move_x = actor.move_z = 0.0
        if actor.world:
            actor.world.fx.push("posture_break", actor=actor.id, x=actor.x, y=actor.y + actor.height, z=actor.z)

    def update(self, dt):
        self.t += dt
        self.actor.set_anim("stagger", min(1.0, self.t / self.dur))
        if self.t >= self.dur:
            self.actor.broken = 0.0
            self.actor.posture = 0.0
            return False
        return True


class ExecuteAction(Action):
    """Execução de um inimigo com postura rompida (ou golpe pelas costas do Ladrão/Ninja)."""
    name = "execute"
    anim = "execute"

    def __init__(self, victim, dur=1.05, impact=0.5, mult=4.5):
        super().__init__()
        self.victim = victim
        self.dur = dur
        self.impact = impact
        self.mult = mult
        self.done = False

    def start(self, actor):
        super().start(actor)
        v = self.victim
        ang = v.angle_to(actor)
        d = v.radius + actor.radius + 0.25
        actor.x, actor.z = v.x + math.cos(ang) * d, v.z + math.sin(ang) * d
        actor.face(actor.angle_to(v))
        actor.invulnerable = True
        v.set_action(ExecutedAction(self.dur + 0.4))
        if actor.world:
            actor.world.fx.push("execution_start", actor=actor.id, victim=v.id, x=v.x, y=v.y, z=v.z)

    def update(self, dt):
        self.t += dt
        a = self.actor
        a.move_x = a.move_z = 0.0
        a.set_anim("execute", min(1.0, self.t / self.dur))
        if not self.done and self.t >= self.impact:
            self.done = True
            v = self.victim
            hit = a.build_execution_hit(v, self.mult) if hasattr(a, "build_execution_hit") else None
            if hit is not None:
                v.broken = 0.0
                apply_hit(v, hit)
                if a.world:
                    a.world.fx.push("execution_hit", x=v.x, y=v.y + 1.0, z=v.z, damage=hit.damage)
                    a.world.fx.push("shake", amount=0.5, time=0.35)
                    a.world.on_execution(a, v, hit)
        return self.t < self.dur

    def exit(self, interrupted):
        self.actor.invulnerable = False


class ExecutedAction(Action):
    name = "executed"
    anim = "hurt"

    def __init__(self, dur):
        super().__init__()
        self.dur = dur

    def update(self, dt):
        self.t += dt
        self.actor.set_anim("stagger", min(1.0, self.t / self.dur))
        return self.t < self.dur

    def exit(self, interrupted):
        a = self.actor
        if not a.dead:
            a.posture = 0.0
            a.broken = 0.0


class DeathAction(Action):
    name = "death"
    anim = "death"

    def start(self, actor):
        super().start(actor)
        actor.move_x = actor.move_z = 0.0

    def update(self, dt):
        self.t += dt
        self.actor.set_anim("death", min(1.0, self.t / 0.9))
        return True


# --------------------------------------------------------------------------- utilitárias
class TimedAction(Action):
    """Ação genérica de duração fixa com animação (interagir, sentar, transformar, rugir...)."""

    def __init__(self, anim, dur, callback=None, at=0.5, loop=False, invulnerable=False, armor=False,
                 interruptible=False, name="timed"):
        super().__init__()
        self.anim = anim
        self.dur = dur
        self.callback = callback
        self.at = at
        self.loop = loop
        self.fired = False
        self.invuln = invulnerable
        self.armor = armor
        self.interruptible = interruptible
        self.name = name

    def start(self, actor):
        super().start(actor)
        actor.move_x = actor.move_z = 0.0
        if self.invuln:
            actor.invulnerable = True

    def update(self, dt):
        self.t += dt
        a = self.actor
        a.move_x = a.move_z = 0.0
        if self.armor:
            a.super_armor = max(a.super_armor, 0.05)
        if self.loop:
            a.set_anim(self.anim)
        else:
            a.set_anim(self.anim, min(1.0, self.t / self.dur))
        if not self.fired and self.t >= self.dur * self.at:
            self.fired = True
            if self.callback:
                self.callback()
        return self.loop or self.t < self.dur

    def exit(self, interrupted):
        if self.invuln:
            self.actor.invulnerable = False

    def interruptible_by_input(self):
        return self.interruptible

    def can_dodge(self):
        return self.interruptible
