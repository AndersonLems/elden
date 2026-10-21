"""Ato I, parte 1: Floresta Carmesim, Vilarejo de Velmora e Cemitério."""
from grade import Grade, carve, scatter, protect
from comum import save

W, D = 64, 46
g = Grade(W, D, ".")
# piso base alternando musgo e folhas
import math, random
rng = random.Random(3)


def noise2(x, y, s):
    return (math.sin(x * 0.31 * s + 1.7) * math.cos(y * 0.27 * s - 0.9) + math.sin((x + y) * 0.13 * s + 2.1)) * 0.5


for r in range(D):
    for x in range(W):
        n = noise2(x, r, 1.0) + rng.uniform(-0.12, 0.12)
        g.put(x, r, "," if n > 0.25 else ";" if (n < -0.45 and r > 20) else ".")
g.border("#", north="#")
# caminho principal (terra): clareira SO -> norte -> leste -> vila -> cemitério
main = [(8, 41), (8, 33), (12, 29), (22, 29), (30, 27), (34, 22), (40, 17), (46, 16)]
to_cem = [(40, 17), (34, 13), (28, 11), (24, 10)]
lake_path = [(12, 29), (10, 24), (13, 20)]
carve(g, main, ":", 1)
carve(g, to_cem, ":", 1)
carve(g, lake_path, ";", 1)
# clareira inicial
g.rect(3, 35, 14, 43, ",")
# lago de sangue (oeste) com ilha
g.rect(2, 12, 11, 21, "w")
g.rect(5, 15, 7, 17, ",")
g.rect(8, 16, 11, 16, "=")
# saliência oculta perto do início (alcançada com salto)
g.rect(1, 25, 4, 28, "1")
# norte-oeste: plataforma do licano alfa com rampa
g.rect(2, 3, 9, 8, "1")
g.rect(5, 9, 6, 9, "a")
# vila de Velmora
g.rect(33, 7, 61, 25, "_")
houses = [(35, 8, 39, 11), (43, 7, 48, 10), (52, 8, 57, 12), (35, 19, 40, 23), (51, 19, 57, 23)]
for (a, b, c, d) in houses:
    g.rect(a, b, c, d, "C")
# casa em ruínas com parede falsa (segredo)
g.frame(43, 19, 48, 24, "C")
g.rect(44, 20, 47, 23, ".")
g.put(45, 24, "_")       # será a parede quebrável
# poço na praça
g.put(46, 13, "P")
# cemitério (noroeste/centro-norte)
g.rect(14, 3, 32, 14, "-")
g.frame(13, 2, 33, 15, "h")
for gap in ((23, 15), (24, 15), (25, 15), (33, 9), (33, 10), (13, 8)):
    g.put(*gap, "-")
# cripta (prédio com portão)
g.rect(20, 1, 28, 4, "H")
g.rect(23, 2, 25, 4, "-")
# lápides e cruzes
scatter(g, "t+", 0.18, 15, 5, 31, 13, keep="-", seed=11,
        avoid=protect([(24, 15), (24, 5)], 2) | protect([(14, 8), (33, 9)], 1))
# floresta densa
avoid = protect(main, 2) | protect(to_cem, 2) | protect(lake_path, 2)
avoid |= {(x, r) for x in range(3, 15) for r in range(34, 44)}
avoid |= {(x, r) for x in range(1, 12) for r in range(2, 23)}
avoid |= {(x, r) for x in range(13, 34) for r in range(1, 16)}
avoid |= {(x, r) for x in range(32, 62) for r in range(6, 26)}
avoid |= {(x, r) for x in range(17, 24) for r in range(28, 33)}
avoid |= {(x, r) for x in range(1, 6) for r in range(24, 30)}
scatter(g, "TTY", 0.42, 1, 1, 62, 44, keep=".,;", seed=5, avoid=avoid)
# bosque leste além da vila
g.rect(58, 27, 62, 44, ".")
bosque = [(50, 25), (50, 31), (54, 36), (58, 40), (60, 42)]
scatter(g, "TY", 0.5, 34, 27, 62, 44, keep=".,;", seed=8, avoid=protect(bosque, 2))
carve(g, bosque, ";", 1)
g.rect(54, 35, 58, 37, ",")

E = g.ent
E(8, 41, type="spawn", id="inicio", angle=90)
E(6, 42, type="exit", id="volta_santuario", to="santuario", spawn="retorno_ato1", label="Voltar ao Santuário", auto=False, sprite="portal_gate", color=[0.9, 0.2, 0.2])
E(10, 38, type="grace", id="graca_clareira", name="Clareira do Despertar")
E(46, 15, type="grace", id="graca_velmora", name="Praça de Velmora")
E(24, 12, type="grace", id="graca_cemiterio", name="Portões do Cemitério")
E(24, 6, type="spawn", id="saida_cripta", angle=-90)
E(24, 2, type="exit", id="descida_cripta", to="ato1_castelo", spawn="cripta", label="Descer à cripta", auto=True)
E(24, 4, type="door", id="portao_cripta", sprite="gate_iron", half=[1.5, 0.5], top=3.0, message="O selo lunar se abre com um gemido de pedra.")
# selo lunar (puzzle 1)
for pid, (x, r) in (("dial_leste", (26, 7)), ("dial_norte", (24, 6)), ("dial_oeste", (22, 7)), ("dial_sul", (24, 8))):
    E(x, r, type="dial", id=pid, sprite="moon_dial", symbols=["lua_nova", "crescente", "cheia", "minguante"], state=2)
