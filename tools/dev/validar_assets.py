"""Valida o manifesto e a existência dos assets externos sem abrir janela."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from elden.render.assets import load_manifest, validate_manifest


errors = validate_manifest(load_manifest())
if errors:
    print("Assets externos inválidos:")
    for error in errors:
        print("-", error)
    raise SystemExit(1)
print("Assets externos: manifesto válido")
