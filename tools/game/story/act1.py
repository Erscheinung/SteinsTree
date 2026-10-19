"""Act 1 - three Persona-style days of first-year B.Tech CSE at MUJ.

Day 1 (Chapter 1): Engineering Physics (AB1) -> dinner at the Quess Mess ->
                   free evening (hang out with one friend) -> sleep.
Day 2 (Chapter 2): Engineering Mathematics (AB2) -> cricket match ->
                   free evening -> sleep.
Day 3 (Chapter 3): Chemistry lab (AB3) -> Workshop (saw practical, Parag
                   builds his launcher) -> night walk behind B7 -> sleep,
                   and the outbreak begins at 3:07 AM.

Phase: 0 morning/class, 1 after class, 2 evening, 3 night.
Objective (shown by the marker on the world map and in the pause menu).
"""

import gbs
from gbs import (say, text, set_var, add, inc, if_var, menu, switch, goto, wait, shake, sfx, hide, show,
                 face, move_to, comment, music, deactivate, emote, choice, set_pos, flicker, rnd, loop_while,
                 input_script, remove_input, get_pos, speed)
from story.common import (CH_DAY1, CH_DAY2, CH_DAY3, CH_OUTBREAK, open_spot, bond, at, NAMES)

N = NAMES
FOLDER = "3 Days"


def only_when(ch, ph):
    """startScript: actor exists only in chapter ch / phase ph."""
    return [if_var("Chapter", "!=", ch, [deactivate("$self$")], [
        if_var("Phase", "!=", ph, [deactivate("$self$")])])]


def spot(ctx, map_name, x, y, avoid=()):
    m = ctx.meta(map_name)
    return open_spot(m["collisions"], m["cols"], m["rows"], x, y, avoid)


# ---------------------------------------------------------------------------
# B7 room (the owner's "Outside" scene): morning call and going to sleep.
# Used by story.legacy, which wraps the original outbreak rumble in Chapter 4.
# ---------------------------------------------------------------------------

def room_script(ctx):
    sleep_next = lambda ch, card: [
        say("", "The fan creaks. Somewhere a speaker plays the same song for the fourth time."),
        say("You", "...okay. Today was okay."),
        gbs.fade_out("1"),
        set_var("Chapter", ch), set_var("Phase", 0), set_var("Hung", 0),
        set_var("Objective", {CH_DAY2: 5, CH_DAY3: 7, CH_OUTBREAK: 0}[ch]),
        set_var("CardDay", card),
        gbs.save_game(),
        goto(ctx.sid_of("day_card"), 1, 16, fade="1"),
    ]
    return [
        gbs.text_speed(1),
        if_var("Phase", "==", 3, [
            switch("Chapter", {
                CH_DAY1: sleep_next(CH_DAY2, 2),
                CH_DAY2: sleep_next(CH_DAY3, 3),
                CH_DAY3: [
                    say("You", "Why did I come here?", "...", "Ask me tomorrow."),
                    gbs.fade_out("1"),
                    set_var("Chapter", CH_OUTBREAK), set_var("Phase", 0), set_var("Step", 0),
                    set_var("Objective", 0), set_var("CardDay", 4),
                    gbs.save_game(),
                    goto(ctx.sid_of("day_card"), 1, 16, fade="1"),
                ],
            }),
        ], [
            if_var("Phase", "==", 0, [
                music(ctx.music("days")),
                switch("Chapter", {
                    CH_DAY1: [
                        comment("DAY 1 MORNING"),
                        sfx("noise", 4, 200, 0.3), shake(0.2, 2),
                        say("", "KNOCK KNOCK KNOCK."),
                        say(N["Mayank"], "Bro! Physics! AB1! Nine o'clock!",
                            "Prof. Rao takes attendance like it's the national census."),
                        say("You", "It's 8:52."),
                        say(N["Mayank"], "Then RUN. Through the hostel gate, down the underpass. AB1 is right there."),
                        say("", "(Press START any time for the menu. The ! on the campus map is where you need to be.)"),
                    ],
                    CH_DAY2: [
                        comment("DAY 2 MORNING"),
                        say(N["Mayank"], "Maths today. AB2, room 214. Bring a pen.",
                            "Bring two. Divyansh will 'borrow' one forever."),
                    ],
                    CH_DAY3: [
                        comment("DAY 3 MORNING"),
                        say(N["Mayank"], "Chem lab in AB3, then Workshop after lunch.",
                            "Closed shoes. The instructor checks. He checked my soul once."),
                    ],
                }),
            ]),
        ]),
    ]


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------

