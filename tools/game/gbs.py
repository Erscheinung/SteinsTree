"""Tiny DSL that writes native GB Studio 4 project resources.

Scenes, actors, triggers and event scripts produced here are ordinary GB
Studio data: open the project in GB Studio and every line of dialogue,
every choice and every movement is editable with the mouse.

Ids are uuid5 values derived from stable names, so regenerating never breaks
references. Event ids are derived from (scene, owner, path) at write time.
"""

import hashlib
import json
import textwrap
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NS = uuid.UUID("5b0c1a3e-7d64-4a8e-9a43-6d7565726e69")
LINE = 18          # characters per dialogue line (gbs-mono, 20-tile box)
LINES = 3          # lines per dialogue page


def sid(*parts):
    return str(uuid.uuid5(NS, "/".join(str(p) for p in parts)))


# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------

class Vars:
    """Named global variables, allocated from id 100 upwards.

    Ids are permanent: tools/game/var_ids.json remembers every name ever
    allocated, so adding a variable never renumbers existing ones (scenes
    edited by hand in GB Studio keep working)."""

    REG = Path(__file__).resolve().parent / "var_ids.json"

    def __init__(self, start=100):
        self.by_name = json.loads(self.REG.read_text()) if self.REG.exists() else {}
        self.next = max([start] + [int(v) + 1 for v in self.by_name.values()])
        self.used = set()

    def __getitem__(self, name):
        if name not in self.by_name:
            self.by_name[name] = str(self.next)
            self.next += 1
        self.used.add(name)
        return self.by_name[name]

    def save(self):
        self.REG.write_text(json.dumps(self.by_name, indent=1, sort_keys=True))

    def resources(self):
        return [{"id": vid, "name": name, "symbol": "var_" + name.lower()}
                for name, vid in sorted(self.by_name.items(), key=lambda kv: int(kv[1]))]


V = Vars()


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

def ev(command, args=None, **children):
    e = {"command": command, "args": args or {}}
    if children:
        e["children"] = {k: list(v) for k, v in children.items()}
    return e


def num(v):
    return {"type": "number", "value": v}


def wrap(s, width=LINE):
    """Word-wrap one paragraph to dialogue lines; explicit \\n kept."""
    out = []
    for para in s.split("\n"):
        out += textwrap.wrap(para, width=width, break_long_words=True) or [""]
    return out


ABBREV = ("Prof.", "Dr.", "Mr.", "Mrs.", "Ms.", "St.", "vs.", "B.", "e.g.", "i.e.")


def pages(s):
    """Paginate one paragraph. Whole sentences are kept together in a box
    when every sentence fits in one box; otherwise plain line pagination."""
    import re
    lines = wrap(s)
    plain = ["\n".join(lines[i:i + LINES]) for i in range(0, len(lines), LINES)]
    if len(lines) <= LINES:
        return plain
    guarded = s
    for a in ABBREV:
        guarded = guarded.replace(a + " ", a.replace(".", "\u2024") + " ")
    sents = [x.replace("\u2024", ".") for x in re.split(r"(?<=[.!?]) +", guarded)]
    if any(len(wrap(x)) > LINES for x in sents):
        return plain
    out = []
    cur = ""
    for sent in sents:
        trial = (cur + " " + sent).strip()
        if len(wrap(trial)) <= LINES:
            cur = trial
        else:
            out.append(cur)
            cur = sent
    if cur:
        out.append(cur)
    return ["\n".join(wrap(p)) for p in out]


def text(*paras, position="bottom"):
    """One dialogue event; each paragraph is wrapped and paginated."""
    pg = []
    for p in paras:
        pg += pages(p)
    a = {"text": pg, "avatarId": ""}
    if position != "bottom":
        a["position"] = position
    return ev("EVENT_TEXT", a)


def raw(*page_list):
    """Pages used exactly as written (for $variable$ readouts)."""
    return ev("EVENT_TEXT", {"text": list(page_list), "avatarId": ""})


def say(who, *lines):
    """Speaker-prefixed lines, one event (one box sequence)."""
    return text(*[("%s: %s" % (who, l)) if who else l for l in lines])


def comment(t):
    return ev("EVENT_COMMENT", {"text": t, "__collapse": False})


def choice(var, a, b):
    return ev("EVENT_CHOICE", {"variable": V[var], "trueText": a[:17], "falseText": b[:17]})


