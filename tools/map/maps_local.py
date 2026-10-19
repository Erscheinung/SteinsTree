"""Every local map of the campus: exteriors (cut from OSM) and interiors.

Edit a spec, then run:  python3 tools/map/build_maps.py [name ...]

Exterior spec keys: center (lat, lon) or center_m (rotated metres), cols, rows,
cell (metres per tile), doors [{label, target, latlon|tile, building?}],
rings, add_buildings, skip_buildings, terrain_fns, decorate, woods, wall_rows.
Interior spec keys: layout (ASCII, see interior.py), floor, alt_floor.
"""

import osm
import painter as pt
from world import RINGS

AB1_RING = [r for r in RINGS if r[0] == "Academic Block 1"]
AB2_RING = [r for r in RINGS if r[0] == "Academic Block 2"]


def trails_to_dirt(terrain, ctx):
    for row in terrain:
        for i, t in enumerate(row):
            if t == "paving":
                row[i] = "dirt"


def avenue_trees(cv, ctx, terrain):
    """Rain trees along both kerbs of the GHS hostel avenue."""
    for r in range(2, cv.ht - 3):
        for c in range(1, cv.wt - 3, 3):
            if terrain[r][c] == "road" and terrain[r - 1][c] in ("grass", "lawn", "scrub") and \
                    terrain[r - 2][c] in ("grass", "lawn", "scrub") and not cv.solid[r - 2][c] and \
                    not cv.solid[r - 2][c + 1]:
                pt.tree(cv, c * 8, (r - 3) * 8 + 4, 16, kind=c % 3)


def amphitheatre(cv, ctx, terrain):
    c, r = ctx.tile(26.8432, 75.5662)
    for i in range(5):
        y = r - 3 + i
        for x in range(c - 6 + i, c + 7 - i):
            cv.blit_tile(x, y, pt.S, ["00000000", "11111111", "11111111", "11111111",
                                       "22222222", "22222222", "33333333", "11111111"], lock=True)
    for x in range(c - 2, c + 3):
        for y in (r + 3, r + 4):
            cv.blit_tile(x, y, pt.T, ["00000000", "11111111", "11111111", "11211121",
                                       "11111111", "11211121", "22222222", "33333333"], lock=True)
            cv.solid[y][x] = 0


def dome_top(cv, ctx, terrain):
    c, r = ctx.tile(26.84173, 75.56584)
    pt.dome(cv, c * 8 + 4, r * 8, 30)


def flagpole(cv, ctx, terrain):
    c, r = ctx.tile(26.84095, 75.56613)
    for y in range(r * 8 - 22, r * 8 + 6):
        cv.set(c * 8 + 3, y, 3, pt.S)
    cv.rect(c * 8 + 4, r * 8 - 22, c * 8 + 12, r * 8 - 17, 1, pt.B)
    cv.solid[r][c] = 0x0F


def staircase(cv, ctx, terrain):
    c, r = ctx.tile(26.8425, 75.5654)
    pt.stairs(cv, c - 8, r - 3, 16, 7)


def cricket_pitch(cv, ctx, terrain):
    c, r = ctx.tile(26.8455, 75.5642)
    for y in range(r - 5, r + 5):
        for x in (c, c + 1):
            cv.blit_tile(x, y, pt.P, ["00000000"] * 8)
    for x in (c, c + 1):
        for y in (r - 5, r + 4):
            cv.blit_tile(x, y, pt.P, ["00000000", "33333333", "00000000", "03030300",
                                      "03030300", "00000000", "00000000", "00000000"])


def pool_lanes(cv, ctx, terrain):
    pass


