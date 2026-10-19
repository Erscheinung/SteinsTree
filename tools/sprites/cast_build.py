"""Build the Dernier cast sprites from cast_art.py.

    python3 tools/sprites/cast_build.py [--force]

Outputs
  assets/sprites/cast_<name>.png (+ .gbsres)  runtime strips, canonical colours
  art/sprites/cast/preview/*.png               GBC-coloured previews + sheet
  project/palettes/muj-spr-*.gbsres            one GBC sprite palette per role

The sidecar replicates GB Studio's "classic" sprite detection (the editor runs
it on import; the CLI compiler does not), and gives every tile the palette
slot of its character (see SLOTS). Hand-edited PNGs are never overwritten
unless --force is passed (tracked in art/sprites/cast/.generated.json).
"""

import json
import sys
import uuid
import zlib
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cast_art as A  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
NS = uuid.UUID("5b0c1a3e-7d64-4a8e-9a43-6d7565726e69")
KEY = {".": (0x65, 0xFF, 0x00), "o": (0xE0, 0xF8, 0xCF), "+": (0x86, 0xC0, 0x6C), "#": (0x07, 0x18, 0x21)}
PREVIEW_BG = (0x59, 0x65, 0x79)

# name -> (sprite palette slot 0..7, palette key)
SLOTS = {
    "player": (0, "player"), "kid": (0, "player"), "plane": (0, "player"),
    "mayank": (1, "mayank"), "sparklet": (1, "sparklet"),
    "divyansh": (2, "divyansh"), "mama": (2, "mama"),
    "kanishk": (3, "kanishk"), "muskaan": (3, "muskaan"),
    "parag": (4, "parag"),
    "anshuman": (5, "anshuman"), "orb": (5, "gold"), "stormcloud": (5, "storm"), "flask": (5, "gold"),
    "marker": (5, "gold"), "handheld": (5, "gold"),
    "garvita": (6, "garvita"), "pea": (6, "pea"), "gnawbit": (6, "gnawbit"),
    "ghoul": (7, "zombie"), "scholar": (7, "zombie"), "prof_m": (7, "prof"), "prof_f": (7, "prof"),
    "instructor": (7, "prof"), "student": (7, "student"),
}

# light, middle, (unused on sprites), dark — GB Studio shows colors 0, 1, 3
PALETTES = {
    "player":   ["F8D0A8", "5878D0", "384890", "202038"],
    "mayank":   ["F8E4CC", "3C8CA8", "2C5870", "282030"],
    "divyansh": ["F0C890", "E8A820", "A07010", "302018"],
    "kanishk":  ["F8D0A8", "48A060", "2C6838", "182820"],
    "parag":    ["F0C8A0", "C84848", "883030", "281818"],
    "anshuman": ["E0C0A0", "4C5C70", "303848", "101018"],
    "garvita":  ["F8D8B8", "D85890", "983060", "301828"],
    "prof":     ["F0C8A0", "987048", "604028", "282018"],
    "zombie":   ["C8E0A0", "6E9858", "485830", "202818"],
    "student":  ["F0C8A0", "6890B0", "405870", "202030"],
    "mama":     ["F0C8A0", "E05878", "A03050", "281820"],
    "muskaan":  ["F8D8C0", "7890E0", "4858A8", "202040"],
    "sparklet": ["F8F0B0", "F09838", "A05818", "382010"],
    "gnawbit":  ["F0E8F0", "9870C0", "604080", "302040"],
    "pea":      ["E0F8A0", "60B830", "387018", "184018"],
    "gold":     ["F8F8F0", "F0C060", "B07830", "604020"],
    "storm":    ["F0F0F8", "8890A8", "585870", "202030"],
}

GEN = ROOT / "art" / "sprites" / "cast" / ".generated.json"


def sid(*parts):
    return str(uuid.uuid5(NS, "/".join(parts)))


def palette_id(key):
    return "muj-spr-" + key


def write_png(path, frames):
    im = Image.new("RGB", (16 * len(frames), 16))
    px = im.load()
    for i, f in enumerate(frames):
        assert len(f) == 16 and all(len(r) == 16 for r in f), (path, i)
        for y, row in enumerate(f):
            for x, ch in enumerate(row):
                px[i * 16 + x, y] = KEY[ch]
    im = im.quantize(colors=4, method=Image.Quantize.FASTOCTREE) if False else im
    im.save(path, optimize=True)


def preview(frames, pal, scale=6):
    cols = {".": PREVIEW_BG, "o": _h(pal[0]), "+": _h(pal[1]), "#": _h(pal[3])}
    im = Image.new("RGB", (16 * len(frames) + len(frames) - 1, 16), (30, 30, 40))
    px = im.load()
    for i, f in enumerate(frames):
        for y, row in enumerate(f):
            for x, ch in enumerate(row):
                px[i * 17 + x, y] = cols[ch]
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


