"""Act 2 - the outbreak (Chapter 4). One friend, one mechanic, one goodbye.

Step  0 rumble + the owner's original B7 scenes (Mayank, the scholar)
      1 B7 lounge council            -> Quess Mess siege (Kanishk, turn-based)
      2 world map -> Hostel Avenue   -> lane defence (Parag, pea shooter)   Parag dies
      3 world map -> Underpass       -> stealth + tunnel (Anshuman)         Anshuman vanishes
      4 world map -> Grand Staircase -> all talk, then a chase (Divyansh)   Divyansh dies
      5 Old Mess last stand (Kanishk, turn-based)                           Kanishk dies
      6 world map -> AB2             -> rooftop run (Garvita, platformer)   Garvita falls
      7 The Dome (Mayank)                                                   -> Act 3

Deaths are written as each character completing their arc. Edit the lines in
GB Studio or the studio; the beats are documented in docs/STORY.md.
"""

import gbs
from gbs import (say, text, set_var, add, inc, if_var, menu, switch, goto, wait, shake, sfx, hide, show,
                 face, move_to, move_rel, comment, music, deactivate, activate, emote, choice, set_pos, flicker,
                 rnd, sub_var, loop_while, input_script, get_pos, speed, if_near, projectile, palette)
from story.common import CH_OUTBREAK, CH_DOME, open_spot, bond, NAMES

N = NAMES
FOLDER = "4 Outbreak"


def lounge(ctx):
    s = ctx.scene("lounge", "B7 Lounge Council", None, FOLDER, legacy_bg="b7_lounge", bank="night")
    from story.common import palette_for
    pos = {"Mayank": (9, 18), "Divyansh": (3, 20), "Kanishk": (11, 21), "Parag": (2, 26),
           "Anshuman": (12, 28), "Garvita": (9, 26)}
    ids = {}
    lc = ctx.legacy["b7_lounge"]
    for f, (x, y) in pos.items():
        x, y = open_spot(lc["collisions"], 32, 32, x, y)
        ids[f] = s.actor(N[f], ctx.sprite(f.lower()), x, y, direction="right").id
    s.script += [
        palette_for(ctx, s, "night"),
        music(ctx.music("outbreak")),
        comment("ACT 2 BEGINS - council in the B7 lounge"),
        set_pos("player", 6, 22), face("player", "up"),
        say(N["Kanishk"], "Facts. Phones dead. Gate guards gone. Those things don't climb stairs well."),
        say(N["Divyansh"], "Zombies. ZOMBIES. Bro, I trained for this. Mentally."),
        say(N["Garvita"], "The Dome. The admin block has the PA system and the satellite phone."),
        say(N["Mayank"], "Then we go to the Dome. Together. Building by building."),
        say(N["Kanishk"], "First the Quess Mess. Food, knives, a door that locks. Turn by turn. I'll call the moves."),
        say(N["Parag"], "The avenue's a straight line. My launcher loves straight lines."),
        say(N["Anshuman"], "The underpass is dark. Dark is mine."),
        say(N["Garvita"], "And from AB2 I can get us across the rooftops. All the way."),
        say(N["Divyansh"], "And I'll... lead. From the front. Probably. Spiritually."),
        say(N["Mayank"], "Okay. Nobody plays hero. Everybody comes back."),
        set_var("Step", 1), set_var("Objective", 10),
        set_var("Alive_Parag", 1), set_var("Alive_Anshuman", 1), set_var("Alive_Divyansh", 1),
        set_var("Alive_Kanishk", 1), set_var("Alive_Garvita", 1), set_var("Alive_Mayank", 1),
        goto(ctx.sid_of("quess_siege"), 3, 12, "right"),
    ]


# ---------------------------------------------------------------------------
# Turn-based battles (Kanishk)
# ---------------------------------------------------------------------------

