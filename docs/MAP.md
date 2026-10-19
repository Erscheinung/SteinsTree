# Campus maps — draft 2, owner's art

The original B7 scenes are the visual reference and the core of the game.
Their PNGs in `assets/backgrounds/` and the pristine scenes in
`tools/game/legacy_snapshot/` must remain unchanged. The enriched draft-1
copies are retired from the owner's scenes.

## Layout and connections

Campus geography determines connections, rather than literal building
footprints. The compact campus overview replaces the 122×115-tile map.
Local scenes use 20×18 to 32×32 tiles. Existing scene keys and IDs remain
stable so the story, menus and saved editing references keep working.

The main destinations are:

| Place | Map keys |
|---|---|
| AB1 / physics | `ab1`, `physics_class` |
| AB2 / maths | `ab2`, `maths_class` |
| AB3 / chemistry | `ab3`, `chem_lab` |
| Quess Mess / B7 approach | `hostel_avenue`, `quess_mess_in`, original B7 scenes |
| Workshop | `workshop`, `workshop_in` |
| Cricket ground | `cricket_ground` |
| Dome / administration | `dome`, `dome_in` |
| Underpass | `underpass`, `underpass_tunnel` |
| Scrub behind B7 | `scrub_trail` |
| NBC food court | `nbc` |

Secondary locations retain their keys too: `b7_courts`, `block1`, `block2`,
`girls_blocks`, `pool`, and `grand_staircase`. These are compact compatibility
maps, not additional giant satellite tracings. Act 2 mechanics and Act 3
memory maps retain their story roles.

The hostel side connects to the academic side through the pedestrian
underpass. B7, Quess Mess and scrub remain on the hostel side; AB1/2/3,
Workshop, Dome and cricket remain academic destinations. NBC is by the road.
The geographical reference is documented in `art/maps/source/muj_osm.json`
(© OpenStreetMap contributors, ODbL); it does not dictate pixel geometry.

## Editable sources

| File | Purpose |
|---|---|
| `tools/map/owner.py` | Owner-art tile extraction and compact map construction |
| `tools/map/owner_layouts.json` | Editable local layouts |
| `art/tilesets/owner_library.png` and `.json` | Reusable tiles and source provenance |
| `assets/backgrounds/muj/*.png` and `.gbsres` | Runtime art and background metadata |
| `art/maps/*.json` | Collisions, spawns, doors and exits |
| `art/maps/preview/compare/` | Original and colour candidates side by side |
| `art/maps/preview/ingame/` | Screenshots from the built ROM |
| `tools/game/story/*.py` | Actors, scene changes, dialogue and story conditions |

Never overwrite the original PNGs when trying a palette conversion. Make a
separate candidate and compare small details: door frames, window mullions,
planter edges and octagon paving should remain distinct.

## Regenerate and verify

Run from the worktree:

```
python3 tools/map/build_maps.py
python3 tools/game/build_game.py
python3 tools/game/build_game.py --check
python3 tools/game/check_maps.py
```

A scene change must arrive away from the destination's own exit trigger.
The player is two tiles wide. Keep actors, doors and paths compatible with
that width, and rerun the map audit after moving any of them. Follow scene
regeneration's edit guard when a scene has been changed manually.

Original `B7-10.png` is 257×257; preserve it. The compiler's size warning for
that original is separate from a tile-budget error. ROM compilation and the
GB Studio load/denormalize check are both necessary: one cannot substitute
for the other.

## Colour choice and the salmon editor rendering

For the original scenes, the selected approach is **monochrome** (option c),
inside the CGB-only project. They reference the original PNGs and explicit
DMG palettes. This retains their original pixel structure without using the
flattened enriched copies. The comparison sheets include the original, the
fixed-colour candidate, and the selected mono rendering. Keep in mind that
mono cannot reproduce the original RGB hues.

New maps use a four-shade indexed PNG and an explicit palette slot per tile.
Their contiguous facade, paving and planter patches keep the original
compositions coherent. The shared day brick ramp is warm plaster/ochre/brown/
mauve (`E8D0A8`, `D0A078`, `A87868`, `786078`); other banks support the existing
night, outbreak and dream logic. This is a constrained GBC conversion, so
some source colours necessarily merge. The tile-library JSON records source
patches for further manual refinement.

GB Studio 4.3.2's `ColorizedImage.worker.ts` reads only the source **green
channel** to select shade 3/2/1/0 at thresholds 65/130/205. It then selects the
palette with `tiles[t] & 7`. It does not render arbitrary RGB colours in the
manual-colour path. The old maps' large warm roofs and walls used the brick
slot's salmon ramp; that colour was a palette/design result rather than an
AutoColor failure. New indexed backgrounds, tile-slot data and palette
resources are regenerated together. The editor's separate AutoColor solver
was not used for the selected runtime art; an earlier local approximation
was removed from the final comparisons.

The stylised overview is **48×32 tiles**, with 18 destination markers; local
exteriors remain at most 32×32. It describes connections, not campus scale.
