# Dernier / SteinsTree — Draft 1 plan

Date: 2026-10-19. Status of each item is tracked at the bottom.

## Refined brief (what was asked, restated so it can be re-run)

Build **draft 1 of a complete, playable GB Studio 4 game** set in Manipal
University Jaipur (MUJ), plus the tools and docs the owner needs to keep
editing it **without AI**.

1. **Campus map (key artifact).** Chart MUJ's real hostel and academic campus
   from OpenStreetMap and satellite imagery. Produce:
   - a Chrono Trigger-style **world map** for moving between places
     (forest and scrub outside B7 included), and
   - **local area maps for every sub-area**: B7 surroundings, the Quess Mess,
     hostel avenue, Block 1 / Block 2, girls' blocks, pool, reservoir trail,
     underpass, Dome (Admin Block), AB1/AB2/AB3, amphitheatre, Old Mess and
     the Grand Staircase, Workshop, cricket ground, NBC, and the interiors.
   - A reusable **tileset with variations** (grass, path, road, scrub, trees,
     hedges, walls, roofs, solar panels, water, courts, interiors…).
   - Keep the owner's existing B7 scenes and art. Fit the new maps around them
     and record where every piece came from.
2. **Art direction.** Pokémon Emerald-inspired, but richer: top-left light,
   cast shadows, highlight and shade ramps. Use GB Color (one palette of 4
   colours per 8×8 tile, up to 8 background palettes per scene). Enrich the
   existing Emerald-style backgrounds into GBC-legal versions with more shading.
   Never overwrite the originals.
3. **Story, in four tonal acts:**
   - **Prologue — pocket-monster nostalgia.** A childhood handheld battle
     (homage only, no Nintendo assets) dissolves into B7, room 10.
   - **Act 1 — Persona-style bonding.** Three days of first-year B.Tech CSE:
     Engineering Physics, Engineering Mathematics, Chemistry, and Workshop
     (saw, fitting, welding). Lighthearted. Bond points with Mayank and
     friends, plus free-time choices.
   - **Act 2 — outbreak.** A real zombie outbreak. Each friend is a
     placeholder for the owner's real friends and brings a different
     mechanic:
     - Kanishk: turn-based
     - Parag: pea-shooter lane defence
     - Anshuman: Tom Clancy-style stealth
     - Divyansh: all talk and no walk. He makes big promises, runs out, and
       gets eaten. Heavier build in his sprite.
     - Garvita: platformer rooftop run
     - Mayank: the last friend standing.

     Travel between buildings on the world map. Friends die in ways that
     complete their character arcs.
   - **Act 3 — consciousness.** The tone and the mechanics both change. It
     becomes philosophical, horror and avant-garde, with psychedelic visual
     levels built from the owner's life story: London, India, the school
     years, Muskaan's recurring theme, 9th grade, 11th-grade stress, 12th,
     then MUJ.
   - **Finale.** A momentary reunion with the friends, knowing it is not
     real, and that it is enough. "Death is just the middle."

   Inspirations: *Before Your Eyes*, *Lost*, and above all *Until Then*.
4. **Editability.** Everything is built from native GB Studio scenes, actors,
   triggers and events, so it is all drag-and-drop editable in GB Studio. No
   custom C or GBVM.
   - A local **web studio** shows the maps, tiles, sprites, every line of
     dialogue and the scene-to-scene logic, and lets the owner edit dialogue
     and save it.
   - A terminal CLI does the same for quick edits.
   - An easy guide explains all of it.
5. **Docs.** The story bible, character arcs and deaths, and the life-story
   levels are written as editable docs. CLAUDE.md explains how to regenerate
   scenes from them.
6. **Verify.**
   - Build the ROM headlessly with GB Studio's own compiler.
   - Playtest it in an emulator with scripted inputs.
   - Review the maps for layout and overlap errors.
   - Get an independent Codex review (`gpt-6.1-sol`, medium) and fold the
     fixes back in.
7. Save a note to Todoist, update the README and CLAUDE.md, then commit and
   push.

## Architecture

