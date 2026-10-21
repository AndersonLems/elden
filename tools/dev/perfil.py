import os, sys, time, cProfile, pstats, io
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tests"))
from elden.app import App
app = App({"size": (1280, 720), "fullscreen": False, "novsync": True})
st = {"f": 0, "times": [], "last": time.perf_counter(), "wall": []}
prof = cProfile.Profile()
orig = app._update
def timed():
    now = time.perf_counter()
    st["wall"].append(now - st["last"]); st["last"] = now
    t0 = time.perf_counter()
    if 500 < st["f"] < 600: prof.enable()
    orig()
    if 500 < st["f"] < 600: prof.disable()
    st["times"].append(time.perf_counter() - t0)
app._update = timed
def hook(a, dt):
    st["f"] += 1
    f = st["f"]
    if f == 5:
        from elden.scenes.gameplay import GameplayScene
        from util import new_session
        s = new_session(); s.slot = 2
        app.replace(GameplayScene(app, s, "ato1_floresta", "inicio"))
    if f % 100 == 0 and f > 100:
        ts = st["times"][-100:]; ws = st["wall"][-100:]
        sv = app.scene_view
        print(f, "update ms %.1f  frame ms %.1f  parts %d/%d lights %d views %d" % (1000*sum(ts)/len(ts), 1000*sum(ws)/len(ws),
              app.fx.add.n, app.fx.dust.n, len(app.fx.lights), len(sv.views) if sv else -1), flush=True)
    if f == 620:
        s = io.StringIO(); pstats.Stats(prof, stream=s).sort_stats("tottime").print_stats(15); print(s.getvalue()[:4000])
        app.quit()
app.test_hook = hook
from elden.scenes.base import Scene
app.run(Scene(app))
