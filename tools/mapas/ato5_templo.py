"""Ato V, parte 2: Templo da Graça (placas e alavanca, o guardião do Selo do Trono e a escadaria final)."""
from grade import Grade
from comum import save

W, D = 56, 52
g = Grade(W, D, "#")
g.border("H", north="H")
# nártex (sul)
g.rect(20, 42, 36, 49, ".")
g.rect(28, 50, 28, 50, ".")
# claustro das placas (centro): três placas com trava e uma alavanca no alto da galeria
g.rect(14, 24, 42, 41, ",")
g.rect(17, 27, 39, 38, ":")
g.rect(26, 30, 30, 35, "w")
g.rect(14, 22, 16, 23, "1")   # galeria da alavanca, sem encostar no santuário
g.rect(16, 24, 16, 24, "a")
# galerias laterais
g.rect(3, 26, 12, 40, ".")
g.rect(13, 32, 13, 34, ".")
g.rect(44, 26, 53, 40, ".")
g.rect(43, 32, 43, 34, ".")
# santuário interno (norte), aberto pelas placas; nele, o guardião e a grade do selo
g.rect(18, 10, 38, 21, ";")
g.rect(27, 22, 29, 23, ";")
g.rect(24, 4, 32, 8, ".")
g.rect(27, 9, 29, 9, ".")
# escadaria do Trono (noroeste), trancada pelo Selo do Trono
g.rect(6, 6, 14, 16, "_")
g.rect(15, 12, 17, 14, "_")   # corredor do selo (porta na coluna 16)
g.rect(10, 2, 10, 5, "_")

E = g.ent
E(28, 48, type="spawn", id="inicio", angle=90)
E(28, 50, type="exit", id="desce_ruinas", to="ato5_ruinas", spawn="graca_portao_celeste", label="Descer às Ruínas",
  auto=False, sprite="stairs_down")
E(24, 45, type="grace", id="graca_nartex", name="Nártex do Templo")

# placas e alavanca
for i, (x, r) in enumerate(((5, 28), (51, 38), (34, 39))):
    E(x, r, type="plate", id=f"placa_{i}", latch=True)
E(15, 22, type="lever", id="alavanca_templo", one_shot=True)
E(28, 23, type="door", id="porta_santuario", sprite="gate", half=[1.5, 0.5], top=3.0,
  message="Placas e alavanca em uníssono: o santuário interno se abre.")

# santuário interno: guardião e o selo
E(36, 20, type="grace", id="graca_escadaria_trono", name="Santuário Interno")
E(28, 14, type="enemy", enemy="guardiao_graca", elite=True, unique="a5_guardiao_selo", group="guarda_selo")
for (x, r) in ((22, 12), (34, 12)):
    E(x, r, type="enemy", enemy="cavaleiro_divino", group="guarda_selo")
E(28, 9, type="door", id="grade_selo", sprite="gate_iron_small", half=[1.5, 0.5], top=3.0,
  message="O guardião cai. A grade do relicário se ergue.")
E(28, 5, type="chest", id="bau_selo_trono", loot=[{"item": "selo_trono"}, {"materials": 5}])

# escadaria do Trono
E(16, 13, type="door", id="porta_trono", key="selo_trono", sprite="gate", half=[0.5, 1.5], top=3.5, consume_key=False,
  locked_text="Um selo de ouro tranca a escadaria do Trono.")
E(10, 2, type="exit", id="sobe_trono", to="ato5_arena", spawn="entrada", label="Subir ao Trono da Graça", auto=True)
E(7, 15, type="chest", id="bau_escadaria", loot=[{"rune": "juramento"}])

# luzes
for (x, r) in ((20, 42), (36, 42), (14, 41), (42, 41), (3, 26), (53, 26), (18, 10), (38, 10), (6, 6), (14, 6)):
    E(x, r, type="decor", sprite="lamp_post", light={"color": [1.0, 0.9, 0.65], "intensity": 1.6, "radius": 6.5, "h": 2.0, "flicker": 0.1})
for (x, r) in ((24, 17), (32, 17)):
    E(x, r, type="decor", sprite="brazier_gold", solid=True, half=[0.3, 0.3], top=1.0,
      light={"color": [1.0, 0.85, 0.5], "intensity": 2.0, "radius": 7, "h": 1.3, "flicker": 0.15})
for (x, r) in ((17, 27), (39, 27), (17, 38), (39, 38)):
    E(x, r, type="decor", sprite="angel_statue", solid=True, half=[0.4, 0.4], top=2.2)

# inimigos
for (x, r) in ((22, 44), (34, 46)):
    E(x, r, type="enemy", enemy="espirito_ancestral")
for (x, r) in ((20, 33), (36, 30), (31, 37)):
    E(x, r, type="enemy", enemy="cavaleiro_divino" if x != 31 else "ser_celestial")
for (x, r) in ((7, 33), (49, 30)):
    E(x, r, type="enemy", enemy="anjo_corrompido")
E(10, 10, type="enemy", enemy="ser_celestial")

puzzles = [
 {"id": "placas_templo", "type": "all_on", "props": ["placa_0", "placa_1", "placa_2", "alavanca_templo"],
  "open": ["porta_santuario"], "message": "O templo inteiro ressoa.", "grace": 900},
 {"id": "guardiao_selo", "type": "kill", "group": "guarda_selo", "open": ["grade_selo"]}]
regions = [{"id": "nartex", "name": "Nártex do Templo", "rect": g.rect_world(19, 42, 37, 51)},
           {"id": "claustro", "name": "Claustro das Placas", "rect": g.rect_world(2, 22, 54, 41)},
           {"id": "santuario", "name": "Santuário Interno", "rect": g.rect_world(17, 3, 39, 23)},
           {"id": "escadaria", "name": "Escadaria do Trono", "rect": g.rect_world(5, 1, 17, 17)},
           {"id": "templo", "name": "Templo da Graça", "rect": [0, 0, W, D]}]
save({"id": "ato5_templo", "name": "Templo da Graça", "act": 5, "theme": "ato5", "env": "trono", "music": "ato5",
      "rows": g.rows(), "entities": g.entities, "puzzles": puzzles, "regions": regions})
