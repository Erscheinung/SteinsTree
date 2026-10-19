"""GBC-legal canvas, shared palette bank and GB Studio background export.

Every map is painted on a Canvas: one shade index (0 light .. 3 dark) per
pixel plus one palette slot per 8x8 tile. That is exactly what the Game Boy
Color can show, so whatever is painted here is what the game shows.

Export writes:
  * the runtime PNG in GB Studio's canonical greens (index image),
  * the background .gbsres sidecar with `tileColors` (palette slot per tile,
    the same data GB Studio's "Colorize" brush paints),
  * a full-colour preview PNG under art/ for humans.

Palette slots are fixed project-wide (see BANK): 0 grass, 1 path/sand,
2 stone/asphalt, 3 brick, 4 roof/glass, 5 water, 6 wood. Slot 7 is the UI.
Scenes may swap a whole bank at runtime (day, night, dream...) with GB
Studio's "Set Background Palettes" event, because every bank keeps the same
slot meanings.
"""

import json
import uuid
import zlib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
NS = uuid.UUID("5b0c1a3e-7d64-4a8e-9a43-6d7565726e69")  # "Dernier" namespace

CANONICAL = [(0xE0, 0xF8, 0xCF), (0x86, 0xC0, 0x6C), (0x30, 0x68, 0x50), (0x07, 0x18, 0x21)]

SLOTS = ["grass", "path", "stone", "brick", "roof", "water", "wood"]
SLOT = {name: i for i, name in enumerate(SLOTS)}

# Light -> dark. Shared colours are deliberate: PATH[3] == GRASS[1] so sand
# edges can carry grass tufts; BRICK[0] is plaster for beige facades.
BANKS = {
    "day": {
        # These ramps are sampled from the protected B7 originals.  The
        # earlier bank used very high-chroma Emerald greens/oranges, which
        # made the fixed slot renderer look fluorescent even when the source
        # geometry was faithful.  Keep the four values ordered light -> dark
        # so every existing tile pattern and night/dream derivation remains
        # valid, while matching the owner's warm plaster, yellow grass,
        # slate, and blue-glass language.
        "grass": ["D8D888", "B0B858", "649A3B", "456C33"],
        "path":  ["F0B050", "D89050", "A87848", "647A43"],
        "stone": ["E8E8D8", "B8B8C0", "707078", "404048"],
        # Warm plaster/ochre with a muted mauve shadow.  The previous
        # red-pink ramp made the owner's paving and wall bands fluorescent;
        # the dark mauve keeps the original paving cue without dominating the
        # yellow grass and facade details.
        "brick": ["E8D0A8", "D0A078", "A87868", "786078"],
        "roof":  ["E8F0F0", "98C0F0", "6070A8", "303048"],
        "water": ["E0F0E0", "90D8D0", "4898A0", "285878"],
        "wood":  ["F0D8A0", "C09050", "885030", "4B2B13"],
    },
}


def _hex(c):
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def _to_hex(rgb):
    return "%02X%02X%02X" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def _derive(bank, fn):
    return {k: [_to_hex(fn(_hex(c), i)) for i, c in enumerate(v)] for k, v in bank.items()}


def _night(rgb, i):
    r, g, b = rgb
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    return (r * 0.30 + lum * 0.10 + 6, g * 0.36 + lum * 0.10 + 10, b * 0.55 + lum * 0.22 + 34)


def _dusk(rgb, i):
    r, g, b = rgb
    return (r * 0.95 + 18, g * 0.72 + 8, b * 0.62 + 20)


def _blood(rgb, i):
    r, g, b = rgb
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    return (lum * 0.72 + 24, lum * 0.20 + 4, lum * 0.22 + 10)


def _memory(rgb, i):  # warm sepia for remembered scenes
    r, g, b = rgb
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    return (lum * 1.02 + 14, lum * 0.88 + 6, lum * 0.66)


def _dream(shift):
    import colorsys

    def fn(rgb, i):
        h, l, s = colorsys.rgb_to_hls(*(v / 255 for v in rgb))
        h = (h + shift) % 1.0
        s = min(0.85, s * 1.1 + 0.05)
        return tuple(v * 255 for v in colorsys.hls_to_rgb(h, l, s))
    return fn


BANKS["night"] = _derive(BANKS["day"], _night)
BANKS["dusk"] = _derive(BANKS["day"], _dusk)
BANKS["blood"] = _derive(BANKS["day"], _blood)
BANKS["memory"] = _derive(BANKS["day"], _memory)
for _n, _s in (("dreamA", 0.30), ("dreamB", 0.55), ("dreamC", 0.80)):
    BANKS[_n] = _derive(BANKS["day"], _dream(_s))

