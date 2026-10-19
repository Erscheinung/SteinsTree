"""Act 3 - The Middle (Chapter 5) and the finale (Chapter 6).

The tone and the mechanics change. A starfield hub holds seven memories
built from the owner's life story (docs/LIFE.md). Each memory is a different
kind of play, and each ends with one of the lost friends reflecting on it.
After all seven, the Hall of Doors asks the "what ifs"; the last door opens
onto the cricket ground at dawn: a reunion that is not real, and is enough.

Every line marked LIFE is a placeholder written from the owner's notes.
Replace them with the real memories (docs/LIFE.md explains each slot).
"""

import gbs
from gbs import (say, text, set_var, add, inc, if_var, menu, switch, goto, wait, shake, sfx, hide, show,
                 face, move_to, comment, music, deactivate, activate, choice, set_pos, flicker, timer, palette,
                 speed, if_near)
from story.common import CH_DOME, CH_FINALE, open_spot, NAMES

N = NAMES
FOLDER = "5 The Middle"

# memory key -> (orb position in the hub, scene key, friend who reflects, reflection lines)
MEMORIES = [
    ("Mem1", (9, 3), "mem_childhood", "Anshuman",
     ["You were the quiet kid too. Hiding in plain sight.", "Funny. The shadows were never empty. You were in them."]),
    ("Mem2", (14, 5), "mem_flight", "Garvita",
     ["You flew all the way to London before you were ten.", "And you still came back. Running far isn't the same as running away."]),
    ("Mem3", (16, 10), "mem_india", "Parag",
     ["New school. New faces. Jarring.", "But you tried again. And again. That's the whole trick. Second try."]),
    ("Mem4", (14, 14), "mem_muskaan", "Mayank",
     ["Some people keep coming back into your life. Like a song.", "That's not a coincidence. That's a theme."]),
    ("Mem5", (4, 14), "mem_ninth", "Divyansh",
     ["You loved someone out loud. Big promises.", "It broke. You didn't. Takes one to know one, bro."]),
    ("Mem6", (2, 10), "mem_eleventh", "Kanishk",
     ["Too many orbits. Too many plans. Everything pulling.", "You can't plan every variable. You can only choose your next move."]),
    ("Mem7", (4, 5), "mem_twelfth", None,
     ["Can't fly too high. IIT pressure.", "Then... MUJ."]),
]


def back_to_hub(ctx, mem, friend, lines, scene, fx=9, fy=8):
    out = [comment("MEMORY END - reflection")]
    if friend:
        f = scene.actor(N[friend] + " (spirit)", ctx.sprite(friend.lower()), fx, fy, direction="down",
                        start=[hide("$self$"), gbs.collisions_off("$self$")])
        out += [show(f.id), flicker(f.id, 0.6), say(N[friend], *lines), flicker(f.id, 0.6), hide(f.id)]
    else:
        out += [say("", *lines)]
    out += [if_var(mem, "==", 0, [set_var(mem, 1), inc("MemCount")]),
            speed("player", 1), gbs.player_sprite(ctx.sprite("player")),
            goto(ctx.sid_of("hub"), 9, 12, "up", fade="1")]
    return out


