"""Ato IV, parte 1: Biblioteca Abissal (Corvin na gaiola, ilhas no vazio ligadas por portais e o selo rúnico)."""
from grade import Grade
from comum import save

W, D = 64, 54
g = Grade(W, D, "#")
g.border("H", north="H")
# saguão de entrada (sul)
g.rect(24, 44, 40, 51, ".")
g.rect(31, 52, 33, 52, ".")
# salão de leitura (centro) com estantes
g.rect(16, 22, 46, 43, ",")
g.rect(30, 22, 32, 43, "_")
for r in range(25, 42, 4):
    g.rect(18, r, 27, r, "B")
    g.rect(35, r, 44, r, "B")
# gaiola de Corvin (oeste)
g.rect(5, 28, 12, 36, ":")
g.rect(13, 32, 15, 32, ":")
# estantes de astronomia (nordeste): a alavanca fica atrás da última fileira, por um vão estreito
g.rect(48, 22, 58, 34, ",")
g.rect(47, 26, 47, 28, ",")
g.rect(49, 25, 57, 25, "B")
g.rect(49, 28, 57, 28, "B")
g.rect(49, 31, 56, 31, "B")
g.rect(49, 33, 57, 33, "B")
# vazio astral (leste) com ilhas alcançadas só por portais
g.rect(48, 4, 61, 20, "~")
g.rect(50, 6, 53, 9, ";")
g.rect(57, 14, 60, 18, ";")
# escadaria do selo (norte)
g.rect(22, 8, 42, 21, ".")
g.rect(28, 3, 36, 7, ":")
g.rect(32, 1, 32, 2, ":")
# alcova secreta (sudoeste), atrás de parede falsa
g.rect(4, 44, 9, 49, ";")
g.rect(10, 46, 23, 46, ",")

E = g.ent
E(32, 50, type="spawn", id="inicio", angle=90)
E(32, 52, type="exit", id="volta_santuario", to="santuario", spawn="retorno_ato4", label="Voltar ao Santuário", auto=False,
  sprite="portal_gate", color=[0.5, 0.4, 1.0])
E(27, 47, type="grace", id="graca_saguao", name="Saguão da Academia")
E(38, 46, type="document", doc="tratado_runas", sprite="lectern")

# Corvin e a gaiola rúnica
E(8, 32, type="npc", npc="corvin", angle=0)
E(13, 32, type="door", id="gaiola_corvin", sprite="gate_iron_small", half=[0.5, 0.5], top=3.0,
  message="A gaiola rúnica se apaga. Corvin está livre!")
E(15, 34, type="document", doc="carta_corvin", sprite="note")
E(57, 29, type="lever", id="alavanca_bronze", sprite="lever", one_shot=True)
E(17, 23, type="grace", id="graca_biblioteca", name="Salão de Leitura")

# portais: salão → ilha A → ilha B (e volta)
E(45, 23, type="portal", id="portal_salao", link="portal_ilha_a", color=[0.6, 0.4, 1.0])
E(51, 7, type="portal", id="portal_ilha_a", link="portal_salao", color=[0.6, 0.4, 1.0])
E(53, 8, type="portal", id="portal_ilha_a2", link="portal_ilha_b", color=[0.4, 0.8, 1.0])
E(58, 15, type="portal", id="portal_ilha_b", link="portal_ilha_a2", color=[0.4, 0.8, 1.0])
E(59, 17, type="chest", id="bau_ilha_estrelas", loot=[{"item": "chave_torre"}, {"materials": 3}])
E(52, 9, type="document", doc="fragmento_ciclo_4", sprite="item_glow")

# selo rúnico: CÍRCULO, TRIÂNGULO, CRUZ, LOSANGO (índices 0, 1, 3, 4)
E(23, 9, type="document", doc="selo_academia", sprite="stone_tablet")
for i, x in enumerate((26, 30, 34, 38)):
    E(x, 12, type="dial", id=f"selo_{i}", sprite="rune_dial",
      symbols=["círculo", "triângulo", "quadrado", "cruz", "losango", "x"], state=5, prompt="Girar selo rúnico")
