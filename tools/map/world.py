"""Build the Chrono Trigger-style campus world map from OSM + land cover.

Scale: CELL metres per 8x8 tile in the rotated campus frame (see osm.py).
Output: assets/backgrounds/muj/world_campus.png (+ sidecar) and
art/maps/world_campus.json with collisions, locations and labels.
"""

import json
from collections import deque

import gbc
import landcover
import osm
import painter as pt

CELL = 7.0
TILE_BUDGET = 380  # GBC-only backgrounds may use 384 unique tiles
X0, Y0 = -380.0, -500.0
COLS, ROWS = 122, 115

# Buildings -> (style, roof). Matched on OSM name prefix; default by class.
STYLE_BY_NAME = [
    ("Administrative Block", ("academic", "flat")),
    ("Academic Block", ("academic", "solar")),
    ("Lecture Hall", ("academic", "flat")),
    ("Workshop", ("plain", "tile")),
    ("Old Mess", ("mess", "tile")),
    ("Quess Mess", ("mess", "flat")),
    ("BlueDove", ("mess", "flat")),
    ("NBC", ("mess", "tile")),
    ("Ocean Hills", ("plain", "flat")),
    ("Faculty Apartment", ("plain", "flat")),
    ("TMA Pai", ("academic", "tile")),
    ("Subway", ("plain", "flat")),
]

# Where the player enters each place from the world map (OSM label or metres).
# kind: scene id the game generator links to.
LOCATIONS = [
    # name shown on arrival,           anchor (x m, y m) in the rotated frame, local map
    ("B7 Hostel",                       (-212, -18),  "legacy_b7_front"),
    ("B7 Courts",                       (-215, -98),  "b7_courts"),
    ("Quess Mess",                      (-197, 60),   "quess_mess"),
    ("GHS Hostel Avenue",               (-120, 80),   "hostel_avenue"),
    ("Block 1 (B1)",                    (-52, 60),    "block1"),
    ("Block 2 (B2)",                    (-78, 6),     "block2"),
    ("Girls' Blocks G1-G4",             (-140, 172),  "girls_blocks"),
    ("Ocean Hills Pool",                (-197, 224),  "pool"),
    ("Scrub Trail behind B7",           (-150, -215), "scrub_trail"),
    ("Hostel Gate & Underpass",         (6, 22),      "underpass"),
    ("The Dome (Admin Block)",          (225, 162),   "dome"),
    ("Academic Block 1",                (124, 52),    "ab1"),
    ("Academic Block 2",                (305, 38),    "ab2"),
    ("Old Mess & Grand Staircase",      (212, 24),    "grand_staircase"),
    ("Academic Block 3 & Labs",         (125, -124),  "ab3"),
    ("Workshop",                        (392, -28),   "workshop"),
    ("Cricket Ground",                  (192, -255),  "cricket_ground"),
    ("NBC Food Court",                  (45, -175),   "nbc"),
]


def tile_of(x, y):
    return int((x - X0) / CELL), int((y - Y0) / CELL)


def building_cells(feats):
    """List of (style, roof, cells, name) per OSM building, rasterised.

    The academic zone is mapped as dozens of room-block fragments; those are
    merged into whole buildings (connected component + gap closing)."""
    raw = _raw_buildings(feats)
    rings = []
    for name, center, outer, inner, (style, roof) in RINGS:
        cells = ring_cells(center, outer, inner)
        cx, cy = osm.project(*center)
        box = (cx - outer[0] / 2 - 4, cy - outer[1] / 2 - 4, cx + outer[0] / 2 + 4, cy + outer[1] / 2 + 4)
        raw = [b for b in raw if not all(box[0] <= X0 + (c + 0.5) * CELL <= box[2] and
                                         box[1] <= Y0 + (r + 0.5) * CELL <= box[3] for c, r in b[2])]
        rings.append((style, roof, cells, name))
    campus = [b for b in raw if min(c[0] for c in b[2]) * CELL + X0 > 60]
    hostel = [b for b in raw if b not in campus]
    owner = {}
    for i, b in enumerate(campus):
        for cell in b[2]:
            owner[cell] = i
    seen = set()
    merged = []
    for cell in list(owner):
        if cell in seen:
            continue
        comp = set()
        stack = [cell]
        while stack:
            x, y = stack.pop()
            if (x, y) in seen or (x, y) not in owner:
                continue
            seen.add((x, y))
            comp.add((x, y))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
                stack.append((x + dx, y + dy))
        # close one-tile gaps inside the component's bounding box
        xs = [c[0] for c in comp]
        ys = [c[1] for c in comp]
        for y in range(min(ys), max(ys) + 1):
            for x in range(min(xs), max(xs) + 1):
                if (x, y) in comp:
                    continue
                if ((x - 1, y) in comp and (x + 1, y) in comp) or ((x, y - 1) in comp and (x, y + 1) in comp):
                    comp.add((x, y))
        members = {owner[c] for c in comp if c in owner}
        best = max(members, key=lambda i: (bool(campus[i][3]), len(campus[i][2])))
        style, roof, _, name = campus[best]
        merged.append((style, roof, comp, name))
    return hostel + merged + rings


