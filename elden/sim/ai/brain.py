"""Cérebro dos inimigos: máquina de estados com percepção, navegação, posicionamento e escolha de ataques.

Estados: patrulha, investigação, perseguição, posicionamento (engajado), ataque, recuperação,
recuo, fuga e retorno. Reações: bloquear/aparar e esquivar quando o jogador ataca por perto.

Comportamentos (data/enemies.json -> "behavior") ajustam a forma de lutar:
  grunt (pressão simples), pack (cerca e flanqueia), duelist (entra e sai, rápido), kiter (mantém
  distância e atira), summoner (invoca e foge), charger (investida em linha), erratic (imprevisível
  com avisos legíveis), guardian (defende e contra-ataca), armored (lento, armadura, ponto fraco nas
  costas), flyer (voa e mergulha), turret (fixo).
"""
import math

from ...core.mathutil import angle_of, angle_diff, dir_of, norm, clamp
from ..combat.actions import MoveAction, BlockAction, DodgeAction, TimedAction
from ..combat.moves import get_move
from .navigation import nav_for

BEHAVIORS = {
    "grunt": dict(pref=1.4, strafe=0.35, dodge=0.0, block=0.0, aggression=0.75, flank=0.0, retreat_hp=0.0, wait=(0.4, 1.2)),
    "pack": dict(pref=2.4, strafe=0.7, dodge=0.15, block=0.0, aggression=0.8, flank=1.0, retreat_hp=0.0, wait=(0.3, 0.9)),
    "duelist": dict(pref=2.6, strafe=0.8, dodge=0.45, block=0.0, aggression=0.85, flank=0.4, retreat_hp=0.0, wait=(0.2, 0.7)),
    "kiter": dict(pref=6.5, strafe=0.6, dodge=0.3, block=0.0, aggression=0.7, flank=0.0, retreat_hp=0.0, wait=(0.6, 1.4)),
    "summoner": dict(pref=7.5, strafe=0.5, dodge=0.2, block=0.0, aggression=0.6, flank=0.0, retreat_hp=0.0, wait=(0.8, 1.6), blink=True),
    "charger": dict(pref=5.0, strafe=0.3, dodge=0.0, block=0.0, aggression=0.9, flank=0.0, retreat_hp=0.0, wait=(0.6, 1.2)),
    "erratic": dict(pref=2.0, strafe=0.9, dodge=0.1, block=0.0, aggression=0.8, flank=0.2, retreat_hp=0.0, wait=(0.2, 1.0), jitter=True),
    "guardian": dict(pref=1.8, strafe=0.5, dodge=0.0, block=0.55, aggression=0.6, flank=0.0, retreat_hp=0.0, wait=(0.5, 1.2), parry=0.35),
    "armored": dict(pref=1.6, strafe=0.1, dodge=0.0, block=0.0, aggression=0.7, flank=0.0, retreat_hp=0.0, wait=(0.8, 1.6)),
    "flyer": dict(pref=3.0, strafe=0.9, dodge=0.2, block=0.0, aggression=0.75, flank=0.5, retreat_hp=0.0, wait=(0.4, 1.0)),
    "turret": dict(pref=8.0, strafe=0.0, dodge=0.0, block=0.0, aggression=0.8, flank=0.0, retreat_hp=0.0, wait=(1.0, 1.8), static=True),
    "coward": dict(pref=3.0, strafe=0.5, dodge=0.3, block=0.0, aggression=0.5, flank=0.0, retreat_hp=0.35, wait=(0.5, 1.2)),
}

TOKENS = {"melee": 2, "ranged": 2}


