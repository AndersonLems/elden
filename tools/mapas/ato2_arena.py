"""Ato II, arena: Núcleo da Forja (SERAFIM-09)."""
import math
from grade import Grade
from comum import save

W, D = 32, 30
g = Grade(W, D, "#")
g.border("P", north="H")
cx, cr, raio = 16, 13, 11.0
for r in range(1, D - 1):
    for x in range(1, W - 1):
        d = math.hypot(x - cx, r - cr)
        if d <= raio:
            # placas de cobre no núcleo, anel de grelhas e fuligem na borda
            g.put(x, r, "_" if d <= 3.2 else (":" if 6.5 <= d <= 7.5 else ("," if d > 9.5 else ".")))
# poças de escória nos cantos, fora do círculo de combate
for (x, r) in ((5, 4), (26, 4), (5, 22), (26, 22)):
    g.rect(x - 1, r - 1, x + 1, r + 1, "w")
# corredor do elevador: o círculo só toca a linha 24 no centro, então a névoa nessa linha fecha a arena
g.rect(15, 24, 17, 28, ".")

E = g.ent
E(16, 27, type="spawn", id="entrada", angle=90)
E(16, 28, type="exit", id="saida_arena", to="ato2_fabrica", spawn="graca_elevador", label="Subir à Casa de Máquinas", auto=False,
  sprite="stairs_down")
E(16, 24, type="door", id="nevoa_arena", sprite="fog_gate", half=[1.5, 0.5], top=3.0, open=True, transient=True,
  close_on="boss_start", open_on="boss_defeated")
E(16, 5, type="boss", boss="serafim_09", angle=-90)
E(16, 13, type="exit", id="portal_vitoria", to="santuario", spawn="retorno_ato2", label="Retornar ao Santuário", auto=False,
  sprite="portal_gate", color=[1.0, 0.55, 0.15], **{"if": {"flag": "boss:serafim_09"}})
E(14, 13, type="grace", id="graca_nucleo", name="Núcleo da Forja", **{"if": {"flag": "boss:serafim_09"}})

# jatos de chama na borda, apontados para o núcleo: inativos sozinhos, o SERAFIM-09 os dispara a partir da fase 2
ox, oz = g.pos(cx, cr)
for i in range(6):
    a = i / 6 * math.tau
    x = round(cx + math.cos(a) * (raio - 0.5))
    r = round(cr + math.sin(a) * (raio - 0.5))
    wx, wz = g.pos(x, r)
    ang = math.degrees(math.atan2(oz - wz, ox - wx))
    E(x, r, type="hazard", id=f"forja_jato_{i}", hazard="flame", active=False, sprite="flame_vent",
      length=6 + (i % 3), angle=round(ang, 1), element="fogo")

for i in range(4):
    a = i / 4 * math.tau + math.pi / 4
    E(round(cx + math.cos(a) * 8.5), round(cr + math.sin(a) * 8.5), type="decor", sprite="gear", solid=True,
      half=[0.5, 0.5], top=1.0)
for (x, r) in ((6, 9), (26, 9), (6, 17), (26, 17)):
    E(x, r, type="decor", sprite="forge", solid=True, half=[0.6, 0.5], top=1.5,
      light={"color": [1.0, 0.45, 0.15], "intensity": 2.4, "radius": 7, "h": 1.2, "flicker": 0.3})
for (x, r) in ((13, 22), (19, 22)):
    E(x, r, type="decor", sprite="brazier", solid=True, half=[0.3, 0.3], top=1.0,
      light={"color": [1.0, 0.5, 0.2], "intensity": 2.0, "radius": 6, "h": 1.3, "flicker": 0.3})

save({"id": "ato2_arena", "name": "Núcleo da Forja", "act": 2, "theme": "ato2", "env": "forja_arena", "music": "chefe2",
      "rows": g.rows(), "entities": g.entities, "arena_center": [ox, oz], "boss_arena": True,
      "regions": [{"id": "arena", "name": "Núcleo da Forja", "rect": [0, 0, W, D]}]})