def battle_engine(waves, ally, ally_move, ally_line, ghoul_ids):
    """Fully event-based turn battle. waves: [(name, hp)]"""
    hp, zhp = gbs.V["HP"], gbs.V["ZHP"]
    turn = [
        gbs.raw("YOU      HP $%s$\nZOMBIES  HP $%s$" % (hp, zhp)),
        menu("Pick", ["Attack", ally_move, "Barrier", "Snack"]),
        switch("Pick", {
            1: [rnd("Tmp", 3, 6), if_var("Read", "!=", 0, [add("Tmp", 5), set_var("Read", 0),
                                                           say(ally, "Now! Left flank!")]),
                text("You swing the mess ladle!"), shake(0.2, 3), sfx("crash", 3, 300, 0.2), sub_var("ZHP", "Tmp")],
            2: [say(ally, ally_line), set_var("Read", 1)],
            3: [text("You drag a table across. Guard up."), set_var("Guard", 1)],
            4: [if_var("Snacks", ">", 0, [
                    add("Snacks", -1), add("HP", 8), if_var("HP", ">", 30, [set_var("HP", 30)]),
                    gbs.raw("Cold Maggi. +8 HP\nSnacks left: $%s$" % gbs.V["Snacks"])],
                    [text("No snacks left. The packet is just air and regret.")])],
        }),
        if_var("ZHP", ">", 0, [
            rnd("Tmp", 2, 5),
            if_var("Guard", "!=", 0, [add("Tmp", -4), set_var("Guard", 0), text("The table holds... mostly.")]),
            text("The zombies lurch forward!"), shake(0.3, 4), sub_var("HP", "Tmp"),
            if_var("HP", "<=", 0, [
                say(ally, "Rewind. Same opening. Better moves."),
                set_var("HP", 30), set_var("ZHP", 0), set_var("Wave", 0), set_var("Lost", 1),
            ]),
        ]),
    ]
    run_waves = [set_var("HP", 30), set_var("Wave", 0), set_var("Lost", 1)]
    assist = [if_var("Bond_Kanishk", ">=", 1, [set_var("Read", 1), say(ally, "I already read this wave. First hit, double.")])]
    body = [set_var("Lost", 0)]
    for i, (name, whp) in enumerate(waves):
        body.append(if_var("Lost", "==", 0, [
            set_var("Wave", i + 1), set_var("ZHP", whp), set_var("Read", 0), set_var("Guard", 0),
            set_var("HP", 30), set_var("Snacks", 3),
            text("WAVE %d: %s" % (i + 1, name)),
        ] + assist + [
            loop_while("ZHP", ">", 0, turn),
            if_var("Lost", "==", 0, [text("Wave %d down." % (i + 1))] +
                   ([flicker(ghoul_ids[i], 0.5), deactivate(ghoul_ids[i])] if i < len(ghoul_ids) else [])),
        ]))
    return run_waves + [loop_while("Lost", "==", 1, body)]


def quess_siege(ctx):
    s = ctx.scene("quess_siege", "Quess Mess Siege (Kanishk)", "battle_zombie", FOLDER, bank="night")
    kan = s.actor(N["Kanishk"], ctx.sprite("kanishk"), 4, 10, direction="right")
    g = [s.actor("Ghoul %d" % i, ctx.sprite("ghoul"), 13 + (i % 2) * 2, 7 + i * 3, direction="left").id
         for i in range(3)]
    s.script += [
        palette("night"), music(ctx.music("battle")),
        comment("KANISHK - TURN-BASED. Waves are listed in battle_engine(); tune HP there."),
        set_pos("player", 3, 13), face("player", "right"),
        say(N["Kanishk"], "They're slow. They don't plan. We do. One move at a time."),
        say(N["Kanishk"], "When I 'Read' them, your next hit lands double. Trust the read."),
    ] + battle_engine([("Mess queue", 14), ("Second shift", 18), ("The Hungry Senior", 24)],
                      N["Kanishk"], "Read", "Pattern: they turn left when they lunge. Next hit, double.", g) + [
        say(N["Kanishk"], "Formation holds. I'll lock the mess and plan the retreat."),
        say(N["Kanishk"], "Go. The avenue. Parag's waiting. I'll meet you at the Old Mess. That's the plan."),
        choice("Pick", "Come with us", "Stick to plan"),
        if_var("Pick", "==", 1, [say(N["Kanishk"], "Someone has to hold a door. I calculated it. It's me."),
                                 bond("Kanishk")],
               [say(N["Kanishk"], "Good. You're learning.")]),
        set_var("Step", 2), set_var("Objective", 11),
        goto(ctx.sid_of("world"), *ctx.world_return["quess_mess"], "down"),
    ]


