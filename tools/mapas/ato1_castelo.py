"""Ato I, parte 2: Cripta de Velmora e Castelo de Varkhan (+ Salão Carmesim da Condessa)."""
from grade import Grade, carve, scatter, protect
from comum import save

W, D = 60, 48
g = Grade(W, D, "#")
g.border("#", north="H")
# ---------------- cripta (sul) ----------------
g.rect(4, 31, 55, 45, ":")
g.rect(4, 31, 55, 31, "#")
# corredores e câmaras da cripta
g.rect(4, 36, 9, 45, "#")          # parede oeste grossa
g.rect(10, 36, 18, 45, ":")
g.rect(19, 32, 19, 45, "C")        # divisória com passagens
g.put(19, 40, ":")
g.put(19, 43, ":")
g.rect(36, 32, 36, 45, "C")
g.put(36, 34, ":")
g.put(36, 42, ":")
g.rect(37, 38, 55, 38, "C")
g.put(46, 38, ":")
g.rect(20, 32, 35, 33, ":")
# sala do mordomo (oeste) com caixões
g.rect(10, 32, 18, 35, ";")
g.rect(10, 31, 18, 31, "#")
scatter(g, "t", 0.15, 10, 37, 18, 45, keep=":", seed=4, avoid={(x, r) for x in range(10, 19) for r in (40, 43)})
scatter(g, "t", 0.12, 37, 39, 55, 45, keep=":", seed=9, avoid={(46, r) for r in range(38, 46)} | {(x, 42) for x in range(37, 56)})
# feixe de luz: linha 40 do emissor (10) ao espelho A (20,40)? deixamos a fileira livre
for x in range(10, 36):
    if g.get(x, 40) in "t":
        g.put(x, 40, ":")
for r in range(33, 41):
    if g.get(24, r) in "t#C":
        g.put(24, r, ":")
for x in range(24, 36):
    g.put(x, 34, ":")
# saída norte da cripta: escada/ponte sobre o abismo
g.rect(28, 28, 32, 30, "~")
g.rect(29, 28, 31, 30, "=")
g.put(30, 31, ":")
# ---------------- pátio (centro) ----------------
g.rect(2, 19, 57, 27, ".")
scatter(g, ",", 0.35, 2, 19, 57, 27, keep=".", seed=2)
g.rect(2, 28, 27, 29, "~")
g.rect(33, 28, 57, 29, "~")
g.rect(2, 30, 57, 30, "#")
g.put(30, 30, ":")
# câmara secreta (canto oeste do pátio)
g.rect(2, 19, 8, 24, "#")
g.rect(3, 20, 7, 23, ":")
g.put(8, 22, ".")
# salão carmesim (leste) trancado
g.rect(43, 19, 57, 27, "#")
g.rect(44, 20, 56, 26, "_")
g.put(43, 23, "_")
g.rect(46, 21, 46, 21, "P")
g.rect(54, 21, 54, 21, "P")
g.rect(46, 25, 46, 25, "P")
g.rect(54, 25, 54, 25, "P")
# ---------------- alas e salão principal (norte) ----------------
g.rect(2, 5, 57, 17, ".")
g.rect(2, 18, 57, 18, "#")
for x in (12, 13, 29, 30, 31, 47, 48):
    g.put(x, 18, ".")
# vitrais na parede norte
g.rect(1, 4, 58, 4, "G")
g.rect(28, 1, 32, 4, ".")
g.rect(27, 1, 27, 4, "H")
g.rect(33, 1, 33, 4, "H")
# divisórias das alas
g.rect(20, 5, 20, 17, "#")
g.rect(39, 5, 39, 17, "#")
g.put(20, 11, ".")
g.put(20, 12, ".")
g.put(39, 11, ".")
g.put(39, 12, ".")
# salão principal: tapete, pilares, estrado
g.rect(27, 5, 33, 17, "_")
for r in (7, 10, 13, 16):
    g.put(24, r, "P")
    g.put(36, r, "P")
