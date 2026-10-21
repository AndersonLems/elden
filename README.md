# ELDEN — Graça Profana: O Crepúsculo dos Deuses

Action RPG *hack and slash* 2.5D dark fantasy em **pixel art**, feito em **Python** (Ursina + Panda3D).
Toda a arte (sprites, texturas, objetos), a música e os efeitos sonoros são **gerados por código**.
Roda localmente no Linux e no Windows, sem internet.

> **Estado atual: em desenvolvimento.** O Santuário (hub) e o **Ato I** estão jogáveis de ponta a ponta;
> o **Ato II** está parcialmente construído; os Atos III–V ainda não têm mapas. Veja [O que falta](#o-que-falta).

---

## Como instalar e jogar

Requisitos: **Python 3.10+** e placa de vídeo com **OpenGL 3.3**.

### Linux
```bash
./instalar.sh        # instala dependências (pip --user) e pré-gera sprites/sons/músicas
./jogar.sh           # inicia o jogo
./jogar.sh --tela-cheia --qualidade alta --resolucao 1600x900
```

### Windows
Instale o Python em python.org marcando **"Add Python to PATH"**, depois dê dois cliques em:
```
instalar.bat
jogar.bat
```

A primeira execução gera caches em `~/.cache/elden-jogo` (Windows: `%LOCALAPPDATA%\ELDEN\cache`).
Saves e configurações ficam em `~/.local/share/elden-jogo` (Windows: `%APPDATA%\ELDEN`).

### Controles (teclado e mouse)
| Ação | Tecla |
|---|---|
| Mover | WASD / setas |
| Ataque leve / pesado (segure = carregado) | J ou botão esquerdo / K ou botão direito |
| Esquiva (segure = correr) | Shift |
| Pular | Espaço |
| Bloquear / aparar (toque no tempo certo) | Q |
| Arte de combate | F |
| Habilidades / Suprema | 1 2 3 / R |
| Interagir, descansar na Graça | E |
| Travar alvo / trocar alvo | Tab / C |
| Frasco de vida / de Foco | Z / X |
| Pausa | Esc |
| Hitboxes / FPS / tela cheia | F3 / F2 / F11 |

O controle (gamepad) também funciona: A pular, B esquiva, X/Y leve/pesado, LB bloquear, RB arte,
LT + X/Y/A habilidades, RT suprema e o direcional para frascos.

**Combos:** L L L • L L H (lançador) • H segurado • esquiva + L • corrida + L • pule após o lançador e use L L L no ar •
rompa a postura (barra amarela) e aperte Leve para **executar**.

---

## O que já existe

- **Motor gráfico próprio** sobre o Panda3D:
  - projeção ortográfica semi-isométrica (45°/38°), renderizada em baixa resolução e ampliada por escala inteira;
  - quatro faces expostas da grade, profundidade real e billboards verticais com oclusão;
  - até 16 luzes com sombras de tochas por raymarching, faixas de luz pontilhadas, bloom, vinheta, granulação e tonemapping;
  - líquidos animados, partículas em pixel, rastros de lâmina e avisos de ataque no chão.
- **Arte procedural:**
  - personagens com esqueleto 3D rasterizado em 8 direções e cerca de 90 animações;
  - texturas em atlas por fase;
  - mais de 100 sprites de objetos.
- **Pipeline híbrido de arte:** manifesto e carregador para modelos, texturas, sprites e animações
  externos, mantendo os geradores procedurais como fallback; a arena de Varkhan usa oito assets
  góticos reais (piso, arco, portão, colunas, estátuas, escadaria e contrafortes).
- **Combate:**
  - grafo de golpes orientado a dados: 15 famílias de armas e cerca de 400 golpes;
  - combos com janelas de cancelamento e buffer de entrada;
  - carregado, aéreo, lançador, contra-ataque e execução;
  - aparar, bloqueio, esquiva com invencibilidade e esquiva perfeita;
  - postura, hitstop, hitstun, empurrão e lançamento;
  - status (sangramento, queimadura, congelamento, choque, maldição) e combinações elementais.
- **Personagens e builds:**
  - **9 classes** (Guerreiro, Ninja, Soldado, Bandido, Ladrão, Mago, Clérigo, Vampiro, Lobisomem), cada uma com 3 habilidades, uma suprema e 2 passivas;
  - **Árvore de Graça** com 126 nós: CORPO, ESPÍRITO, RUÍNA e técnicas de classe com especializações exclusivas; os nós alteram o grafo de combos;
  - **Corrupção**, que afeta modificadores, NPCs e finais;
  - **37 runas** em 9 categorias, com gatilhos e proteções contra recursão;
  - 29 armas e 23 artes de combate.
- **Inimigos e chefes:**
  - 33 inimigos com IA de estados: patrulha, perseguição, flanqueamento, fichas de ataque, bloqueio, aparar, esquiva e A*;
  - versões elite dos inimigos;
  - **6 chefes** com 3 fases (Varkhan, Condessa Rubra, Serafim-09, Santo Imperfeito, Malachar, Aurelion).
- **Mundo e história:**
  - **Graças** (checkpoints): descansar, evoluir, árvore, runas, armas, viajar; os inimigos renascem ao descansar;
  - Graça perdida ao morrer, recuperável;
  - Santuário com NPCs: loja, ferreiro, treinador de artes, biblioteca com redistribuição de pontos;
  - diálogos ramificados, missões e 37 documentos de história;
  - 3 finais (Purificação, Domínio, Ruptura).
- **Puzzles** orientados a dados: combinação, sequência, feixes de luz com espelhos, rede de vapor/energia, engrenagens, alavancas e salas de emboscada.
- **Telas:** título, 3 espaços de save, criação de personagem com prévia animada, HUD, menus e configurações de qualidade, áudio e acessibilidade.
- **Áudio:** cerca de 90 efeitos e 14 músicas sintetizados com NumPy.

## O que falta

| Item | Situação |
|---|---|
| Santuário + Ato I (floresta, vila, cemitério, cripta, castelo, Condessa, Varkhan) | ✅ jogável |
| Ato II — `ato2_cidade`, `ato2_fabrica` | ✅ mapas prontos, sem teste de jogo completo |
| Ato II — `ato2_arena` (Serafim-09) | ❌ falta o mapa (use props `hazard` com `id` `forja_jato_N`, `length` e `angle`) |
| Ato III — `ato3_catedral`, `ato3_laboratorio`, `ato3_arena` | ❌ faltam mapas (dados de inimigos, chefe, NPC e documentos prontos) |
| Ato IV — `ato4_biblioteca`, `ato4_observatorio`, `ato4_arena` | ❌ faltam mapas (precisa de `arena_center` no JSON) |
| Ato V — `ato5_ruinas`, `ato5_templo`, `ato5_arena` (Aurelion + altar `trono` + fragmento 5) | ❌ faltam mapas |
| Testes de chefes com bot, verificação de alcance e solução de puzzles por mapa | ❌ |
| Balanceamento (vida e dano por ato, custo de níveis, preços) | ⚠️ não ajustado |
| Polimento visual (telhados e decoração por tema, mais variação de inimigos) | ⚠️ |
| Mapa/minimapa, rebind de teclas | ➖ opcional |

Portais e saídas para fases inexistentes mostram "Esta região ainda está em construção".
Os planos detalhados de cada ato estão em [`docs/CONTEXTO.md`](docs/CONTEXTO.md).

## Estrutura

```
main.py, instalar.sh/.bat, jogar.sh/.bat, requirements.txt
data/            conteúdo em JSON (classes, armas, famílias, golpes, runas, árvore, inimigos, chefes,
                 fases, diálogos, missões, documentos, ambientes, temas)
elden/core/      dados, caminhos, eventos, configurações, saves
elden/sim/       simulação pura (sem janela): entidades, combate, IA, mundo, progressão, sessão
elden/render/    pipeline, shaders GLSL, malha do cenário, vistas, partículas
elden/art/       geradores de texturas, esqueletos, animações e sprites
elden/ui/        interface em pygame (HUD, widgets, ícones)
elden/scenes/    telas (título, criação, jogo, menus, diálogos, finais)
elden/audio/     síntese e reprodução de áudio
tools/mapas/     scripts que geram data/levels/*.json
tools/gerar_assets.py   pré-geração de caches
tests/           testes sem janela (python3 -m unittest discover -s tests)
```

Desenvolvimento: comece por [`AGENTS.md`](AGENTS.md) (índice) e [`docs/ESTADO_ATUAL.md`](docs/ESTADO_ATUAL.md).
