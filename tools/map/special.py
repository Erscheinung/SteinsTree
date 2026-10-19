"""Backgrounds for set-piece scenes: battles, arcade levels and Act 3.

Each function returns (canvas, meta). Collision values follow GB Studio:
0x0F solid, 0x01 "top" (one-way platform for PLATFORM scenes).
"""

import math

import gbc
import interior
import painter as pt
from painter import G, P, S, B, R, W, T


def _fill(cv, code):
    pt.paint_terrain(cv, [[code] * cv.wt for _ in range(cv.ht)])


def battle_pocket():
    """Pocket-monster style battle screen (homage, original art)."""
    cv = gbc.Canvas(20, 18)
    grid = [["lawn" if y > 7 else "grass"] * 20 for y in range(18)]
    for y in range(0, 4):
        grid[y] = ["court"] * 20  # sky band (blue palette)
    pt.paint_terrain(cv, grid)
    # sky: clean gradient using roof palette shades, clouds in shade 0
    for y in range(0, 32):
        for x in range(160):
            cv.set(x, y, 1 if y < 20 else 0, R)
    for cx, cy, r in ((30, 12, 7), (40, 10, 9), (52, 13, 6), (118, 8, 6), (128, 6, 8)):
        for y in range(cy - r, cy + r):
            for x in range(cx - r * 2, cx + r * 2):
                if ((x - cx) / (2 * r)) ** 2 + ((y - cy) / r) ** 2 <= 1:
                    cv.set(x, y, 0, R)
    # far hills
    for x in range(160):
        top = 34 + int(4 * math.sin(x / 13.0) + 3 * math.sin(x / 5.3))
        for y in range(top, 40):
            cv.set(x, y, 2, G)
    # platforms (enemy top-right, player bottom-left)
    for (cx, cy, rx, ry) in ((116, 58, 34, 9), (44, 106, 40, 11)):
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if d <= 1:
                    cv.set(x, y, 3 if d > 0.82 else (1 if y < cy - ry * 0.2 else 2), P)
    return cv, {"kind": "special"}


def battle_zombie():
    cv, _ = interior.build({"floor": "tile", "layout": """
####################
#WWWwWWWNWWWWWwWWWt#
#WWWwWWWWWWWWWwWWWW#
#.TT..T.....TT...T.#
#..................#
#..................#
#..................#
#..................#
#..................#
#..................#
#..................#
#..................#
#..................#
#..................#
#..................#
#..................#
#..................#
####################
"""})
    # blood-dark scuffs on the floor
    for i in range(18):
        x, y = int(pt.h(i, 1, 3) * 150) + 5, int(pt.h(i, 2, 3) * 90) + 40
        cv.rect(x, y, x + 3, y + 2, 2, S)
    return cv, {"kind": "special"}