def quiz(prof, questions):
    """questions: [(question, [3 options], correct_index_1based, right_line, wrong_line)]"""
    out = []
    for q, opts, correct, right, wrong in questions:
        out += [say(prof, q), menu("Pick", opts),
                if_var("Pick", "==", correct, [say(prof, right), inc("Grade")], [say(prof, wrong)])]
    return out


def physics(ctx):
    s = ctx.scenes["physics_class"]
    cond = only_when(CH_DAY1, 0)
    prof = s.actor("Prof Rao", ctx.sprite("prof_m"), 14, 4, start=cond)
    may = s.actor(N["Mayank"], ctx.sprite("mayank"), 8, 7, direction="up", start=cond)
    div = s.actor(N["Divyansh"], ctx.sprite("divyansh"), 5, 10, direction="up", start=cond)
    kan = s.actor(N["Kanishk"], ctx.sprite("kanishk"), 15, 7, direction="up", start=cond)
    st1 = s.actor("Student 1", ctx.sprite("student"), 2, 10, direction="up", start=cond)
    st2 = s.actor("Student 2", ctx.sprite("student"), 18, 13, direction="up", start=cond)
    P = "Prof. Rao"
    s.script += [at(CH_DAY1, 0, [
        comment("DAY 1 - ENGINEERING PHYSICS (AB1-101)"),
        set_pos("player", 11, 13), move_to("player", 11, 7), face("player", "up"),
        say(P, "Roll number 47? ...47? Proxy is a crime, beta. Present yourself."),
        say("You", "Present, sir!"),
        say(P, "Today: the dual nature of light. Is it a wave? Is it a particle?"),
        say(N["Divyansh"], "(whispering) Sir doesn't know. I'll explain it to him after class."),
        say(N["Kanishk"], "(not looking back) You will not."),
        say(P, "Pop quiz! Three questions. Hands off your phones, I can see the glow."),
    ] + quiz(P, [
        ("Planck's constant has units of...?", ["J s", "kg/m", "vibes"], 1,
         "Correct! Joule-second. Someone attended JEE classes.", "Vibes is not an SI unit. Yet."),
        ("Light behaves as...?", ["only a wave", "only a particle", "both"], 3,
         "Both! Like you all: a wave at 9 AM, a particle at 9 PM.", "Half marks for confidence. Zero for physics."),
        ("Photon energy rises if wavelength...", ["increases", "decreases", "goes home"], 2,
         "Shorter wavelength, more energy. Like this class.", "It may go home. You may not."),
    ]) + [
        say(N["Divyansh"], "Easy. I would have got all three. I was just letting you have them."),
        say(N["Mayank"], "(quietly) He got zero last week. In the test about his own name."),
        sfx("tone", 3, 900, 0.4),
        say(P, "Bell. Go. Read Chapter 2. You won't. But go."),
        flicker(prof.id, 0.3), deactivate(prof.id), deactivate(st1.id), deactivate(st2.id),
        say(N["Mayank"], "Dinner at Quess Mess tonight. The whole gang. Divyansh promised to pay."),
        say(N["Divyansh"], "I promised to THINK about paying. Big difference."),
        say(N["Kanishk"], "Fifty rupees says he forgets his wallet."),
        set_var("Phase", 1), set_var("Objective", 2), bond("Mayank"),
        deactivate(div.id), deactivate(kan.id), deactivate(may.id),
    ])]


