"""Ato III, parte 1: Catedral da Carne (nave, biblioteca médica, capela dos mártires e os quatro sinos)."""
from grade import Grade
from comum import save

W, D = 64, 56
g = Grade(W, D, "#")
g.border("H", north="H")
# átrio (sul)
g.rect(24, 46, 40, 53, ".")
g.rect(31, 54, 33, 54, ".")
# nave central com corredor de tapete vermelho
g.rect(22, 14, 42, 45, ".")
g.rect(31, 14, 33, 45, "_")
for r in range(18, 43, 3):          # fileiras de bancos (muretas de altura 1)
    g.rect(24, r, 29, r, "h")
    g.rect(35, r, 40, r, "h")
for r in range(16, 44, 4):          # colunatas
    g.put(23, r, "P")
    g.put(41, r, "P")
for r in (20, 21, 28, 29, 36, 37):  # vitrais dourados nas paredes da nave
    g.put(21, r, "G")
    g.put(43, r, "G")
# biblioteca médica (oeste)
g.rect(4, 22, 19, 40, ",")
for r in range(24, 39, 3):
    g.rect(6, r, 11, r, "B")
    g.rect(14, r, 17, r, "B")
g.rect(20, 30, 21, 32, ".")
# relicário secreto atrás da biblioteca
g.rect(1, 30, 3, 33, ";")   # a coluna 3 fica sob a parede falsa
# capela dos mártires (leste): ossos e poças de sangue
g.rect(45, 22, 60, 40, ";")
g.rect(43, 30, 44, 32, ".")
g.rect(48, 25, 50, 27, "w")
g.rect(55, 34, 57, 36, "w")
# relicário trancado da capela (norte da capela)
g.rect(50, 16, 56, 20, "_")
g.rect(53, 21, 53, 21, "_")
# presbitério (norte) com o altar elevado e os sinos
g.rect(24, 5, 40, 13, ".")
g.rect(29, 6, 35, 8, "1")
g.rect(31, 9, 33, 9, "a")
g.rect(30, 3, 34, 4, ";")
g.rect(32, 1, 32, 2, ";")

E = g.ent
E(32, 52, type="spawn", id="inicio", angle=90)
E(32, 54, type="exit", id="volta_santuario", to="santuario", spawn="retorno_ato3", label="Voltar ao Santuário", auto=False,
  sprite="portal_gate", color=[0.9, 0.3, 0.35])
E(27, 49, type="grace", id="graca_atrio", name="Átrio da Catedral")
E(37, 48, type="npc", npc="agathe", angle=180)
E(25, 51, type="document", doc="sermao_carne", sprite="lectern")

# nave
E(22, 45, type="document", doc="vitral_ordem", sprite="stone_tablet")
for (x, r) in ((30, 44), (34, 44), (30, 15), (34, 15)):
    E(x, r, type="decor", sprite="candelabra", light={"color": [1.0, 0.7, 0.4], "intensity": 1.7, "radius": 6, "h": 1.6, "flicker": 0.25})
for (x, r) in ((22, 25), (42, 25), (22, 33), (42, 33), (22, 41), (42, 41)):
    E(x, r, type="decor", sprite="wall_torch", light={"color": [1.0, 0.55, 0.35], "intensity": 1.6, "radius": 6, "h": 1.8, "flicker": 0.3})

# biblioteca: página 1, prontuário e passagem secreta
E(5, 23, type="document", doc="pagina_absolvicao_1", sprite="note")
E(18, 39, type="document", doc="prontuario_aldric", sprite="lectern")
E(12, 22, type="document", doc="diario_cirurgiao", sprite="bookpile")
E(3, 31, type="breakable_wall", id="parede_relicario", sprite="cracked_wall")
E(1, 32, type="document", doc="fragmento_ciclo_3", sprite="item_glow")
E(2, 30, type="chest", id="bau_relicario_secreto", loot=[{"rune_slot": 1}, {"materials": 3}])
for (x, r) in ((5, 28), (18, 28), (5, 36), (18, 34)):
    E(x, r, type="decor", sprite="candelabra", light={"color": [1.0, 0.75, 0.45], "intensity": 1.5, "radius": 5.5, "h": 1.6, "flicker": 0.2})

# capela dos mártires: Graça, página 2 e o Abade
E(46, 31, type="grace", id="graca_martires", name="Capela dos Mártires")
E(59, 23, type="document", doc="pagina_absolvicao_2", sprite="note")
for (x, r) in ((47, 23), (58, 39), (52, 31)):
    E(x, r, type="decor", sprite="coffin", solid=True, half=[0.4, 0.6], top=0.8)
