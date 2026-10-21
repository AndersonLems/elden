"""Definições visuais (rigs) de todas as personagens: classes jogáveis, NPCs, inimigos e chefes."""
from .rig import Rig

SKIN_TONES = ["#f0c8a8", "#d8a888", "#b88060", "#8a5a3a", "#64402a", "#4a2e20"]
HAIR_STYLES = ["short", "long", "tied", "spiky", "none"]
HAIR_COLORS = ["#2a1e18", "#5a3a22", "#9a6a3a", "#c8b070", "#d8d0c8", "#7a2222", "#3a3a5a"]

CLASS_VARIANTS = {
    # cada classe: lista de esquemas de cor (variações visuais)
    "guerreiro": [dict(torso="#7a8294", arms="#5a6274", legs="#3a3c48", cape="#7a1a24", shield="#3a4a7a"),
                  dict(torso="#8a7a5a", arms="#6a5a40", legs="#40382c", cape="#1a3a2a", shield="#5a3a20"),
                  dict(torso="#5a5a62", arms="#44444c", legs="#2a2a30", cape="#3a2a50", shield="#2a2a2e")],
    "ninja": [dict(torso="#2a2a34", arms="#22222a", legs="#1e1e26", scarf="#8a1a24"),
              dict(torso="#2a3a44", arms="#22323a", legs="#1a262e", scarf="#d0c8b0"),
              dict(torso="#3a2a2a", arms="#302222", legs="#241a1a", scarf="#3a6a4a")],
    "soldado": [dict(torso="#4a5a3a", arms="#3a4a2e", legs="#2e3424", coat="#5a4a2a"),
                dict(torso="#3a4a5a", arms="#2e3a4a", legs="#242c34", coat="#2a3040"),
                dict(torso="#5a3a2a", arms="#4a2e22", legs="#32221a", coat="#6a5030")],
    "bandido": [dict(torso="#6a4a32", arms="#5a3a28", legs="#3a2a20", sash="#8a2020"),
                dict(torso="#4a4a3a", arms="#3a3a2e", legs="#2a2a22", sash="#c08030"),
                dict(torso="#5a2e2e", arms="#4a2626", legs="#2e1e1e", sash="#3a3a3a")],
    "ladrao": [dict(torso="#3a3240", arms="#2e2834", legs="#24202a", hood="#2a2430"),
               dict(torso="#2e3a32", arms="#26302a", legs="#1e2620", hood="#22302a"),
               dict(torso="#4a3a30", arms="#3e3028", legs="#2c241e", hood="#3a2c24")],
    "mago": [dict(robe="#2a2a6a", trim="#c0a040", hat="#22225a", glow="#9a7aff"),
             dict(robe="#6a1a2a", trim="#d0b060", hat="#5a1422", glow="#ff8040"),
             dict(robe="#1a4a4a", trim="#a0c0c0", hat="#143c3c", glow="#60f0e0")],
    "clerigo": [dict(robe="#d8d0c0", trim="#c0a040", tabard="#8a1a1a", shield="#d8c890"),
                dict(robe="#c8c0d8", trim="#8090c0", tabard="#2a3a6a", shield="#a0b0d0"),
                dict(robe="#4a4038", trim="#c0a040", tabard="#d8c090", shield="#6a5a40")],
    "vampiro": [dict(coat="#2a0a14", vest="#6a1020", legs="#1a1418", cape="#120408"),
                dict(coat="#1a1a2a", vest="#4a1a5a", legs="#141420", cape="#0a0a14"),
                dict(coat="#3a3a40", vest="#8a1010", legs="#202024", cape="#1a0a0a")],
    "lobisomem": [dict(torso="#5a4a3a", arms="#4a3a2e", legs="#3a2e24", fur="#4a3a2e"),
                  dict(torso="#3a3a3a", arms="#2e2e30", legs="#242426", fur="#6a6a70"),
                  dict(torso="#6a3a2a", arms="#5a2e22", legs="#3a2018", fur="#2a2220")],
}


