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

O manifesto inicial está vazio deliberadamente: a infraestrutura não finge substituir modelagem,
animação ou pintura artística que ainda não foram fornecidas. Convenções e formatos estão em
`assets/README.md`.

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

- O pacote ainda não inclui modelos ou animações artísticas externos; o manifesto está pronto para
  recebê-los e os geradores existentes são o fallback.
- Atos III–V e a arena do Ato II não existem no repositório e, portanto, não foram validados.
- A geometria da grade agora é volumosa, mas arcos, telhados e fachadas autorais dependem dos novos
  assets ou de dados adicionais nos mapas.
- O profiling offscreen mede o ambiente atual; recomenda-se repetir em GPU alvo e janela real.