def hub(ctx):
    s = ctx.scene("hub", "The Middle (hub)", "void_stars", FOLDER, bank="dreamA")
    for mem, (x, y), scene_key, friend, _ in MEMORIES:
        enter = [if_var(mem, "==", 0, [sfx("tone", 4, 1800, 0.3), speed("player", 1),
                                       goto(ctx.sid_of(scene_key), *ctx.level_start[scene_key], "down", fade="1")])]
        s.actor("Memory " + mem[-1], ctx.sprite("orb"), x, y, animate=True, script=enter,
                start=[gbs.collisions_off("$self$"), if_var(mem, "!=", 0, [deactivate("$self$")])])
        s.trigger("Enter " + mem, x, y - 1, 2, 2, script=enter)
    door = s.actor("Hall of Doors", ctx.sprite("orb"), 9, 9, animate=True,
                   script=[if_var("MemCount", ">=", 7, [goto(ctx.sid_of("hall"), 13, 11, "up", fade="1")])],
                   start=[gbs.collisions_off("$self$"), if_var("MemCount", "<", 7, [deactivate("$self$")])])
    s.trigger("Enter the Hall", 9, 8, 2, 2, script=[
        if_var("MemCount", ">=", 7, [goto(ctx.sid_of("hall"), 13, 11, "up", fade="1")])])
    cycle = [
        inc("Cycle"), if_var("Cycle", ">", 2, [set_var("Cycle", 0)]),
        switch("Cycle", {0: [palette("dreamA")], 1: [palette("dreamB")], 2: [palette("dreamC")]}),
    ]
    s.script += [
        palette("dreamA"), music(ctx.music("void")),
        comment("ACT 3 HUB - palette cycling makes the void breathe"),
        timer(0.6, cycle),
        if_var("HubSeen", "==", 0, [
            text("..."),
            text("It's quiet here. Not empty. Quiet."),
            say(N["Mayank"], "(somewhere) Everything before this is still in there. Go find out why you came."),
            text("(Walk into the lights. Each one is a memory.)"),
            set_var("HubSeen", 1),
        ]),
        if_var("MemCount", ">=", 7, [text("The centre is open now.")]),
    ]


def mem_childhood(ctx):
    s = ctx.scene("mem_childhood", "Memory: Childhood", "home_india", FOLDER, bank="memory")
    m = ctx.meta("home_india")
    sp = lambda x, y: open_spot(m["collisions"], m["cols"], m["rows"], x, y)
    dad = s.actor("Dad", ctx.sprite("student"), *sp(8, 10), direction="down", script=[
        say("Dad", "Not now, beta. Work call."), comment("LIFE: loneliness with parents")])
    mom = s.actor("Mom", ctx.sprite("mama"), *sp(16, 9), direction="left", script=[
        say("Mom", "Later, okay? Later.")])
    mama = s.actor("Mama", ctx.sprite("prof_m"), *sp(4, 12), direction="right", script=[
        if_var("TookCoins", "==", 1, [
            say("Mama", "You took the coins from the jar, didn't you."),
            say("Mama", "...Come. Let's buy jalebi with them. Together. Then you'll put it back from your pocket money."),
            comment("LIFE: guilt, stealing, and Mama's kindness"),
        ], [
            say("Mama", "Arre, champion! Come, sit. Tell me about your critters."),
        ]),
        say("Mama", "Your parents love you. They're just... far away, even when they're close."),
        say("Mama", "That's what I'm for."),
        set_var("MamaTalk", 1),
    ])
    ctx.level_start["mem_childhood"] = sp(10, 12)
    jar = s.trigger("Coin jar", 13, 12, 2, 1, script=[
        if_var("TookCoins", "==", 0, [
            say("", "A steel jar of coins on the shelf. Nobody's looking."),
            choice("TookCoins", "Take some", "Leave it"),
            if_var("TookCoins", "==", 1, [say("", "Clink. Your pocket is heavy. So is something else.")]),
        ])])
    s.trigger("Door out", 10, 13, 2, 1, script=[
        if_var("MamaTalk", "==", 1, back_to_hub(ctx, "Mem1", MEMORIES[0][3], MEMORIES[0][4], s, 10, 9),
               [say("", "Not yet. Someone's in the corner, waiting for you.")])])
    s.script += [
        palette("memory"), music(ctx.music("dream")),
        gbs.player_sprite(ctx.sprite("kid")),
        set_pos("player", *ctx.level_start["mem_childhood"]),
        comment("MEMORY 1 - CHILDHOOD (LIFE: childhood, loneliness, Mama, guilt, stealing)"),
        text("Before London. A house full of grown-ups talking over your head."),
        set_var("MamaTalk", 0), set_var("TookCoins", 0),
    ]


