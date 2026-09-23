"""Pixel data for the After Hours test sprite pack (16x16 frames).

Glyphs: '.' transparent key, 'o' light, '+' middle, '#' dark.
Base poses are literal 16x16 grids; variants are built with `patch` (replace
whole rows) and `shift_rows` (move a band of rows up/down) so every frame stays
readable here. Everything is a visual interpretation of existing dialogue, not
story canon; the owner is expected to redraw final art.
"""

EMPTY = "." * 16


def patch(base, rows):
    """Return a copy of `base` with {row_index: row_string} replaced."""
    out = list(base)
    for i, r in rows.items():
        out[i] = r
    return out


def shift_rows(base, start, end, dy):
    """Move rows start..end (inclusive) by dy; vacated rows become empty."""
    out = list(base)
    band = base[start:end + 1]
    for i in range(start, end + 1):
        out[i] = EMPTY
    for i, r in enumerate(band):
        j = start + i + dy
        if 0 <= j < 16:
            out[j] = r
    return out


def shift_cols(base, start, end, dx):
    """Move rows start..end (inclusive) sideways by dx pixels."""
    out = list(base)
    for i in range(start, end + 1):
        r = base[i]
        out[i] = ("." * dx + r[:16 - dx]) if dx >= 0 else (r[-dx:] + "." * -dx)
    return out


# ==========================================================================
# PLAYER - tired student: messy hair, side-swept fringe, heavy-lidded eyes,
# hoodie (middle) with light backpack straps, dark trousers.
# Sources: "Life is\nmeaningless..." / "And college sucks!"
# ==========================================================================

P_DOWN = [
    "................",
    ".....#.##.#.....",
    "....########....",
    "...##########...",
    "...##########...",
    "...#####oooo#...",
    "...#o##oo##o#...",  # heavy-lidded eyes
    "...#oooooooo#...",
    "....#oooooo#....",
    "...#+######+#...",
    "..#++o++++o++#..",
    "..#++o++++o++#..",
    "..#o#+####+#o#..",
    "...#++++++++#...",
    "....###..###....",
    "....###..###....",
]
P_DOWN_WALK_A = patch(P_DOWN, {15: "....###........."})
P_DOWN_WALK_B = patch(P_DOWN, {15: ".........###...."})

P_UP = [
    "................",
    ".....#.##.#.....",
    "....########....",
    "...##########...",
    "...##########...",
    "...##########...",
    "...##########...",
    "...##########...",
    "....########....",
    "...#++++++++#...",
    "..#+#oooooo#+#..",  # backpack
    "..#+#o####o#+#..",
    "..#o#oooooo#o#..",
    "...#++++++++#...",
    "....###..###....",
    "....###..###....",
]
P_UP_WALK_A = patch(P_UP, {15: "....###........."})
P_UP_WALK_B = patch(P_UP, {15: ".........###...."})

P_RIGHT_WALK_A = [  # contact: legs apart
    "................",
    "......#.##.#....",
    ".....########...",
    "....##########..",
    "....##########..",
    "....######ooo#..",
    "....####+o##o#..",
    "....#####ooooo#.",
    ".....####ooo#...",
    "....##+#####....",
    "...#oo#+++++#...",
    "..#ooo#++#++#...",
    "..#ooo#++#++#...",
    "...###+++++##...",
    "....##...##.....",
    "...###...###....",
]
# passing: legs together, upper body raised one pixel (weight shift)
P_RIGHT_WALK_B = shift_rows(P_RIGHT_WALK_A, 1, 13, -1)
P_RIGHT_WALK_B = patch(P_RIGHT_WALK_B, {
    13: "....##++++##....",
    14: ".....####.......",
    15: ".....#####......",
})

# Idle "meaningless" slump: stand -> head sinks -> eyes shut -> gaze down.
P_IDLE_0 = P_DOWN
_p_slump = shift_rows(P_DOWN, 1, 8, 1)          # head drops onto collar
_p_slump = patch(_p_slump, {9: "...#+#oooo#+#..."})  # jaw now over collar
P_IDLE_1 = _p_slump
P_IDLE_2 = patch(_p_slump, {7: "...#oooooooo#...", 8: "...#o##oo##o#..."})
P_IDLE_3 = patch(P_DOWN, {6: "...#oooooooo#...", 7: "...#o##oo##o#..."})

