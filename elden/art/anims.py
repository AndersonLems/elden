"""Biblioteca de animações procedurais (poses por tempo normalizado t em [0, 1]).

Golpes seguem a estrutura antecipação -> impacto -> acompanhamento, alinhada às janelas de acerto
dos dados de combate (o jogo reproduz a animação pelo progresso da ação).
"""
import math

from .rig import Pose, lerp_pose

# quadros gerados por animação e se repete em laço
FRAMES = {
    "idle": (4, True), "walk": (8, True), "run": (8, True), "sprint": (6, True), "strafe": (6, True),
    "fly": (6, True), "sit": (2, True), "channel": (4, True), "block": (2, True), "charge": (4, False),
    "jump": (2, False), "fall": (2, False), "launched": (2, True), "down": (2, False), "getup": (3, False),
    "hurt": (2, False), "stagger": (4, True), "death": (6, False), "dodge": (5, False), "mist": (4, False),
    "drink": (4, False), "interact": (3, False), "block_hit": (2, False), "roar": (5, False), "howl": (5, False),
    "transform": (6, False), "pray": (3, False), "executed": (3, False),
}
DEFAULT_FRAMES = (6, False)

ALIASES = {
    "dash_back": "dodge", "pounce": "lunge_beast", "executed": "stagger", "thrust2": "thrust",
    "flurry_thrust": "flurry", "air_thrust": "air_slash", "air_slash2": "air_slash_b", "air_spin": "spin_air",
    "beast_spin": "spin", "gs_spin": "spin", "sc_spin": "spin", "whip_spin": "spin", "spin_air": "spin_air",
    "gs_slash_r": "slash_r", "gs_slash_l": "slash_l", "gs_slash_down": "slash_down", "gs_slash_up": "slash_up",
    "gs_thrust": "thrust", "sc_sweep_r": "slash_r", "sc_sweep_l": "slash_l", "sc_pull": "pull",
    "whip_r": "slash_r", "whip_l": "slash_l", "whip_up": "slash_up", "whip_down": "slash_down", "whip_pull": "pull",
    "stab_r": "thrust", "stab_l": "thrust_l", "stab_down": "slash_down", "staff_swing": "slash_r", "book_bash": "bash",
    "claw_r": "slash_r", "claw_l": "slash_l", "claw_x": "slash_x", "claw_up": "slash_up", "claw_down": "slash_down",
    "beast_claw_r": "slash_r", "beast_claw_l": "slash_l", "beast_claw_up": "slash_up", "beast_claw_down": "slash_down",
    "book_cast": "cast_forward", "book_cast_big": "cast_up", "book_channel": "channel", "air_cast": "air_slash",
    "imbue": "pray", "drain": "channel", "air_shoot": "shoot", "shoot_barrage": "shoot", "fly_attack": "lunge_beast",
    "dive": "air_down", "dash_attack": "lunge", "flail": "spin", "spit": "cast_forward", "explode_charge": "roar",
    "arm_slam": "slam", "arm_sweep": "slash_r", "vent": "roar", "stomp": "slam", "core_beam": "channel",
    "core_pulse": "roar", "leap_high": "leap_slam", "wing_sweep": "spin", "grab": "lunge", "punch": "thrust",
    "shield_charge": "bash", "cast_sweep": "slash_r", "parry_stance": "block", "vanish": "dodge", "rifle_butt": "slash_up",
    "slash_low": "slash_r", "iai": "iai", "intro": "roar", "lectern": "idle", "hammer": "hammer_work", "read": "read",
}


def ease(t):
    return t * t * (3 - 2 * t)