def _build_remap():
    day = BANKS["day"]
    out = {}
    for a in range(7):
        for b in range(7):
            ca = [_hex(c) for c in day[SLOTS[a]]]
            cb = [_hex(c) for c in day[SLOTS[b]]]
            out[(a, b)] = [min(range(4), key=lambda j: sum((p - q) ** 2 for p, q in zip(ca[i], cb[j])))
                           for i in range(4)]
    return out


_REMAP = _build_remap()

UI_PALETTE = ["F8F4E0", "C8C0A8", "686078", "181828"]


def palette_id(bank, slot):
    """Stable GB Studio palette id for a bank slot (e.g. 'muj-day-grass')."""
    return "muj-%s-%s" % (bank.lower(), SLOTS[slot] if isinstance(slot, int) else slot)


def palette_ids(bank):
    return [palette_id(bank, i) for i in range(7)] + ["muj-ui"]


def stable_id(*parts):
    return str(uuid.uuid5(NS, "/".join(str(p) for p in parts)))


class Canvas:
    """Width/height in tiles. Pixels hold shade 0..3; tiles hold a slot."""

    def __init__(self, wt, ht, slot=0, shade=1):
        self.wt, self.ht = wt, ht
        self.w, self.h = wt * 8, ht * 8
        self.px = bytearray([shade]) * (self.w * self.h)
        self.pal = [[slot] * wt for _ in range(ht)]
        self.solid = [[0] * wt for _ in range(ht)]
        self.conflicts = 0
        self.locked = [[False] * wt for _ in range(ht)]

    # -- palette bookkeeping -------------------------------------------
    def tile_slot(self, tx, ty):
        return self.pal[ty][tx]

    def claim(self, tx, ty, slot):
        """Set the palette of a tile, counting clashes with locked tiles."""
        if not (0 <= tx < self.wt and 0 <= ty < self.ht):
            return False
        old = self.pal[ty][tx]
        if old != slot:
            if self.locked[ty][tx]:
                self.conflicts += 1
                return False
            # Re-express the tile's existing pixels in the new palette so a
            # palette change never flips colours wildly (nearest day colour).
            remap = _REMAP[(old, slot)]
            for y in range(8):
                o = (ty * 8 + y) * self.w + tx * 8
                for x in range(8):
                    self.px[o + x] = remap[self.px[o + x]]
            self.pal[ty][tx] = slot
        return True

    # -- pixel ops -------------------------------------------------------
    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y * self.w + x]
        return None

    def set(self, x, y, shade, slot=None):
        if not (0 <= x < self.w and 0 <= y < self.h):
            return
        if slot is not None and self.pal[y >> 3][x >> 3] != slot:
            if not self.claim(x >> 3, y >> 3, slot):
                return
        self.px[y * self.w + x] = shade

    def darken(self, x, y, amount=1, only_slots=None):
        """Shift a pixel darker within its own palette (cast shadows)."""
        if not (0 <= x < self.w and 0 <= y < self.h):
            return
        if only_slots is not None and self.pal[y >> 3][x >> 3] not in only_slots:
            return
        i = y * self.w + x
        self.px[i] = min(3, self.px[i] + amount)

    def blit_tile(self, tx, ty, slot, pattern, lock=False):
        """pattern: 8 strings of 8 chars '0'..'3' ('.' keeps pixel)."""
        if not (0 <= tx < self.wt and 0 <= ty < self.ht):
            return
        self.pal[ty][tx] = slot
        if lock:
            self.locked[ty][tx] = True
        for y, row in enumerate(pattern):
            for x, ch in enumerate(row):
                if ch != ".":
                    self.px[(ty * 8 + y) * self.w + tx * 8 + x] = ord(ch) - 48

    def rect(self, x0, y0, x1, y1, shade, slot=None):
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(self.w, x1)):
                self.set(x, y, shade, slot)

    def set_solid(self, tx0, ty0, tx1, ty1, value=0x0F):
        for ty in range(max(0, ty0), min(self.ht, ty1)):
            for tx in range(max(0, tx0), min(self.wt, tx1)):
                self.solid[ty][tx] = value

    # -- analysis --------------------------------------------------------
    def tile_bytes(self, tx, ty):
        out = bytearray()
        for y in range(8):
            o = (ty * 8 + y) * self.w + tx * 8
            out += self.px[o:o + 8]
        return bytes(out)

    def reduce_tiles(self, limit):
        """Merge rare tiles into their nearest frequent look-alike until the
        background fits GB Studio's tile budget. Returns tiles merged."""
        import numpy as np
        from collections import Counter
        keys = {}
        for ty in range(self.ht):
            for tx in range(self.wt):
                keys.setdefault(self.tile_bytes(tx, ty), []).append((tx, ty))
        if len(keys) <= limit:
            return 0
        counts = Counter({k: len(v) for k, v in keys.items()})
        ranked = [k for k, _ in counts.most_common()]
        keep = np.array([list(k) for k in ranked[:limit]], dtype=np.int16)
        merged = 0
        for k in ranked[limit:]:
            v = np.array(list(k), dtype=np.int16)
            diff = np.abs(keep - v)
            score = (diff > 0).sum(axis=1) * 4 + diff.sum(axis=1)
            best = bytes(keep[int(score.argmin())].astype(np.uint8))
            for tx, ty in keys[k]:
                for y in range(8):
                    o = (ty * 8 + y) * self.w + tx * 8
                    self.px[o:o + 8] = best[y * 8:y * 8 + 8]
            merged += 1
        return merged

    def unique_tiles(self):
        return len({self.tile_bytes(tx, ty) for ty in range(self.ht) for tx in range(self.wt)})

    # -- output ----------------------------------------------------------
    def to_index_image(self):
        im = Image.new("RGB", (self.w, self.h))
        im.putdata([CANONICAL[v] for v in self.px])
        return im

    def to_preview(self, bank="day", scale=1):
        cols = BANKS[bank]
        lut = [[_hex(c) for c in cols[s]] for s in SLOTS]
        data = []
        for y in range(self.h):
            prow = self.pal[y >> 3]
            o = y * self.w
            for x in range(self.w):
                data.append(lut[prow[x >> 3]][self.px[o + x]])
        im = Image.new("RGB", (self.w, self.h))
        im.putdata(data)
        if scale > 1:
            im = im.resize((self.w * scale, self.h * scale), Image.NEAREST)
        return im

    def tile_colors(self):
        flat = [self.pal[ty][tx] for ty in range(self.ht) for tx in range(self.wt)]
        return compress8(flat)

    def collisions(self):
        return compress8([self.solid[ty][tx] for ty in range(self.ht) for tx in range(self.wt)])


