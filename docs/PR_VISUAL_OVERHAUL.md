# Visual Overhaul 2.5D — Câmera, Profundidade, Iluminação e Shaders

## Resumo

- substitui a leitura quase top-down por projeção semi-isométrica 45°/38°;
- gera as quatro fachadas expostas da grade e preserva rampas, plataformas e colisões;
- orienta WASD pela tela sem mudar a geometria do combate;
- mantém depth buffer, silhueta contextual, luzes dinâmicas, bloom multiescala e escala inteira;
- torna AO geométrico configurável por perfil e reduz estouro de bloom;
- adiciona pipeline de assets externos com manifesto, validação, cache e fallback procedural;
- adiciona execução offscreen para capturas e profiling sem abrir janela no desktop.

## Atualização 2.0 — vertical slice artístico

- integra oito assets reais pelo manifesto: atlas gótico e sete modelos BAM reutilizáveis;
- transforma a arena de Varkhan com piso cerimonial, arco, portão, colunas, estátuas, escadaria e contrafortes;
- propaga arco, escadaria, estátuas e colunas para o Castelo de Varkhan;
- troca o vermelho uniforme da arena por luar frio, tochas quentes e bruma baixa;
- melhora escala e contorno por texel de jogador e chefes;
- conecta luz breve aos rastros flamejantes e captura `mag_tempestade` passando pelo combate real;
- corrige definitivamente o modo offscreen da Ursina, com uma asserção contra janelas onscreen.

![Main original, PR #1 e Visual Overhaul 2.0](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/v2/comparacao_3_colunas.png)

As dez comparações V2 estão em `artifacts/visual-overhaul/v2/{before,after}`. A evidência do
ataque não injeta FX: desbloqueia uma habilidade do Mago, envia entrada real e fotografa os eventos
de fogo, gelo e raio gerados pela simulação.

## Atualização 3.0 — pixel art refinada

- substitui o ruído aleatório dos pisos do Ato I por lajes maiores e deliberadas;
- redesenha o atlas gótico com paleta curta, formas legíveis e frequência apropriada à tela;
- eleva o perfil alto a 360p internos, mantendo escala inteira 2× em 720p;
- reduz grão, bloom e AO para preservar contornos;
- refina jogador, esqueleto, guarda morto e licano com folhas de 64 px; Varkhan mantém 96 px;
- aumenta somente a presença visual do jogador e adiciona detalhe de peitoral, sem alterar gameplay.

| Comparação real | V2 à esquerda · V3 à direita |
|---|---|
| Arena | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/v3/comparacao_arena_v2_v3.png) |
| Santuário | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/v3/comparacao_santuario_v2_v3.png) |

A captura de combate V3 também está versionada. A floresta ainda apresenta folhagem procedural
mais ruidosa que o novo padrão; isso permanece documentado, em vez de ser apresentado como concluído.

## Capturas reais do jogo

Todas as imagens abaixo foram produzidas por Panda3D/OpenGL executando o jogo, na mesma resolução
e em pontos equivalentes. Não são conceitos gerados.

| Cena | Antes | Depois |
|---|---|---|
| Santuário | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/before/01_santuario.png) | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/after/01_santuario.png) |
| Floresta | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/before/02_floresta.png) | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/after/02_floresta.png) |
| Vila | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/before/03_vila.png) | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/after/03_vila.png) |
| Arena do primeiro chefe | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/before/04_arena_chefe.png) | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/after/04_arena_chefe.png) |
| Cidade industrial | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/before/05_cidade_industrial.png) | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/after/05_cidade_industrial.png) |
| Fábrica | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/before/06_fabrica.png) | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/after/06_fabrica.png) |
| Múltiplos inimigos | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/before/07_multiplos_inimigos.png) | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/after/07_multiplos_inimigos.png) |
| Ataque especial | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/before/08_ataque_especial.png) | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/after/08_ataque_especial.png) |
| Interface do personagem | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/before/09_interface_personagem.png) | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/after/09_interface_personagem.png) |
| Variação de altura | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/before/10_variacao_altura.png) | ![](https://raw.githubusercontent.com/AndersonLems/elden/feature/visual-overhaul-25d/artifacts/visual-overhaul/after/10_variacao_altura.png) |

## Verificações

```text
python3 -m unittest discover -s tests -v     15 testes, OK
DB.validate()                               []
python3 tools/dev/validar_assets.py         manifesto válido
capturas offscreen                          shaders GLSL compilados e executados
```

Perfil alto, `ato1_floresta`, 1280×720, 68 vistas: base 5,2–5,9 ms de update nas amostras
estáveis; reforma 4,1–4,5 ms; ambos limitados a 16,7 ms/60 FPS pelo ambiente. Logs completos em
`artifacts/visual-overhaul/metrics/`.

Na arena V2, 19 vistas: fallback 3,4–3,7 ms de update/6,2–6,9 ms por quadro; 16 instâncias artísticas
3,2–4,1 ms/5,8–7,5 ms nas amostras estáveis. O buffer offscreen ficou sem VSync; os tours mediram
97–264 FPS conforme o mapa. Os logs V2 preservam os dados brutos.

## Compatibilidade e teste local

Não há migração de save ou mudança de dados obrigatória. Mapas sem `visual_assets` usam apenas o
fallback existente. Execute `python3 main.py`; para evidência sem janela use os comandos documentados
em `docs/VISUAL_OVERHAUL.md`.

## Problemas conhecidos

- A arte externa V2 se concentra na arena e no castelo; os demais mapas ainda usam majoritariamente o fallback.
- A arena do Ato II e os mapas dos Atos III–V não existem e não puderam ser validados visualmente.
- O objetivo de 60 FPS precisa ser repetido em GPUs alvo; o perfil atual é uma medição local offscreen.
- Arcos, telhados e estruturas autorais adicionais dependem de assets ou dados de mapa futuros.
