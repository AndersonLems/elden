import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tests"))
OUT = sys.argv[1]
from elden.app import App
from panda3d.core import Filename
app = App({"size": (1280, 720), "fullscreen": False, "novsync": True})
st = {"f": 0, "step": 0, "t": 0.0}

def shot(name):
    app.base.win.save_screenshot(Filename(os.path.join(OUT, name + ".png")))
    print("shot", name, flush=True)

def game():
    return app.stack[0] if app.stack else None

def plan():
    from elden.scenes.creation import CreationScene
    from elden.scenes.gameplay import GameplayScene
    from elden.scenes import menus, dialogue
    from util import new_session
    s = new_session(os.environ.get("CLS", "mago")); s.slot = 2
    s.char.grace = 5000; s.char.add_rune("trovao"); s.char.add_rune("eclipse"); s.char.add_rune("sangue_eterno"); s.char.add_weapon("katana_lua")
    s.graces["graca_santuario"] = {"name": "Santuário da Última Chama", "level": "santuario"}
    yield ("do", lambda: app.replace(CreationScene(app, 2)), 1.0)
    yield ("shot", "u1_criacao", 0.1)
    yield ("do", lambda: setattr(app.top, "cls", 7), 1.2)
    yield ("shot", "u2_criacao_vampiro", 0.1)
    yield ("do", lambda: app.replace(GameplayScene(app, s, "santuario", "inicio")), 3.0)
    yield ("wait", None, 2.0)
    yield ("do", lambda: s.events.append(("rest", "graca_santuario")), 1.0)
    yield ("shot", "u3_graca", 0.1)
    yield ("do", lambda: app.push(menus.TreeScreen(app, s, game().world.player)), 0.6)
    yield ("shot", "u4_arvore", 0.1)
    yield ("do", lambda: setattr(app.top, "tab", 3) or app.top._select_first(), 0.5)
    yield ("shot", "u5_arvore_classe", 0.1)
    yield ("do", lambda: app.pop(), 0.3)
    yield ("do", lambda: app.push(menus.RunesScreen(app, s, game().world.player)), 0.6)
    yield ("shot", "u6_runas", 0.1)
    yield ("do", lambda: app.pop(), 0.3)
    yield ("do", lambda: app.push(menus.EquipScreen(app, s, game().world.player)), 0.6)
    yield ("shot", "u7_armas", 0.1)
    yield ("do", lambda: app.pop(), 0.3)
    yield ("do", lambda: app.push(menus.StatusScreen(app, s, game().world.player)), 0.6)
    yield ("shot", "u8_status", 0.1)
    yield ("do", lambda: app.pop(), 0.3)
    yield ("do", lambda: app.pop(), 2.5)
    yield ("do", lambda: app.push(dialogue.DialogueOverlay(app, game(), "velaria_intro", "velaria")), 1.5)
    yield ("shot", "u9_dialogo", 0.1)
    yield ("do", lambda: app.pop(), 0.3)
    yield ("do", lambda: app.push(menus.CombosScreen(app, game().world.player)), 0.6)
    yield ("shot", "u10_combos", 0.1)
    yield ("do", lambda: app.quit(), 0.1)

gen = None
def hook(a, dt):
    global gen
    st["f"] += 1
    if st["f"] < 5:
        return
    g = game()
    if g is not None and getattr(g, "_load_now", None):
        return
    if gen is None:
        gen = plan(); st["cur"] = next(gen); st["t"] = 0.0; st["done"] = False
    kind, arg, delay = st["cur"]
    if not st["done"]:
        st["done"] = True
        if kind == "do":
            arg()
        elif kind == "shot":
            shot(arg)
    st["t"] += dt
    if st["t"] >= delay:
        try:
            st["cur"] = next(gen); st["t"] = 0.0; st["done"] = False
        except StopIteration:
            app.quit()

app.test_hook = hook
from elden.scenes.base import Scene
app.run(Scene(app))