EXTERIORS = [
    {"name": "hostel_avenue", "title": "GHS Hostel Avenue", "center_m": (-120, 62), "cols": 76, "rows": 34,
     "cell": 3.0, "decorate": [avenue_trees], "wall_rows": 2,
     "doors": [
         {"label": "Quess Mess", "target": "quess_mess_in", "latlon": (26.8413, 75.5615), "snap": 12},
         {"label": "BlueDove Mess", "target": "bluedove_in", "latlon": (26.8404, 75.5618), "snap": 12},
         {"label": "B1 Block", "target": "block1", "latlon": (26.8419, 75.5629), "snap": 14},
     ]},
    {"name": "b7_courts", "title": "B7 Courts", "center_m": (-215, -50), "cols": 48, "rows": 40, "cell": 2.0,
     "doors": [{"label": "B7 Boy's Block", "target": "LEGACY_B7_ENTRANCE", "latlon": (26.8419, 75.5612), "snap": 20}]},
    {"name": "scrub_trail", "title": "Scrub Trail behind B7", "center_m": (-140, -235), "cols": 64, "rows": 56,
     "cell": 2.5, "terrain_fns": [trails_to_dirt]},
    {"name": "block1", "title": "Block 1 (B1)", "center_m": (-52, 4), "cols": 44, "rows": 60, "cell": 2.0,
     "doors": [{"label": "B1 Lobby", "target": "hostel_corridor", "latlon": (26.8416, 75.5629), "snap": 20}]},
    {"name": "block2", "title": "Block 2 (B2)", "center_m": (-78, -42), "cols": 54, "rows": 48, "cell": 2.0,
     "doors": [{"label": "B2 Lobby", "target": "hostel_corridor", "latlon": (26.8420, 75.5626), "snap": 20}]},
    {"name": "girls_blocks", "title": "Girls' Blocks G1-G4", "center_m": (-130, 132), "cols": 72, "rows": 42,
     "cell": 2.5,
     "doors": [{"label": "BlueDove Mess", "target": "bluedove_in", "latlon": (26.8404, 75.5618), "snap": 14}]},
    {"name": "pool", "title": "Ocean Hills Pool", "center_m": (-197, 196), "cols": 40, "rows": 34, "cell": 2.0,
     "doors": [{"label": "Pool Hall", "target": "pool_in", "latlon": (26.8398, 75.5621), "snap": 16}]},
    {"name": "underpass", "title": "Hostel Gate & Underpass", "center_m": (8, 34), "cols": 48, "rows": 44,
     "cell": 2.0,
     "doors": [{"label": "Underpass (hostel side)", "target": "underpass_tunnel", "tile": (12, 6), "snap": 30},
               {"label": "Underpass (university side)", "target": "underpass_tunnel", "tile": (30, 2), "snap": 30}]},
    {"name": "dome", "title": "The Dome - Administrative Block", "center_m": (224, 135), "cols": 68, "rows": 48,
     "cell": 3.0, "decorate": [dome_top, flagpole], "wall_rows": 3,
     "doors": [{"label": "Dome Rotunda", "target": "dome_in", "latlon": (26.84150, 75.56590),
                "building": "Administrative Block", "snap": 20}]},
    {"name": "ab1", "title": "Academic Block 1", "center": (26.8426, 75.5645), "cols": 64, "rows": 70, "cell": 2.5,
     "rings": AB1_RING, "wall_rows": 3,
     "doors": [{"label": "AB1 Classroom 101", "target": "physics_class", "latlon": (26.84195, 75.5647), "snap": 20}]},
    {"name": "ab2", "title": "Academic Block 2 & Amphitheatre", "center": (26.8432, 75.5662), "cols": 64,
     "rows": 70, "cell": 2.5, "rings": AB2_RING, "decorate": [amphitheatre], "wall_rows": 3,
     "doors": [{"label": "AB2 Room 214", "target": "maths_class", "latlon": (26.84265, 75.5664), "snap": 20}]},
    {"name": "grand_staircase", "title": "Old Mess & Grand Staircase", "center_m": (212, -30), "cols": 44,
     "rows": 60, "cell": 2.5, "decorate": [staircase], "wall_rows": 3,
     "doors": [{"label": "Old Mess", "target": "old_mess_in", "latlon": (26.8430, 75.5653), "snap": 20}]},
    {"name": "ab3", "title": "Academic Block 3 & Labs", "center_m": (128, -195), "cols": 52, "rows": 64,
     "cell": 2.5, "wall_rows": 3,
     "doors": [{"label": "Chemistry Lab", "target": "chem_lab", "latlon": (26.8436, 75.5641), "snap": 20}]},
    {"name": "workshop", "title": "Workshop Building", "center_m": (392, -78), "cols": 44, "rows": 54,
     "cell": 2.0, "wall_rows": 3,
     "doors": [{"label": "Workshop Floor", "target": "workshop_in", "latlon": (26.8432, 75.5669), "snap": 20}]},
    {"name": "cricket_ground", "title": "Cricket Ground", "center": (26.8455, 75.5642), "cols": 64, "rows": 62,
     "cell": 3.0, "decorate": [cricket_pitch], "woods": False},
    {"name": "nbc", "title": "NBC Food Court & BABA", "center_m": (40, -190), "cols": 44, "rows": 52, "cell": 2.5,
     "skip_buildings": ["NBC"],
     "add_buildings": [{"name": "NBC stall", "tile": (14, 20), "size": (6, 4), "style": "mess", "roof": "tile"},
                       {"name": "BABA stall", "tile": (24, 30), "size": (5, 4), "style": "mess", "roof": "tile"},
                       {"name": "Juice stall", "tile": (14, 36), "size": (4, 3), "style": "mess", "roof": "tile"}]},
]

