"""Ato II, parte 1: Cidade de Brasaferro (ruas industriais) até o portão da fundição."""
import math
from grade import Grade, carve, scatter, protect
from comum import save

W, D = 64, 46
g = Grade(W, D, ".")
g.border("H", north="H")
# pisos com manchas de fuligem
for r in range(1, D - 1):
    for x in range(1, W - 1):
        n = math.sin(x * 0.37 + 1.3) * math.cos(r * 0.29 - 0.4) + math.sin((x - r) * 0.21)
        g.put(x, r, "," if n > 0.55 else ("_" if n < -1.1 else "."))
# prédios industriais
blocks = [(2, 2, 12, 9), (16, 2, 26, 7), (40, 2, 50, 8), (2, 14, 8, 22), (20, 12, 30, 18), (44, 12, 52, 19), (56, 22, 62, 30),
          (2, 30, 10, 38), (36, 28, 44, 34)]
for (a, b, c, d) in blocks:
    g.rect(a, b, c, d, "C")
# refeitório (onde está Lise) com porta
g.frame(14, 30, 26, 40, "C")
g.rect(15, 31, 25, 39, ",")
g.put(20, 30, ",")
# canal de lava com pontes
g.rect(1, 23, 34, 25, "w")
g.rect(40, 23, 62, 25, "w")
for x0 in (6, 18, 30):
    g.rect(x0, 23, x0 + 2, 25, "=")
g.rect(35, 21, 39, 27, "~")      # fosso: travessia por plataforma móvel
# pátio da fundição (nordeste) com portão
g.rect(54, 2, 62, 12, "C")
g.rect(55, 3, 61, 11, ";")
g.rect(57, 12, 59, 12, ";")
g.rect(54, 13, 62, 13, "p")
g.put(58, 13, ";")
# saliência secreta sobre a lava, alcançada pela plataforma
g.rect(36, 36, 40, 40, "2")
g.rect(35, 41, 41, 44, "~")
g.rect(32, 36, 35, 40, "~")
g.rect(36, 35, 40, 35, "~")
# trilhos de serra
g.rect(4, 42, 30, 42, ":")
# canos e pilares decorativos
for (x, r) in ((14, 10), (34, 10), (34, 18), (54, 20), (12, 26), (48, 38), (60, 40)):
    g.put(x, r, "P")

E = g.ent
E(4, 43, type="spawn", id="inicio", angle=0)
E(2, 44, type="exit", id="volta_santuario", to="santuario", spawn="retorno_ato2", label="Voltar ao Santuário", auto=False, sprite="portal_gate", color=[1.0, 0.55, 0.15])
E(7, 40, type="grace", id="graca_portoes", name="Portões de Brasaferro")
E(20, 34, type="grace", id="graca_refeitorio", name="Refeitório dos Operários")
E(22, 37, type="npc", npc="lise", angle=-90)
E(17, 38, type="document", doc="carta_lise", sprite="note")
E(24, 32, type="document", doc="manual_operario", sprite="note")
# puzzle 1: engrenagens
for pid, x, has in (("engrenagem_1", 56, False), ("engrenagem_2", 58, True), ("engrenagem_3", 60, False)):
    E(x, 15, type="gear_socket", id=pid, has_gear=has, positions=4)
E(54, 16, type="document", doc="placa_engrenagens", sprite="stone_tablet")
E(58, 13, type="door", id="portao_fundicao", sprite="gate_iron_small", half=[0.5, 0.5], top=3.0, message="As engrenagens se encaixam com um estrondo: o portão da fundição se abre.")
E(58, 8, type="spawn", id="saida_fabrica", angle=-90)
E(58, 5, type="exit", id="entrada_fabrica", to="ato2_fabrica", spawn="entrada", label="Entrar na fundição", auto=True)
E(30, 4, type="gear", id="engrenagem_solta_1")
E(12, 37, type="gear", id="engrenagem_solta_2")
# plataformas móveis sobre o fosso e até a saliência secreta
gx, gz = g.pos(35, 24)
E(34, 24, type="platform", id="plat_fosso", points=[[34.5, 0.0, gz], [40.5, 0.0, gz]], half=[1.0, 1.0], speed=2.2, wait=1.0)
px, pz = g.pos(33, 38)
E(31, 38, type="platform", id="plat_saliencia", points=[[31.0, 0.0, pz], [33.6, 1.0, pz], [35.6, 2.0, pz]], half=[1.0, 1.0], speed=1.6, wait=1.2)
E(38, 38, type="chest", id="bau_saliencia_forja", loot=[{"rune": "engrenagem"}, {"materials": 4}])
# serra no trilho
sx0, sz0 = g.pos(5, 42)
sx1, sz1 = g.pos(29, 42)
E(5, 42, type="hazard", id="serra_trilho", hazard="saw", sprite="saw_hazard", period=0, radius=0.7, dmg=0.12, points=[[sx0, sz0], [sx1, sz1]], speed=4.0)
# vapor
for i, (x, r) in enumerate(((12, 20), (32, 14), (46, 26), (50, 36))):
    E(x, r, type="hazard", id=f"vapor_{i}", hazard="steam", sprite="pipe_vent", period=3.0, on_time=1.0, warn=0.8, offset=i * 0.7, radius=0.9, dmg=0.08, element="fogo")
