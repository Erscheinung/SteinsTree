"""Prologue: pocket-monster nostalgia (2009), the day card, the pause menu.

All lines here are draft placeholders. Rewrite freely in GB Studio, in the
studio (python3 tools/studio/studio.py serve) or in docs/STORY.md + a Claude
regeneration (see CLAUDE.md).
"""

import gbs
from gbs import (say, text, set_var, add, rnd, sub_var, if_var, loop_while, menu, switch, goto, wait,
                 shake, sfx, fade_out, hide, show, face, move_to, flicker, comment, music, text_speed)
from story.common import CH_PROLOGUE, CH_DAY1, CH_OUTBREAK, open_spot

FOLDER = "1 Prologue"


def build(ctx):
    bedroom(ctx)
    battle(ctx)
    card(ctx)
    pause(ctx)


def chapter_select(ctx):
    """Dev tool (Pause > Chapters): jump to any part with the right variables."""
    s = ctx.scene("chapter_select", "Chapter Select (dev)", "void_stars", "0 Menus")
    from build_game import LEGACY

    def jump(vars_, scene_key, x, y, d="down"):
        ev = [set_var(k, v) for k, v in vars_.items()] + \
             [gbs.speed("player", 1), gbs.player_sprite(ctx.sprite("player"))]
        sid = LEGACY.get(scene_key) or ctx.sid_of(scene_key)
        return ev + [goto(sid, x, y, d)]
    alive = {"Alive_" + f: 1 for f in ("Mayank", "Divyansh", "Kanishk", "Parag", "Anshuman", "Garvita")}
    pages = {
        1: [("Prologue", jump({"Chapter": 0, "PrologueBattle": 0}, "prologue_bedroom", 8, 10)),
            ("D1 Morn", jump({"Chapter": 1, "Phase": 0, "Objective": 1}, "room", 22, 20, "left")),
            ("D1 Phys", jump({"Chapter": 1, "Phase": 0}, "physics_class", 11, 13, "up")),
            ("D1 Dine", jump({"Chapter": 1, "Phase": 1}, "quess_mess_in", 12, 14, "up")),
            ("D1 Eve", jump({"Chapter": 1, "Phase": 2, "Objective": 3}, "world", *ctx.world_return["legacy_b7_front"])),
            ("D2 Maths", jump({"Chapter": 2, "Phase": 0}, "maths_class", 9, 14, "up")),
            ("D2 Crik", jump({"Chapter": 2, "Phase": 1}, "cricket_ground", 28, 34, "up"))],
        2: [("D3 Chem", jump({"Chapter": 3, "Phase": 0}, "chem_lab", 9, 13, "up")),
            ("D3 Shop", jump({"Chapter": 3, "Phase": 1}, "workshop_in", 9, 11, "up")),
            ("D3 Walk", jump({"Chapter": 3, "Phase": 2}, "scrub_trail", *ctx.entry["scrub_trail"])),
            ("Outbreak", jump({"Chapter": 4, "Phase": 0, "Step": 0, "SawZombie": 0}, "room", 22, 20, "left")),
            ("Lounge", jump(dict(alive, Chapter=4, Step=0, Objective=10), "lounge", 6, 22, "up")),
            ("Siege", jump(dict(alive, Chapter=4, Step=1, Objective=10), "quess_siege", 3, 13, "right")),
            ("Lanes", jump(dict(alive, Chapter=4, Step=2, Objective=11), "lanes", 2, 10, "right"))],
        3: [("Stealth", jump(dict(alive, Chapter=4, Step=3, Objective=12), "stealth", *ctx.level_start["stealth"])),
            ("Stairs", jump(dict(alive, Chapter=4, Step=4, Objective=13), "staircase_stand",
                            *ctx.level_start["staircase_stand"])),
            ("Old Mess", jump(dict(alive, Chapter=4, Step=5, Objective=13), "old_mess_stand", 3, 13, "right")),
            ("Roofs", jump(dict(alive, Chapter=4, Step=6, Objective=14), "rooftop", *ctx.level_start["rooftop"])),
            ("Dome", jump(dict(alive, Chapter=4, Step=7, Objective=15), "dome_night", 13, 13, "up")),
            ("Hub", jump(dict({"Mem%d" % i: 0 for i in range(1, 8)}, Chapter=5, MemCount=0, HubSeen=0,
                              Objective=16), "hub", 9, 12, "up")),
            ("Finale", jump({"Chapter": 6, "FinaleTalks": 0, "Objective": 16}, "finale", 28, 40, "up"))],
    }
    cases = {}
    for n, items in pages.items():
        cases[n] = [menu("Pick", [t for t, _ in items] + ["Back"]),
                    switch("Pick", {i + 1: evs for i, (_, evs) in enumerate(items)})]
    s.script += [
        hide("player"),
        text("CHAPTER SELECT (dev)", "Jumps set the story variables for you."),
        menu("Page", ["Pro-Day2", "D3-Act2", "Act2-End", "Back"]),
        switch("Page", cases),
        gbs.pop_state(),
    ]


