"""Ato III, parte 2: Laboratório sob a Catedral (alquimia, diagrama anatômico e a antecâmara do Santo)."""
from grade import Grade
from comum import save

W, D = 60, 50
g = Grade(W, D, "#")
g.border("H", north="H")
# enfermaria de entrada (sul)
g.rect(22, 40, 38, 47, ",")
g.rect(30, 48, 30, 48, ",")
# corredor central de carne, com poças de ácido
g.rect(26, 10, 34, 39, ",")
g.rect(27, 30, 28, 32, "x")
g.rect(32, 22, 33, 24, "x")
g.rect(27, 14, 28, 15, "x")
for r in (18, 26, 35):
    g.put(26, r, "F")
    g.put(34, r, "F")
# ala alquímica (oeste): a sequência dos reagentes abre a membrana que bloqueia o caminho norte
g.rect(3, 24, 21, 40, ",")
g.rect(22, 30, 25, 32, ",")
g.rect(6, 34, 9, 37, "x")
g.rect(15, 27, 18, 28, "x")
# almoxarifado trancado (noroeste), aberto pela Chave do Laboratório
g.rect(4, 8, 18, 18, ",")
g.rect(11, 19, 11, 23, ",")
# sala cirúrgica (leste) e sala de operações (nordeste)
g.rect(39, 26, 56, 40, ",")
g.rect(35, 32, 38, 34, ",")
g.rect(42, 10, 56, 21, ":")
g.rect(49, 22, 49, 25, ",")
g.frame(42, 10, 56, 21, "F")
g.rect(49, 21, 49, 21, ":")
# antecâmara do Santo (norte)
g.rect(24, 3, 36, 9, ".")
g.rect(30, 1, 30, 2, ".")

E = g.ent
E(30, 46, type="spawn", id="inicio", angle=90)
E(30, 48, type="exit", id="sobe_catedral", to="ato3_catedral", spawn="escada", label="Subir à Catedral", auto=False,
  sprite="stairs_up")
E(24, 44, type="grace", id="graca_enfermaria", name="Enfermaria dos Penitentes")

# ala alquímica: sequência SAL → MERCÚRIO → ENXOFRE → SANGUE
E(4, 25, type="document", doc="receita_alquimica", sprite="lectern")
for sym, sprite, (x, r) in (("SANGUE", "alchemy_tube_red", (5, 30)), ("ENXOFRE", "alchemy_tube", (10, 26)),
                            ("SAL", "alchemy_tube", (14, 32)), ("MERCÚRIO", "alchemy_tube", (19, 38))):
    E(x, r, type="seq_button", id=f"frasco_{sym.lower().replace('ú', 'u')}", symbol=sym, sprite=sprite,
      prompt=f"Verter {sym.capitalize()}")
E(30, 10, type="door", id="membrana_norte", sprite="blood_seal", half=[4.5, 0.5], top=3.0,
  message="O soro dissolve a membrana de carne ao norte!")
for (x, r) in ((4, 39), (20, 25)):
    E(x, r, type="decor", sprite="alchemy_tube_red", light={"color": [1.0, 0.3, 0.25], "intensity": 1.6, "radius": 5.5, "h": 1.2, "flicker": 0.2})

# almoxarifado (Chave do Laboratório, vinda do relicário do Abade)
E(11, 19, type="door", id="porta_almoxarifado", key="chave_laboratorio", sprite="gate_iron_small", half=[0.5, 0.5], top=3.0,
  consume_key=False, locked_text="Trancada. A chave ficou com o Abade, na capela dos mártires.")
E(6, 9, type="chest", id="bau_almoxarifado", loot=[{"item": "semente_dourada"}, {"materials": 4}])
E(16, 9, type="chest", id="bau_reagentes", loot=[{"rune": "carne_viva"}])
E(10, 12, type="decor", sprite="crate", solid=True, half=[0.4, 0.4], top=1.0)

# sala cirúrgica: três lâminas do diagrama (coração SUL, olho NORTE, mão LESTE)
E(40, 39, type="document", doc="diagrama_anatomico", sprite="stone_tablet")
for pid, nome, (x, r) in (("lamina_coracao", "Coração", (44, 28)), ("lamina_olho", "Olho", (49, 28)), ("lamina_mao", "Mão", (54, 28))):
    E(x, r, type="dial", id=pid, sprite="holy_dial", symbols=["norte", "leste", "sul", "oeste"], state=0,
      prompt=f"Girar lâmina: {nome}")
for (x, r) in ((44, 34), (52, 36)):
    E(x, r, type="decor", sprite="coffin", solid=True, half=[0.6, 0.4], top=0.9)