def maths(ctx):
    s = ctx.scenes["maths_class"]
    cond = only_when(CH_DAY2, 0)
    prof = s.actor("Prof Iyer", ctx.sprite("prof_f"), 4, 5, start=cond)
    may = s.actor(N["Mayank"], ctx.sprite("mayank"), 7, 7, direction="up", start=cond)
    div = s.actor(N["Divyansh"], ctx.sprite("divyansh"), 12, 10, direction="up", start=cond)
    kan = s.actor(N["Kanishk"], ctx.sprite("kanishk"), 2, 7, direction="up", start=cond)
    gar = s.actor(N["Garvita"], ctx.sprite("garvita"), 17, 10, direction="up", start=cond)
    P = "Prof. Iyer"
    s.script += [at(CH_DAY2, 0, [
        comment("DAY 2 - ENGINEERING MATHEMATICS (AB2-214)"),
        set_pos("player", 9, 14), move_to("player", 9, 7), face("player", "up"),
        say(P, "Good morning. Today we integrate. Emotionally and mathematically."),
        say(N["Garvita"], "(to you) I sat in the back so I can leave first. Strategy."),
        say(N["Kanishk"], "That's not strategy. That's an exit."),
    ] + quiz(P, [
        ("The integral of e^x dx is...?", ["e^x + C", "x e^x", "e"], 1,
         "Yes. Never forget the + C. It is the C of compassion.", "Close. Painfully close. Wrong."),
        ("Rank of the 3x3 identity matrix?", ["0", "1", "3"], 3,
         "Three! Full rank, like your attendance should be.", "Identity has full rank. Like your confidence."),
        ("Divyansh says 1/0 = 'infinity, easy'. Is he...", ["right", "undefined", "Divyansh"], 2,
         "Undefined. Much like his plans.", "Mathematically, Divyansh is a constant. Not a correct one."),
    ]) + [
        say(N["Divyansh"], "Ma'am, I did all three in my head. My head just doesn't have a pen."),
        say(P, "Then lend your head a pen. Class dismissed."),
        say(N["Garvita"], "Cricket match after class! Hostel vs. Hostel. Ground near AB3."),
        say(N["Divyansh"], "I will hit a six. First ball. Write it down."),
        say(N["Kanishk"], "Writing it down. For evidence."),
        set_var("Phase", 1), set_var("Objective", 6),
        deactivate(prof.id), deactivate(may.id), deactivate(div.id), deactivate(kan.id), deactivate(gar.id),
    ])]


def chem(ctx):
    s = ctx.scenes["chem_lab"]
    cond = only_when(CH_DAY3, 0)
    prof = s.actor("Dr Mehra", ctx.sprite("prof_m"), 20, 7, direction="left", start=cond)
    may = s.actor(N["Mayank"], ctx.sprite("mayank"), 4, 9, direction="up", start=cond)
    par = s.actor(N["Parag"], ctx.sprite("parag"), 13, 9, direction="up", start=cond)
    P = "Dr. Mehra"
    mix = [
        say(P, "Titration. Burette, pipette, flask. Indicator turns pink at the end point."),
        say(P, "Step one. Diluting the acid. What goes into what?"),
        menu("Pick", ["Water into acid", "Acid into water", "Mix very fast"]),
        if_var("Pick", "==", 2, [say(P, "Correct! Acid into water. Always. Like my coffee into me."), inc("Grade")], [
            shake(0.6, 6), sfx("crash", 4, 200, 0.5),
            say("", "FSSSSSHHH."),
            say(N["Parag"], "Bro your eyebrows are still there. Lucky."),
            say(P, "Acid. Into. Water. Write it a hundred times. Write it on your heart."),
        ]),
        say(P, "Step two. Add drops until...?"),
        menu("Pick", ["Bright pink", "Faint pink", "Purple party"]),
        if_var("Pick", "==", 2, [say(P, "Faint pink. Subtle. Unlike this batch."), inc("Grade")],
               [say(P, "That is not the end point. That is a festival.")]),
    ]
    s.script += [at(CH_DAY3, 0, [
        comment("DAY 3 - CHEMISTRY LAB (AB3)"),
        set_pos("player", 9, 13), move_to("player", 9, 9), face("player", "up"),
        say(P, "Goggles ON. Mr. Parag, goggles are not a headband."),
        say(N["Parag"], "Sir, it's aerodynamic."),
    ] + mix + [
        say(N["Mayank"], "Workshop after this. Saws, files, welding. Try to keep ten fingers."),
        say(N["Parag"], "I've got a plan for the scrap pipes there. A launcher. For the fest."),
        say(N["Parag"], "Fires peas. Or tennis balls. Or Divyansh, if he fits."),
        set_var("Phase", 1), set_var("Objective", 8),
        deactivate(prof.id), deactivate(may.id), deactivate(par.id),
    ])]


