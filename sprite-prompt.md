# Reusable pixel-art and animation brief

Use this with Claude Code (requested model: Opus 5.5, effort high) or another
capable art assistant. The subject is supplied per request; do not assume a
wizard, genre, species, costume, gender, or animation set.

## Request

- Subject / role: [character, creature, prop, effect, or environment]
- References and context: [files, dialogue, visual references]
- Intent and mood: [what the player should feel or recognize]
- Required animations: [idle, walk, interaction, reaction, etc.]
- Views: [down, up, right; mirrored left only if appropriate]
- Constraints: [engine, frame dimensions, palette, frame budget, output paths]
- Must retain / avoid: [recognizable features and exclusions]

Read the relevant project files first. Separate facts from visual interpretations.
When details are missing, state modest assumptions and proceed. Ask only if a
missing decision prevents usable work. Do not change story text or gameplay.

## For this GB Studio project

- Inspect project version, color mode, existing sprite dimensions and sidecars.
- Default to 16×16 frames. A simple walking actor is a 96×16 horizontal strip:
  down A, down B, up A, up B, right A, right B; GB Studio can mirror right for left.
- Import sprite colors: light `#E0F8CF`, middle `#86C06C`, dark `#071821`,
  transparent key `#65FF00`. Do not use background-only `#306850` for sprites.
- Use a consistent grounded baseline and readable silhouettes. Draw distinct
  poses with intentional weight shift, not whole-frame jitter or a static repeat.
- Keep additional reactions in separately named strips or explicitly configured
  animation states. A PNG strip alone does not configure a custom state.
- Store runtime sheets under `assets/sprites/`; editable sources, colored
  previews and GIFs under `art/sprites/`. Never import preview GIFs as sprites.
- Use the After Hours palette for previews when available. Preserve canonical
  import shades independently of display colors; do not change project color mode.
- Original visual interpretations are welcome; never relabel edits of existing
  third-party sprites as original work.

## Delivery and validation

Produce actual files, not just a description. Include editable LibreSprite
sources if the installed tool supports them, PNG strips, animation previews,
and a manifest with frame indices, timing, dimensions, palette, provenance,
dialogue references and import instructions. Keep output restricted to the
agreed paths and preserve all unrelated work. Do not commit unless asked.

Check decoded pixel colors, dimensions, frame count/order, transparency and
distinct movement frames. Open previews when tools allow it. Report exactly
what was tested and whether a GB Studio build/import was actually performed;
never present a visual or structural check as an engine build.

Reference: https://www.gbstudio.dev/docs/assets/sprites/