E(49, 22, type="door", id="porta_operacoes", sprite="door_red", half=[0.5, 0.5], top=3.0,
  message="O diagrama se completa. A sala de operações se abre.")
# sala de operações: página 3 e a aberração
E(55, 11, type="document", doc="pagina_absolvicao_3", sprite="note")
E(43, 11, type="chest", id="bau_operacoes", loot=[{"art": "art_chuva_sangue"}, {"materials": 3}])
E(49, 15, type="enemy", enemy="aberracao", elite=True, unique="a3_aberracao")
for (x, r) in ((44, 18), (54, 18)):
    E(x, r, type="decor", sprite="flesh_pod", solid=True, half=[0.4, 0.4], top=1.4,
      light={"color": [1.0, 0.35, 0.4], "intensity": 1.3, "radius": 5, "h": 1.0, "flicker": 0.2})

# antecâmara e porta da arena
E(26, 4, type="grace", id="graca_antecamara", name="Antecâmara do Santo")
E(30, 1, type="exit", id="porta_santo", to="ato3_arena", spawn="entrada", label="Entrar no Santuário da Carne", auto=True)
for (x, r) in ((25, 8), (35, 8)):
    E(x, r, type="decor", sprite="brazier_red", solid=True, half=[0.3, 0.3], top=1.0,
      light={"color": [1.0, 0.35, 0.25], "intensity": 2.0, "radius": 7, "h": 1.3, "flicker": 0.3})
# luzes do corredor
for (x, r) in ((26, 22), (34, 30), (26, 38), (34, 14), (22, 41), (38, 41), (3, 33), (21, 36), (39, 30), (56, 34)):
    E(x, r, type="decor", sprite="wall_torch", light={"color": [0.75, 1.0, 0.6], "intensity": 1.5, "radius": 6, "h": 1.8, "flicker": 0.25})

# inimigos
for (x, r) in ((28, 42), (34, 44)):
    E(x, r, type="enemy", enemy="experimento")
for (x, r) in ((30, 34), (30, 25), (31, 16)):
    E(x, r, type="enemy", enemy="cirurgiao_corrompido" if r != 25 else "guardiao_mutante")
for (x, r) in ((8, 30), (16, 37), (12, 25)):
    E(x, r, type="enemy", enemy="experimento" if x != 12 else "cirurgiao_corrompido")
for (x, r) in ((45, 37), (53, 31)):
    E(x, r, type="enemy", enemy="servo_fanatico")
E(30, 6, type="enemy", enemy="guardiao_mutante", elite=True, unique="a3_guardiao_antecamara")

puzzles = [
 {"id": "soro_purificacao", "type": "sequence", "props": ["frasco_sal", "frasco_mercurio", "frasco_enxofre", "frasco_sangue"],
  "solution": ["SAL", "MERCÚRIO", "ENXOFRE", "SANGUE"], "open": ["membrana_norte"],
  "fail_text": "A mistura fumega e se perde. Recomece.", "message": "O Soro da Purificação borbulha, dourado.", "grace": 500},
 {"id": "diagrama_anatomico", "type": "combination", "props": ["lamina_coracao", "lamina_olho", "lamina_mao"],
  "solution": ["sul", "norte", "leste"], "open": ["porta_operacoes"], "lock": ["lamina_coracao", "lamina_olho", "lamina_mao"],
  "message": "As lâminas se encaixam no diagrama.", "grace": 500}]
regions = [{"id": "enfermaria", "name": "Enfermaria dos Penitentes", "rect": g.rect_world(21, 39, 39, 49)},
           {"id": "corredor", "name": "Corredor da Carne", "rect": g.rect_world(25, 10, 35, 39)},
           {"id": "alquimia", "name": "Ala Alquímica", "rect": g.rect_world(2, 23, 25, 41)},
           {"id": "almoxarifado", "name": "Almoxarifado", "rect": g.rect_world(3, 7, 19, 23)},
           {"id": "cirurgia", "name": "Sala Cirúrgica", "rect": g.rect_world(35, 22, 57, 41)},
           {"id": "operacoes", "name": "Sala de Operações", "rect": g.rect_world(41, 9, 57, 21)},
           {"id": "antecamara", "name": "Antecâmara do Santo", "rect": g.rect_world(23, 0, 37, 9)},
           {"id": "laboratorio", "name": "Laboratório", "rect": [0, 0, W, D]}]
save({"id": "ato3_laboratorio", "name": "Laboratório da Carne", "act": 3, "theme": "ato3_catedral", "env": "laboratorio",
      "music": "ato3", "rows": g.rows(), "entities": g.entities, "puzzles": puzzles, "regions": regions})
