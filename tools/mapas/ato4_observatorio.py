"""Ato IV, parte 2: Observatório (espelhos e lente, patamares, plataforma sobre o vazio e o relógio astral)."""
from grade import Grade
from comum import save

W, D = 60, 56
g = Grade(W, D, "#")
g.border("H", north="H")
# vestíbulo (sul)
g.rect(20, 44, 40, 53, ".")
g.rect(30, 54, 30, 54, ".")
# sala dos espelhos (oeste)
g.rect(4, 30, 19, 43, ":")
g.rect(20, 39, 28, 41, ".")
# corredor norte até os patamares (a porta da torre abre com os três cristais)
g.rect(29, 29, 31, 43, ".")
g.rect(29, 28, 31, 28, "a")
g.rect(24, 22, 44, 27, "1")
g.rect(29, 21, 31, 21, "b")
# patamares altos cercados por pilares sólidos (topos de parede não podem ser alcançados)
g.rect(23, 2, 45, 21, "P")
g.rect(29, 21, 31, 21, "b")
g.rect(24, 14, 44, 20, "2")
g.rect(24, 10, 44, 13, "~")
g.rect(24, 3, 44, 9, "3")
# planetário (no patamar 3), paredes sólidas e porta trancada pela Chave do Planetário
g.rect(30, 3, 42, 6, "P")
g.rect(31, 3, 41, 5, "3")
g.put(36, 6, "3")
# jardim de telescópios (leste)
g.rect(46, 30, 56, 43, ";")
g.rect(32, 39, 45, 41, ".")

E = g.ent
E(30, 52, type="spawn", id="inicio", angle=90)
E(30, 54, type="exit", id="desce_biblioteca", to="ato4_biblioteca", spawn="escadaria", label="Descer à Biblioteca", auto=False,
  sprite="stairs_down")
E(25, 48, type="grace", id="graca_escadaria", name="Escadaria das Estrelas")

# espelhos: a lente aponta para leste; M1 manda ao norte (Coroa) ou ao sul (M2); M2 manda a oeste (Olho) ou leste (Espada)
E(4, 37, type="emitter", id="lente_solar", sprite="sun_lens", dir="E", color=[1.0, 0.9, 0.6])
E(12, 37, type="mirror", id="espelho_1", state=0)
E(12, 41, type="mirror", id="espelho_2", state=1)
E(12, 32, type="crystal", id="estrela_coroa", receiver=True, latch=True, sprite="crystal_gold", color=[1.0, 0.85, 0.4])
E(18, 41, type="crystal", id="estrela_espada", receiver=True, latch=True, sprite="crystal_gold", color=[1.0, 0.85, 0.4])
E(5, 41, type="crystal", id="estrela_olho", receiver=True, latch=True, sprite="crystal_gold", color=[1.0, 0.85, 0.4])
E(18, 31, type="document", doc="mapa_estelar", sprite="stone_tablet")
E(30, 36, type="door", id="porta_torre", sprite="gate", half=[1.5, 0.5], top=3.0,
  message="As três estrelas se acendem. A porta da torre se abre.")

# patamares e plataforma sobre o vazio
E(26, 26, type="document", doc="confissao_malachar", sprite="lectern")
E(42, 18, type="chest", id="bau_patamar", loot=[{"art": "art_reflexo_arcano"}, {"materials": 4}])
_, z0 = g.pos(34, 12)
_, z1 = g.pos(34, 10)
E(34, 12, type="platform", id="plataforma_astral", points=[[34.5, 2.0, z0], [34.5, 3.0, z1]], half=[1.0, 1.0], speed=1.2,
  wait=1.5, tex="rune_floor")
E(25, 4, type="grace", id="graca_planetario", name="Cúpula do Planetário")

# planetário: relógio astral (QUADRADO, X, CÍRCULO = 2, 5, 0)
E(36, 6, type="door", id="porta_planetario", key="chave_torre", sprite="gate_iron_small", half=[0.5, 0.5], top=3.0,
  consume_key=False, locked_text="Trancada. A Chave do Planetário está nas ilhas do vazio, na biblioteca.")
