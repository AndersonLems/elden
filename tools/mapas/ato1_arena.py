"""Ato I, arena: Salão da Lua Partida (VARKHAN)."""
import math
from grade import Grade
from comum import save

W, D = 30, 28
g = Grade(W, D, "#")
g.border("H", north="H")
cx, cr = 15, 13
for r in range(1, D - 1):
    for x in range(1, W - 1):
        d = math.hypot(x - cx, (r - cr) * 1.0)
        if d <= 11.5:
            g.put(x, r, "." if d > 3 else ",")
# poças de sangue e corredor de entrada
for (x, r) in ((8, 8), (21, 9), (10, 19), (20, 18)):
    g.rect(x - 1, r - 1, x + 1, r, "w")
g.rect(14, 24, 16, 26, ".")
E = g.ent
E(15, 25, type="spawn", id="entrada", angle=90)
E(15, 26, type="exit", id="saida_arena", to="ato1_castelo", spawn="salao", label="Voltar ao castelo", auto=False, sprite="stairs_down")
E(15, 23, type="door", id="nevoa_arena", sprite="fog_gate", half=[1.5, 0.5], top=3.0, open=True, transient=True,
  close_on="boss_start", open_on="boss_defeated")
E(15, 7, type="boss", boss="varkhan", angle=-90)
E(15, 13, type="exit", id="portal_vitoria", to="santuario", spawn="retorno_ato1", label="Retornar ao Santuário", auto=False,
  sprite="portal_gate", color=[0.9, 0.2, 0.2], **{"if": {"flag": "boss:varkhan"}})
E(13, 13, type="grace", id="graca_lua", name="Salão da Lua Partida", **{"if": {"flag": "boss:varkhan"}})
for i in range(8):
    a = i / 8 * math.tau
    x = round(cx + math.cos(a) * 7.5)
    r = round(cr + math.sin(a) * 7.5)
    E(x, r, type="arena_pillar", id=f"arena_pilar_{i}", sprite="pillar_broken" if i % 2 else "pillar")
for i in range(6):
    a = i / 6 * math.tau + 0.3
    x = round(cx + math.cos(a) * 10.5)
    r = round(cr + math.sin(a) * 10.5)
    E(x, r, type="decor", sprite="brazier_red", light={"color": [1.0, 0.25, 0.15], "intensity": 2.4, "radius": 8, "h": 1.4, "flicker": 0.3})
save({"id": "ato1_arena", "name": "Salão da Lua Partida", "act": 1, "theme": "ato1_castelo", "env": "lua_arena", "music": "chefe1",
      "rows": g.rows(), "entities": g.entities, "arena_center": list(g.pos(cx, cr)), "boss_arena": True,
      "regions": [{"id": "arena", "name": "Salão da Lua Partida", "rect": [0, 0, W, D]}]})