def old_mess(ctx):
    s = ctx.scene("old_mess_stand", "Old Mess Last Stand (Kanishk)", "battle_zombie", FOLDER, bank="blood")
    kan = s.actor(N["Kanishk"], ctx.sprite("kanishk"), 4, 10, direction="right")
    g = [s.actor("Ghoul %d" % i, ctx.sprite("ghoul"), 13 + (i % 2) * 2, 6 + i * 3, direction="left").id
         for i in range(4)]
    s.script += [
        palette("blood"), music(ctx.music("battle")),
        comment("KANISHK'S LAST STAND - his arc: the planner meets the variable he can't plan for"),
        set_pos("player", 3, 13), face("player", "right"),
        say(N["Kanishk"], "You made it. I had a 61 percent estimate on that. Glad I was wrong low."),
        say(N["Kanishk"], "Old Mess. Two doors. We hold this, then you go up to AB2."),
    ] + battle_engine([("Old Mess regulars", 18), ("Kitchen crew", 22), ("The horde", 30)],
                      N["Kanishk"], "Read", "Watch the third one. It leads. Hit it.", g) + [
        say(N["Kanishk"], "...Huh."),
        say("You", "Kanishk. Your arm."),
        say(N["Kanishk"], "During wave two. I accounted for every move on the board."),
        say(N["Kanishk"], "Except the one piece I never count. Me."),
        say(N["Kanishk"], "I'll lock the door from inside. Ninety seconds, minimum. Go up to AB2."),
        say(N["Kanishk"], "And hey. You'd have lost in ten moves. Next time, eleven."),
        flicker(kan.id, 1.0), deactivate(kan.id),
        set_var("Alive_Kanishk", 0),
        set_var("Step", 6), set_var("Objective", 14),
        goto(ctx.sid_of("world"), *ctx.world_return["grand_staircase"], "down"),
    ]


# ---------------------------------------------------------------------------
# Lane defence (Parag)
# ---------------------------------------------------------------------------

LANES = [4, 7, 10, 13, 16]