def _h(c):
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def classic_sidecar(name, filename, width, slot, anim_type=None):
    """Replicates GB Studio's detectClassic() with stable ids."""
    n = width // 16

    def tile(i, k, x, slice_x):
        return {"id": sid("sprite", name, "tile", str(i), str(k)), "x": x, "y": 0, "sliceX": slice_x,
                "sliceY": 0, "flipX": False, "flipY": False, "palette": 0, "paletteIndex": slot,
                "objPalette": "OBP0", "priority": False}

    def frame(i, src):
        return {"id": sid("sprite", name, "frame", str(i)),
                "tiles": [tile(i, 0, 0, src * 16), tile(i, 1, 8, src * 16 + 8)]}

    def blank(i):
        return {"id": sid("sprite", name, "blank", str(i)), "tiles": []}

    anims = [[] for _ in range(8)]
    if n == 6 and anim_type != "fixed":
        atype, flip = "multi_movement", True
        anims[0] = [frame(6, 4)]
        anims[2] = [frame(7, 2)]
        anims[3] = [frame(8, 0)]
        anims[4] = [frame(5, 5), frame(4, 4)]
        anims[6] = [frame(3, 3), frame(2, 2)]
        anims[7] = [frame(1, 1), frame(0, 0)]
    elif n == 3 and anim_type != "fixed":
        atype, flip = "multi", True
        anims[0] = [frame(2, 2)]
        anims[2] = [frame(1, 1)]
        anims[3] = [frame(0, 0)]
    else:
        atype, flip = "fixed", False
        anims[0] = [frame(i, i) for i in range(n)]
    animations = []
    for ai, frames in enumerate(anims):
        animations.append({"id": sid("sprite", name, "anim", str(ai)), "frames": frames or [blank(ai)]})
    return {
        "_resourceType": "sprite",
        "id": sid("sprite", name),
        "name": name,
        "symbol": "sprite_" + "".join(c if c.isalnum() else "_" for c in name.lower()),
        "states": [{"id": sid("sprite", name, "state"), "name": "", "animationType": atype,
                    "flipLeft": flip, "animations": animations}],
        "numTiles": 2 * n,
        "canvasOriginX": 0, "canvasOriginY": 0, "canvasWidth": 16, "canvasHeight": 16,
        "boundsX": 0, "boundsY": 0, "boundsWidth": 16, "boundsHeight": 8,
        "animSpeed": 15,
        "filename": filename,
        "width": width, "height": 16,
        "checksum": "",
    }


def write_palettes():
    out = ROOT / "project" / "palettes"
    for key, cols in PALETTES.items():
        res = {"_resourceType": "palette", "id": palette_id(key), "name": "Sprite: " + key.title(),
               "colors": cols, "defaultName": "Sprite: " + key.title(), "defaultColors": cols}
        (out / (palette_id(key) + ".gbsres")).write_text(json.dumps(res, indent=2))


def _checksum(p):
    return "%08x" % (zlib.crc32(p.read_bytes()) & 0xFFFFFFFF)


def build(force=False):
    rec = json.loads(GEN.read_text()) if GEN.exists() else {}
    pdir = ROOT / "art" / "sprites" / "cast" / "preview"
    pdir.mkdir(parents=True, exist_ok=True)
    sheets = []
    jobs = []
    for name in A.WALKERS:
        f = A.walk_frames(name)
        jobs.append((name, [f[k] for k in ("down_a", "down_b", "up_a", "up_b", "right_a", "right_b")], None))
    for name, frames in A.OBJECTS.items():
        jobs.append((name, frames, "fixed"))
    for name, frames, atype in jobs:
        fname = "cast_%s.png" % name
        png = ROOT / "assets" / "sprites" / fname
        if png.exists() and fname in rec and rec[fname] != _checksum(png) and not force:
            print("  SKIP %s (hand-edited)" % fname)
            continue
        write_png(png, frames)
        rec[fname] = _checksum(png)
        slot, pkey = SLOTS[name]
        side = classic_sidecar("cast_" + name, fname, 16 * len(frames), slot, atype)
        png.with_name(fname + ".gbsres").write_text(json.dumps(side, indent=2))
        prev = preview(frames, PALETTES[pkey])
        prev.save(pdir / ("cast_%s.png" % name))
        sheets.append((name, prev))
    # contact sheet
    if sheets:
        w = max(p.width for _, p in sheets)
        sheet = Image.new("RGB", (w, sum(p.height + 4 for _, p in sheets)), (30, 30, 40))
        y = 0
        for _, p in sheets:
            sheet.paste(p, (0, y))
            y += p.height + 4
        sheet.save(pdir / "cast_contact_sheet.png")
    GEN.parent.mkdir(parents=True, exist_ok=True)
    GEN.write_text(json.dumps(rec, indent=1, sort_keys=True))
    write_palettes()
    print("cast sprites:", len(sheets))


if __name__ == "__main__":
    build(force="--force" in sys.argv)