def mem_flight(ctx):
    s = ctx.scene("mem_flight", "Memory: Flight to London", "flight_sky", FOLDER, kind="SHMUP", bank="day")
    ctx.level_start["mem_flight"] = (2, 8)
    m = ctx.meta("flight_sky")
    W = m["cols"]
    for i in range(8):
        x = 18 + i * 11
        y = 3 + (i * 5) % 12
        c = s.actor("Storm %d" % i, ctx.sprite("stormcloud"), x, y, direction="left", animate=True)
        c.update = [if_near("$self$", "player", 1, [shake(0.3, 3), sfx("noise", 2, 100, 0.2)]), gbs.wait(0.1)]
    s.trigger("Heathrow", W - 6, 0, 2, 18, script=[
        text("Touchdown. Grey sky. Red buses. Everything smells like rain and new."),
        goto(ctx.sid_of("mem_london"), 2, 9, "right", fade="1")])
    s.script += [
        music(ctx.music("dream")),
        gbs.player_sprite(ctx.sprite("plane")),
        set_pos("player", 2, 8),
        comment("MEMORY 2a - FLYING TO LONDON (shmup). The 'spaceship' of the life-story levels."),
        text("Flying to a new country. The whole world shrinks to a window seat."),
        text("(Dodge the storm clouds. Fly east.)"),
    ]


def mem_london(ctx):
    s = ctx.scene("mem_london", "Memory: London", "london_street", FOLDER, bank="memory")
    m = ctx.meta("london_street")
    sp = lambda x, y: open_spot(m["collisions"], m["cols"], m["rows"], x, y)
    k1 = s.actor("Kid with a ball", ctx.sprite("student"), *sp(10, 11), direction="left", script=[
        say("Kid", "Oi! You any good? We need a keeper."),
        say("", "You were terrible. You were happy."), comment("LIFE: football with friends, fun with kids"),
        set_var("LonA", 1)])
    k2 = s.actor("Girl at the library", ctx.sprite("garvita"), *sp(24, 12), direction="down", script=[
        say("", "She lends you a book with a dragon on it. You read it twice."),
        comment("LIFE: joy of reading, first love"),
        say("", "First love is mostly staring at someone in a library. It counts."),
        set_var("LonB", 1)])
    s.trigger("Airport", 38, 6, 2, 6, script=[
        if_var("LonA", "==", 1, [if_var("LonB", "==", 1, [
            text("Then back from London.", "Jarring."),
        ] + back_to_hub(ctx, "Mem2", MEMORIES[1][3], MEMORIES[1][4], s, 20, 10), [
            say("", "Not yet. The library's still open.")])], [say("", "Not yet. The kids are still playing.")])])
    s.script += [
        palette("memory"), music(ctx.music("days")),
        gbs.player_sprite(ctx.sprite("kid")),
        set_pos("player", *sp(2, 10)),
        set_var("LonA", 0), set_var("LonB", 0),
        comment("MEMORY 2b - LONDON (LIFE: discovery, fun music, football, first love)"),
    ]


def mem_india(ctx):
    s = ctx.scene("mem_india", "Memory: Back to India", "childhood_school", FOLDER, bank="memory")
    m = ctx.meta("childhood_school")
    sp = lambda x, y: open_spot(m["collisions"], m["cols"], m["rows"], x, y)
    ctx.level_start["mem_india"] = sp(15, 18)
    aryan = s.actor("Aryan", ctx.sprite("student"), *sp(14, 12), direction="down", script=[
        switch("Tries", {
            0: [say("Aryan", "...")],
            1: [say("Aryan", "You talk funny. Like a BBC news guy.")],
        }, [say("Aryan", "Okay fine. You can be on my team. But you're goalkeeper."),
            comment("LIFE: Aryan. Uncertain but heavenly. A familiar abode."), set_var("India", 1)]),
        inc("Tries")])
    s.trigger("School gate", 14, 22, 4, 2, script=[
        if_var("India", "==", 1, [
            text("Then a change of schools. Fifth class.", "Jarring and sad.", "But slowly, it gets better."),
        ] + back_to_hub(ctx, "Mem3", MEMORIES[2][3], MEMORIES[2][4], s, 15, 18),
            [say("", "Try talking to Aryan again. And again.")])])
    s.script += [
        palette("memory"), music(ctx.music("days")),
        gbs.player_sprite(ctx.sprite("kid")),
        set_pos("player", *ctx.level_start["mem_india"]),
        set_var("Tries", 0), set_var("India", 0),
        comment("MEMORY 3 - BACK TO INDIA (mechanic: it only works if you keep trying)"),
        text("A new world. India. Familiar and strange at the same time."),
    ]


