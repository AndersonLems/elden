"""Ato V, parte 1: Ruínas Celestes (Ysolde, as quatro luzes e os três anjos do Portão Celeste)."""
from grade import Grade
from comum import save

W, D = 60, 52
g = Grade(W, D, "#")
g.border("H", north="H")
# escadaria de chegada (sul)
g.rect(22, 42, 38, 49, ",")
g.rect(30, 50, 30, 50, ",")
# avenida das colunas partidas
g.rect(27, 26, 33, 41, ".")
g.rect(29, 26, 31, 41, "_")
# praça das quatro luzes (oeste)
g.rect(4, 24, 20, 38, ":")
g.rect(21, 30, 26, 32, ".")
g.rect(9, 29, 15, 33, "w")
# jardim suspenso (leste), aberto pelas luzes, com a corte dos anjos ao fundo
g.rect(34, 30, 40, 32, ".")
g.rect(41, 27, 56, 38, ".")   # não encosta no pátio do portão
g.rect(42, 28, 53, 30, ";")
# pátio do Portão Celeste (norte)
g.rect(20, 8, 40, 25, ".")
g.rect(28, 3, 32, 7, ";")
g.rect(30, 1, 30, 2, ";")
for r in range(10, 24, 4):
    g.put(22, r, "P")
    g.put(38, r, "P")
# miradouro com vista para o vazio (nordeste)
g.rect(44, 6, 56, 18, ",")
g.rect(41, 12, 43, 14, ",")
g.rect(50, 8, 55, 12, "~")

E = g.ent
E(30, 48, type="spawn", id="inicio", angle=90)
E(30, 50, type="exit", id="volta_santuario", to="santuario", spawn="retorno_ato5", label="Voltar ao Santuário", auto=False,
  sprite="portal_gate", color=[1.0, 0.9, 0.6])
E(26, 45, type="grace", id="graca_escadaria_celeste", name="Escadaria Celeste")
E(35, 45, type="npc", npc="ysolde", angle=180)
E(23, 48, type="document", doc="hino_trono", sprite="stone_tablet")

# quatro luzes: acender todas em até 6 segundos (golpear os cristais)
for i, (x, r) in enumerate(((6, 26), (18, 26), (6, 36), (18, 36))):
    E(x, r, type="crystal", id=f"luz_{i}", hold=6.0, sprite="crystal_gold", color=[1.0, 0.85, 0.5])
E(12, 25, type="document", doc="lamento_anjo", sprite="note")
E(36, 31, type="door", id="portao_jardim", sprite="gate", half=[0.5, 1.5], top=3.0,
  message="As quatro luzes ardem juntas. O portão do jardim se abre.")

# corte dos três anjos (LESTE, NORTE, OESTE)
E(42, 37, type="document", doc="estatuas_anjos", sprite="stone_tablet")
for i, x in enumerate((44, 48, 52)):
    E(x, 28, type="dial", id=f"anjo_{i}", sprite="angel_statue", symbols=["sul", "leste", "norte", "oeste"], state=0,
      prompt="Girar a estátua do anjo")
E(55, 37, type="chest", id="bau_jardim", loot=[{"art": "art_lamina_sagrada"}, {"materials": 4}])

# Portão Celeste
E(24, 23, type="grace", id="graca_portao_celeste", name="Portão Celeste")
E(30, 7, type="door", id="portao_celeste", sprite="gate", half=[2.5, 0.5], top=3.5,
  message="Os anjos se voltam ao Trono. O Portão Celeste se abre.")
E(30, 1, type="exit", id="sobe_templo", to="ato5_templo", spawn="inicio", label="Subir ao Templo da Graça", auto=True)
E(28, 9, type="document", doc="testemunho_ysolde", sprite="note")

# miradouro
E(45, 17, type="chest", id="bau_miradouro", loot=[{"item": "lagrima_eter"}, {"materials": 3}])
E(55, 16, type="altar", id="altar_vazio", altar="profano", prompt="Oferecer sangue ao vazio", reward=[{"rune": "graca_pura"}])

# luzes
for (x, r) in ((22, 42), (38, 42), (27, 34), (33, 34), (4, 24), (20, 38), (41, 27), (56, 38), (20, 9), (40, 9), (44, 6)):
    E(x, r, type="decor", sprite="lamp_post", light={"color": [1.0, 0.9, 0.65], "intensity": 1.6, "radius": 6.5, "h": 2.0, "flicker": 0.1})
for (x, r) in ((28, 30), (32, 37)):
    E(x, r, type="decor", sprite="column_broken", solid=True, half=[0.4, 0.4], top=2.0)

# inimigos
for (x, r) in ((26, 44), (34, 47)):
    E(x, r, type="enemy", enemy="espirito_ancestral")
for (x, r) in ((30, 36), (30, 29)):
    E(x, r, type="enemy", enemy="cavaleiro_divino")
for (x, r) in ((8, 31), (16, 34)):
    E(x, r, type="enemy", enemy="anjo_corrompido")
for (x, r) in ((44, 33), (51, 31), (47, 35)):
    E(x, r, type="enemy", enemy="ser_celestial" if x == 51 else "cavaleiro_divino")
for (x, r) in ((25, 14), (35, 18)):
    E(x, r, type="enemy", enemy="anjo_corrompido")
E(30, 12, type="enemy", enemy="guardiao_graca", elite=True, unique="a5_guardiao_portao")
for (x, r) in ((48, 14), (52, 15)):
    E(x, r, type="enemy", enemy="espirito_ancestral")

puzzles = [
 {"id": "quatro_luzes", "type": "all_on", "props": ["luz_0", "luz_1", "luz_2", "luz_3"], "open": ["portao_jardim"],
  "message": "Por um instante, as ruínas brilham como no primeiro dia.", "grace": 800},
 {"id": "estatuas_anjos", "type": "combination", "props": ["anjo_0", "anjo_1", "anjo_2"], "solution": ["leste", "norte", "oeste"],
  "open": ["portao_celeste"], "lock": ["anjo_0", "anjo_1", "anjo_2"], "message": "Os três anjos olham para onde devem.",
  "grace": 800}]
regions = [{"id": "escadaria", "name": "Escadaria Celeste", "rect": g.rect_world(21, 42, 39, 51)},
           {"id": "avenida", "name": "Avenida das Colunas", "rect": g.rect_world(26, 26, 34, 41)},
           {"id": "luzes", "name": "Praça das Quatro Luzes", "rect": g.rect_world(3, 23, 26, 39)},
           {"id": "jardim", "name": "Jardim Suspenso", "rect": g.rect_world(34, 26, 57, 39)},
           {"id": "portao", "name": "Pátio do Portão Celeste", "rect": g.rect_world(19, 0, 41, 25)},
           {"id": "miradouro", "name": "Miradouro do Vazio", "rect": g.rect_world(41, 5, 57, 19)},
           {"id": "ruinas", "name": "Ruínas Celestes", "rect": [0, 0, W, D]}]
save({"id": "ato5_ruinas", "name": "Ruínas Celestes", "act": 5, "theme": "ato5", "env": "trono", "music": "ato5",
      "rows": g.rows(), "entities": g.entities, "puzzles": puzzles, "regions": regions})