# Ring buildings rebuilt from published dimensions (centre lat/lon, outer
# W x H m, courtyard W x H m) because OSM maps them as patchy fragments.
RINGS = [
    ("Academic Block 1", (26.8426, 75.5645), (130, 148), (85, 110), ("academic", "flat")),
    ("Academic Block 2", (26.8432, 75.5662), (137, 148), (79, 101), ("academic", "solar")),
]


def ring_cells(center, outer, inner):
    cx, cy = osm.project(*center)
    cells = set()
    for r in range(ROWS):
        for c in range(COLS):
            x, y = X0 + (c + 0.5) * CELL, Y0 + (r + 0.5) * CELL
            if abs(x - cx) <= outer[0] / 2 and abs(y - cy) <= outer[1] / 2 and not (
                    abs(x - cx) <= inner[0] / 2 and abs(y - cy) <= inner[1] / 2):
                cells.add((c, r))
    return cells


def _raw_buildings(feats):
    out = []
    for f in feats:
        t = f["tags"]
        if "building" not in t or len(f["pts"]) < 4 or t.get("name") == "NBC":
            continue
        name = t.get("name", "")
        cls = osm.classify(t)
        style, roof = {"hostel": ("hostel", "flat"), "hostel_g": ("hostel", "flat"),
                       "mess": ("mess", "tile"), "housing": ("plain", "flat")}.get(cls, ("plain", "flat"))
        for prefix, sr in STYLE_BY_NAME:
            if name.startswith(prefix):
                style, roof = sr
        pts = f["pts"]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        c0, r0 = tile_of(min(xs), min(ys))
        c1, r1 = tile_of(max(xs), max(ys))
        cells = set()
        for r in range(max(0, r0 - 1), min(ROWS, r1 + 2)):
            for c in range(max(0, c0 - 1), min(COLS, c1 + 2)):
                cx, cy = X0 + (c + 0.5) * CELL, Y0 + (r + 0.5) * CELL
                if osm._point_in_poly(cx, cy, pts):
                    cells.add((c, r))
        if not cells and c0 < COLS and r0 < ROWS and c1 >= 0 and r1 >= 0:
            # tiny buildings: keep their centre tile
            cells.add(tile_of(sum(xs) / len(xs), sum(ys) / len(ys)))
        cells = {(c, r) for c, r in cells if 0 <= c < COLS and 0 <= r < ROWS}
        if cells:
            out.append((style, roof, cells, name))
    return out


def smooth(mask, rounds=1):
    H, W = len(mask), len(mask[0])
    for _ in range(rounds):
        new = [row[:] for row in mask]
        for y in range(H):
            for x in range(W):
                n = sum(mask[yy][xx] for yy in range(max(0, y - 1), min(H, y + 2))
                        for xx in range(max(0, x - 1), min(W, x + 2)))
                new[y][x] = n >= 5
        mask = new
    return mask


def build(feats=None):
    """Build, then guarantee every location is reachable from B7: any location
    walled off by woods or buildings gets a dirt trail carved to it."""
    feats = feats if feats is not None else osm.load_features()
    cv, meta = _build(feats, set())
    carve = connect(cv, meta)
    if carve:
        cv, meta = _build(feats, carve)
        meta["carved_trail_tiles"] = len(carve)
    place_entrances(cv, meta)
    return cv, meta


