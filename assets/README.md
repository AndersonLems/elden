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
