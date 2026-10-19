# Dernier: story bible (draft 1)

This is the editable source of intent for the story. The game itself lives in
GB Studio scenes (edit lines there, or in the studio:
`python3 tools/studio/studio.py serve`). When you change a *beat* here, as
opposed to a single line, ask Claude to "regenerate <scene> from docs/STORY.md".
CLAUDE.md explains the workflow, and hand-edited scenes are never overwritten
without your say-so.

Placeholders are marked **[EDIT]**. Friends' names are real people, so make
sure each friend is happy with how they're written.

## Logline

A first-year CSE student at Manipal University Jaipur spends three ordinary,
funny days becoming friends with five people. Then a zombie outbreak takes
them, one by one, in ways that finish who they were. Under the Dome, the last
friend asks why you came here. The answer is a journey back through your whole
life, and a reunion at dawn that isn't real, and is enough.

## Tone map

| Part | Feels like | Plays like | Palette |
|---|---|---|---|
| Prologue (2009) | Warm nostalgia | A pocket-monster battle on a handheld (homage, original critters) | `memory` sepia |
| Act 1: three days | *Persona* slice-of-life, Indian college humour | Quizzes, a mixing puzzle, a saw-timing minigame, hangouts that raise bonds | `day` then `dusk` |
| Act 2: outbreak | Tense, funny until it isn't | Each friend is a different game: turn-based, lane defence, stealth, talk-battle into a chase, platformer | `night`, `blood` |
| Act 3: the Middle | *Until Then*, *Before Your Eyes*, *Lost* | Abstract and avant-garde: a starfield hub, seven memory levels that each play differently, the Hall of Doors | `dreamA/B/C`, `memory` |
| Finale | Bittersweet calm | Walk and talk; the reunion at dawn | `dusk` |

## Characters

All friend names come from `NAMES` in `tools/game/story/common.py`. Rename them
in one place to change them everywhere.

| Friend | Real-life placeholder for | Act 1 trait | Act 2 mechanic | Arc and death (Act 2) | Reflection (Act 3) |
|---|---|---|---|---|---|
| **Mayank** | your roommate friend | The first friend. Calm, kind, asks "why did you come here?" | Story anchor | Bitten during the staircase run. Dies under the Dome after asking his question one last time: "It's just the middle." | Muskaan's memory: "Some people are a theme." |
| **Divyansh** | **[EDIT]** | Big promises (topper, gym, startup, a six over the Dome) and no follow-through. Heavier build, funniest guy. | "All talk": a speech battle (hype him or warn him), then a chase | For once he walks the walk: charges the horde on the Grand Staircase, buys everyone time. "Tell my mom I topped. Lie a little." | Ninth grade: "You loved someone out loud." |
| **Kanishk** | **[EDIT]** | The planner. Counts library exits, calls field placements. | Turn-based battles (Read, Attack, Barrier, Snack) | Wins the Old Mess last stand, but was bitten in wave two: "I accounted for every move on the board except the one piece I never count: me." Locks himself in. | Eleventh: "You can only choose your next move." |
| **Parag** | **[EDIT]** | Builder. Things work on the second try. Keeps a burnt chip in his wallet. | Lane defence with his PVC Pea Launcher (built in the Day 3 workshop) | The launcher jams "once, when it matters". He stays to clear it. | Back to India: "Second try. That's the whole trick." |
| **Anshuman** | **[EDIT]** | Stealth guy. Appears behind you at dinner. Peacocks on the scrub trail. | Splinter Cell stealth (patrols, shadows, radio) | Goes ahead into the dark tunnel to draw the horde away; his radio goes to static. "Nobody notices the guy who doesn't want to be noticed. But you did." | Childhood: "The shadows were never empty." |
| **Garvita** | **[EDIT]** | Runner and climber. "Running is cheaper than therapy." | Platformer over the AB2 rooftops | The last ledge crumbles. She lets go so you don't go with her. "It's nice that someone's waiting at the finish." | London: "Running far isn't the same as running away." |

Other characters: Prof. Rao (Physics), Prof. Iyer (Maths), Dr. Mehra
(Chemistry), the Workshop Instructor, Mess Bhaiya, Mom (prologue), Mama, Dad,
Aryan, Muskaan, "the girl at the library".

## Beat sheet (scene names as they appear in GB Studio)

