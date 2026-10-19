# Campus map: how it was made, and how to change it

## Sources
- **OpenStreetMap** (Overpass API, fetched 2026-10-19), © OpenStreetMap
  contributors, ODbL 1.0: `art/maps/source/muj_osm.json`. It covers 583
  features: buildings, roads, footpaths, pitches, the pool, the reservoir and
  forest.
- **Land cover** (trees, scrub, bare earth, farms) classified from Esri World
  Imagery colour samples: `art/maps/source/landcover_campus.json`. Only the
  derived grid is stored; the imagery itself is not included.
- Cross-checks: MUJ hostel and campus pages, the Hafeez Contractor project
  page, student reviews. The full research notes and confidence levels are in
  the Todoist "Map" task comment.

## Key facts the map follows
- Two walled zones on either side of a public road: the **hostels (GHS)** to
  the west and the **university** to the east, joined by a **pedestrian
  underpass** under that road. It runs under the road between the zones, not
  under NH-48, which is 1.3 km south.
- The tree-lined **hostel avenue** runs west to east. Boys' blocks
  B1–B7 (B8–B10 are new) are north of it; girls' blocks G1–G4 and the BlueDove
  mess are south.
- **B7** is in the north-west, with the **Quess Mess** next to it, and courts
  inside the U.
- **AB1** and **AB2** are ring buildings with courtyards. The amphitheatre is
  in the AB2 courtyard.
- The **Dome** is the Administrative Block, with the Central Library.
- The **Cricket ground** (a circle with a running track) is north; the courts
  are next to it.
- **NBC/BABA** food stalls are by the road; the **Workshop** is east of AB2;
  the **Ocean Hills Pool** is south-west of the girls' blocks.
- Your sketch matches this if you rotate it so that real west is at the top.

## Rotation
Everything is rotated **−17.4°** so the public road runs vertically and the
avenue horizontally. That gives clean Game Boy roads instead of staircases.
North on the in-game map is therefore tilted.

## Files
| What | Where |
|---|---|
| Runtime backgrounds (GBC, canonical greens + per-tile palettes) | `assets/backgrounds/muj/*.png` + `.gbsres` |
| Colour previews | `art/maps/preview/*.png` |
| Map metadata (doors, exits, spawn, tile counts, collisions) | `art/maps/*.json` |
| Enriched copies of your original B7 art | `assets/backgrounds/enriched/` (originals untouched; provenance in `art/maps/enriched_provenance.json`) |
| Map specs (size, centre, doors, interiors as ASCII) | `tools/map/maps_local.py` |
| World map builder | `tools/map/world.py` |
| Tile and object painter (grass, paths, trees, buildings, shadows) | `tools/map/painter.py` |
| Palettes (day, night, dusk, blood, memory, dreamA/B/C) | `tools/map/gbc.py` |
| **Tile catalogue** (every texture + variants, edges, trees, hedges, roofs, walls; per palette bank) | `art/tilesets/muj/catalogue_<bank>.png` |
| **Per-map tile atlases** (the unique tiles each map uses) | `art/tilesets/muj/atlas_<map>.png` |

## Maps
- **World map** (`world_campus`, 122×115 tiles, 7 m per tile): the
  Chrono Trigger-style travel map. It has 18 locations, and every location is
  guaranteed reachable: woods are cut by dirt trails where needed.
- **Exteriors** (cut from the same OSM world at 2–3 m per tile):
  - Hostel Avenue, B7 Courts, Scrub Trail behind B7
  - Block 1, Block 2, Girls' Blocks, Ocean Hills Pool
  - Hostel Gate & Underpass
  - The Dome, AB1, AB2 & Amphitheatre, Old Mess & Grand Staircase, AB3 & Labs
  - Workshop, Cricket Ground, NBC & BABA
- **Interiors** (ASCII layouts):
  - Physics (AB1-101), Maths (AB2-214), Chemistry lab, Workshop floor
  - Quess Mess, BlueDove Mess, Old Mess
  - Dome rotunda and library, Pool hall, Underpass tunnel, Hostel corridor
  - Bedroom 2009
- **Set pieces:** pocket battle, zombie battle hall, lane defence, rooftop
  run, starfield void, flight sky, London street, childhood school, home,
  orbits, low corridor, day card, Hall of Doors, flower field.
- **Your original B7 scenes** remain the B7 interiors and front. The world map's
  "B7 Hostel" leads into them, and their empty edge triggers lead back out.

## Changing maps
- **Paint by hand** in LibreSprite: open `assets/backgrounds/muj/<map>.png`.
  It uses the four canonical greens (light → dark). Recolour tiles in GB
  Studio with the Colorize brush (palette slots: 0 grass, 1 path/sand,
  2 stone, 3 brick, 4 roof/glass, 5 water, 6 wood, 7 UI). After hand-editing,
  the generator will not overwrite the PNG (`art/maps/.generated.json`).
- **Regenerate**: edit `tools/map/maps_local.py` (an interior's ASCII, a
  door's position), then run `python3 tools/map/build_maps.py <name>` and
  `python3 tools/game/build_game.py`.
- **Check layouts**: `python3 tools/game/check_maps.py`. It reports
  unreachable doors, arrival points on walls or inside triggers, and
  overlapping triggers.
- The tile budget is 384 unique tiles per background in GBC mode. The builder
  merges rare look-alike tiles automatically and reports how many.