def mem_muskaan(ctx):
    s = ctx.scene("mem_muskaan", "Memory: Muskaan's theme", "flower_field", FOLDER, bank="dusk")
    m = ctx.meta("flower_field")
    sp = lambda x, y: open_spot(m["collisions"], m["cols"], m["rows"], x, y)
    spots = [sp(16, 8), sp(26, 4), sp(5, 15), sp(22, 16)]
    ctx.level_start["mem_muskaan"] = sp(4, 10)
    lines = [
        "Sixth class. Muskaan. New friends again, but she laughs at your drawings in the good way.",
        "Seventh. Love found again. Short. But life goes on. You win a drawing competition.",
        "Eighth. PSP, PS2, football at lunch. One of the best years of your life.",
        "Tenth. Muskaan, again. Same music. Some people are a theme, not a scene.",
    ]
    mus = s.actor("Muskaan", ctx.sprite("muskaan"), spots[0][0], spots[0][1], direction="down")
    cases = {}
    for i, l in enumerate(lines):
        nxt = spots[(i + 1) % len(spots)]
        cases[i] = motif() + [say("", l), flicker(mus.id, 0.5), set_pos(mus.id, nxt[0], nxt[1])]
    mus.script = [comment("LIFE: Muskaan returns - make her theme a recurring music track"),
                  switch("MusCount", cases), inc("MusCount"),
                  if_var("MusCount", ">=", 4, back_to_hub(ctx, "Mem4", MEMORIES[3][3], MEMORIES[3][4], s, 15, 10))]
    s.script += [
        palette("dusk"), music(ctx.music("days")),
        gbs.player_sprite(ctx.sprite("player")),
        set_pos("player", *sp(4, 10)), set_var("MusCount", 0),
        comment("MEMORY 4 - MUSKAAN (mechanic: she keeps reappearing; follow her)"),
        text("A field at the end of the school day. The same song is playing that always plays."),
    ]


def mem_ninth(ctx):
    s = ctx.scene("mem_ninth", "Memory: Ninth", "maths_class", FOLDER, bank="memory")
    ctx.level_start["mem_ninth"] = (9, 13)
    her = s.actor("Her", ctx.sprite("muskaan"), 12, 7, direction="down")
    s.script += [
        palette("memory"), music(ctx.music("dream")),
        comment("MEMORY 5 - NINTH (LIFE: love, betrayal, heartbreak. The spaceship coughs.)"),
        set_pos("player", 9, 13), face("player", "up"),
        text("Ninth. Another love. It blossoms. It's nice. You loved her."),
        say("", "Notes passed across desks. A name drawn in the margin of a maths book."),
        move_to("player", 10, 9),
        palette("blood"), shake(0.8, 3), sfx("noise", 3, 100, 0.6),
        text("And then: betrayal.", "Heartbreak. Shattering."),
        flicker(her.id, 1.0), deactivate(her.id),
        text("The spaceship coughs. Slows down."),
        speed("player", 0.5),
        say("", "(Walk to the door. It's further than it was.)"),
    ]
    s.trigger("Door", 3, 16, 2, 1, script=back_to_hub(ctx, "Mem5", MEMORIES[4][3], MEMORIES[4][4], s, 11, 12))


