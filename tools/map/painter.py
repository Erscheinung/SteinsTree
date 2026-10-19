"""Procedural Emerald-style tiles and objects for the GBC Canvas.

Lighting is always from the top-left: highlights sit on upper-left edges,
shade on lower-right, and objects cast shadows down-right onto the ground.
Every ground texture has a small fixed set of variants (picked by a position
hash) so maps look organic while the unique-tile count stays inside GB
Studio's per-background budget.

Terrain codes used in map grids (one per 8x8 tile):
  grass lawn scrub flowers farm dirt sand paving plaza road track outfield
  pitch court water floor_wood floor_tile floor_carpet floor_lab void dark
"""

import math

from gbc import SLOT

G, P, S, B, R, W, T = (SLOT[k] for k in ("grass", "path", "stone", "brick", "roof", "water", "wood"))


def h(x, y, s=0):
    """Deterministic hash noise in [0,1)."""
    n = (x * 374761393 + y * 668265263 + s * 2147483647) & 0xFFFFFFFF
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65536.0


def variant(tx, ty, n, s=0):
    return int(h(tx, ty, s + 17) * n)


# ---------------------------------------------------------------------------
# Ground textures: functions (tx, ty, v) -> 8 rows of shade chars
# ---------------------------------------------------------------------------

def _grid(fill="1"):
    return [[fill] * 8 for _ in range(8)]


def _rows(g):
    return ["".join(r) for r in g]


def tex_grass(v):
    # calm base: mostly flat grass, a single soft tuft on half the variants
    g = _grid("1")
    if v == 1:
        g[2][5] = "0"
    elif v == 2:
        x, y = 2, 3
        g[y][x], g[y][x + 1], g[y + 1][x] = "0", "0", "2"
    elif v == 3:
        g[5][5], g[6][5] = "0", "2"
    return _rows(g)


def tex_lawn(v):
    # mown stripes: the caller picks v from the tile row so bands run E-W
    g = _grid("1")
    for x in range(8):
        y = int(h(x, v, 11) * 8)
        if h(x, v, 12) > 0.55:
            g[y][x] = "0" if v % 2 == 0 else "2"
    return _rows(g)


def tex_scrub(v):
    g = _grid("1")
    for i in range(10):
        x, y = int(h(i, v, 21) * 8), int(h(i, v, 22) * 8)
        g[y][x] = "2" if h(i, v, 23) > 0.35 else "3"
    for i in range(4):
        x, y = int(h(i, v, 24) * 8), int(h(i, v, 25) * 8)
        g[y][x] = "0"
    return _rows(g)


def tex_flowers(v):
    g = [list(r) for r in tex_grass(v)]
    for i in range(2 + v % 2):
        x, y = 1 + int(h(i, v, 31) * 5), 1 + int(h(i, v, 32) * 5)
        g[y][x] = "0"
        g[y - 1][x] = "0"
        g[y + 1][x] = "0"
        g[y][x - 1] = "0"
        g[y][x + 1] = "0"
        g[y][x] = "3"
    return _rows(g)


def tex_farm(v):
    # furrowed field (path palette): parallel furrows with pale ridges
    g = _grid("1")
    for y in range(8):
        if (y + v) % 3 == 0:
            g[y] = list("22222222")
        elif (y + v) % 3 == 1:
            g[y] = list("00100010" if v % 2 else "01000100")
    return _rows(g)


def tex_dirt(v):
    g = _grid("1")
    for i in range(5):
        x, y = int(h(i, v, 41) * 8), int(h(i, v, 42) * 8)
        g[y][x] = "2"
    for i in range(3):
        x, y = int(h(i, v, 43) * 8), int(h(i, v, 44) * 8)
        g[y][x] = "0"
    if v == 2:
        g[3][3], g[3][4], g[4][3] = "0", "2", "2"  # pebble
    return _rows(g)


def tex_sand(v):
    g = _grid("0")
    for i in range(6):
        x, y = int(h(i, v, 51) * 8), int(h(i, v, 52) * 8)
        g[y][x] = "1"
    return _rows(g)


def tex_paving(v):
    # 8x8 concrete slab with a mortar seam on the right/bottom
    g = _grid("1")
    for i in range(8):
        g[7][i] = "2"
        g[i][7] = "2"
        g[0][i] = "0"
    if v % 2:
        g[2][2] = "1"
    if v == 2:
        g[5][4] = "1"
    return _rows(g)


