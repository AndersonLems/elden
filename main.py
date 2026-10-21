#!/usr/bin/env python3
"""ELDEN — Graça Profana: O Crepúsculo dos Deuses.

Uso:
  python3 main.py                  # janela 1280x720
  python3 main.py --tela-cheia
  python3 main.py --resolucao 1600x900 --qualidade alta
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def parse():
    ap = argparse.ArgumentParser(description="ELDEN — Graça Profana")
    ap.add_argument("--tela-cheia", action="store_true", help="iniciar em tela cheia")
    ap.add_argument("--janela", action="store_true", help="iniciar em janela")
    ap.add_argument("--resolucao", default=None, help="tamanho da janela, ex.: 1600x900")
    ap.add_argument("--qualidade", choices=["baixa", "media", "alta", "ultra"], default=None)
    a = ap.parse_args()
    args = {}
    if a.tela_cheia:
        args["fullscreen"] = True
    elif a.janela:
        args["fullscreen"] = False
    if a.resolucao:
        w, h = a.resolucao.lower().split("x")
        args["size"] = (int(w), int(h))
    if a.qualidade:
        args["quality"] = a.qualidade
    return args


if __name__ == "__main__":
    from elden.app import run
    run(parse())