def motif():
    """Muskaan's theme: a short chime phrase (sound effects, no song needed).
    Replace with a proper hUGE song later - see docs/LIFE.md."""
    notes = [(659, 0.22), (784, 0.22), (880, 0.34), (784, 0.22), (659, 0.22), (587, 0.5)]
    out = []
    for f, d in notes:
        out += [sfx("tone", 2, f, d), wait(d + 0.04)]
    return [comment("MUSKAAN'S MOTIF")] + out


def mem_eleventh(ctx):
    """Eleventh: deadlines swarm you. Get overwhelmed - or choose to stop."""
    s = ctx.scene("mem_eleventh", "Memory: Eleventh", "orbits", FOLDER, bank="dreamB")
    ctx.level_start["mem_eleventh"] = (2, 15)
    voices = ["Mock test on Sunday.", "Physics is 33 percent weightage.", "Sharma ji's son got 99.4.",
              "Coaching till 9. School till 2.", "Are you even trying?", "This is the most important year."]
    spots = [(3, 3), (15, 3), (16, 14), (3, 9), (12, 6), (8, 15)]
    for i, (x, y) in enumerate(spots):
        o = s.actor("Deadline %d" % (i + 1), ctx.sprite("orb"), x, y, animate=True, move_speed=1 if i % 2 else 0.5)
        o.update = [
            if_var("Calm", "==", 0, [
                gbs.get_pos("player", "PX", "PY"), gbs.move_to_vars("$self$", "PX", "PY"),
                if_near("$self$", "player", 1, [
                    inc("Stress"), sfx("noise", 3, 200, 0.2), shake(0.2, 3),
                    text(voices[i]),
                    set_pos("$self$", *spots[(i + 3) % len(spots)]), wait(1.0),
                ]),
            ], [wait(0.2)]),
        ]
    cyc = [inc("Cycle"), if_var("Cycle", ">", 2, [set_var("Cycle", 0)]),
           switch("Cycle", {0: [palette("dreamA")], 1: [palette("dreamC")], 2: [palette("blood")]})]
    choose = [
        menu("Pick", ["Walk", "Build it anew"]),
        switch("Pick", {1: [text("So you walk. One foot. Then the other.")],
                        2: [text("So you build it again. Badly. Then less badly.")]}),
    ]
    crash = [
        set_var("Calm", 1), gbs.timer_off(1), shake(1.0, 6), sfx("crash", 4, 100, 1.0),
        text("Too much. The orbits pull you in.", "Until it crashes.", "The spaceship is lost. You have to get out."),
        palette("dreamB"),
    ] + choose + back_to_hub(ctx, "Mem6", MEMORIES[5][3], MEMORIES[5][4], s, 9, 5)
    ref = s.actor("Referee", ctx.sprite("orb"), 18, 0, pinned=True,
                  start=[hide("$self$"), gbs.collisions_off("$self$")])
    ref.update = [if_var("Calm", "==", 0, [if_var("Stress", ">=", 6, crash)]), wait(0.1)]
    s.trigger("Stop", 8, 8, 4, 3, script=[
        if_var("Calm", "==", 0, [
            set_var("Calm", 1), gbs.timer_off(1), palette("dreamA"),
            text("You stop chasing. You stand still in the middle of it.",
                 "The orbits keep spinning. They just don't pull as hard."),
        ] + choose + back_to_hub(ctx, "Mem6", MEMORIES[5][3], MEMORIES[5][4], s, 9, 5))])
    s.script += [
        palette("dreamB"), music(ctx.music("void")),
        comment("MEMORY 6 - ELEVENTH (playable: deadlines chase you; the calm centre ends it)"),
        set_pos("player", 2, 15), set_var("Stress", 0), set_var("Calm", 1),
        text("Eleventh. Too much. Everything at once.", "(The deadlines chase you. Or you could stop, in the middle.)"),
        timer(0.3, cyc), wait(1.0), set_var("Calm", 0),
    ]


