# AGENTS.md — índice para quem (humano ou IA) continuar o ELDEN

## Protocolo de sessão (economia de contexto)
1. **Comece por `docs/ESTADO_ATUAL.md`**: branch ativa, último commit, o que foi validado e próximos trabalhos.
2. **Não releia o repositório inteiro.** Abra só o documento da tabela abaixo que corresponde à tarefa e, a partir dele, os arquivos citados.
3. **Reutilize decisões documentadas** (`MEMORY.md`, `docs/VISUAL.md`). Não reabra uma decisão sem novo motivo concreto.
4. **Não reinvestigue bugs listados em `MEMORY.md` → Armadilhas** a menos que haja novo indício (erro, captura ou teste diferente).
5. **Ao terminar trabalho relevante, atualize `docs/ESTADO_ATUAL.md`**: data, branch, commit, testes realmente executados e resultado.
6. **Registre resultados reais.** Separe *implementado* de *validado*; nunca marque validado sem teste ou execução registrada.
7. **Documentos curtos e sem redundância:** cada fato mora em um só lugar; os demais apontam para ele.
8. **Git:** trabalhe apenas na branch ativa autorizada em `ESTADO_ATUAL.md` (hoje a `main`, com push direto autorizado
   pelo usuário). Sem essa autorização registrada, a `main` só recebe mudanças via PR.
9. **Não apague documentação existente nem reescreva o projeto.** Mudanças incrementais.

## Onde procurar
| Tarefa | Leia |
|---|---|
| Situação atual, prioridades, o que foi testado | `docs/ESTADO_ATUAL.md` |
| Localizar código, dependências, fluxo de um sistema | `docs/ARQUITETURA.md` |
| Câmera, shaders, iluminação, sprites, arte | `docs/VISUAL.md` (histórico e medições: `docs/VISUAL_OVERHAUL.md`) |
| Arte externa (manifesto, formatos) | `assets/README.md` |
| Criar mapa/ato, puzzles, formatos de JSON (golpe, nó, gatilho, diálogo) | `docs/CONTEXTO.md` + "Como criar um mapa" abaixo |
| Decisões técnicas e bugs já resolvidos | `MEMORY.md` |
| Instalação, controles, visão do jogador | `README.md` |

## Regras do projeto
- **Idioma:** textos de jogo, comentários, docstrings e documentação em **português do Brasil**.
- **Python 3.10+**, engine **Ursina 8 + Panda3D 1.10**. Não trocar de engine.
- **Conteúdo em JSON** (`data/`). Prefira adicionar conteúdo por dados. `data/levels/*.json` é gerado por `tools/mapas/`.
- **`elden/sim/` não importa nada de renderização.** A simulação é testável sem janela; a ponte é `world.fx` e `elden/render_bridge.py`.
- Estilo: classes pequenas e herança (`Entity → Actor → Player/Enemy → Boss`, `Prop → Door/Lever/...`, `Scene → Overlay → MenuOverlay`).
- **Não declare algo pronto sem testar.** Testes + `DB.validate()`; para mudanças visuais, capturas.
- Arte externa vai em `assets/manifest.json`; mantenha a arte procedural como fallback.

## Comandos
```bash
python3 main.py                                   # jogar (janela 1280x720)
python3 -m unittest discover -s tests -v          # testes sem janela (inclui bot de chefes, ~13 s)
python3 -c "import sys; sys.path.insert(0,'.'); from elden.core.data import DB; print(DB.validate())"  # validar JSON
python3 tools/dev/validar_assets.py               # manifesto e arquivos de arte externa
python3 tools/mapas/<fase>.py                     # regenerar data/levels/<fase>.json
python3 tools/gerar_assets.py                     # pré-gerar caches (sprites, sons, músicas)

# capturas automáticas (posiciona o jogador e salva PNGs):
python3 tools/dev/tour.py /tmp/out ato1_floresta '[[9,6,"inicio"],[46,30,"vila"]]'
SPAWN=entrada python3 tools/dev/tour.py /tmp/out ato2_fabrica '[[30,40,"a"]]'
python3 tools/dev/ui_tour.py /tmp/out             # telas de interface
python3 tools/dev/perfil.py                       # tempo por quadro e cProfile
SPAWN=entrada ELDEN_OFFSCREEN=1 python3 tools/dev/tour.py /tmp/out ato5_arena '[]' tools/dev/scenarios/luta_chefe.py
ELDEN_OFFSCREEN=1 python3 tools/dev/tour.py /tmp/out santuario '[]' tools/dev/scenarios/finais.py
```
- `ELDEN_OFFSCREEN=1` captura/perfila sem abrir janela; `ELDEN_DISABLE_EXTERNAL_ASSETS=1` força o fallback procedural.
- As ferramentas de captura desligam o vsync (`App({"novsync": True})`). **Com vsync, janelas escondidas ficam em ~1 FPS.**
- Nunca rode duas instâncias ao mesmo tempo e não use `pkill -f <padrão>` num comando cujo próprio texto contém o padrão.

## Como criar um mapa novo
1. Copie um gerador de `tools/mapas/` (por exemplo `ato2_fabrica.py`). Use `Grade` (`rect`, `frame`, `put`, `ent`) e `carve`/`scatter`.
2. A primeira linha do texto é o **norte**. Use `g.ent(x, r, type=..., ...)` com coordenadas da grade (convertidas automaticamente).
3. Use as legendas de `data/themes.json` (tema do ato). Rampas sobem para o norte (`a` 0→1, `b` 1→2, `c` 2→3).
4. Inclua: `spawn` (ids usados pelas saídas), Graças (`grace`), saídas (`exit` com `to`/`spawn`), `puzzles`, regiões e inimigos
   (`enemy`, com `elite`/`unique`). Arenas: `boss`, porta `close_on: boss_start` / `open_on: boss_defeated` e `arena_center`.
   Arte externa opcional por `visual_assets`.
5. Rode o script, `DB.validate()`, os testes e um `tour.py` da fase; registre o resultado em `docs/ESTADO_ATUAL.md`.
6. Arena nova: adicione o chefe a `CHEFES` em `tests/test_chefes.py` (vitória, fases, névoa, chefe dentro da arena).

As pendências prioritárias ficam em `docs/ESTADO_ATUAL.md` → "Próximos trabalhos".
