"""Santuário da Última Chama (hub)."""
from grade import Grade
from comum import save

g = Grade(40, 30, ".")
g.border("#", north="H")
g.rect(1, 1, 38, 3, "1")
g.rect(1, 4, 13, 4, "1")
g.rect(26, 4, 38, 4, "1")
g.rect(14, 4, 25, 4, "a")
# forja (oeste)
g.rect(1, 6, 9, 6, "#")
g.rect(9, 6, 9, 8, "#")
g.rect(9, 11, 9, 12, "#")
g.rect(1, 7, 8, 12, ",")
# biblioteca (leste)
g.rect(30, 6, 38, 6, "B")
g.rect(30, 6, 30, 8, "B")
g.rect(30, 11, 30, 12, "B")
g.rect(31, 7, 38, 12, "_")
# anel de runas em volta da Graça
for x in range(14, 27):
    for r in range(9, 20):
        dx, dr = x - 20, (r - 14) * 1.0
        d = (dx * dx + dr * dr) ** 0.5
        if 3.6 <= d <= 4.5:
            g.put(x, r, ":")
# pilares
for (x, r) in ((12, 8), (27, 8), (12, 20), (27, 20)):
    g.put(x, r, "P")
# pátio de treino (sudeste) com cerca baixa
g.frame(29, 17, 38, 26, "h")
g.rect(29, 21, 29, 22, ".")
g.rect(30, 18, 37, 25, ",")
# entrada sul
g.rect(19, 21, 21, 28, "_")
# árvores e água
for (x, r) in ((2, 27), (4, 25), (2, 23), (6, 27), (12, 27), (26, 27), (28, 28)):
    g.put(x, r, "T")
g.rect(2, 15, 5, 18, "w")

# entidades
g.ent(20, 14, type="grace", id="graca_santuario", name="Santuário da Última Chama")
g.ent(20, 24, type="spawn", id="inicio", angle=90)
g.ent(20, 10, type="npc", npc="velaria", angle=-90)
g.ent(5, 9, type="npc", npc="ferrus", angle=0)
g.ent(7, 22, type="npc", npc="oriana", angle=0)
g.ent(32, 20, type="npc", npc="kaelen", angle=180)
g.ent(35, 9, type="npc", npc="theodric", angle=-90)
g.ent(32, 8, type="document", doc="livro_portadores", sprite="lectern")
g.ent(37, 2, type="document", doc="carta_velaria", sprite="note")
g.ent(6, 8, type="decor", sprite="anvil", solid=True, half=[0.4, 0.3], top=1.0)
g.ent(3, 8, type="decor", sprite="forge", solid=True, half=[0.6, 0.5], top=1.5,
      light={"color": [1.0, 0.5, 0.2], "intensity": 2.6, "radius": 7, "h": 1.2, "flicker": 0.25})
g.ent(5, 22, type="decor", sprite="cart", solid=True, half=[0.8, 0.5], top=1.5)
g.ent(4, 21, type="decor", sprite="lantern", light={"color": [1.0, 0.75, 0.4], "intensity": 1.5, "radius": 5, "h": 1.6, "flicker": 0.1})
for (x, r) in ((16, 11), (24, 11), (16, 17), (24, 17)):
    g.ent(x, r, type="decor", sprite="brazier", solid=True, half=[0.3, 0.3], top=1.0,
          light={"color": [1.0, 0.62, 0.3], "intensity": 2.0, "radius": 6.5, "h": 1.3, "flicker": 0.2})
for (x, r) in ((33, 23), (36, 23), (36, 19)):
    g.ent(x, r, type="enemy", enemy="boneco_treino", angle=180)
for (x, r) in ((2, 13), (37, 13)):
    g.ent(x, r, type="decor", sprite="candelabra", light={"color": [1.0, 0.8, 0.45], "intensity": 1.4, "radius": 5, "h": 1.5, "flicker": 0.15})
# portais dos atos (no terraço)
acts = [("ato1", "Ato I — Lua Sangrenta", "ato1_floresta", "intro_velaria", (0.9, 0.2, 0.2)),
        ("ato2", "Ato II — Forja das Almas", "ato2_cidade", "ato1_concluido", (1.0, 0.55, 0.15)),
        ("ato3", "Ato III — Catedral da Carne", "ato3_catedral", "ato2_concluido", (0.9, 0.75, 0.5)),
        ("ato4", "Ato IV — Observatório do Abismo", "ato4_biblioteca", "ato3_concluido", (0.5, 0.4, 1.0)),
        ("ato5", "Ato V — Trono da Graça", "ato5_ruinas", "ato4_concluido", (1.0, 0.9, 0.6))]
for i, (aid, label, lvl, req, col) in enumerate(acts):
    x = 5 + i * 7
    g.ent(x, 2, type="exit", id=f"portal_{aid}", to=lvl, spawn="inicio", label=f"Portal: {label}", auto=False,
          require_flag=req, locked_text="O portal está selado. Ainda não é hora.", sprite="portal_gate", color=list(col))
    g.ent(x, 5, type="spawn", id=f"retorno_{aid}", angle=-90)
    g.ent(x - 2, 1, type="decor", sprite=f"trofeu_{aid}", **{"if": {"flag": f"{aid}_concluido" if aid != "ato5" else "aurelion_derrotado"}},
          light={"color": list(col), "intensity": 1.2, "radius": 3.5, "h": 1.2, "flicker": 0.0})
for x in (2, 37):
    g.ent(x, 3, type="decor", sprite="banner")

save({"id": "santuario", "name": "Santuário da Última Chama", "act": 0, "theme": "santuario", "env": "santuario",
      "music": "santuario", "rows": g.rows(), "entities": g.entities, "safe": True,
      "regions": [{"id": "santuario", "name": "Santuário da Última Chama", "rect": [0, 0, 40, 30]}]})
