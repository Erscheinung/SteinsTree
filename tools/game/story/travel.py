"""The explorable campus: world map, exteriors, interiors and their links.

Story modules decorate these scenes (actors, init scripts) and register
location gates (ctx.loc_gate[target]) that can redirect a world-map entrance
during the outbreak. finalize() builds the location trigger scripts last.
"""

import gbs
from story.common import open_spot, night_palette, CH_OUTBREAK, CH_DOME

FOLDER_WORLD = "2 Campus"
FOLDER_IN = "2 Campus Interiors"

# interior -> list of (exterior map, door label) it is entered from
INTERIOR_LINKS = {}


def build(ctx):
    ctx.loc_gate = {}
    ctx.loc_trig = {}
    ctx.world_return = {}
    ctx.entry = {}          # map/legacy key -> (x, y) spawn when arriving from the world map
    wm = ctx.meta("world_campus")
    world = ctx.scene("world", "Campus World Map", "world_campus", FOLDER_WORLD)
    world.script += night_palette(ctx, world)
    W, H = world.width, world.height
    trig_cells = set()
    for loc in wm["locations"]:
        for dx in (0, 1):
            trig_cells.add((loc["x"] + dx, loc["y"]))
    main = main_component(world.collisions, W, H)
    for loc in wm["locations"]:
        # return spot: nearest tile of the main walkable area, outside the trigger
        cands = [c for c in main if c not in trig_cells and (c[0] + 1, c[1]) not in trig_cells]
        rx, ry = min(cands, key=lambda c: abs(c[0] - loc["x"]) + abs(c[1] - (loc["y"] + 2)))
        ctx.world_return[loc["target"]] = (rx, ry)
        t = world.trigger("Go: " + loc["name"], loc["x"], loc["y"], 2, 1)
        ctx.loc_trig[loc["target"]] = (t, loc["name"])

    # exteriors cut from OSM
    import maps_local
    for spec in maps_local.EXTERIORS:
        name = spec["name"]
        m = ctx.meta(name)
        sc = ctx.scene(name, m["title"], name, FOLDER_WORLD)
        sc.script += night_palette(ctx, sc)
        avoid = ext_avoid(m)
        ctx.entry[name] = tuple(open_spot(m["collisions"], m["cols"], m["rows"], m["spawn"][0], m["spawn"][1],
                                          avoid=avoid))
        back = ctx.world_return.get(name, (60, 60))
        for ex in m["exits"]:
            cells = ex["cells"]
            if ex["side"] in "ew":
                cells = [c for c in cells if 0 < c < m["rows"] - 1]
            for run in _runs(cells):
                if ex["side"] in "ns":
                    y = 0 if ex["side"] == "n" else m["rows"] - 1
                    sc.trigger("Exit %s %d" % (ex["side"], run[0]), run[0], y, len(run), 1,
                               script=[gbs.goto(ctx.sid_of("world"), back[0], back[1], "down")])
                else:
                    x = 0 if ex["side"] == "w" else m["cols"] - 1
                    sc.trigger("Exit %s %d" % (ex["side"], run[0]), x, run[0], 1, len(run),
                               script=[gbs.goto(ctx.sid_of("world"), back[0], back[1], "down")])
        for d in m["doors"]:
            if d.get("missing") or not d.get("target"):
                continue
            # the trigger covers the 2-wide doorstep; arriving back from inside
            # puts you one tile further out so you don't walk straight back in
            sx, sy = d["spawn"]
            d = dict(d)
            d["step"] = (sx, sy)
            d["spawn"] = list(open_spot(m["collisions"], m["cols"], m["rows"], sx, sy + 1, avoid=avoid))
            INTERIOR_LINKS.setdefault(d["target"], []).append((name, d))

    # interiors
    for spec in maps_local.INTERIORS:
        name = spec["name"]
        if name == "prologue_bedroom":
            continue
        m = ctx.meta(name)
        sc = ctx.scene(name, m["title"], name, FOLDER_IN)
        sc.script += night_palette(ctx, sc)
        links = INTERIOR_LINKS.get(name, [])
        doors = m["doors"]
        ctx.entry[name] = tuple(doors[0]["spawn"]) if doors else tuple(m["spawn"])
        if name == "underpass_tunnel":
            west = [d for d in doors if d["x"] == 0]
            east = [d for d in doors if d["x"] > 0]
            ext = dict((d["label"], d) for _, d in links)
            for side, group in (("west", west), ("east", east)):
                label = "Underpass (hostel side)" if side == "west" else "Underpass (university side)"
                d_out = ext.get(label)
                for d in group:
                    if d_out:
                        sc.trigger("Exit %s %d" % (side, d["y"]), d["x"], d["y"], 1, 1,
                                   script=[gbs.goto(ctx.sid_of("underpass"), d_out["spawn"][0], d_out["spawn"][1],
                                                    "down")])
            ctx.entry["underpass_tunnel_west"] = tuple(west[1]["spawn"]) if len(west) > 1 else (1, 4)
            ctx.entry["underpass_tunnel_east"] = tuple(east[1]["spawn"]) if len(east) > 1 else (30, 4)
            continue
        ret_var = "Ret_" + name
        if not links:
            continue
        cases = {}
        for i, (ext_name, d) in enumerate(links):
            cases[i] = [gbs.goto(ctx.sid_of(ext_name), d["spawn"][0], d["spawn"][1], "down")]
        for d in doors:
            sc.trigger("Exit %d %d" % (d["x"], d["y"]), d["x"], d["y"], 1, 1,
                       script=[gbs.switch(ret_var, cases)] if len(cases) > 1 else cases[0])

    # exterior doors -> interiors
    for interior, links in INTERIOR_LINKS.items():
        if interior not in ctx.scenes:
            continue
        for i, (ext_name, d) in enumerate(links):
            sc = ctx.scenes[ext_name]
            if interior == "underpass_tunnel":
                side = "west" if "hostel" in d["label"] else "east"
                sx, sy = ctx.entry["underpass_tunnel_" + side]
                script = [gbs.goto(ctx.sid_of(interior), sx, sy, "right" if side == "west" else "left")]
            else:
                sx, sy = ctx.entry[interior]
                script = [gbs.set_var("Ret_" + interior, i), gbs.goto(ctx.sid_of(interior), sx, sy, "up")]
            sc.trigger("Door " + d["label"], d["step"][0], d["step"][1], 2, 1, script=script)

    # the owner's B7 scenes: arrival spot on the B7 front scene
    lf = ctx.legacy["b7_front"]
    ctx.entry["legacy_b7_front"] = open_spot(lf["collisions"], lf["width"], lf["height"], 14, 26)


