"""Classify open land (trees / scrub / bare earth / farm) from satellite tiles.

The imagery itself is not stored in the repo. Run once with a folder of
z17/z18 Web-Mercator JPEG tiles named t_<z>_<x>_<y>.jpg; the result is cached
as a small derived grid in art/maps/source/landcover_<name>.json, which the
map builders use. Without imagery or cache every open cell falls back to
"scrub".

    python3 tools/map/landcover.py <tile_dir>
"""

import json
import math
import sys
from pathlib import Path

from PIL import Image

import osm

CACHE_DIR = osm.ROOT / "art" / "maps" / "source"


def _tile_xy(lat, lon, z):
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n
    return x, y


class Imagery:
    def __init__(self, folder):
        self.tiles = {}
        for p in Path(folder).glob("t_*_*_*.jpg"):
            _, z, x, y = p.stem.split("_")
            self.tiles[(int(z), int(x), int(y))] = p
        self.cache = {}

    def sample(self, lat, lon, radius=2):
        for z in (18, 17):
            fx, fy = _tile_xy(lat, lon, z)
            key = (z, int(fx), int(fy))
            if key not in self.tiles:
                continue
            if key not in self.cache:
                self.cache[key] = Image.open(self.tiles[key]).convert("RGB")
            im = self.cache[key]
            px, py = int((fx % 1) * 256), int((fy % 1) * 256)
            acc = [0, 0, 0]
            n = 0
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    qx, qy = min(255, max(0, px + dx)), min(255, max(0, py + dy))
                    r, g, b = im.getpixel((qx, qy))
                    acc[0] += r
                    acc[1] += g
                    acc[2] += b
                    n += 1
            return tuple(v / n for v in acc)
        return None


def classify_rgb(rgb):
    if rgb is None:
        return "scrub"
    r, g, b = rgb
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    if g > r + 2 and g > b + 8 and lum < 118:
        return "trees"
    if g >= r - 8 and g > b + 4 and lum < 150:
        return "scrub"
    if lum > 165 or r - b < 40:
        return "bare"
    return "farm"


def build(name, x0, y0, cols, rows, cell, folder):
    img = Imagery(folder)
    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            lat, lon = osm.unproject(x0 + (c + 0.5) * cell, y0 + (r + 0.5) * cell)
            row.append(classify_rgb(img.sample(lat, lon, radius=max(1, int(cell / 2.2)))))
        grid.append("".join({"trees": "T", "scrub": "s", "bare": "b", "farm": "f"}[v] for v in row))
    out = {"name": name, "x0": x0, "y0": y0, "cols": cols, "rows": rows, "cell_m": cell,
           "legend": {"T": "trees", "s": "scrub", "b": "bare", "f": "farm"},
           "note": "Derived from Esri World Imagery colour samples; imagery not redistributed.",
           "grid": grid}
    (CACHE_DIR / ("landcover_%s.json" % name)).write_text(json.dumps(out, indent=0))
    return out


def load(name, x0, y0, cols, rows, cell):
    """Return rows x cols of trees/scrub/bare/farm, resampled from the cache."""
    path = CACHE_DIR / ("landcover_%s.json" % name)
    if not path.exists():
        path = CACHE_DIR / "landcover_campus.json"
    if not path.exists():
        return [["scrub"] * cols for _ in range(rows)]
    d = json.loads(path.read_text())
    leg = d["legend"]
    out = []
    for r in range(rows):
        row = []
        for c in range(cols):
            x = x0 + (c + 0.5) * cell
            y = y0 + (r + 0.5) * cell
            cc = int((x - d["x0"]) / d["cell_m"])
            rr = int((y - d["y0"]) / d["cell_m"])
            if 0 <= rr < d["rows"] and 0 <= cc < d["cols"]:
                row.append(leg[d["grid"][rr][cc]])
            else:
                row.append("farm")
        out.append(row)
    return out


if __name__ == "__main__":
    # Whole campus at 3 m cells; every map resamples from this one cache.
    build("campus", -420.0, -520.0, 310, 280, 3.0, sys.argv[1])
    print("wrote", CACHE_DIR / "landcover_campus.json")
