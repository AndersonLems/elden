"""Resolução de acertos: esquiva, bloqueio, aparar, crítico, costas, postura, lançamento e reações.

Toda fonte de dano (golpe corpo a corpo, projétil, zona, runa) passa por apply_hit para que as
regras sejam as mesmas para jogador e inimigos.
"""
import math
import random

from .status import ELEMENT_STATUS

PARRY_BASE = 0.16     # janela de aparar perfeito (s) a partir do início do bloqueio
BLOCK_ANGLE = math.radians(150)


class Hit:
    """Pacote de dano já calculado pelo atacante."""

    def __init__(self, attacker, elements, posture=10.0, knockback=2.0, launch=0.0, stun=0.3, heavy=False,
                 unblockable=False, unparryable=False, status=None, tags=(), source=None, crit_bonus=0.0,
                 hitstop=None, dir_angle=None, pos=None, move_type="light", can_crit=True, lifesteal=0.0,
                 fervor=1.0, no_reaction=False):
        self.attacker = attacker
        self.elements = elements            # {"fisico": 12.0, "fogo": 4.0}
        self.posture = posture
        self.knockback = knockback
        self.launch = launch
        self.stun = stun
        self.heavy = heavy
        self.unblockable = unblockable
        self.unparryable = unparryable
        self.status = status or {}
        self.tags = set(tags)
        self.source = source
        self.crit_bonus = crit_bonus
        self.hitstop = hitstop
        self.dir_angle = dir_angle
        self.pos = pos
        self.move_type = move_type
        self.can_crit = can_crit
        self.lifesteal = lifesteal
        self.fervor = fervor
        self.no_reaction = no_reaction
        # preenchidos na resolução
        self.result = None
        self.damage = 0.0
        self.crit = False
        self.backstab = False
        self.combo = None

    def total(self):
        return sum(self.elements.values())


def _type_mult(att, hit):
    s = att.stats
    m = 1.0 + s.get("atk_mult")
    t = hit.move_type
    if t in ("light", "run", "dash"):
        m += s.get("light_mult")
    if t in ("heavy", "charged", "launcher", "slam"):
        m += s.get("heavy_mult")
    if t in ("air", "slam") or "air" in hit.tags:
        m += s.get("air_mult")
    if t == "skill" or "skill" in hit.tags:
        m += s.get("skill_mult")
    if t == "art" or "art" in hit.tags:
        m += s.get("art_mult")
    if t == "counter":
        m += s.get("counter_mult") + 0.5
    if t == "execution":
        m += s.get("execution_mult")
    if "finisher" in hit.tags:
        m += s.get("finisher_mult")
    if "ranged" in hit.tags:
        m += s.get("ranged_mult")
    if "beast" in hit.tags:
        m += s.get("beast_mult")
    if "ruin" in hit.tags:
        m += s.get("ruin_mult")
    if "holy" in hit.tags:
        m += s.get("holy_mult")
    return max(0.05, m)


def compute_damage(att, tgt, hit):
    s = att.stats if att is not None else None
    mult = _type_mult(att, hit) if att is not None else 1.0
    if att is not None:
        if tgt.status.has("sangramento"):
            mult += s.get("vs_bleeding_mult")
        if tgt.broken > 0:
            mult += s.get("vs_broken_mult")
        if tgt.max_hp > 0 and tgt.hp / tgt.max_hp < 0.35:
            mult += s.get("vs_low_hp_mult")
        if "undead" in getattr(tgt, "tags", ()):
            mult += s.get("vs_undead_mult")
        mult += getattr(att, "dynamic_damage_bonus", lambda t, h: 0.0)(tgt, hit)
    # crítico e costas. Contra o jogador: sem crítico aleatório, e "pelas costas" só vale para golpes corpo a corpo
    # (zona/projétil vem de onde está, não do corpo do chefe); empilhados, chegavam a 97% da vida num golpe
    contra_jogador = getattr(tgt, "team", None) == "player"
    corpo_a_corpo = hit.source is None or isinstance(hit.source, str)
    if att is not None and hit.can_crit:
        chance = 0.05 + s.get("crit_chance") + hit.crit_bonus
        if att.world is not None:
            roll = att.world.rng.random()
        else:
            roll = random.random()
        if roll < chance and not contra_jogador:
            hit.crit = True
            mult *= 1.5 + s.get("crit_mult")
        if hit.move_type not in ("execution",) and tgt.is_behind(att) and getattr(tgt, "can_be_backstabbed", True) \
                and (corpo_a_corpo or not contra_jogador):
            hit.backstab = True
            mult *= 1.25 + s.get("backstab_mult") + getattr(tgt, "weak_back", 0.0)
    total = 0.0
    for el, v in hit.elements.items():
        if v <= 0:
            continue
        el_mult = 1.0 + (s.get("elem_" + el) if s else 0.0)
        res = tgt.stats.get("res_" + el) + getattr(tgt, "resist", {}).get(el, 0.0)
        part = v * mult * el_mult * (1.0 - min(0.9, res))
        if el == "fisico":
            part = max(part * 0.25, part - tgt.stats.get("def_flat"))
        total += part
    total *= max(0.1, 1.0 + tgt.stats.get("dmg_taken_mult"))
    # combinações elementais (todas as classes; o Mago e a Convergência amplificam)
    combo = None
    if tgt.status.has("congelamento") and (hit.elements.get("raio", 0) > 0 or hit.heavy):
        combo, cm = "Estilhaçar", 1.4
    elif tgt.status.has("queimadura") and hit.elements.get("gelo", 0) > 0:
        combo, cm = "Choque Térmico", 1.3
    elif tgt.status.has("choque") and hit.elements.get("fogo", 0) > 0:
        combo, cm = "Combustão", 1.3
    elif tgt.status.has("maldicao") and hit.elements.get("sagrado", 0) > 0:
        combo, cm = "Purgação", 1.35
    if combo is not None:
        if att is not None and "elemental_synergy" in getattr(att, "flags", ()):
            cm += 0.25
        total *= cm
        hit.combo = combo
        if combo == "Estilhaçar":
            tgt.status.active.pop("congelamento", None)
    if "holy" in hit.tags and ("undead" in getattr(tgt, "tags", ()) or "corrupt" in getattr(tgt, "tags", ())):
        total *= 1.3
    return max(1.0, total) if hit.total() > 0 else 0.0


