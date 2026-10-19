"""Surgical patches to the owner's original scenes (all listed in
docs/EDITING_GUIDE.md under "What the generator changed in your scenes").

Rules: original dialogue text is never rewritten. Original events are kept
verbatim and only wrapped in chapter checks; empty edge triggers get a
"go to the campus map" script; backgrounds point at the original PNGs.  The
legacy scenes use the DMG palette with an explicit mono scene override so their detail stays
readable without flattening the source art into the generated GBC copies.
"""

import copy
import json

import gbs
from gbs import if_var, set_var, say, goto, deactivate
from story.common import CH_OUTBREAK, CH_PROLOGUE, palette_for, NAMES

ROOT = gbs.ROOT
EXTERIOR = {"b7_back_exit", "b7_back_exit_right", "b7_back_left", "b7_front", "b7_front_right",
            "b7_front_left", "b7_chiller", "mess_to_main"}


class _Fake:
    def __init__(self, key):
        self.legacy_bg = key
        self.bank = "day"


def _ids(events, prefix):
    return gbs._assign_ids(events, prefix)


def pause_hook(ctx):
    """START opens the shared 'Dernier/Pause Menu' script (edit it once in
    GB Studio > Scripts; every scene calls the same one)."""
    if not hasattr(ctx, "pause_script"):
        from story.prologue import pause_events
        ctx.pause_script = gbs.Script("pause_menu", "Dernier/Pause Menu", pause_events(ctx),
                                      "START menu: objective, bonds, save, chapter select, title")
        ctx.scripts.append(ctx.pause_script)
    return gbs.input_script("start", [gbs.call_script(ctx.pause_script)])


SNAP = ROOT / "tools" / "game" / "legacy_snapshot"


def snapshot():
    """Keep a pristine copy of the owner's scenes; patches always start from it."""
    import shutil
    from build_game import LEGACY_DIRS
    for folder in LEGACY_DIRS.values():
        src = ROOT / "project" / "scenes" / folder
        dst = SNAP / folder
        if not dst.exists():
            shutil.copytree(src, dst)