# ---------------------------------------------------------------------------
# Interiors. Rows must be equal length; one char = one 8x8 tile.
# ---------------------------------------------------------------------------

INTERIORS = [
    {"name": "physics_class", "title": "AB1-101: Engineering Physics", "floor": "tile", "layout": """
########################
#WWWwWBBBBBBBBBBWwWWWWX#
#WWWwWBBBBBBBBBBWwWWWWW#
#..........P...........#
#......................#
#.dd.dd.dd.dd..dd.dd.dd#
#.cc.cc.cc.cc..cc.cc.cc#
#......................#
#.dd.dd.dd.dd..dd.dd.dd#
#.cc.cc.cc.cc..cc.cc.cc#
#......................#
#.dd.dd.dd.dd..dd.dd.dd#
#.cc.cc.cc.cc..cc.cc.cc#
#......................#
#p....................p#
###########DD###########
"""},
    {"name": "maths_class", "title": "AB2-214: Engineering Mathematics", "floor": "wood", "layout": """
########################
#WNWWwWBBBBBBBBBBBWwWWW#
#WWWWwWBBBBBBBBBBBWwWWW#
#.P....................#
#......................#
#.dddd.dddd.dddd.dddd..#
#.cccc.cccc.cccc.cccc..#
#......................#
#.dddd.dddd.dddd.dddd..#
#.cccc.cccc.cccc.cccc..#
#......................#
#.dddd.dddd.dddd.dddd..#
#.cccc.cccc.cccc.cccc..#
#......................#
#S....................p#
###DD###################
"""},
    {"name": "chem_lab", "title": "AB3 Chemistry Lab", "floor": "lab", "layout": """
########################
#WWFFWWwWWNWWwWWBBBBWWW#
#WWFFWWwWWWWWwWWBBBBWWW#
#......................#
#.LLLLLL....LLLLLL.....#
#.cccccc....cccccc...P.#
#......................#
#.LLLLLL....LLLLLL.....#
#.cccccc....cccccc.....#
#......................#
#.LLLLLL....LLLLLL..SS.#
#.cccccc....cccccc.....#
#......................#
#p...................p.#
##########DD############
"""},
    {"name": "workshop_in", "title": "Workshop: Fitting, Carpentry & Welding", "floor": "stone", "layout": """
##########################
#WWwWWWWwWWWNWWWWwWWWWwWW#
#WWwWWWWwWWWWWWWWwWWWWwWW#
#........................#
#.MM.MM.MM......VV.VV.VV.#
#........................#
#.MM.MM.MM......VV.VV.VV.#
#........................#
#,,,,,,,,,......LLLL.....#
#,,,,P,,,,......cccc.....#
#,,,,,,,,,...............#
#.SS.................TTT.#
#........................#
###########DD#############
""", "alt_floor": "sand"},
    {"name": "quess_mess_in", "title": "Quess Mess", "floor": "tile", "layout": """
##########################
#WWWwWWWNWWWWWWWWWWwWWWtW#
#WWWwWWWWWWWWWWWWWWwWWWWW#
#.CCCCCCCCCCCC...........#
#........................#
#.cTTTTc..cTTTTc..cTTTTc.#
#.cTTTTc..cTTTTc..cTTTTc.#
#........................#
#.cTTTTc..cTTTTc..cTTTTc.#
#.cTTTTc..cTTTTc..cTTTTc.#
#........................#
#.cTTTTc..cTTTTc..cTTTTc.#
#........................#
#p......................p#
###########DD#############
"""},
    {"name": "bluedove_in", "title": "BlueDove Mess", "floor": "carpet", "alt_floor": "tile", "layout": """
######################
#WWwWWNWWWWWwWWWWWtWW#
#WWwWWWWWWWWwWWWWWWWW#
#,CCCCCCCC,,,,,,,,,,,#
#,,,,,,,,,,,,,,,,,,,,#
#,cTTc,,cTTc,,cTTc,,,#
#,cTTc,,cTTc,,cTTc,,,#
#,,,,,,,,,,,,,,,,,,,,#
#,cTTc,,cTTc,,cTTc,,p#
#,,,,,,,,,,,,,,,,,,,,#
#########DD###########
"""},
    {"name": "old_mess_in", "title": "Old Mess Food Court", "floor": "tile", "layout": """
##########################
#WWWwWWNWWWWWwWWWWWWtWWWW#
#WWWwWWWWWWWWwWWWWWWWWWWW#
#CCCC....CCCC....CCCC....#
#........................#
#..cTTc....cTTc....cTTc..#
#..cTTc....cTTc....cTTc..#
#........................#
#..cTTc....cTTc....cTTc..#
#..cTTc....cTTc....cTTc..#
#o......................o#
###########DD#############
"""},
    {"name": "dome_in", "title": "Dome Rotunda & Central Library", "floor": "stone", "alt_floor": "carpet",
     "layout": """
############################
#WWWWSSSSWWWWwwWWWWSSSSWWWW#
#WWWWSSSSWWWWwwWWWWSSSSWWWW#
#....,,,,..........,,,,....#
#.o..,,,,..o....o..,,,,..o.#
#....,TT,..........,TT,....#
#....,cc,..,,,,,,..,cc,....#
#.........,,,,,,,,.........#
#.o.......,,,,,,,,.......o.#
#.........,,,,,,,,.........#
#....,,,,..,,,,,,..,,,,....#
#....,TT,..........,TT,....#
#.o..,cc,..o....o..,cc,..o.#
#p........................p#
#############DD#############
"""},
    {"name": "pool_in", "title": "Ocean Hills Pool Hall", "floor": "tile", "layout": """
##########################
#WWwWWWWwWWWWNWWWWwWWWWwW#
#WWwWWWWwWWWWWWWWWwWWWWwW#
#........................#
#.______________________.#
#._~~~~~~~~~~~~~~~~~~~~_.#
#._~~~~~~~~~~~~~~~~~~~~_.#
#._~~~~~~~~~~~~~~~~~~~~_.#
#._~~~~~~~~~~~~~~~~~~~~_.#
#._~~~~~~~~~~~~~~~~~~~~_.#
#.______________________.#
#p..cc..cc.......cc..cc.p#
###########DD#############
"""},
    {"name": "underpass_tunnel", "title": "The Underpass", "floor": "stone", "alt_floor": "tile", "layout": """
################################
#WWWWXWWWWWWWWWXWWWWWWWWWXWWWWW#
#WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW#
D..............................D
D,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,D
D..............................D
#WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW#
################################
"""},
    {"name": "hostel_corridor", "title": "Hostel Corridor", "floor": "tile", "alt_floor": "carpet", "layout": """
##############################
#WWQWWWQWWWQWWWQWWWQWWWQWWwWW#
#WWWWWWWWWWWWWWWWWWWWWWWWWwWW#
#,,,,,,,,,,,,,,,,,,,,,,,,,,,,#
#,,,,,,,,,,,,,,,,,,,,,,,,,,,,#
#WWQWWWQWWWQWW..WWWQWWW==WWWW#
##############DD##############
"""},
    {"name": "prologue_bedroom", "title": "Bedroom, 2009", "floor": "wood", "alt_floor": "carpet", "layout": """
####################
#WWwWWWXWWWWWwWWWtW#
#WWwWWWWWWWWWwWWWWW#
#bb.......,,,,,,..S#
#bb.......,,,,,,..S#
#.........,,H,,,...#
#.........,,,,,,...#
#..T..............p#
#..c...............#
#p.................#
#########DD#########
"""},
]
