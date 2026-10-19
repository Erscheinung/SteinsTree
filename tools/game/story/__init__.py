"""Dernier draft 1 - the whole game, assembled.

Order matters: travel builds the campus scenes first, then each act adds its
scenes and decorates campus scenes, then location gates are finalised.
"""

import gbs
from story import travel, prologue, act1, act2, act3, legacy
from story.legacy import pause_hook

# scenes where START should not open the pause menu (cutscene-only screens)
NO_PAUSE = {"battle_pocket", "pause", "credits", "quess_siege", "old_mess_stand",
            "dome_night", "chapter_select"}

FOLDER_ROWS = ["0 Menus", "1 Prologue", "3 Days", "2 Campus", "2 Campus Interiors", "4 Outbreak",
               "5 The Middle", "6 Finale"]


def build(ctx):
    travel.build(ctx)
    prologue.build(ctx)
    act1.build(ctx)
    act2.build(ctx)
    act3.build(ctx)
    prologue.chapter_select(ctx)
    for key, s in ctx.scenes.items():
        if key not in NO_PAUSE:
            s.script.insert(0, pause_hook(ctx))
    travel.finalize(ctx)
    layout(ctx)


def layout(ctx):
    """Place generated scenes on GB Studio's world canvas, one row per folder,
    below the owner's original scenes (which keep their positions)."""
    y = 1900
    for folder in FOLDER_ROWS:
        x = 0
        row_h = 0
        for key in ctx.order:
            s = ctx.scenes[key]
            if s.folder != folder:
                continue
            s.pos = (x, y)
            x += s.width * 8 + 40
            row_h = max(row_h, s.height * 8)
            if x > 6000:
                x = 0
                y += row_h + 60
                row_h = 0
        y += row_h + 120


def palettes_for(ctx, scene):
    import gbc
    if getattr(scene, "legacy_bg", None):
        # The owner's hand-made backgrounds stay intact.  Their source art
        # was authored for the four-shade Game Boy palette, so use the DMG
        # palette for every tile instead of the lossy enriched copy.
        bg = ["dmg"] * 7 + ["muj-ui"]
    else:
        bg = gbc.palette_ids(scene.bank)
    # sprite palettes: default slot colours unless a sprite in this scene needs another
    SPRITE_SLOTS = ctx.sprite_slots
    default = ["player", "mayank", "divyansh", "kanishk", "parag", "anshuman", "garvita", "zombie"]
    spr = [""] * 8
    by_id = {}
    for name in SPRITE_SLOTS:
        try:
            by_id[ctx.sprite(name)] = name
        except Exception:
            pass
    used = [a.sprite_id for a in scene.actors]
    scripts = [scene.script] + [x for a in scene.actors for x in (a.script, a.start, a.update, a.hit1)] + \
              [t.script for t in scene.triggers]
    for sc in scripts:
        for e in gbs.walk_events(sc):
            if e["command"] in ("EVENT_LAUNCH_PROJECTILE", "EVENT_ACTOR_SET_SPRITE", "EVENT_PLAYER_SET_SPRITE"):
                used.append(e["args"].get("spriteSheetId"))
    for sprite_id in used:
        name = by_id.get(sprite_id)
        if not name:
            continue
        slot, key = SPRITE_SLOTS[name]
        if key != default[slot]:
            spr[slot] = "muj-spr-" + key
    # the player's sprite may be swapped (kid, plane): that palette lives in slot 0 too
    return bg, spr


def legacy_patches(ctx):
    return legacy.patches(ctx)