def lanes_avenue():
    """Parag's lane defence on the hostel avenue: 5 lanes, barricade at left."""
    cv = gbc.Canvas(20, 18)
    grid = [["road"] * 20 for _ in range(18)]
    for lane in range(5):
        y0 = 3 + lane * 3
        for y in range(y0, y0 + 3):
            grid[y] = ["lawn" if lane % 2 == 0 else "grass"] * 20
            grid[y][0] = "paving"
            grid[y][1] = "paving"
            grid[y][18] = "road"
            grid[y][19] = "road"
    pt.paint_terrain(cv, grid)
    pt.blob_building(cv, {(x, y) for x in range(0, 20) for y in range(0, 2)}, style="hostel", wall_rows=1)
    for lane in range(5):
        y = (3 + lane * 3) * 8 + 4
        pt.bush(cv, 0, y, 8, 8, solid=False)
        # chalk lane border (dark seam + lit edge) between lanes
        for x in range(16, 144):
            cv.darken(x, (3 + lane * 3) * 8, 2)
            if (x // 4) % 2 == 0:
                cv.set(x, (3 + lane * 3) * 8 + 1, 0)
    pt.hedge(cv, 0, 2, 20)
    cv.set_solid(0, 0, 20, 3)
    cv.set_solid(0, 18 - 0, 20, 18)
    return cv, {"kind": "special", "lanes_y": [4, 7, 10, 13, 16], "player_x": 2}


def rooftop_run(width=100):
    """Side-view night rooftops for Garvita's platformer run."""
    cv = gbc.Canvas(width, 18)
    _fill(cv, "dark")
    # moon
    for y in range(8, 26):
        for x in range(120, 140):
            if (x - 130) ** 2 + (y - 17) ** 2 <= 81:
                cv.set(x, y, 0 if (x - 127) ** 2 + (y - 15) ** 2 > 20 else 1, S)
    # rooftops: (start tile, width, top row)
    blocks = []
    x = 0
    k = 0
    while x < width:
        w = 6 + int(pt.h(k, 1, 5) * 8)
        top = 10 + int(pt.h(k, 2, 5) * 5)
        if x == 0:
            top, w = 13, 10
        if x + w > width - 8:
            w = width - x
            top = 12
        blocks.append((x, w, top))
        gap = 0 if x + w >= width else 2 + int(pt.h(k, 3, 5) * 2)
        x += w + gap
        k += 1
    for (bx, bw, top) in blocks:
        for ty in range(top, 18):
            for tx in range(bx, min(width, bx + bw)):
                if ty == top:
                    cv.blit_tile(tx, ty, S, ["33333333", "00000000", "11111111", "12111211",
                                             "11111111", "22222222", "33333333", "21212121"], lock=True)
                elif (tx - bx) % 3 == 1 and ty < 17:
                    lit = pt.h(tx, ty, 8) > 0.55
                    cv.blit_tile(tx, ty, R, ["11111111", "13333331", "13" + ("00" if lit else "22") + ("00" if lit else "22") + "31",
                                             "13" + ("00" if lit else "22") * 2 + "31", "13333331",
                                             "11111111", "11111111", "11111111"], lock=True)
                else:
                    cv.blit_tile(tx, ty, B, ["11121112", "11121112", "22222222", "12111211",
                                             "12111211", "22222222", "11121112", "11121112"], lock=True)
                cv.solid[ty][tx] = 0x0F
        # rooftop props: water tank and solar rack (also platforms)
        if bw >= 8:
            tx = bx + bw // 2
            for ty in (top - 2, top - 1):
                cv.blit_tile(tx, ty, S, ["00111100", "01111110", "01111112", "01111112",
                                         "01111112", "01111112", "02222220", "03000030"], lock=True)
                cv.solid[ty][tx] = 0x0F
    # goal: the Dome's lantern at the far right
    pt.dome(cv, (width - 4) * 8, 11 * 8, 22)
    return cv, {"kind": "special", "blocks": blocks}


def void_stars():
    cv = gbc.Canvas(20, 18)
    _fill(cv, "dark")
    return cv, {"kind": "special"}


def flight_sky(width=120):
    """SHMUP: flying to London. Sky, clouds, and the skyline at the end."""
    cv = gbc.Canvas(width, 18)
    for ty in range(18):
        for tx in range(width):
            cv.blit_tile(tx, ty, R, [("2" if ty < 5 else "1" if ty < 12 else "0") * 8] * 8)
    for i in range(40):
        cx, cy, r = int(pt.h(i, 1, 6) * width * 8), 10 + int(pt.h(i, 2, 6) * 120), 4 + int(pt.h(i, 3, 6) * 7)
        for y in range(cy - r, cy + r):
            for x in range(cx - 2 * r, cx + 2 * r):
                if ((x - cx) / (2 * r)) ** 2 + ((y - cy) / r) ** 2 <= 1:
                    cv.set(x, y, 0 if y < cy else (0 if (x + y) % 5 else 1), R)
    # London skyline: Big Ben + roofs, last 30 tiles
    base = 14 * 8
    sx = (width - 30) * 8
    for x in range(sx, width * 8):
        top = base - 10 - int(6 * abs(math.sin(x / 9.0)))
        for y in range(top, 144):
            cv.set(x, y, 3, R)
    bx = (width - 18) * 8
    for y in range(40, 144):
        for x in range(bx, bx + 12):
            cv.set(x, y, 3, R)
    for y in range(28, 40):
        for x in range(bx + 3 + (40 - y) // 4, bx + 9 - (40 - y) // 4):
            cv.set(x, y, 3, R)
    for y in range(52, 62):
        for x in range(bx + 2, bx + 10):
            if (x - bx - 6) ** 2 + (y - 57) ** 2 <= 16:
                cv.set(x, y, 0, R)
    return cv, {"kind": "special"}


def london_street():
    """Top-down rainy London terrace street (memory)."""
    cv = gbc.Canvas(40, 18)
    grid = [["paving"] * 40 for _ in range(18)]
    for y in range(8, 12):
        grid[y] = ["road"] * 40
    pt.paint_terrain(cv, grid)
    for i in range(0, 40, 8):
        pt.blob_building(cv, {(x, y) for x in range(i, i + 7) for y in range(0, 6)}, style="academic",
                         roof="tile", wall_rows=2, doors={(i + 3, 5)}, seed=i)
        pt.blob_building(cv, {(x, y) for x in range(i, i + 7) for y in range(13, 18)}, style="hostel",
                         roof="tile", wall_rows=1, seed=i + 1)
    # red phone box and a bus
    cv.rect(17 * 8 + 1, 6 * 8 + 1, 17 * 8 + 7, 7 * 8 + 7, 2, B)
    cv.rect(17 * 8 + 2, 6 * 8 + 2, 17 * 8 + 6, 6 * 8 + 6, 0, B)
    cv.solid[6][17] = cv.solid[7][17] = 0x0F
    for y in range(8 * 8 + 6, 10 * 8 + 2):
        for x in range(26 * 8, 33 * 8):
            edge = y in (8 * 8 + 6, 10 * 8 + 1) or x in (26 * 8, 33 * 8 - 1)
            cv.set(x, y, 3 if edge else (0 if (x // 4) % 2 and y < 9 * 8 + 4 else 2), B)
    # puddles
    for i in range(10):
        x, y = int(pt.h(i, 7, 1) * 300) + 8, 8 * 8 + int(pt.h(i, 8, 1) * 28)
        cv.rect(x, y, x + 6, y + 2, 0, S)
    return cv, {"kind": "special"}


def childhood_school():
    """Autumn school courtyard (memory palette at runtime)."""
    cv = gbc.Canvas(32, 24)
    grid = [["grass"] * 32 for _ in range(24)]
    for y in range(10, 14):
        grid[y] = ["dirt"] * 32
    for y in range(14, 24):
        for x in range(12, 20):
            grid[y][x] = "dirt"
    pt.paint_terrain(cv, grid)
    pt.blob_building(cv, {(x, y) for x in range(2, 30) for y in range(0, 7)}, style="hostel", roof="tile",
                     wall_rows=2, doors={(15, 6), (16, 6)})
    for x in (2, 6, 24, 28):
        pt.tree(cv, x * 8, 15 * 8, 24, kind=x % 3)
    for x in (3, 9, 21, 26):
        pt.bush(cv, x * 8, 8 * 8, 8, 7)
    pt.bench(cv, 9 * 8, 18 * 8)
    pt.bench(cv, 21 * 8, 18 * 8)
    # fallen leaves (light flecks on the path)
    for i in range(60):
        x, y = int(pt.h(i, 1, 2) * 256), 80 + int(pt.h(i, 2, 2) * 110)
        if cv.tile_slot(x // 8, y // 8) == P:
            cv.set(x, y, 0)
    return cv, {"kind": "special"}


def home_india():
    cv, _ = interior.build({"floor": "tile", "alt_floor": "carpet", "layout": """
######################
#WWwWWWXWWWWWwWWWWtWW#
#WWwWWWWWWWWWwWWWWWWW#
#S...,,,,,,,,,......S#
#S...,,TTTT,,,..cc..S#
#....,,cccc,,,......p#
#....,,,,,,,,,.......#
#bb..................#
#bb.........C.CC.....#
#p...................#
##########DD##########
"""})
    return cv, {"kind": "special"}


def orbits():
    """Concentric unstable orbits (11th grade). Palette cycling animates it."""
    cv = gbc.Canvas(20, 18)
    _fill(cv, "dark")
    cx, cy = 80, 72
    for y in range(144):
        for x in range(160):
            dx, dy = x - cx, (y - cy) * 1.25
            r = math.hypot(dx, dy)
            a = math.atan2(dy, dx)
            band = int((r + 9 * math.sin(a * 3 + r / 14.0)) / 7)
            if r < 70:
                cv.set(x, y, band % 4, R if band % 2 else B)
    return cv, {"kind": "special"}


def corridor12(width=64):
    """Low-ceilinged corridor for 12th grade: you can't fly too high."""
    cv = gbc.Canvas(width, 18)
    _fill(cv, "dark")
    for tx in range(width):
        ceil = 7 + (2 if (tx // 9) % 3 == 1 else 0)
        for ty in range(0, ceil):
            cv.blit_tile(tx, ty, S, ["22222222", "21212121", "22222222", "12121212"] * 2, lock=True)
            cv.solid[ty][tx] = 0x0F
        for ty in range(15, 18):
            cv.blit_tile(tx, ty, S, ["33333333", "00000000", "11111111", "11211121",
                                     "11111111", "22222222", "22222222", "33333333"], lock=True)
            cv.solid[ty][tx] = 0x0F
        if tx % 6 == 0:
            for ty in range(ceil, 15):
                cv.blit_tile(tx, ty, R, ["13333331", "13000031", "13000031", "13000031",
                                         "13000031", "13000031", "13000031", "13333331"])
    return cv, {"kind": "special"}


def day_card():
    """Persona-style calendar card: date panel + weather, text drawn by events."""
    cv = gbc.Canvas(20, 18)
    _fill(cv, "dark")
    for ty in range(2, 13):
        for tx in range(2, 18):
            cv.blit_tile(tx, ty, S, ["00000000"] * 8)
    for tx in range(2, 18):
        cv.blit_tile(tx, 2, B, ["33333333", "11111111", "11111111", "11111111",
                                "11111111", "11111111", "22222222", "33333333"])
    for ty in range(2, 13):
        cv.set(2 * 8, ty * 8, 3, None)
    # torn edge at the bottom of the page
    for x in range(16, 144):
        for y in range(13 * 8 - 3 + (x // 3) % 3, 13 * 8):
            cv.set(x, y, 3)
    # sun icon
    for y in range(28, 44):
        for x in range(120, 136):
            if (x - 128) ** 2 + (y - 36) ** 2 <= 25:
                cv.set(x, y, 1, S)
    return cv, {"kind": "special"}


def hall_of_doors():
    cv, _ = interior.build({"floor": "stone", "alt_floor": "carpet", "layout": """
############################
#QWWQWWQWWQWWQWWQWWQWWQWWQW#
#WWWWWWWWWWWWWWWWWWWWWWWWWW#
#,,,,,,,,,,,,,,,,,,,,,,,,,,#
#,o,,,,o,,,,,o,,,,,o,,,,,o,#
#,,,,,,,,,,,,,,,,,,,,,,,,,,#
#,,,,,,,,,,,,,,,,,,,,,,,,,,#
#,o,,,,o,,,,,o,,,,,o,,,,,o,#
#,,,,,,,,,,,,,,,,,,,,,,,,,,#
#,,,,,,,,,,,,,,,,,,,,,,,,,,#
#############DD#############
"""})
    return cv, {"kind": "special"}


def flower_field():
    """Evening field with a bench: Muskaan's recurring theme."""
    cv = gbc.Canvas(32, 20)
    grid = [["flowers" if (x * 7 + y * 3) % 5 else "grass" for x in range(32)] for y in range(20)]
    for y in range(9, 11):
        grid[y] = ["dirt"] * 32
    pt.paint_terrain(cv, grid)
    pt.tree(cv, 4 * 8, 2 * 8, 24, kind=1)
    pt.tree(cv, 24 * 8, 12 * 8, 24, kind=2)
    pt.bench(cv, 15 * 8, 7 * 8)
    return cv, {"kind": "special"}


SPECIALS = {
    "battle_pocket": battle_pocket,
    "battle_zombie": battle_zombie,
    "lanes_avenue": lanes_avenue,
    "rooftop_run": rooftop_run,
    "void_stars": void_stars,
    "flight_sky": flight_sky,
    "london_street": london_street,
    "childhood_school": childhood_school,
    "home_india": home_india,
    "orbits": orbits,
    "corridor12": corridor12,
    "day_card": day_card,
    "hall_of_doors": hall_of_doors,
    "flower_field": flower_field,
}
