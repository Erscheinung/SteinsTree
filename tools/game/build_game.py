"""Generate draft 1 of Dernier as native GB Studio 4 project data.

    python3 tools/game/build_game.py            # write everything (safe)
    python3 tools/game/build_game.py --check    # validate only, write nothing
    python3 tools/game/build_game.py --force scene_key [...]

What it writes
  project/scenes/<act>/<scene>/...   generated scenes (actors, triggers, events)
  project/palettes/muj-*.gbsres       background banks (day/night/dream/...) + UI
  project/variables.gbsres            existing variables + named story variables
  project/settings.gbsres             GBC colour, hUGE music, start scene, palettes
  assets/music/*.uge                  sample tracks (credited in README)
  surgical patches to the owner's legacy scenes (listed in docs/EDITING_GUIDE.md)

Safety: every file written is hashed into tools/game/.generated.json. If a
file has changed since (hand-edited in GB Studio or the studio), it is left
alone and reported, unless its scene key is passed after --force.
"""

import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "map"))

import gbs  # noqa: E402
from gbs import V  # noqa: E402
import gbc  # noqa: E402

ROOT = gbs.ROOT
GEN_PATH = HERE / ".generated.json"

LEGACY = {
    "logo": "382961a1-e615-4b92-92a7-f1a791b50b7a",
    "title": "4912bee2-387a-472f-ae4f-6679b6149517",
    "room": "94c18861-b352-4f49-a64d-52f2e3415077",        # Outside = B7 room 10
    "corridor": "4f68877c-5cdc-44b2-b66f-2fcb75a783b9",    # Scene 5 (B7 gallery, Mayank)
    "b7_back": "d774f396-46c9-4062-9288-a07cfbeeba81",     # Scene 6
    "b7_right_exit": "dacb3072-09e0-444c-94ee-dc3731064b92",  # Scene 7
    "b7_entrance": "bdd73ca3-4cd8-4630-bb76-e185db8bc9e9",    # Scene 8
    "b7_lounge": "b63ffe64-20be-42e1-9488-4fb58e1bc82f",      # Scene 9
    "b7_back_exit": "bf17f63e-7842-4276-b70f-bdc23ae2c8b0",   # Scene 10
    "b7_back_exit_right": "7ada10b0-6469-4377-ad3a-ef51bd648f61",  # Scene 11
    "b7_back_left": "e4bf5cd5-fe41-4ee7-8e1b-cd682272dff4",   # Scene 12
    "b7_front": "8d55091e-8af7-4cd5-8b69-e656e449f723",       # Scene 13 (scholar)
    "b7_front_right": "fdcbeb0f-345f-47b2-81d0-acde510be00a",  # Scene 14
    "b7_front_left": "888f7a31-325f-4363-8637-f182e4161e47",   # Scene 15
    "b7_chiller": "c8fd72d4-9bb0-41e8-8a16-c17e72187f30",      # Scene 16
    "mess_to_main": "e3bba6a6-20b8-4598-b6f7-af53392b66fa",    # Scene 17
}
LEGACY_DIRS = {
    "logo": "logo", "title": "title_screen", "room": "outside", "corridor": "scene_5", "b7_back": "scene_6",
    "b7_right_exit": "scene_7", "b7_entrance": "scene_8", "b7_lounge": "scene_9", "b7_back_exit": "scene_10",
    "b7_back_exit_right": "scene_11", "b7_back_left": "scene_12", "b7_front": "scene_13",
    "b7_front_right": "scene_14", "b7_front_left": "scene_15", "b7_chiller": "scene_16",
    "mess_to_main": "scene_17",
}
# legacy background file per legacy scene (for the enriched GBC copies)
LEGACY_BG = {
    "room": "B7-10", "corridor": "B7", "b7_back": "B7-back", "b7_right_exit": "B7-right-exit",
    "b7_entrance": "B7-entrance", "b7_lounge": "B7-lounge", "b7_back_exit": "B7-back-exit",
    "b7_back_exit_right": "B7-back-exit-right", "b7_back_left": "B7-back-left", "b7_front": "B7-front",
    "b7_front_right": "B7-front-right", "b7_front_left": "B7-front-left", "b7_chiller": "B7-chiller",
    "mess_to_main": "mess-to-main",
}
PAUSE_SCENE_ID = "fd223a5f-7148-4705-98a7-b0ef56cb5c74"   # referenced by the title screen's Start menu