def menu(var, options, cancel_b=False):
    a = {"variable": V[var], "items": len(options), "cancelOnLastOption": False, "cancelOnB": cancel_b,
         "layout": "menu" if len(options) > 3 else "dialogue"}
    for i, o in enumerate(options):
        a["option%d" % (i + 1)] = o[:17]
    return ev("EVENT_MENU", a)


def set_var(var, value):
    return ev("EVENT_SET_VALUE", {"variable": V[var], "value": num(value)})


def copy_var(var, src):
    return ev("EVENT_VARIABLE_MATH", {"vectorX": V[var], "operation": "set", "other": "var",
                                       "vectorY": V[src], "value": "0", "minValue": "0", "maxValue": "0",
                                       "clamp": False})


def add(var, n):
    return ev("EVENT_VARIABLE_MATH", {"vectorX": V[var], "operation": "add" if n >= 0 else "sub", "other": "val",
                                       "value": str(abs(n)), "minValue": "0", "maxValue": "0", "clamp": True})


def rnd(var, lo, hi):
    return ev("EVENT_VARIABLE_MATH", {"vectorX": V[var], "operation": "set", "other": "rnd", "value": "0",
                                       "minValue": str(lo), "maxValue": str(hi), "clamp": False})


def sub_var(var, other):
    return ev("EVENT_VARIABLE_MATH", {"vectorX": V[var], "operation": "sub", "other": "var", "vectorY": V[other],
                                       "value": "0", "minValue": "0", "maxValue": "0", "clamp": True})


def inc(var):
    return ev("EVENT_INC_VALUE", {"variable": V[var]})


OPS = {"==": "eq", "!=": "ne", "<": "lt", "<=": "lte", ">": "gt", ">=": "gte"}


def if_var(var, op, value, then, else_=None):
    """GB Studio 4 'If' with a script-value condition (variable OP number)."""
    cond = {"type": OPS[op], "valueA": {"type": "variable", "value": V[var]}, "valueB": num(value)}
    return ev("EVENT_IF", {"condition": cond, "__collapseElse": not else_}, true=then, false=else_ or [])


def if_true(var, then, else_=None):
    return if_var(var, "!=", 0, then, else_)


def switch(var, cases, default=None):
    """cases: {value: [events]} (up to 16)."""
    a = {"variable": V[var], "choices": len(cases), "__collapseElse": not default}
    ch = {}
    for i, (val, evs) in enumerate(cases.items()):
        a["value%d" % i] = num(val)
        ch["true%d" % i] = list(evs)
    ch["false"] = list(default or [])
    return {"command": "EVENT_SWITCH", "args": a, "children": ch}


def loop_while(var, op, value, body):
    opmap = {"<": "lt", "<=": "lte", ">": "gt", ">=": "gte", "==": "eq", "!=": "ne"}
    cond = {"type": opmap[op], "valueA": {"type": "variable", "value": V[var]}, "valueB": num(value)}
    return ev("EVENT_LOOP_WHILE", {"condition": cond}, true=body)


def loop(body):
    return ev("EVENT_LOOP", {}, true=body)


def group(label, body):
    return ev("EVENT_GROUP", {"__label": label, "__collapse": False}, true=body)


def wait(seconds):
    return ev("EVENT_WAIT", {"time": num(seconds), "frames": num(int(seconds * 60))})


def goto(scene_id, x, y, direction="", fade="2"):
    return ev("EVENT_SWITCH_SCENE", {"sceneId": scene_id, "x": num(x), "y": num(y), "direction": direction,
                                     "fadeSpeed": fade})


def move_to(actor, x, y, walls=False, move_type="horizontal"):
    return ev("EVENT_ACTOR_MOVE_TO", {"actorId": actor, "x": num(x), "y": num(y),
                                      "collideWith": ["walls"] if walls else [], "moveType": move_type})


def move_rel(actor, dx, dy, walls=False):
    return ev("EVENT_ACTOR_MOVE_RELATIVE", {"actorId": actor, "x": num(dx), "y": num(dy),
                                            "collideWith": ["walls"] if walls else [], "moveType": "horizontal"})


def set_pos(actor, x, y):
    return ev("EVENT_ACTOR_SET_POSITION", {"actorId": actor, "x": num(x), "y": num(y)})


def face(actor, direction):
    return ev("EVENT_ACTOR_SET_DIRECTION", {"actorId": actor, "direction": {"type": "direction", "value": direction}})


def speed(actor, s):
    return ev("EVENT_ACTOR_SET_MOVEMENT_SPEED", {"actorId": actor, "speed": s})


