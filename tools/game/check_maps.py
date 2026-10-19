"""Static audit of every scene's layout (no emulator needed).

    python3 tools/game/check_maps.py

Checks, per scene:
  * every arrival point (any "Change Scene" event targeting it) is open
    ground for a 16x16 actor, and not inside a trigger (instant re-trigger),
  * every trigger can be reached from at least one arrival point,
  * triggers do not overlap each other,
  * actors are not placed inside walls or outside the scene.
Exit code 1 if any ERROR is found; WARN lines are worth a look.
"""

import json
import sys
from collections import deque, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "map"))
import gbc  # noqa: E402

PLATFORM_KINDS = {"PLATFORM", "SHMUP", "POINTNCLICK"}


def load_project():
    scenes = {}
    for sp in (ROOT / "project" / "scenes").rglob("scene.gbsres"):
        d = json.loads(sp.read_text())
        d["_dir"] = sp.parent
        d["_actors"] = [json.loads(p.read_text()) for p in sorted((sp.parent / "actors").glob("*.gbsres"))] \
            if (sp.parent / "actors").exists() else []
        d["_triggers"] = [json.loads(p.read_text()) for p in sorted((sp.parent / "triggers").glob("*.gbsres"))] \
            if (sp.parent / "triggers").exists() else []
        scenes[d["id"]] = d
    return scenes


def walk(script):
    for e in script or []:
        yield e
        for kids in (e.get("children") or {}).values():
            yield from walk(kids)


def all_scripts(s):
    yield "scene", s["script"]
    for a in s["_actors"]:
        for k in ("script", "startScript", "updateScript", "hit1Script"):
            yield "actor " + a.get("name", ""), a.get(k, [])
    for t in s["_triggers"]:
        yield "trigger " + t.get("name", ""), t.get("script", [])
        yield "trigger " + t.get("name", ""), t.get("leaveScript", [])


def grid_of(s):
    w, h = s["width"], s["height"]
    c = gbc.decompress8(s["collisions"]) if s["collisions"] else [0] * (w * h)
    if len(c) < w * h:
        c += [0] * (w * h - len(c))
    return [[c[y * w + x] == 0 for x in range(w)] for y in range(h)]


def fits(g, w, h, x, y):
    return 0 <= x < w - 1 and 0 <= y < h and g[y][x] and g[y][x + 1]


def reach(g, w, h, start):
    seen = {start}
    q = deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n not in seen and fits(g, w, h, *n):
                seen.add(n)
                q.append(n)
    return seen