E(32, 5, type="document", doc="relogio_astral", sprite="telescope")
for i, x in enumerate((34, 36, 38)):
    E(x, 4, type="dial", id=f"anel_{i}", sprite="rune_dial", symbols=["círculo", "triângulo", "quadrado", "cruz", "losango", "x"],
      state=1, prompt="Girar anel do relógio")
E(41, 3, type="exit", id="portal_astral", to="ato4_arena", spawn="entrada", label="Atravessar para a Cúpula Partida",
  auto=False, sprite="portal_gate", color=[0.6, 0.4, 1.0], require_flag="puzzle:relogio_astral",
  locked_text="O portal está selado. Os anéis do relógio ainda não mostram a noite da queda.")

# jardim de telescópios
for (x, r) in ((48, 32), (54, 34), (50, 40)):
    E(x, r, type="decor", sprite="telescope", solid=True, half=[0.4, 0.4], top=1.6)
E(55, 42, type="chest", id="bau_telescopios", loot=[{"rune": "estrela_guia"}])
E(47, 41, type="altar", id="altar_estrelas", altar="profano", prompt="Oferecer sangue às estrelas", reward=[{"rune": "eclipse"}])

# luzes
for (x, r) in ((20, 46), (40, 46), (4, 31), (19, 43), (46, 31), (56, 43), (24, 23), (44, 23), (24, 15), (44, 15)):
    E(x, r, type="decor", sprite="wall_torch", light={"color": [0.55, 0.5, 1.0], "intensity": 1.6, "radius": 6, "h": 1.8, "flicker": 0.2})
for (x, r) in ((26, 8), (43, 8)):
    E(x, r, type="decor", sprite="brazier_blue", solid=True, half=[0.3, 0.3], top=1.0,
      light={"color": [0.5, 0.6, 1.0], "intensity": 2.0, "radius": 7, "h": 1.3, "flicker": 0.2})

# inimigos
for (x, r) in ((24, 46), (36, 50)):
    E(x, r, type="enemy", enemy="livro_voador")
for (x, r) in ((8, 33), (16, 35)):
    E(x, r, type="enemy", enemy="sombra_arcana")
E(30, 32, type="enemy", enemy="armadura_encantada")
for (x, r) in ((27, 24), (40, 25), (30, 17), (39, 16)):
    E(x, r, type="enemy", enemy="bruxo" if x < 35 else "bruxa")
E(36, 18, type="enemy", enemy="sentinela_runica")
for (x, r) in ((50, 36), (52, 31)):
    E(x, r, type="enemy", enemy="sentinela_runica" if x == 50 else "bruxa")
E(28, 6, type="enemy", enemy="bruxa", elite=True, unique="a4_astronoma")

puzzles = [
 {"id": "estrelas_espelhos", "type": "beam", "props": ["estrela_coroa", "estrela_espada", "estrela_olho"], "open": ["porta_torre"],
  "lock": ["espelho_1", "espelho_2"], "message": "Coroa, Espada e Olho brilham juntos.", "grace": 700},
 {"id": "relogio_astral", "type": "combination", "props": ["anel_0", "anel_1", "anel_2"], "solution": [2, 5, 0],
  "lock": ["anel_0", "anel_1", "anel_2"], "message": "Os anéis param na noite em que o deus caiu. O portal desperta.",
  "grace": 700}]
regions = [{"id": "vestibulo", "name": "Vestíbulo do Observatório", "rect": g.rect_world(19, 44, 41, 55)},
           {"id": "espelhos", "name": "Sala das Lentes", "rect": g.rect_world(3, 29, 21, 44)},
           {"id": "patamares", "name": "Patamares da Torre", "rect": g.rect_world(23, 10, 45, 28)},
           {"id": "planetario", "name": "Cúpula do Planetário", "rect": g.rect_world(23, 2, 45, 9)},
           {"id": "jardim", "name": "Jardim de Telescópios", "rect": g.rect_world(41, 29, 57, 44)},
           {"id": "observatorio", "name": "Observatório do Abismo", "rect": [0, 0, W, D]}]
save({"id": "ato4_observatorio", "name": "Observatório do Abismo", "act": 4, "theme": "ato4", "env": "observatorio",
      "music": "ato4", "rows": g.rows(), "entities": g.entities, "puzzles": puzzles, "regions": regions})
