"""Bot de teste de chefes: aproxima pelo A*, contorna obstáculos (props sólidos) e ataca com golpes leves.

O bot é imortal: cada morte é interceptada e contada (`mortes`), e o dano recebido é somado para medir a pressão do chefe.
"""
import math

from util import new_session, world_for, step, DT
from elden.sim.ai.bosses.base import Boss
from elden.sim.ai.navigation import nav_for
from elden.sim.progression import grace_tree
from elden.core.data import DB


def preparar(c, ato):
    """Progresso típico ao chegar no chefe do ato: arma no nível que o ferreiro libera (+1 por chefe principal)
    e cerca de 5 níveis por ato gastos em nós de CORPO, na ordem da árvore."""
    c.weapon_levels[c.weapon] = min(5, ato)
    c.grace = 10 ** 7
    while c.level < 1 + (ato - 1) * 5 and c.level_up():
        pass
    for nid in [n for n in grace_tree.nodes() if n.startswith("c_")]:
        if c.points_available <= 0:
            break
        grace_tree.unlock(c, nid)
    c.grace = 0


class Luta:
    def __init__(self, level, spawn="entrada", cls="guerreiro", seed=1, perto=None, ato=None):
        self.session = new_session(cls)
        if ato:
            preparar(self.session.char, ato)
        self.world = world_for(self.session, level, spawn, seed=seed)
        self.player = self.world.player
        self.boss = next(e for e in self.world.enemies() if isinstance(e, Boss))
        self.door = next((p for p in self.world.props if p.spec.get("close_on") == "boss_start"), None)
        if perto is not None:
            # fases sem arena própria: começa no primeiro chão livre a `perto` unidades do chefe
            lv = self.world.level
            for k in range(16):
                a = math.tau * k / 16
                x, z = self.boss.x + math.cos(a) * perto, self.boss.z + math.sin(a) * perto
                if lv.ground_at(x, z) is not None and nav_for(lv).find(x, z, self.boss.x, self.boss.z):
                    self.player.x, self.player.z = x, z
                    break
        self.mortes = 0
        self.player.die = self._morte
        self.time = 0.0
        self.damage_taken = 0.0
        self.phases = set()
        self.door_closed = False
        self.zones_seen = {}
        self.boss_na_parede = 0   # quadros com o chefe sobre células de parede (empurrado para fora da arena)
        self.separados = 0        # quadros com a névoa fechada e chefe/jogador em lados opostos dela
        self._path, self._repath, self._stuck, self._side, self._last = [], 0.0, 0.0, 0.0, None

    def _mesmo_lado(self):
        """Jogador e chefe na mesma região do grid quando as células da névoa contam como bloqueadas."""
        nav = nav_for(self.world.level)
        d = self.door
        hx, hz = d.half
        porta = {(x, z) for x in range(int(d.x - hx), int(d.x + hx) + 1) for z in range(int(d.z - hz), int(d.z + hz) + 1)
                 if abs(x + 0.5 - d.x) < hx + 0.01 and abs(z + 0.5 - d.z) < hz + 0.01}
        ini, fim = (int(self.player.x), int(self.player.z)), (int(self.boss.x), int(self.boss.z))
        vistos, pilha = {ini}, [ini]
        while pilha:
            c = pilha.pop()
            if c == fim:
                return True
            for nx, nz, _ in nav.nbrs.get(c, ()):
                if (nx, nz) not in vistos and (nx, nz) not in porta:
                    vistos.add((nx, nz))
                    pilha.append((nx, nz))
        return fim not in nav.nbrs   # chefe fora do grid navegável (no ar, por exemplo): não conta

    def _morte(self, killer):
        self.mortes += 1
        self.player.hp = self.player.max_hp

    def alvo(self):
        # foca o chefe e suas partes (braços etc.); inimigos comuns da fase são ignorados
        vivos = [e for e in self.world.enemies() if not e.dead and (e is self.boss or getattr(e, "owner", None) is self.boss)]
        return min(vivos, key=lambda e: e.dist_to(self.player)) if vivos else self.boss

    def _direcao(self, alvo):
        p = self.player
        self._repath -= DT
        if self._repath <= 0:
            self._path = nav_for(self.world.level).find(p.x, p.z, alvo.x, alvo.z) or []
            self._repath = 0.5
        while self._path and math.hypot(self._path[0][0] - p.x, self._path[0][1] - p.z) < 0.6:
            self._path.pop(0)
        tx, tz = self._path[0] if len(self._path) > 1 else (alvo.x, alvo.z)
        ang = math.atan2(tz - p.z, tx - p.x)
        # preso num prop sólido: anda de lado por um tempo
        if self._last and math.hypot(p.x - self._last[0], p.z - self._last[1]) < 0.01:
            self._stuck += DT
        else:
            self._stuck = 0.0
        self._last = (p.x, p.z)
        if self._stuck > 0.3:
            self._side = 0.8
        if self._side > 0:
            self._side -= DT
            ang += math.pi / 2
        return math.cos(ang), math.sin(ang)

    def lutar(self, limite=360.0):
        p, w = self.player, self.world
        i = 0
        while self.time < limite and not self.boss.dead:
            alvo = self.alvo()
            d = alvo.dist_to(p) - getattr(alvo, "radius", 0.5)   # distância até a borda do alvo
            antes = p.hp
            perto = d < 1.3
            if perto and p.action is None:
                p.facing = math.atan2(alvo.z - p.z, alvo.x - p.x)   # mira, como um jogador faria
            step(w, 1, press="light" if i % 12 == 0 and perto else None,
                 move=self._direcao(alvo) if d > 0.8 else (0.0, 0.0))
            self.damage_taken += max(0.0, antes - p.hp)
            p.hp = p.max_hp
            self.phases.add(self.boss.phase)
            c = w.level.cell(int(self.boss.x), int(self.boss.z))
            if c is None or c.kind == "wall":
                self.boss_na_parede += 1
            if self.door is not None and not self.door.open:
                self.door_closed = True
                if i % 30 == 0 and not self.boss.dead and not self._mesmo_lado():
                    self.separados += 1
            for z in w.zones:
                self.zones_seen.setdefault(z.id, z)
            self.time += DT
            i += 1
        step(w, 120)
        return self