def player_rig(class_id, appearance, transformed=False):
    skin = SKIN_TONES[appearance.get("skin", 2) % len(SKIN_TONES)]
    hair_style = HAIR_STYLES[appearance.get("hair", 0) % len(HAIR_STYLES)]
    hair_col = HAIR_COLORS[appearance.get("hair_color", 0) % len(HAIR_COLORS)]
    v = CLASS_VARIANTS[class_id][appearance.get("variant", 0) % len(CLASS_VARIANTS[class_id])]
    hair = None if hair_style == "none" else {"color": hair_col, "style": hair_style}
    base = dict(colors={"skin": skin, "boots": "#2a1e1a", "belt": "#5a3a22"}, parts={})
    c, p = base["colors"], base["parts"]
    if hair:
        p["hair"] = hair
    if class_id == "guerreiro":
        c.update(torso=v["torso"], arms=v["arms"], legs=v["legs"], shield=v["shield"], emblem="#d8b450", blade="#d0d4dc",
                 grip="#4a3020", accent="#c09a40")
        p.update(cape={"color": v["cape"], "len": 1.0}, pauldrons=v["arms"], chestplate={"color": v["torso"]})
        return Rig(weapon="sword", offhand="shield", shoulder=7.6, torso_w=7.0, **base)
    if class_id == "ninja":
        c.update(torso=v["torso"], arms=v["arms"], legs=v["legs"], blade="#e0e4ec", grip="#2a1a1a", accent="#8a8a90")
        p.update(mask={"color": v["torso"]}, cape={"color": v["scarf"], "len": 0.55})
        if hair:
            hair["style"] = "tied" if hair["style"] != "none" else "none"
        return Rig(weapon="katana", leg=11.5, torso=8.5, torso_w=5.8, limb_w=2.3, **base)
    if class_id == "soldado":
        c.update(torso=v["torso"], arms=v["arms"], legs=v["legs"], blade="#c8ccd4", grip="#3a2a1a", gun="#3a3230", barrel="#8a7a60")
        p.update(helmet={"color": "#5a5a50"}, cape={"color": v["coat"], "len": 0.8})
        return Rig(weapon="gun", offhand="rifle", **base)
    if class_id == "bandido":
        c.update(torso=v["torso"], arms=skin, legs=v["legs"], blade="#b8bcc4", grip="#4a3020", belt=v["sash"])
        p.update(cape={"color": v["sash"], "len": 0.45})
        return Rig(weapon="axe", offhand="dagger", shoulder=7.6, torso_w=7.0, limb_w=2.9, **base)
    if class_id == "ladrao":
        c.update(torso=v["torso"], arms=v["arms"], legs=v["legs"], blade="#d0d4dc", grip="#2a1a1a")
        p.update(hood={"color": v["hood"]}, cape={"color": v["hood"], "len": 0.75})
        return Rig(weapon="daggers", offhand="dagger", torso_w=5.8, limb_w=2.3, **base)
    if class_id == "mago":
        c.update(torso=v["robe"], arms=v["robe"], legs=v["robe"], skirt=v["robe"], belt=v["trim"], grip="#5a3a20", glow=v["glow"])
        p.update(skirt={"len": 0.95, "flare": 1.7}, hat={"color": v["hat"]})
        return Rig(weapon="staff", offhand="orb", **base)
    if class_id == "clerigo":
        c.update(torso=v["tabard"], arms=v["robe"], legs=v["robe"], skirt=v["robe"], belt=v["trim"], shield=v["shield"],
                 emblem="#c0a040", hammer="#d8c27a", grip="#5a3a20")
        p.update(skirt={"len": 0.8, "flare": 1.4}, helmet={"color": "#c8c4b8"} if not hair else None)
        if p.get("helmet") is None:
            p.pop("helmet")
        return Rig(weapon="holy", offhand="shield", **base)
    if class_id == "vampiro":
        c.update(torso=v["vest"], arms=v["coat"], legs=v["legs"], blade="#e0d8e0", grip="#3a0a14", accent="#c0a040",
                 skin="#e8dcd8" if appearance.get("skin", 2) < 2 else skin)
        p.update(cape={"color": v["cape"], "len": 1.2}, pauldrons=v["coat"])
        rig = Rig(weapon="rapier", eyes="#ff2030", eyes_glow=True, torso_w=5.8, **base)
        return rig
    if class_id == "lobisomem":
        if transformed:
            fur = v["fur"]
            return Rig(scale=1.25, frame=64, weapon="claws", offhand="claws", hunch=22, eyes="#ffd040", eyes_glow=True,
                       shoulder=8.5, torso_w=7.6, limb_w=3.0, leg_w=3.2, head_r=3.6,
                       colors={"skin": fur, "head": fur, "torso": fur, "arms": fur, "legs": fur, "hands": fur, "boots": fur,
                               "blade": "#e8e0d0", "belt": fur},
                       parts={"ears": {"color": fur, "len": 3.2}, "snout": {"color": fur, "len": 3.2}, "tail": {"color": fur, "len": 7}})
        c.update(torso=v["torso"], arms=skin, legs=v["legs"], blade="#c8ccd4")
        p.update(cape={"color": v["fur"], "len": 0.5}, pauldrons=v["fur"])
        return Rig(weapon="claws", offhand="claws", shoulder=7.8, torso_w=7.0, limb_w=2.9, eyes="#d0a020", **base)
    raise KeyError(class_id)