# React "college sucks!" shrug: hands out -> shrug + shout -> drop.
_p_shrug = patch(P_DOWN, {
    10: ".#o#+o++++o+#o#.",
    11: "..##+o++++o+##..",
    12: "...#++####++#...",
})
P_REACT_0 = patch(P_DOWN, {
    11: ".#o#+o++++o+#o#.",
    12: "..##+######+##..",
})
P_REACT_1 = shift_rows(_p_shrug, 1, 12, -1)  # shoulders up
P_REACT_1 = patch(P_REACT_1, {12: "...#++++++++#..."})
P_REACT_2 = patch(P_REACT_1, {
    6: "...#ooo##ooo#...",   # shouting mouth
    7: "....#oo##oo#....",
})
P_REACT_3 = patch(P_DOWN, {
    8: "....#oo++oo#....",   # muttering
    12: "..#o#+####+#o#..",
})

# ==========================================================================
# MAYANK - alert friend: neat side-parted hair, glasses, light collared
# shirt, belt, middle trousers.
# Sources: "Something weird is\ngoing on..." / "Mayank: Hey! Did\nyou\nhear
# that?" / "came from the B7\nmain gate area." / "Mayank: Ok, I'll\nwait here."
# ==========================================================================

M_DOWN = [
    "................",
    "................",
    ".....######.....",
    "....##+#####....",
    "...##+#######...",
    "...#oooooooo#...",
    "...##++##++##...",  # glasses
    "...#oooooooo#...",
    "...#ooo##ooo#...",
    "....#oooooo#....",
    "..##oo#oo#oo##..",  # collar
    "..#o#oooooo#o#..",
    "..#o#oooooo#o#..",
    "..#o########o#..",  # belt, hands
    "...#+++##+++#...",
    "...###....###...",
]
M_DOWN_WALK_A = patch(M_DOWN, {  # right hand forward, left hand back
    13: "..##########o#..",
    14: "...#++#..####...",
    15: "...####.........",
})
M_DOWN_WALK_B = patch(M_DOWN, {
    13: "..#o##########..",
    14: "...####..#++#...",
    15: ".........####...",
})

M_UP = [
    "................",
    "................",
    ".....######.....",
    "....########....",
    "...##########...",
    "...##########...",
    "...+#########+..",  # glasses arms over ears
    "...##########...",
    "...#o######o#...",
    "....##oooo##....",
    "..##ooo##ooo##..",
    "..#o#oooooo#o#..",
    "..#o#oooooo#o#..",
    "..#o########o#..",
    "...#+++##+++#...",
    "...###....###...",
]
M_UP_WALK_A = patch(M_UP, {
    13: "..##########o#..",
    14: "...#++#..####...",
    15: "...####.........",
})
M_UP_WALK_B = patch(M_UP, {
    13: "..#o##########..",
    14: "...####..#++#...",
    15: ".........####...",
})

M_RIGHT_WALK_A = [
    "................",
    "................",
    "......######....",
    ".....##+#####...",
    "....##+#######..",
    "....######ooo#..",
    "....###+###+#o#.",  # ear, glasses arm, lens
    "....####+ooooo#.",
    ".....####oooo#..",
    ".......#oooo#...",
    "....#oooooooo#..",
    "...#+#ooo#ooo#..",  # bag at back, arm forward
    "...#+#oo#ooo#...",
    "....####o####...",
    "....#++#..#++#..",
    "...###....####..",
]
M_RIGHT_WALK_B = shift_rows(M_RIGHT_WALK_A, 2, 13, -1)
M_RIGHT_WALK_B = patch(M_RIGHT_WALK_B, {
    11: "...#+#oooo#o#...",  # arm back
    12: "....#########...",
    13: ".....#++++#.....",
    14: "......#++#......",
    15: ".....#####......",
})

# Idle "I'll wait here": stand -> glance left -> foot tap -> glance right.
M_IDLE_0 = M_DOWN
M_IDLE_1 = patch(M_DOWN, {6: "..##++##++###...", 8: "...#oo##oooo#..."})
M_IDLE_2 = patch(M_DOWN, {14: "...#+++#.####...", 15: "...###.........."})
M_IDLE_3 = patch(M_DOWN, {6: "...###++##++##..", 8: "...#oooo##oo#..."})

