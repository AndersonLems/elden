"""O Portador (jogador): interpreta a entrada, escolhe golpes no grafo de combos e gerencia recursos.

Contextos de entrada para ataques:
  L/H normais, DL/DH (logo após esquiva), RL/RH (correndo), AL/AH (no ar), BH (afastando-se do alvo
  travado = lançador), FH (avançando para o alvo), C (contra-ataque após aparar), X (execução).
"""
import math

from ..core.data import DB
from ..core.mathutil import angle_of, angle_diff, dir_of, length, norm, clamp
from .entity import Actor
from .input_state import InputState
from .combat.actions import (MoveAction, ChargeAction, DodgeAction, BlockAction, ExecuteAction, TimedAction,
                             HurtAction, LaunchedAction, StaggerAction, KnockdownAction, DeathAction)
from .combat.damage import Hit
from .combat.moves import get_move
from .combat.triggers import TriggerEngine
from .progression import loadout as loadout_mod

JUMP_SPEED = 9.6
SPRINT_MULT = 1.5
DODGE_RECHARGE = 0.65
FERVOR_MAX = 100.0


class Player(Actor):
    kind = "player"
    team = "player"
    radius = 0.34
    height = 1.7
    base_speed = 5.6
    turn_speed = 18.0
    stagger_resist = 0
    can_be_launched = True

    def __init__(self, character, x=0.0, z=0.0, y=0.0):
        super().__init__(x, z, y)
        self.char = character
        self.input = InputState()
        self.fervor = 0.0
        self.cooldowns = {}
        self.dodge_charges = 2
        self.max_dodges = 2
        self.dodge_timer = 0.0
        self.since_dodge = 9.0
        self.counter_window = 0.0
        self.teleport_window = 0.0
        self.teleport_target = None
        self.sprinting = False
        self.locked = None
        self.barrier = 0.0
        self.barrier_time = 0.0
        self.transformed = False
        self.transform_time = 0.0
        self.mist_time = 0.0
        self.invisible = 0.0
        self.ammo = 6
        self.max_ammo = 6
        self.ammo_special = 0
        self.fury = 0.0
        self.heat = 0.0
        self.flasks_hp = character.flasks_hp
        self.flasks_fp = character.flasks_fp
        self.interact_target = None
        self.combo_count = 0
        self.combo_timer = 0.0
        self.last_move_id = None
        self.stats_log = {"perfect_dodges": 0, "parries": 0, "executions": 0, "kills": 0, "max_combo": 0}
        self.apply_loadout()
        self.hp = self.max_hp
        self.fp = self.max_fp

    # ------------------------------------------------------------------ loadout
    def apply_loadout(self):
        L = loadout_mod.compute(self.char)
        self.L = L
        ratio_hp = self.hp / self.max_hp if self.max_hp else 1.0
        ratio_fp = self.fp / self.max_fp if self.max_fp else 1.0
        self.stats.base = {}
        self.stats.set_source("loadout", L.mods)
        self.stats.set_source("def", {"def_flat": L.def_flat})
        self.max_hp = L.hp_max
        self.max_fp = L.fp_max
        self.max_posture = L.posture_max
        self.hp = max(1.0, min(self.max_hp, ratio_hp * self.max_hp))
        self.fp = min(self.max_fp, ratio_fp * self.max_fp)
        self.max_dodges = L.dodge_charges
        self.dodge_charges = min(self.dodge_charges, self.max_dodges) if self.dodge_charges else self.max_dodges
        self.moveset = L.moveset
        self.triggers = TriggerEngine(self, L.triggers)
        self.flags = L.flags
        self.max_ammo = 6 + (2 if "extended_mag" in self.flags else 0)
        self.ammo = min(self.ammo, self.max_ammo)
        self.weapon_anim = DB.families[L.family].get("anim_set", "sword")

    @property
    def active_moveset(self):
        if self.transformed and self.L.beast_moveset is not None:
            return self.L.beast_moveset
        return self.moveset

    # ------------------------------------------------------------------ poder de ataque
    def attack_power(self, move, spec):
        L = self.L
        school = spec.get("scale") if spec else None
        if school is None and move is not None:
            school = move.magic
        if school in ("intelecto", "fe"):
            base = {"fisico": L.spell_power[school]}
        else:
            base = dict(L.weapon_power)
        if self.transformed:
            base = {k: v * 1.3 for k, v in base.items()}
        if spec and spec.get("shot") and self.ammo_special > 0:
            total = sum(base.values())
            base["fogo"] = base.get("fogo", 0.0) + total * 0.6
        return base

    def dynamic_damage_bonus(self, tgt, hit):
        bonus = 0.0
        if getattr(tgt, "marked", 0) > 0:
            bonus += 0.25 + (0.15 if "mark_master" in self.flags else 0.0)
        if getattr(self.world, "night", False) and "night_creature" in self.flags:
            bonus += 0.12
        if self.invisible > 0:
            bonus += 0.5
        if "berserk" in self.flags and self.hp < self.max_hp * 0.4:
            bonus += 0.2
        return bonus

    def build_execution_hit(self, victim, mult):
        base = self.attack_power(None, {})
        m = mult * (1.0 + self.stats.get("execution_mult"))
        return Hit(self, {k: v * m for k, v in base.items()}, posture=0, knockback=3.0, stun=0.6, heavy=True,
                   move_type="execution", tags=("execution",), hitstop=0.2, crit_bonus=0.2)

    def absorb(self, dmg):
        if self.barrier > 0:
            take = min(self.barrier, dmg)
            self.barrier -= take
            dmg -= take
            if self.world:
                self.world.fx.push("barrier_hit", actor=self.id, amount=take)
        return dmg

    # ------------------------------------------------------------------ recursos
    def add_fervor(self, amount):
        self.fervor = min(FERVOR_MAX, self.fervor + amount * (1.0 + self.stats.get("fervor_gain")))

    def ability_cost(self, aid):
        a = DB.abilities[aid]
        return a.get("fp", 0) * max(0.2, 1.0 + self.stats.get("fp_cost_mult"))

    def ability_ready(self, aid):
        return self.cooldowns.get(aid, 0.0) <= 0.0

    def refill(self):
        """Descansar numa Graça: tudo restaurado."""
        self.hp = self.max_hp
        self.fp = self.max_fp
        self.flasks_hp = self.char.flasks_hp
        self.flasks_fp = self.char.flasks_fp
        self.status.clear_negative()
        self.status.buffs.clear()
        self.status._sync()
        self.posture = 0.0
        self.cooldowns.clear()
        self.dodge_charges = self.max_dodges
        self.ammo = self.max_ammo
        self.barrier = 0.0
        if self.transformed:
            self.set_transformed(False)

    # ------------------------------------------------------------------ atualização
    def update(self, dt):
        inp = self.input
        self.triggers.update(dt)
        for k in list(self.cooldowns):
            self.cooldowns[k] = max(0.0, self.cooldowns[k] - dt)
        if self.dodge_charges < self.max_dodges:
            self.dodge_timer += dt
            if self.dodge_timer >= DODGE_RECHARGE:
                self.dodge_timer = 0.0
                self.dodge_charges += 1
        self.since_dodge += dt
        for attr in ("counter_window", "teleport_window", "mist_time", "invisible", "combo_timer"):
            v = getattr(self, attr)
            if v > 0:
                setattr(self, attr, max(0.0, v - dt))
        if self.combo_timer <= 0:
            self.combo_count = 0
        if self.barrier > 0:
            self.barrier_time -= dt
            if self.barrier_time <= 0:
                self.barrier = 0.0
        if self.invisible > 0:
            self.untargetable = True
        elif self.untargetable and not self.invisible:
            self.untargetable = False
        # regeneração de Foco
        if not self.dead and self.max_fp > 0:
            regen = 1.2 + self.stats.get("fp_regen")
            self.fp = min(self.max_fp, self.fp + regen * dt)
        # Fervor decai fora de combate
        if self.world is not None and self.world.combat_heat <= 0 and self.fervor > 0:
            self.fervor = max(0.0, self.fervor - 3.0 * dt)
        # transformação (Lobisomem) consome fúria
        if self.transformed:
            self.transform_time -= dt
            self.fury = max(0.0, self.fury - (2.5 if "long_transform" in self.flags else 5.0) * dt)
            if self.transform_time <= 0 or (self.fury <= 0 and self.transform_time < 99):
                self.set_transformed(False)
        if getattr(self, "marked_targets_decay", None):
            pass
        if self.locked is not None and (not self.locked.alive or self.locked.dead or self.dist_to(self.locked) > 16):
            self.locked = None
        if self.hitstop <= 0 and not self.dead:
            self.handle_input(dt)
        super().update(dt)
        inp.end_frame()

    # ------------------------------------------------------------------ controle
    def move_dir(self):
        mx, mz = self.input.move
        if length(mx, mz) < 0.15:
            return None
        return angle_of(mx, mz)

    def handle_input(self, dt):
        inp = self.input
        a = self.action
        if isinstance(a, ChargeAction) and not inp.holding("heavy"):
            a.release()
        if isinstance(a, BlockAction) and not inp.holding("block"):
            a.holding = False
        if isinstance(a, TimedAction) and a.name == "rest":
            return
        if inp.pressed and "lock" in inp.pressed:
            self.toggle_lock()
        if "lock_next" in inp.pressed:
            self.cycle_lock()
        cmd = inp.peek("dodge", "jump", "light", "heavy", "art", "skill1", "skill2", "skill3", "ultimate",
                       "flask", "flask_fp", "interact")
        if cmd is None:
            if inp.holding("block") and self._free(a) and not isinstance(a, BlockAction) and self.grounded:
                self.start_block()
            return
        handler = getattr(self, "_cmd_" + cmd)
        if handler(a):
            inp.consume(cmd)

    def _free(self, a):
        return a is None or a.interruptible_by_input()

    def _chainable(self, a):
        return a is None or a.interruptible_by_input() or a.can_chain()

    # ---- comandos (devolvem True se consumiram a entrada)
    def _cmd_dodge(self, a):
        if not (a is None or a.can_dodge()):
            return False
        # janela de teletransporte até o inimigo lançado (runa/nó)
        if self.teleport_window > 0 and self.teleport_target is not None and not self.teleport_target.dead:
            self._teleport_to_launched()
            return True
        if self.dodge_charges <= 0:
            return False
        ang = self.move_dir()
        if ang is None:
            ang = self.facing + (math.pi if self.locked is not None else 0.0)
        self.dodge_charges -= 1
        self.dodge_timer = 0.0
        if "mist_dodge" in self.flags:
            act = DodgeAction(ang, distance=4.6, dur=0.38, iframes=0.36, anim="mist")
            self.mist_time = 0.38
        elif self.transformed:
            act = DodgeAction(ang, distance=5.0, dur=0.32, iframes=0.24, anim="pounce")
        else:
            act = DodgeAction(ang, distance=4.0, dur=0.34, iframes=0.24)
        if not self.grounded:
            act.dist_scale = 0.8
        self.set_action(act)
        self.triggers.emit("dodge")
        return True

    def _teleport_to_launched(self):
        t = self.teleport_target
        self.teleport_window = 0.0
        ang = t.angle_to(self)
        x, z = t.x + math.cos(ang) * (t.radius + 0.6), t.z + math.sin(ang) * (t.radius + 0.6)
        if self.world.level.ground_at(x, z) is None:
            x, z = t.x, t.z
        self.world.fx.push("teleport", x0=self.x, y0=self.y, z0=self.z, x=x, y=t.y, z=z, actor=self.id)
        self.x, self.z, self.y = x, z, t.y
        self.vy = 1.5
        self.grounded = False
        self.face(self.angle_to(t))
        self.target = t
        self.set_action(None)

    def _cmd_jump(self, a):
        if not self.grounded:
            return True     # descarta
        if not (a is None or a.interruptible_by_input() or (isinstance(a, MoveAction) and a.can_chain())):
            return False
        if a is not None:
            self.set_action(None)
        self.vy = JUMP_SPEED * (1.0 + self.stats.get("jump_mult"))
        self.grounded = False
        self.y += 0.01
        if self.world:
            self.world.fx.push("jump", actor=self.id, x=self.x, y=self.y, z=self.z)
        return True

    def _attack_context(self, kind):
        """Determina a entrada de combo (L, H, DL, RL, AL, BH, ...) para um ataque."""
        a = self.action
        k = "L" if kind == "light" else "H"
        if self.counter_window > 0 and self.active_moveset.has_start("C" if k == "L" else "C" + k):
            return "C" if k == "L" else "C" + k
        if not self.grounded:
            return "A" + k
        if isinstance(a, DodgeAction) or self.since_dodge < 0.3:
            return "D" + k
        if self.sprinting:
            return "R" + k
        if k == "H" and self.locked is not None:
            md = self.move_dir()
            if md is not None:
                d = abs(angle_diff(self.angle_to(self.locked), md))
                if d > math.radians(120) and self.active_moveset.has_start("BH"):
                    return "BH"
                if d < math.radians(50) and self.active_moveset.has_start("FH"):
                    return "FH"
        return k

    def _try_execution(self):
        best = None
        for e in self.world.enemies_of(self):
            if e.broken > 0 and e.dist_to(self) < 2.4 + e.radius and getattr(e, "executable", True):
                if best is None or e.dist_to(self) < best.dist_to(self):
                    best = e
        if best is None and "backstab_execute" in self.flags:
            for e in self.world.enemies_of(self):
                if (e.kind == "enemy" and not getattr(e, "is_boss", False) and e.dist_to(self) < 1.9 + e.radius
                        and e.is_behind(self, math.radians(90)) and not e.brain.aware()):
                    best = e
                    break
        if best is None:
            return False
        mult = 4.5 if best.broken > 0 else 3.2
        if getattr(best, "is_boss", False):
            mult = 3.0
        self.set_action(ExecuteAction(best, mult=mult))
        return True

    def _start_move(self, move, inp=None, extra=None):
        if move is None:
            return False
        if move.fp > 0:
            cost = move.fp * max(0.2, 1.0 + self.stats.get("fp_cost_mult"))
            if self.fp < cost:
                if self.world:
                    self.world.fx.push("no_resource", what="fp")
                return False
            self.fp -= cost
        if "shot" in move.tags:
            if self.ammo <= 0:
                reload = self.active_moveset.get(self.L.cls.get("reload_move", "sol_reload"))
                if reload is not None:
                    self.set_action(MoveAction(reload, moveset=self.active_moveset))
                    return True
                return False
            self.ammo -= 1
            if self.ammo_special > 0:
                self.ammo_special -= 1
        self.auto_aim(move)
        self.set_action(MoveAction(move, inp=inp, moveset=self.active_moveset, extra=extra))
        self.last_move_id = move.id
        return True

    def auto_aim(self, move):
        if self.locked is not None:
            self.target = self.locked
            return
        md = self.move_dir()
        aim = md if md is not None else self.facing
        best, best_score = None, 1e9
        for e in self.world.enemies_of(self) if self.world else []:
            d = e.dist_to(self)
            if d > 6.0:
                continue
            diff = abs(angle_diff(aim, self.angle_to(e)))
            if diff > math.radians(75):
                continue
            score = d + diff * 2.0
            if score < best_score:
                best, best_score = e, score
        self.target = best
        if best is None and md is not None:
            self.face(md)

    def _cmd_light(self, a):
        return self._attack("light", a)

    def _cmd_heavy(self, a):
        return self._attack("heavy", a)

    def _attack(self, kind, a):
        ms = self.active_moveset
        k = "L" if kind == "light" else "H"
        # continuação do combo
        if isinstance(a, MoveAction):
            if not a.can_chain():
                return False
            nxt = ms.next(a.move, k)
            if nxt is not None:
                if self.grounded or nxt.air or nxt.type in ("air", "slam"):
                    return self._begin_attack(nxt, k)
            if not a.interruptible_by_input():
                return False
        elif isinstance(a, DodgeAction):
            if not a.can_chain():
                return False
        elif isinstance(a, (BlockAction,)):
            if self.counter_window <= 0:
                return False
            a.holding = False
            self.set_action(None)
        elif not self._free(a):
            return False
        if k == "L" and self.grounded and self._try_execution():
            return True
        if k == "H" and self.grounded and "backstab_execute" in self.flags and self._try_execution():
            return True
        ctx = self._attack_context(kind)
        move = ms.start(ctx)
        if move is None:
            move = ms.start(k) if self.grounded else ms.start("A" + k)
        if move is None:
            return True
        if ctx.startswith("C"):
            self.counter_window = 0.0
        return self._begin_attack(move, ctx)

    def _begin_attack(self, move, ctx):
        if move.charge and ctx in ("H", "BH", "FH") and self.input.holding("heavy"):
            rel = self.active_moveset.get(move.charge.get("release"))
            self.auto_aim(move)
            self.set_action(ChargeAction(move, rel, move.charge.get("min", 0.35), move.charge.get("max", 1.1),
                                         self.active_moveset))
            return True
        return self._start_move(move, ctx) or True

    def _use_ability(self, aid, a):
        if not (self._free(a) or (isinstance(a, MoveAction) and a.can_dodge()) or isinstance(a, DodgeAction)):
            return False
        ab = DB.abilities[aid]
        if not self.ability_ready(aid):
            if self.world:
                self.world.fx.push("no_resource", what="cooldown")
            return True
        cost = self.ability_cost(aid)
        if self.fp < cost:
            if self.world:
                self.world.fx.push("no_resource", what="fp")
            return True
        req = ab.get("requires")
        if req == "fury" and self.fury < ab.get("fury", 50):
            self.world.fx.push("no_resource", what="fury")
            return True
        move = self.active_moveset.get(ab["move"]) if not self.transformed or not ab.get("beast_move") else \
            self.active_moveset.get(ab["beast_move"])
        if move is None:
            move = get_move(ab["move"])
        self.fp -= cost
        self.cooldowns[aid] = ab.get("cd", 6.0) * max(0.3, 1.0 + self.stats.get("cooldown_mult"))
        self.auto_aim(move)
        self.set_action(MoveAction(move, moveset=self.active_moveset, extra={"ability": aid}))
        self.triggers.emit("skill", ability=aid)
        return True

    def _cmd_skill1(self, a):
        return self._skill_slot(0, a)

    def _cmd_skill2(self, a):
        return self._skill_slot(1, a)

    def _cmd_skill3(self, a):
        return self._skill_slot(2, a)

    def _skill_slot(self, i, a):
        if i >= len(self.L.abilities):
            return True
        aid, unlocked = self.L.abilities[i]
        if not unlocked:
            if self.world:
                self.world.fx.push("no_resource", what="locked")
            return True
        return self._use_ability(aid, a)

    def _cmd_ultimate(self, a):
        aid, unlocked = self.L.ultimate
        if not unlocked:
            self.world.fx.push("no_resource", what="locked")
            return True
        if self.fervor < FERVOR_MAX:
            self.world.fx.push("no_resource", what="fervor")
            return True
        if not (self._free(a) or (isinstance(a, MoveAction) and a.can_dodge()) or isinstance(a, DodgeAction)):
            return False
        move = self.active_moveset.get(DB.abilities[aid]["move"]) or get_move(DB.abilities[aid]["move"])
        self.fervor = 0.0
        self.auto_aim(move)
        self.set_action(MoveAction(move, moveset=self.active_moveset, extra={"ability": aid, "ultimate": True}))
        self.world.fx.push("ultimate", actor=self.id, ability=aid, x=self.x, y=self.y, z=self.z)
        self.triggers.emit("skill", ability=aid)
        return True

    def _cmd_art(self, a):
        aid = self.L.art
        if aid is None:
            return True
        if not (self._free(a) or (isinstance(a, MoveAction) and a.can_chain()) or isinstance(a, DodgeAction)):
            return False
        art = DB.arts[aid]
        if self.cooldowns.get("art", 0) > 0:
            self.world.fx.push("no_resource", what="cooldown")
            return True
        cost = art.get("fp", 10) * max(0.2, 1.0 + self.stats.get("fp_cost_mult"))
        if self.fp < cost:
            self.world.fx.push("no_resource", what="fp")
            return True
        move = self.active_moveset.get(art["move"]) or get_move(art["move"])
        self.fp -= cost
        self.cooldowns["art"] = art.get("cd", 4.0) * max(0.3, 1.0 + self.stats.get("cooldown_mult"))
        self.auto_aim(move)
        self.set_action(MoveAction(move, moveset=self.active_moveset, extra={"art": aid}))
        self.triggers.emit("art", art=aid)
        return True

    def _cmd_flask(self, a):
        if not self._free(a) or not self.grounded:
            return False
        if self.flasks_hp <= 0:
            self.world.fx.push("no_resource", what="flask")
            return True
        self.flasks_hp -= 1

        def drink():
            self.heal(self.max_hp * self.L.flask_heal * (1.0 + self.stats.get("heal_mult")))
            self.triggers.emit("heal")
        self.set_action(TimedAction("drink", 0.85, drink, at=0.55, name="drink"))
        self.world.fx.push("flask", actor=self.id, flask_kind="hp")
        return True

    def _cmd_flask_fp(self, a):
        if not self._free(a) or not self.grounded:
            return False
        if self.flasks_fp <= 0:
            self.world.fx.push("no_resource", what="flask")
            return True
        self.flasks_fp -= 1

        def drink():
            self.fp = min(self.max_fp, self.fp + self.max_fp * 0.55)
        self.set_action(TimedAction("drink", 0.85, drink, at=0.55, name="drink"))
        self.world.fx.push("flask", actor=self.id, flask_kind="fp")
        return True

    def _cmd_interact(self, a):
        if not self._free(a) or not self.grounded:
            return False
        t = self.find_interactable()
        if t is not None:
            t.interact(self)
        return True

    def find_interactable(self):
        if self.world is None:
            return None
        best, bd = None, 1e9
        for p in self.world.props + self.world.pickups + [x for x in self.world.actors if x.kind == "npc"]:
            if not p.alive or not getattr(p, "interactable", False):
                continue
            if not p.can_interact(self):
                continue
            d = math.hypot(p.x - self.x, p.z - self.z) - getattr(p, "interact_radius", 1.3)
            if d < 0.15 and abs(p.y - self.y) < 1.6 and d < bd:
                best, bd = p, d
        return best

    def start_block(self):
        red = self.L.block_reduction
        self.set_action(BlockAction(red, self.L.block_posture))
        self.target = self.locked

    # ------------------------------------------------------------------ travar alvo
    def toggle_lock(self):
        if self.locked is not None:
            self.locked = None
            return
        cands = [e for e in self.world.enemies_of(self) if e.dist_to(self) < 12]
        if not cands:
            return
        f = self.facing
        self.locked = min(cands, key=lambda e: e.dist_to(self) + abs(angle_diff(f, self.angle_to(e))) * 3)
        self.world.fx.push("lock", target=self.locked.id)

    def cycle_lock(self):
        cands = sorted([e for e in self.world.enemies_of(self) if e.dist_to(self) < 12], key=lambda e: e.id)
        if not cands:
            self.locked = None
            return
        if self.locked in cands:
            i = (cands.index(self.locked) + 1) % len(cands)
        else:
            i = 0
        self.locked = cands[i]

    # ------------------------------------------------------------------ locomoção
    def think(self, dt):
        inp = self.input
        mx, mz = inp.move
        mag = min(1.0, length(mx, mz))
        sprint_hold = inp.hold_time("dodge") > 0.28 and mag > 0.2
        self.sprinting = sprint_hold and self.grounded
        sp = self.speed * (SPRINT_MULT if self.sprinting else 1.0) * (1.25 if self.transformed else 1.0)
        if mag > 0.15:
            dx, dz = norm(mx, mz)
            ctrl = 1.0 if self.grounded else 0.85
            tx, tz = dx * sp * mag, dz * sp * mag
            k = min(1.0, dt * (18.0 if self.grounded else 8.0))
            self.move_x += (tx - self.move_x) * k * ctrl
            self.move_z += (tz - self.move_z) * k * ctrl
            if self.locked is not None and not self.sprinting:
                self.face(self.angle_to(self.locked), dt)
            else:
                self.face(angle_of(dx, dz), dt)
        else:
            k = min(1.0, dt * (20.0 if self.grounded else 3.0))
            self.move_x -= self.move_x * k
            self.move_z -= self.move_z * k
            if self.locked is not None:
                self.face(self.angle_to(self.locked), dt)
        if not self.grounded:
            self.set_anim("jump" if self.vy > 0 else "fall")
        elif mag > 0.15:
            if self.sprinting:
                self.set_anim("sprint")
            elif self.locked is not None and abs(angle_diff(self.facing, angle_of(mx, mz))) > math.radians(60):
                self.set_anim("strafe")
            else:
                self.set_anim("run")
        else:
            self.set_anim("idle")

    def on_land(self, fall_speed):
        super().on_land(fall_speed)
        if fall_speed > 6 and self.world:
            self.world.fx.push("land", actor=self.id, x=self.x, y=self.y, z=self.z, speed=fall_speed)

    def on_fall_void(self):
        if self.dead:
            return
        self.hp -= self.max_hp * 0.15
        if self.world:
            self.world.fx.push("fall_void", actor=self.id)
        if self.hp <= 0:
            self.hp = 0
            self.die(None)
            return
        self.x, self.y, self.z = self.last_safe
        self.vy = 0.0
        self.kx = self.kz = 0.0
        self.grounded = True
        self.iframes = 1.0
        self.set_action(None)

    # ------------------------------------------------------------------ eventos de combate
    def on_dealt_hit(self, tgt, hit):
        if hit.result not in ("hit", "killed", "guardbreak", "blocked"):
            return
        if getattr(tgt, "is_prop", False):
            return
        gain = 2.0 + (4.0 if hit.heavy else 0.0) + (3.0 if hit.crit else 0.0)
        if hit.move_type not in ("rune",):
            self.add_fervor(gain)
            self.combo_count += 1
            self.combo_timer = 2.2
            self.stats_log["max_combo"] = max(self.stats_log["max_combo"], self.combo_count)
        if self.L.resource == "fury":
            self.fury = min(100.0, self.fury + (4.0 if hit.heavy else 2.0))
        if self.L.resource == "fp_on_hit":
            self.fp = min(self.max_fp, self.fp + 1.5)
        if getattr(tgt, "marked", 0) > 0 and "consume_mark" in hit.tags:
            tgt.marked = 0.0
        if hit.move_type == "rune":
            return
        T = self.triggers
        T.emit("hit", target=tgt, hit=hit)
        if hit.crit:
            T.emit("crit", target=tgt, hit=hit)
        if hit.backstab:
            T.emit("backstab", target=tgt, hit=hit)
        if hit.heavy:
            T.emit("heavy_hit", target=tgt, hit=hit)
        if "finisher" in hit.tags:
            T.emit("finisher_hit", target=tgt, hit=hit)
        if hit.launch > 0:
            T.emit("launch_hit", target=tgt, hit=hit)
        if not tgt.grounded:
            T.emit("air_hit", target=tgt, hit=hit)
        if hit.move_type == "counter":
            T.emit("counter_hit", target=tgt, hit=hit)
        if self.transformed or "beast" in hit.tags:
            T.emit("beast_hit", target=tgt, hit=hit)

    def on_took_hit(self, att, hit):
        if hit.result in ("hit", "killed"):
            self.add_fervor(4.0)
            if self.L.resource == "fury":
                self.fury = min(100.0, self.fury + 6.0)
            self.triggers.emit("took_hit", attacker=att, hit=hit)
            if self.hp < self.max_hp * 0.3:
                self.triggers.emit("low_hp", attacker=att, hit=hit)
            if self.world:
                self.world.fx.push("player_hurt", amount=hit.damage, x=self.x, y=self.y, z=self.z)
        elif hit.result == "blocked":
            self.triggers.emit("block", attacker=att, hit=hit)

    def on_evaded(self, hit):
        a = self.action
        if isinstance(a, MoveAction) and "counter_stance" in a.move.tags and not getattr(a, "_countered", False):
            a._countered = True
            mv = self.active_moveset.get("art_contrapostura_hit") or get_move("art_contrapostura_hit")
            if hit.attacker is not None:
                self.target = hit.attacker
            a.chain = MoveAction(mv, moveset=self.active_moveset)
            a.t = a.move.dur
            if self.world:
                self.world.fx.push("perfect_dodge", actor=self.id, x=self.x, y=self.y, z=self.z)
            self.triggers.emit("parry", attacker=hit.attacker, hit=hit, target=hit.attacker)
            return
        if isinstance(a, DodgeAction) and a.t < 0.2 and not a.perfect_triggered:
            a.perfect_triggered = True
            self.stats_log["perfect_dodges"] += 1
            self.add_fervor(10.0)
            self.counter_window = max(self.counter_window, 0.5) if "dodge_counter" in self.flags else self.counter_window
            if self.world:
                self.world.fx.push("perfect_dodge", actor=self.id, x=self.x, y=self.y, z=self.z)
                self.world.slowmo(0.35, 0.22)
            if "perfect_vanish" in self.flags:
                self.invisible = max(self.invisible, 2.0)
            self.triggers.emit("perfect_dodge", attacker=hit.attacker, hit=hit)

    def on_parry_success(self, hit):
        self.counter_window = 0.9
        self.stats_log["parries"] += 1
        self.add_fervor(15.0)
        self.triggers.emit("parry", attacker=hit.attacker, hit=hit, target=hit.attacker)

    def on_broke_posture(self, tgt, hit):
        self.add_fervor(12.0)
        self.triggers.emit("posture_break", target=tgt, hit=hit)

    def on_killed(self, victim):
        self.stats_log["kills"] += 1
        self.triggers.emit("kill", target=victim)

    def on_executed(self, victim, hit):
        self.stats_log["executions"] += 1
        self.add_fervor(20.0)
        self.triggers.emit("execution", target=victim, hit=hit)

    def on_status_proc(self, tgt, name):
        self.triggers.emit("status_proc", target=tgt, status=name)

    def on_enemy_launched(self, enemy):
        if "launch_teleport" in self.flags and enemy.team != self.team:
            self.teleport_window = 0.9
            self.teleport_target = enemy

    def on_dodge_end(self, action):
        self.since_dodge = 0.0

    def on_move_end(self, action, interrupted):
        pass

    def on_steal(self, tgt, t):
        if self.world and self.world.session is not None:
            self.world.session.on_steal(self, tgt)

    # ------------------------------------------------------------------ transformação
    def set_transformed(self, on, time=20.0):
        if on == self.transformed:
            if on:
                self.transform_time = max(self.transform_time, time)
            return
        self.transformed = on
        self.transform_time = time if on else 0.0
        if on:
            self.stats.set_source("beast", {"speed_mult": 0.15, "hp_regen": 2.5 if "beast_regen" in self.flags else 1.0,
                                            "def_flat": 4.0, "poise": 1.0})
            self.scale = 1.25
            self.stagger_resist = 1
            self.fury = max(self.fury, 40.0)
            self.triggers.emit("transform")
        else:
            self.stats.remove_source("beast")
            self.scale = 1.0
            self.stagger_resist = 0
        if self.world:
            self.world.fx.push("transform", actor=self.id, on=on, x=self.x, y=self.y, z=self.z)

    def die(self, killer):
        if self.dead:
            return
        if "last_stand" in self.flags and not getattr(self, "_last_stand_used", False):
            self._last_stand_used = True
            self.hp = self.max_hp * 0.2
            self.iframes = 1.5
            if self.world:
                self.world.fx.push("last_stand", actor=self.id)
            return
        super().die(killer)