# luzes
for (x, r) in ((10, 28), (24, 28), (44, 21), (52, 33), (30, 20), (14, 4), (46, 10), (60, 18), (4, 26), (26, 44)):
    E(x, r, type="decor", sprite="lamp_post", solid=True, half=[0.2, 0.2], top=2.5, light={"color": [1.0, 0.6, 0.25], "intensity": 1.8, "radius": 6.5, "h": 2.2, "flicker": 0.2})
for (x, r) in ((16, 22), (40, 26), (24, 22)):
    E(x, r, type="decor", sprite="brazier", solid=True, half=[0.3, 0.3], top=1.0, light={"color": [1.0, 0.5, 0.2], "intensity": 2.2, "radius": 6, "h": 1.3, "flicker": 0.3})
for (x, r) in ((34, 6), (12, 12), (50, 42), (28, 26)):
    E(x, r, type="decor", sprite="gear", solid=True, half=[0.5, 0.5], top=1.0)
for (x, r) in ((31, 8), (32, 8), (9, 27), (45, 43), (46, 43), (53, 28)):
    E(x, r, type="breakable", sprite="crate" if x % 2 else "barrel")
# segredo: parede falsa com fragmento do ciclo
g.rect(3, 34, 10, 34, "_")
g.rect(3, 32, 5, 35, ",")
E(10, 34, type="breakable_wall", id="parede_brasaferro", sprite="cracked_wall_brick", hp=3)
E(4, 33, type="document", doc="fragmento_ciclo_2", sprite="bone_shard")
E(4, 35, type="chest", id="bau_brasaferro_secreto", loot=[{"materials": 3}, {"item": "lagrima_eter"}])
# inimigos
for (x, r) in ((12, 34), (28, 36), (40, 40), (44, 30)):
    E(x, r, type="enemy", enemy="operario_corrompido")
for (x, r) in ((20, 20), (24, 20), (48, 22)):
    E(x, r, type="enemy", enemy="cao_mecanico")
for (x, r) in ((32, 4), (52, 10)):
    E(x, r, type="enemy", enemy="sentinela")
for (x, r) in ((40, 14), (14, 16)):
    E(x, r, type="enemy", enemy="automato")
E(46, 4, type="enemy", enemy="maquina_serra")
E(32, 30, type="enemy", enemy="operario_corrompido", elite=True, unique="a2_capataz", loot=[{"item": "valvula_lise"}])
puzzles = [{"id": "engrenagens_fundicao", "type": "gears", "props": ["engrenagem_1", "engrenagem_2", "engrenagem_3"], "solution": [1, 3, 2],
            "open": ["portao_fundicao"], "lock": [], "message": "As engrenagens giram em sincronia!", "grace": 250}]
regions = [{"id": "portoes", "name": "Portões de Brasaferro", "rect": g.rect_world(1, 36, 14, 45)},
           {"id": "refeitorio", "name": "Refeitório dos Operários", "rect": g.rect_world(14, 30, 26, 40)},
           {"id": "fundicao", "name": "Pátio da Fundição", "rect": g.rect_world(52, 2, 63, 18)},
           {"id": "cidade", "name": "Cidade de Brasaferro", "rect": [0, 0, W, D]}]
save({"id": "ato2_cidade", "name": "Cidade de Brasaferro", "act": 2, "theme": "ato2", "env": "forja", "music": "ato2",
      "rows": g.rows(), "entities": g.entities, "puzzles": puzzles, "regions": regions})