def player_sprite_id(class_id, appearance, transformed=False):
    a = appearance
    return f"pl_{class_id}_{a.get('skin', 2)}_{a.get('hair', 0)}_{a.get('hair_color', 0)}_{a.get('variant', 0)}" + ("_besta" if transformed else "")


# ---------------------------------------------------------------------------- NPCs, inimigos e chefes
def H(**kw):
    kw.setdefault("kind", "humanoid")
    return kw


SPECS = {
    # ----- NPCs
    "velaria": H(colors=dict(skin="#e0c0a8", torso="#e8e0d0", arms="#e8e0d0", skirt="#e8e0d0", legs="#e8e0d0", belt="#c0a040"),
                 parts=dict(skirt={"len": 1.0, "flare": 1.5}, hood={"color": "#f0ead8", "peak": False}), weapon="staff",
                 eyes="#4a3a2a"),
    "ferrus": H(scale=1.05, leg=9.5, torso_w=8.0, shoulder=8.6, colors=dict(skin="#b07858", torso="#6a4a32", arms="#b07858", legs="#3a3028", hammer="#7a7a80", grip="#4a3020", belt="#3a2a1a"),
                parts=dict(hair={"color": "#c8c0b8", "style": "short"}), weapon="hammer"),
    "oriana": H(colors=dict(skin="#d8a888", torso="#6a3a5a", arms="#6a3a5a", skirt="#4a2a3a", legs="#4a2a3a"),
                parts=dict(skirt={"len": 0.9, "flare": 1.5}, hat={"color": "#3a2a4a"}, hair={"color": "#9a3a22", "style": "long"})),
    "kaelen": H(colors=dict(skin="#c08868", torso="#8a8e98", arms="#7a7e88", legs="#4a4a54", blade="#d0d4dc", accent="#c0a040"),
                parts=dict(helmet={"color": "#9a9ea8", "crest": "#a01a1a"}, pauldrons="#9a9ea8", cape={"color": "#2a3a6a"}), weapon="greatsword"),
    "theodric": H(colors=dict(skin="#d8b898", torso="#3a3a4a", arms="#3a3a4a", skirt="#3a3a4a", legs="#3a3a4a", book="#5a3a2a"),
                  parts=dict(skirt={"len": 1.0, "flare": 1.4}, hair={"color": "#d8d8d8", "style": "long"}), offhand="book", hunch=12),
    "bram": H(colors=dict(skin="#b88060", torso="#4a3a2a", arms="#4a3a2a", legs="#3a3024", grip="#5a3a20"),
              parts=dict(hood={"color": "#3a4a2a"}, cape={"color": "#3a4a2a", "len": 0.8}), weapon="crossbow"),
    "lise": H(colors=dict(skin="#e0b090", torso="#7a5a3a", arms="#5a4a3a", legs="#3a3a3a"),
              parts=dict(hair={"color": "#c8a050", "style": "tied"}), weapon="hammer"),
    "agathe": H(colors=dict(skin="#d8b8a0", torso="#2a2a2a", arms="#2a2a2a", skirt="#2a2a2a", legs="#2a2a2a", belt="#d0d0d0"),
                parts=dict(skirt={"len": 1.0, "flare": 1.4}, hood={"color": "#1a1a1a", "peak": False})),
    "corvin": H(scale=0.9, colors=dict(skin="#e0c0a0", torso="#3a2a6a", arms="#3a2a6a", skirt="#3a2a6a", legs="#3a2a6a", glow="#60c0ff"),
                parts=dict(skirt={"len": 0.8, "flare": 1.3}, hat={"color": "#2a1a4a"}), weapon="staff"),
    "ysolde": H(translucent=True, colors=dict(skin="#d0e0f0", torso="#b0c8e0", arms="#a0b8d0", legs="#90a8c0", blade="#e0f0ff", glow="#c0e0ff"),
                parts=dict(helmet={"color": "#c0d8f0"}, cape={"color": "#8098c0"}), weapon="sword", eyes="#ffffff", eyes_glow=True),
    # ----- Ato I
    "esqueleto": H(limb_w=1.8, leg_w=2.0, torso_w=5.0, eyes="#ff4030", eyes_glow=True,
                   colors=dict(skin="#d8d0b8", torso="#c8c0a8", arms="#d8d0b8", legs="#c8c0a8", boots="#b8b098", blade="#9a9890", grip="#4a3020"),
                   parts=dict(), weapon="sword"),
    "lobo": dict(kind="quadruped", leg=6.0, leg_w=2.2, torso_w=4.4, head_r=2.6, eyes="#ff3020", eyes_glow=True,
                 colors=dict(cloth="#4a3a3a", cloth2="#3a2a2a", head="#4a3a3a"), parts=dict(body_len=10, tail={"len": 6, "color": "#3a2a2a"}, snout={"len": 2.5, "color": "#3a2a2a"})),
    "licano": H(scale=1.15, frame=56, hunch=25, eyes="#ffb020", eyes_glow=True, shoulder=8.4, torso_w=7.6, limb_w=3.0,
                colors=dict(skin="#4a3a32", head="#4a3a32", torso="#5a4a3e", arms="#4a3a32", legs="#3a2e28", hands="#3a2e28", boots="#3a2e28", blade="#e0d8c8"),
                parts=dict(ears={"color": "#4a3a32", "len": 3}, snout={"color": "#4a3a32", "len": 3}, tail={"color": "#3a2e28", "len": 6}), weapon="claws", offhand="claws"),
    "vampiro_menor": H(eyes="#ff2030", eyes_glow=True, colors=dict(skin="#d8ccd0", torso="#5a1020", arms="#2a0a14", legs="#1a1014", blade="#d8d0d8"),
                       parts=dict(cape={"color": "#1a0408", "len": 1.0}, hair={"color": "#1a1418", "style": "short"}), weapon="rapier"),
    "guarda_morto": H(eyes="#80c0ff", eyes_glow=True, colors=dict(skin="#8a8a7a", torso="#5a5e66", arms="#4a4e56", legs="#3a3e46", shield="#4a3a2a", emblem="#6a1a1a", blade="#8a8e94"),
                      parts=dict(helmet={"color": "#6a6e76", "full": True}, pauldrons="#6a6e76", cape={"color": "#3a1a1a", "len": 0.9}), weapon="sword", offhand="shield"),
    "cacador": H(colors=dict(skin="#a87858", torso="#3a2e24", arms="#3a2e24", legs="#2a241e", grip="#4a3020"),
                 parts=dict(hat={"color": "#2a221c"}, cape={"color": "#2a221c", "len": 0.9}), weapon="crossbow", eyes="#c0a060"),
    "morcego": dict(kind="blob", leg=12, scale=1.0, colors=dict(cloth="#3a1a24", wing="#2a0e16"), parts=dict(shape="bat"), eyes="#ff3040", eyes_glow=True),
    # ----- Ato II
    "automato": H(scale=1.15, frame=56, blocky=True, eyes="#ffa030", eyes_glow=True, shoulder=8.6, torso_w=8.0, limb_w=3.2, leg_w=3.4,
                  colors=dict(skin="#8a6a40", head="#9a7a48", torso="#7a5a32", arms="#6a5030", legs="#5a4228", hands="#3a3030", boots="#3a3030"),
                  parts=dict(helmet={"color": "#a07a40", "full": True}, pauldrons="#8a6a3a")),
    "cao_mecanico": dict(kind="quadruped", leg=6.5, leg_w=2.4, torso_w=4.8, head_r=2.6, eyes="#ff8020", eyes_glow=True,
                         colors=dict(cloth="#6a5a48", cloth2="#4a3e30", head="#7a6a50"), parts=dict(body_len=11, tail={"len": 3, "color": "#4a3e30"}, snout={"len": 3, "color": "#5a4a38"})),
    "operario": H(colors=dict(skin="#a88868", torso="#5a4a3a", arms="#a88868", legs="#3a3430", hammer="#6a6a70", grip="#4a3020"),
                  parts=dict(mask={"color": "#4a4a4a"}, helmet={"color": "#7a6a3a"}), weapon="hammer", eyes="#ff8040", eyes_glow=True),
    "sentinela": dict(kind="blob", leg=12, colors=dict(body="#4a4038", head="#7a6a50", barrel="#3a3230", glow="#ff5020"), parts=dict(shape="turret")),
    "serra": dict(kind="blob", leg=6, colors=dict(body="#5a4a3a", blade="#c0c4cc", glow="#ff7030"), parts=dict(shape="saw")),
    "guardiao_industrial": H(scale=1.35, frame=72, blocky=True, eyes="#ff6020", eyes_glow=True, shoulder=9.5, torso_w=9.0, limb_w=3.6, leg_w=3.8,
                             colors=dict(skin="#7a5a30", head="#8a6a38", torso="#6a4a28", arms="#5a4224", legs="#4a3a22", hands="#2a2828", hammer="#5a5a60", grip="#3a2a1a"),
                             parts=dict(helmet={"color": "#9a7a40", "full": True}, pauldrons="#a07a40"), weapon="hammer"),
    # ----- Ato III
    "monge": H(hunch=20, colors=dict(skin="#c89880", torso="#5a4a3a", arms="#c89880", skirt="#4a3a2e", legs="#4a3a2e", blade="#8a8a8a"),
               parts=dict(skirt={"len": 0.9, "flare": 1.3}, hood={"color": "#4a3a2e"}), weapon="flail", eyes="#ffe0a0", eyes_glow=True),
    "experimento": H(hunch=30, extra_arms=1, colors=dict(skin="#b88070", torso="#9a6a5a", arms="#b88070", legs="#8a5a4a", extra_arm="#a06050"),
                     parts=dict(), eyes="#c0ff60", eyes_glow=True),
    "cirurgiao": H(colors=dict(skin="#d8c0b0", torso="#d0d0c8", arms="#c8c8c0", legs="#3a3a3a", blade="#e0e0e0"),
                   parts=dict(mask={"color": "#e0e0d8"}, hat={"color": "#2a2a2a"}), weapon="scalpel", offhand="dagger"),
    "aberracao": H(scale=1.5, frame=80, hunch=25, extra_arms=2, eyes="#ff4060", eyes_glow=True, shoulder=9, torso_w=9, limb_w=3.4,
                   colors=dict(skin="#a05050", head="#b06060", torso="#8a4040", arms="#a05050", legs="#7a3a3a", extra_arm="#c07060", hands="#6a2a2a"), parts=dict()),
    "mutante": H(scale=1.3, frame=64, hunch=12, shoulder=10, torso_w=8.5, limb_w=4.0, eyes="#ff8040", eyes_glow=True,
                 colors=dict(skin="#9a6a5a", torso="#5a4a4a", arms="#a87060", legs="#4a3a3a", hands="#7a4a3a"), parts=dict(mask={"color": "#3a3a3a"})),
    "fanatico": H(colors=dict(skin="#c8a080", torso="#8a6a2a", arms="#8a6a2a", skirt="#6a5020", legs="#6a5020"),
                  parts=dict(skirt={"len": 0.8, "flare": 1.3}, hood={"color": "#6a5020"}), eyes="#ffd060", eyes_glow=True),
    # ----- Ato IV
    "bruxa": H(colors=dict(skin="#c0c8a8", torso="#2a1a3a", arms="#2a1a3a", skirt="#1a1028", legs="#1a1028", glow="#b060ff"),
               parts=dict(skirt={"len": 1.0, "flare": 1.6}, hat={"color": "#1a1028"}, hair={"color": "#3a3a3a", "style": "long"}), offhand="orb", eyes="#c080ff", eyes_glow=True),
    "bruxo": H(colors=dict(skin="#c8b090", torso="#1a2a5a", arms="#1a2a5a", skirt="#141e44", legs="#141e44", book="#3a2a6a", glow="#6080ff"),
               parts=dict(skirt={"len": 1.0, "flare": 1.4}, hood={"color": "#141e44"}), offhand="book", eyes="#80a0ff", eyes_glow=True),
    "armadura": H(scale=1.15, frame=56, eyes="#60c0ff", eyes_glow=True, colors=dict(skin="#2a2a3a", head="#7a8098", torso="#6a7088", arms="#5a6078", legs="#4a5068", blade="#a0c0ff", accent="#6a5aa0"),
                  parts=dict(helmet={"color": "#7a8098", "full": True, "crest": "#5a4aa0"}, pauldrons="#7a8098", weapon_glow=True), weapon="sword"),
    "invocacao": H(scale=0.7, frame=40, colors=dict(skin="#7a4aa0", torso="#5a3a80", arms="#7a4aa0", legs="#5a3a80"),
                   parts=dict(wings={"color": "#4a2a6a", "span": 9}, horns={"color": "#2a1a3a", "len": 2}, tail={"color": "#5a3a80", "len": 4}), eyes="#ffe060", eyes_glow=True),
    "sombra": dict(kind="blob", leg=8, colors=dict(cloth="#1a1028", glow="#c0a0ff"), parts=dict(shape="shadow")),
    "sentinela_runica": dict(kind="blob", leg=22, colors=dict(body="#3a3458", glow="#60f0d0"), parts=dict(shape="rune_pillar")),
    "livro": dict(kind="blob", leg=4, colors=dict(cover="#5a2a3a", glow="#a080ff"), parts=dict(shape="book")),
    # ----- Ato V
    "cavaleiro_divino": H(scale=1.15, frame=56, eyes="#ffe8a0", eyes_glow=True,
                          colors=dict(skin="#e0d0b0", head="#d8c890", torso="#e0d8c0", arms="#c8c0a8", legs="#b0a890", blade="#fff4d0", accent="#d0a840", shield="#e0d0a0", emblem="#c09030"),
                          parts=dict(helmet={"color": "#e0d0a0", "full": True, "crest": "#fff0c0"}, pauldrons="#d8c890", cape={"color": "#e8e0d0"}, weapon_glow=True), weapon="sword", offhand="shield"),
    "anjo": H(eyes="#ffffff", eyes_glow=True, colors=dict(skin="#e8e0e0", torso="#d0c8c8", arms="#d0c8c8", skirt="#c8c0c0", legs="#c0b8b8", blade="#fff0d0", grip="#8a7a50"),
              parts=dict(skirt={"len": 1.0, "flare": 1.3}, wings={"color": "#e0d8d8", "span": 14}, halo={"color": "#ffe090", "r": 3.2, "broken": True}, faceless=True), weapon="lance"),
    "guardiao_graca": H(scale=1.6, frame=88, blocky=True, eyes="#fff0a0", eyes_glow=True, shoulder=10, torso_w=9.5, limb_w=3.8, leg_w=4.0,
                        colors=dict(skin="#c8c0a8", head="#d8d0b8", torso="#c0b8a0", arms="#b0a890", legs="#a09880", hands="#908870", hammer="#e0c870", grip="#6a5a3a"),
                        parts=dict(helmet={"color": "#d8d0b8", "full": True}, halo={"color": "#ffe090", "r": 4.0}), weapon="hammer"),
    "espirito": H(translucent=True, eyes="#a0e0ff", eyes_glow=True, colors=dict(skin="#a0b8d0", torso="#8098b8", arms="#8098b8", skirt="#6880a0", legs="#6880a0", blade="#d0f0ff"),
                  parts=dict(skirt={"len": 1.1, "flare": 1.2}, helmet={"color": "#90a8c8", "crest": "#c0d8f0"}), weapon="sword"),
    "celestial": H(scale=1.4, frame=72, extra_arms=2, eyes="#ff80a0", eyes_glow=True,
                   colors=dict(skin="#e0c8c0", head="#f0e0d8", torso="#d0b0a8", arms="#e0c8c0", legs="#c0a098", extra_arm="#f0d0c8"),
                   parts=dict(wings={"color": "#e8c8c0", "span": 16, "glow": True}, halo={"color": "#ff90b0", "r": 4.0, "broken": True}, faceless=True)),
    "boneco": dict(kind="blob", leg=8, colors=dict(cloth="#b09060", pole="#5a4030"), parts=dict(shape="dummy")),
    # ----- Chefes
    "condessa": H(scale=1.15, frame=56, eyes="#ff2030", eyes_glow=True,
                  colors=dict(skin="#e8dcd8", torso="#6a0a1a", arms="#6a0a1a", skirt="#4a0612", legs="#4a0612", blade="#f0e0e8", accent="#d0a040"),
                  parts=dict(skirt={"len": 1.05, "flare": 1.9}, hair={"color": "#1a0a10", "style": "long"}, cape={"color": "#2a0408", "len": 1.1}), weapon="rapier"),
    "varkhan": H(scale=2.0, frame=96, hunch=25, eyes="#ffe040", eyes_glow=True, shoulder=9, torso_w=8.2, limb_w=3.1, leg_w=3.3, head_r=3.4,
                 colors=dict(skin="#3a3030", head="#3a3030", torso="#4a3a36", arms="#3a3030", legs="#2e2626", hands="#2a2222", boots="#2a2222", blade="#f0e8d8", belt="#5a1a1a"),
                 parts=dict(ears={"color": "#3a3030", "len": 3}, snout={"color": "#3a3030", "len": 3}, tail={"color": "#2e2626", "len": 7}, cape={"color": "#5a1a1a", "len": 0.6}),
                 weapon="claws", offhand="claws"),
    "varkhan_besta": H(scale=2.5, frame=128, hunch=35, eyes="#ff3020", eyes_glow=True, shoulder=10, torso_w=9, limb_w=3.4, leg_w=3.6, head_r=3.6,
                       colors=dict(skin="#2a2222", head="#2a2222", torso="#3a2e2a", arms="#2a2222", legs="#221c1c", hands="#1a1616", boots="#1a1616", blade="#f8f0e0"),
                       parts=dict(ears={"color": "#2a2222", "len": 3.5}, snout={"color": "#2a2222", "len": 3.6}, tail={"color": "#221c1c", "len": 9}),
                       weapon="claws", offhand="claws"),
    "serafim": H(scale=2.6, frame=128, blocky=True, eyes="#ffa030", eyes_glow=True, shoulder=6, torso_w=10, torso_d=7, limb_w=3.5, leg_w=4.2, head_r=3.0,
                 colors=dict(skin="#7a5a30", head="#a07a40", torso="#6a4a28", arms="#6a4a28", legs="#4a3a22", hands="#3a3030", boots="#3a3030"),
                 parts=dict(helmet={"color": "#b08a48", "full": True, "crest": "#ff8030"}, chestplate={"color": "#ff9040"}, halo={"color": "#ffb060", "r": 4.0})),
    "serafim_arm": dict(kind="blob", leg=10, scale=2.0, frame=80, colors=dict(cloth="#8a6a3a", glow="#ff8030"), parts=dict(shape="orb")),
    "santo": H(scale=1.3, frame=64, eyes="#fff0c0", eyes_glow=True, colors=dict(skin="#d8b8a0", torso="#c0b8a8", arms="#a8a090", legs="#807868", blade="#f0f0f8", accent="#c0a040"),
               parts=dict(helmet={"color": "#c8c0b0", "crest": "#a01a1a"}, pauldrons="#c8c0b0", cape={"color": "#e0d8c8"}), weapon="sword"),
    "santo_mut": H(scale=1.6, frame=80, extra_arms=2, hunch=10, eyes="#ffd090", eyes_glow=True,
                   colors=dict(skin="#c89080", torso="#b09888", arms="#b88878", legs="#7a6858", blade="#f0f0f8", extra_arm="#c87868"),
                   parts=dict(helmet={"color": "#b0a898"}, cape={"color": "#c8a898"}), weapon="sword"),
    "santo_hibrido": H(scale=2.2, frame=112, extra_arms=4, hunch=20, eyes="#ffe060", eyes_glow=True,
                       colors=dict(skin="#b06a60", head="#d0a090", torso="#a06058", arms="#c07868", legs="#804a40", extra_arm="#e0b090", blade="#fff0c0"),
                       parts=dict(halo={"color": "#ffd070", "r": 4.0}, wings={"color": "#d08070", "span": 12, "glow": False}), weapon="greatsword"),
    "malachar": H(scale=1.2, frame=64, eyes="#80c0ff", eyes_glow=True,
                  colors=dict(skin="#c8b8a0", torso="#1a1440", arms="#1a1440", skirt="#120e30", legs="#120e30", book="#2a1a5a", glow="#70b0ff"),
                  parts=dict(skirt={"len": 1.05, "flare": 1.7}, hood={"color": "#120e30"}, halo={"color": "#70b0ff", "r": 4.5}), offhand="book", weapon="staff"),
    "aurelion": H(scale=1.8, frame=96, eyes="#ffffff", eyes_glow=True,
                  colors=dict(skin="#f0e0c0", head="#f8ecd0", torso="#f0e0b0", arms="#e0d0a0", legs="#d0c090", blade="#fff8e0", accent="#e0b040"),
                  parts=dict(helmet={"color": "#f0d880", "crest": "#ffffff"}, pauldrons="#f0d880", cape={"color": "#fff0d0", "len": 1.2}, halo={"color": "#ffe8a0", "r": 4.2}, weapon_glow=True),
                  weapon="sword"),
    "aurelion_celestial": H(scale=2.4, frame=128, eyes="#ffffff", eyes_glow=True,
                            colors=dict(skin="#fff0d0", head="#fff8e8", torso="#f8e8c0", arms="#f0e0b0", legs="#e0d0a0", blade="#ffffff", accent="#ffd060"),
                            parts=dict(helmet={"color": "#ffe890", "crest": "#ffffff"}, wings={"color": "#fff4e0", "span": 18, "glow": True},
                                       halo={"color": "#fff0b0", "r": 5.0, "broken": True}, weapon_glow=True, faceless=True), weapon="greatsword"),
    "aurelion_fragment": dict(kind="blob", leg=14, scale=1.5, frame=56, colors=dict(cloth="#fff0b0"), parts=dict(shape="crystal")),
}

ENEMY_SPRITES = {"esqueleto": "esqueleto", "lobo": "lobo", "licano": "licano", "vampiro_menor": "vampiro_menor",
                 "guarda_morto": "guarda_morto", "cacador": "cacador", "morcego": "morcego"}


def rig_for(sprite_id):
    """Rig de qualquer sprite que não seja do jogador."""
    spec = dict(SPECS[sprite_id])
    return Rig(**spec)


TWO_HANDED = {"greatsword", "hammer", "holy", "scythe", "staff", "lance", "crossbow"}


def is_two_handed(rig):
    return rig.weapon in TWO_HANDED and rig.offhand not in ("shield", "book")
