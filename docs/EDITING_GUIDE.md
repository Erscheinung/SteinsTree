# Editing Dernier without AI: the easy guide

Everything in the game is ordinary GB Studio data: scenes, actors, triggers
and events. You can change all of it with the mouse in GB Studio. The studio
is a second window that lets you *see* the whole game at once and edit dialogue
quickly. Python scripts are only needed if you want to regenerate maps or
scenes from their source.

## 0. Setup (once)
1. Install **GB Studio 4.3** (already in /Applications). Open `Dernier.json`
   from this folder.
2. Python 3 is already on your Mac. Nothing else is needed for the studio.
3. Optional: **LibreSprite** (installed) for pixel art and **Tiled** for
   studying the old atlas.

## 1. Play it
- **In GB Studio:** press **Play** (top right). Use the arrows or WASD; A is Z/J;
  B is X/K; Start is Enter.
- **Jump to any part:** press **Start** in-game, choose **Chapters**, pick a
  page and a scene. This "chapter select" sets all the story variables for
  you. It's meant for testing; you can delete it later (scene
  `0 Menus/Chapter Select (dev)`).
- **Export a ROM:** *Build > Export ROM*. Copy it to `rom/game.gb` so that
  `index.html` / `bgb.exe` play the new version.

## 2. See everything: the studio
```
python3 tools/studio/studio.py serve
```
This opens http://localhost:8765. Close GB Studio before editing in the
studio, and reopen the project afterwards: both edit the same files.

| Tab | What it shows | What you can do |
|---|---|---|
| Story flow | Every scene as a card, in columns by folder (Prologue, Days, Campus, Outbreak, The Middle, Finale); arrows show which scene leads where | Filter; click to open |
| Scene | The scene's background, with collisions (red), triggers (yellow) and actors (sprites) overlaid | Click an actor or trigger to read its whole script in plain English, and edit dialogue, choices and menus inline |
| Dialogue | All dialogue, choices and menus in one searchable list | Edit and save; "auto-wrap" does the 18-character line breaks |
| Campus map | The world map with location labels | Click a place to open its scene |
| Sprites / Palettes / Variables | Every character, every palette bank, every story variable | Reference |
| Guide | These docs | |
| Check | Runs the layout audit and the validator | |

Dialogue box rules: **18 characters per line, 3 lines per box**. A line with
only `---` starts a new box. `$123$` shows the value of a variable (it's used
for HP and bond counters).

## 3. Edit from the terminal (same thing, no browser)
```
python3 tools/studio/studio.py scenes                          # list scenes
python3 tools/studio/studio.py dialogue --grep "Divyansh"      # find lines (shows each event id)
python3 tools/studio/studio.py set <event-id> "New line|Next box"
python3 tools/studio/studio.py export dialogue.tsv             # whole script into a spreadsheet
python3 tools/studio/studio.py import dialogue.tsv             # bring your edits back in
python3 tools/studio/studio.py check                           # layout audit + validator
```
The TSV round trip is the fastest way to rewrite a lot of dialogue. Open it in
Numbers, Excel or Google Sheets, edit the last column (` | ` separates boxes
and `\n` is a line break), save as TSV, then import it.

## 4. Common edits in GB Studio (mouse only)
- **Change a line:** click the scene, then the actor or trigger. In the right
  panel, find the *Display Dialogue* event and type.
- **Rename a friend everywhere:** easiest is the TSV round trip (search and
  replace), or edit `NAMES` in `tools/game/story/common.py` and regenerate (§7).
- **Move a character:** drag the actor in the scene.
- **Who appears when:** many actors start with an *If Chapter ... / If Phase ...
  → Remove actor* rule in their **On Init** tab. Chapter 1–3 are the days, 4 is
  the outbreak, 5 is the Middle, 6 is the finale. Phase 0 is morning, 1 after
  class, 2 evening, 3 night.
- **Add a door:** add a trigger with a *Change Scene* event. Put the arrival
  point one tile away from the target's own triggers, otherwise you bounce
  straight back.
- **Recolour part of a map:** in the scene, choose the paint bucket tool's
  **Colorize** mode and pick a palette slot (0 grass, 1 path/sand, 2 stone,
  3 brick, 4 roof/glass, 5 water, 6 wood).
- **Day, night, dream:** the *Set Background Palettes* event swaps all slots
  at once. Banks are named `MUJ day ...`, `MUJ night ...`, `MUJ dreamA ...`
  and so on.
