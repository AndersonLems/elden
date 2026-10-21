#!/usr/bin/env python3
"""Pré-gera o cache de sprites, áudio e música (opcional: o jogo gera sob demanda na primeira vez).

Uso: python3 tools/gerar_assets.py [--rapido]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from elden.core.data import DB
    from elden.art import spritegen, characters
    from elden.audio import synth
    from elden.audio.manager import build_music_files, AUDIO_VERSION
    from elden.core.paths import cache_dir

    rapido = "--rapido" in sys.argv
    reqs = []
    anims = spritegen.player_anims()
    for cls in DB.classes:
        reqs.append((characters.player_sprite_id(cls, {"skin": 2, "hair": 0, "hair_color": 0, "variant": 0}), anims))
    reqs.append((characters.player_sprite_id("lobisomem", {"skin": 2, "hair": 0, "hair_color": 0, "variant": 0}, True), anims))
    if not rapido:
        for eid, d in DB.enemies.items():
            reqs.append((d.get("sprite", eid), spritegen.enemy_anims(eid)))
        for bid, b in DB.bosses.items():
            an = spritegen.boss_anims(bid)
            reqs.append((b.get("sprite", bid), an))
            for ph in b["phases"]:
                if "sprite" in ph:
                    reqs.append((ph["sprite"], an))
        for nid, n in DB.npcs.items():
            reqs.append((n.get("sprite", nid), spritegen.NPC_ANIMS))
    print(f"Gerando {len(reqs)} folhas de sprites...")
    spritegen.ensure_sheets(reqs, lambda i, n, s: print(f"  [{i}/{n}] {s}"))
    adir = os.path.join(cache_dir(), f"audio_v{AUDIO_VERSION}")
    os.makedirs(adir, exist_ok=True)
    if not os.path.exists(os.path.join(adir, "sfx_ok")):
        print("Sintetizando efeitos sonoros...")
        for name, x in synth.build_sfx().items():
            synth.write_wav(os.path.join(adir, name + ".wav"), x)
        open(os.path.join(adir, "sfx_ok"), "w").close()
    print("Sintetizando músicas (pode levar alguns minutos)...")
    build_music_files(adir)
    print("Pronto.")


if __name__ == "__main__":
    main()
