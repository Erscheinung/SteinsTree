"""Tile catalogue + per-map tile atlases (for LibreSprite / reference).

    python3 tools/map/tilesheet.py

Writes
  art/tilesets/muj/catalogue_<bank>.png  every terrain texture and its variants,
                                         edges, trees, bushes, hedges, roofs, walls
                                         (8x8 grid, labelled), per palette bank
  art/tilesets/muj/atlas_<map>.png       the unique tiles a generated map uses
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw

import gbc
import painter as pt

OUT = gbc.ROOT / "art" / "tilesets" / "muj"


def catalogue(bank):
    rows = []
    # terrain variants
    for code, (slot, fn, nvar, solid) in pt.TERRAIN.items():
        cv = gbc.Canvas(max(nvar, 1) * 2 + 1, 2)
        for v in range(nvar):
            for dy in range(2):
                cv.blit_tile(v * 2, dy, slot, fn(v))
                cv.blit_tile(v * 2 + 1, dy, slot, fn(v))
        rows.append((code + " (%d variants)" % nvar, cv))
    # edges: a 6x4 patch of each hard surface surrounded by grass
    for code in ("dirt", "paving", "plaza", "road", "water", "track", "court"):
        grid = [["grass"] * 8 for _ in range(4)]
        for y in range(1, 3):
            for x in range(2, 6):
                grid[y][x] = code
        cv = gbc.Canvas(8, 4)
        pt.paint_terrain(cv, grid)
        rows.append((code + " edges", cv))
    # objects
    cv = gbc.Canvas(16, 4)
    pt.paint_terrain(cv, [["grass"] * 16 for _ in range(4)])
    pt.tree(cv, 0, 0, 16, 0)
    pt.tree(cv, 24, 0, 16, 1)
    pt.tree(cv, 48, 0, 24, 2)
    pt.bush(cv, 80, 8, 8, 7)
    pt.hedge(cv, 11, 2, 15)
    pt.bench(cv, 88, 24)
    pt.lamp(cv, 120, 4)
    rows.append(("trees, bush, hedge, bench, lamp", cv))
    cv = gbc.Canvas(12, 6)
    pt.paint_terrain(cv, [["grass"] * 12 for _ in range(6)])
    pt.paint_forest_tiles(cv, [[x >= 6 for x in range(12)] for _ in range(6)])
    pt.blob_building(cv, {(x, y) for x in range(0, 5) for y in range(0, 5)}, style="hostel", roof="flat",
                     wall_rows=1)
    rows.append(("woodland canopy, hostel block", cv))
    cv = gbc.Canvas(16, 6)
    pt.paint_terrain(cv, [["grass"] * 16 for _ in range(6)])
    pt.blob_building(cv, {(x, y) for x in range(0, 7) for y in range(0, 6)}, style="academic", roof="solar",
                     wall_rows=2, doors={(3, 5)})
    pt.blob_building(cv, {(x, y) for x in range(8, 15) for y in range(0, 6)}, style="mess", roof="tile",
                     wall_rows=2, doors={(11, 5)})
    rows.append(("academic (solar roof), mess (tiled roof)", cv))

    scale = 3
    width = max(c.w for _, c in rows) * scale + 260
    height = sum(c.h * scale + 14 for _, c in rows) + 10
    sheet = Image.new("RGB", (width, height), (24, 22, 32))
    d = ImageDraw.Draw(sheet)
    y = 6
    for label, c in rows:
        im = c.to_preview(bank, scale)
        sheet.paste(im, (250, y))
        d.text((8, y + 2), label, fill=(236, 231, 216))
        y += c.h * scale + 14
    return sheet


def atlas(name):
    png = gbc.ROOT / "assets" / "backgrounds" / "muj" / (name + ".png")
    side = png.with_name(png.name + ".gbsres")
    if not png.exists():
        return None
    meta = json.loads(side.read_text())
    pal = gbc.decompress8(meta["tileColors"])
    im = Image.open(png).convert("RGB")
    w, h = im.size
    lut = {c: i for i, c in enumerate(gbc.CANONICAL)}
    seen = {}
    for ty in range(h // 8):
        for tx in range(w // 8):
            tile = im.crop((tx * 8, ty * 8, tx * 8 + 8, ty * 8 + 8))
            key = tile.tobytes()
            if key not in seen:
                seen[key] = (tile, pal[ty * (w // 8) + tx] if ty * (w // 8) + tx < len(pal) else 0)
    cols = 16
    n = len(seen)
    out = Image.new("RGB", (cols * 9 + 1, ((n + cols - 1) // cols) * 9 + 1), (24, 22, 32))
    bankcols = [[gbc._hex(c) for c in gbc.BANKS["day"][s]] for s in gbc.SLOTS]
    for i, (tile, slot) in enumerate(seen.values()):
        colored = Image.new("RGB", (8, 8))
        colored.putdata([bankcols[min(slot, 6)][lut.get(p, 0)] for p in tile.getdata()])
        out.paste(colored, ((i % cols) * 9 + 1, (i // cols) * 9 + 1))
    return out.resize((out.width * 3, out.height * 3), Image.NEAREST)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for bank in ("day", "night", "dusk", "memory", "dreamA"):
        catalogue(bank).save(OUT / ("catalogue_%s.png" % bank), optimize=True)
    n = 0
    for p in sorted((gbc.ROOT / "assets" / "backgrounds" / "muj").glob("*.png")):
        a = atlas(p.stem)
        if a:
            a.save(OUT / ("atlas_%s.png" % p.stem), optimize=True)
            n += 1
    print("catalogues: 5 banks, atlases:", n)


if __name__ == "__main__":
    main()