MUSIC = {  # role -> GB Studio sample track (hUGEDriver .uge)
    "intro": "Rulz_Intro", "days": "Rulz_LightMood", "world": "Rulz_Outside", "woods": "Rulz_Into the woods",
    "battle": "Rulz_BattleTheme", "chase": "Rulz_FastPaceSpeedRace", "outbreak": "Rulz_SpaceEmergency",
    "stealth": "Rulz_UndergroundCave", "void": "Rulz_Pause_Underground", "dream": "Rulz_GonaSpace",
}

SPRITE_SLOTS = None  # filled from cast_build.SLOTS


class Ctx:
    def __init__(self):
        sys.path.insert(0, str(ROOT / "tools" / "sprites"))
        import cast_build
        global SPRITE_SLOTS
        SPRITE_SLOTS = cast_build.SLOTS
        self.cast_palettes = cast_build.PALETTES
        self.sprite_slots = cast_build.SLOTS
        self.maps = {}
        for p in (ROOT / "art" / "maps").glob("*.json"):
            if p.name.startswith(".") or p.name == "enriched_provenance.json":
                continue
            d = json.loads(p.read_text())
            if "name" in d:
                self.maps[d["name"]] = d
        self.enriched = json.loads((ROOT / "art" / "maps" / "enriched_provenance.json").read_text())
        self.scenes = {}
        self.order = []
        self.level_start = {}
        self.scripts = []
        self.legacy = {k: json.loads((ROOT / "project" / "scenes" / v / "scene.gbsres").read_text())
                       for k, v in LEGACY_DIRS.items()}
        self.emotes = {}
        for p in (ROOT / "assets" / "emotes").glob("*.gbsres"):
            d = json.loads(p.read_text())
            self.emotes[d["name"]] = d["id"]
        self.music_ids = {role: gbs.sid("music", track) for role, track in MUSIC.items()}

    # ----- assets
    def bg(self, name):
        for folder in ("muj", "enriched"):
            p = ROOT / "assets" / "backgrounds" / folder / (name + ".png.gbsres")
            if p.exists():
                return json.loads(p.read_text())["id"]
        raise KeyError("background " + name)

    def sprite(self, name):
        afterhours = {"player": "afterhours_player_walk", "mayank": "afterhours_mayank_walk",
                      "scholar": "afterhours_scholar_walk"}
        fname = afterhours.get(name, "cast_" + name)
        p = ROOT / "assets" / "sprites" / (fname + ".png.gbsres")
        return json.loads(p.read_text())["id"]

    def emote(self, name):
        return self.emotes[name]

    def music(self, role):
        return self.music_ids[role]

    # ----- scenes
    def sid_of(self, key):
        if key == "title":
            return LEGACY["title"]
        if key in LEGACY:
            return LEGACY[key]
        if key == "pause":
            return PAUSE_SCENE_ID
        return gbs.sid("scene", key)

    def scene(self, key, name, map_name, folder, kind="TOPDOWN", bank="day", pos=None, legacy_bg=None):
        if legacy_bg:
            meta = self.legacy[legacy_bg]
            bg_id = self.bg(LEGACY_BG[legacy_bg])
            w, h, coll = meta["width"], meta["height"], meta["collisions"]
        else:
            meta = self.maps[map_name]
            bg_id = self.bg(map_name)
            w, h, coll = meta["cols"], meta["rows"], meta.get("collisions", "")
        if pos is None:
            pos = (0, 0)
        s = gbs.Scene(key, name, bg_id, w, h, coll, kind=kind, folder=folder, bank=bank, pos=pos)
        if key == "pause":
            s.id = PAUSE_SCENE_ID
        s.map_name = map_name
        s.legacy_bg = legacy_bg
        self.scenes[key] = s
        self.order.append(key)
        return s

    def meta(self, map_name):
        return self.maps[map_name]


# ---------------------------------------------------------------------------
# Project-level resources
# ---------------------------------------------------------------------------

def palette_resources():
    out = {}
    for bank, slots in gbc.BANKS.items():
        for i, s in enumerate(gbc.SLOTS):
            pid = gbc.palette_id(bank, i)
            name = "MUJ %s %s" % (bank, s)
            out[ROOT / "project" / "palettes" / (pid + ".gbsres")] = {
                "_resourceType": "palette", "id": pid, "name": name, "colors": slots[s],
                "defaultName": name, "defaultColors": slots[s]}
    out[ROOT / "project" / "palettes" / "muj-ui.gbsres"] = {
        "_resourceType": "palette", "id": "muj-ui", "name": "MUJ UI", "colors": gbc.UI_PALETTE,
        "defaultName": "MUJ UI", "defaultColors": gbc.UI_PALETTE}
    return out