def bedroom(ctx):
    s = ctx.scene("prologue_bedroom", "Bedroom, 2009", "prologue_bedroom", FOLDER)
    s.bank = "memory"
    hx, hy = 12, 8
    s.actor("Handheld", ctx.sprite("handheld"), hx, hy + 1, script=[
        if_var("PrologueBattle", "==", 0, [
            say("", "A PocketBoy. Batteries at 2 bars. Enough for one more battle."),
            say("You", "Just one. Then homework. Probably."),
            goto(ctx.sid_of("battle_pocket"), 1, 16, fade="1"),
        ], [say("", "The screen is warm. SPARKLET is asleep in the corner of it.")])])
    mom = s.actor("Mom", ctx.sprite("mama"), 4, 12, direction="right", script=[
        if_var("PrologueBattle", "==", 0, [
            say("Mom", "Beta, ten minutes. Then lights off. Deal?"),
            say("You", "Deal. Fifteen."),
        ], [say("Mom", "Sleep now. The critters will be there tomorrow.")])])
    s.script += [
        gbs.palette("memory"),
        gbs.player_sprite(ctx.sprite("kid")),
        text_speed(1),
        music(ctx.music("intro")),
        if_var("PrologueBattle", "==", 0, [
            comment("PROLOGUE - edit freely. The first thing the player sees."),
            if_var("PrologueIntro", "==", 0, [
                text("Jaipur. 2009.", "A small room. A big world on a tiny screen."),
                say("Mom", "Homework done?"),
                say("You", "...define 'done'."),
                say("Mom", "Ten minutes of your critters. Then sleep."),
                set_var("PrologueIntro", 1),
            ]),
        ], [
            say("", "GNAWBIT's eyes glowed for a second before it fainted. Weird."),
            say("Mom", "Lights off, beta."),
            gbs.palette("night"), hide(mom.id), hide("player"),
            wait(0.8),
            text("Eleven years later..."),
            text("Manipal University Jaipur.", "B.Tech, Computer Science. First year.", "Block B7. Room 10."),
            set_var("Chapter", CH_DAY1), set_var("Phase", 0), set_var("Objective", 1),
            gbs.player_sprite(ctx.sprite("player")),
            set_var("CardDay", 1),
            goto(ctx.sid_of("day_card"), 1, 16, fade="1"),
        ]),
    ]


def battle(ctx):
    s = ctx.scene("battle_pocket", "Pocket Critters Battle", "battle_pocket", FOLDER)
    s.actor("Sparklet", ctx.sprite("sparklet"), 5, 13, direction="right", animate=True)
    foe = s.actor("Gnawbit", ctx.sprite("gnawbit"), 14, 7, direction="left", animate=True)
    bx, by = open_spot(ctx.meta("prologue_bedroom")["collisions"], 20, 18, 12, 10)
    turn = [
        gbs.raw("SPARKLET  HP $%s$\nGNAWBIT   HP $%s$" % (gbs.V["MyHP"], gbs.V["EnHP"])),
        menu("Pick", ["Fight", "Bag", "Run"]),
        switch("Pick", {
            1: [menu("Pick", ["Tackle", "Spark", "Growl"]),
                switch("Pick", {
                    1: [rnd("Tmp", 3, 5), text("SPARKLET used TACKLE!"), sub_var("EnHP", "Tmp"), shake(0.2, 2)],
                    2: [rnd("Tmp", 4, 7), text("SPARKLET used SPARK!"), sfx("crash", 4, 200, 0.2),
                        flicker(foe.id, 0.4), sub_var("EnHP", "Tmp"),
                        if_var("Tmp", ">=", 7, [text("A critical hit!")])],
                    3: [text("SPARKLET used GROWL!", "GNAWBIT's attack fell. It looks... hungrier?"),
                        set_var("Growled", 1)],
                })],
            2: [text("You used Mom's laddoo!", "SPARKLET recovered 8 HP."), add("MyHP", 8),
                if_var("MyHP", ">", 20, [set_var("MyHP", 20)])],
            3: [text("Can't escape!", "(Nobody escapes the first battle. That's the rule.)")],
        }),
        if_var("EnHP", ">", 0, [
            rnd("Tmp", 2, 5),
            if_var("Growled", "!=", 0, [add("Tmp", -1)]),
            text("Wild GNAWBIT used BITE!"), shake(0.3, 3), sub_var("MyHP", "Tmp"),
            if_var("MyHP", "<=", 0, [
                text("SPARKLET fainted...", "...You hit RESET like a professional.", "Round two!"),
                set_var("MyHP", 20), set_var("EnHP", 18), set_var("Growled", 0),
            ]),
        ]),
    ]
    s.script += [
        hide("player"),
        music(ctx.music("battle")),
        comment("POCKET BATTLE - homage only: original critters, no Nintendo assets."),
        set_var("MyHP", 20), set_var("EnHP", 18), set_var("Growled", 0),
        text("A wild GNAWBIT appeared!"),
        text("Go! SPARKLET!"),
        loop_while("EnHP", ">", 0, turn),
        flicker(foe.id, 1.0), gbs.deactivate(foe.id),
        text("Wild GNAWBIT fainted!", "SPARKLET grew to Lv. 6!"),
        text("...for a second, GNAWBIT looked straight out of the screen. At you."),
        set_var("PrologueBattle", 1),
        goto(ctx.sid_of("prologue_bedroom"), bx, by, "up", fade="1"),
    ]