def hide(actor):
    return ev("EVENT_ACTOR_HIDE", {"actorId": actor})


def show(actor):
    return ev("EVENT_ACTOR_SHOW", {"actorId": actor})


def deactivate(actor):
    return ev("EVENT_ACTOR_DEACTIVATE", {"actorId": actor})


def activate(actor):
    return ev("EVENT_ACTOR_ACTIVATE", {"actorId": actor})


def emote(actor, emote_id):
    return ev("EVENT_ACTOR_EMOTE", {"actorId": actor, "emoteId": emote_id})


def flicker(actor, seconds=0.5):
    return ev("EVENT_ACTOR_EFFECTS", {"effect": "flicker", "actorId": actor, "time": seconds,
                                      "frames": int(seconds * 60)})


def set_sprite(actor, sprite_id):
    return ev("EVENT_ACTOR_SET_SPRITE", {"actorId": actor, "spriteSheetId": sprite_id})


def player_sprite(sprite_id):
    return ev("EVENT_PLAYER_SET_SPRITE", {"spriteSheetId": sprite_id, "persist": True})


def shake(seconds=0.5, magnitude=4):
    return ev("EVENT_CAMERA_SHAKE", {"time": seconds, "frames": int(seconds * 60), "shakeDirection": "horizontal",
                                     "magnitude": num(magnitude)})


def fade_out(speed="2"):
    return ev("EVENT_FADE_OUT", {"speed": speed})


def fade_in(speed="2"):
    return ev("EVENT_FADE_IN", {"speed": speed})


def music(music_id):
    return ev("EVENT_MUSIC_PLAY", {"musicId": music_id, "loop": True})


def music_stop():
    return ev("EVENT_MUSIC_STOP", {})


def sfx(kind="beep", pitch=4, freq=200, duration=0.3):
    kind = {"noise": "crash"}.get(kind, kind)   # GB Studio built-ins: beep, tone, crash
    return ev("EVENT_SOUND_PLAY_EFFECT", {"type": kind, "priority": "medium", "pitch": pitch, "frequency": freq,
                                          "duration": duration, "wait": False, "effect": 0})


def palette(bank):
    """Swap every background palette slot to a bank (day/night/dream...)."""
    import sys
    sys.path.insert(0, str(ROOT / "tools" / "map"))
    import gbc
    ids = gbc.palette_ids(bank)
    return ev("EVENT_PALETTE_SET_BACKGROUND", {"palette%d" % i: ids[i] for i in range(8)})


def input_script(button, body, persist=False):
    return ev("EVENT_SET_INPUT_SCRIPT", {"input": [button], "override": True, "persist": persist},
              true=body)


def remove_input(button):
    return ev("EVENT_REMOVE_INPUT_SCRIPT", {"input": [button]})


def timer(seconds, body, slot=1):
    return ev("EVENT_SET_TIMER_SCRIPT", {"timer": slot, "duration": seconds, "frames": int(seconds * 60)},
              script=body)


def timer_off(slot=1):
    return ev("EVENT_TIMER_DISABLE", {"timer": slot})


def get_pos(actor, vx, vy):
    return ev("EVENT_ACTOR_GET_POSITION", {"actorId": actor, "vectorX": V[vx], "vectorY": V[vy]})


def move_to_vars(actor, vx, vy):
    return ev("EVENT_ACTOR_MOVE_TO", {"actorId": actor, "x": {"type": "variable", "value": V[vx]},
                                      "y": {"type": "variable", "value": V[vy]}, "collideWith": [],
                                      "moveType": "horizontal"})


def set_pos_vars(actor, vx, vy):
    return ev("EVENT_ACTOR_SET_POSITION", {"actorId": actor, "x": {"type": "variable", "value": V[vx]},
                                           "y": {"type": "variable", "value": V[vy]}})


def if_near(actor, other, dist, then, else_=None):
    return ev("EVENT_IF_ACTOR_DISTANCE_FROM_ACTOR", {"actorId": actor, "operator": "<=", "distance": num(dist),
                                                    "otherActorId": other, "__collapseElse": not else_},
              true=then, false=else_ or [])


def projectile(sprite_id, actor="player", direction="right", spd=3, life=1.2, group="1"):
    return ev("EVENT_LAUNCH_PROJECTILE", {"spriteSheetId": sprite_id, "spriteStateId": "", "actorId": actor,
                                          "x": 0, "y": 0, "directionType": "direction", "otherActorId": "$self$",
                                          "direction": direction, "angle": 0, "angleVariable": V["Tmp"],
                                          "targetActorId": "$self$", "speed": spd, "animSpeed": 7, "lifeTime": life,
                                          "initialOffset": 0, "loopAnim": True, "destroyOnHit": True,
                                          "collisionGroup": group, "collisionMask": [group]})