- **Character colours:** each friend has a sprite palette (*Settings* →
  default sprite palettes, or per scene). Slots:
  - 0 you
  - 1 Mayank
  - 2 Divyansh / Mom
  - 3 Kanishk / Muskaan
  - 4 Parag
  - 5 Anshuman / objects
  - 6 Garvita / peas
  - 7 zombies / professors
- **Music:** pick a song in *Play Music* events. The songs in `assets/music`
  are GB Studio's sample tracks by Rulz, as placeholders. Compose your own in
  GB Studio's music editor (hUGE) and swap them in.

## 5. Change the art
- **Sprites:** `assets/sprites/cast_*.png` are 6-frame strips (16×16 frames:
  down, down-walk, up, up-walk, right, right-walk; left is mirrored). Draw in
  LibreSprite using the four canonical sprite colours (the lime green is
  transparent). Colour previews are in `art/sprites/cast/preview/`. Once
  you've hand-edited a PNG, the generator leaves it alone.
- **Maps:** see `docs/MAP.md`. You can paint over `assets/backgrounds/muj/*.png`
  in LibreSprite (keep the four greens) and colour the result in GB Studio.
- **Your original B7 art** is untouched in `assets/backgrounds/*.png`. The game
  uses enriched GBC copies from `assets/backgrounds/enriched/`. To go back to
  an original, pick it as the scene's background in GB Studio.

## 6. Test
- **Chapter select** (§1) jumps to any part.
- `python3 tools/game/check_maps.py` finds:
  - doors you can't reach;
  - arrival points inside walls;
  - arrival points on top of triggers (which cause loops);
  - overlapping triggers.
- **Automated playtests (optional):**
  ```
  python3 -m pip install pyboy pillow
  python3 tools/playtest/harness.py rom/game.gb build/dernier.sym out/
  ```
  The harness can read story variables and the player's tile; see
  `tools/playtest/README.md`.

## 7. Regenerate from source (optional, scripts)
Scenes were generated from Python "screenplays" in `tools/game/story/`:
`prologue.py`, `act1.py`, `act2.py`, `act3.py` and `legacy.py`. Every line of
dialogue is plain text there too.
```
python3 tools/sprites/cast_build.py      # sprites
python3 tools/map/build_maps.py          # maps (or: build_maps.py ab1 dome)
python3 tools/map/enrich.py              # GBC copies of your original backgrounds
python3 tools/game/build_game.py         # scenes, palettes, variables, settings
```
**Safety:** every generated file is fingerprinted. If you've edited it in GB
Studio or the studio, the generator skips it and lists it. Pass
`--force <scene_key>` only when you want the script version back.
`python3 tools/game/build_game.py --check` validates without writing.

## 8. What the generator changed in your original scenes
- **Title screen:** "New Game" now starts the prologue (Bedroom, 2009) and
  resets the story variables. The logo and title use the After Hours palette.
- **Outside (B7 room 10):** your rumble events are wrapped in *If Chapter = 4*
  (the outbreak night). On other days the room runs the morning call and
  bedtime script. Your "Life is meaningless... And college sucks!" trigger is
  unchanged.
- **Scene 5 (Mayank):** his sprite is now *afterhours_mayank_walk*. His original
  events run only in Chapter 4, and he sends you to the lounge once you've
  seen the scholar.
- **Scene 13 (scholar):** the scholar uses *afterhours_scholar_walk*. The
  scene's original events run only in Chapter 4, and they set `SawZombie`.
- **All B7 scenes:**
  - their backgrounds point at the enriched GBC copies, with fitted palettes;
  - a night palette is applied in Chapter 4;
  - Start opens the pause menu;
  - edge triggers that were empty now lead to the campus world map.
- **Pristine copies** of your originals are kept in
  `tools/game/legacy_snapshot/`.

## 9. Troubleshooting
- **GB Studio says a file changed on disk:** reload the project (*File >
  Reopen*).
- **"Background has too many tiles":** each map must stay under 384 unique
  8×8 tiles. Simplify the art, or rerun `build_maps.py`, which merges near
  duplicates.
- **A character shows in the wrong colours:** check its sprite's palette slot
  (Sprite editor → each tile's palette), and the scene's sprite palettes.
- **Something loops when you enter a room:** you arrived standing on a trigger.
  Move the arrival point one tile away (run `check_maps.py`).
