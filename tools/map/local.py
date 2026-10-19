"""Local area maps cut from the same OSM world as the campus world map.

Each spec in maps_local.py names a centre (lat, lon), a size in tiles and a
scale. Buildings get tall 3/4 facades with doors where the spec asks; open
land comes from the satellite land-cover cache; trees are individual crowns
where sparse and woodland canopy where dense.

Meta written for the game generator: doors (tile + label + target), the
walkable border used for "back to the world map" exits, and a spawn tile.
"""

import json
from collections import deque

import gbc
import landcover
import osm
import painter as pt
from world import STYLE_BY_NAME, smooth

TILE_BUDGET = 380


class Ctx:
    def __init__(self, spec, x0, y0, cell):
        self.spec, self.x0, self.y0, self.cell = spec, x0, y0, cell

    def tile(self, lat, lon):
        x, y = osm.project(lat, lon)
        return int((x - self.x0) / self.cell), int((y - self.y0) / self.cell)

    def tile_m(self, x, y):
        return int((x - self.x0) / self.cell), int((y - self.y0) / self.cell)


def _style(tags):
    name = tags.get("name", "")
    cls = osm.classify(tags)
    style, roof = {"hostel": ("hostel", "flat"), "hostel_g": ("hostel", "flat"),
                   "mess": ("mess", "tile"), "housing": ("plain", "flat")}.get(cls, ("plain", "flat"))
    for prefix, sr in STYLE_BY_NAME:
        if name.startswith(prefix):
            style, roof = sr
    return style, roof