def tex_plaza(v):
    # red brick herringbone (brick palette)
    rows = ["11112111", "11112111", "22222222", "21111111", "21111111", "22222222",
            "11112111", "11112111"]
    if v % 2:
        rows = [r[4:] + r[:4] for r in rows]
    return rows


def tex_road(v):
    g = _grid("2")
    for i in range(2 + v):
        x, y = int(h(i, v, 61) * 8), int(h(i, v, 62) * 8)
        g[y][x] = "3" if h(i, v, 63) > 0.5 else "1"
    return _rows(g)


def tex_track(v):
    g = _grid("1")
    for i in range(4):
        x, y = int(h(i, v, 71) * 8), int(h(i, v, 72) * 8)
        g[y][x] = "2"
    return _rows(g)


def tex_court(v):
    g = _grid("2")
    for i in range(3):
        x, y = int(h(i, v, 81) * 8), int(h(i, v, 82) * 8)
        g[y][x] = "1"
    return _rows(g)


def tex_water(v):
    g = _grid("1")
    y = 2 + (v * 3) % 5
    x = (v * 5) % 6
    g[y][x], g[y][x + 1], g[y][x + 2] = "0", "0", "2"
    if v % 2:
        g[(y + 3) % 8][(x + 3) % 8] = "0"
    return _rows(g)


