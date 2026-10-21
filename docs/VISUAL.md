# VISUAL — direção gráfica do ELDEN

Resumo da direção e das decisões vigentes. O histórico completo do PR #1 (V1–V3, medições e comparações) está em
`docs/VISUAL_OVERHAUL.md`; capturas em `artifacts/visual-overhaul/`.

## Identidade
- **Dark fantasy** em pixel art: ruína sagrada, gótico decadente, corrupção. Paleta curta por ambiente, sombras profundas,
  pontos de luz quentes (tochas, braseiros, Graças) contra luz fria (luar, névoa).
- **Legibilidade de combate acima de detalhe:** jogador, inimigos e avisos de ataque precisam se destacar do cenário.
  Evitar ruído de alta frequência em pisos e folhagem.

## Câmera e perspectiva (vigente)
- **Semi-isométrica ortográfica 3/4:** azimute 45°, elevação 38° (`elden/render/projection.py`, compartilhado por shaders e testes).
- A simulação continua no plano X/Z; só apresentação e entrada são projetadas. WASD é orientado à tela.
- A malha gera as **quatro faces expostas** de cada célula, em faixas de 1 unidade (densidade de texel constante).
- Sprites são **billboards verticais** com profundidade dos pés; depth buffer de 24 bits decide a oclusão; silhueta dourada do
  jogador quando encoberto.
- A projeção oblíqua antiga (`tela_y = z + y`, só topo + face sul) foi **substituída** — não reintroduzir.

## Pixel art e resolução
- Render em baixa resolução interna e ampliação **inteira** nearest-neighbor; sem FSR/filtros suavizantes.
- Perfis: baixa 200p, média 240p, alta/ultra 360p (2× exato em 720p). Deslocamento sub-pixel da câmera no composite.
- Personagens: esqueleto 3D procedural rasterizado em 8 direções (5 desenhadas + 3 espelhadas). Folhas refinadas de ≥64 px
  para jogador, esqueleto, guarda morto e licano; Varkhan 96 px. Contorno por texel. Escala visual do jogador +18% (só visual).
- Pixels emissivos usam alfa 120 (shader trata alfa < 0,6 como brilho).

## Iluminação híbrida
- Luz direcional por ambiente + até 16 luzes pontuais dinâmicas (`data/environments.json`).
- Sombras de tochas por **raymarching numa textura de ocupação**; luz em faixas pontilhadas (look pixel art).
- **AO geométrico por vértice** a partir da grade (SSAO descartado: instável em baixa resolução).
- Pós: bloom em duas escalas com threshold, ACES, color grading por ambiente, vinheta e grão contidos.
- FX de ataque podem acender luz curta (rastros flamejantes).

## Arte procedural + externa
- Procedural é o **fallback permanente** (`elden/art/`). Arte externa entra por `assets/manifest.json` (`assets/README.md`).
- Padrão de referência atual: **arena de Varkhan** (`ato1_arena`) — atlas gótico 1024² + 7 módulos BAM instanciados,
  luar azul-violeta, braseiros quentes, bruma baixa `moon_mist`, piso cerimonial.

## Referências artísticas (direção)
- *Elden Ring* / *Dark Souls*: tom, Graças como checkpoints, arquitetura gótica monumental.
- *Blasphemous*: pixel art sombria e iconografia religiosa corrompida.
- *Hyper Light Drifter*, *Hades*, *Diablo*: leitura 3/4 de combate, contraste de silhueta.
- *Octopath Traveler* (HD-2D): pixel art com iluminação moderna e profundidade.

## Limitações visuais conhecidas
- Floresta ainda com folhagem procedural de alta frequência.
- Acabamento autoral concentrado na arena e parcialmente no castelo; floresta, vila e fábrica com visual do PR #1.
- As 9 classes ainda usam as folhas procedurais (sem animações externas).
