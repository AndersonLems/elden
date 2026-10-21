# Assets artísticos externos

Este diretório recebe a arte final criada fora do gerador procedural. O jogo continua funcional sem
esses arquivos: sprites e geometria atuais são o fallback durante a produção.

Registre cada recurso em `manifest.json`. Tipos aceitos: `model` (`.bam`, `.gltf`, `.glb`, `.egg`),
`texture`, `sprite_sheet`, `animation` e `material`. Use `pixel_art: true` em texturas que precisam de
filtro nearest-neighbor. Modelos usam Y como eixo vertical no mundo do ELDEN e devem ter origem no
ponto de contato com o piso. Prefira glTF/GLB como formato de intercâmbio e BAM para builds finais.

Exemplo:

```json
{"id":"ato1_arco_gotico","kind":"model","path":"models/ato1/arco.glb","scale":1.0}
```

Valide o pacote com `python3 tools/dev/validar_assets.py`. Caminhos absolutos ou que escapem deste
diretório são rejeitados. Arquivos artísticos grandes podem usar Git LFS.

## Pacote gótico do Ato I

`textures/ato1/gothic_stone_atlas.png` contém quatro materiais em quadrantes. Os modelos BAM em
`models/ato1/` usam Y como altura, origem no contato com o piso e compartilham esse atlas. Eles podem
ser regenerados com `python3 tools/assets/build_gothic_modules.py`. O manifesto liga cada modelo à
textura por `texture`; dependências ausentes fazem a validação falhar.

Mapas instanciam os módulos por `visual_assets`:

```json
{"asset":"ato1_coluna_gotica","x":6.2,"y":0,"z":8.0,"angle":0,"scale":0.9}
```

Use `ELDEN_DISABLE_EXTERNAL_ASSETS=1` para testar deliberadamente o fallback procedural.
