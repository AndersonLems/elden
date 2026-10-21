"""Catálogo de arte externa com validação, cache e fallback explícito.

O manifesto não substitui a arte procedural: cada referência externa é opcional.
Quando um arquivo não existe ou falha ao carregar, o chamador mantém a vista atual.
"""
import json
import os
from dataclasses import dataclass

from panda3d.core import SamplerState

from ..core.paths import ROOT


ASSET_DIR = os.path.join(ROOT, "assets")
MANIFEST = os.path.join(ASSET_DIR, "manifest.json")
KINDS = {"model", "texture", "sprite_sheet", "animation", "material"}
EXTENSIONS = {
    "model": {".bam", ".gltf", ".glb", ".egg"},
    "texture": {".png", ".tga", ".jpg", ".jpeg"},
    "sprite_sheet": {".png"},
    "animation": {".bam", ".gltf", ".glb", ".egg"},
    "material": {".json"},
}


@dataclass(frozen=True)
class AssetSpec:
    id: str
    kind: str
    path: str
    scale: float = 1.0
    pixel_art: bool = False


def _safe_path(relative):
    path = os.path.realpath(os.path.join(ASSET_DIR, relative))
    root = os.path.realpath(ASSET_DIR) + os.sep
    return path if path.startswith(root) else None


def load_manifest(path=MANIFEST):
    if not os.path.exists(path):
        return {"version": 1, "assets": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_manifest(data=None, require_files=True):
    """Devolve erros legíveis; não exige Panda3D nem abre uma janela."""
    data = load_manifest() if data is None else data
    errors = []
    if data.get("version") != 1:
        errors.append("manifesto: version deve ser 1")
    items = data.get("assets")
    if not isinstance(items, list):
        return errors + ["manifesto: assets deve ser uma lista"]
    seen = set()
    for i, item in enumerate(items):
        where = f"assets[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: entrada deve ser um objeto")
            continue
        aid, kind, rel = item.get("id"), item.get("kind"), item.get("path")
        if not isinstance(aid, str) or not aid:
            errors.append(f"{where}: id ausente")
        elif aid in seen:
            errors.append(f"{where}: id duplicado '{aid}'")
        else:
            seen.add(aid)
        if kind not in KINDS:
            errors.append(f"{where}: kind inválido '{kind}'")
        if not isinstance(rel, str) or not rel:
            errors.append(f"{where}: path ausente")
            continue
        full = _safe_path(rel)
        if full is None:
            errors.append(f"{where}: path sai de assets/")
            continue
        ext = os.path.splitext(rel)[1].lower()
        if kind in EXTENSIONS and ext not in EXTENSIONS[kind]:
            errors.append(f"{where}: extensão '{ext}' incompatível com {kind}")
        if require_files and not os.path.isfile(full):
            errors.append(f"{where}: arquivo inexistente '{rel}'")
        if "scale" in item and (not isinstance(item["scale"], (int, float)) or item["scale"] <= 0):
            errors.append(f"{where}: scale deve ser positivo")
    return errors


class ExternalAssets:
    """Carrega recursos sob demanda; falhas retornam ``None`` para ativar fallback."""

    def __init__(self, loader, manifest=None):
        self.loader = loader
        data = load_manifest() if manifest is None else manifest
        self.errors = validate_manifest(data)
        self.specs = {}
        for item in data.get("assets", []):
            if isinstance(item, dict) and all(k in item for k in ("id", "kind", "path")):
                self.specs[item["id"]] = AssetSpec(item["id"], item["kind"], item["path"],
                                                    float(item.get("scale", 1.0)), bool(item.get("pixel_art", False)))
        self.models = {}
        self.textures = {}

    def has(self, asset_id, kind=None):
        spec = self.specs.get(asset_id)
        return spec is not None and (kind is None or spec.kind == kind) and os.path.isfile(_safe_path(spec.path) or "")

    def model(self, asset_id):
        spec = self.specs.get(asset_id)
        if spec is None or spec.kind != "model" or not self.has(asset_id):
            return None
        if asset_id not in self.models:
            node = self.loader.loadModel(_safe_path(spec.path), noCache=False)
            if node is None or node.is_empty():
                return None
            node.set_scale(spec.scale)
            self.models[asset_id] = node
        return self.models[asset_id]

    def texture(self, asset_id):
        spec = self.specs.get(asset_id)
        if spec is None or spec.kind not in ("texture", "sprite_sheet") or not self.has(asset_id):
            return None
        if asset_id not in self.textures:
            tex = self.loader.loadTexture(_safe_path(spec.path))
            if tex is None:
                return None
            filt = SamplerState.FT_nearest if spec.pixel_art else SamplerState.FT_linear
            tex.set_minfilter(filt)
            tex.set_magfilter(filt)
            self.textures[asset_id] = tex
        return self.textures[asset_id]

    def instantiate_model(self, asset_id, parent, pos=(0, 0, 0), heading=0.0):
        template = self.model(asset_id)
        if template is None:
            return None
        node = template.copy_to(parent)
        node.set_pos(*pos)
        node.set_h(heading)
        node.set_two_sided(True)
        return node
