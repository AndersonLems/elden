"""Utilitário dos geradores de mapas: valida o desenho ASCII e grava data/levels/<id>.json."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def rows_from(text, pad="#"):
    lines = [l.rstrip("\n") for l in text.strip("\n").splitlines()]
    w = max(len(l) for l in lines)
    out = []
    for l in lines:
        if len(l) < w:
            l = l + pad * (w - len(l))
        out.append(l)
    return out


def save(level):
    rows = level["rows"]
    w = len(rows[0])
    for i, r in enumerate(rows):
        if len(r) != w:
            sys.exit(f"{level['id']}: linha {i} com largura {len(r)} (esperado {w})")
    path = os.path.join(ROOT, "data", "levels", level["id"] + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(level, f, ensure_ascii=False, indent=1)
    print("gravado", path, f"{w}x{len(rows)}")


def find(rows, ch):
    """Coordenadas (x, z) de todas as ocorrências de um caractere (z cresce para o norte)."""
    out = []
    d = len(rows)
    for r, row in enumerate(rows):
        for x, c in enumerate(row):
            if c == ch:
                out.append((x + 0.5, d - 1 - r + 0.5))
    return out
