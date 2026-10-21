# MEMORY.md — decisões e armadilhas (para continuidade)

## Estado
Movido para `docs/ESTADO_ATUAL.md` (fonte única de progresso e validação). Este arquivo guarda só decisões e armadilhas.

## Decisões de projeto
- **Vertical slice visual:** arena de Varkhan usa 8 entradas do manifesto (atlas gótico + 7 BAM, 16 instâncias); `tools/assets/build_gothic_modules.py` regenera os BAM. Arte procedural continua como fallback.
- **WASD orientado à tela:** convertido para X/Z em `input_map` via `projection.screen_move_to_world`; simulação intocada.
- **Projeção semi-isométrica ortográfica:** azimute 45° e elevação 38°. As quatro faces
  expostas são geradas; sprites continuam usando a profundidade dos pés (`sprite.vert`).
- **Offscreen real:** configure `application.window_type = "offscreen"` antes de instanciar Ursina;
  apenas o PRC é sobrescrito pela engine e ainda abre uma janela.
- **Escala inteira:** resolução interna por perfil (200p/240p/360p; alta = 360p, 2× em 720p). O deslocamento sub-pixel da câmera é feito no shader de composição.
- **Sombras de tochas:** raymarching numa textura de ocupação (altura por célula); árvores contribuem com `occ`.
- **Interface** desenhada em pygame (cerca de 640x360) e enviada como textura em **BGRA** (`set_ram_image`, sem conversão). Com RGBA, o envio custava 4,5 ms.
- **Sprites:** esqueleto 3D (`rig.py`) com poses procedurais (`anims.py`).
  - 5 direções são desenhadas e as outras 3 são espelhadas.
  - Os pixels emissivos usam alfa 120 (o shader trata alfa < 0,6 como brilho).
  - As folhas ficam em cache em `~/.cache/elden-jogo/sprites` e o nome inclui um hash da especificação.
- **Elites** usam sprite com sufixo `@1.15` (gerado na escala certa, sem esticar pixels).
- **Progressão:** a Graça é a moeda de evolução; cada nível dá 1 ponto na árvore e +6 de vida máxima. Os atributos vêm da
  classe mais os nós da árvore (vida = 80 + vigor×8 + (nível−1)×6).
- **Dano contra o jogador:** sem crítico aleatório; "pelas costas" só em golpe corpo a corpo; rajadas inimigas
  (`count` > 1) acertam cada alvo uma vez. Alvo de balanceamento: golpe mediano ~10–25% da vida do personagem
  preparado para o ato, p90 ≤ ~40% (medido pelo bot, `tests/bot.py` → `preparar`).
- **Fervor** é o recurso de combate da suprema. A **Fúria** é exclusiva do Lobisomem. A munição é exclusiva do Soldado.
- **Corrupção:**
  - de 0 a 100, em faixas de 25;
  - aumenta com os nós de RUÍNA e ao absorver chefes;
  - diminui ao purificar e ao rezar com a Velária (uma vez por chefe derrotado).
  - Os finais são calculados em `Session.ending_options()`.
- **Inimigos renascem ao descansar:** a fase é recarregada na Graça (`GameplayScene.end_rest`).

## Armadilhas já resolvidas (não repetir)
- **Ursina usa `coordinate-system y-up-left`:** inverte o sentido dos triângulos. Use `set_two_sided(True)` nas raízes e nos quads de tela cheia.
- **Uma textura sem imagem num nó** faz o Panda3D descartar a região de desenho inteira. Inicialize sempre com 1x1.
- **`textures-auto-power-2`:** desligar depois de criar o `Ursina()` (ver `app.py`).
- **`GeomTriangles.clear_vertices()`** volta o índice para uint16. Chame `set_index_type(NT_uint32)` antes de escrever.
- **`FxQueue.push(_kind, **data)`:** não use a chave `kind` nos dados (use `actor_kind`, `tkind`, `mark_kind`).
- **`hash()` de strings** muda entre execuções. Use `zlib.crc32` como semente.
- **`Character.to_dict`** precisa de `deepcopy`; sem isso, a comparação de runas alterava o personagem real.
- **Música:** era gerada numa thread e disputava o GIL, derrubando o FPS. Agora é gerada em outro processo (`multiprocessing`).
- **Vsync com a janela escondida** limita o jogo a cerca de 1 FPS (compositor), o que confunde medições.
- **A* lento:** os vizinhos agora são pré-calculados em `NavGrid`.

- **Separação física ignora atores `noclip`** (partes de chefe presas ao corpo). Sem isso o braço do Serafim (peso 99)
  empurrava o corpo ~10 u/s para trás, atravessando paredes.
- **Névoa de arena precisa ficar numa linha onde o chão tem exatamente a largura da porta** (corredor de 3 células);
  se o círculo da arena alcança a linha da porta, ela é contornável. `test_chefes` detecta (chefe sai / não reabre).
- **Props sem `id` têm `pid = None`:** use `(p.pid or "")` antes de `startswith`.
- **Bot de chefe (`tests/bot.py`):** mede distância até a borda do alvo (`radius`), mira antes de atacar, foca chefe + partes
  e intercepta `player.die` (restaurar vida depois do quadro não basta: golpes > vida máxima matam e travam a luta).

- **Topo de parede é "andável"** (`level.walkable` só olha sólido/vazio): qualquer teleporte/invocação precisa exigir
  altura do chão igual à de origem (`abs(g - y) <= 0.5`) e não atravessar props sólidos (`Brain._sem_portas`).
- **Paredes `#` de altura 3 ao lado de piso `2`/`3` viram caminho** (pulo sobe ~1,54). Cerque patamares altos com `P`
  (sólido); `test_fases` acusa "topo de parede alcançável".
- **Resultados do bot dependem da ordem das lutas no processo** (contador global de ids). Para reproduzir uma seed,
  rode as anteriores antes, na mesma ordem.

- **Entidades com `if` só eram avaliadas ao carregar a fase.** O loader agora as reavalia no evento `boss_defeated`
  (portal/Graça/altar pós-chefe surgem na hora); `scene_view` registra as luzes de props que surgem depois.
- **Portas de puzzle/chave na mesma largura do corredor:** `test_fases` acusa "porta não bloqueia nada" se der para
  contornar.

- **Inimigo de mapa pode carregar saque fixo** (`loot` na entidade `enemy`): use para chaves de progressão.
  `tests/test_campanha.py` resolve cada ato logicamente; se mudar portas, chaves, plataformas ou saídas, rode-o.

## Ideias anotadas
- Telhados por tema (já existe `roof_slate`/`roof_red`), mais variações de decoração por ato.
- Sprites de sinos e reagentes para os puzzles de sequência do Ato III (hoje caem no genérico `button`).
- Bot de teste de chefe: aproximar, atacar, esquivar quando houver `enemy_windup` ou zona em `telegraphing`.
