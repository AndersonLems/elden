"""Carrega shaders GLSL do disco com suporte a '#include arquivo' (cada arquivo entra uma vez)."""
import os

from panda3d.core import Shader

SHADER_DIR = os.path.join(os.path.dirname(__file__), "shaders")
_cache = {}


def _expand(name, seen):
    if name in seen:
        return ""
    seen.add(name)
    with open(os.path.join(SHADER_DIR, name), encoding="utf-8") as f:
        src = f.read()
    out = []
    for line in src.splitlines():
        s = line.strip()
        if s.startswith("#include"):
            out.append(_expand(s.split()[1].strip('"<>'), seen))
        else:
            out.append(line)
    return "\n".join(out)


def source(name):
    text = _expand(name, set())
    # a diretiva #version precisa vir primeiro; o #define FRAGMENT deve vir antes do include
    lines = text.splitlines()
    version = [l for l in lines if l.strip().startswith("#version")]
    rest = [l for l in lines if not l.strip().startswith("#version")]
    return "\n".join(version[:1] + rest)


def load(vert, frag):
    key = (vert, frag)
    if key not in _cache:
        _cache[key] = Shader.make(Shader.SL_GLSL, vertex=source(vert), fragment=source(frag))
    return _cache[key]