| Piece | Path | Role |
|---|---|---|
| OSM campus data | `art/maps/source/muj_osm.json` | Raw geometry (© OpenStreetMap contributors, ODbL) |
| Map pipeline | `tools/map/` | Palettes, tile painter, OSM rasteriser, map layouts → backgrounds, collisions and exits |
| Map sources | `tools/map/maps/*.py` | One file per map: terrain grid, buildings and exits, all editable |
| Backgrounds | `assets/backgrounds/muj/*.png` | Generated runtime art (GBC, autoColor) |
| Enriched legacy art | `assets/backgrounds/enriched/*.png` | Shaded GBC versions of the existing B7 art; originals untouched |
| Sprites | `tools/sprites/cast_art.py` → `assets/sprites/cast_*.png` | New cast: friends, professors, zombies, family, effects |
| Game generator | `tools/game/` | Builds the GB Studio scenes from story modules. Deterministic IDs, hand-edit guard |
| Studio | `tools/studio/` | `python3 tools/studio/studio.py serve` (web) and the dialogue CLI |
| Docs | `docs/STORY.md`, `docs/LIFE.md`, `docs/MAP.md`, `docs/EDITING_GUIDE.md` | Owner-editable sources of intent |

### Rules the generator follows

- IDs are `uuid5(name)`, so regenerating never breaks references.
- `tools/game/.generated.json` stores a hash of every file the generator
  wrote. If a file has changed since, it has been hand-edited in GB Studio or
  the studio, and the generator **refuses to overwrite it** unless given
  `--force <scene>`.
- Existing scenes are only touched surgically. For example, the outbreak
  rumble is wrapped in a `Chapter` check. Every such change is listed in
  `docs/EDITING_GUIDE.md`.

## Draft 1 status (2026-10-19)

### Built
- **Maps:**
  - an OSM and land-cover campus world map (122×115 tiles, every location reachable);
  - 16 exteriors, 12 interiors and 14 set-piece backgrounds;
  - a tile catalogue (in 5 palette banks) and per-map tile atlases;
  - enriched GBC copies of the 14 original B7 backgrounds.
- **Sprites:** 13 walking characters and 9 objects, each with its own GBC sprite palette.
- **Game:** 54 generated scenes plus the patched originals.
  - Prologue → 3 Persona days → the outbreak (6 mechanics) → Act 3 (hub,
    7 memories, Hall of Doors) → finale → credits.
  - Bond assists, the in-place pause menu (a shared custom Script), and the
    dev chapter select.
- **Tools:**
  - the studio (web and CLI, with a TSV round trip);
  - the layout audit (`check_maps.py`);
  - the generator validator;
  - the PyBoy playtest harness.
- **Docs:** EDITING_GUIDE, STORY, LIFE, MAP, this plan; README; CLAUDE.md.

### Verified
- A headless GB Studio 4.3.2 build (CLI built from source) produces the ROM
  with no warnings.
- PyBoy playtests driven by real button presses and pathfinding:
  - the prologue battle;
  - Day 1 physics, Day 2 maths, the Day 1 dinner, the Day 3 workshop saw, the
    night walk into the outbreak;
  - world-map travel B7 → NBC (enter prompt, arrival banner);
  - the lounge into the siege; the lanes (15 kills); stealth through the tunnel;
  - the staircase chase; the rooftop run; the Dome;
  - all 7 memories completed normally; Hall of Doors → finale.
- The Codex review gate (`gpt-6.1-sol`):
  - round 1 (medium) found 2 blockers, 5 bugs, polish items and feature ideas;
    all were fixed or adopted;
  - round 2 (high) ran a continuous playtest of the pre-fix ROM and
    found 3 blockers (collision box, India start trap, off-camera controller
    actors), 8 bugs and pacing notes.
  - I made the final call on each finding. The blockers and bugs, plus most
    polish items, are fixed and re-verified on the rebuilt ROM. The decisions
    are listed in CLAUDE.md under "Review gate".
- The layout audit is clean apart from intentional items: your original
  "Begin" trigger, isolated edge pockets, and overlaps already present in the
  original scenes.

### Not done or open
- No full new-game-to-credits run by one human player yet: play it and tell
  me what feels off.
- Music is placeholder (GB Studio sample songs by Rulz); Muskaan's theme is a
  sound-effect chime.
- Characters are draft pixel art; the friends' personalities are placeholders
  (see the [EDIT] items in docs/STORY.md).
- Not verified on real hardware or in the GB Studio GUI's play mode, only in
  the CLI build, PyBoy and (structurally) the web export.
- Pause is unavailable inside the blocking turn-based battles and the saw loop
  (by GB Studio design); available everywhere else.
- Deferred feature ideas from review:
  - a free-evening friend picker / map highlight;
  - "Return to Hub" from inside a memory;
  - a re-arranged Muskaan motif for the reunion;
  - studio overlays of actor bounds and activation areas.