def place_entrances(cv, meta, radius=6):
    """Move each location's entrance off the through-routes between the
    other locations, preferring a spot against its building, so walking
    across campus doesn't keep stepping on entrances."""
    from collections import deque
    W, H = cv.wt, cv.ht

    def fits(x, y):
        return 0 <= x < W - 1 and 0 <= y < H and not cv.solid[y][x] and not cv.solid[y][x + 1]

    def bfs_from(start):
        prev = {start: None}
        q = deque([start])
        while q:
            c = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + dx, c[1] + dy)
                if n not in prev and fits(*n):
                    prev[n] = c
                    q.append(n)
        return prev
    locs = meta["locations"]
    traffic = {}
    trees = {l["target"]: bfs_from((l["x"], l["y"])) for l in locs}
    for a in locs:
        prev = trees[a["target"]]
        for b in locs:
            if a is b or (b["x"], b["y"]) not in prev:
                continue
            c = prev[(b["x"], b["y"])]
            while c is not None and prev.get(c) is not None:
                traffic[c] = traffic.get(c, 0) + 1
                c = prev[c]
    taken = set()
    for l in locs:
        ax, ay = l["x"], l["y"]
        reach = trees[l["target"]]
        best = None
        for (x, y), _ in reach.items():
            d = abs(x - ax) + abs(y - ay)
            if d > radius or (x, y) in taken or (x + 1, y) in taken:
                continue
            busy = traffic.get((x, y), 0) + traffic.get((x + 1, y), 0)
            against = cv.solid[y - 1][x] if y > 0 else 0
            score = (busy > 0) * 100 + d - (2 if against else 0)
            if best is None or score < best[0]:
                best = (score, x, y)
        if best:
            l["x"], l["y"] = best[1], best[2]
        taken |= {(l["x"], l["y"]), (l["x"] + 1, l["y"])}


def connect(cv, meta):
    from collections import deque
    import heapq
    W, H = cv.wt, cv.ht
    locs = {l["target"]: (l["x"], l["y"]) for l in meta["locations"]}
    def fits(x, y):
        return 0 <= x < W - 1 and 0 <= y < H and not cv.solid[y][x] and not cv.solid[y][x + 1]
    # origin: the largest connected walkable area of the campus
    seen = set()
    done = set()
    for y0 in range(H):
        for x0 in range(W):
            if (x0, y0) in done or not fits(x0, y0):
                continue
            comp = {(x0, y0)}
            q = deque([(x0, y0)])
            while q:
                x, y = q.popleft()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (x + dx, y + dy)
                    if n not in comp and fits(*n):
                        comp.add(n)
                        q.append(n)
            done |= comp
            if len(comp) > len(seen):
                seen = comp
    carve = set()
    for t, (lx, ly) in locs.items():
        cells = {(lx + dx, ly + dy) for dx in (-1, 0, 1, 2) for dy in (-1, 0, 1, 2)}
        if cells & seen:
            continue
        # cheapest path (open 0, woods/scrub 1, buildings 25) from the reachable area
        dist = {}
        pq = []
        for c in seen:
            dist[c] = 0
            pq.append((0, c, None))
        heapq.heapify(pq)
        prev = {}
        goal = None
        while pq:
            d, c, p = heapq.heappop(pq)
            if dist.get(c, 1 << 30) < d:
                continue
            if c in cells:
                goal = c
                break
            x, y = c
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if not (0 <= n[0] < W - 1 and 0 <= n[1] < H):
                    continue
                cost = 0 if fits(*n) else (25 if cv.locked[n[1]][n[0]] else 1)
                if d + cost < dist.get(n, 1 << 30):
                    dist[n] = d + cost
                    prev[n] = c
                    heapq.heappush(pq, (d + cost, n, c))
        c = goal
        while c is not None and c not in seen:
            carve.add(c)
            carve.add((c[0] + 1, c[1]))
            c = prev.get(c)
    return carve


