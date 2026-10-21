"""Cenário reproduzível para fotografar luz e partículas de uma habilidade suprema."""
w.fx.push("ultimate", actor=p.id, ability="captura", x=p.x, y=p.y, z=p.z)
w.fx.push("lightning", x0=p.x - 2.0, y0=p.y + 0.3, z0=p.z - 1.0,
          x=p.x + 2.0, y=p.y + 1.8, z=p.z + 1.0)


def capturar(task):
    shot("08_ataque_especial")
    return task.done


app.base.taskMgr.doMethodLater(0.22, capturar, "captura_ataque_especial")
