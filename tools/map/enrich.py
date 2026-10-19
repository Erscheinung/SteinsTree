"""Enrich the owner's Emerald-style backgrounds into GBC-legal versions.

    python3 tools/map/enrich.py            # all legacy backgrounds
    python3 tools/map/enrich.py B7-front   # one

The originals in assets/backgrounds/*.png are never modified. Each output
goes to assets/backgrounds/enriched/<name>.png with a sidecar carrying the
per-tile palette map (tileColors), plus a colour preview in
art/maps/preview/enriched_<name>.png.

Steps (full colour first, then quantise):
  1. find the ground colours (the most common colours of the image),
  2. cast soft shadows down-right from everything that is not ground,
  3. add contact shadow under objects and a rim light on their top edges,
  4. for every 8x8 tile pick the best palette of the shared GBC "day" bank and
     snap each pixel to it (so legacy art and the new maps share palettes and
     the night / dream banks recolour both at runtime),
  5. merge rare tiles if the image exceeds the 384-tile GBC budget.
A 257x257 original (B7-10) is cropped to 256x256 in the copy, never resized.
"""

import json
import sys
from collections import Counter

from PIL import Image

import gbc

SRC = gbc.ROOT / "assets" / "backgrounds"
LEGACY = ["B7-10", "B7-back-exit-right", "B7-back-exit", "B7-back-left", "B7-back", "B7-chiller",
          "B7-entrance", "B7-front-left", "B7-front-right", "B7-front", "B7-lounge", "B7-right-exit", "B7",
          "mess-to-main"]


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def _scale(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def enrich_rgb(im):
    w, h = im.size
    px = im.load()
    counts = Counter(px[x, y] for y in range(h) for x in range(w))
    total = w * h
    ground = {c for c, n in counts.most_common(6) if n > total * 0.04 and _lum(c) > 60}
    src = {(x, y): px[x, y] for y in range(h) for x in range(w)}
    is_obj = {k: v not in ground and _lum(v) > 12 for k, v in src.items()}
    out = Image.new("RGB", (w, h))
    op = out.load()
    for y in range(h):
        for x in range(w):
            c = src[(x, y)]
            if not is_obj[(x, y)]:
                f = 1.0
                # cast shadow: an object 2..5 px up-left of this ground pixel
                if any(is_obj.get((x - d, y - d), False) for d in range(2, 6)):
                    f *= 0.80
                elif is_obj.get((x, y - 1), False):
                    f *= 0.88           # contact shadow under objects
                op[x, y] = _scale(c, f)
            else:
                f = 1.0
                if not is_obj.get((x, y - 1), True) or not is_obj.get((x - 1, y), True):
                    f *= 1.10           # rim light on the lit (top/left) edge
                elif not is_obj.get((x + 1, y), True) or not is_obj.get((x, y + 1), True):
                    f *= 0.86           # self-shadow on the far edge
                op[x, y] = _scale(c, f)
    return out


def _d2(a, b):
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return 2 * dr * dr + 4 * dg * dg + 3 * db * db


def _assign(tile, cols, cache, si):
    err = 0
    idx = []
    for c in tile:
        key = (si, c)
        if key not in cache:
            cache[key] = min(range(4), key=lambda i: _d2(c, cols[i]))
        i = cache[key]
        err += _d2(c, cols[i])
        idx.append(i)
    return err, idx


def fit_palettes(rgb, seed_bank="day", rounds=8):
    """7 palettes x 4 colours fitted to the image (k-means over tiles),
    seeded from the shared bank so slot meanings stay roughly the same."""
    w, h = rgb.size
    px = rgb.load()
    tiles = [[px[tx * 8 + x, ty * 8 + y] for y in range(8) for x in range(8)]
             for ty in range(h // 8) for tx in range(w // 8)]
    pal = [[gbc._hex(c) for c in gbc.BANKS[seed_bank][s]] for s in gbc.SLOTS]
    for _ in range(rounds):
        cache = {}
        acc = [[[0, 0, 0, 0] for _ in range(4)] for _ in range(7)]
        for tile in tiles:
            best = min(((_assign(tile, pal[s], cache, s), s) for s in range(7)), key=lambda t: t[0][0])
            (err, idx), s = best
            for c, i in zip(tile, idx):
                a = acc[s][i]
                a[0] += c[0]
                a[1] += c[1]
                a[2] += c[2]
                a[3] += 1
        for s in range(7):
            for i in range(4):
                a = acc[s][i]
                if a[3]:
                    pal[s][i] = (a[0] // a[3], a[1] // a[3], a[2] // a[3])
            pal[s].sort(key=lambda c: -_lum(c))
    return pal


def quantise(rgb, pal):
    """RGB image -> gbc.Canvas: best of the 7 palettes per tile."""
    w, h = rgb.size
    wt, ht = w // 8, h // 8
    cv = gbc.Canvas(wt, ht)
    px = rgb.load()
    cache = {}
    for ty in range(ht):
        for tx in range(wt):
            tile = [px[tx * 8 + x, ty * 8 + y] for y in range(8) for x in range(8)]
            best = None
            for si, cols in enumerate(pal):
                err, idx = _assign(tile, cols, cache, si)
                if best is None or err < best[0]:
                    best = (err, si, idx)
            _, si, idx = best
            cv.pal[ty][tx] = si
            for k, i in enumerate(idx):
                cv.px[(ty * 8 + k // 8) * cv.w + tx * 8 + k % 8] = i
    return cv


def _boost(c, sat=1.12):
    l = _lum(c)
    return tuple(max(0, min(255, int(l + (v - l) * sat))) for v in c)


def write_palettes(name, pal):
    """Day + night palette resources for one enriched background."""
    ids = {"day": [], "night": []}
    for bank, fn in (("day", lambda c: c), ("night", lambda c: gbc._night(c, 0))):
        for s, cols in enumerate(pal):
            pid = "enr-%s-%d%s" % (name.lower(), s, "" if bank == "day" else "-night")
            hexes = [gbc._to_hex(fn(c)) for c in cols]
            res = {"_resourceType": "palette", "id": pid, "name": "%s %s %d" % (name, bank, s),
                   "colors": hexes, "defaultName": "%s %s %d" % (name, bank, s), "defaultColors": hexes}
            (gbc.ROOT / "project" / "palettes" / (pid + ".gbsres")).write_text(json.dumps(res, indent=2))
            ids[bank].append(pid)
    return ids


def run(name):
    src = SRC / (name + ".png")
    im = Image.open(src).convert("RGB")
    w, h = im.size
    crop = None
    if w % 8 or h % 8:
        crop = (w // 8 * 8, h // 8 * 8)
        im = im.crop((0, 0) + crop)
    rich = enrich_rgb(im)
    rich = Image.eval(rich, lambda v: v)
    rich = Image.frombytes("RGB", rich.size, bytes(b for p in rich.getdata() for b in _boost(p)))
    pal = fit_palettes(rich)
    cv = quantise(rich, pal)
    ids = write_palettes(name, pal)
    before = cv.unique_tiles()
    merged = cv.reduce_tiles(380)
    bg_id = gbc.write_background(cv, name, folder="enriched")
    gbc.ROOT.joinpath("art", "maps", "preview").mkdir(parents=True, exist_ok=True)
    _preview(cv, pal).save(gbc.ROOT / "art" / "maps" / "preview" / ("enriched_%s.png" % name))
    return {"name": name, "source": "assets/backgrounds/%s.png" % name, "source_size": [w, h],
            "cropped_to": crop, "background_id": bg_id, "unique_tiles": cv.unique_tiles(),
            "unique_before_merge": before, "tiles_merged": merged, "palette_ids": ids}


def _preview(cv, pal):
    data = []
    for y in range(cv.h):
        prow = cv.pal[y >> 3]
        for x in range(cv.w):
            data.append(tuple(pal[prow[x >> 3]][cv.px[y * cv.w + x]]))
    im = Image.new("RGB", (cv.w, cv.h))
    im.putdata(data)
    return im


def main(names):
    names = names or LEGACY
    prov_path = gbc.ROOT / "art" / "maps" / "enriched_provenance.json"
    prov = json.loads(prov_path.read_text()) if prov_path.exists() else {}
    for n in names:
        rec = run(n)
        prov[n] = rec
        print("%-20s tiles %3d (merged %d)%s" % (n, rec["unique_tiles"], rec["tiles_merged"],
                                                 " cropped" if rec["cropped_to"] else ""))
    prov_path.write_text(json.dumps(prov, indent=1, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1:])
