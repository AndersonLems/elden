# Reformulação visual 2.5D

## Arquitetura anterior

O mundo lógico sempre foi tridimensional (`x`, altura `y`, `z`), mas a projeção visual era
`tela_x=x`, `tela_y=z+y`. Apenas topos e faces sul da grade eram gerados. Isso preservava texels,
porém escondia um dos eixos horizontais e aproximava a composição de um top-down.

A simulação, colisões, rampas, plataformas e alcance de ataques já operavam corretamente no plano
X/Z e foram preservados.

## Câmera e projeção novas

`elden/render/projection.py` define uma projeção ortográfica semi-isométrica com azimute de 45° e
elevação de 38°. O shader usa a mesma base para posição e profundidade. Sprites são billboards
verticais: os pés participam do depth buffer e o quadro não é inclinado pela rotação do chão.

WASD expressa direções da tela e é convertido para X/Z antes de chegar ao `InputState`. Assim, W
sempre sobe visualmente e D sempre segue para a direita, sem alterar hitboxes, IA ou projéteis.
A câmera mantém antecipação, seguimento suave, zoom de chefe, limites e shake existentes.

## Geometria, profundidade e oclusão

`level_mesh.py` agora gera as quatro faces expostas de cada célula, em faixas de uma unidade para
manter a densidade de texels. Desníveis, pontes, plataformas e bordas de abismos apresentam volume
sob qualquer enquadramento. O depth buffer de 24 bits continua sendo a autoridade de oclusão.
Sprites usam profundidade dos pés, sombras de contato ficam no piso, e a silhueta dourada do jogador
permanece visível quando uma estrutura o encobre.

O AO escolhido é geométrico por vértice, calculado pela ocupação da grade. Ele é estável em baixa
resolução, não cria halos de SSAO e pode ser desligado pelo perfil baixo. SSAO foi descartado nesta
etapa por exigir profundidade linear adicional e introduzir instabilidade subpixel desproporcional ao
benefício na pixel art.

## Iluminação e composição

O pipeline HDR preservado executa: cena com luz direcional e até 16 luzes pontuais; sombras por
raymarching da ocupação; bloom em duas escalas; ACES, color grading por ambiente, vinheta e grão;
UI em passe separado. O bloom continua restrito por threshold e foi moderado nos perfis para manter
contornos. O buffer interno usa nearest-neighbor e escala inteira; não foi adicionado FSR porque a
reconstrução espacial suavizaria os pixels e não trouxe uma vantagem demonstrável para esta arte.

## Pipeline de arte externa

`assets/manifest.json` é o catálogo versionado de modelos, texturas, folhas de sprites, animações e
materiais produzidos fora do Python. `elden/render/assets.py` valida caminhos e extensões, carrega sob
demanda, configura nearest-neighbor para pixel art, guarda cache e instancia modelos. Mapas podem
declarar `visual_assets`, e props podem declarar `asset`. Se o recurso estiver ausente ou inválido,
a vista procedural existente continua sendo usada.

Validação:

```bash
python3 tools/dev/validar_assets.py
```

O manifesto do primeiro PR nasceu vazio; a iteração 2.0 passou a registrar o pacote gótico real
descrito ao fim deste documento. Convenções e formatos estão em `assets/README.md`.

## Qualidade e desempenho

| Perfil | Resolução interna | AO | Bloom | Luzes | Sombras |
|---|---:|---:|---:|---:|---:|
| baixa | 200p | não | não | 6 | não |
| média | 240p | 65% | 65% | 10 | 6 passos |
| alta | 240p | 85% | 90% | 16 | 10–12 passos |
| ultra | 270p | 100% | 105% | 16 | 16–20 passos |

Medição offscreen em `ato1_floresta`, 1280×720, perfil alto, 68 vistas:

- base: 5,2–5,9 ms de update nas amostras estáveis; quadro 16,7 ms;
- reforma: 4,1–4,5 ms de update nas amostras estáveis; quadro 16,7 ms;
- ambas permaneceram limitadas a 60 FPS pelo ambiente gráfico.

Esses números não provam 60 FPS em todo hardware. Os logs completos estão em
`artifacts/visual-overhaul/metrics/`.

## Testes e evidências

`tests/test_render.py` cobre eixos projetados, altura, profundidade, WASD orientado à tela, perfis,
expansão dos shaders e segurança do manifesto. A compilação real dos shaders foi exercitada pelas
capturas Panda3D/OpenGL em `artifacts/visual-overhaul/{before,after}`.

Para capturar sem abrir janela no desktop:

```bash
ELDEN_OFFSCREEN=1 python3 tools/dev/tour.py /tmp/out ato1_floresta '[[9,6,"inicio"]]'
ELDEN_OFFSCREEN=1 python3 tools/dev/ui_tour.py /tmp/out
ELDEN_OFFSCREEN=1 python3 tools/dev/perfil.py
```

## Limitações conhecidas

- O pacote V2 inclui modelos e textura da arquitetura gótica, mas ainda não inclui novas animações
  externas de personagens; as folhas procedurais continuam sendo o fallback.
- Atos III–V e a arena do Ato II não existem no repositório e, portanto, não foram validados.
- A geometria da grade agora é volumosa, mas arcos, telhados e fachadas autorais dependem dos novos
  assets ou de dados adicionais nos mapas.
- O profiling offscreen mede o ambiente atual; recomenda-se repetir em GPU alvo e janela real.

## Vertical slice artístico 2.0

A arena de Varkhan, `ato1_arena`, é o padrão visual desta segunda iteração. Ela integra arte
externa real pelo manifesto em vez de depender apenas dos geradores originais:

- atlas de pedra gótica 1024×1024 com lajes, parede trabalhada, pedra com musgo e ornamentos;
- coluna octogonal com base, fuste, capitel e pináculos;
- arco ogival modular e portão monumental com grade;
- estátua alada, escadaria, contraforte e piso cerimonial de lajes;
- oito entradas válidas em `assets/manifest.json`, com dependência de textura verificada;
- 7.316 vértices e 3.658 triângulos no pacote completo; modelos repetidos usam instâncias;
- 16 instâncias na arena em uma textura compartilhada; parte dos módulos também foi aplicada ao castelo.

O gerador determinístico em `tools/assets/build_gothic_modules.py` permite ajustar a geometria
modular; os `.bam` prontos permanecem versionados e são os arquivos carregados em runtime. O atlas
foi criado com a ferramenta integrada de geração de imagens, reduzido por nearest-neighbor e
integrado como material real. A cena final continua sendo renderizada pelo jogo.

A identidade da arena foi alterada de vermelho uniforme para luar azul-violeta com pontos quentes
de braseiros. `moon_mist` adiciona bruma baixa de alfa discreto. O piso cerimonial quebra a repetição
do tile base e organiza um centro de combate legível. Jogador e chefes receberam escala visual
moderada e contorno por texel; colisões, alcance e escala da simulação não mudaram.

Os rastros flamejantes agora mantêm uma luz curta sobre o atacante. A evidência de combate V2 usa
`mag_tempestade` de verdade: a ferramenta envia entrada ao jogador e a simulação cria zonas de fogo,
gelo e raio. Não há injeção de partículas preparada apenas para screenshot.

### Desempenho do vertical slice

Perfil alto, 1280×720, arena, 19 vistas, Intel Iris Xe do ambiente atual:

- fallback sem arte externa: 3,4–3,7 ms de update e 6,2–6,9 ms por quadro nas amostras estáveis;
- 16 instâncias externas: 3,2–4,1 ms de update e 5,8–7,5 ms por quadro;
- os tours mediram 97–264 FPS conforme a complexidade do mapa; a arena ficou normalmente entre
  180 e 240 FPS antes da captura, sem VSync.

Logs: `artifacts/visual-overhaul/v2/metrics/`. O equipamento identificado pelo renderer é Intel
Iris Xe, perfil alto, 1280×720. Os números variam com UI, partículas e carregamento e não constituem
garantia para outros hardwares.

### Captura realmente invisível

O PR inicial configurava apenas `window-type offscreen` no PRC. A Ursina o sobrescrevia com o valor
padrão do construtor e ainda mapeava uma janela. A V2 passa `window_type="offscreen"` diretamente ao
construtor e aborta se o resultado for um `GraphicsWindow`. As capturas usam um `GraphicsBuffer`,
portanto `ELDEN_OFFSCREEN=1` não abre janela no desktop.

### Limitações V2

- O acabamento autoral completo está concentrado na arena e parcialmente propagado ao castelo;
  floresta, vila e fábrica preservam majoritariamente o visual do PR #1.
- As nove classes continuam usando as folhas procedurais existentes. A V2 melhora escala, contorno,
  iluminação e efeitos, mas não afirma ter redesenhado todas as animações.
- O atlas artístico é novo, mas os módulos BAM foram construídos pelo gerador modular do projeto;
  futuros modelos esculpidos em Blender podem substituí-los pelo mesmo manifesto.
