# ARQUITETURA — mapa dos módulos

Mapa conciso para localizar código sem varrer o repositório. Detalhes de formato de dados: `docs/CONTEXTO.md`.
Linhas aproximadas em 2026-10-21.

## Camadas e dependências

```
main.py → elden/app.py ──► scenes/ ──► sim/      (simulação pura, sem janela)
                  │           │   └──► ui/       (pygame → textura BGRA)
                  │           └──────► render/   (Panda3D/Ursina, shaders)
                  └──► audio/                    render/ ──► art/ (sprites e texturas procedurais)
core/ (dados, caminhos, eventos, settings, saves) é usado por todos.
```

Regra dura: **`elden/sim/` nunca importa `render/`, `ui/`, `scenes/`, `audio/` nem Panda3D.**
A ponte sim → apresentação é `world.fx` (fila `FxQueue`) e `elden/render_bridge.py` (luzes como dados).

## Módulos

| Pasta | ~Linhas | Papel | Arquivos-chave |
|---|---:|---|---|
| `elden/core/` | 400 | `DB` (JSON de `data/` + `validate()`), caminhos, `FxQueue`, presets de qualidade, saves (3 slots) | `data.py`, `settings.py`, `events.py`, `saves.py` |
| `elden/sim/` (raiz) | — | `Entity → Actor → Player`, NPCs, clones, `Session` (flags, `grant`, missões, finais, `session.events`) | `entity.py`, `player.py`, `session.py`, `stats.py` |
| `elden/sim/combat/` | 2100 | `MoveAction` (janelas de hit/buffer/cancel), dano (aparar, bloqueio, postura, crítico, status, combos elementais), hitboxes, projéteis, `TriggerEngine` | `actions.py`, `damage.py`, `moves.py`, `triggers.py` |
| `elden/sim/ai/` | 1300 | `Brain` (FSM + fichas de ataque), inimigos, A* com vizinhos pré-calculados; `bosses/` com 6 chefes de 3 fases | `brain.py`, `navigation.py`, `bosses/base.py` |
| `elden/sim/world/` | 2000 | `World`, grade e física, props, puzzles, `build_world(session, level_id, spawn)` | `loader.py`, `world.py`, `props.py`, `puzzles.py` |
| `elden/sim/progression/` | 420 | personagem, árvore de Graça (aplica nós no grafo de golpes), loadout | `grace_tree.py`, `character.py` |
| `elden/render/` | 2500 | pipeline HDR (bloom, composite), malha da fase (4 faces), vistas de entidades, FX, luzes, **projeção semi-isométrica**, assets externos | `pipeline.py`, `projection.py`, `level_mesh.py`, `scene_view.py`, `views.py`, `fx.py`, `assets.py` |
| `elden/render/shaders/` | — | GLSL: world, sprite, decor, fx, post, bright, blur, composite, ui; `common.glsl` é incluído | — |
| `elden/art/` | 3300 | texturas por tile, esqueleto 3D (`rig.py`), poses (`anims.py`), aparência (`characters.py`), folhas em paralelo + cache (`spritegen.py`), sprites de props | — |
| `elden/ui/` | 900 | widgets, tema, ícones, HUD (pygame) | `hud.py`, `widgets.py` |
| `elden/scenes/` | 2300 | pilha de cenas: título, criação, jogo, menus (Graça, árvore, runas, armas), diálogo, final | `gameplay.py`, `menus.py`, `base.py` |
| `elden/audio/` | 650 | síntese NumPy; música gerada em **processo** separado | `synth.py`, `manager.py` |
| `elden/input_map.py` | — | teclado/gamepad → `InputState`; WASD é convertido da tela para X/Z via `projection.screen_move_to_world` | — |

## Fluxos principais

- **Quadro de jogo:** `App` → cena do topo (`GameplayScene.update`) → `input_map` → `World.step(dt)` (atores, IA, combate, props, puzzles) → `world.fx` → `render/fx.py` + `scene_view` sincronizam vistas → `pipeline` (cena HDR → bloom → composite + UI).
- **Carregar fase:** `build_world` lê `data/levels/<id>.json` (gerado por `tools/mapas/<id>.py`) → `scene_view` cria malha (`level_mesh`), atlas, vistas, luzes e `visual_assets` do manifesto (fallback procedural se ausente).
- **Descanso na Graça:** `session.events` (`rest`) → menus de Graça → `GameplayScene.end_rest` recarrega a fase (inimigos renascem).
- **Golpes:** `data/moves/*.json` → `moves.py` monta o grafo por família de arma → nós da árvore (`replace_move`, `add_transition`) alteram o grafo → `MoveAction` executa.
- **Gatilhos:** runas, nós e passivas registram `{on, do}` no `TriggerEngine`; eventos de combate disparam efeitos com proteção contra recursão.

## Dados e ferramentas

- `data/*.json`: todo o conteúdo (classes, armas, golpes, runas, árvore, inimigos, chefes, NPCs, diálogos, missões, lore, ambientes, temas, atos). Fases em `data/levels/` — **não editar à mão**, regenerar com `tools/mapas/`.
- `assets/manifest.json` + `assets/models|textures`: arte externa opcional (ver `assets/README.md`).
- `tools/dev/`: `tour.py`, `ui_tour.py`, `perfil.py`, `validar_assets.py`, `scenarios/`.
- `tools/assets/build_gothic_modules.py`: regenera os BAM góticos.
- `tests/`: `test_basico.py` (dados, simulação, árvore, save) e `test_render.py` (projeção, WASD, manifesto, shaders, perfis).
- Variáveis: `ELDEN_OFFSCREEN=1` (captura sem janela), `ELDEN_DISABLE_EXTERNAL_ASSETS=1` (força fallback).
