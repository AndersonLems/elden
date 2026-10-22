# ESTADO ATUAL — progresso real

> Atualize este arquivo ao fim de todo trabalho relevante (data, branch, commit, testes executados).
> **Implementado** = código/dados existem. **Validado** = verificado por teste ou execução registrada abaixo.

## Referência
- **Data:** 2026-10-21
- **Branch ativa autorizada:** `main`. Em 2026-10-21 o usuário autorizou commits e push **direto na `main`**
  enquanto o jogo é terminado (Atos III–V). `feature/ato2-arena` e `docs/contexto-persistente` já foram integradas.
- **Base:** `main` @ `d3fd48d` (merge do PR #1 `feature/visual-overhaul-25d`).
- **Branches remotas:** `main`, `feature/visual-overhaul-25d` (já mergeada).

## Última validação registrada (2026-10-21, `feature/ato2-arena`)
| Verificação | Resultado |
|---|---|
| `python3 -m unittest discover -s tests` | ✅ 35 testes OK em ~23 s (`test_basico`, `test_render`, `test_chefes`, `test_fases`, `test_finais`, `test_campanha`, `test_dialogos`) |
| Diálogos (`test_dialogos`) | ✅ 36 diálogos, 518 estados percorridos, 227 finais de caminho sem nó inexistente; missões de Agathe e Corvin avançam |
| Solucionador lógico da campanha (`test_campanha`) | ✅ os 5 atos chegam ao chefe partindo do Santuário (baús, saques, puzzles, chaves, alavancas, plataformas) |
| Inimigos comuns × personagem preparado (medição ad hoc) | ✅ 5–20% por golpe; elites 28–35%; pico ~50% (julgamento do Cavaleiro Divino, com aviso e imbloqueável) |
| Bot de chefe (`tests/bot.py`), preparo do ato (arma +ato, ~5 níveis/ato em CORPO) | ✅ todos vencidos (Aurelion 268–525 s simulados). Golpe mediano/p90 em % da vida: Varkhan 15/33, Serafim 25/32, Santo 15/29, Malachar 12/23, Aurelion 17/42 |
| Captura offscreen de todas as fases novas (`tour.py`) | ✅ Atos II–V renderizam (125–330 FPS offscreen) |
| Lutas no app real (`scenarios/luta_chefe.py`): Santo, Malachar, Aurelion | ✅ 3 fases, efeitos, morte, portal/Graça revelados; achou e corrigiu travamento do HUD (alfa negativo) |
| Telas dos 3 finais (`scenarios/finais.py`) | ✅ texto e créditos renderizam |
| `DB.validate()` | ✅ `[]` |
| Instaladores (2026-10-22) | ✅ `instalar.sh` em contêineres limpos Ubuntu 24.04, Fedora 41 e Arch (instala Python, `.venv`, deps importam); `instalar.bat` no Wine: Python 3.12.10 silencioso, `.venv`, deps, `jogar.bat` usa o `.venv`. Windows real, winget e download (curl/PowerShell) não testados |
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
| Ato III `ato3_catedral`, `ato3_laboratorio`, `ato3_arena` | ✅ | ✅ `test_fases` (alcance, puzzles sinos/soro/diagrama/Abade), Santo vencido pelo bot, capturas; ⚠️ não jogado por humano |
| Ato IV `ato4_biblioteca`, `ato4_observatorio`, `ato4_arena` | ✅ | ✅ `test_fases` (portais, plataforma, Corvin, selo, espelhos, relógio), Malachar vencido pelo bot (8/8 seeds), capturas; ⚠️ não jogado por humano |
| Ato V `ato5_ruinas`, `ato5_templo`, `ato5_arena` | ✅ | ✅ `test_fases` (luzes, anjos, placas+alavanca, guardião, selo), Aurelion vencido pelo bot preparado, altar do Trono e escolha de final (`test_finais`), capturas; ⚠️ não jogado por humano |
| 9 classes, árvore (126 nós), 37 runas, 29 armas, 23 artes | ✅ | ✅ parcial: `test_basico` (rotas das classes, árvore, save); menus vistos em `ui_tour` |
| 6 chefes (Condessa com 2 fases, demais com 3) | ✅ código | ✅ os 6 vencidos pelo bot com preparo do ato (`test_chefes`, 3 seeds cada) |
| Puzzles (combinação, sequência, feixe, rede, engrenagens, all_on, kill) | ✅ | ✅ combinação, sequência, kill, all_on e feixe resolvidos pela dica em `test_fases`; ⚠️ rede e engrenagens sem teste automático |
| 3 finais | ✅ | ✅ `test_finais` (fragmentos, altar, condições) + telas capturadas no app real |
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
1. Jogar a campanha inteira em janela real (o usuário testa em 2026-10-22) e registrar o resultado aqui.
2. Balanceamento fino com jogo humano (números do bot estão na tabela acima; inimigos comuns dos Atos IV–V não medidos).
3. Testes automáticos de puzzles de rede e engrenagens.
4. Propagar o padrão visual da arena do Ato I (assets góticos) para as outras fases.

## Histórico curto
- 2026-10-22 — `main`: instaladores instalam o Python se faltar (Linux: apt/dnf/pacman/zypper/apk; Windows: winget
  ou python.org, por usuário) e usam `.venv`; `jogar.*` aceitam a instalação antiga `pip --user`.
- 2026-10-21 — `main`: **Ato II não podia ser terminado** — a Manivela de Lise (porta da distribuição de energia →
  elevador → arena) não era entregue por ninguém. Agora o Capataz a carrega (`loot` em inimigo de mapa, novo).
  `test_campanha` (solucionador lógico) e `test_chaves_obteniveis` impedem regressões desse tipo.
- 2026-10-21 — `main`: balanceamento — vida +6/nível; sem crítico aleatório contra o jogador; costas só corpo a corpo;
  rajada inimiga acerta 1×; Aurelion −20% ataque e impacto/pilares/lanças menores; Santo e Malachar com picos menores.
- 2026-10-21 — `main`: Ato V completo — **todas as 15 fases existem**. Portal/Graça/altar pós-chefe agora surgem na
  hora (antes só após recarregar). Teste novo: porta de puzzle/chave precisa bloquear algo — achou contornos em
  `ato2_fabrica` (pistão) e `ato3_catedral` (escada), corrigidos. Bot de chefe usa preparo do ato.
- 2026-10-21 — `main`: Ato IV completo. Bugs de IA corrigidos: teleporte (`blink_away`) caía em topo de parede e
  atravessava portas fechadas; invocações (`summon`) nasciam sobre paredes. Bot verifica chefe × névoa por região do grid.
- 2026-10-21 — `main`: Ato III completo; `tests/test_fases.py`; topo da fábrica (Ato II) estava inalcançável — corrigido;
  documento da floresta dentro de casa fechada — corrigido. Bot de nível 1 leva ~5 min simulados contra o Santo (balanceamento).
- 2026-10-21 — branch `feature/ato2-arena`: mapa `ato2_arena`; bot e `tests/test_chefes.py`; correções: braços do Serafim
  empurravam o chefe através das paredes (`physics.separate` ignora `noclip`), crash do Serafim com props sem `id`,
  névoa da arena do Ato I contornável (movida para o corredor), cache do A* por `id()`, rótulos sobrepostos das partes de chefe.
- 2026-10-21 — branch `docs/contexto-persistente`: infraestrutura de contexto (ARQUITETURA, VISUAL, ESTADO_ATUAL; AGENTS como índice).
- PR #1 (`d3fd48d`) — reforma visual 2.5D V1–V3 (projeção, 4 faces, assets externos, offscreen, refinamento de pixel art).
- `3e83d45` — commit inicial: motor, combate, RPG, Santuário, Ato I e parte do Ato II.