def text_draw(s, x, y, location="background"):
    return ev("EVENT_TEXT_DRAW", {"text": s, "x": x, "y": y, "location": location})


def save_game():
    return ev("EVENT_SAVE_DATA", {"saveSlot": 0}, true=[], load=[])


def collisions_off(actor):
    return ev("EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": actor})


def collisions_on(actor):
    return ev("EVENT_ACTOR_COLLISIONS_ENABLE", {"actorId": actor})


def stop_update(actor):
    return ev("EVENT_ACTOR_STOP_UPDATE", {"actorId": actor})


def text_speed(speed=1):
    return ev("EVENT_TEXT_SET_ANIMATION_SPEED", {"speedIn": -1, "speedOut": -1, "speed": speed,
                                                 "allowFastForward": True})


def camera_to(x, y, spd=1):
    return ev("EVENT_CAMERA_MOVE_TO", {"x": num(x), "y": num(y), "speed": spd})


def camera_lock(spd=1):
    return ev("EVENT_CAMERA_LOCK", {"speed": spd, "axis": ["x", "y"]})


def if_input(buttons, then, else_=None):
    return ev("EVENT_IF_INPUT", {"input": list(buttons), "__collapseElse": not else_}, true=then, false=else_ or [])


def await_input(buttons=("a", "b")):
    return ev("EVENT_AWAIT_INPUT", {"input": list(buttons)})


def pop_state():
    return ev("EVENT_SCENE_POP_STATE", {"fadeSpeed": "2"})


def stop():
    return ev("EVENT_STOP", {})


def platform_state(state):
    return ev("EVENT_PLATFORMER_STATE_SET", {"state": state})


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

def _assign_ids(script, prefix):
    """Return an independent copy of `script` with ids derived from `prefix`.
    The input is never mutated, so a list shared by two owners can't end up
    with the same event ids in both (GB Studio keys events by id)."""
    # a JSON round trip (unlike deepcopy) never keeps shared sub-objects,
    # so an event reused twice in one script still gets two distinct ids
    out = json.loads(json.dumps(script))

    def walk(events, pre):
        for i, e in enumerate(events):
            p = "%s/%d" % (pre, i)
            e["id"] = str(uuid.UUID(hashlib.md5(p.encode()).hexdigest()))
            for k, kids in (e.get("children") or {}).items():
                walk(kids, p + "/" + k)
    walk(out, prefix)
    return out


class Actor:
    def __init__(self, name, sprite_id, x, y, direction="down", script=None, start=None, update=None,
                 hit1=None, hit2=None, hit3=None, move_speed=1, anim_speed=15, collision_group="",
                 persistent=False, pinned=False, animate=False, frame=0):
        self.name, self.sprite_id, self.x, self.y = name, sprite_id, x, y
        self.direction = direction
        self.script, self.start, self.update = script or [], start or [], update or []
        self.hit1, self.hit2, self.hit3 = hit1 or [], hit2 or [], hit3 or []
        self.move_speed, self.anim_speed = move_speed, anim_speed
        self.collision_group, self.persistent, self.pinned = collision_group, persistent, pinned
        self.animate, self.frame = animate, frame
        self.id = None


class Trigger:
    def __init__(self, name, x, y, w=1, h=1, script=None, leave=None):
        self.name, self.x, self.y, self.w, self.h = name, x, y, w, h
        self.script, self.leave = script or [], leave or []
        self.id = None


class Scene:
    def __init__(self, key, name, background_id, width, height, collisions="", kind="TOPDOWN",
                 folder="game", bank="day", sprite_palettes=None, script=None, pos=(0, 0)):
        self.key = key
        self.id = sid("scene", key)
        self.name, self.background_id = name, background_id
        self.width, self.height, self.collisions = width, height, collisions
        self.kind, self.folder, self.bank = kind, folder, bank
        self.sprite_palettes = sprite_palettes or {}
        self.script = script or []
        self.hit1, self.hit2, self.hit3 = [], [], []
        self.actors, self.triggers = [], []
        self.pos = pos

    def actor(self, *a, **k):
        act = Actor(*a, **k)
        act.id = sid("actor", self.key, act.name)
        self.actors.append(act)
        return act

    def trigger(self, *a, **k):
        t = Trigger(*a, **k)
        t.id = sid("trigger", self.key, t.name)
        self.triggers.append(t)
        return t


