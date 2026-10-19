# Life-story levels (Act 3: "The Middle")

Fill this in with your own memories. Each block maps to one memory scene in
GB Studio (`5 The Middle/...`). The draft lines in the game came from your
Todoist notes ("Levels (READ description): are your life story", Dec 2025),
quoted below. Replace the **[EDIT]** parts. Then either edit the lines directly
in GB Studio or the studio, or ask Claude to "regenerate the memory scenes
from docs/LIFE.md".

Your notes in the order you wrote them:

> Childhood in school. Loneliness with parents. Mama is nice respite. Guilt.
> Stealing (show). London (flying to new country), London-esque graphics. Fun
> with kids. Fun music. Discovery. Love and heartbreak, first love. Football
> with friends. Invention, discovery. Joy of reading. Fight with friends.
> Jawahar Bagh. Spring and Autumn, especially autumn (school life), nice
> softer colours. Then back from London. Jarring. New world. India. Settling
> in. Nice. Aryan. Uncertain but heavenly, in familiar abode. Then change of
> schools. Jarring and sad. 5th class. But slowly gets better. 6th class is
> nice, Muskaan. But again new friends. 7th is lovely and fun. Love found
> again. But shortlived. But life goes on. Winning competitions. Love of
> drawing. PSP, PS2. Gaming. Football comes in again. 8th class is one of the
> best of my life. Then another love in 9th. Blossoms. And it's nice. I loved
> her. And then betrayal. Heartbreak. Shattering. Spaceship coughs, slows
> down. 10th, Muskaan is found again. Same music. Her theme plays again. Make
> it a constant theme. And a constant figure that keeps returning. And then
> too much. Brain fries in 11th. Stress. Everything is getting too much. Map
> is a whirling magnum of unstable orbits. Sucking you in. Until it crashes.
> Spaceship is lost. And you have to get out. Walk. Or construct it anew. 12th
> is passing by. Slowly. Can't fly too high. IIT pressure. Then MUJ.
> Write more later. Develop as you go.

## 1. Childhood (scene "Memory: Childhood", background `home_india`)
- Where: **[EDIT]** (city, house, school). Jawahar Bagh could be a level here.
- People: Mom, Dad (busy: "Not now, beta"), **Mama** (**[EDIT]**: mother or
  maternal uncle?)
- The guilt: the coin jar ("Stealing (show)"). **[EDIT]**: what was it really?
- Seasons: spring and autumn, softer colours. The `memory` palette is sepia; an
  autumn palette could be added.
- Reflection: Anshuman.

## 2. Flight to London (shoot-'em-up "Memory: Flight to London")
- "Flying to a new country." The plane is the spaceship from your levels idea.
- **[EDIT]**: age, who flew with you, the first thing you saw.

## 2b. London (scene "Memory: London", background `london_street`)
- Fun with kids, fun music, discovery, football with friends, joy of reading,
  first love, invention, a fight with friends.
- **[EDIT]**: the street, the school, the friend's name, the book.
- Reflection: Garvita.

## 3. Back to India (scene "Memory: Back to India", background `childhood_school`)
- "Jarring. New world. Settling in. Aryan. Uncertain but heavenly."
- Change of schools in 5th: "jarring and sad, but slowly gets better". The
  mechanic: classmates only open up after you try three times.
- **[EDIT]**: Aryan's lines, the new school's name.
- Reflection: Parag.

## 4. Muskaan (scene "Memory: Muskaan's theme", background `flower_field`)
- 6th (Muskaan), 7th (love found again, short-lived; competitions, drawing,
  PSP/PS2), 8th (one of the best years), 10th (Muskaan found again: "Same
  music. Her theme plays again.")
- She is a constant figure who keeps returning. The mechanic is that she
  reappears somewhere else each time you talk to her.
- **[EDIT]**: her theme (compose a `.uge` song in GB Studio's music editor and
  swap it in), four real moments.
- Reflection: Mayank.

## 5. Ninth (scene "Memory: Ninth", background `maths_class`)
- Love blossoms, then betrayal. Heartbreak, shattering. "The spaceship coughs,
  slows down." The mechanic: you walk at half speed afterwards.
- **[EDIT]**: what to show, and how much.
- Reflection: Divyansh.

## 6. Eleventh (scene "Memory: Eleventh", background `orbits`)
- "Brain fries. Stress. A whirling magnum of unstable orbits. Until it
  crashes. Walk, or construct it anew." The mechanic: flashing palettes, voices,
  then a choice.
- **[EDIT]**: the real voices (coaching, tests, people).
- Reflection: Kanishk.

## 7. Twelfth (platformer "Memory: Twelfth", background `corridor12`)
- "Passing by. Slowly. Can't fly too high. IIT pressure. Then MUJ." A low
  ceiling, signs on the walls.
- **[EDIT]**: the signs' text.

## More slots
Add more by copying a memory function in `tools/game/story/act3.py` (or
duplicating a memory scene in GB Studio), then adding an orb to the hub.
Ideas from your notes:
- Jawahar Bagh
- the joy of reading
- winning competitions
- the PSP/PS2 years
- "the end is never the end"