### Prologue (`1 Prologue/`)
1. **Bedroom, 2009.** Mom: homework or critters? Walk to the PocketBoy and press A.
2. **Pocket Critters Battle.** SPARKLET vs a wild GNAWBIT (Fight, Bag, Run).
   Retry if you lose. After winning, "GNAWBIT looked straight out of the
   screen. At you." (foreshadowing)
3. Back in the bedroom: "Eleven years later..." → MUJ, B7, room 10 → **Day Card**.

### Act 1: three days (`3 Days/`, campus `2 Campus/`)
Mornings start in **B7 room 10** (the original "Outside" scene). Mayank
knocks. Travel by the **Campus World Map**; the `!` marks the objective.

- **Day 1:** Physics in **AB1-101** (3-question quiz). Dinner at the
  **Quess Mess**: meet Divyansh, Parag, Garvita and Anshuman (Kanishk is at
  the library). Free evening: hang out with one friend. Sleep.
- **Day 2:** Maths in **AB2-214** (quiz). **Cricket match**: Divyansh's
  promised six; the stumps go flying. Free evening. Sleep.
- **Day 3:** **Chemistry lab** (acid into water). **Workshop** saw practical:
  three clean cuts; Parag reveals the Pea Launcher Mark I. Night walk on the
  **Scrub Trail behind B7** with Mayank: "Why did you come here?" A distant
  howl. Sleep.

Hangout spots on free evenings:
- Divyansh: NBC
- Kanishk: the Dome library
- Parag: the hostel avenue
- Anshuman: the scrub trail
- Garvita: the cricket ground
- Mayank: B7 courts

Each hangout raises `Bond_<name>`, which changes the finale.

### Act 2: the outbreak (`4 Outbreak/`)
0. 3:07 AM. Your original scenes play out as written: the rumble, Mayank in the
   corridor, the scholar at the B7 gate ("grrrr!"). Tell Mayank, then go to
   the lounge.
1. **B7 Lounge Council.** The plan: reach the Dome (PA system, satellite phone).
2. **Quess Mess Siege:** Kanishk, turn-based, 3 waves.
3. World map, then **Avenue Lane Defence**: Parag, 15 kills. *Parag dies.*
4. World map, then **Underpass Stealth** and **The Tunnel**: Anshuman. *Anshuman vanishes.*
5. World map, then **Grand Staircase**: Divyansh's speech, his charge, then the chase. *Divyansh dies.*
6. **Old Mess Last Stand:** Kanishk, turn-based. *Kanishk dies.*
7. World map, then AB2: **Rooftop Run**, Garvita, platformer. *Garvita falls.*
8. **Under the Dome:** Mayank. *Mayank dies.* → Act 3.

### Act 3: the Middle (`5 The Middle/`)
**The Middle (hub)**: a breathing starfield (palette cycling) with seven
lights. Each light is a memory from docs/LIFE.md, and each plays differently:

| # | Memory | Mechanic | Reflection by |
|---|---|---|---|
| 1 | Childhood (home) | Explore. A coin jar choice (guilt). Mama's kindness. | Anshuman |
| 2 | Flight to London | Shoot-'em-up: dodge storm clouds, east to Heathrow | Garvita |
| 2b | London | Football with kids; the girl at the library | Garvita |
| 3 | Back to India | Only works if you keep trying (talk to Aryan 3 times) | Parag |
| 4 | Muskaan | She keeps disappearing and reappearing; follow her | Mayank |
| 5 | Ninth | Love, then betrayal; afterwards you walk at half speed | Divyansh |
| 6 | Eleventh | Too many orbits: flashing palettes and voices; choose "walk" or "build it anew" | Kanishk |
| 7 | Twelfth | Platformer with a low ceiling: you can't fly too high. "Then MUJ." | everyone |

After all seven, the centre opens onto the **Hall of Doors** (the "what ifs").
The last door leads to the finale.

### Finale (`6 Finale/`)
**Reunion at Dawn** on the cricket ground: talk to everyone. Lines depend on
`Bond_<name>` (2 or more gives the warmer line). Mayank last: "You know this
isn't real?" "I know." "Is it enough?" "...It's enough." "Death isn't the end.
It's just the middle." → **Credits** → title.

## Things to decide [EDIT]
- [ ] Each friend's real personality notes and in-jokes.
- [ ] Whether "Mama" in LIFE.md means mother or maternal uncle. Draft 1 uses
      an uncle-like figure for Mama and "Mom" in the prologue.
- [ ] Muskaan's theme music (needs its own track; for now a placeholder).
- [ ] Real class names, professors and campus in-jokes.
- [ ] Whether the reunion should change if a friend was barely bonded with.
