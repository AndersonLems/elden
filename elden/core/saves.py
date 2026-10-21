"""Salvamento em espaços (slots) com escrita atômica e cópia de segurança."""
import json
import os
import time

from .paths import user_dir

SLOTS = 3


def _dir():
    d = os.path.join(user_dir(), "saves")
    os.makedirs(d, exist_ok=True)
    return d


def slot_path(slot):
    return os.path.join(_dir(), f"espaco{slot + 1}.json")


def save_session(session, slot=None):
    slot = session.slot if slot is None else slot
    data = session.to_dict()
    data["saved_at"] = time.time()
    path = slot_path(slot)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    if os.path.exists(path):
        try:
            os.replace(path, path + ".bak")
        except OSError:
            pass
    os.replace(tmp, path)
    return path


def load_session(slot):
    from ..sim.session import Session
    path = slot_path(slot)
    for p in (path, path + ".bak"):
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            s = Session.from_dict(d)
            s.slot = slot
            return s
        except (OSError, ValueError, KeyError):
            continue
    return None


def slot_info(slot):
    path = slot_path(slot)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        c = d["char"]
        return {"name": c.get("name"), "class_id": c.get("class_id"), "level": c.get("level", 1), "playtime": d.get("playtime", 0),
                "location": d.get("level"), "saved_at": d.get("saved_at", 0), "bosses": len(d.get("bosses", [])),
                "ending": d.get("ending")}
    except (OSError, ValueError, KeyError):
        return {"corrupt": True}


def delete_slot(slot):
    for p in (slot_path(slot), slot_path(slot) + ".bak"):
        if os.path.exists(p):
            os.remove(p)
