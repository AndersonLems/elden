"""Ato IV, arena: Cúpula Partida (MALACHAR). Na fase 3 só o círculo central (raio 6,5) é seguro."""
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
            # o anel de runas marca o círculo seguro da fase final; fora dele, piso astral
            g.put(x, r, ":" if d <= 6.5 else (";" if d > 7.5 else "."))
g.rect(14, 24, 16, 28, ".")

E = g.ent
E(15, 27, type="spawn", id="entrada", angle=90)
E(15, 28, type="exit", id="saida_arena", to="ato4_observatorio", spawn="graca_planetario", label="Voltar ao planetário",
  auto=False, sprite="stairs_down")
E(15, 24, type="door", id="nevoa_arena", sprite="fog_gate", half=[1.5, 0.5], top=3.0, open=True, transient=True,
  close_on="boss_start", open_on="boss_defeated")
E(15, 6, type="boss", boss="malachar", angle=-90)
ox, oz = g.pos(cx, cr)
E(15, 13, type="exit", id="portal_vitoria", to="santuario", spawn="retorno_ato4", label="Retornar ao Santuário", auto=False,
  sprite="portal_gate", color=[0.6, 0.45, 1.0], **{"if": {"flag": "boss:malachar"}})
E(13, 13, type="grace", id="graca_cupula", name="Cúpula Partida", **{"if": {"flag": "boss:malachar"}})
for i in range(8):
    a = i / 8 * math.tau
    E(round(cx + math.cos(a) * 9.5), round(cr + math.sin(a) * 9.5), type="decor", sprite="crystal_cluster",
      light={"color": [0.55, 0.5, 1.0], "intensity": 1.4, "radius": 5, "h": 1.0, "flicker": 0.15})
E(15, 3, type="decor", sprite="telescope", solid=True, half=[0.5, 0.5], top=2.0)

save({"id": "ato4_arena", "name": "Cúpula Partida", "act": 4, "theme": "ato4", "env": "observatorio_arena", "music": "chefe4",
      "rows": g.rows(), "entities": g.entities, "arena_center": [ox, oz], "boss_arena": True,
      "regions": [{"id": "arena", "name": "Cúpula Partida", "rect": [0, 0, W, D]}]})