def card(ctx):
    """Persona-style calendar card shown at the start of every day."""
    s = ctx.scene("day_card", "Day Card", "day_card", "3 Days")
    days = {
        1: ("MONDAY", "DAY 1", "Sunny"),
        2: ("TUESDAY", "DAY 2", "Cloudy"),
        3: ("WEDNESDAY", "DAY 3", "Clear"),
        4: ("WEDNESDAY", "3:07 AM", "???"),
    }
    from build_game import LEGACY
    cases = {}
    for n, (d, label, weather) in days.items():
        cases[n] = [gbs.text_draw(label, 4, 4), gbs.text_draw(d, 4, 6), gbs.text_draw(weather, 4, 9)]
    s.script += [
        hide("player"),
        switch("CardDay", cases),
        sfx("tone", 4, 1600, 0.2),
        wait(1.5),
        if_var("CardDay", "==", 4, [shake(0.6, 4)]),
        goto(LEGACY["room"], 22, 20, "left", fade="2"),
    ]


OBJECTIVES = {
    1: "Physics class, AB1",
    2: "Dinner, Quess Mess",
    3: "Free evening. Friends: NBC, avenue, scrub trail, cricket, Dome, B7 courts",
    4: "Sleep. B7, room 10",
    5: "Maths class, AB2",
    6: "Cricket match",
    7: "Chemistry lab, AB3",
    8: "Workshop practical",
    9: "Night walk behind B7",
    10: "Hold the Quess Mess",
    11: "Hostel Avenue",
    12: "The Underpass",
    13: "Grand Staircase",
    14: "AB2 rooftops",
    15: "The Dome",
    16: "The middle.",
}


def pause_events(ctx, in_place=True):
    """The START menu. Runs in place inside each scene (no scene change, so
    nothing restarts); Chapters pushes the scene and opens the dev select."""
    return [
        switch("Objective", {k: [text("NOW: " + v)] for k, v in OBJECTIVES.items()},
               [text("NOW: keep going.")]),
        gbs.raw("BONDS\nMayank $%s$  Divy $%s$\nKani $%s$  Parag $%s$" % tuple(
            gbs.V["Bond_" + f] for f in ("Mayank", "Divyansh", "Kanishk", "Parag")),
                "BONDS\nAnsh $%s$  Garv $%s$\nGrade $%s$" % tuple(
            gbs.V[k] for k in ("Bond_Anshuman", "Bond_Garvita", "Grade"))),
        menu("Pick", ["Resume", "Save", "Chapters", "Title"]),
        switch("Pick", {
            2: [gbs.save_game(), text("Saved.")],
            3: ([gbs.ev("EVENT_SCENE_PUSH_STATE", {})] if in_place else []) +
               [goto(ctx.sid_of("chapter_select"), 0, 0)],
            4: [goto(ctx.sid_of("title"), 0, 0)],
        }),
    ]


def pause(ctx):
    """Pause scene used by the title screen's original Start binding."""
    s = ctx.scene("pause", "Pause Menu", "void_stars", "0 Menus")
    from story.legacy import pause_hook
    pause_hook(ctx)  # make sure the shared script exists
    s.script += [hide("player"), gbs.call_script(ctx.pause_script), gbs.pop_state()]