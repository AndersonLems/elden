# ESTADO ATUAL — progresso real

> Atualize este arquivo ao fim de todo trabalho relevante (data, branch, commit, testes executados).
> **Implementado** = código/dados existem. **Validado** = verificado por teste ou execução registrada abaixo.

## Referência
- **Data:** 2026-10-21
- **Branch ativa autorizada:** `docs/contexto-persistente` (criada a partir de `main`). `main` só recebe merge via PR.
- **Base:** `main` @ `d3fd48d` (merge do PR #1 `feature/visual-overhaul-25d`).
- **Branches remotas:** `main`, `feature/visual-overhaul-25d` (já mergeada).

## Última validação registrada (2026-10-21, `main` @ d3fd48d)
| Verificação | Resultado |
|---|---|
| `python3 -m unittest discover -s tests` | ✅ 15 testes OK (5 `test_basico`, 10 `test_render`) |
| `DB.validate()` | ✅ `[]` |
| `python3 tools/dev/validar_assets.py` | ✅ manifesto válido |
| Jogo em janela real após o PR #1 | ⚠️ não executado nesta sessão |

Tamanho: ~19 mil linhas de Python, ~420 de GLSL, ~40 arquivos JSON. Antes do PR #1, em janela real: ~60 FPS
na Intel Iris Xe (1280x720, alta).

Medições de desempenho (feitas pelo PR #1, offscreen, Intel Iris Xe, 1280x720, perfil alto): arena 2,1–2,7 ms de update e
3,8–4,5 ms por quadro. Logs em `artifacts/visual-overhaul/*/metrics/`. Não equivale a teste em janela real.

## Conteúdo
| Área | Implementado | Validado |
|---|---|---|
| Santuário (hub) + Ato I (`ato1_floresta`, `ato1_castelo`, `ato1_arena`) | ✅ | ✅ carregamento e tours com captura; ⚠️ sem *playthrough* completo registrado após a nova projeção |
| Ato II `ato2_cidade`, `ato2_fabrica` | ✅ | ⚠️ só carregamento/capturas, sem *playthrough* |
| Ato II `ato2_arena` (Serafim-09) | ❌ mapa | — |
| Atos III–V (9 mapas) | ❌ mapas (dados de inimigos, chefes, NPCs, documentos e missões existem) | — |
| 9 classes, árvore (126 nós), 37 runas, 29 armas, 23 artes | ✅ | ✅ parcial: `test_basico` (rotas das classes, árvore, save); menus vistos em `ui_tour` |
| 6 chefes com 3 fases | ✅ código | ⚠️ nenhuma vitória registrada; sem bot de chefe |
| Puzzles (combinação, sequência, feixe, rede, engrenagens, all_on, kill) | ✅ | ⚠️ sem teste automatizado de solução nem registro de resolução |
| 3 finais | ✅ lógica (`Session.ending_options`) | ❌ não alcançáveis (faltam Atos III–V) |
| Projeção semi-isométrica, 4 faces, WASD da tela | ✅ | ✅ `test_render` + capturas do PR #1 |
| Pipeline de assets externos + pacote gótico (arena/castelo) | ✅ | ✅ `validar_assets.py`, `test_render` |
| Captura offscreen (`ELDEN_OFFSCREEN=1`) | ✅ | ✅ segundo PR #1 |
| Scripts Linux/Windows | ✅ | ✅ Linux; ⚠️ Windows não testado em máquina real |

## Problemas conhecidos
- Folhagem da floresta com ruído de alta frequência (ver `docs/VISUAL.md`).
- Saídas para fases inexistentes mostram "Esta região ainda está em construção" (comportamento esperado).
- Balanceamento (vida/dano por ato, custos, preços) não ajustado.

## Próximos trabalhos (ordem)
1. Jogar Santuário + Ato I em janela real com a nova projeção e registrar o resultado aqui.
2. `ato2_arena` (Serafim-09) — plano em `docs/CONTEXTO.md`.
3. Mapas dos Atos III–V (plano em `docs/CONTEXTO.md`).
4. Bot de teste de chefe e teste automatizado de solução de puzzles por fase.
5. Propagar o padrão visual da arena para floresta, vila e fábrica; balanceamento.

## Histórico curto
- 2026-10-21 — branch `docs/contexto-persistente`: infraestrutura de contexto (ARQUITETURA, VISUAL, ESTADO_ATUAL; AGENTS como índice).
- PR #1 (`d3fd48d`) — reforma visual 2.5D V1–V3 (projeção, 4 faces, assets externos, offscreen, refinamento de pixel art).
- `3e83d45` — commit inicial: motor, combate, RPG, Santuário, Ato I e parte do Ato II.