def apply_hit(tgt, hit):
    """Aplica o acerto. Resultado em hit.result: evaded, parried, blocked, guardbreak, hit, killed, immune."""
    from .actions import (BlockAction, HurtAction, LaunchedAction, StaggerAction)
    att = hit.attacker
    world = tgt.world
    if tgt.dead or not tgt.alive:
        hit.result = "immune"
        return hit
    if tgt.invulnerable:
        hit.result = "immune"
        return hit
    # esquiva (quadros de invencibilidade)
    if tgt.iframes > 0:
        hit.result = "evaded"
        if hasattr(tgt, "on_evaded"):
            tgt.on_evaded(hit)
        return hit
    ang_from = tgt.angle_to(att) if att is not None else None
    if hit.pos is not None:
        ang_from = math.atan2(hit.pos[2] - tgt.z, hit.pos[0] - tgt.x)
    # bloqueio / aparar
    act = tgt.action
    if isinstance(act, BlockAction) and not hit.unblockable and ang_from is not None:
        diff = abs((ang_from - tgt.facing + math.pi) % math.tau - math.pi)
        if diff <= BLOCK_ANGLE * 0.5:
            window = PARRY_BASE + tgt.stats.get("parry_window")
            if act.t <= window and not hit.unparryable:
                hit.result = "parried"
                act.on_parry(hit)
                if att is not None and not att.dead:
                    broke = att.add_posture(hit.posture * 2.2 + 25)
                    if broke:
                        att.broken = getattr(att, "break_time", 2.5)
                        att.set_action(StaggerAction(att.broken))
                    elif att.stagger_resist < 2 or getattr(att, "parry_staggers", False):
                        att.set_action(HurtAction(0.75, parried=True))
                    else:
                        att.hitstop = 0.18
                if world:
                    world.fx.push("parry", x=tgt.x, y=tgt.y + 1.1, z=tgt.z, angle=ang_from)
                    world.on_parry(tgt, att, hit)
                tgt.hitstop = 0.1
                return hit
            # bloqueio comum
            reduction = min(0.95, act.reduction + tgt.stats.get("block_reduction"))
            dmg = compute_damage(att, tgt, hit) * (1.0 - reduction)
            hit.damage = dmg
            tgt.hp -= tgt.absorb(dmg)
            broke = tgt.add_posture(hit.posture * act.posture_mult)
            push = hit.knockback * 0.6
            tgt.kx += -math.cos(ang_from) * push
            tgt.kz += -math.sin(ang_from) * push
            if world:
                world.fx.push("block", x=tgt.x, y=tgt.y + 1.0, z=tgt.z, angle=ang_from, material="metal")
            if tgt.hp <= 0:
                tgt.die(att)
                hit.result = "killed"
                return hit
            if broke:
                hit.result = "guardbreak"
                tgt.broken = getattr(tgt, "break_time", 2.0)
                tgt.set_action(StaggerAction(tgt.broken))
                if world:
                    world.on_posture_break(tgt, att, hit)
            else:
                hit.result = "blocked"
                act.on_block(hit)
            if att is not None:
                att.hitstop = max(att.hitstop, 0.06)
            return hit
    # dano normal
    dmg = compute_damage(att, tgt, hit)
    hit.damage = dmg
    tgt.hp -= tgt.absorb(dmg)
    tgt.last_hit_by = att
    tgt.flash = 1.0
    tgt.flash_color = (1.0, 1.0, 1.0) if not hit.crit else (1.0, 0.85, 0.4)
    hit.result = "hit"
    # acúmulo de status
    st_mult = 1.0 + (att.stats.get("status_mult") if att is not None else 0.0)
    status = dict(hit.status)
    if att is not None:
        for name, key in (("sangramento", "bleed_add"), ("queimadura", "burn_add"), ("congelamento", "frost_add"),
                          ("choque", "shock_add"), ("maldicao", "curse_add")):
            add = att.stats.get(key)
            if add:
                status[name] = status.get(name, 0.0) + add
    for el, v in hit.elements.items():
        st = ELEMENT_STATUS.get(el)
        if st and v > 0 and el != "fisico":
            status[st] = status.get(st, 0.0) + v * 1.2
    procs = []
    for name, amount in status.items():
        if tgt.status.add_buildup(name, amount * st_mult):
            procs.append(name)
    for name in procs:
        _status_proc(tgt, att, name)
    # postura
    pmult = 1.0 + (att.stats.get("posture_dmg_mult") if att is not None else 0.0)
    broke = tgt.add_posture(hit.posture * pmult)
    # empurrão
    if hit.dir_angle is not None:
        ka = hit.dir_angle
    elif att is not None:
        ka = att.angle_to(tgt)
    else:
        ka = tgt.facing + math.pi
    kb = hit.knockback / max(0.3, tgt.weight)
    if tgt.stagger_resist >= 2 and not broke:
        kb *= 0.15
    tgt.kx += math.cos(ka) * kb
    tgt.kz += math.sin(ka) * kb
    # roubo de vida
    if att is not None and not att.dead:
        ls = att.stats.get("lifesteal") + hit.lifesteal
        if ls > 0:
            att.heal(dmg * ls)
        fp_gain = att.stats.get("fp_on_hit")
        if fp_gain and hasattr(att, "fp"):
            att.fp = min(att.max_fp, att.fp + fp_gain)
    # hitstop
    hs = hit.hitstop if hit.hitstop is not None else (0.09 if hit.heavy else 0.05)
    if hit.crit:
        hs += 0.03
    tgt.hitstop = max(tgt.hitstop, hs)
    if att is not None:
        att.hitstop = max(att.hitstop, hs * 0.8)
    killed = tgt.hp <= 0
    if world:
        world.fx.push("hit", x=tgt.x, y=tgt.y + tgt.height * 0.6, z=tgt.z, angle=ka, damage=dmg, crit=hit.crit,
                      material=tgt.material, heavy=hit.heavy, elements=list(hit.elements), target=tgt.id,
                      backstab=hit.backstab, team=tgt.team, combo=hit.combo)
    if killed:
        tgt.die(att)
        hit.result = "killed"
        if world:
            world.on_hit(att, tgt, hit)
        return hit
    # reação
    if broke:
        tgt.broken = getattr(tgt, "break_time", 2.5)
        tgt.set_action(StaggerAction(tgt.broken))
        if world:
            world.on_posture_break(tgt, att, hit)
    elif hit.no_reaction:
        pass
    elif hit.launch > 0 and tgt.can_be_launched and tgt.stagger_resist < 2 and tgt.super_armor <= 0:
        tgt.set_action(LaunchedAction(hit.launch / max(0.5, tgt.weight)))
    elif isinstance(tgt.action, LaunchedAction):
        tgt.action.juggle_hit(hit)
    elif _flinches(tgt, hit):
        tgt.set_action(HurtAction(hit.stun * (1.4 if hit.heavy else 1.0)))
    if world:
        world.on_hit(att, tgt, hit)
    return hit