def main():
    scenes = load_project()
    arrivals = defaultdict(list)
    for s in scenes.values():
        for owner, sc in all_scripts(s):
            for e in walk(sc):
                if e["command"] == "EVENT_SWITCH_SCENE":
                    a = e["args"]
                    x = a["x"]["value"] if isinstance(a["x"], dict) else a["x"]
                    y = a["y"]["value"] if isinstance(a["y"], dict) else a["y"]
                    if isinstance(x, int) and isinstance(y, int):
                        arrivals[a["sceneId"]].append((x, y, s["name"], owner))
    errors = warns = 0
    for sid, s in sorted(scenes.items(), key=lambda kv: kv[1]["name"]):
        name = s["name"]
        w, h = s["width"], s["height"]
        g = grid_of(s)
        out = []
        trig_cells = {}
        for t in s["_triggers"]:
            for yy in range(t["y"], t["y"] + t["height"]):
                for xx in range(t["x"], t["x"] + t["width"]):
                    if (xx, yy) in trig_cells:
                        out.append(("WARN", "triggers overlap at %d,%d: %r / %r" % (xx, yy, trig_cells[(xx, yy)],
                                                                                 t.get("name"))))
                    trig_cells[(xx, yy)] = t.get("name")
            if t["x"] + t["width"] > w or t["y"] + t["height"] > h:
                out.append(("ERROR", "trigger %r extends outside the scene" % t.get("name")))
        terrain = [row[:] for row in g]
        # solid actors block movement too (unless their init disables collisions or removes them)
        for a in s["_actors"]:
            init = json.dumps(a.get("startScript", []))
            # note: a hidden actor still collides in GB Studio; only these make it passable
            if "EVENT_ACTOR_COLLISIONS_DISABLE" in init or "EVENT_ACTOR_DEACTIVATE" in init:
                continue
            for xx in (a["x"], a["x"] + 1):
                if 0 <= xx < w and 0 <= a["y"] < h:
                    g[a["y"]][xx] = False
        reachable = set()
        for (x, y, src, owner) in arrivals.get(sid, []):
            if not (0 <= x < w and 0 <= y < h):
                out.append(("ERROR", "arrival %d,%d from %s outside the scene" % (x, y, src)))
                continue
            if s["type"] == "TOPDOWN" and s["collisions"] and not fits(g, w, h, x, y):
                out.append(("WARN", "arrival %d,%d from %s (%s) is on a wall" % (x, y, src, owner)))
            if s["type"] == "TOPDOWN" and s["collisions"] and not fits(g, w, h, x, y) and fits(terrain, w, h, x, y):
                out.append(("WARN", "arrival %d,%d from %s is blocked by an actor" % (x, y, src)))
            if (x, y) in trig_cells or (x + 1, y) in trig_cells:
                out.append(("WARN", "arrival %d,%d from %s lands on trigger %r" % (x, y, src,
                                                                                trig_cells.get((x, y)) or
                                                                                trig_cells.get((x + 1, y)))))
            if s["type"] == "TOPDOWN":
                reachable |= reach(g, w, h, (x, y))
        # soft-lock check: from every arrival, some scene-changing trigger must be reachable
        if s["type"] == "TOPDOWN" and s["collisions"]:
            leaving = [t for t in s["_triggers"] if "EVENT_SWITCH_SCENE" in json.dumps(t.get("script", []))]
            for (x, y, src, owner) in arrivals.get(sid, []):
                if not (0 <= x < w and 0 <= y < h) or not leaving:
                    continue
                comp = reach(g, w, h, (x, y))
                ok = False
                for t in leaving:
                    cells = {(cx + dx, cy) for cy in range(t["y"], t["y"] + t["height"])
                             for cx in range(t["x"], t["x"] + t["width"]) for dx in (0, -1)}
                    if cells & comp:
                        ok = True
                        break
                if not ok and len(comp) > 1:
                    out.append(("ERROR", "SOFT-LOCK: arrival %d,%d from %s can reach no exit" % (x, y, src)))
        if s["type"] == "TOPDOWN" and reachable and s["collisions"]:
            for t in s["_triggers"]:
                cells = {(xx, yy) for yy in range(t["y"], t["y"] + t["height"]) for xx in range(t["x"], t["x"] + t["width"])}
                near = {(cx + dx, cy) for cx, cy in cells for dx in (0, -1)}
                if not (near & reachable) and t.get("script"):
                    out.append(("WARN", "trigger %r at %d,%d not reachable from any arrival" % (t.get("name"), t["x"], t["y"])))
        for a in s["_actors"]:
            if not (0 <= a["x"] < w and 0 <= a["y"] < h):
                out.append(("ERROR", "actor %r outside the scene" % a.get("name")))
            elif s["type"] == "TOPDOWN" and s["collisions"] and not terrain[a["y"]][a["x"]] and not a.get("isPinned"):
                out.append(("WARN", "actor %r stands on a wall tile %d,%d" % (a.get("name"), a["x"], a["y"])))
        if out:
            print("== %s" % name)
            for lvl, msg in out:
                print("  %s %s" % (lvl, msg))
                errors += lvl == "ERROR"
                warns += lvl == "WARN"
    print("\n%d scenes checked: %d errors, %d warnings" % (len(scenes), errors, warns))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