def workshop(ctx):
    """Saw timing minigame: press A when the marker is over the pencil line."""
    s = ctx.scenes["workshop_in"]
    cond = only_when(CH_DAY3, 1)
    ins = s.actor("Instructor", ctx.sprite("instructor"), 2, 11, direction="right", start=cond)
    par = s.actor(N["Parag"], ctx.sprite("parag"), 17, 11, direction="left", start=cond)
    # the marker slides along the saw bench (x 15..22); the pencil line is x 18..20
    marker = s.actor("Saw Marker", ctx.sprite("marker"), 15, 7, start=cond)
    I = "Instructor"
    ok = [sfx("crash", 2, 300, 0.2), inc("Cuts"), gbs.raw("SHHK! Clean cut.\n$%s$ of 3" % gbs.V["Cuts"])]
    miss = [shake(0.2, 2), say(I, "Off the line! Again.")]
    poll = [
        gbs.ev("EVENT_VARIABLE_MATH", {"vectorX": gbs.V["MarkX"], "operation": "add", "other": "var",
                                       "vectorY": gbs.V["MarkDir"], "value": "0", "minValue": "0",
                                       "maxValue": "0", "clamp": False}),
        if_var("MarkX", ">=", 22, [set_var("MarkDir", -1)]),
        if_var("MarkX", "<=", 15, [set_var("MarkDir", 1)]),
        gbs.set_pos_vars(marker.id, "MarkX", "MarkY"),
        gbs.if_input(["a"], [
            if_var("MarkX", ">=", 18, [if_var("MarkX", "<=", 20, ok, miss)], miss),
            if_var("Cuts", ">=", 3, [set_var("Sawing", 2)]),
            wait(0.3),
        ]),
        wait(0.08),
    ]
    s.script += [at(CH_DAY3, 1, [
        comment("DAY 3 - WORKSHOP PRACTICAL (saw minigame)"),
        set_pos("player", 9, 11), face("player", "right"),
        say(I, "Carpentry first. Hacksaw. Three cuts on the line. Fingers stay attached."),
        say(I, "Press A when the marker crosses the pencil line in the middle of the bench."),
        say(N["Parag"], "Pro tip: breathe out when you cut. Like a sniper. Like a carpenter sniper."),
        set_var("Cuts", 0), set_var("Sawing", 1), set_var("MarkX", 15), set_var("MarkY", 7),
        set_var("MarkDir", 1),
        loop_while("Sawing", "==", 1, poll),
        set_var("Sawing", 0),
        inc("Grade"),
        say(I, "Good. Now fitting. File it smooth. Then welding... from far away. Watching."),
        say(N["Parag"], "Look! Scrap PVC, a spring, a bike valve. The Pea Launcher Mark I."),
        say(N["Parag"], "It jams if you look at it wrong, but it WORKS."),
        choice("Pick", "It's genius.", "It'll jam."),
        if_var("Pick", "==", 1, [say(N["Parag"], "Finally someone with vision."), bond("Parag")],
               [say(N["Parag"], "It'll jam ONCE. When it doesn't matter. Probably.")]),
        say(N["Mayank"], "(on the phone) Night walk behind B7 later? The scrub trail. I'll bring chai."),
        set_var("Phase", 2), set_var("Objective", 9),
        deactivate(ins.id), deactivate(par.id), deactivate(marker.id),
    ])]


# ---------------------------------------------------------------------------
# After class: dinner (day 1) and the cricket match (day 2)
# ---------------------------------------------------------------------------