g.rect(26, 5, 34, 6, "1")
g.rect(28, 7, 32, 7, "a")
# ala oeste: biblioteca/arsenal com sacada (altura 2)
g.rect(3, 5, 12, 7, "1")
g.rect(10, 8, 12, 8, "a")
# ala leste: sacada
g.rect(50, 5, 56, 8, "1")
g.rect(52, 9, 54, 9, "a")
g.rect(40, 14, 44, 17, ";")

E = g.ent
E(30, 44, type="spawn", id="cripta", angle=90)
E(30, 2, type="spawn", id="salao", angle=-90)
E(27, 43, type="grace", id="graca_cripta", name="Cripta de Velmora")
E(30, 24, type="grace", id="graca_patio", name="Pátio do Castelo")
E(33, 44, type="exit", id="subida_cemiterio", to="ato1_floresta", spawn="saida_cripta", label="Subir ao cemitério", auto=False, sprite="stairs_up")
# feixe de luz da cripta (puzzle 2)
E(10, 40, type="emitter", id="vitral_cripta", dir="E", sprite="moon_shaft", color=[0.8, 0.85, 1.0])
E(24, 40, type="mirror", id="espelho_a", state=1)
E(24, 34, type="mirror", id="espelho_b", state=1)
E(35, 34, type="crystal", id="receptor_cripta", receiver=True, color=[0.7, 0.8, 1.0], latch=True, targets=["porta_cripta_norte"])
E(30, 31, type="door", id="porta_cripta_norte", sprite="gate_iron", half=[0.5, 0.5], top=3.0, message="A luz da lua desperta o mecanismo: o portão norte se ergue.")
E(14, 38, type="document", doc="carta_condessa", sprite="note")
E(33, 36, type="document", doc="vitral_lenda", sprite="stone_tablet")
E(12, 33, type="chest", id="bau_mordomo", loot=[{"item": "chave_castelo"}, {"grace": 200}, {"flag": "q_condessa_inicio"}])
E(54, 44, type="chest", id="bau_cripta_leste", loot=[{"item": "semente_dourada"}])
E(50, 40, type="pickup", id="medalhao", loot={"item": "medalhao_lina", "flag": "pegou_medalhao"}, sprite="locket")
# estátuas do vitral (puzzle 3): devem olhar para o vitral central
for pid, x in (("estatua_esq", 26), ("estatua_meio", 30), ("estatua_dir", 34)):
    E(x, 15, type="dial", id=pid, sprite="king_statue", symbols=["sul", "leste", "norte", "oeste"], state=0, prompt="Girar estátua")
E(8, 22, type="door", id="passagem_vitral", sprite="secret_wall", half=[0.5, 0.5], top=3.0, message="Uma passagem se abre atrás da parede!")
E(5, 21, type="document", doc="fragmento_ciclo_1", sprite="bone_shard")
E(4, 22, type="chest", id="bau_secreto_castelo", loot=[{"rune": "trovao"}, {"points": 1}])
# alavancas das alas (puzzle 4): abrem o portão do salão da lua
E(4, 6, type="lever", id="alavanca_oeste", targets=["portao_lua"])
E(55, 6, type="lever", id="alavanca_leste", targets=["portao_lua"])
E(30, 4, type="door", id="portao_lua", need=2, sprite="gate_iron", half=[2.5, 0.5], top=3.5, message="Os dois mecanismos giram. O Salão da Lua Partida está aberto.")
E(30, 1, type="exit", id="entrada_arena", to="ato1_arena", spawn="entrada", label="Salão da Lua Partida", auto=True)
# salão da condessa
E(43, 23, type="door", id="porta_salao_carmesim", key="chave_castelo", sprite="door_red", half=[0.5, 0.5], top=3.0)
E(44, 23, type="door", id="salao_tranca", sprite="blood_seal", half=[0.5, 0.5], top=3.0, open=True, transient=True,
  close_on="boss_start", open_on="boss_defeated")
E(51, 23, type="boss", boss="condessa_rubra", angle=180)
E(55, 26, type="chest", id="bau_condessa", loot=[{"materials": 4}], **{"if": {"flag": "boss:condessa_rubra"}})
# luzes
for (x, r) in ((22, 34), (38, 33), (15, 42), (44, 42), (28, 38), (32, 43)):
    E(x, r, type="decor", sprite="wall_torch", light={"color": [1.0, 0.55, 0.25], "intensity": 1.8, "radius": 6.0, "h": 1.8, "flicker": 0.3})