def tex_floor_wood(v):
    rows = []
    for y in range(8):
        if y % 4 == 3:
            rows.append("22222222")
        else:
            r = ["1"] * 8
            seam = (v * 3 + (y // 4) * 4) % 8
            if y % 4 == 1:
                r[seam] = "2"
            if y % 4 == 0:
                r[(seam + 2) % 8] = "0"
            rows.append("".join(r))
    return rows


def tex_floor_tile(v):
    g = _grid("0")
    for i in range(8):
        g[7][i] = "1"
        g[i][7] = "1"
    g[0][0] = "0"
    if v % 2:
        g[3][3] = "1"
    return _rows(g)


def tex_floor_carpet(v):
    g = _grid("1")
    for y in range(8):
        for x in range(8):
            if (x + y + v) % 4 == 0:
                g[y][x] = "2"
    return _rows(g)


def tex_floor_lab(v):
    # checkerboard lino
    return ["00001111"] * 4 + ["11110000"] * 4 if v % 2 == 0 else ["11110000"] * 4 + ["00001111"] * 4


def tex_flat(shade):
    return lambda v: [shade * 8] * 8


def tex_stars(v):
    g = _grid("3")
    for i in range(1 + v % 3):
        x, y = int(h(i, v, 91) * 8), int(h(i, v, 92) * 8)
        g[y][x] = "0" if i == 0 else "1"
    return _rows(g)


TERRAIN = {
    # code: (slot, texture fn, variants, solid)
    "grass": (G, tex_grass, 4, 0),
    "lawn": (G, tex_lawn, 2, 0),
    "scrub": (G, tex_scrub, 3, 0),
    "flowers": (G, tex_flowers, 2, 0),
    "farm": (P, tex_farm, 3, 0),
    "dirt": (P, tex_dirt, 3, 0),
    "sand": (P, tex_sand, 2, 0),
    "paving": (S, tex_paving, 3, 0),
    "plaza": (B, tex_plaza, 2, 0),
    "road": (S, tex_road, 3, 0),
    "track": (B, tex_track, 2, 0),
    "outfield": (G, tex_lawn, 2, 0),
    "pitch": (P, tex_sand, 2, 0),
    "court": (R, tex_court, 2, 0),
    "water": (W, tex_water, 4, 0x0F),
    "floor_wood": (T, tex_floor_wood, 2, 0),
    "floor_tile": (S, tex_floor_tile, 2, 0),
    "floor_carpet": (B, tex_floor_carpet, 2, 0),
    "floor_lab": (S, tex_floor_lab, 2, 0),
    "void": (S, tex_flat("3"), 1, 0x0F),
    "dark": (S, tex_stars, 4, 0),
}

# Classes that read as "soft ground": edges of harder surfaces get tufts here.
SOFT = {"grass", "lawn", "scrub", "flowers", "outfield"}


def paint_terrain(cv, grid):
    """grid[ty][tx] -> terrain code. Paints textures plus autotiled edges."""
    for ty in range(cv.ht):
        for tx in range(cv.wt):
            code = grid[ty][tx]
            slot, fn, nvar, solid = TERRAIN[code]
            if code in ("lawn", "outfield"):
                v = (ty // 2) % 2
            else:
                v = variant(tx, ty, nvar, sum(map(ord, code)))
            cv.blit_tile(tx, ty, slot, fn(v))
            if solid:
                cv.solid[ty][tx] = solid
    for ty in range(cv.ht):
        for tx in range(cv.wt):
            _edges(cv, grid, tx, ty)


def _nb(grid, tx, ty):
    H, Wd = len(grid), len(grid[0])
    def at(x, y):
        if 0 <= x < Wd and 0 <= y < H:
            return grid[y][x]
        return grid[ty][tx]
    return at(tx, ty - 1), at(tx + 1, ty), at(tx, ty + 1), at(tx - 1, ty)


def _edges(cv, grid, tx, ty):
    code = grid[ty][tx]
    n, e, s, w = _nb(grid, tx, ty)
    X, Y = tx * 8, ty * 8

    def line(side, shade, width=1, slot=None):
        for i in range(8):
            for k in range(width):
                if side == "n":
                    cv.set(X + i, Y + k, shade, slot)
                elif side == "s":
                    cv.set(X + i, Y + 7 - k, shade, slot)
                elif side == "w":
                    cv.set(X + k, Y + i, shade, slot)
                else:
                    cv.set(X + 7 - k, Y + i, shade, slot)

    sides = {"n": n, "e": e, "s": s, "w": w}
    if code in ("dirt", "sand", "pitch", "farm"):
        # grass tufts creep over sand edges (PATH[3] is the grass colour)
        for side, other in sides.items():
            if other in SOFT:
                for i in range(8):
                    depth = (1, 2, 1, 3, 2, 1, 2, 1)[i]
                    for k in range(depth):
                        if side == "n":
                            cv.set(X + i, Y + k, 3)
                        elif side == "s":
                            cv.set(X + i, Y + 7 - k, 3)
                        elif side == "w":
                            cv.set(X + k, Y + i, 3)
                        else:
                            cv.set(X + 7 - k, Y + i, 3)
    elif code == "road":
        for side, other in sides.items():
            if other != "road":
                line(side, 0, 1)      # bright curb
                if side in ("s", "e"):
                    line(side, 3, 1)  # curb shadow on the lit side's far edge
    elif code == "paving":
        for side, other in sides.items():
            if other not in ("paving", "road", "plaza"):
                line(side, 2, 1)
    elif code == "plaza":
        for side, other in sides.items():
            if other not in ("plaza", "paving"):
                line(side, 3, 1)
    elif code == "water":
        for side, other in sides.items():
            if other != "water":
                line(side, 0, 2)
                if side == "n":
                    for i in range(8):
                        cv.set(X + i, Y + 2, 2)   # shadow under the north coping
    elif code == "track":
        for side, other in sides.items():
            if other != "track":
                line(side, 0, 1)
    elif code == "court":
        for side, other in sides.items():
            if other != "court":
                line(side, 0, 1)
    elif code in SOFT:
        # soft shading where grass meets a raised hard edge to the north/west
        if n in ("road", "paving", "plaza"):
            line("n", 2, 1)
        if w in ("road", "paving", "plaza"):
            line("w", 2, 1)


# ---------------------------------------------------------------------------
# Shadows
# ---------------------------------------------------------------------------

GROUND_SLOTS = {G, P, S, B, R}


def cast_shadow_rect(cv, x0, y0, x1, y1, dx=4, dy=4, amount=1):
    """Shadow of an axis-aligned block, offset down-right, on ground only.

    Offsets are snapped to 4px so shadow edges come in a few fixed shapes,
    which keeps the unique-tile count low."""
    dx = 4 if dx >= 3 else dx
    dy = 4 if dy >= 3 else dy
    for y in range(y0 + dy, y1 + dy):
        for x in range(x0 + dx, x1 + dx):
            if x0 <= x < x1 and y0 <= y < y1:
                continue
            cv.darken(x, y, amount, GROUND_SLOTS)


def cast_shadow_ellipse(cv, cx, cy, rx, ry, amount=1):
    for y in range(int(cy - ry), int(cy + ry) + 1):
        for x in range(int(cx - rx), int(cx + rx) + 1):
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                cv.darken(x, y, amount, GROUND_SLOTS)


# ---------------------------------------------------------------------------
# Objects
# ---------------------------------------------------------------------------

def _sphere_shade(nx, ny, noise):
    d = (nx + ny) * 0.75 + noise * 0.35
    if d < -0.55:
        return 0
    if d < 0.15:
        return 1
    if d < 0.75:
        return 2
    return 3


def tree(cv, x, y, size=16, kind=0, shadow=True, solid=True):
    """Round-canopy tree whose canopy box starts at pixel (x,y)."""
    r = size / 2.0
    cx, cy = x + r - 0.5, y + r - 0.5
    trunk_h = max(3, size // 5)
    if shadow:
        cast_shadow_ellipse(cv, cx + size * 0.3, cy + r * 0.85, r * 0.85, r * 0.45)
    # bumpy silhouette from overlapping lobes
    lobes = [(0, 0, 1.0)]
    for i in range(5):
        ang = i * 2 * math.pi / 5 + kind
        lobes.append((math.cos(ang) * r * 0.45, math.sin(ang) * r * 0.40, 0.62))
    for py in range(int(y), int(y + size)):
        for px in range(int(x), int(x + size)):
            inside = False
            for lx, ly, lr in lobes:
                if ((px - cx - lx) ** 2 + (py - cy - ly) ** 2) <= (r * lr) ** 2:
                    inside = True
                    break
            if not inside:
                continue
            # outline: any 4-neighbour outside the silhouette
            edge = False
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                qx, qy = px + ox, py + oy
                if not any(((qx - cx - lx) ** 2 + (qy - cy - ly) ** 2) <= (r * lr) ** 2 for lx, ly, lr in lobes):
                    edge = True
            nx, ny = (px - cx) / r, (py - cy) / r
            lx, ly = px - int(x), py - int(y)
            shade = 3 if edge and (nx + ny) > -0.3 else _sphere_shade(nx, ny, h(lx, ly, kind) - 0.5)
            if edge and (nx + ny) <= -0.3:
                shade = 2 if (nx + ny) > -0.9 else 1
            # leaf clusters: small highlight flecks on the lit half
            if shade == 1 and h(lx, ly, 9) > 0.86:
                shade = 0
            cv.set(px, py, shade, G)
    # trunk
    tx0 = int(cx) - 1
    for py in range(int(y + size - 2), int(y + size - 2 + trunk_h)):
        cv.set(tx0, py, 2, G)
        cv.set(tx0 + 1, py, 3, G)
        cv.set(tx0 + 2, py, 3, G)
    if solid:
        cv.set_solid(int(x) // 8, int(y + size * 0.5) // 8, int(x + size - 1) // 8 + 1, int(y + size + trunk_h - 2) // 8 + 1)


def bush(cv, x, y, w=8, hgt=7, solid=True):
    cast_shadow_ellipse(cv, x + w * 0.7, y + hgt * 0.95, w * 0.55, 2.2)
    cx, cy = x + w / 2 - 0.5, y + hgt / 2
    for py in range(y, y + hgt):
        for px in range(x, x + w):
            nx, ny = (px - cx) / (w / 2), (py - cy) / (hgt / 2)
            d2 = nx * nx + ny * ny
            if d2 > 1.0:
                continue
            shade = 3 if d2 > 0.72 and (nx + ny) > -0.2 else _sphere_shade(nx, ny, h(px - x, py - y, 4) - 0.5)
            cv.set(px, py, shade, G)
    if solid:
        cv.set_solid(x // 8, y // 8, (x + w - 1) // 8 + 1, (y + hgt - 1) // 8 + 1)


def hedge(cv, tx0, ty, tx1, solid=True):
    """A clipped hedge along tile row `ty` from tile tx0 to tx1 (exclusive)."""
    y0 = ty * 8
    cast_shadow_rect(cv, tx0 * 8, y0, tx1 * 8, y0 + 8, dx=3, dy=3)
    for x in range(tx0 * 8, tx1 * 8):
        bump = 1 if (x // 3) % 2 else 0
        for y in range(y0 + bump, y0 + 8):
            yy = y - y0
            if yy == bump or x == tx0 * 8 or x == tx1 * 8 - 1 or yy == 7:
                shade = 3 if (yy == 7 or x == tx1 * 8 - 1) else 2
            elif yy <= 2:
                shade = 0 if h(x % 8, yy, 6) > 0.4 else 1
            elif yy <= 5:
                shade = 1 if h(x % 8, yy, 7) > 0.25 else 2
            else:
                shade = 2
            cv.set(x, y, shade, G)
    if solid:
        cv.set_solid(tx0, ty, tx1, ty + 1)


def forest(cv, tx0, ty0, tx1, ty1, seed=0, density=1.0, skip=None):
    """Dense Emerald-style woodland: staggered overlapping tree rows."""
    rows = []
    for py in range(ty0 * 8 - 4, ty1 * 8 - 8, 9):
        rows.append(py)
    for ri, py in enumerate(rows):
        off = 0 if ri % 2 == 0 else 8
        for px in range(tx0 * 8 - 4 + off, tx1 * 8 - 8, 16):
            if skip and skip(px // 8, py // 8):
                continue
            if h(px, py, seed) > density:
                continue
            tree(cv, px, py, 16, kind=(px + py) % 3, shadow=False, solid=False)
    cv.set_solid(tx0, ty0, tx1, ty1)


def building(cv, tx, ty, w, hgt, wall=2, style="hostel", roof="flat", doors=(), windows="small",
             solid=True, shadow=True, sign=False):
    """3/4 top-down block: roof on top rows, front wall on the last `wall` rows.

    style: hostel (plaster + terracotta), academic (terracotta + big glass),
           plain (concrete), mess (terracotta + awning).
    roof:  flat | solar | tile
    """
    x0, y0, x1, y1 = tx * 8, ty * 8, (tx + w) * 8, (ty + hgt) * 8
    if shadow:
        cast_shadow_rect(cv, x0, y0, x1, y1, dx=6, dy=4)
    roof_rows = hgt - wall
    # ---- roof
    for ry in range(roof_rows):
        for rx in range(w):
            ttx, tty = tx + rx, ty + ry
            if roof == "solar" and 0 < rx < w - 1 and 0 < ry < roof_rows - 1 and (rx + ry) % 3 != 0:
                cv.blit_tile(ttx, tty, R, ["32222223", "21111112", "21111112", "33333333",
                                            "21111112", "21011112", "21111112", "33333333"], lock=True)
                continue
            slot = B if roof == "tile" else S
            pat = []
            for py in range(8):
                row = []
                for px in range(8):
                    X, Y = rx * 8 + px, ry * 8 + py
                    if X == 0 or Y == 0 or X == w * 8 - 1:
                        c = "3"
                    elif X == 1 or Y == 1:
                        c = "0"
                    elif X == w * 8 - 2 or (Y == roof_rows * 8 - 1):
                        c = "2"
                    elif roof == "tile":
                        c = "2" if Y % 4 == 3 else ("0" if (X + Y // 4 * 2) % 8 == 0 else "1")
                    else:
                        c = "1" if h(X % 8, Y % 8, 3) > 0.08 else "2"
                    row.append(c)
                pat.append("".join(row))
            cv.blit_tile(ttx, tty, slot, pat, lock=True)
    # ---- front wall
    for wy in range(wall):
        for wx in range(w):
            ttx, tty = tx + wx, ty + roof_rows + wy
            is_door = wx in doors and wy == wall - 1
            win = (windows != "none" and not is_door and 0 < wx < w - 1 and
                   (windows == "big" or wx % 2 == 1) and not (wy == wall - 1 and windows == "small" and wall > 1))
            if is_door:
                cv.blit_tile(ttx, tty, T, ["33333333", "32222223", "32111123", "32111123",
                                            "32111123", "32110123", "32111123", "32111123"], lock=True)
                continue
            if win:
                top = "00000000" if wy == 0 else "11111111"
                cv.blit_tile(ttx, tty, R, [top, "03333330", "03122130", "03211230",
                                            "03122130", "03211230", "03333330", "00000000" if wy < wall - 1 else "33333333"],
                             lock=True)
                continue
            slot = B
            pat = []
            for py in range(8):
                row = []
                for px in range(8):
                    if wy == 0 and py == 0:
                        c = "3"
                    elif wy == 0 and py <= 2 and style in ("hostel", "plain"):
                        c = "0"
                    elif wy == wall - 1 and py == 7:
                        c = "3"
                    elif wy == wall - 1 and py == 6:
                        c = "2"
                    elif wx == w - 1 and px == 7:
                        c = "2"
                    elif style == "academic":
                        c = "2" if py % 4 == 3 else ("2" if (px + (py // 4) * 4) % 8 == 7 else "1")
                    elif style == "plain":
                        c = "0" if py < 4 else "1"
                    else:
                        c = "1"
                    row.append(c)
                pat.append("".join(row))
            cv.blit_tile(ttx, tty, slot, pat, lock=True)
    if solid:
        cv.set_solid(tx, ty, tx + w, ty + hgt)
        for d in doors:
            cv.solid[ty + hgt - 1][tx + d] = 0
    return [(tx + d, ty + hgt - 1) for d in doors]


def dome(cv, cx, cy, r):
    """Shaded hemispherical dome (stone palette) centred on pixel (cx,cy)."""
    for y in range(int(cy - r), int(cy + r) + 1):
        for x in range(int(cx - r), int(cx + r) + 1):
            nx, ny = (x - cx) / r, (y - cy) / r
            d2 = nx * nx + ny * ny
            if d2 > 1:
                continue
            if d2 > 0.86:
                c = 3
            else:
                lit = -(nx * 0.6 + ny * 0.8) + 0.3 * (1 - d2)
                c = 0 if lit > 0.45 else 1 if lit > -0.05 else 2
                if abs(nx) < 0.08 and ny < 0:
                    c = 2  # meridian rib
            cv.set(x, y, c, S)


def bench(cv, x, y):
    for i in range(12):
        cv.set(x + i, y, 1, T)
        cv.set(x + i, y + 1, 2, T)
        cv.set(x + i, y + 2, 3, T)
    for i in (1, 10):
        cv.set(x + i, y + 3, 3, T)
        cv.set(x + i, y + 4, 3, T)
    cv.set_solid(x // 8, y // 8, (x + 11) // 8 + 1, (y + 4) // 8 + 1)


def lamp(cv, x, y):
    for i in range(10):
        cv.set(x, y + i, 3, S)
        cv.set(x + 1, y + i, 2, S)
    cv.rect(x - 1, y - 2, x + 3, y, 0, S)
    cv.solid[(y + 9) // 8][x // 8] = 0x0F


def car(cv, x, y, horizontal=True):
    w, hh = (14, 8) if horizontal else (8, 14)
    cast_shadow_rect(cv, x, y, x + w, y + hh, dx=2, dy=2)
    for py in range(hh):
        for px in range(w):
            edge = px in (0, w - 1) or py in (0, hh - 1)
            glass = (2 <= px <= w - 3 and 2 <= py <= hh - 3)
            c = 3 if edge else (2 if glass else (0 if py == 1 or px == 1 else 1))
            cv.set(x + px, y + py, c, R)


def fence(cv, tx0, ty, tx1, slot=None):
    slot = S if slot is None else slot
    for x in range(tx0 * 8, tx1 * 8):
        cv.set(x, ty * 8 + 2, 0, slot)
        cv.set(x, ty * 8 + 3, 2, slot)
        if x % 4 == 0:
            for k in range(1, 7):
                cv.set(x, ty * 8 + k, 3 if k > 3 else 2, slot)
    cv.set_solid(tx0, ty, tx1, ty + 1)


def wall_v(cv, tx, ty0, ty1, slot=None):
    slot = B if slot is None else slot
    for ty in range(ty0, ty1):
        cv.blit_tile(tx, ty, slot, ["32111123", "32111123", "32222223", "32111123",
                                     "32111123", "32222223", "32111123", "32111123"], lock=True)
    cv.set_solid(tx, ty0, tx + 1, ty1)


def wall_h(cv, tx0, tx1, ty, slot=None):
    slot = B if slot is None else slot
    for tx in range(tx0, tx1):
        cv.blit_tile(tx, ty, slot, ["33333333", "00000000", "11121112", "11121112",
                                     "22222222", "12111211", "22222222", "33333333"], lock=True)
    cv.set_solid(tx0, ty, tx1, ty + 1)


def stairs(cv, tx, ty, w, hgt):
    for y in range(ty * 8, (ty + hgt) * 8):
        for x in range(tx * 8, (tx + w) * 8):
            k = (y - ty * 8) % 4
            cv.set(x, y, 0 if k == 0 else 1 if k == 1 else 2, S)
    for y in range(ty * 8, (ty + hgt) * 8):
        cv.set(tx * 8, y, 3, S)
        cv.set((tx + w) * 8 - 1, y, 3, S)


def solar_field(cv, tx0, ty0, tx1, ty1):
    for ty in range(ty0, ty1):
        for tx in range(tx0, tx1):
            if ty % 3 == 2:
                continue
            cv.blit_tile(tx, ty, R, ["33333333", "21212121", "12121212", "21212121",
                                      "12121212", "21212121", "33333333", "........"], lock=True)
    cv.set_solid(tx0, ty0, tx1, ty1)


def sign(cv, x, y):
    cv.rect(x, y, x + 10, y + 6, 0, T)
    cv.rect(x, y + 5, x + 10, y + 6, 3, T)
    for i in range(1, 9):
        cv.set(x + i, y + 2, 2, T)
    cv.set(x + 2, y + 6, 3, T)
    cv.set(x + 7, y + 6, 3, T)
    cv.set(x + 2, y + 7, 3, T)
    cv.set(x + 7, y + 7, 3, T)
    cv.solid[(y + 6) // 8][x // 8] = 0x0F


def table(cv, tx, ty, w=2, hgt=1, slot=None):
    slot = T if slot is None else slot
    x0, y0, x1, y1 = tx * 8, ty * 8, (tx + w) * 8, (ty + hgt) * 8
    cast_shadow_rect(cv, x0 + 1, y0 + 1, x1 - 1, y1 - 1, dx=2, dy=3)
    for y in range(y0 + 1, y1 - 1):
        for x in range(x0 + 1, x1 - 1):
            edge = y == y1 - 2 or x == x1 - 2
            cv.set(x, y, 3 if edge else (0 if y == y0 + 1 or x == x0 + 1 else 1), slot)
    cv.set_solid(tx, ty, tx + w, ty + hgt)


def stool(cv, x, y, slot=None):
    slot = B if slot is None else slot
    cv.rect(x + 1, y + 1, x + 6, y + 5, 1, slot)
    cv.rect(x + 1, y + 1, x + 6, y + 2, 0, slot)
    cv.rect(x + 1, y + 5, x + 6, y + 6, 3, slot)


# ---------------------------------------------------------------------------
# Tile-efficient woodland and arbitrary-footprint buildings (world scale)
# ---------------------------------------------------------------------------

def _canopy_pattern(crowns=((4, 4, 5.2), (12, 12, 5.2), (12, 3, 4.2), (3, 12, 4.2)), seed=77):
    """16x16 repeating crown pattern -> 4 tiles (lit top-left, dark seams)."""
    out = [[1] * 16 for _ in range(16)]
    for y in range(16):
        for x in range(16):
            best = None
            for cx, cy, r in crowns:
                for ox in (-16, 0, 16):
                    for oy in (-16, 0, 16):
                        dx, dy = x - cx - ox, y - cy - oy
                        d = math.hypot(dx, dy) / r
                        if best is None or d < best[0]:
                            best = (d, dx / r, dy / r)
            d, nx, ny = best
            if d > 1.0:
                out[y][x] = 3
            elif d > 0.82:
                out[y][x] = 3 if (nx + ny) > -0.2 else 2
            else:
                out[y][x] = _sphere_shade(nx, ny, h(x, y, seed) - 0.5)
                if out[y][x] == 1 and h(x, y, seed + 1) > 0.8:
                    out[y][x] = 0
    return out


_CANOPY = _canopy_pattern()
# a second grove pattern (bigger, offset crowns) breaks up long identical rows
_CANOPY2 = _canopy_pattern(((7, 5, 6.0), (1, 13, 4.6), (13, 13, 4.4)), seed=91)


def paint_forest_tiles(cv, mask, base="grass"):
    """mask[ty][tx] True = woodland. Interior uses the 16x16 crown pattern;
    the southern edge shows trunks + shadow, the northern edge rounded tops."""
    H, Wd = len(mask), len(mask[0])
    for ty in range(H):
        for tx in range(Wd):
            if not mask[ty][tx]:
                continue
            north = ty > 0 and mask[ty - 1][tx]
            south = ty < H - 1 and mask[ty + 1][tx]
            rows = []
            for py in range(8):
                row = []
                for px in range(8):
                    pat = _CANOPY2 if ((tx // 6) + (ty // 5)) % 3 == 0 else _CANOPY
                    c = pat[(ty * 8 + py) % 16][(tx * 8 + px) % 16]
                    row.append(str(c))
                rows.append(row)
            if not north:
                # scalloped crown tops: keep only pixels inside rounded bumps
                for px in range(8):
                    gx = tx * 8 + px
                    top = int(2 + 2 * math.cos((gx % 8) / 8 * 2 * math.pi))
                    for py in range(top):
                        rows[py][px] = "."
                    if top < 8:
                        rows[top][px] = "3" if (gx % 8) > 4 else "2"
            if not south:
                # trunks between crowns, shadowed ground strip
                for px in range(8):
                    gx = tx * 8 + px
                    for py in range(5, 8):
                        rows[py][px] = "3" if gx % 8 in (3, 4) else ("2" if py == 5 else ".")
                    if gx % 8 == 3:
                        rows[6][px] = "2"
            cv.blit_tile(tx, ty, G, ["".join(r) for r in rows])
            cv.solid[ty][tx] = 0x0F


def blob_building(cv, cells, style="hostel", roof="flat", doors=(), wall_rows=1, seed=0):
    """Draw a building over an arbitrary set of tiles (tx,ty).

    The southern `wall_rows` tiles of every column become the front wall,
    everything else roof. Roof edges get outline + highlight; the building
    casts its shadow down-right."""
    cells = set(cells)
    doors = set(doors)
    if not cells:
        return
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    # shadow first
    for (tx, ty) in cells:
        for oy in range(8):
            for ox in range(8):
                x, y = tx * 8 + ox + 4, ty * 8 + oy + 4
                if (x // 8, y // 8) not in cells:
                    cv.darken(x, y, 1, GROUND_SLOTS)
    def inside(tx, ty):
        return (tx, ty) in cells

    def is_wall(tx, ty):
        return inside(tx, ty) and any(not inside(tx, ty + k) for k in range(1, wall_rows + 1))

    for (tx, ty) in cells:
        if is_wall(tx, ty):
            below_is_wall_end = not inside(tx, ty + 1)
            if (tx, ty) in doors:
                cv.blit_tile(tx, ty, T, ["33333333", "32222223", "32111123", "32111123",
                                          "32111123", "32110123", "32111123", "32111123"], lock=True)
                continue
            left_edge = not inside(tx - 1, ty)
            right_edge = not inside(tx + 1, ty)
            window = not left_edge and not right_edge and (tx + seed) % 2 == 0
            if window and style != "plain":
                rows = ["33333333", "01111110", "03322330", "03211230", "03322330", "03211230", "01111110",
                        "33333333" if below_is_wall_end else "11111111"]
                if style == "academic":
                    rows = ["33333333", "03333330", "03122130", "03211230", "03122130", "03211230", "03333330",
                            "33333333" if below_is_wall_end else "00000000"]
                cv.blit_tile(tx, ty, R, rows, lock=True)
                continue
            rows = []
            for py in range(8):
                r = []
                for px in range(8):
                    if py == 0 and not is_wall(tx, ty - 1):
                        c = "3"
                    elif py == 7 and below_is_wall_end:
                        c = "3"
                    elif py == 6 and below_is_wall_end:
                        c = "2"
                    elif right_edge and px == 7:
                        c = "3"
                    elif left_edge and px == 0:
                        c = "2"
                    elif style == "academic":
                        c = "2" if (py % 4 == 3 or (px + (py // 4) * 4) % 8 == 7) else "1"
                    elif style == "hostel":
                        c = "0" if (py <= 2 and not is_wall(tx, ty - 1)) else ("2" if py == 7 and not below_is_wall_end else "1")
                    elif style == "mess":
                        c = "2" if py <= 1 else ("0" if py == 2 else "1")
                    else:
                        c = "0" if py <= 3 else "1"
                    r.append(c)
                rows.append("".join(r))
            cv.blit_tile(tx, ty, B, rows, lock=True)
            continue
        # roof tile
        n, e, s, w = (inside(tx, ty - 1), inside(tx + 1, ty), inside(tx, ty + 1), inside(tx - 1, ty))
        interior = n and e and w and inside(tx, ty + 2)
        if roof == "solar" and interior and (tx + ty + seed) % 3 != 0:
            cv.blit_tile(tx, ty, R, ["32222223", "21111112", "21011112", "33333333",
                                      "21111112", "21111112", "21111112", "33333333"], lock=True)
            continue
        slot = B if roof == "tile" else S
        rows = []
        for py in range(8):
            r = []
            for px in range(8):
                if (not n and py == 0) or (not w and px == 0) or (not e and px == 7):
                    c = "3"
                elif (not n and py == 1) or (not w and px == 1):
                    c = "0"
                elif not e and px == 6:
                    c = "2"
                elif roof == "tile":
                    c = "2" if py % 4 == 3 else ("0" if (px + (py // 4) * 2) % 8 == 0 else "1")
                else:
                    c = "2" if h(px, py, 1) > 0.93 else "1"
                r.append(c)
            rows.append("".join(r))
        # rooftop water tank on some hostel roofs
        if roof == "flat" and interior and (tx * 7 + ty * 3 + seed) % 11 == 0:
            rows = rows[:2] + ["11033011", "10333301", "10322301", "11322311"] + rows[6:]
        cv.blit_tile(tx, ty, slot, rows, lock=True)
    for (tx, ty) in cells:
        cv.solid[ty][tx] = 0 if (tx, ty) in doors else 0x0F
