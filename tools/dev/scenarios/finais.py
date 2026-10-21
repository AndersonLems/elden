"""Cenário de captura: mostra as telas dos três finais (primeira página e créditos de cada um).

Uso: ELDEN_OFFSCREEN=1 python3 tools/dev/tour.py <saida> santuario '[]' tools/dev/scenarios/finais.py
"""
from elden.scenes.ending import EndingScene, ENDING_TEXT

sessao = g.session
fila = []
for fim in ("purificacao", "dominio", "ruptura"):
    fila += [(fim, 0, f"{fim}_1"), (fim, None, f"{fim}_creditos")]
estado = {"t": 0.0, "i": -1, "cena": None}


def mostrar(task):
    from direct.showbase.ShowBaseGlobal import globalClock
    estado["t"] += globalClock.getDt()
    if estado["i"] >= 0 and estado["t"] < 2.5:
        return task.cont
    if estado["i"] >= 0:
        shot(fila[estado["i"]][2])
    estado["i"] += 1
    estado["t"] = 0.0
    if estado["i"] >= len(fila):
        app.quit()
        return task.done
    fim, pagina, _ = fila[estado["i"]]
    if estado["cena"] is None or estado["cena"].e != fim:
        if estado["cena"] is None:
            app.get_scene_view().unload()
        estado["cena"] = EndingScene(app, sessao, fim)
        app.replace(estado["cena"])
    cena = estado["cena"]
    if pagina is None:
        cena.credits = True
        cena.page = len(ENDING_TEXT[fim]["pages"]) - 1
    return task.cont


st["t"] = -999.0
app.base.taskMgr.add(mostrar, "finais")