def main_component(collisions, w, h):
    from story.common import walkable_grid
    from collections import deque
    g = walkable_grid(collisions, w, h)

    def fits(x, y):
        return 0 <= x < w - 1 and 0 <= y < h and g[y][x] and g[y][x + 1]
    best, seen = set(), set()
    for y in range(h):
        for x in range(w):
            if (x, y) in seen or not fits(x, y):
                continue
            comp = {(x, y)}
            q = deque([(x, y)])
            while q:
                cx, cy = q.popleft()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (cx + dx, cy + dy)
                    if n not in comp and fits(*n):
                        comp.add(n)
                        q.append(n)
            seen |= comp
            if len(comp) > len(best):
                best = comp
    return best


def ext_avoid(m):
    """Cells covered by edge exits and doorsteps of an exterior map."""
    out = set()
    for ex in m["exits"]:
        for c in ex["cells"]:
            out.add({"n": (c, 0), "s": (c, m["rows"] - 1), "w": (0, c), "e": (m["cols"] - 1, c)}[ex["side"]])
    for d in m["doors"]:
        if "spawn" in d:
            sx, sy = d["spawn"]
            out |= {(sx, sy), (sx + 1, sy)}
    # keep one tile clear of the edges as well
    for c in range(m["cols"]):
        out |= {(c, 1), (c, m["rows"] - 2)}
    for r in range(m["rows"]):
        out |= {(1, r), (m["cols"] - 2, r)}
    return out


def _runs(cells):
    cells = sorted(cells)
    out = []
    for c in cells:
        if out and c == out[-1][-1] + 1:
            out[-1].append(c)
        else:
            out.append([c])
    return [r for r in out if len(r) >= 2]


SHORT = {"hostel_avenue": "GHS Avenue", "b7_courts": "B7 Courts", "scrub_trail": "Scrub Trail",
         "block1": "Block 1 (B1)", "block2": "Block 2 (B2)", "girls_blocks": "Girls' Blocks",
         "pool": "Ocean Hills Pool", "underpass": "The Underpass", "dome": "The Dome",
         "ab1": "Academic Block 1", "ab2": "AB2 & Amphitheatre", "grand_staircase": "Grand Staircase",
         "ab3": "AB3 & Labs", "workshop": "Workshop", "cricket_ground": "Cricket Ground",
         "nbc": "NBC & BABA"}


def banner(name):
    """Chrono Trigger-style location name on arrival from the campus map."""
    return [gbs.if_var("FromWorld", "==", 1, [
        gbs.set_var("FromWorld", 0),
        gbs.ev("EVENT_OVERLAY_SHOW", {"color": "white", "x": 0, "y": 16}),
        gbs.text_draw(name[:18], 1, 0, "overlay"),
        gbs.wait(1.4),
        gbs.ev("EVENT_OVERLAY_HIDE", {}),
    ])]


# world locations without their own exterior: (exterior, door label to arrive at)
ALIAS = {"quess_mess": ("hostel_avenue", "Quess Mess")}


def enter_events(ctx, target):
    """Default events for walking into a world-map location."""
    if target in ALIAS:
        ext, label = ALIAS[target]
        for links in INTERIOR_LINKS.values():
            for e_name, d in links:
                if e_name == ext and d["label"] == label:
                    return [gbs.goto(ctx.sid_of(ext), d["spawn"][0], d["spawn"][1], "down")]
        target = ext
    if target == "legacy_b7_front":
        x, y = ctx.entry["legacy_b7_front"]
        return [gbs.goto(ctx.sid_of("b7_front"), x, y, "up")]
    x, y = ctx.entry[target]
    return [gbs.goto(ctx.sid_of(target), x, y, "down")]


def finalize(ctx):
    for key, short in SHORT.items():
        if key in ctx.scenes:
            ctx.scenes[key].script += banner(short)
    for target, (trig, name) in ctx.loc_trig.items():
        gate = ctx.loc_gate.get(target)
        default = [gbs.set_var("FromWorld", 1)] + enter_events(ctx, target)
        body = gate(default) if gate else default
        # entrances never hijack travel: stepping on one asks first
        trig.script = [gbs.text(name), gbs.choice("Pick", "Enter", "Keep walking"),
                       gbs.if_var("Pick", "==", 1, body)]
