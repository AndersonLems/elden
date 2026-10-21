"""Ato II, parte 2: Casa de Máquinas (vapor, energia e elevador até o Núcleo da Forja)."""
import math
from grade import Grade, carve, scatter, protect
from comum import save

W, D = 60, 48
g = Grade(W, D, "#")
g.border("H", north="H")
# salão de entrada (sul)
g.rect(20, 36, 40, 46, ".")
g.rect(28, 46, 32, 46, ".")
# casa de caldeiras (oeste)
g.rect(2, 24, 18, 44, ",")
g.rect(19, 38, 19, 40, ".")
# lava das fornalhas
g.rect(4, 26, 9, 30, "w")
g.rect(12, 38, 16, 42, "w")
# corredor dos operários (perigo do vapor) e câmara do pistão (centro)
g.rect(20, 24, 40, 34, ";")
g.rect(29, 35, 31, 35, ".")
# sala de distribuição de energia (leste) trancada
g.rect(42, 24, 57, 40, ":")
g.rect(41, 30, 41, 32, ":")
# área superior (altura 3) ao norte, cercada por canos sólidos; só o elevador sobe até ela
g.rect(9, 2, 51, 21, "P")
g.rect(10, 3, 50, 20, "3")
g.rect(28, 17, 32, 23, ".")       # poço do elevador (a plataforma no alto encosta no planalto)
g.rect(36, 16, 38, 20, "~")
g.rect(26, 2, 34, 4, "3")
g.rect(25, 1, 35, 1, "P")
# grades e canos
for x in (21, 39):
    g.rect(x, 24, x, 34, "p")
g.put(21, 29, ";")
g.put(39, 29, ";")
for (x, r) in ((6, 34), (12, 30), (25, 40), (35, 40), (46, 36), (52, 28), (18, 10), (42, 10)):
    g.put(x, r, "P")

E = g.ent
E(30, 45, type="spawn", id="entrada", angle=90)
E(30, 46, type="exit", id="volta_cidade", to="ato2_cidade", spawn="saida_fabrica", label="Voltar à cidade", auto=False, sprite="stairs_down")
E(27, 42, type="grace", id="graca_caldeiras", name="Casa de Caldeiras")
E(30, 8, type="grace", id="graca_elevador", name="Topo do Elevador")
E(24, 44, type="document", doc="diagrama_valvulas", sprite="stone_tablet")
E(36, 44, type="document", doc="relatorio_serafim", sprite="note")
# puzzle 2: válvulas (vapor da caldeira até o pistão sem vazar no corredor)
E(8, 36, type="valve", id="valvula_a", positions=2, state=0)
E(14, 34, type="valve", id="valvula_b", positions=2, state=1)
E(16, 26, type="valve", id="valvula_alivio", positions=2, state=1)
E(4, 40, type="decor", sprite="forge", solid=True, half=[0.6, 0.5], top=1.5, light={"color": [1.0, 0.45, 0.15], "intensity": 2.6, "radius": 7, "h": 1.2, "flicker": 0.3})
for i, (x, r) in enumerate(((10, 36), (14, 30), (24, 26))):
    E(x, r, type="power_node", id=f"cano_{i}", sprite="power_node", interact=False)
E(30, 24, type="door", id="porta_pistao", sprite="gate_iron", half=[2.5, 0.5], top=3.0, message="O pistão principal sobe e abre a passagem ao norte!")
# corredor com jatos de vapor (só param quando a válvula de alívio fecha)
for i, x in enumerate(range(23, 38, 3)):
    E(x, 31, type="hazard", id=f"jato_corredor_{i}", hazard="steam", sprite="pipe_vent", period=2.0, on_time=0.8, warn=0.6, offset=i * 0.4,
      radius=0.9, dmg=0.1, element="fogo", targets=[])
# puzzle 3: distribuição de energia (porta trancada pela manivela de Lise)
E(41, 31, type="door", id="porta_distribuicao", key="valvula_lise", sprite="gate_iron_small", half=[0.5, 1.5], top=3.0, consume_key=False,
  locked_text="Trancada. A manivela da válvula mestra está com o Capataz da cidade.")
for i, (x, r) in enumerate(((45, 36), (50, 36), (55, 36), (45, 28), (50, 28), (55, 28))):
    E(x, r, type="power_node", id=f"no_{i}", state=0)
E(50, 25, type="document", doc="placa_energia", sprite="stone_tablet")
# elevador: plataforma que sobe da sala de pistão ao nível superior
ex, ez = g.pos(30, 18)
E(30, 18, type="platform", id="elevador", points=[[ex, 0.0, ez], [ex, 3.0, ez]], half=[1.6, 1.6], speed=1.4, wait=2.5, active=False,
  tex="copper_plate")
