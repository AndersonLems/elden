# Visual Overhaul 2.5D — Câmera, Profundidade, Iluminação e Shaders

## Resumo

- substitui a leitura quase top-down por projeção semi-isométrica 45°/38°;
- gera as quatro fachadas expostas da grade e preserva rampas, plataformas e colisões;
- orienta WASD pela tela sem mudar a geometria do combate;
- mantém depth buffer, silhueta contextual, luzes dinâmicas, bloom multiescala e escala inteira;
- torna AO geométrico configurável por perfil e reduz estouro de bloom;
- adiciona pipeline de assets externos com manifesto, validação, cache e fallback procedural;
- adiciona execução offscreen para capturas e profiling sem abrir janela no desktop.

## Capturas reais do jogo

Todas as imagens abaixo foram produzidas por Panda3D/OpenGL executando o jogo, na mesma resolução
e em pontos equivalentes. Não são conceitos gerados.

| Cena | Antes | Depois |
|---|---|---|
| Santuário | ![](../artifacts/visual-overhaul/before/01_santuario.png) | ![](../artifacts/visual-overhaul/after/01_santuario.png) |
| Floresta | ![](../artifacts/visual-overhaul/before/02_floresta.png) | ![](../artifacts/visual-overhaul/after/02_floresta.png) |
| Vila | ![](../artifacts/visual-overhaul/before/03_vila.png) | ![](../artifacts/visual-overhaul/after/03_vila.png) |
| Arena do primeiro chefe | ![](../artifacts/visual-overhaul/before/04_arena_chefe.png) | ![](../artifacts/visual-overhaul/after/04_arena_chefe.png) |
| Cidade industrial | ![](../artifacts/visual-overhaul/before/05_cidade_industrial.png) | ![](../artifacts/visual-overhaul/after/05_cidade_industrial.png) |
| Fábrica | ![](../artifacts/visual-overhaul/before/06_fabrica.png) | ![](../artifacts/visual-overhaul/after/06_fabrica.png) |
| Múltiplos inimigos | ![](../artifacts/visual-overhaul/before/07_multiplos_inimigos.png) | ![](../artifacts/visual-overhaul/after/07_multiplos_inimigos.png) |
| Ataque especial | ![](../artifacts/visual-overhaul/before/08_ataque_especial.png) | ![](../artifacts/visual-overhaul/after/08_ataque_especial.png) |
| Interface do personagem | ![](../artifacts/visual-overhaul/before/09_interface_personagem.png) | ![](../artifacts/visual-overhaul/after/09_interface_personagem.png) |
| Variação de altura | ![](../artifacts/visual-overhaul/before/10_variacao_altura.png) | ![](../artifacts/visual-overhaul/after/10_variacao_altura.png) |

## Verificações

```text
python3 -m unittest discover -s tests -v     13 testes, OK
DB.validate()                               []
python3 tools/dev/validar_assets.py         manifesto válido
capturas offscreen                          shaders GLSL compilados e executados
```

Perfil alto, `ato1_floresta`, 1280×720, 68 vistas: base 5,2–5,9 ms de update nas amostras
estáveis; reforma 4,1–4,5 ms; ambos limitados a 16,7 ms/60 FPS pelo ambiente. Logs completos em
`artifacts/visual-overhaul/metrics/`.

## Compatibilidade e teste local

Não há migração de save ou mudança de dados obrigatória. Mapas sem `visual_assets` usam apenas o
fallback existente. Execute `python3 main.py`; para evidência sem janela use os comandos documentados
em `docs/VISUAL_OVERHAUL.md`.

## Problemas conhecidos

- O repositório ainda não inclui arte autoral externa; o pipeline está pronto, mas o manifesto inicia vazio.
- A arena do Ato II e os mapas dos Atos III–V não existem e não puderam ser validados visualmente.
- O objetivo de 60 FPS precisa ser repetido em GPUs alvo; o perfil atual é uma medição local offscreen.
- Arcos, telhados e estruturas autorais adicionais dependem de assets ou dados de mapa futuros.