# React "Did you hear that?": startle hop -> hand to ear -> listen.
M_REACT_0 = patch(M_DOWN, {6: "...##oo##oo##...", 8: "...#ooo##ooo#..."})
M_REACT_1 = shift_rows(M_DOWN, 2, 13, -1)       # hop: body up, legs stretch
M_REACT_1 = patch(M_REACT_1, {
    0: ".....#.#.#......",                       # hair stands up
    5: "...##oo##oo##...",                       # lenses flash
    7: "...#ooo##ooo#...",
    13: "...#+++##+++#...",
    14: "...#++#..#++#...",
    15: "...###....###...",
})
_m_ear = patch(M_DOWN, {
    5: "...#oooooooo#o#.",
    6: "...##++##++##o#.",
    7: "...#oooooooo##..",
    10: "..##oo#oo#o##...",
    11: "..#o#oooooo#....",
    12: "..#o#oooooo#....",
    13: "..#o#########...",
})
M_REACT_2 = _m_ear
M_REACT_3 = patch(_m_ear, {6: "...###++##++#o#.", 8: "...#oooo##oo#..."})

# ==========================================================================
# RANDOM MUJ SCHOLAR - uncanny echo / optional zombie study: grey (middle)
# skin, blank light eyes, gaping mouth, tilted head, light coat with dark
# lanyard and card, torn hem, reaching arms, dragging gait.
# Source: "Random MUJ\nscholar: grrrr!"
# ==========================================================================

S_DOWN = [
    "................",
    "................",
    "......######....",
    ".....########...",
    ".....##+++#+#...",
    ".....#+o++o+#...",  # blank eyes
    ".....#+#++#+#...",
    ".....#++##++#...",  # gaping mouth
    "......#+##+#....",
    ".......#++#.....",
    "..##oo#oo#oo##..",
    "..#oo#o##o#oo#..",
    "..#++#o++o#++#..",  # hands hang forward
    "..##oooooooo##..",
    "...#o#o##o#o#...",  # torn hem
    "...###....###...",
]
# shamble: head lolls to the other side each step, one foot drags
S_DOWN_WALK_A = patch(S_DOWN, {15: "...###.....##..."})
S_DOWN_WALK_B = patch(shift_cols(S_DOWN, 2, 9, -1), {15: "....##....###..."})

S_UP = [
    "................",
    "................",
    "......######....",
    ".....########...",
    ".....########...",
    ".....########...",
    ".....+######+...",  # grey ears
    ".....########...",
    "......######....",
    ".......#++#.....",
    "..##oooooooo##..",
    "..#oo#oooo#oo#..",
    "..#oo#oooo#oo#..",
    "..##oooooooo##..",
    "...#o#o##o#o#...",
    "...###....###...",
]
S_UP_WALK_A = patch(S_UP, {15: "...###.....##..."})
S_UP_WALK_B = patch(shift_cols(S_UP, 2, 9, -1), {15: "....##....###..."})

S_RIGHT_WALK_A = [  # hunched, arms reaching, stiff stride
    "................",
    "........######..",
    ".......########.",
    ".......####+++#.",
    ".......###+o++#.",
    ".......###++#+#.",
    "........#+++###.",
    ".....####+##....",
    "....#oooo######.",
    "...#ooooooooo++#",
    "...#oooo#######.",
    "...#oo#o#.......",
    "...#oo#o#.......",
    "...#o#o#o#......",
    "...##...##......",
    "..###...###.....",
]
# drag: back foot scrapes, body sinks one pixel, head droops
S_RIGHT_WALK_B = shift_rows(S_RIGHT_WALK_A, 1, 13, 1)
S_RIGHT_WALK_B = patch(S_RIGHT_WALK_B, {
    14: "...#o#o##o#.....",
    15: ".####..###......",
})

