# CONTEXTO — pedido original, plano e formatos de dados

## Pedido do usuário (resumo)
O jogo pedido é um Action RPG *hack and slash* 2.5D dark fantasy em pixel art, feito em Python, com Ursina preferencial. Precisa estar completo e jogável, sem entregas em etapas. O nome é **ELDEN**, e os checkpoints são **Graças** no estilo Elden Ring: sentar para evoluir, curar e trocar a build.

Requisitos principais:
- 9 classes com identidade própria, cada uma com 4 rotas de combo, 3 habilidades ativas, uma suprema e 2 passivas;
- sistema de Graça (CORPO, ESPÍRITO, RUÍNA e técnicas de classe que mudam os combos);
- corrupção e mais de 27 runas em 9 categorias;
- famílias de armas e artes de combate;
- 5 atos, cada um com 5 chefes de 3 fases, áreas exploráveis, segredos, elites, checkpoints e pelo menos 2 puzzles;
- IA com máquina de estados;
- hub (Santuário da Última Chama) com serviços;
- narrativa com 3 finais;
- scripts para Linux e Windows, README e testes.

## Plano dos atos (o que falta construir em mapas)
Todos os dados de inimigos, chefes, NPCs, missões e documentos citados abaixo **já existem** em `data/`.

### Ato II — Forja das Almas (✅ `ato2_arena` feito em 2026-10-21; registro mantido como referência)
- **Arena "Núcleo da Forja":**
  - SERAFIM-09 (`boss: serafim_09`), com os braços criados automaticamente;
  - 4 a 6 props `hazard` com `id` `forja_jato_N`, `hazard: "flame"`, `active: false`, `sprite: flame_vent`, `length` (4–8) e `angle` (direção do jato);
  - spawn `entrada`;
  - porta de névoa (`close_on: boss_start`, `open_on: boss_defeated`);
  - portal de vitória para `santuario`/`retorno_ato2` com `if: {flag: boss:serafim_09}` e uma Graça pós-chefe.


### Ato III — Catedral da Carne (tema `ato3_catedral`, ambientes `catedral`, `laboratorio`, `catedral_arena`)
- **`ato3_catedral`:**
  - nave com bancos (`h`), vitrais (`G`) e biblioteca médica (`B`);
  - NPC `agathe`, com as páginas `pagina_absolvicao_1` na biblioteca e `_2` na capela dos mártires (como `document`);
  - **puzzle de sequência** com os sinos (`seq_button` com `symbol` CORDEIRO, CÁLICE, ESPADA, COROA), dica no documento `vitral_ordem`, que abre a escada (porta) até a saída para o laboratório;
  - Graças `graca_atrio` e `graca_martires`;
  - segredo com `fragmento_ciclo_3`;
  - elite: monge (Abade).
- **`ato3_laboratorio`:**
  - poças de ácido (`x`) e paredes de carne (`F`);
  - **puzzle alquímico** com `seq_button` SAL, MERCÚRIO, ENXOFRE, SANGUE (dica em `receita_alquimica`);
  - **puzzle de diagrama:** 3 `dial` com `symbols` `["norte","leste","sul","oeste"]`; a solução `["sul","norte","leste"]` (dica em `diagrama_anatomico`) abre a sala de operações;
  - `pagina_absolvicao_3`;
  - elite: aberração;
  - saída para `ato3_arena`.
- **`ato3_arena`:** `santo_imperfeito`.

### Ato IV — Observatório do Abismo (tema `ato4`)
- **`ato4_biblioteca`:**
  - NPC `corvin` dentro de uma cela (porta `gaiola_corvin`) aberta por uma alavanca escondida atrás de estantes; o puzzle `all_on` dá a recompensa `{"flag":"corvin_livre"}`;
  - **portais conectados** (`portal` com `link`) entre plataformas cercadas de vazio (`~`);
  - **sequência de runas:** 4 `dial` com 6 símbolos (índices 0 círculo, 1 triângulo, 2 quadrado, 3 cruz, 4 losango, 5 X) e solução `[0,1,3,4]` (`selo_academia`);
  - Graças `graca_saguao` e `graca_biblioteca`.