def settings_patch(ctx):
    p = ROOT / "project" / "settings.gbsres"
    s = json.loads(p.read_text())
    s["colorMode"] = "color"
    s["musicDriver"] = "huge"
    s["defaultBackgroundPaletteIds"] = gbc.palette_ids("day")
    order = ["player", "mayank", "divyansh", "kanishk", "parag", "anshuman", "garvita", "zombie"]
    s["defaultSpritePaletteIds"] = ["muj-spr-" + k for k in order]
    s["defaultSpritePaletteId"] = "muj-spr-player"
    s["defaultUIPaletteId"] = "muj-ui"
    player = ctx.sprite("player")
    s["defaultPlayerSprites"] = {k: player for k in s["defaultPlayerSprites"]}
    s["startSceneId"] = LEGACY["logo"]
    return p, s


def variables_resource():
    p = ROOT / "project" / "variables.gbsres"
    d = json.loads(p.read_text())
    keep = [v for v in d["variables"] if int(v["id"]) < 100]
    d["variables"] = keep + V.resources()
    return p, d


def music_files():
    """Sidecars for the sample .uge tracks in assets/music (GB Studio's
    bundled sample songs by Rulz; replace them with your own any time)."""
    out = {}
    for role, track in MUSIC.items():
        dest = ROOT / "assets" / "music" / (track + ".uge")
        if dest.exists():
            out[dest.with_name(dest.name + ".gbsres")] = {
                "_resourceType": "music", "id": gbs.sid("music", track), "name": track,
                "symbol": "song_" + "".join(c if c.isalnum() else "_" for c in track.lower()),
                "settings": {}, "filename": track + ".uge", "type": "uge"}
    return out


# ---------------------------------------------------------------------------
# Writing with the hand-edit guard
# ---------------------------------------------------------------------------

def _hash(text):
    return hashlib.sha1(text.encode()).hexdigest()


class Writer:
    def __init__(self, force=(), check=False):
        self.rec = json.loads(GEN_PATH.read_text()) if GEN_PATH.exists() else {}
        self.force = set(force)
        self.check = check
        self.skipped = []
        self.written = 0
        self.touched = set()
        self.removed = []

    def put(self, path, obj, key=None, adopt=False):
        path = Path(path)
        rel = str(path.relative_to(ROOT))
        self.touched.add(rel)
        txt = gbs.dump(obj)
        if path.exists():
            cur = path.read_text()
            if cur == txt:
                self.rec[rel] = _hash(txt)
                return
            forced = key in self.force or "*" in self.force
            if rel in self.rec and self.rec[rel] != _hash(cur) and not forced:
                self.skipped.append(rel)
                return
            if rel not in self.rec and not adopt and not forced:
                self.skipped.append(rel + " (exists but was not written by the generator)")
                return
        if self.check:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(txt)
        self.rec[rel] = _hash(txt)
        self.written += 1

    def prune(self):
        """Delete files we generated earlier that this run no longer produces
        (renamed triggers etc.), unless they were edited by hand since."""
        for rel in list(self.rec):
            if rel in self.touched or not rel.startswith("project/scenes/"):
                continue
            p = ROOT / rel
            if not p.exists():
                del self.rec[rel]
                continue
            if _hash(p.read_text()) == self.rec[rel]:
                if not self.check:
                    p.unlink()
                    del self.rec[rel]
                self.removed.append(rel)
            else:
                self.skipped.append(rel + " (no longer generated, kept because it was edited)")

    def save(self):
        if not self.check:
            GEN_PATH.write_text(json.dumps(self.rec, indent=1, sort_keys=True))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

ALLOWED = set(" !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\n")