def build(spec, feats=None):
    feats = feats if feats is not None else osm.load_features()
    cols, rows, cell = spec["cols"], spec["rows"], spec.get("cell", 2.0)
    cx, cy = spec["center_m"] if "center_m" in spec else osm.project(*spec["center"])
    x0, y0 = cx - cols * cell / 2, cy - rows * cell / 2
    ctx = Ctx(spec, x0, y0, cell)
    sem, labels = osm.rasterise(x0, y0, cols, rows, cell, feats)
    lc = landcover.load("local", x0, y0, cols, rows, cell)

    # buildings (one blob per OSM building, filtered/overridden by the spec)
    skip = set(spec.get("skip_buildings", []))
    blobs = []
    for f in feats:
        t = f["tags"]
        if "building" not in t or len(f["pts"]) < 4 or t.get("name") in skip:
            continue
        pts = f["pts"]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if max(xs) < x0 or min(xs) > x0 + cols * cell or max(ys) < y0 or min(ys) > y0 + rows * cell:
            continue
        cells = set()
        c0, r0 = ctx.tile_m(min(xs), min(ys))
        c1, r1 = ctx.tile_m(max(xs), max(ys))
        for r in range(max(0, r0), min(rows, r1 + 1)):
            for c in range(max(0, c0), min(cols, c1 + 1)):
                if osm._point_in_poly(x0 + (c + 0.5) * cell, y0 + (r + 0.5) * cell, pts):
                    cells.add((c, r))
        if len(cells) >= 2:
            style, roof = _style(t)
            blobs.append({"name": t.get("name", ""), "style": style, "roof": roof, "cells": cells})
    for name, center, outer, inner, (style, roof) in spec.get("rings", []):
        rx, ry = osm.project(*center)
        box = (rx - outer[0] / 2 - 6, ry - outer[1] / 2 - 6, rx + outer[0] / 2 + 6, ry + outer[1] / 2 + 6)
        blobs = [b for b in blobs if not all(box[0] <= x0 + (c + 0.5) * cell <= box[2] and
                                             box[1] <= y0 + (r + 0.5) * cell <= box[3] for c, r in b["cells"])]
        cells = set()
        for r in range(rows):
            for c in range(cols):
                x, y = x0 + (c + 0.5) * cell, y0 + (r + 0.5) * cell
                if abs(x - rx) <= outer[0] / 2 and abs(y - ry) <= outer[1] / 2 and not (
                        abs(x - rx) <= inner[0] / 2 and abs(y - ry) <= inner[1] / 2):
                    # a 3-tile archway through the south wing into the courtyard
                    if abs(x - rx) <= 1.5 * cell and y > ry:
                        continue
                    cells.add((c, r))
        blobs.append({"name": name, "style": style, "roof": roof, "cells": cells})
    for extra in spec.get("add_buildings", []):
        (c0, r0), (w, hh) = extra["tile"], extra["size"]
        blobs.append({"name": extra.get("name", ""), "style": extra.get("style", "plain"),
                      "roof": extra.get("roof", "flat"),
                      "cells": {(c, r) for r in range(r0, r0 + hh) for c in range(c0, c0 + w)
                                if 0 <= c < cols and 0 <= r < rows}})
    built = set()
    for b in blobs:
        built |= b["cells"]

    terrain = [["grass"] * cols for _ in range(rows)]
    wood = [[False] * cols for _ in range(rows)]
    sparse = []
    for r in range(rows):
        for c in range(cols):
            s = sem[r][c]
            t = {"lawn": "lawn", "plaza": "plaza", "path": "paving", "road": "road", "road_major": "road",
                 "ground": "outfield", "track": "track", "court": "court", "parking": "paving",
                 "water": "water"}.get(s)
            if t is None:
                l = lc[r][c]
                t = {"trees": "grass", "scrub": "scrub", "bare": "dirt", "farm": "farm"}[l]
                if l == "trees" or s == "forest":
                    wood[r][c] = True
            terrain[r][c] = t
    # running tracks are rings: interior cells become outfield
    for r in range(rows):
        for c in range(cols):
            if sem[r][c] == "track" and all(0 <= r + dr < rows and 0 <= c + dc < cols and
                                             sem[r + dr][c + dc] in ("track", "ground")
                                             for dr in (-3, 0, 3) for dc in (-3, 0, 3)):
                terrain[r][c] = "outfield"
    for (c, r), code in spec.get("paint", {}).items():
        terrain[r][c] = code
    for fn in spec.get("terrain_fns", []):
        fn(terrain, ctx)
    wood = smooth(wood, 2)
    for r in range(rows):
        for c in range(cols):
            if terrain[r][c] not in ("grass", "scrub", "dirt", "farm", "lawn") or (c, r) in built:
                wood[r][c] = False
    if not spec.get("woods", True):
        wood = [[False] * cols for _ in range(rows)]
    # keep woods off a 2-tile border so exits stay open, and thin small clumps to sparse trees
    for r in range(rows):
        for c in range(cols):
            if wood[r][c]:
                n = sum(wood[rr][cc] for rr in range(max(0, r - 2), min(rows, r + 3))
                        for cc in range(max(0, c - 2), min(cols, c + 3)))
                if n < 18:
                    wood[r][c] = False
                    sparse.append((c, r))
            if wood[r][c] or any(wood[rr][cc] for rr in range(max(0, r - 1), min(rows, r + 2))
                                 for cc in range(max(0, c - 1), min(cols, c + 2))):
                if terrain[r][c] in ("farm", "dirt", "scrub"):
                    terrain[r][c] = "grass"

    cv = gbc.Canvas(cols, rows)
    pt.paint_terrain(cv, terrain)
    pt.paint_forest_tiles(cv, wood)
    # sparse trees: keep a natural spacing (no two crowns closer than 3 tiles)
    placed = []
    picks = []
    for c, r in sorted(sparse, key=lambda t: pt.h(t[0], t[1], 99)):
        if all(abs(c - pc) + abs(r - pr) >= 4 for pc, pr in placed):
            placed.append((c, r))
            picks.append((c, r))
    for c, r in picks:
        if (c, r) not in built and (c + 1, r) not in built and (c, r + 1) not in built and \
                (c + 1, r + 1) not in built and terrain[r][c] in ("grass", "scrub") and \
                0 < c < cols - 3 and 2 < r < rows - 3:
            pt.tree(cv, c * 8, r * 8, 16, kind=(c + r) % 3)

    # doors: snap each requested door to the nearest front-wall tile
    wall_rows = spec.get("wall_rows", 3)
    door_req = []
    for d in spec.get("doors", []):
        if "latlon" in d:
            tc = ctx.tile(*d["latlon"])
        else:
            tc = tuple(d["tile"])
        door_req.append((d, tc))
    for b in sorted(blobs, key=lambda b: min(c[1] for c in b["cells"])):
        hgt = max(c[1] for c in b["cells"]) - min(c[1] for c in b["cells"]) + 1
        pt.blob_building(cv, b["cells"], style=b["style"], roof=b["roof"], doors=(),
                         wall_rows=min(wall_rows, max(1, hgt // 3)), seed=len(b["cells"]))
    for fn in spec.get("decorate", []):
        fn(cv, ctx, terrain)
    # doors: snap each requested door to the nearest front-wall tile whose
    # doorstep is on the map's main walkable network
    main = largest_component(cv)
    for d, (dc, dr) in door_req:
        cands = []
        for b in blobs:
            if d.get("building") and d["building"] != b["name"]:
                continue
            for (c, r) in b["cells"]:
                if (c, r + 1) in b["cells"] or r + 2 >= rows:
                    continue
                for sx in (c, c - 1):
                    if (sx, r + 1) in main:
                        cands.append((abs(c - dc) + abs(r - dr) * 1.5, c, r, sx))
                        break
        if cands:
            _, c, r, sx = min(cands)
            d["_at"] = (c, r)
            d["_spawn"] = (sx, r + 1)
            cv.blit_tile(c, r, pt.T, ["33333333", "32222223", "32111123", "32111123",
                                       "32111123", "32110123", "32111123", "32111123"], lock=True)
            cv.solid[r][c] = 0

    doors_meta = []
    for d, _ in door_req:
        if "_at" in d:
            c, r = d["_at"]
            doors_meta.append({"label": d["label"], "target": d.get("target"), "x": c, "y": r,
                               "spawn": list(d["_spawn"])})
        else:
            doors_meta.append({"label": d["label"], "target": d.get("target"), "missing": True})
    meta = finish(cv, spec, doors_meta)
    return cv, meta


def finish(cv, spec, doors_meta):
    """Tile budget, walkable border exits, connectivity check."""
    before = cv.unique_tiles()
    merged = cv.reduce_tiles(spec.get("budget", TILE_BUDGET))
    exits = []
    sides = spec.get("exits", ["n", "s", "e", "w"])
    if sides:
        exits = edge_openings(cv, sides)
    spawn = spec.get("spawn")
    if spawn is None:
        main = largest_component(cv)
        cx, cy = cv.wt // 2, cv.ht // 2
        spawn = list(min(main, key=lambda t: abs(t[0] - cx) + abs(t[1] - cy))) if main else _first_open(cv)
    meta = {"name": spec["name"], "title": spec.get("title", spec["name"]), "cols": cv.wt, "rows": cv.ht,
            "doors": doors_meta, "exits": exits, "spawn": list(spawn),
            "unique_before_reduce": before, "tiles_merged": merged, "unique_tiles": cv.unique_tiles(),
            "palette_conflicts": cv.conflicts, "collisions": cv.collisions()}
    meta["unreachable_doors"] = unreachable(cv, spawn, [(d["spawn"][0], d["spawn"][1]) for d in doors_meta
                                                        if "spawn" in d])
    return meta


def edge_openings(cv, sides, max_len=4, depth=3):
    """Exits are short openings where a path really leads off the map.
    Every other border tile becomes solid, so walking alongside the edge
    never bounces the player back to the campus map."""
    W, H = cv.wt, cv.ht
    out = []
    for side in sides:
        n = W if side in "ns" else H

        def cell(i, k):  # k = 0 border, 1.. inward
            return {"n": (i, k), "s": (i, H - 1 - k), "w": (k, i), "e": (W - 1 - k, i)}[side]
        deep = []
        for i in range(n):
            ok = all(not cv.solid[cell(i, k)[1]][cell(i, k)[0]] for k in range(depth))
            deep.append(ok)
        runs, cur = [], []
        for i, ok in enumerate(deep):
            if ok and 0 < i < n - 1:
                cur.append(i)
            elif cur:
                runs.append(cur)
                cur = []
        if cur:
            runs.append(cur)
        keep = set()
        for r in runs:
            if len(r) < 2:
                continue
            mid = len(r) // 2
            seg = r[max(0, mid - max_len // 2): max(0, mid - max_len // 2) + max_len]
            keep |= set(seg)
            out.append({"side": side, "cells": seg})
        for i in range(n):
            if i not in keep:
                x, y = cell(i, 0)
                cv.solid[y][x] = 0x0F
    return out


def largest_component(cv):
    """Largest walkable area that reaches the map edge (so it has exits);
    enclosed pockets like courtyards are never used for arrivals or doors."""
    seen = set()
    best = set()
    for r in range(cv.ht):
        for c in range(cv.wt):
            if (c, r) in seen or not walkable(cv, c, r):
                continue
            comp = {(c, r)}
            q = deque([(c, r)])
            seen.add((c, r))
            while q:
                x, y = q.popleft()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (x + dx, y + dy)
                    if n not in seen and walkable(cv, *n):
                        seen.add(n)
                        comp.add(n)
                        q.append(n)
            edge = any(x <= 0 or y <= 0 or x >= cv.wt - 2 or y >= cv.ht - 1 for x, y in comp)
            if edge and len(comp) > len(best):
                best = comp
    return best


def _first_open(cv):
    for r in range(cv.ht // 2, cv.ht - 2):
        for c in range(cv.wt // 2, cv.wt - 2):
            if not any(cv.solid[r + dy][c + dx] for dx in (0, 1) for dy in (0, 1)):
                return [c, r]
    return [1, 1]


def walkable(cv, c, r):
    """A 16x16 actor occupies tiles (c,r)..(c+1,r) at feet level in GB Studio."""
    return 0 <= c < cv.wt - 1 and 0 <= r < cv.ht and not cv.solid[r][c] and not cv.solid[r][c + 1]


def unreachable(cv, start, targets):
    seen = {tuple(start)}
    q = deque([tuple(start)])
    while q:
        c, r = q.popleft()
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c + dc, r + dr)
            if n not in seen and walkable(cv, *n):
                seen.add(n)
                q.append(n)
    return [list(t) for t in targets if tuple(t) not in seen and (t[0] - 1, t[1]) not in seen]


def save(cv, meta, folder="muj"):
    gbc.write_background(cv, meta["name"], folder=folder)
    out = gbc.ROOT / "art" / "maps" / (meta["name"] + ".json")
    out.write_text(json.dumps(meta, indent=1))
