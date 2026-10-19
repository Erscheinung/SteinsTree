"""Interior rooms from ASCII layouts (one character per 8x8 tile).

Legend (edit layouts in maps_local.py; every char is one tile):
  ' ' void (outside the room, solid black)
  '#' wall top (solid)            'W' wall face (solid)    'w' window in wall face
  'B' blackboard on wall face     'N' notice board         'D' door / exit (walkable)
  '.' floor                       ',' rug / alt floor      '=' stairs (walkable)
  'd' student desk (solid)        'c' chair / stool        'P' lectern
  'T' table (solid)               'C' counter (solid)      'S' shelf / bookcase
  'L' lab bench (solid)           'F' fume hood            'M' machine (lathe)
  'V' vice / saw bench            'b' bed                  'p' potted plant
  'o' pillar                      '~' water (pool)         '_' pool edge / coping
  'H' handheld console glow       'X' poster / frame       't' TV / monitor
  'Q' closed door in a wall face (decorative, solid)
"""

import gbc
import owner
import painter as pt
from painter import G, P, S, B, R, W, T

FLOORS = {"wood": ("floor_wood", T), "tile": ("floor_tile", S), "lab": ("floor_lab", S),
          "carpet": ("floor_carpet", B), "stone": ("paving", S), "sand": ("sand", P)}

SOLID = set("#WwBNdTCSLFMVbpo~XtHPQ")
WALKABLE_OVER = set(".,=Dc_ ")