def patches(ctx):
    from build_game import LEGACY, LEGACY_DIRS, LEGACY_BG
    from story import act1, prologue
    snapshot()
    out = {}
    for key, folder in LEGACY_DIRS.items():
        d = ROOT / "project" / "scenes" / folder
        s_dir = SNAP / folder
        scene = json.loads((s_dir / "scene.gbsres").read_text())
        orig_script = copy.deepcopy(scene["script"])
        if key in ("logo", "title"):
            scene["paletteIds"] = ["after-hours"] * 7 + ["muj-ui"]
            if key == "title":
                _patch_title(ctx, scene)
            out[d / "scene.gbsres"] = scene
            continue
        scene["backgroundId"] = ctx.original_bg(LEGACY_BG[key])
        # The project is CGB-only so generated maps may use 384 unique tiles.
        # Keep the owner's original backgrounds on the DMG path explicitly;
        # this preserves their source palette and the 192-tile legacy budget.
        scene["colorModeOverride"] = "mono"
        scene["paletteIds"] = ["dmg"] * 7 + ["muj-ui"]
        night = [if_var("Chapter", "==", CH_OUTBREAK, [palette_for(ctx, _Fake(key), "night")])]
        if key == "room":
            new = night + [pause_hook(ctx)] + [
                if_var("Chapter", "==", CH_OUTBREAK, orig_script, act1.room_script(ctx))]
        elif key == "b7_front":
            new = night + [pause_hook(ctx)] + [
                if_var("Chapter", "==", CH_OUTBREAK, orig_script + [set_var("SawZombie", 1)])]
        else:
            new = night + [pause_hook(ctx)] + orig_script
        scene["script"] = _ids(new, scene["id"] + "/gen-script")
        out[d / "scene.gbsres"] = scene
        # actors
        for sp in sorted((s_dir / "actors").glob("*.gbsres")) if (s_dir / "actors").exists() else []:
            p = d / "actors" / sp.name
            a = json.loads(sp.read_text())
            if key == "corridor" and a.get("name") == "Mayank":
                a["spriteSheetId"] = ctx.sprite("mayank")
                start = copy.deepcopy(a["startScript"])
                talk = copy.deepcopy(a["script"])
                a["startScript"] = _ids([if_var("Chapter", "==", CH_OUTBREAK, start, [deactivate("$self$")])],
                                        a["id"] + "/gen-start")
                a["script"] = _ids([if_var("Chapter", "==", CH_OUTBREAK, talk + [
                    if_var("SawZombie", "==", 1, [
                        say(NAMES["Mayank"], "You saw it too. Okay. Okay. Lounge. Everyone's there. NOW."),
                        goto(ctx.sid_of("lounge"), 6, 22, "up")])])], a["id"] + "/gen-script")
                out[p] = a
            elif key == "b7_front" and a.get("spriteSheetId", "").startswith("40dcd163"):
                a["spriteSheetId"] = ctx.sprite("scholar")
                start = copy.deepcopy(a["startScript"])
                upd = copy.deepcopy(a["updateScript"])
                a["startScript"] = _ids([if_var("Chapter", "==", CH_OUTBREAK, start, [deactivate("$self$")])],
                                        a["id"] + "/gen-start")
                a["updateScript"] = _ids([if_var("Chapter", "==", CH_OUTBREAK, upd)], a["id"] + "/gen-update")
                out[p] = a
        if key == "room":
            # The owner's Outside scene has no generated actors.  Add the
            # PocketBoy as a normal editable actor so the prologue starts in
            # the original room at the owner's requested (22,20) arrival.
            actor_id = gbs.sid("actor", "outside", "Handheld")
            out[d / "actors" / "handheld.gbsres"] = {
                "_resourceType": "actor", "id": actor_id, "_index": 0,
                "symbol": "actor_outside_handheld", "prefabId": "",
                "name": "Handheld", "coordinateType": "tiles", "x": 19,
                "y": 20, "frame": 0, "animate": False,
                "spriteSheetId": ctx.sprite("handheld"), "paletteId": "",
                "direction": "down", "moveSpeed": 1, "animSpeed": 15,
                "isPinned": False, "persistent": False, "collisionGroup": "",
                "collisionExtraFlags": [], "prefabScriptOverrides": {},
                "script": gbs._assign_ids(prologue.handheld_script(ctx), actor_id + "/script"),
                "startScript": [], "updateScript": [], "hit1Script": [],
                "hit2Script": [], "hit3Script": [],
            }
        # clamp triggers that extend past the scene edge (one in the original Scene 13 data)
        for sp in sorted((s_dir / "triggers").glob("*.gbsres")) if (s_dir / "triggers").exists() else []:
            t = json.loads(sp.read_text())
            if t["x"] + t["width"] > scene["width"] or t["y"] + t["height"] > scene["height"]:
                t["width"] = min(t["width"], scene["width"] - t["x"])
                t["height"] = min(t["height"], scene["height"] - t["y"])
                out[d / "triggers" / sp.name] = t
        # empty edge triggers on exterior scenes lead to the campus world map
        if key in EXTERIOR and (s_dir / "triggers").exists():
            back = ctx.world_return["quess_mess" if key == "mess_to_main" else "legacy_b7_front"]
            for sp in sorted((s_dir / "triggers").glob("*.gbsres")):
                p = d / "triggers" / sp.name
                t = out.get(p) or json.loads(sp.read_text())
                edge = t["x"] == 0 or t["y"] == 0 or t["x"] + t["width"] >= scene["width"] or \
                    t["y"] + t["height"] >= scene["height"]
                if not t["script"] and edge:
                    t["script"] = _ids([gbs.goto(ctx.sid_of("world"), back[0], back[1], "down")],
                                       t["id"] + "/gen-exit")
                    out[p] = t
    # GBC sprite palette slots for the After Hours sprites (Mayank 1, scholar 7)
    for fname, slot in (("afterhours_player_walk", 0), ("afterhours_player_idle", 0),
                        ("afterhours_player_react", 0), ("afterhours_mayank_walk", 1), ("afterhours_mayank_idle", 1), ("afterhours_mayank_react", 1),
                        ("afterhours_scholar_walk", 7), ("afterhours_scholar_idle", 7),
                        ("afterhours_scholar_react", 7)):
        p = ROOT / "assets" / "sprites" / (fname + ".png.gbsres")
        if p.exists():
            sd = json.loads(p.read_text())
            # feet-only collision (16x8), as the original GB Studio 2 game used
            sd["boundsX"], sd["boundsY"], sd["boundsWidth"], sd["boundsHeight"] = 0, 0, 16, 8
            for st in sd["states"]:
                for an in st["animations"]:
                    for fr in an["frames"]:
                        for t in fr["tiles"]:
                            t["paletteIndex"] = slot
            out[p] = sd
    return out


def _patch_title(ctx, scene):
    """New Game -> the owner's Outside room; story variables reset first."""
    from build_game import LEGACY
    reset = [set_var(v, 0) for v in ("Chapter", "Phase", "Step", "Objective", "PrologueBattle", "PrologueIntro", "Day1IntroSeen", "Grade",
                                      "MemCount", "HubSeen", "SawZombie", "CardDay")] + \
            [set_var("Bond_" + f, 0) for f in ("Mayank", "Divyansh", "Kanishk", "Parag", "Anshuman", "Garvita")] + \
            [set_var("Mem%d" % i, 0) for i in range(1, 8)]
    for e in gbs.walk_events(scene["script"]):
        if e["command"] == "EVENT_IF" and e["args"].get("variable") == "10":
            kids = e["children"]["true"]
            for i, k in enumerate(kids):
                if k["command"] == "EVENT_SWITCH_SCENE":
                    k["args"]["sceneId"] = ctx.sid_of("room")
                    k["args"]["x"] = {"type": "number", "value": 22}
                    k["args"]["y"] = {"type": "number", "value": 20}
                    k["args"]["direction"] = "left"
                    if not any(x.get("args", {}).get("variable") == gbs.V["Chapter"] for x in kids):
                        e["children"]["true"] = _ids(copy.deepcopy(reset), scene["id"] + "/gen-reset") + kids
                    break
