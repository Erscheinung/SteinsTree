"""Owner-style compact maps and the reusable tile library.

The first map pass was painted from OSM geometry.  This module deliberately
keeps the geography in the story graph while moving the pixels back to the
owner's Emerald-style language: grass texture, warm facades, hedges, planters,
stairs, benches and railings.  The source art is sampled as 8x8 tiles and is
never modified.  ``owner_layouts.json`` is the hand-editable layout source.

Run directly with::

    python3 tools/map/owner.py --library --compare

The normal map command calls :func:`build` for specs marked ``owner_layout``.
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

import gbc

ROOT = gbc.ROOT
SOURCE_DIR = ROOT / "assets" / "backgrounds"
LIBRARY_PNG = ROOT / "art" / "tilesets" / "owner_library.png"
LIBRARY_JSON = ROOT / "art" / "tilesets" / "owner_library.json"
LAYOUTS_JSON = ROOT / "tools" / "map" / "owner_layouts.json"
COMPARE_DIR = ROOT / "art" / "maps" / "preview" / "compare"
_SOURCE_CACHE = {}

SOURCES = [
    "B7-front", "B7-front-left", "B7-front-right", "B7-back", "B7-back-left",
    "B7-back-exit", "B7-back-exit-right", "B7-chiller", "B7-entrance", "B7-10",
    "B7-lounge", "B7-right-exit", "B7", "mess-to-main",
]

COMPACT_MAPS = {
    "hostel_avenue", "b7_courts", "scrub_trail", "block1", "block2",
    "girls_blocks", "pool", "underpass", "dome", "ab1", "ab2",
    "grand_staircase", "ab3", "workshop", "cricket_ground", "nbc",
}

# Interior floors and work areas use the same intact source-art language as
# the exteriors.  Furniture symbols are drawn after these patches, so the
# existing collision and actor coordinates remain unchanged.
INTERIOR_PATCHES = {
    "physics_class": [
        {"source": "B7-10", "src": [12, 16], "dst": [2, 4], "size": [12, 7]},
    ],
    "maths_class": [
        {"source": "B7-10", "src": [12, 16], "dst": [2, 4], "size": [12, 7]},
    ],
    "chem_lab": [
        {"source": "B7-10", "src": [12, 16], "dst": [2, 3], "size": [12, 8]},
    ],
    "workshop_in": [
        {"source": "B7-back", "src": [8, 8], "dst": [1, 3], "size": [16, 8]},
    ],
    "quess_mess_in": [
        {"source": "mess-to-main", "src": [12, 15], "dst": [2, 3], "size": [14, 8]},
    ],
}

# Patterns for the small pieces which are easier to keep coherent when drawn
# by hand.  The larger textures and repeated owner details come from the tile
# library below.  Rows are light -> dark indices in a GB Studio palette slot.
CUSTOM = {
    "h": ("33333333", "32222223", "32111123", "32222223", "31111113", "32222223", "33333333", "11111111"),
    "T": ("00111000", "01111100", "11111110", "11122111", "11222211", "01111110", "00111000", "00011000"),
    "P": ("00111000", "01111110", "11222211", "12222221", "11111111", "33333333", "32222223", "33333333"),
    "D": ("33333333", "31111113", "31222213", "31211213", "31222213", "31111113", "32222223", "33333333"),
    "W": ("33333333", "30000003", "30122103", "30211203", "30122103", "30211203", "30000003", "33333333"),
    "R": ("33333333", "22222222", "11111111", "22222222", "11111111", "22222222", "11111111", "33333333"),
    "S": ("00000000", "11111111", "22222222", "11111111", "22222222", "11111111", "22222222", "33333333"),
    "K": ("00000000", "01111110", "02222220", "33333333", "00111100", "00111100", "00333300", "00333300"),
    "|": ("33333333", "11111111", "11111111", "33333333", "11111111", "11111111", "33333333", "33333333"),
    "~": ("11111111", "12222221", "21111112", "22222222", "11111111", "12222221", "21111112", "22222222"),
    "#": ("33333333", "32222223", "32111123", "32222223", "32111123", "32222223", "33333333", "11111111"),
    "F": ("33333333", "30000003", "31111113", "31122113", "31122113", "31111113", "32222223", "33333333"),
}

SLOT_BY_TOKEN = {
    "g": gbc.SLOT["grass"], "c": gbc.SLOT["grass"], "h": gbc.SLOT["grass"], "T": gbc.SLOT["grass"],
    "P": gbc.SLOT["grass"], ".": gbc.SLOT["path"], "=": gbc.SLOT["path"], "s": gbc.SLOT["stone"],
    ",": gbc.SLOT["stone"], "S": gbc.SLOT["stone"], "|": gbc.SLOT["stone"], "~": gbc.SLOT["water"],
    "f": gbc.SLOT["brick"], "F": gbc.SLOT["brick"], "#": gbc.SLOT["brick"], "D": gbc.SLOT["wood"],
    "K": gbc.SLOT["wood"], "W": gbc.SLOT["roof"], "R": gbc.SLOT["roof"], "^": gbc.SLOT["roof"],
}


def _lum(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def _slot(rgb):
    """Classify a source tile into one of the shared seven background slots."""
    r, g, b = rgb
    # The owner's lawn is a warm yellow-green (216,216,136), rather than the
    # saturated green used by the generated terrain.  Keep that ramp in the
    # grass slot; otherwise its equal red/green channels are mistaken for
    # orange paving and the whole facade crop turns fluorescent.
    if r >= 150 and g >= 150 and b < 165 and abs(r - g) <= 32:
        return "grass"
    if g > r * 1.10 and g > b * 1.04:
        return "grass"
    if b > r * 1.10 and b > g * 1.04:
        return "water" if b > 150 and g > 100 else "roof"
    if r > g * 1.20 and r > b * 1.10:
        return "brick"
    if r > b * 1.16 and g > b * 1.08:
        return "path" if _lum(rgb) > 145 else "wood"
    return "stone"


def _pattern(im, x0, y0):
    pixels = [im.getpixel((x0 + x, y0 + y)) for y in range(8) for x in range(8)]
    ls = [_lum(p) for p in pixels]
    lo, hi = min(ls), max(ls)
    if hi - lo < 10:
        shades = [1] * 64
    else:
        # Quantile thresholds preserve outlines and highlights even when the
        # original tile has many RGB colours.  Flat tiles remain quiet.
        ordered = sorted(ls)
        q1, q2, q3 = (ordered[int(len(ordered) * q)] for q in (0.28, 0.52, 0.76))
        shades = [0 if v >= q3 else 1 if v >= q2 else 2 if v >= q1 else 3 for v in ls]
    return tuple("".join(str(shades[y * 8 + x]) for x in range(8)) for y in range(8))


def build_library():
    """Extract and deduplicate 8x8 owner tiles, preserving provenance."""
    records = []
    seen = {}
    for source in SOURCES:
        path = SOURCE_DIR / (source + ".png")
        im = Image.open(path).convert("RGB")
        for ty in range(im.height // 8):
            for tx in range(im.width // 8):
                pat = _pattern(im, tx * 8, ty * 8)
                rgb = tuple(sum(im.getpixel((tx * 8 + x, ty * 8 + y))[i] for y in range(8) for x in range(8)) // 64 for i in range(3))
                slot = _slot(rgb)
                key = (slot, pat)
                if key in seen:
                    continue
                seen[key] = len(records)
                records.append({"id": len(records), "source": source, "source_xy": [tx, ty],
                                "slot": slot, "pattern": list(pat), "mean_rgb": list(rgb)})
    LIBRARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    LIBRARY_JSON.write_text(json.dumps({"version": 1, "tile_size": 8, "sources": SOURCES,
                                        "tiles": records}, indent=1) + "\n")
    cols = 16
    rows = max(1, math.ceil(len(records) / cols))
    out = Image.new("RGB", (cols * 8, rows * 8))
    for rec in records:
        x, y = (rec["id"] % cols) * 8, (rec["id"] // cols) * 8
        pal = [gbc._hex(c) for c in gbc.BANKS["day"][rec["slot"]]]
        for yy, line in enumerate(rec["pattern"]):
            for xx, val in enumerate(line):
                out.putpixel((x + xx, y + yy), pal[int(val)])
    out.save(LIBRARY_PNG, optimize=True)
    return records


def _library():
    if not LIBRARY_JSON.exists():
        return build_library()
    return json.loads(LIBRARY_JSON.read_text())["tiles"]


def _tiles_by_slot(records):
    by = defaultdict(list)
    for rec in records:
        by[rec["slot"]].append(rec)
    # Prefer tiles with enough contrast to read as texture, but retain the
    # source order so regeneration is stable.
    for slot in by:
        by[slot].sort(key=lambda r: (-len(set("".join(r["pattern"]))), r["id"]))
    return by


def _pick(by, slot, offset=0):
    candidates = by.get(slot) or by["stone"]
    return candidates[offset % len(candidates)]["pattern"]


def _put(cv, x, y, token, by):
    if not (0 <= x < cv.wt and 0 <= y < cv.ht):
        return
    slot = SLOT_BY_TOKEN.get(token, gbc.SLOT["grass"])
    pattern = CUSTOM.get(token)
    if pattern is None:
        role = {"g": "grass", "c": "grass", ".": "path", "=": "path", "s": "stone",
                ",": "stone", "f": "brick", "^": "roof", "W": "roof", "R": "roof", "D": "wood",
                "K": "wood"}.get(token, "grass")
        pattern = _pick(by, role, x + y * 3)
    cv.blit_tile(x, y, slot, pattern, lock=token not in ("g", "c", ".", "=", "s", ","))


def _source_tile(source, tx, ty):
    """Return one original-art tile as an owner-style slot/pattern pair.

    Patches are deliberately reduced per tile because the Game Boy still needs
    four shades and one palette slot per 8x8 tile.  Keeping the source tile's
    position and its neighbouring tiles together is what preserves the owner's
    larger facade, paving and planter shapes.
    """
    im = _SOURCE_CACHE.get(source)
    if im is None:
        im = Image.open(SOURCE_DIR / (source + ".png")).convert("RGB")
        _SOURCE_CACHE[source] = im
    if not (0 <= tx < im.width // 8 and 0 <= ty < im.height // 8):
        return None
    tile = im.crop((tx * 8, ty * 8, tx * 8 + 8, ty * 8 + 8))
    rgb = tuple(sum(tile.getpixel((x, y))[i] for y in range(8) for x in range(8)) // 64 for i in range(3))
    return _slot(rgb), _pattern(tile, 0, 0)


def _blit_source_patch(cv, patch):
    """Blit an intact multi-tile crop from an original owner background.

    Coordinates are tile coordinates: ``src`` and ``dst`` are [x, y], while
    ``size`` is [width, height].  Out-of-bounds source and destination cells
    are clipped, which lets the same facade module fit the 24-, 28- and
    32-tile owner layouts without changing their metadata coordinates.
    """
    source = patch["source"]
    sx, sy = patch.get("src", [0, 0])
    dx, dy = patch.get("dst", [0, 0])
    pw, ph = patch.get("size", [1, 1])
    slot_override = patch.get("slot")
    for oy in range(ph):
        for ox in range(pw):
            tile = _source_tile(source, sx + ox, sy + oy)
            if tile is None:
                continue
            x, y = dx + ox, dy + oy
            if not (0 <= x < cv.wt and 0 <= y < cv.ht):
                continue
            slot, pattern = tile
            if slot_override is not None:
                slot = gbc.SLOT[slot_override]
            cv.blit_tile(x, y, gbc.SLOT[slot] if isinstance(slot, str) else slot,
                         pattern, lock=patch.get("lock", True))


def _facade_patches(width):
    """Return coherent facade/planter modules for a compact exterior.

    The old token-only layout repeated single 8x8 samples.  These modules are
    8x7 or 16x7 crops from the original B7 frontage, so windows, roof bands,
    paving and hedges line up across tile boundaries.  A door is painted after
    these patches and therefore remains at its existing coordinate.
    """
    if width < 24:
        return []
    sources = [
        {"source": "B7-front", "src": [8, 8], "size": [8, 7]},
        {"source": "B7-front-right", "src": [0, 8], "size": [8, 7]},
        {"source": "mess-to-main", "src": [8, 8], "size": [8, 7]},
    ]
    out = []
    for i, x in enumerate(range(2, width - 2, 8)):
        patch = dict(sources[i % len(sources)])
        patch["dst"] = [x, 2]
        out.append(patch)
    return out


def _apply_patches(cv, patches):
    for patch in patches:
        _blit_source_patch(cv, patch)


def _layout(name):
    data = json.loads(LAYOUTS_JSON.read_text())
    if name not in data:
        raise KeyError("owner layout " + name)
    spec = data[name]
    rows = spec["rows"]
    if not rows or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("unequal owner layout rows: " + name)
    return spec


def build(spec):
    records = _library()
    by = _tiles_by_slot(records)
    layout = _layout(spec["name"])
    rows = layout["rows"]
    cv = gbc.Canvas(len(rows[0]), len(rows))
    solid_tokens = set("hTPWFRK|~#f^")
    for y, row in enumerate(rows):
        for x, token in enumerate(row):
            _put(cv, x, y, token, by)
            if token in solid_tokens:
                cv.solid[y][x] = 0x0F
            elif token == "D":
                cv.solid[y][x] = 0
    # Source patches are applied before doors and edge openings so the
    # hand-authored navigation coordinates always win over decorative art.
    # A source_base is an intact, contiguous crop from one original scene.
    # It replaces the old repeated 8x7 facade snippets as the visual ground;
    # the row layout still owns collisions, exits, and navigation metadata.
    patches = list(layout.get("patches", []))
    base = layout.get("source_base")
    base_patches = list(layout.get("base_patches", []))
    if layout.get("facade_patches", True) and not (base or base_patches):
        patches = _facade_patches(cv.wt) + patches
    if base:
        base_patches.insert(0, base)
    if base_patches:
        _apply_patches(cv, base_patches)
    _apply_patches(cv, patches)
    # A compact map has intentional short exits only.  Edge openings are
    # computed by the shared local-map code after this function returns.
    doors = []
    for d in layout.get("doors", []):
        x, y = d["at"]
        if not (0 <= x < cv.wt and 0 <= y < cv.ht):
            raise ValueError("door outside owner layout %s: %s" % (spec["name"], d))
        _put(cv, x, y, "D", by)
        cv.solid[y][x] = 0
        sx, sy = d.get("spawn", [x, min(cv.ht - 1, y + 1)])
        doors.append({"label": d["label"], "target": d.get("target"), "x": x, "y": y,
                      "spawn": [sx, sy]})
    # Keep the walkable border clear where the JSON declares an edge exit.
    for side in layout.get("exits", ["n", "s", "e", "w"]):
        cells = range(cv.wt) if side in "ns" else range(cv.ht)
        for i in cells:
            x, y = ({"n": (i, 0), "s": (i, cv.ht - 1), "w": (0, i), "e": (cv.wt - 1, i)}[side])
            # only clear runs with a path two tiles deep; local.finish will
            # trim the rest and record the exact runs in metadata.
            if 1 < i < (cv.wt if side in "ns" else cv.ht) - 2:
                if side == "n" and rows[min(2, cv.ht - 1)][i] in ".=g": cv.solid[y][x] = 0
                if side == "s" and rows[max(0, cv.ht - 3)][i] in ".=g": cv.solid[y][x] = 0
                if side == "w" and rows[i][min(2, cv.wt - 1)] in ".=g": cv.solid[y][x] = 0
                if side == "e" and rows[i][max(0, cv.wt - 3)] in ".=g": cv.solid[y][x] = 0
    import local  # late import avoids the owner/local module cycle
    meta_spec = dict(spec)
    meta_spec.update(layout)
    meta_spec["name"] = spec["name"]
    meta_spec["title"] = layout.get("title", spec.get("title", spec["name"]))
    meta = local.finish(cv, meta_spec, doors)
    meta["kind"] = "owner_compact"
    meta["style_source"] = "owner_library"
    meta["layout_source"] = "tools/map/owner_layouts.json#" + spec["name"]
    meta["tile_library"] = "art/tilesets/owner_library.json"
    if base_patches or patches:
        meta["source_patches"] = base_patches + patches
    return cv, meta


def build_world(locations):
    """Build the compact stylised campus overview.

    The story still uses the stable world-scene key and location targets, but
    the old 122x115 OSM canvas is replaced by a small hand-readable overview.
    ``locations`` is supplied by ``world.py`` so target names stay in one
    place for the story worker.
    """
    layout = _layout("world_campus")
    cv, meta = build({"name": "world_campus", "title": layout.get("title", "Campus Overview"),
                      "exits": []})
    by_target = {item["target"]: item for item in layout.get("locations", [])}
    world_locations = []
    for name, _anchor, target in locations:
        item = by_target.get(target)
        if item is None:
            raise ValueError("missing compact world location %s" % target)
        world_locations.append({"name": name, "target": target,
                                "x": item["at"][0], "y": item["at"][1]})
    meta["locations"] = world_locations
    meta["labels"] = {}
    meta["kind"] = "owner_overview"
    meta["overview_source"] = "tools/map/owner_layouts.json#world_campus"
    meta["cell_m"] = 1
    meta["origin_m"] = [0, 0]
    return cv, meta


def _render_original(im, scale=2):
    w, h = (im.width // 8) * 8, (im.height // 8) * 8
    im = im.crop((0, 0, w, h)).resize((w * scale, h * scale), Image.NEAREST)
    return im


def _fixed_preview(im):
    """Use the same explicit slot model as runtime maps for comparison."""
    records = _library()
    by = _tiles_by_slot(records)
    cv = gbc.Canvas(im.width // 8, im.height // 8)
    for ty in range(cv.ht):
        for tx in range(cv.wt):
            tile = im.crop((tx * 8, ty * 8, tx * 8 + 8, ty * 8 + 8))
            rgb = tuple(sum(tile.getpixel((x, y))[i] for y in range(8) for x in range(8)) // 64 for i in range(3))
            slot = gbc.SLOT[_slot(rgb)]
            pat = _pattern(tile, 0, 0)
            cv.blit_tile(tx, ty, slot, pat)
            cv.pal[ty][tx] = slot
    return cv.to_preview("day", scale=2)


def _gbc_display(rgb):
    """GB Studio's default 5-bit GBC preview transform."""
    r5, g5, b5 = (max(0, min(31, int(c) // 8)) for c in rgb)
    value = (b5 << 10) + (g5 << 5) + r5
    r, g, b = value & 31, (value >> 5) & 31, (value >> 10) & 31
    return ((r * 13 + g * 2 + b) >> 1,
            (g * 3 + b) << 1,
            (r * 3 + g * 2 + b * 11) >> 1)


def _canonical(rgb):
    """Quantize a source pixel to the raw GBC colour space."""
    return tuple(max(0, min(31, int(c) // 8)) * 8 for c in rgb)


def _auto_palette_preview(im):
    """Reproduce GB Studio's tile-based AutoColor preview.

    The editor takes the first four colours in each source tile, canonicalizes
    them, merges palettes whose union fits four colours, and maps every pixel
    to the nearest entry.  Keeping this audit implementation beside the map
    builder makes the comparison sheets reflect the actual worker algorithm.
    """
    w, h = (im.width // 8) * 8, (im.height // 8) * 8
    tw, th = w // 8, h // 8
    palettes, tile_map = [], []
    for ty in range(th):
        for tx in range(tw):
            colors = []
            for y in range(ty * 8, ty * 8 + 8):
                for x in range(tx * 8, tx * 8 + 8):
                    c = _canonical(im.getpixel((x, y)))
                    if c not in colors:
                        colors.append(c)
                    if len(colors) == 4:
                        break
                if len(colors) == 4:
                    break
            colors.sort(key=_lum, reverse=True)
            while len(colors) < 4:
                colors.append(colors[-1] if colors else (0, 0, 0))
            key = tuple(colors)
            if key not in palettes:
                palettes.append(key)
            tile_map.append(palettes.index(key))

    compressed, remap = [], {}
    for i, palette in enumerate(palettes):
        found = next((j for j, candidate in enumerate(compressed)
                      if len(set(candidate + list(palette))) <= 4), None)
        if found is None:
            found = len(compressed)
            compressed.append(list(palette))
        else:
            compressed[found] = list(dict.fromkeys(compressed[found] + list(palette)))[:4]
        remap[i] = found % 8
    raw_palettes, display_palettes = [], []
    for palette in compressed[:8]:
        palette = list(palette)
        while len(palette) < 4:
            palette.append(palette[-1] if palette else (0, 0, 0))
        raw_palettes.append(palette)
        display_palettes.append([_gbc_display(c) for c in palette])

    out = Image.new("RGB", (w, h))
    for ty in range(th):
        for tx in range(tw):
            pi = remap[tile_map[ty * tw + tx]]
            raw, display = raw_palettes[pi], display_palettes[pi]
            for y in range(ty * 8, ty * 8 + 8):
                for x in range(tx * 8, tx * 8 + 8):
                    c = _canonical(im.getpixel((x, y)))
                    idx = min(range(4), key=lambda j: sum((c[k] - raw[j][k]) ** 2 for k in range(3)))
                    out.putpixel((x, y), display[idx])
    return out.resize((w * 2, h * 2), Image.Resampling.NEAREST)


def _mono_preview(im):
    """Reproduce ColorizedImage.worker's explicit mono candidate."""
    w, h = (im.width // 8) * 8, (im.height // 8) * 8
    dmg = [_gbc_display((0xE8, 0xF8, 0xE0)), _gbc_display((0xB0, 0xF0, 0x88)),
           _gbc_display((0x50, 0x98, 0x78)), _gbc_display((0x20, 0x28, 0x50))]
    out = Image.new("RGB", (w, h))
    for y in range(h):
        for x in range(w):
            g = im.getpixel((x, y))[1]
            index = 3 if g < 65 else 2 if g < 130 else 1 if g < 205 else 0
            out.putpixel((x, y), dmg[index])
    return out.resize((w * 2, h * 2), Image.Resampling.NEAREST)


def compare_sources():
    COMPARE_DIR.mkdir(parents=True, exist_ok=True)
    for name in SOURCES:
        original = Image.open(SOURCE_DIR / (name + ".png")).convert("RGB")
        left = _render_original(original)
        fixed = _fixed_preview(original)
        mono = _mono_preview(original)
        # Keep the comparison honest: the selected candidate is the actual
        # fixed-slot fit used by runtime PNGs and tileColors.  AutoColor's
        # worker has a separate palette solver, so a local approximation must
        # not be presented as if it were the editor's candidate.
        w = max(left.width, fixed.width, mono.width)
        h = max(left.height, fixed.height, mono.height) + 24
        sheet = Image.new("RGB", (w * 3, h), (36, 35, 45))
        draw = ImageDraw.Draw(sheet)
        for i, (label, panel) in enumerate((
            ("original", left), ("fixed slots", fixed), ("mono legacy", mono)
        )):
            sheet.paste(panel, (i * w, 24))
            draw.text((i * w + 4, 6), label, fill=(248, 244, 224))
        sheet.save(COMPARE_DIR / (name + ".png"), optimize=True)


def main(argv):
    if "--library" in argv or not LIBRARY_JSON.exists():
        records = build_library()
        print("owner tile library: %d unique tiles" % len(records))
    if "--compare" in argv:
        compare_sources()
        print("comparison sheets: %s" % COMPARE_DIR)


if __name__ == "__main__":
    main(sys.argv[1:])