E(21, 9, type="document", doc="inscricao_cripta", sprite="stone_tablet")
# NPC Bram e acampamento
E(20, 30, type="npc", npc="bram", angle=-90)
E(21, 31, type="decor", sprite="campfire", light={"color": [1.0, 0.55, 0.2], "intensity": 2.4, "radius": 7.5, "h": 0.8, "flicker": 0.3})
E(18, 31, type="document", doc="diario_cacador", sprite="note")
# tochas e postes da vila
for (x, r) in ((34, 15), (42, 14), (50, 14), (58, 16), (42, 21), (49, 18), (37, 17), (56, 24)):
    E(x, r, type="decor", sprite="lamp_post", solid=True, half=[0.2, 0.2], top=2.5,
      light={"color": [1.0, 0.6, 0.3], "intensity": 1.9, "radius": 6.5, "h": 2.2, "flicker": 0.15})
for (x, r) in ((16, 4), (31, 4), (23, 5), (25, 5)):
    E(x, r, type="decor", sprite="candelabra", light={"color": [0.9, 0.3, 0.3], "intensity": 1.3, "radius": 4.5, "h": 1.4, "flicker": 0.2})
E(9, 30, type="decor", sprite="shrine", light={"color": [0.8, 0.2, 0.25], "intensity": 1.0, "radius": 4.0, "h": 1.0, "flicker": 0.1})
# segredos e recompensas
E(45, 24, type="breakable_wall", id="parede_velmora", sprite="cracked_wall_brick", hp=2)
E(45, 21, type="chest", id="bau_velmora_secreto", loot=[{"rune": "marca_negra"}, {"grace": 250}])
E(2, 26, type="chest", id="bau_saliência", loot=[{"materials": 3}, {"item": "lagrima_eter"}])
E(4, 4, type="chest", id="bau_licano", loot=[{"weapon": "espadao_ferro"}, {"materials": 2}])
E(6, 16, type="chest", id="bau_ilha", loot=[{"rune": "sede"}])
E(60, 42, type="chest", id="bau_bosque", loot=[{"item": "frasco_brasa"}])
E(55, 13, type="document", doc="cronica_licanos", sprite="note")   # pregado na porta da casa
for (x, r) in ((38, 14), (39, 14), (53, 16), (54, 17), (41, 24), (58, 20), (60, 9)):
    E(x, r, type="breakable", sprite="barrel")
# altar profano (corrupção) escondido no bosque
E(56, 36, type="altar", id="altar_lua", altar="profano", prompt="Oferecer sangue ao altar", reward=[{"rune": "lua_cheia"}, {"grace": 200}])
# inimigos
for (x, r) in ((14, 31), (16, 33), (15, 28)):
    E(x, r, type="enemy", enemy="lobo_corrompido")
for (x, r) in ((20, 24), (26, 26), (30, 22), (12, 22)):
    E(x, r, type="enemy", enemy="esqueleto")
E(8, 7, type="enemy", enemy="licano", elite=True, unique="a1_licano_alfa")
E(10, 10, type="enemy", enemy="lobo_corrompido")
for (x, r) in ((41, 16), (53, 18)):
    E(x, r, type="enemy", enemy="cacador_amaldicoado")
for (x, r) in ((47, 22), (56, 14), (37, 13)):
    E(x, r, type="enemy", enemy="vampiro_menor")
for (x, r) in ((18, 8), (29, 9)):
    E(x, r, type="enemy", enemy="guarda_morto")
for (x, r) in ((16, 5), (31, 12), (20, 12), (28, 5)):
    E(x, r, type="enemy", enemy="esqueleto")
E(48, 38, type="enemy", enemy="licano")
E(44, 34, type="enemy", enemy="lobo_corrompido")
E(52, 40, type="enemy", enemy="lobo_corrompido")

puzzles = [{"id": "selo_lunar", "type": "combination", "props": ["dial_leste", "dial_norte", "dial_oeste", "dial_sul"],
            "solution": ["lua_nova", "crescente", "cheia", "minguante"], "open": ["portao_cripta"], "lock": ["dial_leste", "dial_norte", "dial_oeste", "dial_sul"],
            "message": "As fases da lua se alinham. O selo da cripta se rompe!", "grace": 150}]
regions = [
 {"id": "clareira", "name": "Clareira do Despertar", "rect": g.rect_world(1, 33, 16, 44)},
 {"id": "lago", "name": "Lago de Sangue", "rect": g.rect_world(1, 2, 12, 23)},
 {"id": "cemiterio", "name": "Cemitério de Velmora", "rect": g.rect_world(13, 1, 33, 16)},
 {"id": "vila", "name": "Vilarejo de Velmora", "rect": g.rect_world(33, 6, 62, 26)},
 {"id": "floresta", "name": "Floresta Carmesim", "rect": [0, 0, W, D]}]
save({"id": "ato1_floresta", "name": "Floresta Carmesim", "act": 1, "theme": "ato1_floresta", "env": "lua_floresta", "music": "ato1",
      "rows": g.rows(), "entities": g.entities, "puzzles": puzzles, "regions": regions})