def lanes(ctx):
    meta = ctx.meta("lanes_avenue")
    s = ctx.scene("lanes", "Avenue Lane Defence (Parag)", "lanes_avenue", FOLDER, bank="night")
    # the player may only move up and down the defence column (x 2..3)
    import gbc
    coll = [0x0F] * (20 * 18)
    for y in range(3, 18):
        for x in (2, 3):
            coll[y * 20 + x] = 0
    s.collisions = gbc.compress8(coll)
    par = s.actor(N["Parag"], ctx.sprite("parag"), 0, 3, direction="right")
    zombies = []
    for i, ly in enumerate(LANES):
        z = s.actor("Lane %d ghoul" % (i + 1), ctx.sprite("ghoul"), 17 + (i % 2), ly, direction="left",
                    collision_group="1", move_speed=0.5 if i % 2 else 1)
        z.update = [
            if_var("LaneOn", "==", 1, [
                move_rel("$self$", -1, 0),
                gbs.wait(0.45 + 0.15 * (i % 3)),
                get_pos("$self$", "ZX%d" % i, "ZY%d" % i),
                if_var("ZX%d" % i, "<=", 4, [
                    sfx("crash", 2, 120, 0.3), shake(0.2, 3), add("Lives", -1),
                    set_pos("$self$", 18, ly)]),
            ], [gbs.wait(0.1)]),
        ]
        z.hit1 = [inc("Kills"), sfx("crash", 4, 600, 0.1), flicker("$self$", 0.2), set_pos("$self$", 18, ly)]
        zombies.append(z)
    referee = s.actor("Referee", ctx.sprite("orb"), 19, 1)
    zids = [z.id for z in zombies]
    stop_all = [set_var("LaneOn", 0)] + [deactivate(z) for z in zids]
    win = stop_all + [
        gbs.remove_input("a"),
        say(N["Parag"], "FIFTEEN! The Mark I is a legend! A LEGEND--"),
        sfx("noise", 3, 200, 0.4),
        say("", "CLK. CLK. The launcher jams."),
        say(N["Parag"], "...jammed. Of course. Once, when it matters. I said 'when it doesn't'."),
    ] + [activate(z) for z in zids] + [set_pos(z, 12, LANES[i]) for i, z in enumerate(zids)] + [
        say(N["Parag"], "Go. Underpass. I'll clear it. I always clear it. Second try, remember?"),
        choice("Pick", "Not without you", "Clear it fast"),
        if_var("Pick", "==", 1, [say(N["Parag"], "Bro. Somebody has to build the second try. GO."), bond("Parag")],
               [say(N["Parag"], "That's the spirit. Burnt chip's in my wallet. For luck.")]),
        move_to(par.id, 6, 3), flicker(par.id, 1.2), deactivate(par.id),
        say("", "Behind you, the launcher fires once more. Then once more. Then nothing."),
        set_var("Alive_Parag", 0),
        set_var("Step", 3), set_var("Objective", 12),
        goto(ctx.sid_of("world"), *ctx.world_return["hostel_avenue"], "down"),
    ]
    lose = stop_all + [
        gbs.remove_input("a"),
        say(N["Parag"], "Overrun! Okay, okay. Reset. Again. Second try."),
        goto(ctx.sid_of("lanes"), 2, 10, "right", fade="1"),
    ]
    referee.update = [
        if_var("LaneOn", "==", 1, [
            if_var("Kills", ">=", 15, win),
            if_var("Lives", "<=", 0, lose),
        ]),
        gbs.wait(0.1),
    ]
    referee.start = [hide("$self$"), gbs.collisions_off("$self$")]
    ctx.level_start["lanes"] = (2, 10)
    s.script += [
        palette("night"), music(ctx.music("chase")),
        comment("PARAG - PEA SHOOTER LANES. Up/Down to change lane, A to fire. 15 kills wins, 5 breaches loses."),
        set_pos("player", 2, 10), face("player", "right"),
        set_var("Kills", 0), set_var("Lives", 5), set_var("LaneOn", 0),
        if_var("Bond_Parag", ">=", 1, [set_var("Lives", 7),
                                       say(N["Parag"], "Spare barrels from the workshop. Two extra lives, partner.")]),
        say(N["Parag"], "Five lanes. Up and down to pick one. A to fire. Don't let them past the hedge."),
        say(N["Parag"], "Fifteen and the avenue's clear. Easy. Probably."),
        input_script("a", [face("player", "right"),
                           projectile(ctx.sprite("pea"), "player", "right", 4, 1.4, "1")]),
        set_var("LaneOn", 1),
    ]


# ---------------------------------------------------------------------------
# Stealth (Anshuman)
# ---------------------------------------------------------------------------