# Idle uncanny sway: tilt right -> droop -> loll left -> twitch/blink.
S_IDLE_0 = S_DOWN
S_IDLE_1 = patch(shift_rows(S_DOWN, 2, 8, 1), {2: EMPTY})
S_IDLE_1 = patch(S_IDLE_1, {9: ".......#++#....."})
S_IDLE_2 = shift_cols(S_IDLE_1, 3, 9, -1)
S_IDLE_3 = patch(S_DOWN, {5: ".....#+#++#+#...", 6: ".....#++++++#..."})

# React "grrrr!": hunch -> arms up, mouth wide -> lunge -> hold snarl.
S_REACT_0 = patch(S_DOWN, {7: ".....#+####+#...", 8: "......#####....."})
_s_arms_up = patch(S_DOWN, {
    7: ".....#+####+#...",
    8: "..##..#o##o#.##.",   # teeth, raised hands
    9: ".#++#..#++#.#++#",
    10: ".#oo#o#oo#o##oo#",
    11: "..#o#o####o#oo#.",
    12: "..#o#oo++oo#o#..",
    13: "..##oooooooo##..",
})
S_REACT_1 = _s_arms_up
S_REACT_2 = shift_rows(_s_arms_up, 2, 13, 1)  # lunge down/forward
S_REACT_2 = patch(S_REACT_2, {
    14: "..#o#o#oo#o#o#..",
    15: "..###......###..",
})
S_REACT_3 = shift_cols(_s_arms_up, 2, 7, -1)


# ==========================================================================
# Pack definition: runtime strip -> ordered frames and preview timing (ms).
# ==========================================================================

WALK_ORDER = ["down_a", "down_b", "up_a", "up_b", "right_a", "right_b"]

STRIPS = {
    "afterhours_player_walk": {
        "frames": [P_DOWN_WALK_A, P_DOWN_WALK_B, P_UP_WALK_A, P_UP_WALK_B,
                   P_RIGHT_WALK_A, P_RIGHT_WALK_B],
        "labels": WALK_ORDER,
        "ms": [180] * 6,
    },
    "afterhours_player_idle": {
        "frames": [P_IDLE_0, P_IDLE_1, P_IDLE_2, P_IDLE_3],
        "labels": ["stand", "head_sinks", "eyes_shut", "gaze_down"],
        "ms": [700, 400, 800, 400],
    },
    "afterhours_player_react": {
        "frames": [P_REACT_0, P_REACT_1, P_REACT_2, P_REACT_3],
        "labels": ["hands_out", "shrug", "shrug_shout", "drop_mutter"],
        "ms": [200, 200, 500, 500],
    },
    "afterhours_mayank_walk": {
        "frames": [M_DOWN_WALK_A, M_DOWN_WALK_B, M_UP_WALK_A, M_UP_WALK_B,
                   M_RIGHT_WALK_A, M_RIGHT_WALK_B],
        "labels": WALK_ORDER,
        "ms": [160] * 6,
    },
    "afterhours_mayank_idle": {
        "frames": [M_IDLE_0, M_IDLE_1, M_IDLE_2, M_IDLE_3],
        "labels": ["stand", "glance_left", "foot_tap", "glance_right"],
        "ms": [600, 500, 300, 500],
    },
    "afterhours_mayank_react": {
        "frames": [M_REACT_0, M_REACT_1, M_REACT_2, M_REACT_3],
        "labels": ["wide_eyes", "startle_hop", "hand_to_ear", "listen_right"],
        "ms": [200, 150, 400, 700],
    },
    "afterhours_scholar_walk": {
        "frames": [S_DOWN_WALK_A, S_DOWN_WALK_B, S_UP_WALK_A, S_UP_WALK_B,
                   S_RIGHT_WALK_A, S_RIGHT_WALK_B],
        "labels": WALK_ORDER,
        "ms": [280] * 6,
    },
    "afterhours_scholar_idle": {
        "frames": [S_IDLE_0, S_IDLE_1, S_IDLE_2, S_IDLE_3],
        "labels": ["tilt_right", "droop", "loll_left", "twitch_blink"],
        "ms": [700, 500, 700, 120],
    },
    "afterhours_scholar_react": {
        "frames": [S_REACT_0, S_REACT_1, S_REACT_2, S_REACT_3],
        "labels": ["teeth", "arms_up_growl", "lunge", "snarl_hold"],
        "ms": [250, 200, 300, 500],
    },
}