class Brain:
    def __init__(self, enemy, behavior="grunt", overrides=None):
        self.e = enemy
        self.behavior = behavior
        self.p = dict(BEHAVIORS.get(behavior, BEHAVIORS["grunt"]))
        self.p.update(overrides or {})
        self.state = "patrol"
        self.state_t = 0.0
        self.home = (enemy.x, enemy.z)
        self.patrol_points = []
        self.patrol_i = 0
        self.target = None
        self.last_seen = None
        self.lost_t = 0.0
        self.path = None
        self.path_t = 0.0
        self.wait = 0.0
        self.attack_cds = {}
        self.react_cd = 0.0
        self.token = None
        self.strafe_dir = 1 if enemy.id % 2 else -1
        self.slot = (enemy.id * 2.399) % math.tau     # ângulo de flanqueio (proporção áurea)
        self.chosen = None
        self.alerted = False
        self.jitter_t = 0.0
        self.investigate_point = None

    # ------------------------------------------------------------------ utilidades
    def aware(self):
        return self.alerted

    def set_state(self, s):
        if s != self.state:
            self.state = s
            self.state_t = 0.0
            if s not in ("attack",):
                self.release_token()

    def alert(self, target):
        w = self.e.world
        if target is None or (w is not None and getattr(target, "dead", False)):
            return
        first = not self.alerted
        self.target = target
        self.e.target = target
        self.alerted = True
        self.last_seen = (target.x, target.z)
        if self.state in ("patrol", "investigate", "return", "idle"):
            self.set_state("chase")
            if first and w is not None:
                w.fx.push("alert", actor=self.e.id, x=self.e.x, y=self.e.y + self.e.height * self.e.scale + 0.3, z=self.e.z)
                # alerta inimigos próximos (grupo)
                for o in w.enemies():
                    if o is not self.e and o.dist_to(self.e) < 6.0 and hasattr(o, "brain") and not o.brain.alerted:
                        o.brain.target = target
                        o.brain.e.target = target
                        o.brain.alerted = True
                        o.brain.set_state("chase")

    def acquire_token(self, kind):
        w = self.e.world
        if getattr(self.e, "is_boss", False) or self.e.elite:
            self.token = kind
            return True
        pool = w.__dict__.setdefault("ai_tokens", dict(TOKENS))
        if self.token == kind:
            return True
        if pool.get(kind, 0) > 0:
            pool[kind] -= 1
            self.token = kind
            return True
        return False

    def release_token(self):
        if self.token is None:
            return
        w = self.e.world
        if w is not None and not getattr(self.e, "is_boss", False) and not self.e.elite:
            pool = w.__dict__.setdefault("ai_tokens", dict(TOKENS))
            pool[self.token] = min(TOKENS[self.token], pool.get(self.token, 0) + 1)
        self.token = None

    def can_see(self, t):
        e = self.e
        if t is None or getattr(t, "dead", True) or getattr(t, "untargetable", False):
            return False
        d = e.dist_to(t)
        if d > e.aggro:
            return False
        # visão em cone de 220° (de costas só percebe muito perto)
        if d > 2.5 and not self.alerted:
            diff = abs(angle_diff(e.facing, e.angle_to(t)))
            if diff > math.radians(110):
                return False
        return e.world.level.line_clear(e.x, e.z, t.x, t.z, e.y + 1.2)

    # ------------------------------------------------------------------ locomoção
    def steer_to(self, x, z, speed_mult=1.0, dt=0.016, face=True):
        e = self.e
        w = e.world
        dx, dz = x - e.x, z - e.z
        d = math.hypot(dx, dz)
        if d < 0.15:
            e.move_x = e.move_z = 0.0
            return True
        flying = getattr(e, "flying", False)
        if not flying and not w.level.line_clear(e.x, e.z, x, z, e.y + 0.3):
            self.path_t -= dt
            if self.path is None or self.path_t <= 0:
                self.path = nav_for(w.level).find(e.x, e.z, x, z)
                self.path_t = 0.8 + (e.id % 5) * 0.1
            if self.path:
                while len(self.path) > 1 and math.hypot(self.path[0][0] - e.x, self.path[0][1] - e.z) < 0.5:
                    self.path.pop(0)
                px, pz = self.path[0]
                dx, dz = px - e.x, pz - e.z
                d = math.hypot(dx, dz) or 1.0
        else:
            self.path = None
        sp = e.speed * speed_mult
        nx, nz = dx / d, dz / d
        e.move_x += (nx * sp - e.move_x) * min(1.0, dt * 10)
        e.move_z += (nz * sp - e.move_z) * min(1.0, dt * 10)
        if face:
            e.face(angle_of(nx, nz), dt)
        return False

    def stop(self, dt):
        e = self.e
        k = min(1.0, dt * 10)
        e.move_x -= e.move_x * k
        e.move_z -= e.move_z * k

    # ------------------------------------------------------------------ ciclo
    def update(self, dt):
        e = self.e
        self.state_t += dt
        self.react_cd = max(0.0, self.react_cd - dt)
        for k in list(self.attack_cds):
            self.attack_cds[k] -= dt
            if self.attack_cds[k] <= 0:
                del self.attack_cds[k]
        w = e.world
        player = w.player
        decoys = [c for c in w.misc if getattr(c, "is_decoy", lambda: False)() and c.team != e.team]
        if decoys and self.alerted:
            self.target = decoys[0]
        elif self.target is not None and getattr(self.target, "kind", "") == "clone":
            self.target = player
        if not self.alerted and player is not None and not player.dead:
            if self.can_see(player) or (e.dist_to(player) < 2.0 and not player.untargetable):
                self.alert(player)
        t = self.target
        if t is not None and (getattr(t, "dead", False) or not getattr(t, "alive", True)):
            self.target = None
            e.target = None
            self.alerted = False
            self.set_state("return")
            t = None
        getattr(self, "st_" + self.state)(dt, t)
        e.target = t if t is not None else e.target
        # animação de locomoção
        sp = math.hypot(e.move_x, e.move_z)
        if e.action is None:
            if getattr(e, "flying", False):
                e.set_anim("fly")
            elif sp > e.speed * 0.6:
                e.set_anim("run")
            elif sp > 0.3:
                e.set_anim("walk")
            else:
                e.set_anim("idle")

    # ------------------------------------------------------------------ estados
    def st_idle(self, dt, t):
        self.stop(dt)

    def st_patrol(self, dt, t):
        e = self.e
        if self.p.get("static"):
            self.stop(dt)
            return
        if not self.patrol_points:
            r = 2.5
            hx, hz = self.home
            self.patrol_points = [(hx + math.cos(a) * r, hz + math.sin(a) * r) for a in (0.0, 2.1, 4.2)]
        if self.wait > 0:
            self.wait -= dt
            self.stop(dt)
            return
        px, pz = self.patrol_points[self.patrol_i % len(self.patrol_points)]
        if e.world.level.ground_at(px, pz) is None:
            self.patrol_i += 1
            return
        if self.steer_to(px, pz, 0.4, dt) or self.state_t > 6:
            self.patrol_i += 1
            self.state_t = 0.0
            self.wait = 1.0 + (e.id % 3) * 0.6

    def st_investigate(self, dt, t):
        if self.investigate_point is None or self.state_t > 5:
            self.set_state("return")
            return
        if self.steer_to(*self.investigate_point, 0.6, dt):
            self.stop(dt)

    def st_return(self, dt, t):
        e = self.e
        self.alerted = False
        if self.steer_to(*self.home, 0.7, dt) or self.state_t > 10:
            e.hp = min(e.max_hp, e.hp + e.max_hp * 0.5)
            self.set_state("patrol")

    def st_chase(self, dt, t):
        e = self.e
        if t is None:
            self.set_state("return")
            return
        d = e.dist_to(t)
        if self.can_see(t):
            self.last_seen = (t.x, t.z)
            self.lost_t = 0.0
        else:
            self.lost_t += dt
            if self.lost_t > 6.0:
                self.investigate_point = self.last_seen
                self.set_state("investigate")
                return
        hx, hz = self.home
        if math.hypot(e.x - hx, e.z - hz) > e.leash and d > 6:
            self.set_state("return")
            return
        if d <= self.p["pref"] + 1.2 or self.p.get("static"):
            self.set_state("engage")
            return
        gx, gz = self.last_seen if self.last_seen else (t.x, t.z)
        self.steer_to(gx, gz, 1.0, dt)

    def _engage_pos(self, t):
        """Ponto desejado ao redor do alvo (distância preferida, flanqueio)."""
        e = self.e
        pref = self.p["pref"]
        if self.p["flank"] > 0:
            ang = t.facing + math.pi * 0.5 * self.strafe_dir + self.slot * 0.3 * self.p["flank"]
        else:
            ang = t.angle_to(e)
        return t.x + math.cos(ang) * pref, t.z + math.sin(ang) * pref

    def st_engage(self, dt, t):
        e = self.e
        if t is None:
            self.set_state("return")
            return
        d = e.dist_to(t)
        if d > max(self.p["pref"] + 4.0, 7.0) and not self.p.get("static"):
            self.set_state("chase")
            return
        if self.p["retreat_hp"] and e.hp < e.max_hp * self.p["retreat_hp"] and self.state_t > 0.5:
            self.set_state("flee")
            return
        # escolher ataque
        if self.wait <= 0:
            choice = self.choose_attack(d, t)
            if choice is not None:
                kind = "ranged" if choice.get("ranged") else "melee"
                if self.acquire_token(kind):
                    self.start_attack(choice, t)
                    return
                self.wait = 0.3
        else:
            self.wait -= dt * (0.6 + self.p["aggression"])
        # posicionamento
        if self.p.get("static"):
            self.stop(dt)
            e.face(e.angle_to(t), dt)
            return
        if self.p.get("jitter"):
            self.jitter_t -= dt
            if self.jitter_t <= 0:
                self.jitter_t = 0.3 + e.world.rng.random() * 0.6
                self.strafe_dir = -self.strafe_dir if e.world.rng.random() < 0.5 else self.strafe_dir
        pref = self.p["pref"]
        if d < pref - 1.2 and self.behavior in ("kiter", "summoner", "turret"):
            ang = t.angle_to(e)
            gx, gz = t.x + math.cos(ang) * pref, t.z + math.sin(ang) * pref
            if e.world.level.ground_at(gx, gz) is None:
                gx, gz = e.x, e.z
            self.steer_to(gx, gz, 0.9, dt, face=False)
            e.face(e.angle_to(t), dt)
            if self.p.get("blink") and d < 2.4 and self.react_cd <= 0:
                self.blink_away(t)
            return
        if abs(d - pref) > 1.0:
            gx, gz = self._engage_pos(t)
            self.steer_to(gx, gz, 0.85, dt, face=False)
        else:
            # circular o alvo
            if e.world.rng.random() < dt * 0.3:
                self.strafe_dir = -self.strafe_dir
            tang = t.angle_to(e) + math.pi * 0.5 * self.strafe_dir
            sp = e.speed * 0.45 * self.p["strafe"]
            fx, fz = dir_of(tang)
            nx, nz = e.x + fx * 0.5, e.z + fz * 0.5
            if e.world.level.ground_at(nx, nz) is None or e.world.level.is_hazard(nx, nz):
                self.strafe_dir = -self.strafe_dir
                fx, fz = -fx, -fz
            e.move_x += (fx * sp - e.move_x) * min(1.0, dt * 8)
            e.move_z += (fz * sp - e.move_z) * min(1.0, dt * 8)
        e.face(e.angle_to(t), dt)

    def st_attack(self, dt, t):
        # a ação de golpe controla o ator; ao terminar volta a 'recover'
        self.set_state("recover")

    def st_recover(self, dt, t):
        e = self.e
        self.release_token()
        lo, hi = self.p["wait"]
        self.wait = lo + (hi - lo) * e.world.rng.random()
        if t is not None and self.behavior in ("duelist", "pack", "flyer") and e.dist_to(t) < 2.5 \
                and e.world.rng.random() < 0.5:
            # recua após atacar (bate e sai)
            ang = t.angle_to(e) + (e.world.rng.random() - 0.5)
            e.set_action(DodgeAction(ang, distance=2.6, dur=0.35, iframes=0.0, anim="dash_back"))
        self.set_state("engage" if t is not None else "return")

    def st_flee(self, dt, t):
        e = self.e
        if t is None or self.state_t > 3.0:
            self.set_state("engage" if t is not None else "return")
            return
        ang = t.angle_to(e)
        gx, gz = e.x + math.cos(ang) * 3, e.z + math.sin(ang) * 3
        if e.world.level.ground_at(gx, gz) is None:
            self.set_state("engage")
            return
        self.steer_to(gx, gz, 1.0, dt)

    # ------------------------------------------------------------------ ataques
    def choose_attack(self, d, t):
        e = self.e
        rng = e.world.rng
        opts = []
        for i, atk in enumerate(e.attacks):
            if self.attack_cds.get(i, 0) > 0:
                continue
            lo, hi = atk.get("range", [0, 2])
            if not (lo <= d <= hi):
                continue
            if atk.get("airborne_target") and t.grounded:
                continue
            if atk.get("min_hp_frac") is not None and e.hp / e.max_hp > atk["min_hp_frac"]:
                continue
            if atk.get("summon") and len([o for o in e.world.enemies() if getattr(o, "summoned", False)]) >= atk.get("max_summons", 3):
                continue
            if atk.get("behind_only") and not t.is_behind(e):
                continue
            if not e.world.level.line_clear(e.x, e.z, t.x, t.z, e.y + 0.9):
                continue
            opts.append((atk.get("weight", 1.0), i, atk))
        if not opts:
            return None
        if rng.random() > self.p["aggression"] + 0.2:
            return None
        total = sum(o[0] for o in opts)
        r = rng.random() * total
        for wgt, i, atk in opts:
            r -= wgt
            if r <= 0:
                atk = dict(atk)
                atk["_i"] = i
                return atk
        return None

    def start_attack(self, atk, t):
        e = self.e
        move = get_move(atk["move"])
        self.attack_cds[atk["_i"]] = atk.get("cd", 1.5)
        e.face(e.angle_to(t))
        self.chosen = atk
        self.set_state("attack")
        e.set_action(MoveAction(move, target=t))
        if move.d.get("telegraph", True) and e.world is not None:
            e.world.fx.push("enemy_windup", actor=e.id, move=move.id, x=e.x, y=e.y + e.height * e.scale, z=e.z,
                            unblockable=any(h.get("unblockable") for h in move.hits),
                            time=move.hits[0]["t"][0] if move.hits else 0.3)

    def _sem_portas(self, x0, z0, x1, z1, y):
        """O segmento não atravessa props sólidos (portas fechadas, névoa da arena)."""
        w = self.e.world
        n = max(2, int(math.hypot(x1 - x0, z1 - z0) * 4))
        for i in range(n + 1):
            px, pz = x0 + (x1 - x0) * i / n, z0 + (z1 - z0) * i / n
            for s in w.solids:
                if s.solid and s.contains_point(px, y + 1.0, pz):
                    return False
        return True

    def blink_away(self, t):
        e = self.e
        w = e.world
        for k in range(8):
            ang = t.angle_to(e) + (k - 4) * 0.4
            x, z = t.x + math.cos(ang) * 7.0, t.z + math.sin(ang) * 7.0
            g = w.level.ground_at(x, z)
            # mesmo nível do chão atual: topo de parede também é "andável" e virava destino
            if g is None or abs(g - e.y) > 0.5:
                continue
            if w.level.walkable(int(x), int(z)) and w.level.line_clear(t.x, t.z, x, z) and \
                    self._sem_portas(t.x, t.z, x, z, e.y):
                w.fx.push("teleport", x0=e.x, y0=e.y, z0=e.z, x=x, y=g, z=z, actor=e.id)
                e.x, e.z = x, z
                e.y = g
                self.react_cd = 3.0
                return True
        return False

    # ------------------------------------------------------------------ reações ao jogador
    def on_player_attack(self, player, action):
        """Chamado quando o jogador inicia um golpe por perto: chance de bloquear, aparar ou esquivar."""
        e = self.e
        if e.dead or e.action is not None or self.react_cd > 0 or not self.alerted:
            return
        if e.dist_to(player) > 3.2 or e.broken > 0:
            return
        rng = e.world.rng
        heavy = action.move.type in ("heavy", "charged", "launcher", "slam")
        if self.p.get("parry", 0) > 0 and not heavy and rng.random() < self.p["parry"]:
            e.face(e.angle_to(player))
            e.set_action(BlockAction(reduction=0.8, posture_mult=0.8))
            e.block_timer = 0.8
            self.react_cd = 2.2
            return
        if self.p["block"] > 0 and rng.random() < self.p["block"] * (0.5 if heavy else 1.0):
            e.face(e.angle_to(player))
            act = BlockAction(reduction=0.8, posture_mult=0.9)
            act.t = 0.3     # bloqueio comum (sem aparar)
            e.set_action(act)
            e.block_timer = 1.0
            self.react_cd = 1.5
            return
        if self.p["dodge"] > 0 and rng.random() < self.p["dodge"]:
            ang = player.angle_to(e) + (rng.random() - 0.5) * 1.6
            e.set_action(DodgeAction(ang, distance=3.0, dur=0.32, iframes=0.25, anim="dodge"))
            self.react_cd = 1.8
