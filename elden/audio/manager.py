"""Gerenciador de áudio: gera (uma vez) e toca efeitos e músicas via Panda3D, com volumes e espacialização simples."""
import os
import threading
import time

from ..core.paths import cache_dir
from . import synth

AUDIO_VERSION = 3

EVENT_SFX = {
    "parry": "parry", "perfect_dodge": "perfect_dodge", "posture_break": "posture_break", "execution_hit": "execution",
    "dodge": "dodge", "jump": "jump", "land": "land", "heal": "heal", "flask": "flask", "buff": "buff", "chest": "chest",
    "door": "door", "lever": "lever", "dial": "dial", "mirror": "dial", "valve": "lever", "gear_turn": "dial", "gear_place": "lever",
    "switch": "lever", "plate": "lever", "seq_press": "dial", "puzzle_solved": "puzzle_solved", "puzzle_fail": "puzzle_fail",
    "grace_found": "grace_found", "block": "block", "explosion": "explosion", "teleport": "blink", "transform": "howl",
    "boss_start": "boss_start", "lightning": "cast_lightning", "proj_impact": "hit_ether", "break": "hit_wood",
    "pickup": "item", "steal": "item", "ultimate": "ultimate", "wall_crash": "impact", "reflect": "parry", "mist": "mist",
    "vanish": "shadow", "barrier": "holy", "last_stand": "holy", "spawn": "summon", "alert": "alert",
}


MUSIC_ORDER = ["titulo", "santuario", "ato1", "chefe1", "morte", "ato2", "chefe2", "ato3", "chefe3", "ato4", "chefe4", "ato5",
               "chefe5", "final"]


def build_music_files(directory):
    """Gera as trilhas que faltam (roda em outro processo para não travar o jogo)."""
    for name in MUSIC_ORDER:
        p = os.path.join(directory, f"mus_{name}.wav")
        if not os.path.exists(p):
            try:
                x = synth.build_track(name)
                synth.write_wav(p + ".tmp", x)
                os.replace(p + ".tmp", p)
            except Exception:
                continue


class AudioManager:
    def __init__(self, base, settings):
        self.base = base
        self.settings = settings
        self.dir = os.path.join(cache_dir(), f"audio_v{AUDIO_VERSION}")
        os.makedirs(self.dir, exist_ok=True)
        self.sounds = {}
        self.music = None
        self.music_name = None
        self.music_target = None
        self.music_vol = 0.0
        self.pending_music = {}
        self.ready = False
        self.last_played = {}
        self._thread = None
        self.enabled = base is not None and hasattr(base, "loader")
        self._build_sfx()
        self._proc = None
        if any(not os.path.exists(self._music_path(n)) for n in MUSIC_ORDER):
            import multiprocessing as mp
            try:
                self._proc = mp.Process(target=build_music_files, args=(self.dir,), daemon=True)
                self._proc.start()
            except Exception:
                self._thread = threading.Thread(target=build_music_files, args=(self.dir,), daemon=True)
                self._thread.start()

    # ------------------------------------------------------------------ geração
    def _build_sfx(self):
        marker = os.path.join(self.dir, "sfx_ok")
        if not os.path.exists(marker):
            for name, x in synth.build_sfx().items():
                synth.write_wav(os.path.join(self.dir, name + ".wav"), x)
            open(marker, "w").close()
        if not self.enabled:
            return
        for f in os.listdir(self.dir):
            if f.endswith(".wav") and not f.startswith("mus_"):
                name = f[:-4]
                try:
                    self.sounds[name] = self.base.loader.loadSfx(os.path.join(self.dir, f))
                except Exception:
                    pass
        self.ready = True

    def _music_path(self, name):
        return os.path.join(self.dir, f"mus_{name}.wav")


    # ------------------------------------------------------------------ reprodução
    def vol(self, kind):
        s = self.settings
        return s.get("master", 0.8) * s.get(kind, 0.8)

    def play(self, name, volume=1.0, pitch=1.0):
        if not self.enabled:
            return
        snd = self.sounds.get(name)
        if snd is None:
            return
        now = time.time()
        if now - self.last_played.get(name, 0) < 0.035:
            return
        self.last_played[name] = now
        try:
            snd.setVolume(min(1.0, volume * self.vol("sfx")))
            snd.setPlayRate(pitch)
            snd.play()
        except Exception:
            pass

    def play_music(self, name):
        self.music_target = name

    def update(self, dt):
        if not self.enabled:
            return
        tgt = self.music_target
        if tgt != self.music_name:
            # fade out
            self.music_vol -= dt * 0.8
            if self.music is not None:
                self.music.setVolume(max(0.0, self.music_vol) * self.vol("music"))
            if self.music_vol <= 0:
                if self.music is not None:
                    self.music.stop()
                self.music = None
                self.music_name = None
                if tgt and os.path.exists(self._music_path(tgt)):
                    try:
                        self.music = self.base.loader.loadMusic(self._music_path(tgt))
                        self.music.setLoop(True)
                        self.music.setVolume(0.0)
                        self.music_vol = 0.0
                        self.music.play()
                        self.music_name = tgt
                    except Exception:
                        self.music = None
        elif self.music is not None:
            self.music_vol = max(0.0, min(1.0, self.music_vol + dt * 0.5))
            self.music.setVolume(self.music_vol * self.vol("music"))

    def handle_event(self, ev, listener=None):
        k = ev["kind"]
        vol = 1.0
        if listener is not None and "x" in ev:
            d = ((ev["x"] - listener[0]) ** 2 + (ev["z"] - listener[1]) ** 2) ** 0.5
            vol = max(0.0, 1.0 - d / 22.0)
            if vol < 0.05:
                return
        if k == "hit":
            mat = ev.get("material", "flesh")
            self.play("hit_" + mat if ("hit_" + mat) in self.sounds else "hit_flesh", vol)
            if ev.get("crit"):
                self.play("crit", vol * 0.8)
            if ev.get("team") == "player":
                self.play("player_hurt", 0.8)
        elif k == "swing_start":
            s = ev.get("sound")
            if s:
                self.play(s, vol * 0.8)
        elif k == "zone_active":
            vis = ev.get("visual", "")
            if any(w in vis for w in ("explosion", "meteor", "impact", "burst")):
                self.play("explosion", vol * 0.7)
            elif "pillar" in vis or "spear" in vis:
                self.play("holy", vol * 0.6)
            elif "lightning" in vis:
                self.play("cast_lightning", vol * 0.7)
        elif k == "shoot":
            pass
        elif k == "death":
            self.play("death", vol * 0.7)
        elif k == "enemy_windup" and ev.get("unblockable"):
            self.play("warn", vol * 0.6)
        elif k in EVENT_SFX:
            self.play(EVENT_SFX[k], vol)
