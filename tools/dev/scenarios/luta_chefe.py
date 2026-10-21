"""Cenário de captura: o chefe da arena luta de verdade (IA ligada) contra o jogador imortal; as fases são forçadas
pela vida do chefe e cada uma é fotografada, até a morte e a revelação do portal/Graça.

Uso: SPAWN=entrada ELDEN_OFFSCREEN=1 python3 tools/dev/tour.py <saida> <arena> '[]' tools/dev/scenarios/luta_chefe.py
"""
from elden.sim.ai.bosses.base import Boss

w.paused_ai = False
boss = next(e for e in w.enemies() if isinstance(e, Boss))
p.x, p.z = boss.x, boss.z - 4.0
p.invulnerable = True
roteiro = {"t": 0.0, "i": 0}
# (segundos de luta, fração de vida a aplicar antes, nome da captura)
passos = [(6.0, None, "fase1"), (6.0, 0.6, "fase2"), (7.0, 0.3, "fase3"), (3.0, 0.0, "vitoria")]


def lutar(task):
    dt = globalClock.getDt()
    roteiro["t"] += dt
    p.hp = p.max_hp
    if roteiro["i"] >= len(passos):
        app.quit()
        return task.done
    dur, frac, nome = passos[roteiro["i"]]
    if roteiro["t"] < dt * 1.5 and frac is not None and not boss.dead:
        if frac <= 0:
            boss.hp = 0
            boss.die(p)
        else:
            boss.hp = boss.max_hp * frac
    if roteiro["t"] >= dur:
        shot(nome)
        roteiro["t"] = 0.0
        roteiro["i"] += 1
    return task.cont


from direct.showbase.ShowBaseGlobal import globalClock   # noqa: E402
st["t"] = -999.0
app.base.taskMgr.add(lutar, "luta_chefe")
