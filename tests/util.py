"""Utilitários de teste: cria sessão/mundo sem janela e simula entradas."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elden.sim.progression.character import Character   # noqa: E402
from elden.sim.session import Session                     # noqa: E402
from elden.sim.world.loader import build_world            # noqa: E402

DT = 1.0 / 60.0


def new_session(cls="guerreiro", name="Teste"):
    c = Character(name, cls)
    for r in list(c.runes)[:1]:
        c.equip_rune(r)
    s = Session(c)
    s.set_flag("intro_velaria")
    return s


def world_for(session, level, spawn="inicio", seed=1):
    return build_world(session, level, spawn, seed=seed)


def step(world, n=1, press=None, hold=(), move=(0.0, 0.0)):
    p = world.player
    for i in range(n):
        st = p.input
        st.begin_frame(DT)
        st.move = move
        for a in list(st.held):
            if a not in hold:
                st.release(a)
        for a in hold:
            if a not in st.held:
                st.press(a)
        if press and i == 0:
            for a in ([press] if isinstance(press, str) else press):
                st.press(a)
        world.step(DT)
        world.fx.drain()


def nearest_enemy(world):
    p = world.player
    es = [e for e in world.enemies() if not e.d.get("dummy")] or world.enemies()
    return min(es, key=lambda e: e.dist_to(p)) if es else None