- **`ato4_observatorio`:**
  - **espelhos:** `emitter` com `sprite: sun_lens` e 3 `crystal` `receiver: true` `latch: true` (Coroa, Espada, Olho), dica em `mapa_estelar`, puzzle `beam`;
  - **relógio astral:** 3 `dial`, solução `[2,5,0]` (`relogio_astral`);
  - plataformas em alturas diferentes e plataformas móveis;
  - Graças `graca_escadaria` e `graca_planetario`.
- **`ato4_arena`:** `malachar`, com `arena_center` obrigatório (círculo seguro de raio 6,5 na fase 3).

### Ato V — Trono da Graça (tema `ato5`)
- **`ato5_ruinas`:**
  - NPC `ysolde`;
  - **luzes:** 4 `crystal` com `hold: 6` (acender todos em até 6 s, puzzle `all_on`);
  - **estátuas:** 3 `dial` com `symbols` `["sul","leste","norte","oeste"]` e `sprite: king_statue`, solução `["leste","norte","oeste"]` (`estatuas_anjos`);
  - Graça `graca_portao_celeste`.
- **`ato5_templo`:**
  - placas com `latch` mais uma alavanca;
  - baú com `selo_trono` (depois de um elite);
  - porta com `key: selo_trono`;
  - Graça `graca_escadaria_trono`.
- **`ato5_arena`:**
  - `aurelion`;
  - após a vitória, um `altar` com `altar: "trono"` e `if: {flag: aurelion_derrotado}` abre a escolha de final;
  - `document` `fragmento_ciclo_5`.

O portal de cada ato no Santuário já aponta para `<ato>_...` (ver `data/acts.json` e `tools/mapas/santuario.py`).

## Formatos principais
- **Golpe** (`data/moves/*.json`): `anim`, `dur`, `type`, `hits[{t:[a,b], shape: arc|circle|line|ring, range, angle, dmg, posture, kb, launch, stun, heavy, elem, status, rehit, unblockable}]`, `move[{t, speed, to_target}]`, `jump`, `hang`, `charge{min,max,release}`, `spawn[{proj|zone|summon}]`, `effects[{t,type}]`, `iframes`, `armor`, `cancel`, `dodge_cancel`, `next{L,H}`, `land`.
- **Entradas iniciais da família:** L, H, DL, DH, RL, RH, AL, AH, BH, FH, C.
- **Nó da árvore:** `effects` com `attr`, `mods`, `replace_move`, `add_transition`, `add_start`, `move_effect{tag,elem,status,launch,lifesteal}`, `trigger`, `unlock`, `flag`, `corruption`, `rune_slot`. Também `requires`, `exclusive`, `class`, `pos` e `cost`.
- **Gatilho** (runas, nós, passivas): `{"on": hit|crit|kill|parry|perfect_dodge|dodge|heavy_hit|finisher_hit|launch_hit|took_hit|low_hp|skill|art|block|execution|status_proc|transform, "do": heal|fp|fervor|buff|zone|proj|chain|clone|cooldown|status|heat|teleport_window|bonus_damage|mark|refund_dodge|barrier|steal|fury, "cd", "chance", "cond"}`.
- **Puzzle:** `type` combination|all_on|sequence|beam|network|gears|kill. As recompensas usam `open`, `activate`, `lock`, `reward`, `grace` e `message`.
- **Diálogo:** `nodes{id:{text, next | choices[{text,next,if,do}], do, if, else}}`. Os efeitos `do` são `set_flag`, `give`, `take_item`, `quest`, `corruption`, `pray`, `service` (mercador|ferreiro|treinador|biblioteca) e `ending`.
