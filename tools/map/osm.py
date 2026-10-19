"""OpenStreetMap campus geometry -> rotated metric frame -> semantic rasters.

MUJ's hostel and university grids are both aligned to the public road that
runs between them (bearing about 17 degrees west of north). Rotating every
coordinate by ROTATION_DEG makes that road vertical and the hostel avenue
horizontal, so the campus can be drawn on an axis-aligned Game Boy tile grid
without staircase roads. North on the in-game map is therefore tilted; the
world map draws a compass that shows it.

Data: art/maps/source/muj_osm.json (c) OpenStreetMap contributors, ODbL.
"""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OSM_PATH = ROOT / "art" / "maps" / "source" / "muj_osm.json"

# Projection origin: the underpass under the public road (hostel <-> uni).
ORIGIN = (26.8420, 75.5634)
M_PER_DEG_LAT = 111_320.0
M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(ORIGIN[0]))
# Measured from the road polyline 26.8387,75.5652 -> 26.8478,75.5620.
ROTATION_DEG = -17.4


def project(lat, lon):
    """Return (x east, y south) metres in the rotated campus frame."""
    x = (lon - ORIGIN[1]) * M_PER_DEG_LON
    y = -(lat - ORIGIN[0]) * M_PER_DEG_LAT
    a = math.radians(ROTATION_DEG)
    # rotate so the road (bearing ROTATION_DEG) points straight up
    rx = x * math.cos(a) + y * math.sin(a)
    ry = -x * math.sin(a) + y * math.cos(a)
    return rx, ry


def load_features():
    data = json.loads(OSM_PATH.read_text())
    feats = []
    for f in data["features"]:
        pts = [project(a, b) for a, b in f["pts"]]
        feats.append({"id": f["id"], "tags": f["tags"], "pts": pts})
    return feats


def classify(tags):
    """Map OSM tags to a semantic class used by the rasteriser (or None)."""
    name = tags.get("name", "")
    if tags.get("leisure") == "swimming_pool" or tags.get("natural") == "water":
        return "water"
    if tags.get("landuse") == "groundwater_refill":
        return "water"
    if "building" in tags:
        low = name.lower()
        if "mess" in low or "food" in low or tags.get("amenity") in ("food_court", "fast_food"):
            return "mess"
        if low.startswith("b") and low[1:].strip().isdigit():
            return "hostel"
        if low.startswith("g") and any(c.isdigit() for c in low):
            return "hostel_g"
        if tags.get("building") in ("apartments", "residential"):
            return "housing"
        return "building"
    if tags.get("leisure") == "track":
        return "track"
    if tags.get("leisure") == "pitch":
        sport = tags.get("sport", "")
        return "ground" if sport in ("cricket", "soccer", "football") else "court"
    if tags.get("landuse") == "forest" or tags.get("natural") == "wood":
        return "forest"
    if tags.get("landuse") in ("grass", "flowerbed") or tags.get("leisure") in ("park", "garden"):
        return "lawn"
    if tags.get("amenity") in ("parking", "motorcycle_parking"):
        return "parking"
    hw = tags.get("highway")
    if hw in ("tertiary", "secondary", "primary", "trunk"):
        return "road_major"
    if hw in ("residential", "service", "unclassified"):
        return "road"
    if hw in ("pedestrian",):
        return "plaza"
    if hw in ("footway", "path", "steps", "track"):
        return "path"
    return None


def _point_in_poly(x, y, pts):
    inside = False
    n = len(pts)
    j = n - 1
    for i in range(n):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def _dist_seg(px, py, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy + 1e-12)
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


# Paint order: later entries overwrite earlier ones.
AREA_ORDER = ["lawn", "forest", "parking", "plaza", "ground", "track", "court",
              "water", "housing", "building", "mess", "hostel", "hostel_g"]
LINE_WIDTH = {"road_major": 13.0, "road": 6.0, "path": 2.5, "plaza": 5.0}


def rasterise(x0, y0, cols, rows, cell_m, feats=None):
    """Semantic grid of `cols` x `rows` cells of `cell_m` metres from (x0,y0).

    Returns (grid, labels) where grid[r][c] is a class name or "open" and
    labels maps feature names to (col,row) of their centroid inside the grid.
    """
    feats = feats if feats is not None else load_features()
    grid = [["open"] * cols for _ in range(rows)]
    labels = {}
    closed = []
    lines = []
    for f in feats:
        cls = classify(f["tags"])
        pts = f["pts"]
        if cls is None:
            continue
        is_area = len(pts) > 3 and pts[0] == pts[-1] or (cls in AREA_ORDER and len(pts) > 3)
        if cls in AREA_ORDER and is_area:
            closed.append((AREA_ORDER.index(cls), cls, f))
        elif cls in LINE_WIDTH and len(pts) > 1:
            lines.append((cls, f))
    closed.sort(key=lambda t: t[0])
    centers = [(x0 + (c + 0.5) * cell_m, y0 + (r + 0.5) * cell_m)
               for r in range(rows) for c in range(cols)]
    for _, cls, f in closed:
        pts = f["pts"]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        c0 = max(0, int((min(xs) - x0) / cell_m) - 1)
        c1 = min(cols - 1, int((max(xs) - x0) / cell_m) + 1)
        r0 = max(0, int((min(ys) - y0) / cell_m) - 1)
        r1 = min(rows - 1, int((max(ys) - y0) / cell_m) + 1)
        hit = []
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                cx, cy = centers[r * cols + c]
                if _point_in_poly(cx, cy, pts):
                    grid[r][c] = cls
                    hit.append((c, r))
        name = f["tags"].get("name")
        if name and hit:
            labels[name] = (sum(h[0] for h in hit) / len(hit), sum(h[1] for h in hit) / len(hit))
    for cls, f in lines:
        pts = f["pts"]
        w = LINE_WIDTH[cls] / 2.0
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        c0 = max(0, int((min(xs) - w - x0) / cell_m))
        c1 = min(cols - 1, int((max(xs) + w - x0) / cell_m))
        r0 = max(0, int((min(ys) - w - y0) / cell_m))
        r1 = min(rows - 1, int((max(ys) + w - y0) / cell_m))
        reach = max(w, cell_m * 0.5)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                cur = grid[r][c]
                if cur in ("building", "mess", "hostel", "hostel_g", "housing", "water"):
                    continue
                cx, cy = centers[r * cols + c]
                if any(_dist_seg(cx, cy, pts[i], pts[i + 1]) <= reach for i in range(len(pts) - 1)):
                    if cls == "path" and cur in ("road", "road_major"):
                        continue
                    grid[r][c] = cls
    for f in feats:
        if len(f["pts"]) == 1 and "name" in f["tags"]:
            x, y = f["pts"][0]
            c, r = (x - x0) / cell_m, (y - y0) / cell_m
            if 0 <= c < cols and 0 <= r < rows:
                labels.setdefault(f["tags"]["name"], (c, r))
    return grid, labels


def bounds(feats=None):
    feats = feats if feats is not None else load_features()
    xs = [p[0] for f in feats for p in f["pts"]]
    ys = [p[1] for f in feats for p in f["pts"]]
    return min(xs), min(ys), max(xs), max(ys)


def unproject(rx, ry):
    """Inverse of project(): rotated metres -> (lat, lon)."""
    a = math.radians(ROTATION_DEG)
    x = rx * math.cos(a) - ry * math.sin(a)
    y = rx * math.sin(a) + ry * math.cos(a)
    return ORIGIN[0] - y / M_PER_DEG_LAT, ORIGIN[1] + x / M_PER_DEG_LON
