"""Ato III, arena: Santuário da Carne (O SANTO IMPERFEITO)."""
import math
from grade import Grade
from comum import save

W, D = 30, 30
g = Grade(W, D, "#")
g.border("H", north="H")
cx, cr, raio = 15, 13, 10.5
for r in range(1, D - 1):
    for x in range(1, W - 1):
        d = math.hypot(x - cx, r - cr)
        if d <= raio:
            # tapete de carne no centro, nave de mármore ao redor e ossos na borda
            g.put(x, r, ":" if d <= 3.0 else ("_" if abs(x - cx) <= 1 and r > cr else (";" if d > 8.6 else ".")))
# poças de sangue que retardam (não ferem)
for (x, r) in ((9, 8), (21, 8), (8, 18), (22, 18)):
    g.rect(x, r, x + 1, r, "w")
# corredor de entrada: a névoa fica na linha 24, onde o círculo já terminou
g.rect(14, 24, 16, 28, ".")

E = g.ent
E(15, 27, type="spawn", id="entrada", angle=90)
E(15, 28, type="exit", id="saida_arena", to="ato3_laboratorio", spawn="graca_antecamara", label="Voltar à antecâmara",
  auto=False, sprite="stairs_down")
E(15, 24, type="door", id="nevoa_arena", sprite="fog_gate", half=[1.5, 0.5], top=3.0, open=True, transient=True,
  close_on="boss_start", open_on="boss_defeated")
E(15, 5, type="boss", boss="santo_imperfeito", angle=-90)
ox, oz = g.pos(cx, cr)
E(15, 13, type="exit", id="portal_vitoria", to="santuario", spawn="retorno_ato3", label="Retornar ao Santuário", auto=False,
  sprite="portal_gate", color=[0.95, 0.35, 0.4], **{"if": {"flag": "boss:santo_imperfeito"}})
E(13, 13, type="grace", id="graca_carne", name="Santuário da Carne", **{"if": {"flag": "boss:santo_imperfeito"}})
for i in range(6):
    a = i / 6 * math.tau + math.pi / 6
    E(round(cx + math.cos(a) * 7.0), round(cr + math.sin(a) * 7.0), type="decor", sprite="candelabra",
      light={"color": [1.0, 0.6, 0.45], "intensity": 1.7, "radius": 6, "h": 1.6, "flicker": 0.25})
for (x, r) in ((11, 3), (19, 3)):
    E(x, r, type="decor", sprite="angel_statue", solid=True, half=[0.4, 0.4], top=2.2)
E(15, 3, type="decor", sprite="halo_broken", light={"color": [1.0, 0.85, 0.5], "intensity": 2.2, "radius": 8, "h": 2.5, "flicker": 0.1})

save({"id": "ato3_arena", "name": "Santuário da Carne", "act": 3, "theme": "ato3_catedral", "env": "catedral_arena",
      "music": "chefe3", "rows": g.rows(), "entities": g.entities, "arena_center": [ox, oz], "boss_arena": True,
      "regions": [{"id": "arena", "name": "Santuário da Carne", "rect": [0, 0, W, D]}]})