def mem_twelfth(ctx):
    s = ctx.scene("mem_twelfth", "Memory: Twelfth", "corridor12", FOLDER, kind="PLATFORM", bank="memory")
    ctx.level_start["mem_twelfth"] = (2, 14)
    m = ctx.meta("corridor12")
    W = m["cols"]
    for i, line in enumerate(["JEE MAIN: 47 DAYS", "Don't fly too high.", "Rank > Dreams",
                              "Slowly. Slowly.", "Almost."]):
        s.trigger("Sign %d" % i, 8 + i * 11, 9, 1, 6, script=[
            if_var("Sign%d" % i, "==", 0, [say("", line), set_var("Sign%d" % i, 1)])])
    s.trigger("End", W - 3, 7, 2, 8, script=[
        text("Twelfth passes. Slowly.", "You can't fly too high. So you walk."),
        text("Then MUJ."),
        say(N["Mayank"], "(from very far) ...room 10. Hey. Glad it's you."),
    ] + back_to_hub(ctx, "Mem7", None, MEMORIES[6][4], s))
    s.script += [
        palette("memory"), music(ctx.music("void")),
        comment("MEMORY 7 - TWELFTH (platformer with a low ceiling: you can't jump high here)"),
        set_pos("player", 2, 14),
    ] + [set_var("Sign%d" % i, 0) for i in range(5)] + [
        text("Twelfth. You can't fly too high. IIT pressure.", "(Left/Right to walk, A to jump. Mind your head.)"),
    ]


def hall(ctx):
    s = ctx.scene("hall", "Hall of Doors", "hall_of_doors", FOLDER, bank="dreamC")
    whatifs = [
        ("If you'd cleared IIT", "A different hostel. Different friends. Somewhere, a different room 10."),
        ("If you'd stayed in London", "Rain. Red buses. A version of you who never learned the word 'mess'."),
        ("If you'd said sorry in 9th", "Maybe. Maybe not. The heart heals the same either way, just slower."),
        ("If you'd never met them", "...", ),
        ("If you'd run, not hidden", "You'd have been somewhere else. The middle would still be the middle."),
    ]
    xs = [4, 10, 16, 21, 23]
    for i, wi in enumerate(whatifs):
        title, line = wi[0], wi[1]
        s.trigger("Door: " + title, xs[i], 6, 1, 1, script=[
            text(title + "?"), text(line),
            text("...and every door opens onto the same cricket ground at dawn.") if i == 3 else gbs.comment("")])
    final_map = ctx.meta("cricket_ground")
    final_entry = open_spot(final_map["collisions"], final_map["cols"], final_map["rows"],
                            final_map["spawn"][0], min(final_map["rows"] - 1, final_map["spawn"][1] + 5))
    s.trigger("The last door", 13, 13, 2, 2, script=[
        text("The last door is just a door. You open it."),
        set_var("Chapter", CH_FINALE),
        goto(ctx.sid_of("finale"), final_entry[0], final_entry[1], "up", fade="1")])
    s.script += [
        palette("dreamC"), music(ctx.music("void")),
        comment("HALL OF DOORS - questioning choices"),
        set_pos("player", 13, 11), face("player", "up"),
        text("A hall of doors. Every 'what if' you ever had, with a handle."),
    ]


