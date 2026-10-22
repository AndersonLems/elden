# ELDEN — Graça Profana: O Crepúsculo dos Deuses

Action RPG *hack and slash* 2.5D dark fantasy em **pixel art**, feito em **Python** (Ursina + Panda3D).
Toda a arte (sprites, texturas, objetos), a música e os efeitos sonoros são **gerados por código**.
Roda localmente no Linux e no Windows, sem internet.

> **Estado atual:** todas as fases dos 5 atos existem e passam nos testes automáticos (alcance, puzzles, chefes por bot,
> finais). Ainda falta uma partida completa jogada por uma pessoa e o balanceamento. Veja [O que falta](#o-que-falta).

---

## Como instalar e jogar

Requisitos: placa de vídeo com **OpenGL 3.3** e internet na primeira instalação. O Python (3.10+) é instalado
automaticamente se faltar; as dependências ficam num ambiente próprio em `.venv`, sem mexer no sistema.

### Linux
```bash
./instalar.sh        # instala o Python se faltar (apt, dnf, pacman, zypper ou apk; pode pedir a senha),
                     # cria o .venv, instala as dependências e pré-gera sprites/sons/músicas
./jogar.sh           # inicia o jogo (roda a instalação sozinho se faltar algo)
./jogar.sh --tela-cheia --qualidade alta --resolucao 1600x900
```

### Windows
Dois cliques em `instalar.bat` e depois em `jogar.bat`. Se não houver Python 3.10+, o instalador baixa o
Python 3.12 (winget ou python.org) e instala só para o usuário, sem precisar de administrador.

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
| Santuário + 5 atos (15 fases, 6 chefes, puzzles, NPCs, 3 finais) | ✅ completos e testados automaticamente; ⚠️ ainda sem partida humana completa |
| Testes automáticos | ✅ fases (alcance, portas, chaves, puzzles), campanha lógica por ato, chefes por bot, finais |
| Balanceamento | ⚠️ ajuste inicial pelo bot (golpe mediano 10–25% da vida); falta calibrar jogando |
| Polimento visual (padrão gótico da arena do Ato I nas demais fases, mais variação de inimigos) | ⚠️ |
| Mapa/minimapa, rebind de teclas | ➖ opcional |

O estado detalhado (o que foi validado e como) está em [`docs/ESTADO_ATUAL.md`](docs/ESTADO_ATUAL.md).
As soluções dos puzzles de cada ato estão em [`docs/CONTEXTO.md`](docs/CONTEXTO.md).

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