def _build(feats, force_open):
    sem, labels = osm.rasterise(X0, Y0, COLS, ROWS, CELL, feats)
    lc = landcover.load("world", X0, Y0, COLS, ROWS, CELL)
    buildings = [(st, rf, cells - force_open, nm) for st, rf, cells, nm in building_cells(feats)]
    buildings = [b for b in buildings if b[2]]
    built = set()
    for _, _, cells, _ in buildings:
        built |= cells

    terrain = [["grass"] * COLS for _ in range(ROWS)]
    wood = [[False] * COLS for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            s = sem[r][c]
            l = lc[r][c]
            t = {"lawn": "lawn", "plaza": "plaza", "road": "road",
                 "road_major": "road", "ground": "outfield", "track": "track",
                 "court": "court", "parking": "paving", "water": "water"}.get(s)
            if t is None:
                t = {"trees": "grass", "scrub": "scrub", "bare": "dirt", "farm": "farm"}[l]
                if l == "trees" or s == "forest":
                    wood[r][c] = True
            terrain[r][c] = t
    # forest polygons from OSM are dense woods; satellite trees fill the rest
    wood = smooth(wood, 2)
    for (c, r) in force_open:
        if 0 <= c < COLS and 0 <= r < ROWS:
            wood[r][c] = False
            if terrain[r][c] in ("grass", "scrub", "farm", "lawn", "water", "outfield", "court", "track"):
                terrain[r][c] = "dirt"
    for r in range(ROWS):
        for c in range(COLS):
            if terrain[r][c] in ("road", "paving", "plaza", "water", "court", "track", "outfield") or (c, r) in built:
                wood[r][c] = False
    # a clean grass apron around woods so crowns sit on grass, not farmland
    for r in range(ROWS):
        for c in range(COLS):
            if wood[r][c] or any(wood[rr][cc] for rr in range(max(0, r - 1), min(ROWS, r + 2))
                                 for cc in range(max(0, c - 1), min(COLS, c + 2))):
                if terrain[r][c] in ("farm", "dirt", "scrub"):
                    terrain[r][c] = "grass"
    # running tracks are rings: interior cells become outfield
    for r in range(1, ROWS - 1):
        for c in range(1, COLS - 1):
            if sem[r][c] == "track" and all(sem[r + dr][c + dc] in ("track", "ground")
                                             for dr in (-2, 0, 2) for dc in (-2, 0, 2)
                                             if 0 <= r + dr < ROWS and 0 <= c + dc < COLS):
                terrain[r][c] = "outfield"
    # NBC is mapped as one huge building but is really open ground with stalls
    nbc = [f for f in feats if f["tags"].get("name") == "NBC"]
    for f in nbc:
        xs = [p[0] for p in f["pts"]]
        ys = [p[1] for p in f["pts"]]
        c0, r0 = tile_of(min(xs), min(ys))
        c1, r1 = tile_of(max(xs), max(ys))
        for r in range(max(0, r0), min(ROWS, r1 + 1)):
            for c in range(max(0, c0), min(COLS, c1 + 1)):
                if osm._point_in_poly(X0 + (c + 0.5) * CELL, Y0 + (r + 0.5) * CELL, f["pts"]):
                    terrain[r][c] = "dirt"
                    wood[r][c] = False
    # cricket ground: pitch strip in the middle of the outfield
    cg = labels.get("Cricket Ground")
    if cg:
        cc, rr = int(cg[0]), int(cg[1])
        for r in range(rr - 2, rr + 2):
            terrain[r][cc] = "pitch"
    # hostel avenue: OSM footways become one paved avenue
    cv = gbc.Canvas(COLS, ROWS)
    pt.paint_terrain(cv, terrain)
    pt.paint_forest_tiles(cv, wood)

    # trees lining the hostel avenue ("GHS Hostel Main Road")
    av0, av1 = osm.project(26.8407, 75.5614), osm.project(26.8413, 75.5635)
    ax0, ay = tile_of(av0[0], av0[1])
    ax1, _ = tile_of(av1[0], av1[1])
    for c in range(ax0, ax1, 2):
        for rr in (ay - 2, ay + 2):
            if 0 <= rr < ROWS and terrain[rr][c] not in ("road", "water", "dirt") and (c, rr) not in built \
                    and (c, rr - 1) not in built and (c + 1, rr) not in built:
                pt.tree(cv, c * 8, rr * 8 - 8, 12, kind=c % 3, solid=True)

    for i, (style, roof, cells, name) in enumerate(sorted(buildings, key=lambda b: min(c[1] for c in b[2]))):
        height = max(c[1] for c in cells) - min(c[1] for c in cells) + 1
        pt.blob_building(cv, cells, style=style, roof=roof, wall_rows=1 if height < 5 else 2, seed=i)

    # the Dome over the Administrative Block
    ab = labels.get("Administrative Block")
    if ab:
        dx, dy = osm.project(26.84173, 75.56584)
        dc, dr = tile_of(dx, dy)
        pt.dome(cv, dc * 8 + 4, dr * 8 - 4, 14)
    # NBC / BABA food stalls: small sheds on the open ground
    for lat, lon in ((26.8430, 75.5631), (26.8436, 75.5630), (26.8442, 75.5629)):
        c, r = tile_of(*osm.project(lat, lon))
        pt.blob_building(cv, {(c, r), (c + 1, r), (c, r + 1), (c + 1, r + 1)}, style="mess", roof="tile")
    # underpass stairs on both sides of the public road
    for lat, lon in ((26.84179, 75.56331), (26.84200, 75.56370)):
        c, r = tile_of(*osm.project(lat, lon))
        pt.stairs(cv, c, r, 1, 2)
    # dashed centre line down the public road
    for r in range(ROWS):
        for c in range(COLS - 1):
            if terrain[r][c] == "road" and terrain[r][c + 1] == "road" and \
                    sem[r][c] == "road_major" and sem[r][c + 1] == "road_major" and r % 2 == 0:
                for y in range(r * 8 + 1, r * 8 + 6):
                    cv.set(c * 8 + 7, y, 0)
                    cv.set(c * 8 + 8, y, 0)
                break
    # solar panel field north-west of the hostels (26.8459, 75.5602)
    sx, sy = osm.project(26.8459, 75.5602)
    c0, r0 = tile_of(sx - 60, sy - 35)
    c1, r1 = tile_of(sx + 60, sy + 35)
    pt.solar_field(cv, max(0, c0), max(0, r0), min(COLS, c1), min(ROWS, r1))

    # locations: entrance tile on the nearest walkable cell to the anchor
    locs = []
    for name, (mx, my), target in LOCATIONS:
        c, r = tile_of(mx, my)
        c, r = nearest_walkable(cv, c, r)
        locs.append({"name": name, "target": target, "x": c, "y": r})

    meta = {
        "name": "world_campus", "cols": COLS, "rows": ROWS, "cell_m": CELL, "origin_m": [X0, Y0],
        "rotation_deg": osm.ROTATION_DEG, "locations": locs,
        "labels": {k: [round(v[0], 1), round(v[1], 1)] for k, v in labels.items()},
        "collisions": cv.collisions(),
        "unique_tiles": cv.unique_tiles(), "palette_conflicts": cv.conflicts,
    }
    return cv, meta


def nearest_walkable(cv, c, r):
    seen = {(c, r)}
    q = deque([(c, r)])
    while q:
        x, y = q.popleft()
        if 0 <= x < cv.wt - 1 and 0 <= y < cv.ht - 1 and not cv.solid[y][x] and not cv.solid[y][x + 1] \
                and not cv.solid[y + 1][x] and not cv.solid[y + 1][x + 1]:
            return x, y
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n not in seen and 0 <= n[0] < cv.wt and 0 <= n[1] < cv.ht:
                seen.add(n)
                q.append(n)
    return c, r


if __name__ == "__main__":
    cv, meta = build()
    meta["unique_before_reduce"] = cv.unique_tiles()
    meta["tiles_merged"] = cv.reduce_tiles(TILE_BUDGET)
    meta["unique_tiles"] = cv.unique_tiles()
    gbc.write_background(cv, "world_campus")
    out = gbc.ROOT / "art" / "maps" / "world_campus.json"
    out.write_text(json.dumps(meta, indent=1))
    print("unique tiles", meta["unique_before_reduce"], "->", meta["unique_tiles"],
          "conflicts", meta["palette_conflicts"])