for (x, r) in ((26, 9), (34, 9), (26, 14), (34, 14), (6, 12), (15, 15), (45, 12), (53, 15), (10, 25), (20, 21), (40, 21), (50, 22)):
    E(x, r, type="decor", sprite="candelabra", light={"color": [1.0, 0.7, 0.35], "intensity": 1.6, "radius": 5.5, "h": 1.5, "flicker": 0.2})
for (x, r) in ((47, 20), (53, 20), (47, 26), (53, 26)):
    E(x, r, type="decor", sprite="blood_candle", light={"color": [1.0, 0.15, 0.2], "intensity": 1.8, "radius": 5.0, "h": 1.2, "flicker": 0.25})
for (x, r) in ((15, 21), (45, 24)):
    E(x, r, type="decor", sprite="statue_knight", solid=True, half=[0.4, 0.4], top=2.5)
for (x, r) in ((5, 14), (14, 14), (42, 7), (46, 16)):
    E(x, r, type="decor", sprite="armor_stand", solid=True, half=[0.3, 0.3], top=1.8)
# inimigos
for (x, r) in ((14, 41), (22, 43), (40, 41), (50, 43), (30, 36), (44, 34)):
    E(x, r, type="enemy", enemy="esqueleto")
E(15, 34, type="enemy", enemy="guarda_morto")
for (x, r) in ((22, 22), (38, 25)):
    E(x, r, type="enemy", enemy="guarda_morto")
E(12, 25, type="enemy", enemy="cacador_amaldicoado")
for (x, r) in ((34, 21), (36, 22)):
    E(x, r, type="enemy", enemy="lobo_corrompido")
E(8, 11, type="enemy", enemy="licano")
for (x, r) in ((14, 10), (16, 14)):
    E(x, r, type="enemy", enemy="esqueleto")
for (x, r) in ((44, 10), (52, 13)):
    E(x, r, type="enemy", enemy="vampiro_menor")
for (x, r) in ((48, 7), (55, 12)):
    E(x, r, type="enemy", enemy="morcego_sanguineo")
E(30, 11, type="enemy", enemy="guarda_morto", elite=True, unique="a1_capitao")
E(26, 16, type="enemy", enemy="vampiro_menor")
for (x, r) in ((10, 20), (25, 26), (50, 7)):
    E(x, r, type="breakable", sprite="urn")

puzzles = [
 {"id": "luz_cripta", "type": "beam", "props": ["receptor_cripta"], "message": "O feixe de luar atravessa a cripta!", "grace": 150},
 {"id": "estatuas_vitral", "type": "combination", "props": ["estatua_esq", "estatua_meio", "estatua_dir"], "solution": ["leste", "norte", "oeste"],
  "open": ["passagem_vitral"], "lock": ["estatua_esq", "estatua_meio", "estatua_dir"], "message": "Os três reis contemplam o vitral. Algo range na ala oeste do pátio.", "grace": 200},
 {"id": "alavancas_alas", "type": "all_on", "props": ["alavanca_oeste", "alavanca_leste"], "message": "O portão do Salão da Lua Partida está aberto.", "grace": 100}]
regions = [
 {"id": "cripta", "name": "Cripta de Velmora", "rect": g.rect_world(1, 31, 58, 46)},
 {"id": "patio", "name": "Pátio do Castelo", "rect": g.rect_world(1, 19, 42, 30)},
 {"id": "salao_carmesim", "name": "Salão Carmesim", "rect": g.rect_world(43, 19, 58, 27)},
 {"id": "castelo", "name": "Castelo de Varkhan", "rect": [0, 0, W, D]}]
save({"id": "ato1_castelo", "name": "Castelo de Varkhan", "act": 1, "theme": "ato1_castelo", "env": "lua_castelo", "music": "ato1",
      "rows": g.rows(), "entities": g.entities, "puzzles": puzzles, "regions": regions})