def stealth(ctx):
    meta = ctx.meta("underpass")
    s = ctx.scene("stealth", "Underpass Stealth (Anshuman)", "underpass", FOLDER, bank="night")
    W, H = meta["cols"], meta["rows"]
    sp = lambda x, y: open_spot(meta["collisions"], W, H, x, y)
    start = sp(6, 41)
    ctx.level_start["stealth"] = start
    door = [d for d in meta["doors"] if "hostel" in d["label"]][0]
    patrols = [((2, 34), (30, 34)), ((40, 27), (14, 27)), ((4, 18), (36, 18)), ((30, 10), (16, 10))]
    ghouls = []
    for i, (a, b) in enumerate(patrols):
        a, b = sp(*a), sp(*b)
        g = s.actor("Patrol %d" % (i + 1), ctx.sprite("ghoul"), a[0], a[1], direction="right",
                    move_speed=0.5 if i % 2 else 1)
        g.update = [move_to("$self$", b[0], b[1]), wait(0.4), move_to("$self$", a[0], a[1]), wait(0.4)]
        ghouls.append(g.id)
    hides = [(5, 30), (22, 30), (8, 22), (26, 22), (14, 14), (36, 14), (24, 6)]
    for i, (x, y) in enumerate(hides):
        x, y = sp(x, y)
        s.trigger("Shadow %d" % (i + 1), x, y - 1, 3, 2,
                  script=[set_var("Hidden", 1), say(N["Anshuman"], "(radio) Good. You're a shadow.")
                          if i == 0 else set_var("Hidden", 1)],
                  leave=[set_var("Hidden", 0)])
    watcher = s.actor("Watcher", ctx.sprite("orb"), W - 2, 1)
    caught = [
        set_var("Spotted", 1),
        sfx("crash", 4, 200, 0.4), shake(0.5, 4),
        say("", "!! SPOTTED !!"),
        say(N["Anshuman"], "(radio) Back. Back to the last shadow. Breathe. Again."),
        set_pos("player", start[0], start[1]), set_var("Spotted", 0), set_var("Hidden", 0),
    ]
    watcher.start = [hide("$self$"), gbs.collisions_off("$self$")]
    watcher.update = [
        if_var("Hidden", "==", 0, [
            if_var("Bond_Anshuman", ">=", 1, [if_near("player", g, 1, caught) for g in ghouls],
                   [if_near("player", g, 2, caught) for g in ghouls])]),
        wait(0.05),
    ]
    tx, ty = ctx.entry["underpass_tunnel_west"]
    sx, sy = door["spawn"]
    s.trigger("Tunnel door", sx, sy, 2, 1, script=[
        say(N["Anshuman"], "(radio) The tunnel. I'm inside already. Come."),
        goto(ctx.sid_of("tunnel"), tx, ty, "right"),
    ])
    s.script += [
        palette("night"), music(ctx.music("stealth")),
        comment("ANSHUMAN - STEALTH. Patrols walk fixed routes; shadows (triggers) hide you."),
        set_pos("player", start[0], start[1]), face("player", "up"),
        set_var("Hidden", 0),
        say(N["Anshuman"], "(radio) Splinter rules. Patrols walk lines. Lines have gaps."),
        say(N["Anshuman"], "(radio) Get within two steps of one in the open and it sees you.",
            "Stand in a shadow and you don't exist. Reach the hostel-side tunnel door, top left."),
        if_var("Bond_Anshuman", ">=", 1, [say(N["Anshuman"], "(radio) You walked the trail with me. You're quieter now. One step is enough.")]),
    ]


def tunnel(ctx):
    s = ctx.scene("tunnel", "The Tunnel (Anshuman)", "underpass_tunnel", FOLDER, bank="night")
    tx, ty = ctx.entry["underpass_tunnel_west"]
    ans = s.actor(N["Anshuman"], ctx.sprite("anshuman"), tx + 4, ty, direction="right")
    s.script += [
        palette("night"),
        comment("ANSHUMAN'S GOODBYE - he becomes what he always was: unseen, and kind"),
        set_pos("player", tx, ty), face("player", "right"),
        say(N["Anshuman"], "Listen. Hear that? University side. A lot of them."),
        say(N["Anshuman"], "I'll go first and pull them off. Count to sixty. Then run straight."),
        say("You", "Anshuman--"),
        say(N["Anshuman"], "It's okay. I like the dark. Nobody notices the guy who doesn't want to be noticed."),
        say(N["Anshuman"], "But you did. Thanks for that."),
        move_to(ans.id, 29, ty), deactivate(ans.id),
        wait(1.0),
        say("", "(radio) ...it's quiet out here... the peacocks are..."),
        sfx("noise", 1, 100, 1.5), shake(0.3, 1),
        say("", "(radio) KSSSHHHHHHHHHH."),
        say("You", "...one. Two. Three..."),
        set_var("Alive_Anshuman", 0), bond("Anshuman"),
        set_var("Step", 4), set_var("Objective", 13),
    ]
    # east exit: back to the world on the university side
    s.trigger("Out (university side)", 31, ty - 1, 1, 3, script=[
        if_var("Step", ">=", 4, [goto(ctx.sid_of("world"), *ctx.world_return["grand_staircase"], "down")])])


