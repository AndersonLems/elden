"""Tour de capturas: posiciona o jogador em pontos da fase e fotografa; abre menus."""
import os, sys, math, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tests"))
OUT = sys.argv[1]
LVL = sys.argv[2]
SPOTS = json.loads(sys.argv[3])          # [[x, z, nome], ...]
EXTRA = sys.argv[4] if len(sys.argv) > 4 else ""
from elden.app import App
from panda3d.core import Filename
app = App({"size": (1280, 720), "fullscreen": False, "novsync": True,
           "offscreen": os.environ.get("ELDEN_OFFSCREEN") == "1"})
st = {"f": 0, "i": 0, "t": 0.0, "phase": "load"}

def shot(name):
    app.base.win.save_screenshot(Filename(os.path.join(OUT, name + ".png")))
    print("shot", name, "fps %.0f" % app.fps, flush=True)

def hook(a, dt):
    st["f"] += 1
    if st["f"] == 3:
        from elden.scenes.gameplay import GameplayScene
        from util import new_session
        s = new_session(os.environ.get("CLS", "guerreiro")); s.slot = 2
        for k in os.environ.get("FLAGS", "").split(","):
            if k: s.set_flag(k)
        app.replace(GameplayScene(app, s, LVL, os.environ.get("SPAWN", "inicio")))
        return
    g = app.stack[0] if app.stack else None
    w = getattr(g, "world", None)
    if w is None or getattr(g, "_load_now", None):
        return
    p = w.player
    st["t"] += dt
    if st["i"] < len(SPOTS):
        x, z, name = SPOTS[st["i"]]
        if st["t"] < 0.1:
            p.x, p.z = x, z
            gy = w.level.ground_at(x, z)
            p.y = gy if gy is not None else p.y
            p.vy = 0
            w.paused_ai = os.environ.get("PAUSE_AI", "1") == "1"
            app.scene_view.camera.snap_to(x, z + p.y)
        if st["t"] > 1.2:
            shot(name)
            st["i"] += 1
            st["t"] = 0.0
    else:
        if EXTRA and st.get("extra_done") is None:
            st["extra_done"] = True
            exec(open(EXTRA).read(), {"app": app, "g": g, "w": w, "p": p, "shot": shot, "st": st})
            return
        if st["t"] > 0.5:
            app.quit()

app.test_hook = hook
from elden.scenes.base import Scene
app.run(Scene(app))
