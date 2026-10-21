# AGENTS.md — guia para quem (humano ou IA) continuar o ELDEN

Leia também: `MEMORY.md` (decisões e armadilhas já descobertas) e `docs/CONTEXTO.md` (pedido original, plano dos atos e formatos de dados).

## Regras do projeto
- **Idioma:** textos de jogo, comentários e docstrings em **português do Brasil**.
- **Python 3.10+**, engine **Ursina 8 + Panda3D 1.10**. Não trocar de engine.
- **Conteúdo em JSON** (`data/`). O código interpreta os dados; prefira adicionar conteúdo por dados.
- **`elden/sim/` não importa nada de renderização.** A simulação é testável sem janela. A ponte com a apresentação é `world.fx` (fila de eventos visuais/sonoros) e `elden/render_bridge.py` (luzes como dados).
- O estilo do código segue o existente: classes pequenas, herança (`Entity → Actor → Player/Enemy → Boss`, `Prop → Door/Lever/...`, `Scene → Overlay → MenuOverlay`).
- **Não declare algo pronto sem testar.** Rode os testes e, para mudanças visuais, as ferramentas de captura.

## Comandos
```bash
python3 main.py                                   # jogar (janela 1280x720)
python3 -m unittest discover -s tests -v          # testes sem janela
python3 -c "import sys; sys.path.insert(0,'.'); from elden.core.data import DB; print(DB.validate())"  # validar JSON
python3 tools/mapas/<fase>.py                     # regenerar data/levels/<fase>.json
python3 tools/gerar_assets.py                     # pré-gerar caches (sprites, sons, músicas)

# capturas automáticas (abre janela, posiciona o jogador e salva PNGs):
python3 tools/dev/tour.py /tmp/out ato1_floresta '[[9,6,"inicio"],[46,30,"vila"]]'
SPAWN=entrada python3 tools/dev/tour.py /tmp/out ato2_fabrica '[[30,40,"a"]]'
python3 tools/dev/ui_tour.py /tmp/out             # capturas das telas de interface
python3 tools/dev/perfil.py                       # tempo por quadro e cProfile
```
As ferramentas de captura desligam o vsync (`App({"novsync": True})`). **Com vsync, janelas escondidas
são limitadas a cerca de 1 FPS pelo compositor do sistema.** Nunca rode duas instâncias ao mesmo tempo
e não use `pkill -f <padrão>` num comando cujo próprio texto contém o padrão.

## Arquitetura rápida
- `elden/app.py`: janela, pipeline, pilha de cenas (`push`/`pop`/`replace`/`transition`), interface (pygame → textura) e áudio.
- `elden/sim/world/loader.py`: `build_world(session, level_id, spawn)` monta o `World` a partir do JSON.
- `elden/sim/session.py`: progresso, flags, recompensas (`grant`), missões e pedidos para as cenas (`session.events`: rest, travel, dialogue, document, boss_choice, ending_choice).
- `elden/scenes/gameplay.py`: laço do jogo, carregamento, descanso, morte e respawn.
- `elden/render/scene_view.py`: cria as vistas das entidades, luzes e câmera; `render/fx.py` traduz os eventos `world.fx`.
- Sprites: `elden/art/characters.py` (aparência), `anims.py` (poses), `rig.py` (rasterizador) e `spritegen.py` (folhas e cache, geradas em paralelo).

## Como criar um mapa novo
1. Copie um gerador de `tools/mapas/` (por exemplo `ato2_fabrica.py`). Use `Grade` (`rect`, `frame`, `put`, `ent`) e `carve`/`scatter`.
2. A primeira linha do texto é o **norte**. Use `g.ent(x, r, type=..., ...)` com coordenadas da grade (convertidas automaticamente).
3. Use as legendas de `data/themes.json` (tema do ato). Rampas sobem para o norte (`a` 0→1, `b` 1→2, `c` 2→3).
4. Para cada fase, inclua: `spawn` (ids usados pelas saídas), Graças (`grace`), saídas (`exit` com `to` e `spawn`), puzzles (`puzzles`), regiões nomeadas e inimigos (`enemy`, com `elite`/`unique`). Nas arenas, use `boss`, uma porta `close_on: boss_start` / `open_on: boss_defeated` e `arena_center`.
5. Rode o script, `DB.validate()`, os testes e um `tour.py` da fase.

## Pendências prioritárias (em ordem)
1. `ato2_arena` (Serafim-09). O chefe usa props `hazard` com `id` começando em `forja_jato`, mais `length` e `angle`.
2. Atos III, IV e V: 9 mapas no total. O plano detalhado está em `docs/CONTEXTO.md`. Os dados de inimigos, chefes, NPCs, documentos e missões já existem.
3. Teste de bot contra cada chefe (verificar que é vencível e justo) e teste de solução dos puzzles por fase.
4. Balanceamento e polimento visual.