def finale(ctx):
    s = ctx.scene("finale", "Reunion at Dawn", "cricket_ground", "6 Finale", bank="dusk")
    m = ctx.meta("cricket_ground")
    def sp(x, y):
        x = max(0, min(m["cols"] - 2, x))
        y = max(1, min(m["rows"] - 1, y))
        return open_spot(m["collisions"], m["cols"], m["rows"], x, y)
    cx, cy = sp(m["spawn"][0], m["spawn"][1])
    ctx.final_entry = sp(cx, min(m["rows"] - 1, cy + 5))
    friends = ["Divyansh", "Kanishk", "Parag", "Anshuman", "Garvita"]
    finals = {
        "Divyansh": (["Bro! I hit it! Six! Over the Dome! ...okay it's a dream, but it COUNTS."],
                     ["I walked the walk. Once. Turns out once is enough."]),
        "Kanishk": (["I finally planned for the one variable. It was you showing up."],
                    ["You played it right. Mostly. That's more than most."]),
        "Parag": (["Second try worked. Look, I'm here. Kind of."],
                  ["Second try. It always works on the second try."]),
        "Anshuman": (["You can see me. Everyone can, here. It's... nice."],
                     ["You can see me. That's enough."]),
        "Garvita": (["I ran so far. And look who's waiting at the finish."],
                    ["Race you to the pavilion. For real this time."]),
    }
    for i, f in enumerate(friends):
        x, y = sp(cx - 10 + i * 5, cy + (2 if i % 2 else 0))
        hi, lo = finals[f]
        s.actor(N[f] + " (dawn)", ctx.sprite(f.lower()), x, y, direction="down", script=[
            if_var("Talked" + f, "==", 0, [inc("FinaleTalks"), set_var("Talked" + f, 1)]),
            if_var("Bond_" + f, ">=", 2, [say(N[f], *hi)], [say(N[f], *lo)]),
        ])
    may = s.actor(N["Mayank"] + " (dawn)", ctx.sprite("mayank"), cx, cy - 4, direction="down", script=[
        if_var("FinaleTalks", "<", 5, [say(N["Mayank"], "Say hi to everyone first. We've got time. Weirdly.")], [
            say(N["Mayank"], "So. You found out? Why you came here?"),
            menu("Pick", ["For you lot", "Still don't know", "To get here"]),
            switch("Pick", {
                1: [say(N["Mayank"], "Cheesy. Correct.")],
                2: [say(N["Mayank"], "That's allowed. That's most people.")],
                3: [say(N["Mayank"], "Yeah. Here. Right here.")],
            }),
            say(N["Mayank"], "You know this isn't real, right?"),
            say("You", "I know."),
            say(N["Mayank"], "Is it enough?"),
        ] + motif() + [
            say("You", "...It's enough."),
            say(N["Mayank"], "Nani was right. It's a circle. You'll end up back where you started."),
            say(N["Mayank"], "Different you. Different place."),
            say(N["Mayank"], "Death isn't the end, room 10. It's just the middle."),
            gbs.fade_out("1"),
            goto(ctx.sid_of("credits"), 9, 9, fade="1"),
        ])])
    s.script += [
        palette("dusk"), music(ctx.music("days")),
        gbs.player_sprite(ctx.sprite("player")),
        comment("FINALE - the reunion. Lines change with each friend's Bond."),
        set_var("FinaleTalks", 0),
    ] + [set_var("Talked" + f, 0) for f in friends] + [
        set_pos("player", *ctx.final_entry), face("player", "up"),
        text("Dawn. The cricket ground. Dew on everything."),
        text("They're all here."),
    ]


def credits(ctx):
    s = ctx.scene("credits", "Credits", "void_stars", "6 Finale", bank="dreamA")
    roll = [
        "DERNIER",
        "a game about the middle",
        "Story, art and life: KC",
        "Friends: Mayank, Divyansh, Kanishk, Parag, Anshuman, Garvita",
        "Inspired by Before Your Eyes, Lost, and Until Then",
        "Music: GB Studio sample songs by Rulz (placeholder)",
        "Map data (c) OpenStreetMap contributors",
        "Made with GB Studio",
        "Draft 1. The end is never the end.",
    ]
    s.script += [hide("player"), palette("dreamA"), music(ctx.music("void"))] + \
                [text(r) for r in roll] + [
        set_var("Chapter", 0),
        goto(ctx.sid_of("title"), 0, 0, fade="1"),
    ]


def build(ctx):
    mem_childhood(ctx)
    mem_flight(ctx)
    mem_london(ctx)
    mem_india(ctx)
    mem_muskaan(ctx)
    mem_ninth(ctx)
    mem_eleventh(ctx)
    mem_twelfth(ctx)
    hall(ctx)
    hub(ctx)
    finale(ctx)
    credits(ctx)