for (x, r) in ((46, 38), (59, 30), (52, 23)):
    E(x, r, type="decor", sprite="blood_candle", light={"color": [1.0, 0.25, 0.2], "intensity": 1.6, "radius": 5.5, "h": 1.0, "flicker": 0.35})
E(53, 21, type="door", id="porta_relicario", sprite="gate_iron_small", half=[0.5, 0.5], top=3.0,
  message="Com o Abade caído, o relicário se abre.")
E(53, 17, type="chest", id="bau_relicario", loot=[{"item": "chave_laboratorio"}, {"materials": 4}])
E(51, 18, type="decor", sprite="angel_statue", solid=True, half=[0.4, 0.4], top=2.2)
E(55, 18, type="decor", sprite="angel_statue", solid=True, half=[0.4, 0.4], top=2.2)

# presbitério: os quatro sinos (sequência) abrem a escada da cripta
for sym, (x, r) in zip(("COROA", "CORDEIRO", "ESPADA", "CÁLICE"), ((25, 6), (39, 6), (25, 12), (39, 12))):
    E(x, r, type="seq_button", id=f"sino_{sym.lower().replace('á', 'a')}", symbol=sym, sprite="button",
      prompt=f"Tocar o sino do {sym.capitalize()}")
E(32, 6, type="altar", id="altar_carne", altar="oracao", prompt="Rezar diante da Carne Santa", sprite="altar")
E(32, 4, type="door", id="escada_cripta", sprite="gate", half=[1.5, 0.5], top=3.0,
  message="Os sinos ecoam em ordem. A escada para o laboratório se abre.")
E(32, 10, type="spawn", id="escada", angle=-90)
E(32, 1, type="exit", id="desce_laboratorio", to="ato3_laboratorio", spawn="inicio", label="Descer ao Laboratório", auto=True)
for (x, r) in ((26, 9), (38, 9)):
    E(x, r, type="decor", sprite="brazier_gold", solid=True, half=[0.3, 0.3], top=1.0,
      light={"color": [1.0, 0.8, 0.45], "intensity": 2.0, "radius": 7, "h": 1.3, "flicker": 0.2})

# inimigos
for (x, r) in ((27, 47), (37, 51)):
    E(x, r, type="enemy", enemy="servo_fanatico")
for (x, r) in ((26, 38), (38, 35), (32, 30), (26, 23), (38, 20)):
    E(x, r, type="enemy", enemy="monge_deformado" if r % 2 else "servo_fanatico")
for (x, r) in ((9, 26), (15, 33), (8, 37)):
    E(x, r, type="enemy", enemy="experimento")
for (x, r) in ((50, 34), (57, 27)):
    E(x, r, type="enemy", enemy="servo_fanatico", group="guarda_abade")
E(53, 29, type="enemy", enemy="monge_deformado", elite=True, unique="a3_abade", group="guarda_abade")
for (x, r) in ((28, 11), (36, 11)):
    E(x, r, type="enemy", enemy="monge_deformado")

puzzles = [
 {"id": "sinos_ordem", "type": "sequence", "props": ["sino_cordeiro", "sino_calice", "sino_espada", "sino_coroa"],
  "solution": ["CORDEIRO", "CÁLICE", "ESPADA", "COROA"], "open": ["escada_cripta"],
  "fail_text": "Os sinos dissonam. A missa precisa recomeçar.", "message": "A escada da cripta range e se abre.", "grace": 400},
 {"id": "abade_caido", "type": "kill", "group": "guarda_abade", "open": ["porta_relicario"]}]
regions = [{"id": "atrio", "name": "Átrio da Catedral", "rect": g.rect_world(23, 46, 41, 55)},
           {"id": "nave", "name": "Nave da Carne Santa", "rect": g.rect_world(21, 14, 43, 45)},
           {"id": "biblioteca", "name": "Biblioteca Médica", "rect": g.rect_world(0, 21, 20, 41)},
           {"id": "capela", "name": "Capela dos Mártires", "rect": g.rect_world(44, 15, 61, 41)},
           {"id": "presbiterio", "name": "Presbitério dos Sinos", "rect": g.rect_world(23, 0, 41, 13)},
           {"id": "catedral", "name": "Catedral da Carne", "rect": [0, 0, W, D]}]
save({"id": "ato3_catedral", "name": "Catedral da Carne", "act": 3, "theme": "ato3_catedral", "env": "catedral", "music": "ato3",
      "rows": g.rows(), "entities": g.entities, "puzzles": puzzles, "regions": regions})