def _flinches(tgt, hit):
    if tgt.super_armor > 0 or hit.stun <= 0:
        return False
    act = tgt.action
    if act is not None and getattr(act, "armor_active", lambda: False)():
        return False
    if tgt.stagger_resist == 0:
        return True
    if tgt.stagger_resist == 1:
        return hit.heavy or hit.crit or hit.move_type in ("counter", "execution")
    return False


def _status_proc(tgt, att, name):
    world = tgt.world
    if name == "sangramento":
        burst = tgt.max_hp * (0.08 if getattr(tgt, "is_boss", False) else 0.15) + 8
        tgt.hp -= burst
        if world:
            world.fx.push("status_proc", status=name, x=tgt.x, y=tgt.y + 1.0, z=tgt.z, damage=burst, target=tgt.id)
        if tgt.hp <= 0:
            tgt.die(att)
    elif name == "choque":
        from .actions import HurtAction
        if tgt.stagger_resist < 2:
            tgt.set_action(HurtAction(0.6))
        if world:
            world.fx.push("status_proc", status=name, x=tgt.x, y=tgt.y + 1.0, z=tgt.z, target=tgt.id)
    else:
        if world:
            world.fx.push("status_proc", status=name, x=tgt.x, y=tgt.y + 1.0, z=tgt.z, target=tgt.id)
    tgt.status._sync()
    if world:
        world.on_status_proc(tgt, att, name)
