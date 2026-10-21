# ESTADO ATUAL — progresso real

> Atualize este arquivo ao fim de todo trabalho relevante (data, branch, commit, testes executados).
> **Implementado** = código/dados existem. **Validado** = verificado por teste ou execução registrada abaixo.

## Referência
- **Data:** 2026-10-21
- **Branch ativa autorizada:** `feature/ato2-arena` (criada a partir de `docs/contexto-persistente` @ `7cbeadb`, que sai de `main`).
  `main` só recebe merge via PR. Nenhuma das duas branches foi enviada ao GitHub ainda.
- **Base:** `main` @ `d3fd48d` (merge do PR #1 `feature/visual-overhaul-25d`).
- **Branches remotas:** `main`, `feature/visual-overhaul-25d` (já mergeada).

## Última validação registrada (2026-10-21, `feature/ato2-arena`)
| Verificação | Resultado |
|---|---|
| `python3 -m unittest discover -s tests` | ✅ 18 testes OK em ~13 s (5 `test_basico`, 10 `test_render`, 3 `test_chefes`) |
| Bot de chefe (`tests/bot.py`), 8 seeds por chefe | ✅ 24/24 vitórias: Varkhan 117–147 s, Condessa 47–66 s, Serafim 125–195 s (tempo simulado, guerreiro nível 1, só ataque leve) |
| Captura offscreen de `ato2_arena` (`tour.py`) | ✅ renderiza, ~270 FPS offscreen |
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
| Ato II `ato2_arena` (Serafim-09) | ✅ | ✅ `test_chefes` (3 fases, névoa fecha/reabre, jatos sobre o chão, flags `ato2_concluido`) + captura; ⚠️ não jogado por humano |
| Atos III–V (9 mapas) | ❌ mapas (dados de inimigos, chefes, NPCs, documentos e missões existem) | — |
| 9 classes, árvore (126 nós), 37 runas, 29 armas, 23 artes | ✅ | ✅ parcial: `test_basico` (rotas das classes, árvore, save); menus vistos em `ui_tour` |
| 6 chefes (Condessa com 2 fases, demais com 3) | ✅ código | ✅ Varkhan, Condessa, Serafim vencidos pelo bot (`test_chefes`); ❌ Santo, Malachar, Aurelion sem fase para testar |
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
- Bot de chefe é "imortal" e não esquiva: mede vencibilidade e regressões, não justiça/dificuldade. Dano recebido por luta
  (2–4 mil, vida máxima 200) indica que um humano precisa esquivar; não calibrado.
- As barras dos dois braços do Serafim se projetam quase no mesmo ponto (aparecem como uma barra).

## Próximos trabalhos (ordem)
1. Jogar Santuário + Ato I + Ato II em janela real com a nova projeção e registrar o resultado aqui.
2. Mapas dos Atos III–V (plano em `docs/CONTEXTO.md`); adicionar cada chefe a `tests/test_chefes.py`.
3. Teste automatizado de solução de puzzles por fase.
4. Propagar o padrão visual da arena do Ato I (assets góticos) para Ato II e demais fases; balanceamento.

## Histórico curto
- 2026-10-21 — branch `feature/ato2-arena`: mapa `ato2_arena`; bot e `tests/test_chefes.py`; correções: braços do Serafim
  empurravam o chefe através das paredes (`physics.separate` ignora `noclip`), crash do Serafim com props sem `id`,
  névoa da arena do Ato I contornável (movida para o corredor), cache do A* por `id()`, rótulos sobrepostos das partes de chefe.
- 2026-10-21 — branch `docs/contexto-persistente`: infraestrutura de contexto (ARQUITETURA, VISUAL, ESTADO_ATUAL; AGENTS como índice).
- PR #1 (`d3fd48d`) — reforma visual 2.5D V1–V3 (projeção, 4 faces, assets externos, offscreen, refinamento de pixel art).
- `3e83d45` — commit inicial: motor, combate, RPG, Santuário, Ato I e parte do Ato II.