def dinner(ctx):
    s = ctx.scenes["quess_mess_in"]
    cond = only_when(CH_DAY1, 1)
    may = s.actor(N["Mayank"], ctx.sprite("mayank"), 8, 8, direction="down", start=cond)
    div = s.actor(N["Divyansh"], ctx.sprite("divyansh"), 9, 10, direction="up", start=cond)
    par = s.actor(N["Parag"], ctx.sprite("parag"), 15, 8, direction="down", start=cond)
    gar = s.actor(N["Garvita"], ctx.sprite("garvita"), 16, 10, direction="up", start=cond)
    ans = s.actor(N["Anshuman"], ctx.sprite("anshuman"), 1, 13, direction="right", start=cond)
    cook = s.actor("Mess Bhaiya", ctx.sprite("student"), 6, 5, direction="down", start=cond)
    s.script += [at(CH_DAY1, 1, [
        comment("DAY 1 - DINNER AT THE QUESS MESS: meet the gang"),
        set_pos("player", 12, 14), move_to("player", 12, 11), face("player", "up"),
        say("Mess Bhaiya", "Rajma chawal. Again. It's Monday. It's always rajma on Monday."),
        say(N["Mayank"], "Okay. Formal introductions. This is our new member."),
        say(N["Divyansh"], "Divyansh. Future topper, future CEO, future gym guy.",
            "Starting Monday. Not this one."),
        say(N["Parag"], "Parag. I build stuff. Mostly stuff that works on the second try."),
        say(N["Garvita"], "Garvita. I run. Stairs, ledges, anything. Don't race me."),
        say(N["Divyansh"], "I could beat her. I just don't want to embarrass her."),
        say(N["Garvita"], "Race me to the counter then."),
        say(N["Divyansh"], "...after dinner. Digestion is important."),
        say(N["Mayank"], "And Anshuman. He's... somewhere."),
        move_to(ans.id, 11, 13), face("player", "down"), emote("player", ctx.emote("shock")),
        say(N["Anshuman"], "Behind you. Since the rajma."),
        say("You", "HOW."),
        say(N["Anshuman"], "Practice. Nobody notices the guy who doesn't want to be noticed."),
        say(N["Mayank"], "Kanishk skipped. Library. He's 'planning the semester like a campaign'."),
        say(N["Divyansh"], "Okay, bill. I'll pay. Definitely. Let me just... find... my wallet..."),
        say(N["Parag"], "Fifty rupees, Kanishk called it. He's not even here and he won."),
        say(N["Mayank"], "Free evening! Hang out with someone. They're around campus.",
            "Divyansh: NBC. Parag: the avenue. Anshuman: the scrub trail. Garvita: cricket ground.",
            "Kanishk: the Dome library. Me: B7 courts."),
        set_var("Phase", 2), set_var("Objective", 3),
        deactivate(may.id), deactivate(div.id), deactivate(par.id), deactivate(gar.id),
        deactivate(ans.id), deactivate(cook.id),
    ])]


def cricket(ctx):
    s = ctx.scenes["cricket_ground"]
    cond = only_when(CH_DAY2, 1)
    cx, cy = spot(ctx, "cricket_ground", 31, 30)
    div = s.actor(N["Divyansh"], ctx.sprite("divyansh"), cx, cy + 4, direction="up", start=cond)
    kan = s.actor(N["Kanishk"], ctx.sprite("kanishk"), cx + 6, cy - 2, direction="left", start=cond)
    gar = s.actor(N["Garvita"], ctx.sprite("garvita"), cx - 7, cy - 6, direction="right", start=cond)
    par = s.actor(N["Parag"], ctx.sprite("parag"), cx, cy - 8, direction="down", start=cond)
    may = s.actor(N["Mayank"], ctx.sprite("mayank"), cx + 4, cy + 6, direction="left", start=cond)
    s.script += [at(CH_DAY2, 1, [
        comment("DAY 2 - CRICKET MATCH"),
        set_pos("player", cx - 4, cy + 6), face("player", "up"),
        say(N["Kanishk"], "Field placements. Garvita deep midwicket. Parag bowls. You, slip."),
        say("You", "What's a slip?"),
        say(N["Kanishk"], "Exactly what you'll do. Stand there."),
        say(N["Divyansh"], "Watch. First ball. Six. Over the solar panels. Into AB3."),
        say(N["Mayank"], "That's two hundred metres."),
        say(N["Divyansh"], "Two hundred and ONE. Write it down."),
        sfx("crash", 3, 400, 0.2), shake(0.3, 3), move_to(par.id, cx, cy + 2),
        say("", "Parag bowls. Divyansh swings with his whole soul."),
        say("", "The ball hits the stumps. The stumps fall over. Divyansh does not move."),
        say(N["Divyansh"], "...I was testing the bowler."),
        say(N["Garvita"], "I sprinted all the way from midwicket to laugh at you up close."),
        say(N["Kanishk"], "Evidence logged."),
        choice("Pick", "Cheer Divyansh up", "Laugh along"),
        if_var("Pick", "==", 1, [say("You", "Next match. Seven. Over the Dome."),
                                 say(N["Divyansh"], "SEE? Someone believes in me."), bond("Divyansh")],
               [say(N["Divyansh"], "Laugh now. When I'm famous, you're not in the documentary.")]),
        say(N["Mayank"], "Free evening again. Same spots as yesterday. Go hang out with someone."),
        set_var("Phase", 2), set_var("Objective", 3),
        deactivate(div.id), deactivate(kan.id), deactivate(gar.id), deactivate(par.id), deactivate(may.id),
    ])]