# ---------------------------------------------------------------------------
# All talk, no walk (Divyansh) + chase
# ---------------------------------------------------------------------------

def divyansh(ctx):
    meta = ctx.meta("grand_staircase")
    s = ctx.scene("staircase_stand", "Grand Staircase (Divyansh)", "grand_staircase", FOLDER, bank="night")
    W, H = meta["cols"], meta["rows"]
    sp = lambda x, y: open_spot(meta["collisions"], W, H, x, y)
    px, py = sp(24, 50)
    ctx.level_start["staircase_stand"] = (px, py)
    dv = s.actor(N["Divyansh"], ctx.sprite("divyansh"), *sp(26, 48), direction="up")
    may = s.actor(N["Mayank"], ctx.sprite("mayank"), *sp(21, 50), direction="up")
    gar = s.actor(N["Garvita"], ctx.sprite("garvita"), *sp(28, 51), direction="up")
    horde = [s.actor("Horde %d" % i, ctx.sprite("ghoul"), *sp(18 + i * 3, 42), direction="down").id
             for i in range(4)]
    chasers = []
    for i in range(3):
        c = s.actor("Chaser %d" % i, ctx.sprite("ghoul"), *sp(22 + i * 4, 40), direction="down",
                    move_speed=0.5)
        c.start = [deactivate("$self$")]
        c.update = [
            if_var("Chase", "==", 1, [
                get_pos("player", "PX", "PY"), gbs.move_to_vars("$self$", "PX", "PY"),
                if_near("$self$", "player", 1, [set_var("Caught", 1)])]),
            wait(0.35)]
        chasers.append(c.id)
    goal = sp(4, 55)
    reset_chase = [set_var("Chase", 0), set_var("Caught", 0),
                   say("", "Hands grab your sleeve. You tear free and fall back down the steps."),
                   set_pos("player", px, py)] + \
                  [set_pos(cid, *sp(22 + i * 4, 40)) for i, cid in enumerate(chasers)] + [wait(1.0), set_var("Chase", 1)]
    ref = s.actor("Referee", ctx.sprite("orb"), W - 2, 1, start=[hide("$self$"), gbs.collisions_off("$self$")])
    ref.update = [if_var("Caught", "==", 1, reset_chase), wait(0.1)]
    s.trigger("Escape", goal[0] - 1, goal[1] - 2, 4, 4, script=[
        if_var("Chase", "==", 1, [
            set_var("Chase", 0)] + [deactivate(cid) for cid in chasers] + [
            say(N["Mayank"], "Old Mess! Kanishk's light is on!"),
            set_var("Step", 5),
            goto(ctx.sid_of("old_mess_stand"), 3, 13, "right")])])
    talk = [
        say(N["Divyansh"], "Okay. OKAY. Listen. I've got this. I've literally been waiting my whole life."),
        menu("Pick", ["You've got this", "Divyansh, run", "We go together"]),
        switch("Pick", {
            1: [say(N["Divyansh"], "SEE? Finally someone gets it."), bond("Divyansh")],
            2: [say(N["Divyansh"], "Run? Bro. I've been running my mouth for 18 years. Time to run the other thing.")],
            3: [say(N["Divyansh"], "Together's slow. I'm slow. Do the math, Kanishk would.")],
        }),
        say(N["Divyansh"], "Everyone back home says I'm all talk. Big promises. No follow through."),
        say(N["Divyansh"], "Gym on Monday. Topper by sem two. Six over the Dome."),
        say(N["Divyansh"], "Watch me walk the walk. ONCE."),
        say(N["Garvita"], "Divyansh, NO--"),
        speed(dv.id, 2), move_to(dv.id, 24, 42),
    ]
    death = [
        shake(0.8, 5), sfx("crash", 4, 100, 0.8),
    ] + [move_to(h, 24, 43) for h in horde] + [
        say(N["Divyansh"], "HA! See?! I'm doing it! I'm actually--"),
        flicker(dv.id, 1.5), deactivate(dv.id),
        say(N["Divyansh"], "(far away) ...tell my mom I topped. Lie a little..."),
        set_var("Alive_Divyansh", 0),
        say(N["Mayank"], "He bought us the whole staircase. MOVE!"),
        deactivate(may.id), deactivate(gar.id),
        say("", "RUN for the Old Mess, down the path to the south-west!"),
    ] + [activate(cid) for cid in chasers] + [
        if_var("Bond_Divyansh", ">=", 1, [deactivate(chasers[2]),
                                          say("", "One of them is still stuck on Divyansh. He's still buying you time.")]),
        wait(1.0), set_var("Chase", 1), set_var("Caught", 0)]
    s.script += [
        palette("night"), music(ctx.music("outbreak")),
        comment("DIVYANSH - ALL TALK, NO WALK. Then he walks. Then the chase."),
        set_pos("player", px, py), face("player", "up"), set_var("Chase", 0), set_var("Caught", 0),
    ] + talk + death