class Script:
    """A reusable GB Studio custom Script (Project > Scripts). Edit it once in
    GB Studio and every scene that calls it changes."""

    def __init__(self, key, name, events, description=""):
        self.key, self.name, self.events, self.description = key, name, events, description
        self.id = sid("script", key)


def call_script(script):
    return ev("EVENT_CALL_CUSTOM_EVENT", {"customEventId": script.id, "__name": script.name.split("/")[-1]})


def write_script(script):
    sym = _slug(script.key)
    path = ROOT / "project" / "scripts" / (_slug(script.name.split("/")[0]) if "/" in script.name else "") / (sym + ".gbsres")
    return {path: {"_resourceType": "script", "id": script.id, "name": script.name, "symbol": "script_" + sym,
                   "description": script.description, "variables": {}, "actors": {},
                   "script": _assign_ids(script.events, script.id + "/script")}}


def scene_dir(scene):
    sym = "".join(c if c.isalnum() else "_" for c in scene.key.lower())
    return ROOT / "project" / "scenes" / scene.folder / sym


def write_scene(scene, index, palette_ids, sprite_palette_ids):
    d = scene_dir(scene)
    sym = "".join(c if c.isalnum() else "_" for c in scene.key.lower())
    files = {}
    res = {
        "_resourceType": "scene", "id": scene.id, "_index": index, "type": scene.kind,
        "name": scene.folder + "/" + scene.name, "symbol": "scene_" + sym,
        "x": scene.pos[0], "y": scene.pos[1], "width": scene.width, "height": scene.height,
        "backgroundId": scene.background_id, "tilesetId": "", "colorModeOverride": "none",
        "paletteIds": palette_ids, "spritePaletteIds": sprite_palette_ids, "autoFadeSpeed": 1,
        "script": _assign_ids(scene.script, scene.id + "/script"),
        "playerHit1Script": _assign_ids(scene.hit1, scene.id + "/hit1"),
        "playerHit2Script": _assign_ids(scene.hit2, scene.id + "/hit2"),
        "playerHit3Script": _assign_ids(scene.hit3, scene.id + "/hit3"),
        "collisions": scene.collisions,
    }
    files[d / "scene.gbsres"] = res
    for i, a in enumerate(scene.actors):
        files[d / "actors" / (_slug(a.name) + ".gbsres")] = {
            "_resourceType": "actor", "id": a.id, "_index": i, "symbol": "actor_%s_%s" % (sym, _slug(a.name)),
            "prefabId": "", "name": a.name, "coordinateType": "tiles", "x": a.x, "y": a.y, "frame": a.frame,
            "animate": a.animate, "spriteSheetId": a.sprite_id, "paletteId": "", "direction": a.direction,
            "moveSpeed": a.move_speed, "animSpeed": a.anim_speed, "isPinned": a.pinned,
            "persistent": a.persistent, "collisionGroup": a.collision_group, "collisionExtraFlags": [],
            "prefabScriptOverrides": {},
            "script": _assign_ids(a.script, a.id + "/script"),
            "startScript": _assign_ids(a.start, a.id + "/start"),
            "updateScript": _assign_ids(a.update, a.id + "/update"),
            "hit1Script": _assign_ids(a.hit1, a.id + "/hit1"),
            "hit2Script": _assign_ids(a.hit2, a.id + "/hit2"),
            "hit3Script": _assign_ids(a.hit3, a.id + "/hit3"),
        }
    for i, t in enumerate(scene.triggers):
        files[d / "triggers" / (_slug(t.name) + ".gbsres")] = {
            "_resourceType": "trigger", "id": t.id, "_index": i, "symbol": "trigger_%s_%s" % (sym, _slug(t.name)),
            "prefabId": "", "name": t.name, "x": t.x, "y": t.y, "width": t.w, "height": t.h,
            "prefabScriptOverrides": {},
            "script": _assign_ids(t.script, t.id + "/script"),
            "leaveScript": _assign_ids(t.leave, t.id + "/leave"),
        }
    return files


def _slug(s):
    out = "".join(c if c.isalnum() else "_" for c in s.lower()).strip("_")
    while "__" in out:
        out = out.replace("__", "_")
    return out or "x"


def dump(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False)


def walk_events(script):
    for e in script:
        yield e
        for kids in (e.get("children") or {}).values():
            yield from walk_events(kids)