# ---------------------------------------------------------------------------
# Free evenings: one hangout per evening (Persona social links)
# ---------------------------------------------------------------------------

HANGOUTS = {
    # friend: (scene, near tile, day 1 lines, day 2 lines)
    "Divyansh": ("nbc", (20, 26), [
        "Maggi with extra cheese. This is fuel. Champions eat this.",
        "I'm going to do everything this year. Gym. Coding. Guitar. Startup.",
        "...I haven't started any of them. But I've planned all of them. That's half."],
        ["Okay real talk. I talk big because if I say it out loud, maybe it happens.",
         "Back home everyone says I'm all talk. Maybe. But one day I'll walk the walk.",
         "When it counts. You'll see."]),
    "Kanishk": ("dome_in", (13, 9), [
        "This library has 14 exits. I counted. Habit.",
        "I plan everything. Semester, meals, which stairs are fastest.",
        "If you have a plan, nothing can surprise you. That's the theory."],
        ["Chess? You lost in nine moves. Good. You'll lose in ten next time.",
         "My dad says I calculate people like pieces. I don't. Mostly.",
         "There's always one variable you can't plan for. I hate that variable."]),
    "Parag": ("hostel_avenue", (30, 16), [
        "See this avenue? Perfect test range. Long, straight, no professors.",
        "I fix things. Fans, phones, my roommate's love life. Okay, not that.",
        "If it breaks, I build it again. That's the whole philosophy."],
        ["I failed my first robot in school. It caught fire. Everyone laughed.",
         "I kept the burnt chip. It's in my wallet. Reminds me to try twice.",
         "Things jam. People jam. You clear it and keep going."]),
    "Anshuman": ("scrub_trail", (30, 30), [
        "...",
        "You found me. Most people don't. That's kind of the point.",
        "Peacocks sleep in these trees. If you're quiet enough you can hear them."],
        ["I used to hide in the library at school. Not from bullies. From noise.",
         "Stealth games are honest. Stay in the shadow, nobody gets hurt.",
         "Thanks for walking out here. Even if you made noise the whole way."]),
    "Garvita": ("cricket_ground", (20, 20), [
        "Race you to the pavilion! ...No? Coward.",
        "I run because when I stop, I start thinking. Running is cheaper than therapy.",
        "Tomorrow I'm doing the AB2 stairs. All of them. Twice."],
        ["Back home I was 'the girl who climbs things'. Here I'm just me. It's nice.",
         "One day I want to run so far nobody can call me back.",
         "But also... it's nice when someone waits at the finish."]),
    "Mayank": ("b7_courts", (20, 20), [
        "First week's always weird. You'll get used to it. Or I'll get used to you.",
        "I came here because my cousin did. Not a great reason. Turned out okay.",
        "Why did you come here?"],
        ["You didn't answer yesterday. About why you came here.",
         "It's fine. Nobody really knows. We just end up somewhere and make it ours.",
         "Hey. Glad it's you in room 10."]),
}


