"""Captura uma habilidade real passando pelo InputState e sistema de combate."""
if "mag_hab2" not in p.char.nodes:
    p.char.nodes.append("mag_hab2")
p.apply_loadout()
p.fp = p.max_fp
targets = [a for a in w.actors if a.team != p.team and not a.dead]
if targets:
    target = min(targets, key=lambda a: p.dist_to(a))
    p.locked = target
    p.target = target
app.input.on_key("2")
st["t"] = -1.0


def soltar(task):
    app.input.on_key("2 up")
    return task.done


def capturar(task):
    shot("07_personagem_atacando")
    return task.done


app.base.taskMgr.doMethodLater(0.05, soltar, "soltar_ataque_especial")
app.base.taskMgr.doMethodLater(0.86, capturar, "captura_ataque_especial")