# ---------------------------------------------------------------------------
# Rooftop run (Garvita, platformer)
# ---------------------------------------------------------------------------

def rooftop(ctx):
    meta = ctx.meta("rooftop_run")
    s = ctx.scene("rooftop", "Rooftop Run (Garvita)", "rooftop_run", FOLDER, kind="PLATFORM", bank="night")
    W = meta["cols"]
    blocks = meta["blocks"]
    gar = s.actor(N["Garvita"], ctx.sprite("garvita"), 6, blocks[0][2] - 1, direction="right")
    ctx.level_start["rooftop"] = (2, blocks[0][2] - 1)
    # checkpoints at the start of every rooftop; falling sends you back to the last one
    for i, (bx, bw, top) in enumerate(blocks):
        s.trigger("Checkpoint %d" % i, bx + 1, top - 3, 1, 3,
                  script=[set_var("CheckX", bx + 1), set_var("CheckY", top - 1)])
    s.trigger("Fall", 0, 17, W, 1, script=[
        shake(0.3, 3), say(N["Garvita"], "Got you! Again. Momentum, then jump."),
        gbs.set_pos_vars("player", "CheckX", "CheckY")])
    # roof ghouls pace their roof; touching one knocks you back to the checkpoint
    for i, (bx, bw, top) in enumerate(blocks[2::3]):
        g = s.actor("Roof ghoul %d" % i, ctx.sprite("ghoul"), bx + 2, top - 1, direction="left", move_speed=0.5,
                    start=[if_var("Bond_Garvita", ">=", 1, [deactivate("$self$")])])
        g.update = [move_to("$self$", bx + bw - 3, top - 1), move_to("$self$", bx + 2, top - 1),
                    if_near("$self$", "player", 1, [shake(0.3, 3), gbs.set_pos_vars("player", "CheckX", "CheckY")])]
    last = blocks[-1]
    s.trigger("The Dome", last[0] + 2, last[2] - 4, 3, 4, script=[
        set_var("Step", 7),
        say(N["Garvita"], "Last gap. I'll jump first and catch you. Like at the ground."),
        shake(0.6, 4), sfx("crash", 3, 100, 0.6),
        say("", "The ledge under her crumbles. She catches the edge with one hand."),
        say("You", "GARVITA!"),
        say(N["Garvita"], "Hey. Don't. If you grab me we both go."),
        say(N["Garvita"], "Funny. I always wanted to run so far nobody could call me back."),
        say(N["Garvita"], "...it's nice that someone's waiting at the finish."),
        flicker(gar.id, 1.2), deactivate(gar.id),
        set_var("Alive_Garvita", 0), bond("Garvita"),
        goto(ctx.sid_of("dome_night"), 13, 13, "up", fade="1"),
    ])
    s.script += [
        palette("night"), music(ctx.music("chase")),
        comment("GARVITA - PLATFORMER over the AB2 rooftops to the Dome"),
        set_var("CheckX", 2), set_var("CheckY", blocks[0][2] - 1),
        set_pos("player", 2, blocks[0][2] - 1),
        say(N["Garvita"], "Rooftops all the way to the Dome. Left/Right to run, A to jump."),
        say(N["Garvita"], "Don't look down. Actually, look down a bit. Gaps are down."),
        if_var("Bond_Garvita", ">=", 1, [say(N["Garvita"], "I cleared the roofs on my warm-up lap. You're welcome.")]),
        speed(gar.id, 2), move_to(gar.id, blocks[1][0] + 2, blocks[1][2] - 1),
    ]