def build(spec):
    rows = [r.rstrip("\n") for r in spec["layout"].strip("\n").split("\n")]
    wt = max(len(r) for r in rows)
    rows = [r.ljust(wt) for r in rows]
    # GB Studio scenes must fill the 20x18-tile screen: pad with void
    if wt < 20:
        lpad = (20 - wt) // 2
        rows = [" " * lpad + r + " " * (20 - wt - lpad) for r in rows]
        wt = 20
    if len(rows) < 18:
        top = (18 - len(rows)) // 2
        rows = [" " * wt] * top + rows + [" " * wt] * (18 - len(rows) - top)
    ht = len(rows)
    floor_code, floor_slot = FLOORS[spec.get("floor", "wood")]
    alt_code = FLOORS[spec.get("alt_floor", "carpet")][0]
    wall_slot = spec.get("wall_slot", B)
    cv = gbc.Canvas(wt, ht)
    terrain = [[floor_code] * wt for _ in range(ht)]
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == ",":
                terrain[y][x] = alt_code
            elif ch == " ":
                terrain[y][x] = "void"
            elif ch in "~":
                terrain[y][x] = "water"
            elif ch == "_":
                terrain[y][x] = "paving"
    pt.paint_terrain(cv, terrain)
    patches = spec.get("owner_patches", owner.INTERIOR_PATCHES.get(spec.get("name"), []))
    # Furniture and wall symbols are painted afterwards and may legitimately
    # claim their own palette slot over a floor patch.
    owner._apply_patches(cv, [dict(patch, lock=False) for patch in patches])
    doors = []
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            X, Y = x * 8, y * 8
            if ch == "#":
                cv.blit_tile(x, y, wall_slot, ["33333333", "32222223", "32222223", "32222223",
                                                "32222223", "32222223", "32222223", "33333333"]
                             if rows[min(ht - 1, y + 1)][x] == "#" or y == ht - 1 else
                             ["33333333", "32222223", "32222223", "32222223", "32222223", "32222223",
                              "33333333", "33333333"], lock=True)
            elif ch in "WBNXtQ":
                above_face = y > 0 and rows[y - 1][x] in "WwBNXtQ"
                base = ["11111111" if above_face else "00000000", "00000000" if not above_face else "11111111",
                        "11111111", "11111111", "11111111", "11111111", "22222222", "33333333"]
                if y + 1 < ht and rows[y + 1][x] in "WwBNXtQ":
                    base[6], base[7] = "11111111", "11111111"
                cv.blit_tile(x, y, wall_slot, base, lock=True)
                if ch == "B":
                    cv.blit_tile(x, y, G, ["33333333", "32222223", "32202223", "32022023",
                                           "32222203", "32220223", "33333333", "11111111"], lock=True)
                elif ch == "N":
                    cv.blit_tile(x, y, T, ["33333333", "30010103", "31000003", "30101003",
                                           "30000103", "31010003", "33333333", "22222222"], lock=True)
                elif ch == "X":
                    cv.blit_tile(x, y, R, ["33333333", "30000003", "30122103", "30211203",
                                           "30122103", "30000003", "33333333", "00000000"], lock=True)
                elif ch == "Q":
                    cv.blit_tile(x, y, T, ["33333333", "32222223", "32111123", "32111123",
                                           "32111023", "32111123", "32111123", "33333333"], lock=True)
                elif ch == "t":
                    cv.blit_tile(x, y, S, ["33333333", "32222223", "32111123", "32111123",
                                           "32111123", "33333333", "00333300", "00000000"], lock=True)
            elif ch == "w":
                cv.blit_tile(x, y, R, ["33333333", "30000003", "30122103", "30211203",
                                       "30122103", "30211203", "30000003", "33333333"], lock=True)
            elif ch == "D":
                doors.append({"x": x, "y": y})
                cv.blit_tile(x, y, T, ["22222222", "21111112", "21111112", "21111112",
                                       "21111112", "21111112", "21111112", "22222222"])
            elif ch == "=":
                pt.stairs(cv, x, y, 1, 1)
            elif ch == "d":
                pt.cast_shadow_rect(cv, X + 1, Y + 2, X + 8, Y + 6, dx=2, dy=2)
                cv.rect(X, Y + 1, X + 8, Y + 6, 1, T)
                cv.rect(X, Y + 1, X + 8, Y + 2, 0, T)
                cv.rect(X, Y + 5, X + 8, Y + 6, 3, T)
                cv.set(X + 1, Y + 6, 3, T)
                cv.set(X + 6, Y + 6, 3, T)
                if x % 2 == 0:
                    cv.rect(X + 2, Y + 2, X + 5, Y + 4, 0, T)   # notebook
            elif ch == "c":
                pt.stool(cv, X, Y + 1)
            elif ch == "P":
                cv.rect(X + 1, Y, X + 7, Y + 7, 1, T)
                cv.rect(X + 1, Y, X + 7, Y + 2, 0, T)
                cv.rect(X + 1, Y + 6, X + 7, Y + 7, 3, T)
            elif ch == "T":
                cv.rect(X, Y + 1, X + 8, Y + 7, 1, T)
                cv.rect(X, Y + 1, X + 8, Y + 2, 0, T)
                cv.rect(X, Y + 6, X + 8, Y + 7, 3, T)
                if (x + y) % 3 == 0:
                    cv.rect(X + 2, Y + 3, X + 6, Y + 5, 0, T)   # steel thali
                    cv.set(X + 3, Y + 4, 2, T)
            elif ch == "C":
                cv.rect(X, Y, X + 8, Y + 8, 1, S)
                cv.rect(X, Y, X + 8, Y + 2, 0, S)
                cv.rect(X, Y + 7, X + 8, Y + 8, 3, S)
                if x % 2:
                    cv.rect(X + 2, Y + 2, X + 6, Y + 5, 2, S)   # steam tray
            elif ch == "S":
                for k in range(8):
                    cv.set(X + k, Y, 3, T)
                    cv.set(X + k, Y + 7, 3, T)
                for yy in (1, 4):
                    for k in range(8):
                        cv.set(X + k, Y + yy + 2, 2, T)
                    for k in range(0, 8, 2):
                        cv.set(X + k, Y + yy, (k // 2) % 3, T)
                        cv.set(X + k, Y + yy + 1, (k // 2 + 1) % 3, T)
            elif ch == "L":
                cv.rect(X, Y + 1, X + 8, Y + 8, 1, S)
                cv.rect(X, Y + 1, X + 8, Y + 2, 0, S)
                cv.rect(X, Y + 7, X + 8, Y + 8, 3, S)
                if x % 2 == 0:
                    cv.rect(X + 3, Y + 2, X + 5, Y + 5, 0, S)   # flask
                    cv.set(X + 3, Y + 4, 2, S)
            elif ch == "F":
                cv.rect(X, Y, X + 8, Y + 8, 2, S)
                cv.rect(X + 1, Y + 1, X + 7, Y + 5, 0, S)
                cv.rect(X, Y + 7, X + 8, Y + 8, 3, S)
            elif ch == "M":
                cv.rect(X, Y + 1, X + 8, Y + 8, 2, S)
                cv.rect(X + 1, Y + 2, X + 7, Y + 4, 1, S)
                cv.rect(X + 2, Y + 5, X + 6, Y + 6, 0, S)
                cv.rect(X, Y + 7, X + 8, Y + 8, 3, S)
            elif ch == "V":
                cv.rect(X, Y + 2, X + 8, Y + 7, 1, T)
                cv.rect(X, Y + 2, X + 8, Y + 3, 0, T)
                for k in range(1, 7):
                    cv.set(X + k, Y + 4, 3 if k % 2 else 2, T)   # saw teeth
                cv.rect(X, Y + 7, X + 8, Y + 8, 3, T)
            elif ch == "b":
                cv.rect(X, Y, X + 8, Y + 8, 0, B)
                cv.rect(X, Y, X + 8, Y + 3, 1, B)
                cv.rect(X, Y + 7, X + 8, Y + 8, 3, B)
            elif ch == "p":
                pt.bush(cv, X, Y, 8, 6, solid=False)
                cv.rect(X + 2, Y + 6, X + 6, Y + 8, 3, G)
            elif ch == "o":
                cv.rect(X + 1, Y, X + 7, Y + 8, 1, S)
                cv.rect(X + 1, Y, X + 3, Y + 8, 0, S)
                cv.rect(X + 6, Y, X + 7, Y + 8, 2, S)
            elif ch == "H":
                cv.rect(X + 1, Y + 1, X + 7, Y + 7, 3, R)
                cv.rect(X + 2, Y + 2, X + 6, Y + 5, 0, R)
                cv.set(X + 3, Y + 6, 1, R)
            if ch in SOLID:
                cv.solid[y][x] = 0x0F
            if ch == " ":
                cv.solid[y][x] = 0x0F
    for fn in spec.get("decorate", []):
        fn(cv)
    if patches:
        cv.owner_source_patches = patches
    return cv, doors