E(30, 3, type="exit", id="elevador_nucleo", to="ato2_arena", spawn="entrada", label="Descer ao Núcleo da Forja", auto=True)
# baús e segredos
E(16, 43, type="chest", id="bau_caldeiras", loot=[{"item": "frasco_brasa"}])
E(56, 39, type="chest", id="bau_energia", loot=[{"art": "art_lamina_flamejante"}, {"materials": 3}])
E(12, 6, type="chest", id="bau_topo", loot=[{"weapon": "martelo_ferreiro"}, {"materials": 4}])
E(47, 6, type="altar", id="altar_forja", altar="profano", prompt="Alimentar a fornalha com sangue", reward=[{"rune": "sobrecarga"}])
# luzes
for (x, r) in ((22, 38), (38, 38), (22, 44), (38, 44), (3, 25), (17, 25), (43, 39), (56, 25), (12, 18), (48, 18), (26, 33), (34, 33)):
    E(x, r, type="decor", sprite="wall_torch", light={"color": [1.0, 0.55, 0.2], "intensity": 1.8, "radius": 6, "h": 1.8, "flicker": 0.3})
for (x, r) in ((16, 12), (44, 12), (20, 6), (40, 6)):
    E(x, r, type="decor", sprite="brazier", solid=True, half=[0.3, 0.3], top=1.0, light={"color": [1.0, 0.5, 0.2], "intensity": 2.2, "radius": 7, "h": 1.3, "flicker": 0.3})
for (x, r) in ((10, 40), (6, 28), (52, 32), (46, 26), (18, 16), (42, 16)):
    E(x, r, type="decor", sprite="gear", solid=True, half=[0.5, 0.5], top=1.0)
# inimigos
for (x, r) in ((24, 40), (36, 42)):
    E(x, r, type="enemy", enemy="cao_mecanico")
for (x, r) in ((10, 32), (6, 42)):
    E(x, r, type="enemy", enemy="operario_corrompido")
E(30, 28, type="enemy", enemy="automato")
E(26, 30, type="enemy", enemy="operario_corrompido")
for (x, r) in ((48, 33), (53, 31)):
    E(x, r, type="enemy", enemy="automato")
E(44, 38, type="enemy", enemy="sentinela")
for (x, r) in ((20, 12), (40, 12), (30, 11)):
    E(x, r, type="enemy", enemy="maquina_serra" if x == 30 else "cao_mecanico")
E(30, 6, type="enemy", enemy="guardiao_industrial", elite=True, unique="a2_colosso_bronze")
E(16, 8, type="enemy", enemy="sentinela")
E(44, 8, type="enemy", enemy="sentinela")
puzzles = [
 {"id": "vapor_caldeira", "type": "network", "source": "caldeira",
  "edges": [["caldeira", "n1", "valvula_a", 1], ["n1", "n2", "valvula_b", 0], ["n2", "pistao"], ["n1", "corredor", "valvula_alivio", 1],
            ["caldeira", "n3", "valvula_b", 1], ["n3", "corredor"]],
  "sinks": ["pistao"], "forbidden": ["corredor"], "indicators": {"n1": "cano_0", "n2": "cano_1", "pistao": "cano_2"},
  "overload_text": "O vapor escapa pelo corredor dos operários!", "open": ["porta_pistao"],
  "activate": [], "message": "O vapor chega ao pistão principal!", "grace": 300},
 {"id": "forja_energia", "type": "network", "source": "dinamo",
  "edges": [["dinamo", "a", "no_0", 1], ["a", "b", "no_1", 1], ["b", "elevador", "no_2", 0], ["b", "sobrecarga", "no_2", 1],
            ["dinamo", "c", "no_3", 1], ["c", "d", "no_4", 0], ["c", "sobrecarga", "no_4", 1], ["d", "elevador", "no_5", 1]],
  "sinks": ["elevador"], "forbidden": ["sobrecarga"], "overload_text": "Sobrecarga! Faíscas saltam dos cabos.",
  "activate": ["elevador"], "message": "A energia corre até o elevador principal!", "grace": 300,
  "reward": [{"flag": "puzzle:forja_energia"}]}]
regions = [{"id": "caldeiras", "name": "Casa de Caldeiras", "rect": g.rect_world(1, 24, 19, 46)},
           {"id": "pistao", "name": "Câmara do Pistão", "rect": g.rect_world(20, 22, 40, 35)},
           {"id": "distribuicao", "name": "Sala de Distribuição", "rect": g.rect_world(41, 24, 58, 41)},
           {"id": "topo", "name": "Topo do Elevador", "rect": g.rect_world(9, 1, 51, 21)},
           {"id": "fabrica", "name": "Casa de Máquinas", "rect": [0, 0, W, D]}]
save({"id": "ato2_fabrica", "name": "Casa de Máquinas", "act": 2, "theme": "ato2", "env": "forja", "music": "ato2",
      "rows": g.rows(), "entities": g.entities, "puzzles": puzzles, "regions": regions})