def compress8(arr):
    """GB Studio's run-length string (compress8bitNumberArray)."""
    out = []
    last = None
    count = 0

    def flush():
        if count == 1:
            out.append("!")
        elif count > 1:
            out.append("%x+" % count)

    for v in arr:
        if v != last:
            flush()
            count = 0
            last = v
            out.append("%02x" % (v % 256))
        count += 1
    flush()
    return "".join(out)


def decompress8(s):
    arr = []
    i = 0
    while i < len(s):
        v = int(s[i:i + 2], 16)
        i += 2
        if i < len(s) and s[i] == "!":
            arr.append(v)
            i += 1
            continue
        j = s.index("+", i)
        arr += [v] * int(s[i:j], 16)
        i = j + 1
    return arr


def write_background(canvas, name, folder="muj", preview_bank="day", preview_dir=None):
    """Write runtime PNG + sidecar + previews. Returns the background id."""
    rel = Path(folder) / (name + ".png") if folder else Path(name + ".png")
    png = ROOT / "assets" / "backgrounds" / rel
    png.parent.mkdir(parents=True, exist_ok=True)
    canvas.to_index_image().save(png, optimize=True)
    bg_id = stable_id("background", str(rel))
    sidecar = {
        "_resourceType": "background",
        "id": bg_id,
        "name": name,
        "symbol": "bg_" + "".join(ch if ch.isalnum() else "_" for ch in name.lower()),
        "tileColors": canvas.tile_colors(),
        "filename": rel.as_posix(),
        "width": canvas.wt,
        "height": canvas.ht,
        "imageWidth": canvas.w,
        "imageHeight": canvas.h,
    }
    png.with_name(png.name + ".gbsres").write_text(json.dumps(sidecar, indent=2))
    pdir = Path(preview_dir) if preview_dir else ROOT / "art" / "maps" / "preview"
    pdir.mkdir(parents=True, exist_ok=True)
    canvas.to_preview(preview_bank).save(pdir / (name + ".png"), optimize=True)
    return bg_id


def checksum(path):
    return "%08x" % (zlib.crc32(Path(path).read_bytes()) & 0xFFFFFFFF)