def validate(ctx):
    problems = []
    ids = {s.id for s in ctx.scenes.values()} | set(LEGACY.values()) | {PAUSE_SCENE_ID}
    from types import SimpleNamespace
    pseudo = {("script:" + sc.key): SimpleNamespace(script=sc.events, hit1=[], actors=[], triggers=[], width=1,
                                                     height=1) for sc in ctx.scripts}
    for key, s in list(ctx.scenes.items()) + list(pseudo.items()):
        if len(s.actors) > 20:
            problems.append("%s: %d actors (max 20)" % (key, len(s.actors)))
        if len(s.triggers) > 30:
            problems.append("%s: %d triggers (max 30)" % (key, len(s.triggers)))
        sheets = {a.sprite_id for a in s.actors}
        if len(sheets) > 9:
            problems.append("%s: %d different sprite sheets (VRAM)" % (key, len(sheets)))
        scripts = [s.script, s.hit1] + [a.script for a in s.actors] + [a.start for a in s.actors] + \
                  [a.update for a in s.actors] + [a.hit1 for a in s.actors] + [t.script for t in s.triggers] + \
                  [t.leave for t in s.triggers]
        for sc in scripts:
            for e in gbs.walk_events(sc):
                a = e.get("args", {})
                if e["command"] == "EVENT_SWITCH_SCENE" and a["sceneId"] not in ids:
                    problems.append("%s: switch to unknown scene %s" % (key, a["sceneId"]))
                if e["command"] == "EVENT_MENU" and a["items"] > 3:
                    for i in range(a["items"]):
                        if len(a["option%d" % (i + 1)]) > 8:
                            problems.append("%s: menu option longer than 8 chars %r" % (key, a["option%d" % (i + 1)]))
                if e["command"] == "EVENT_TEXT":
                    for pg in a["text"]:
                        bad = set(pg) - ALLOWED
                        if bad:
                            problems.append("%s: unsupported chars %r in %r" % (key, bad, pg[:30]))
                        for line in pg.split("\n"):
                            import re
                            shown = re.sub(r"\$(L\d|T\d|V\d|\d+)\$", "00", line)
                            if len(shown) > gbs.LINE:
                                problems.append("%s: line too long %r" % (key, line))
        for a in s.actors + s.triggers:
            if not (0 <= a.x < s.width and 0 <= a.y < s.height):
                problems.append("%s: %s outside the scene at %d,%d" % (key, a.name, a.x, a.y))
    return problems


def duplicate_event_ids():
    from collections import Counter
    c = Counter()
    for p in list((ROOT / "project" / "scenes").rglob("*.gbsres")) + list((ROOT / "project" / "scripts").rglob("*.gbsres")):
        for e in gbs.walk_events(_scripts_of(json.loads(p.read_text()))):
            if "id" in e:
                c[e["id"]] += 1
    return [k for k, n in c.items() if n > 1]


def _scripts_of(d):
    out = []
    for k in ("script", "startScript", "updateScript", "hit1Script", "hit2Script", "hit3Script", "leaveScript",
              "playerHit1Script", "playerHit2Script", "playerHit3Script"):
        out += d.get(k, []) or []
    return out


def main(argv):
    check = "--check" in argv
    force = []
    if "--force" in argv:
        force = argv[argv.index("--force") + 1:]
    import story  # noqa: E402  (registers all scenes)
    ctx = Ctx()
    story.build(ctx)
    problems = validate(ctx)
    w = Writer(force=force, check=check)
    for path, obj in palette_resources().items():
        w.put(path, obj, adopt=True)
    for path, obj in music_files().items():
        w.put(path, obj, adopt=True)
    p, s = settings_patch(ctx)
    w.put(p, s, key="settings", adopt=True)
    for idx, key in enumerate(ctx.order):
        scene = ctx.scenes[key]
        pal_ids, spr_ids = story.palettes_for(ctx, scene)
        for path, obj in gbs.write_scene(scene, 100 + idx, pal_ids, spr_ids).items():
            w.put(path, obj, key=key)
    for sc in ctx.scripts:
        for path, obj in gbs.write_script(sc).items():
            w.put(path, obj, key="scripts")
    for path, obj in story.legacy_patches(ctx).items():
        w.put(path, obj, key="legacy", adopt=True)
    p, d = variables_resource()
    w.put(p, d, key="variables", adopt=True)
    if not check:
        V.save()
    dup = duplicate_event_ids()
    if dup:
        problems.append("%d event ids are used more than once (e.g. %s)" % (len(dup), dup[0]))
    w.prune()
    w.save()
    if w.removed:
        print("removed %d stale generated files" % len(w.removed))
    print("scenes generated: %d, files written: %d%s" % (len(ctx.order), w.written, " (check only)" if check else ""))
    if w.skipped:
        print("hand-edited, left alone (use --force <scene>):")
        for r in w.skipped:
            print("  ", r)
    if problems:
        print("PROBLEMS:")
        for pr in problems:
            print("  ", pr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
