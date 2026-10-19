"""Shared story state, constants and helpers.

Global variables used by the story (GB Studio > Variables shows these names):
  Chapter   0 prologue, 1-3 Persona days, 4 outbreak, 5 the Dome (Act 3), 6 finale
  Phase     time of day inside a chapter (0 morning, 1 after class, 2 evening, 3 night)
  Step      outbreak level reached (Act 2) / memories finished (Act 3)
  Bond_*    friendship points (raised by hangouts and kind choices)
  Grade     class quiz score, Alive_* who is still alive, Mem* memories seen
"""

import json
import sys
from collections import deque
from pathlib import Path

import gbs
from gbs import V

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "map"))
import gbc  # noqa: E402

CH_PROLOGUE, CH_DAY1, CH_DAY2, CH_DAY3, CH_OUTBREAK, CH_DOME, CH_FINALE = range(7)
FRIENDS = ["Mayank", "Divyansh", "Kanishk", "Parag", "Anshuman", "Garvita"]

# Every name the player sees for a friend comes from here: rename in one place
# (and in docs/STORY.md) to swap a placeholder for a real person.
NAMES = {f: f for f in FRIENDS}


def walkable_grid(collisions, w, h):
    c = gbc.decompress8(collisions) if collisions else [0] * (w * h)
    return [[c[y * w + x] == 0 for x in range(w)] for y in range(h)]


def open_spot(collisions, w, h, x, y, avoid=()):
    """Nearest tile where a 16x16 actor fits (2 tiles wide), from (x,y)."""
    g = walkable_grid(collisions, w, h)
    avoid = set(avoid)
    seen = {(x, y)}
    q = deque([(x, y)])
    while q:
        cx, cy = q.popleft()
        if 0 <= cx < w - 1 and 1 <= cy < h and g[cy][cx] and g[cy][cx + 1] and g[cy - 1][cx] and \
                g[cy - 1][cx + 1] and (cx, cy) not in avoid and (cx + 1, cy) not in avoid:
            return cx, cy
        for dx, dy in ((0, 1), (1, 0), (-1, 0), (0, -1)):
            n = (cx + dx, cy + dy)
            if n not in seen and 0 <= n[0] < w and 0 <= n[1] < h:
                seen.add(n)
                q.append(n)
    return x, y


def is_ch(n, then, else_=None):
    return gbs.if_var("Chapter", "==", n, then, else_)


def is_phase(n, then, else_=None):
    return gbs.if_var("Phase", "==", n, then, else_)


def at(ch, ph, then, else_=None):
    """Run `then` only in chapter `ch` and phase `ph`."""
    return gbs.if_var("Chapter", "==", ch, [gbs.if_var("Phase", "==", ph, then, else_)], else_)


def night_palette(ctx, scene):
    """Palette events that make a scene follow the clock."""
    bank_day = scene.bank
    return [
        gbs.if_var("Chapter", ">=", CH_OUTBREAK,
                   [gbs.if_var("Chapter", "<", CH_DOME, [palette_for(ctx, scene, "night")])],
                   [gbs.if_var("Phase", ">=", 2, [palette_for(ctx, scene, "dusk")])]),
    ] if bank_day == "day" else []


def palette_for(ctx, scene, bank):
    """Palette swap event for a scene: shared banks, or the enriched legacy set."""
    if getattr(scene, "legacy_bg", None):
        prov = ctx.enriched[_legacy_bg_name(scene.legacy_bg)]
        ids = prov["palette_ids"]["night" if bank in ("night", "blood") else "day"] + ["muj-ui"]
        return gbs.ev("EVENT_PALETTE_SET_BACKGROUND", {"palette%d" % i: ids[i] for i in range(8)})
    return gbs.palette(bank)


def _legacy_bg_name(key):
    from build_game import LEGACY_BG
    return LEGACY_BG[key]


def bond(friend, n=1):
    return gbs.add("Bond_" + friend, n)


def day_card(ctx, day_name, number, weather):
    """Events that jump to the Persona-style calendar card."""
    return [gbs.set_var("CardDay", number), gbs.goto(ctx.sid_of("day_card"), 1, 16, fade="1")]


EMOTE = {}
