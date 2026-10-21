"""Ato V, arena: Trono da Graça (AURELION). Depois da vitória, o altar do Trono abre a escolha do final."""
import math
from grade import Grade
from comum import save

W, D = 34, 34
g = Grade(W, D, "#")
g.border("H", north="H")
cx, cr, raio = 17, 15, 12.0
for r in range(1, D - 1):
    for x in range(1, W - 1):
        d = math.hypot(x - cx, r - cr)
        if d <= raio:
            g.put(x, r, ";" if d <= 2.5 else (":" if 7.5 <= d <= 8.4 else ("," if d > 10.8 else ".")))
# tapete até o trono e o estrado do trono ao norte (degrau baixo)
g.rect(16, 4, 18, 26, "_")
g.rect(14, 3, 20, 4, "1")
g.rect(16, 5, 18, 5, "a")
g.rect(16, 28, 18, 32, ".")

E = g.ent
E(17, 31, type="spawn", id="entrada", angle=90)
E(17, 32, type="exit", id="saida_arena", to="ato5_templo", spawn="graca_escadaria_trono", label="Descer ao Templo",
  auto=False, sprite="stairs_down")
E(17, 28, type="door", id="nevoa_arena", sprite="fog_gate", half=[1.5, 0.5], top=3.0, open=True, transient=True,
  close_on="boss_start", open_on="boss_defeated")
E(17, 8, type="boss", boss="aurelion", angle=-90)
ox, oz = g.pos(cx, cr)
E(17, 3, type="altar", id="altar_trono", altar="trono", prompt="Sentar no Trono da Graça", sprite="altar", once=False,
  **{"if": {"flag": "aurelion_derrotado"}})
E(15, 15, type="grace", id="graca_trono", name="Trono da Graça", **{"if": {"flag": "boss:aurelion"}})
E(19, 15, type="document", doc="fragmento_ciclo_5", sprite="item_glow", **{"if": {"flag": "boss:aurelion"}})
E(17, 17, type="exit", id="portal_vitoria", to="santuario", spawn="retorno_ato5", label="Retornar ao Santuário", auto=False,
  sprite="portal_gate", color=[1.0, 0.9, 0.6], **{"if": {"flag": "boss:aurelion"}})
for i in range(8):
    a = i / 8 * math.tau + math.pi / 8
    E(round(cx + math.cos(a) * 10.0), round(cr + math.sin(a) * 10.0), type="decor", sprite="angel_statue", solid=True,
      half=[0.4, 0.4], top=2.2)
for (x, r) in ((14, 3), (20, 3)):
    E(x, r, type="decor", sprite="brazier_gold", solid=True, half=[0.3, 0.3], top=1.0,
      light={"color": [1.0, 0.88, 0.55], "intensity": 2.4, "radius": 8, "h": 1.4, "flicker": 0.1})

save({"id": "ato5_arena", "name": "Trono da Graça", "act": 5, "theme": "ato5", "env": "trono_arena", "music": "chefe5",
      "rows": g.rows(), "entities": g.entities, "arena_center": [ox, oz], "boss_arena": True,
      "regions": [{"id": "arena", "name": "Trono da Graça", "rect": [0, 0, W, D]}]})