def hangouts(ctx):
    for friend, (scene_key, (x, y), d1, d2) in HANGOUTS.items():
        s = ctx.scenes[scene_key]
        m = ctx.meta(scene_key)
        x, y = open_spot(m["collisions"], m["cols"], m["rows"], x, y)
        start = [if_var("Phase", "!=", 2, [deactivate("$self$")], [
            if_var("Chapter", ">", CH_DAY2, [deactivate("$self$")], [
                if_var("Chapter", "<", CH_DAY1, [deactivate("$self$")])])])]
        end = [
            bond(friend),
            say("", "The evening slips away. You walk back to B7."),
            set_var("Phase", 3), set_var("Objective", 4), set_var("Hung", 1),
            goto(ctx.sid_of("room"), 14, 17, "up", fade="1"),
        ]
        name = N[friend]
        s.actor(name + " (hangout)", ctx.sprite(friend.lower()), x, y, direction="down", start=start, script=[
            comment("HANGOUT - %s (Persona social link). Raises Bond_%s." % (friend, friend)),
            choice("Pick", "Hang out", "Not now"),
            if_var("Pick", "==", 1, [
                if_var("Chapter", "==", CH_DAY1, [say(name, *d1)], [say(name, *d2)]),
            ] + end),
        ])


def night_walk(ctx):
    s = ctx.scenes["scrub_trail"]
    x, y = ctx.entry["scrub_trail"]
    cond = only_when(CH_DAY3, 2)
    may = s.actor(N["Mayank"] + " (night walk)", ctx.sprite("mayank"), *spot(ctx, "scrub_trail", x + 3, y, avoid={(x, y), (x + 1, y)}),
                  direction="left", start=cond)
    s.script += [at(CH_DAY3, 2, [
        comment("DAY 3 - NIGHT WALK BEHIND B7 (seeds Act 3)"),
        music(ctx.music("woods")),
        set_pos("player", x, y), face("player", "right"),
        say(N["Mayank"], "Chai. Cutting. Two rupees more than last year. Inflation is real."),
        say(N["Mayank"], "You know what I like about this place? Out here it's quiet enough to think."),
        say(N["Mayank"], "So. Why did you come here? For real this time."),
        gbs.menu("Pick", ["Didn't clear IIT", "Didn't know", "To meet you lot"]),
        switch("Pick", {
            1: [say("You", "IIT didn't happen. Twelfth was... a lot."),
                say(N["Mayank"], "Yeah. Everyone here has an IIT-shaped hole somewhere. We fill it with chai.")],
            2: [say("You", "Honestly? I don't know. I just ended up here."),
                say(N["Mayank"], "That's the most honest answer anyone's given me.")],
            3: [say("You", "To meet you lot. Obviously."),
                say(N["Mayank"], "Liar. ...Thanks though."), bond("Mayank")],
        }),
        say(N["Mayank"], "My nani says life isn't a line. It's a circle. You end up where you started,",
            "but you're different, so it's a different place."),
        say(N["Mayank"], "Deep, right? She also says don't eat Maggi at 2 AM. Ignored that one."),
        sfx("noise", 1, 100, 1.0), shake(0.4, 1),
        say("", "Far off, past the reservoir, something howls. Not a dog. Not quite."),
        say(N["Mayank"], "...Let's head back."),
        set_var("Phase", 3), set_var("Objective", 4),
        goto(ctx.sid_of("room"), 14, 17, "up", fade="1"),
    ])]


def world_marker(ctx):
    """The bouncing ! on the campus world map: points at the current objective."""
    w = ctx.scenes["world"]
    wm = ctx.meta("world_campus")
    loc = {l["target"]: (l["x"], l["y"]) for l in wm["locations"]}
    targets = {1: "ab1", 2: "quess_mess", 4: "legacy_b7_front", 5: "ab2", 6: "cricket_ground", 7: "ab3",
               8: "workshop", 9: "scrub_trail", 11: "hostel_avenue", 12: "underpass", 13: "grand_staircase",
               14: "ab2", 15: "dome"}
    cases = {}
    for k, t in targets.items():
        x, y = loc[t]
        cases[k] = [set_pos("$self$", x, y - 1), show("$self$")]
    w.actor("Objective", ctx.sprite("orb"), 1, 1, animate=True, start=[
        gbs.collisions_off("$self$"), hide("$self$"), switch("Objective", cases)])
    w.script += [
        if_var("Chapter", "<", CH_OUTBREAK, [music(ctx.music("world"))]),
    ]


def build(ctx):
    physics(ctx)
    maths(ctx)
    chem(ctx)
    workshop(ctx)
    dinner(ctx)
    cricket(ctx)
    hangouts(ctx)
    night_walk(ctx)
    world_marker(ctx)