# ---------------------------------------------------------------------------
# The Dome (Mayank) -> Act 3
# ---------------------------------------------------------------------------

def dome_night(ctx):
    s = ctx.scene("dome_night", "Under the Dome (Mayank)", "dome_in", FOLDER, bank="night")
    may = s.actor(N["Mayank"], ctx.sprite("mayank"), 13, 8, direction="down")
    s.script += [
        palette("night"), music(ctx.music("void")),
        comment("MAYANK - the last friend, the first question"),
        set_pos("player", 13, 13), face("player", "up"),
        say(N["Mayank"], "You made it. I took the long way. Through the library. Sat down for a bit."),
        say("You", "The PA. The phone. We can call--"),
        say(N["Mayank"], "Already did. Nobody's coming tonight."),
        say(N["Mayank"], "Hey. Look at the ceiling. The dome. It's beautiful from underneath."),
        say(N["Mayank"], "I got bit on the staircase. When Divyansh ran. It's fine. It doesn't hurt much."),
        choice("Pick", "No. No no no.", "Sit with him"),
        if_var("Pick", "==", 1, [say(N["Mayank"], "Yeah. Same."), say(N["Mayank"], "Sit with me anyway.")],
               [say(N["Mayank"], "Thanks.")]),
        bond("Mayank"),
        say(N["Mayank"], "You never answered me. Behind B7. Why did you come here?"),
        say("You", "I... I don't know."),
        say(N["Mayank"], "Then go find out. I think it's all still in there. Everything before this."),
        say(N["Mayank"], "My nani said life is a circle. So this isn't the end."),
        say(N["Mayank"], "It's just... the middle."),
        flicker(may.id, 1.5), deactivate(may.id),
        set_var("Alive_Mayank", 0),
        shake(1.0, 2), gbs.fade_out("1"),
        set_var("Chapter", CH_DOME), set_var("Step", 0), set_var("Objective", 16),
        gbs.save_game(),
        goto(ctx.sid_of("hub"), 9, 12, "up", fade="1"),
    ]


def world_gates(ctx):
    """During the outbreak, world-map entrances lead to the next level only."""
    routes = {"hostel_avenue": (2, "lanes", (2, 10)), "underpass": (3, "stealth", None),
              "grand_staircase": (4, "staircase_stand", None), "ab2": (6, "rooftop", None)}

    def make(target):
        def gate(default):
            act2 = []
            if target in routes:
                step, scene, xy = routes[target]
                xy = ctx.level_start.get(scene, xy or (2, 2))
                act2.append(if_var("Step", "==", step, [goto(ctx.sid_of(scene), xy[0], xy[1], "right")],
                                   [say("", "No time. Stick to the plan. (Check START for the objective.)")]))
            elif target == "legacy_b7_front":
                act2.append(say("", "B7 is overrun. There's no going back."))
            else:
                act2.append(say("", "Shapes move behind the windows. Not here. Not now."))
            return [if_var("Chapter", "==", CH_OUTBREAK, act2, default)]
        return gate
    for t in ctx.loc_trig:
        ctx.loc_gate[t] = make(t)
    w = ctx.scenes["world"]
    w.script += [if_var("Chapter", "==", CH_OUTBREAK, [
        music(ctx.music("outbreak")),
        if_var("Step", "==", 2, [say("", "The campus is dark. Hostel Avenue - Parag is waiting.")]),
    ])]


def fix_stealth_start(ctx):
    # stealth/staircase/rooftop scenes set the player position in their init script, so the
    # world gate can drop the player anywhere; nothing to do here (kept for clarity)
    return None


def build(ctx):
    lounge(ctx)
    quess_siege(ctx)
    lanes(ctx)
    stealth(ctx)
    tunnel(ctx)
    divyansh(ctx)
    old_mess(ctx)
    rooftop(ctx)
    dome_night(ctx)
    world_gates(ctx)