E(32, 7, type="door", id="porta_escadaria", sprite="gate", half=[4.5, 0.5], top=3.0,
  message="Os quatro selos formam a pergunta proibida. A escadaria se abre.")
E(32, 9, type="spawn", id="escadaria", angle=-90)
E(32, 1, type="exit", id="sobe_observatorio", to="ato4_observatorio", spawn="inicio", label="Subir ao Observatório", auto=True)

# alcova secreta
E(10, 46, type="breakable_wall", id="parede_alcova", sprite="cracked_wall")
E(5, 45, type="chest", id="bau_alcova", loot=[{"item": "lagrima_eter"}, {"materials": 2}])

# luzes
for (x, r) in ((24, 44), (40, 44), (16, 30), (46, 30), (16, 40), (46, 40), (22, 10), (42, 10), (5, 29), (58, 23)):
    E(x, r, type="decor", sprite="wall_torch", light={"color": [0.55, 0.5, 1.0], "intensity": 1.7, "radius": 6, "h": 1.8, "flicker": 0.2})
for (x, r) in ((29, 15), (35, 15)):
    E(x, r, type="decor", sprite="brazier_blue", solid=True, half=[0.3, 0.3], top=1.0,
      light={"color": [0.5, 0.6, 1.0], "intensity": 2.0, "radius": 7, "h": 1.3, "flicker": 0.2})
E(54, 19, type="decor", sprite="crystal_cluster", light={"color": [0.6, 0.8, 1.0], "intensity": 1.5, "radius": 5, "h": 1.0})

# inimigos
for (x, r) in ((28, 48), (36, 49)):
    E(x, r, type="enemy", enemy="livro_voador")
for (x, r) in ((22, 27), (40, 31), (24, 39), (38, 37)):
    E(x, r, type="enemy", enemy="bruxo" if x < 30 else "bruxa")
E(31, 34, type="enemy", enemy="armadura_encantada")
for (x, r) in ((52, 23), (55, 32)):
    E(x, r, type="enemy", enemy="sombra_arcana")
E(9, 34, type="enemy", enemy="livro_voador")
for (x, r) in ((25, 17), (39, 17)):
    E(x, r, type="enemy", enemy="sentinela_runica")
E(32, 15, type="enemy", enemy="armadura_encantada", elite=True, unique="a4_guarda_selo")

puzzles = [
 {"id": "gaiola_corvin", "type": "all_on", "props": ["alavanca_bronze"], "open": ["gaiola_corvin"],
  "reward": [{"flag": "corvin_livre"}], "message": "Um estalo de bronze ecoa pelas estantes.", "grace": 300},
 {"id": "selo_academia", "type": "combination", "props": ["selo_0", "selo_1", "selo_2", "selo_3"], "solution": [0, 1, 3, 4],
  "open": ["porta_escadaria"], "lock": ["selo_0", "selo_1", "selo_2", "selo_3"], "message": "Os selos brilham em uníssono.",
  "grace": 600}]
regions = [{"id": "saguao", "name": "Saguão da Academia", "rect": g.rect_world(23, 44, 41, 53)},
           {"id": "leitura", "name": "Salão de Leitura", "rect": g.rect_world(15, 22, 47, 43)},
           {"id": "gaiola", "name": "Gaiola Rúnica", "rect": g.rect_world(4, 27, 15, 37)},
           {"id": "astronomia", "name": "Estantes de Astronomia", "rect": g.rect_world(47, 21, 59, 35)},
           {"id": "vazio", "name": "Ilhas do Vazio", "rect": g.rect_world(48, 3, 62, 21)},
           {"id": "escadaria", "name": "Escadaria do Selo", "rect": g.rect_world(21, 0, 43, 21)},
           {"id": "biblioteca", "name": "Biblioteca Abissal", "rect": [0, 0, W, D]}]
save({"id": "ato4_biblioteca", "name": "Biblioteca Abissal", "act": 4, "theme": "ato4", "env": "observatorio", "music": "ato4",
      "rows": g.rows(), "entities": g.entities, "puzzles": puzzles, "regions": regions})