def keyframes(t, keys):
    """keys: lista de (tempo, Pose). Interpola suavemente."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, p0), (t1, p1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            k = (t - t0) / max(1e-6, t1 - t0)
            return lerp_pose(p0, p1, ease(k))
    return keys[-1][1]


P = Pose

# ---------------------------------------------------------------------------- locomoção
def idle(t):
    b = math.sin(t * math.tau) * 0.5
    return P(bob=b, r_arm_p=12, r_arm_o=12, l_arm_p=8, l_arm_o=12, weapon=55, cape=b * 4, tail=t * 360, flap=t * 360, wings=5)


def walk(t):
    s = math.sin(t * math.tau)
    return P(bob=abs(math.cos(t * math.tau)) * 0.6, r_leg_p=s * 24, l_leg_p=-s * 24, r_knee=max(0, -s) * 25,
             l_knee=max(0, s) * 25, r_arm_p=-s * 16 + 10, l_arm_p=s * 16 + 10, weapon=55, cape=4, tail=t * 720, flap=t * 720)


def run(t):
    s = math.sin(t * math.tau)
    return P(bob=abs(math.cos(t * math.tau)) * 1.2 - 0.6, lean=12, r_leg_p=s * 42, l_leg_p=-s * 42,
             r_knee=max(0, -s) * 55 + 10, l_knee=max(0, s) * 55 + 10, r_arm_p=-s * 32 + 20, l_arm_p=s * 32 + 20,
             r_elbow=45, l_elbow=45, weapon=35, cape=12 + s * 4, tail=t * 900, flap=t * 900)


def sprint(t):
    p = run(t)
    p["lean"] = 22
    p["r_arm_p"] = -30 + math.sin(t * math.tau) * 20
    p["l_arm_p"] = -30 - math.sin(t * math.tau) * 20
    p["weapon"] = 10
    p["cape"] = 22
    return p


def strafe(t):
    s = math.sin(t * math.tau)
    return P(bob=abs(s) * 0.5, r_leg_p=s * 18, l_leg_p=-s * 18, r_knee=15, l_knee=15, r_arm_p=40, l_arm_p=35,
             r_elbow=50, l_elbow=60, weapon=60, crouch=1.0)


def jump(t):
    return P(r_leg_p=30, l_leg_p=-10, r_knee=60, l_knee=40, r_arm_p=50, l_arm_p=60, r_arm_o=25, l_arm_o=25, weapon=60, cape=-10, offset_y=0)


def fall(t):
    return P(r_leg_p=15, l_leg_p=-5, r_knee=30, l_knee=20, r_arm_p=100, l_arm_p=110, r_arm_o=35, l_arm_o=35, weapon=40, cape=-25)


def fly(t):
    return P(bob=math.sin(t * math.tau) * 1.2, flap=t * 360, wings=10 + math.sin(t * math.tau) * 25, r_leg_p=10, l_leg_p=-5,
             r_knee=40, l_knee=30, r_arm_p=30, l_arm_p=30, tail=t * 360)


def dodge(t):
    k = math.sin(t * math.pi)
    return P(crouch=4 * k, lean=35 * k + 5, r_leg_p=50 * k, l_leg_p=-20 * k, r_knee=70 * k, l_knee=50 * k,
             r_arm_p=40 * k, l_arm_p=60 * k, r_elbow=80, l_elbow=80, weapon=10, cape=25 * k)


def mist(t):
    p = dodge(t)
    p["crouch"] = 5
    return p


def hurt(t):
    k = math.sin(min(1.0, t) * math.pi)
    return P(lean=-18 * k, head_tilt=-15 * k, r_arm_p=30 + 20 * k, l_arm_p=30 + 30 * k, r_arm_o=40 * k, l_arm_o=40 * k,
             weapon=50, crouch=k, cape=-10 * k)


def launched(t):
    return P(lean=-35, r_leg_p=50, l_leg_p=30, r_knee=50, l_knee=40, r_arm_p=140, l_arm_p=150, r_arm_o=40, l_arm_o=40, weapon=30, cape=-30)


def down(t):
    return P(crouch=9, lean=-80, r_leg_p=80, l_leg_p=70, r_knee=10, l_knee=20, r_arm_p=150, l_arm_p=170, r_arm_o=50, l_arm_o=50,
             weapon=90, cape=-40)


def getup(t):
    return lerp_pose(down(0), P(crouch=3, lean=20, r_leg_p=40, l_leg_p=-10, r_knee=80, l_knee=40, r_arm_p=30, l_arm_p=30), ease(t)) \
        if t < 0.6 else lerp_pose(P(crouch=3, lean=20, r_leg_p=40, l_leg_p=-10, r_knee=80, l_knee=40, r_arm_p=30, l_arm_p=30), idle(0), ease((t - 0.6) / 0.4))


def stagger(t):
    w = math.sin(t * math.tau) * 6
    return P(lean=28, head_tilt=20, crouch=2, r_arm_p=-5, l_arm_p=-5, r_arm_o=15, l_arm_o=15, r_elbow=5, l_elbow=5, weapon=10,
             r_knee=25, l_knee=25, r_leg_p=15, l_leg_p=10, twist=w, jaw=20)


def death(t):
    if t < 0.35:
        return lerp_pose(hurt(0.5), P(crouch=5, lean=40, r_knee=90, l_knee=90, r_leg_p=60, l_leg_p=60, r_arm_p=10, l_arm_p=10), ease(t / 0.35))
    return lerp_pose(P(crouch=5, lean=40, r_knee=90, l_knee=90, r_leg_p=60, l_leg_p=60, r_arm_p=10, l_arm_p=10),
                     P(crouch=9.5, lean=85, r_leg_p=80, l_leg_p=75, r_knee=10, l_knee=15, r_arm_p=170, l_arm_p=160, r_arm_o=40,
                       l_arm_o=30, weapon=90), ease((t - 0.35) / 0.65))


def block(t):
    return P(crouch=1.5, lean=8, r_arm_p=55, r_arm_o=-10, r_elbow=70, l_arm_p=75, l_arm_o=-20, l_elbow=50, weapon=100,
             weapon_roll=0, r_leg_p=15, l_leg_p=-15, r_knee=20, l_knee=10)


def block_hit(t):
    p = block(t)
    p["lean"] = -12
    p["crouch"] = 2.5
    return p


def charge(t):
    k = min(1.0, t)
    return P(crouch=2.5, lean=-10, twist=-45, r_arm_p=150 * k + 30, r_arm_o=20, r_elbow=40, l_arm_p=60, l_arm_o=10, l_elbow=60,
             weapon=80, r_leg_p=25, l_leg_p=-25, r_knee=30, l_knee=20, glow=k, cape=8)


def drink(t):
    k = math.sin(t * math.pi)
    return P(r_arm_p=40, l_arm_p=60 + 90 * k, l_elbow=90 + 40 * k, l_arm_o=-20, head_tilt=-20 * k, weapon=40)


def interact(t):
    k = math.sin(t * math.pi)
    return P(lean=15 * k, r_arm_p=70 * k + 10, r_elbow=20, weapon=40, crouch=1.5 * k)


def sit(t):
    return P(crouch=6.5, lean=8, r_leg_p=85, l_leg_p=75, r_knee=95, l_knee=100, r_arm_p=40, l_arm_p=40, r_elbow=60, l_elbow=60,
             weapon=95, cape=-20, bob=math.sin(t * math.tau) * 0.2)


def roar(t):
    k = math.sin(min(1.0, t * 1.4) * math.pi * 0.5)
    return P(lean=-20 * k, head_tilt=-30 * k, r_arm_p=60 * k + 20, l_arm_p=60 * k + 20, r_arm_o=60 * k, l_arm_o=60 * k,
             jaw=60 * k, crouch=1.0, weapon=60, cape=-15, wings=40 * k, glow=k)


def transform(t):
    if t < 0.4:
        k = t / 0.4
        return P(crouch=4 * k, lean=40 * k, r_arm_p=0, l_arm_p=0, r_arm_o=5, l_arm_o=5, head_tilt=30 * k)
    k = ease((t - 0.4) / 0.6)
    return lerp_pose(P(crouch=4, lean=40, head_tilt=30), roar(0.8), k)


def pray(t):
    return P(crouch=3.5, lean=10, r_leg_p=80, r_knee=100, l_leg_p=-10, l_knee=90, r_arm_p=80, l_arm_p=80, r_arm_o=-35, l_arm_o=-35,
             r_elbow=60, l_elbow=60, weapon=120, head_tilt=15, glow=0.8)


def read(t):
    return P(r_arm_p=60, l_arm_p=60, r_arm_o=-20, l_arm_o=-20, r_elbow=60, l_elbow=60, head_tilt=20, weapon=120)


def hammer_work(t):
    k = (math.sin(t * math.tau) + 1) * 0.5
    return P(lean=15, r_arm_p=40 + 100 * k, r_elbow=40, weapon=90, l_arm_p=50, l_elbow=40, crouch=1)


# ---------------------------------------------------------------------------- golpes
def swing(t, a, b, c=None, impact=0.45):
    """Antecipação (a) -> impacto (b) -> acompanhamento (c)."""
    c = c or b
    return keyframes(t, [(0.0, idle(0)), (impact * 0.65, a), (impact, b), (min(0.95, impact + 0.25), c), (1.0, c)])


def slash_r(t):
    return swing(t, P(twist=-55, r_arm_p=95, r_arm_o=45, r_elbow=40, weapon=95, lean=-5, l_arm_p=30, r_leg_p=-10, l_leg_p=15, crouch=1),
                 P(twist=45, r_arm_p=85, r_arm_o=-35, r_elbow=5, weapon=100, lean=12, l_arm_p=20, r_leg_p=20, l_leg_p=-15, r_knee=20, crouch=1.5),
                 P(twist=60, r_arm_p=60, r_arm_o=-45, r_elbow=15, weapon=80, lean=10, l_arm_p=15, r_leg_p=20, l_leg_p=-15, crouch=1))


def slash_l(t):
    return swing(t, P(twist=50, r_arm_p=85, r_arm_o=-45, r_elbow=40, weapon=95, lean=-5, l_arm_p=30, crouch=1),
                 P(twist=-45, r_arm_p=85, r_arm_o=40, r_elbow=5, weapon=100, lean=12, l_arm_p=20, l_leg_p=20, r_leg_p=-15, crouch=1.5),
                 P(twist=-60, r_arm_p=60, r_arm_o=50, r_elbow=15, weapon=80, lean=10, l_arm_p=15, crouch=1))


def slash_b(t):
    return slash_l(t)


def slash_down(t):
    return swing(t, P(lean=-15, r_arm_p=175, r_arm_o=10, r_elbow=30, weapon=60, l_arm_p=150, l_elbow=40, r_leg_p=-10, l_leg_p=25, crouch=0.5),
                 P(lean=25, r_arm_p=40, r_arm_o=-5, r_elbow=0, weapon=100, l_arm_p=40, r_leg_p=30, l_leg_p=-20, r_knee=30, crouch=2.5),
                 P(lean=22, r_arm_p=15, r_elbow=0, weapon=95, l_arm_p=20, r_leg_p=30, l_leg_p=-20, r_knee=30, crouch=2.5), impact=0.45)


def slash_up(t):
    return swing(t, P(lean=20, crouch=3, r_arm_p=-5, r_arm_o=10, r_elbow=10, weapon=30, l_arm_p=10, r_leg_p=20, l_leg_p=-20, r_knee=40),
                 P(lean=-15, crouch=0, r_arm_p=165, r_arm_o=0, r_elbow=5, weapon=100, l_arm_p=60, offset_y=1.5, r_leg_p=-10, l_leg_p=10),
                 P(lean=-12, r_arm_p=175, r_elbow=10, weapon=90, l_arm_p=70, offset_y=1.0), impact=0.38)


def slash_x(t):
    return swing(t, P(twist=0, r_arm_p=140, r_arm_o=40, l_arm_p=140, l_arm_o=40, r_elbow=30, l_elbow=30, weapon=90, lean=-8, crouch=1),
                 P(twist=0, r_arm_p=60, r_arm_o=-40, l_arm_p=60, l_arm_o=-40, r_elbow=5, l_elbow=5, weapon=100, lean=15, crouch=2, r_leg_p=20, l_leg_p=-20),
                 P(r_arm_p=40, r_arm_o=-50, l_arm_p=40, l_arm_o=-50, weapon=90, lean=12, crouch=2))


def thrust(t):
    return swing(t, P(twist=-30, r_arm_p=70, r_arm_o=10, r_elbow=110, weapon=100, lean=-5, crouch=1.5, r_leg_p=-15, l_leg_p=20, l_arm_p=40),
                 P(twist=20, r_arm_p=88, r_arm_o=0, r_elbow=0, weapon=90, lean=18, crouch=2.5, r_leg_p=40, l_leg_p=-30, r_knee=30, l_arm_p=-20, l_arm_o=30),
                 P(twist=20, r_arm_p=85, r_elbow=5, weapon=90, lean=15, crouch=2.5, r_leg_p=40, l_leg_p=-30, r_knee=30), impact=0.35)


def thrust_l(t):
    p = thrust(t)
    p["twist"] = -p["twist"]
    return p


def lunge(t):
    p = thrust(t)
    p["lean"] = p["lean"] * 1.4
    p["crouch"] = p["crouch"] + 1
    return p


def lunge_beast(t):
    return swing(t, P(crouch=4, lean=30, r_arm_p=40, l_arm_p=40, r_knee=70, l_knee=70, r_leg_p=30, l_leg_p=30, jaw=10),
                 P(crouch=0, lean=45, r_arm_p=120, l_arm_p=120, r_elbow=10, l_elbow=10, r_leg_p=-40, l_leg_p=-40, offset_y=2, jaw=60, flap=180),
                 P(crouch=1, lean=25, r_arm_p=60, l_arm_p=60, r_leg_p=10, l_leg_p=-10, jaw=20, flap=360), impact=0.45)


def flurry(t):
    k = (t * 4) % 1.0
    side = 1 if int(t * 4) % 2 == 0 else -1
    base = thrust(0.35 + k * 0.1)
    base["twist"] = side * 25
    base["l_arm_p"] = 80 if side < 0 else 30
    base["l_elbow"] = 10 if side < 0 else 60
    return base


def spin(t):
    return P(spin=-t * 360 * 1.2, r_arm_p=85, r_arm_o=70, r_elbow=5, weapon=95, l_arm_p=60, l_arm_o=60, crouch=1.5, lean=8,
             cape=25, glow=1.0, wings=30, flap=t * 720)


def spin_air(t):
    p = spin(t)
    p["r_leg_p"] = 30
    p["r_knee"] = 60
    p["l_knee"] = 50
    return p


def iai(t):
    return keyframes(t, [(0.0, idle(0)),
                         (0.25, P(crouch=3, lean=25, twist=-50, r_arm_p=20, r_arm_o=-30, r_elbow=60, weapon=170, l_arm_p=40, l_arm_o=-30, r_leg_p=40, l_leg_p=-30, r_knee=60)),
                         (0.4, P(crouch=2.5, lean=30, twist=50, r_arm_p=90, r_arm_o=-50, r_elbow=0, weapon=95, l_arm_p=-20, r_leg_p=50, l_leg_p=-40, r_knee=40)),
                         (1.0, P(crouch=2, lean=20, twist=60, r_arm_p=80, r_arm_o=-60, weapon=90, l_arm_p=-10, r_leg_p=45, l_leg_p=-35, r_knee=35))])


def leap_slam(t):
    return keyframes(t, [(0.0, P(crouch=3, lean=20, r_arm_p=20, l_arm_p=20, r_knee=60, l_knee=60, r_leg_p=30, l_leg_p=30)),
                         (0.3, P(lean=-15, r_arm_p=175, l_arm_p=170, r_elbow=20, weapon=60, r_leg_p=40, l_leg_p=-10, r_knee=70, l_knee=60, offset_y=2)),
                         (0.55, P(lean=30, crouch=3.5, r_arm_p=30, l_arm_p=30, weapon=100, r_leg_p=40, l_leg_p=-30, r_knee=50)),
                         (1.0, P(lean=22, crouch=3, r_arm_p=20, l_arm_p=25, weapon=95, r_leg_p=35, l_leg_p=-25, r_knee=45))])


def slam(t):
    return swing(t, P(lean=-10, r_arm_p=170, l_arm_p=170, r_elbow=20, l_elbow=20, weapon=70, crouch=0.5),
                 P(lean=35, crouch=4, r_arm_p=20, l_arm_p=20, weapon=110, r_leg_p=30, l_leg_p=-20, r_knee=60, l_knee=40),
                 P(lean=30, crouch=3.5, r_arm_p=15, l_arm_p=15, weapon=105, r_leg_p=30, l_leg_p=-20, r_knee=55), impact=0.25)


def air_slash(t):
    p = slash_r(t)
    p.update(r_leg_p=30, l_leg_p=-10, r_knee=70, l_knee=50, crouch=0)
    return p


def air_slash_b(t):
    p = slash_l(t)
    p.update(r_leg_p=30, l_leg_p=-10, r_knee=70, l_knee=50, crouch=0)
    return p


def air_down(t):
    return P(lean=25, r_arm_p=20, r_elbow=0, weapon=170, l_arm_p=60, r_leg_p=20, l_leg_p=-10, r_knee=60, l_knee=40, cape=-35)


def bash(t):
    return swing(t, P(twist=-30, l_arm_p=60, l_arm_o=-10, l_elbow=90, lean=-5, r_arm_p=30, crouch=1.5),
                 P(twist=30, l_arm_p=90, l_arm_o=-10, l_elbow=20, lean=25, r_arm_p=20, crouch=2, r_leg_p=35, l_leg_p=-25, r_knee=30),
                 P(twist=25, l_arm_p=80, l_elbow=30, lean=20, crouch=2), impact=0.35)


def kick(t):
    return swing(t, P(lean=-10, r_leg_p=40, r_knee=90, crouch=1, r_arm_p=40, l_arm_p=40),
                 P(lean=-15, r_leg_p=80, r_knee=0, crouch=0.5, r_arm_p=50, l_arm_p=60, r_arm_o=40, l_arm_o=40),
                 P(lean=-10, r_leg_p=60, r_knee=20, crouch=0.5), impact=0.4)


def pull(t):
    return swing(t, P(twist=20, r_arm_p=100, r_arm_o=-10, r_elbow=0, weapon=90, lean=10, glow=1.0, r_leg_p=25, l_leg_p=-15),
                 P(twist=-40, r_arm_p=40, r_arm_o=30, r_elbow=90, weapon=60, lean=-20, glow=0.4, r_leg_p=-20, l_leg_p=25),
                 P(twist=-40, r_arm_p=30, r_elbow=100, weapon=60, lean=-15, glow=0.0), impact=0.4)


def cast_forward(t):
    return swing(t, P(twist=-25, r_arm_p=60, r_elbow=70, l_arm_p=40, l_elbow=60, lean=-5, glow=0.5),
                 P(twist=15, r_arm_p=88, r_elbow=0, l_arm_p=60, l_elbow=20, lean=12, glow=1.0, r_leg_p=25, l_leg_p=-15),
                 P(twist=10, r_arm_p=80, r_elbow=10, l_arm_p=40, lean=8, glow=0.6), impact=0.35)


def cast_up(t):
    return swing(t, P(crouch=2, r_arm_p=40, l_arm_p=40, r_elbow=60, l_elbow=60, lean=10, glow=0.6),
                 P(crouch=0, r_arm_p=170, l_arm_p=165, r_arm_o=25, l_arm_o=25, r_elbow=5, l_elbow=5, lean=-12, glow=1.0, head_tilt=-20, wings=40),
                 P(r_arm_p=160, l_arm_p=155, r_arm_o=30, l_arm_o=30, lean=-10, glow=0.8), impact=0.4)


def channel(t):
    w = math.sin(t * math.tau) * 4
    return P(r_arm_p=95 + w, l_arm_p=95 - w, r_arm_o=-10, l_arm_o=-10, r_elbow=0, l_elbow=0, lean=8, crouch=1.5, glow=1.0,
             r_leg_p=20, l_leg_p=-20, cape=10 + w, wings=20, flap=t * 360, jaw=30)


def shoot(t):
    return swing(t, P(twist=-20, l_arm_p=85, l_arm_o=-10, l_elbow=10, r_arm_p=70, r_elbow=60, lean=-3, crouch=1),
                 P(twist=-15, l_arm_p=92, l_arm_o=-5, l_elbow=0, r_arm_p=75, r_elbow=55, lean=-12, crouch=1.2, glow=1.0),
                 P(twist=-15, l_arm_p=88, l_elbow=5, r_arm_p=70, r_elbow=60, lean=-5, crouch=1), impact=0.25)


def shoot_heavy(t):
    return keyframes(t, [(0.0, idle(0)),
                         (0.3, P(crouch=2.5, twist=-30, l_arm_p=90, l_elbow=0, r_arm_p=85, r_elbow=40, lean=0, r_leg_p=40, l_leg_p=-20, r_knee=60)),
                         (0.45, P(crouch=2.5, twist=-30, l_arm_p=100, l_elbow=0, r_arm_p=90, r_elbow=40, lean=-18, r_leg_p=40, l_leg_p=-20, r_knee=60, glow=1)),
                         (1.0, P(crouch=2, twist=-25, l_arm_p=90, l_elbow=5, r_arm_p=80, r_elbow=40, lean=-6, r_leg_p=35, l_leg_p=-15, r_knee=50))])


def reload(t):
    k = math.sin(t * math.pi)
    return P(l_arm_p=50, l_elbow=60, r_arm_p=40 + 30 * k, r_elbow=90, head_tilt=20 * k, lean=10 * k, weapon=60)


def throw(t):
    return swing(t, P(twist=-40, r_arm_p=170, r_arm_o=30, r_elbow=70, lean=-12, l_arm_p=60, r_leg_p=-15, l_leg_p=20),
                 P(twist=35, r_arm_p=70, r_arm_o=-20, r_elbow=0, lean=18, l_arm_p=10, r_leg_p=25, l_leg_p=-20, r_knee=20),
                 P(twist=40, r_arm_p=40, r_elbow=10, lean=15), impact=0.4)


def bite(t):
    return swing(t, P(lean=-10, jaw=40, crouch=2, r_arm_p=40, l_arm_p=40, head_tilt=-15),
                 P(lean=40, jaw=0, crouch=2.5, r_arm_p=80, l_arm_p=80, r_elbow=40, l_elbow=40, head_tilt=20, r_leg_p=30, l_leg_p=-20),
                 P(lean=25, jaw=10, crouch=2), impact=0.4)


def execute(t):
    return keyframes(t, [(0.0, idle(0)),
                         (0.35, P(lean=-10, r_arm_p=180, r_elbow=10, weapon=180, l_arm_p=170, crouch=0.5)),
                         (0.5, P(lean=40, crouch=4, r_arm_p=60, r_elbow=0, weapon=170, l_arm_p=60, r_leg_p=40, l_leg_p=-30, r_knee=70)),
                         (1.0, P(lean=35, crouch=4, r_arm_p=50, weapon=170, l_arm_p=50, r_leg_p=40, l_leg_p=-30, r_knee=70))])


ANIMS = {k: v for k, v in globals().items() if callable(v) and not k.startswith("_") and k not in
         ("ease", "keyframes", "lerp_pose", "Pose", "P", "swing", "pose_for")}


def pose_for(name, t, two_handed=False):
    fn = ANIMS.get(name) or ANIMS.get(ALIASES.get(name, ""), None) or slash_r
    p = fn(t)
    if two_handed and name not in ("block", "drink", "throw", "shoot", "shoot_heavy", "reload", "bash"):
        # mão esquerda acompanha a direita no cabo
        p["l_arm_p"] = p["r_arm_p"] - 8
        p["l_arm_o"] = -p["r_arm_o"] * 0.4
        p["l_elbow"] = p["r_elbow"] + 15
    return p
