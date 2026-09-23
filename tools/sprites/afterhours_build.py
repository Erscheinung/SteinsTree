#!/usr/bin/env python3
"""Build the After Hours test sprite pack from tools/sprites/afterhours_art.py.

Writes (and only writes):
  assets/sprites/afterhours_*.png          runtime strips, canonical GB colors
  art/sprites/source/afterhours_*.ase      editable LibreSprite/Aseprite sources
  art/sprites/preview/afterhours_*.png|gif After Hours colored previews
  art/sprites/afterhours_manifest.json     frame order, timing, provenance

Usage: python3 tools/sprites/afterhours_build.py   (from the repo root or anywhere)
Requires Pillow. Validate afterwards with afterhours_validate.py.
"""
import json
import os
import struct
import sys
import zlib

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import afterhours_art as art  # noqa: E402

RUNTIME_DIR = os.path.join(ROOT, "assets", "sprites")
SOURCE_DIR = os.path.join(ROOT, "art", "sprites", "source")
PREVIEW_DIR = os.path.join(ROOT, "art", "sprites", "preview")
MANIFEST = os.path.join(ROOT, "art", "sprites", "afterhours_manifest.json")

# Canonical GB Studio sprite import colors (runtime strips use ONLY these).
RUNTIME = {
    ".": (0x65, 0xFF, 0x00),  # transparent key
    "o": (0xE0, 0xF8, 0xCF),  # light
    "+": (0x86, 0xC0, 0x6C),  # middle
    "#": (0x07, 0x18, 0x21),  # dark
}
# After Hours display colors for previews only.
PREVIEW = {
    "o": (0xE8, 0xDF, 0xC8),
    "+": (0x9B, 0xA5, 0x8D),
    "#": (0x24, 0x23, 0x37),
}
PREVIEW_BG = (0x59, 0x65, 0x79)  # 4th After Hours background shade
GLYPHS = [".", "o", "+", "#"]
F = 16


def hexc(c):
    return "#%02X%02X%02X" % c


# ----------------------------------------------------------------------------
# Runtime PNG (indexed, like the existing assets/sprites/*.png)
# ----------------------------------------------------------------------------

def strip_indices(frames):
    w = F * len(frames)
    data = bytearray(w * F)
    for i, g in enumerate(frames):
        for y, row in enumerate(g):
            for x, ch in enumerate(row):
                data[y * w + i * F + x] = GLYPHS.index(ch)
    return w, bytes(data)


def write_runtime(name, frames):
    w, data = strip_indices(frames)
    im = Image.frombytes("P", (w, F), data)
    pal = []
    for g in GLYPHS:
        pal += RUNTIME[g]
    im.putpalette(pal)
    im.save(os.path.join(RUNTIME_DIR, name + ".png"), optimize=False)


# ----------------------------------------------------------------------------
# Minimal Aseprite/LibreSprite .ase writer (RGBA, two layers, tags, durations)
# ----------------------------------------------------------------------------

def _string(s):
    b = s.encode("utf-8")
    return struct.pack("<H", len(b)) + b


def _chunk(ctype, payload):
    return struct.pack("<IH", len(payload) + 6, ctype) + payload


def _cel(layer, rgba):
    head = struct.pack("<HhhBH", layer, 0, 0, 255, 2) + b"\0" * 7
    return _chunk(0x2005, head + struct.pack("<HH", F, F) + zlib.compress(rgba))


def _frame_rgba(grid, key_only=False):
    out = bytearray()
    for row in grid:
        for ch in row:
            if key_only:
                out += bytes(RUNTIME["."]) + b"\xff"
            elif ch == ".":
                out += b"\0\0\0\0"
            else:
                out += bytes(RUNTIME[ch]) + b"\xff"
    return bytes(out)


def write_ase(path, frames, durations, tags):
    colors = [RUNTIME[g] for g in GLYPHS]
    frame_blobs = []
    for i, (grid, ms) in enumerate(zip(frames, durations)):
        chunks = []
        if i == 0:
            old_pal = struct.pack("<HBB", 1, 0, len(colors))
            old_pal += b"".join(bytes(c) for c in colors)
            chunks.append(_chunk(0x0004, old_pal))
            new_pal = struct.pack("<III", len(colors), 0, len(colors) - 1)
            new_pal += b"\0" * 8
            new_pal += b"".join(struct.pack("<HBBBB", 0, *c, 255) for c in colors)
            chunks.append(_chunk(0x2019, new_pal))
            # bottom layer: opaque GB Studio key; top layer: the drawing
            chunks.append(_chunk(0x2004, struct.pack("<HHHHHHB", 1 | 2 | 4 | 8, 0, 0, F, F, 0, 255)
                                 + b"\0" * 3 + _string("gbs_key_65FF00")))
            chunks.append(_chunk(0x2004, struct.pack("<HHHHHHB", 1 | 2, 0, 0, F, F, 0, 255)
                                 + b"\0" * 3 + _string("art")))
            tag_blob = struct.pack("<H", len(tags)) + b"\0" * 8
            for name, a, b in tags:
                tag_blob += struct.pack("<HHB", a, b, 0) + b"\0" * 8
                tag_blob += bytes((0, 0, 0)) + b"\0" + _string(name)
            chunks.append(_chunk(0x2018, tag_blob))
        chunks.append(_cel(0, _frame_rgba(grid, key_only=True)))
        chunks.append(_cel(1, _frame_rgba(grid)))
        body = b"".join(chunks)
        header = struct.pack("<IHHH2sI", 16 + len(body), 0xF1FA, len(chunks), ms, b"\0\0", len(chunks))
        frame_blobs.append(header + body)
    frames_data = b"".join(frame_blobs)
    header = struct.pack("<IHHHHHIHIIB3sHBBhhHH",
                         128 + len(frames_data), 0xA5E0, len(frames), F, F, 32, 1,
                         durations[0], 0, 0, 0, b"\0\0\0", len(colors), 1, 1, 0, 0, 0, 0)
    header += b"\0" * (128 - len(header))
    with open(path, "wb") as fh:
        fh.write(header + frames_data)


# ----------------------------------------------------------------------------
# Previews
# ----------------------------------------------------------------------------

PREVIEW_PAL_ORDER = [PREVIEW_BG, PREVIEW["o"], PREVIEW["+"], PREVIEW["#"]]


def grid_to_preview(grid, bg=PREVIEW_BG, mirror=False):
    im = Image.new("RGB", (F, F), bg)
    for y, row in enumerate(grid):
        if mirror:
            row = row[::-1]
        for x, ch in enumerate(row):
            if ch != ".":
                im.putpixel((x, y), PREVIEW[ch])
    return im


def to_p(im):
    """Quantize to the exact 4 preview colors (no dithering, exact lookup)."""
    pal = []
    for c in PREVIEW_PAL_ORDER:
        pal += c
    idx = {c: i for i, c in enumerate(PREVIEW_PAL_ORDER)}
    p = Image.frombytes("P", im.size, bytes(idx[c] for c in im.getdata()))
    p.putpalette(pal)
    return p


def write_strip_preview(name, frames, scale=8, gap=1):
    n = len(frames)
    w = (n * F + (n + 1) * gap) * scale
    h = (F + 2 * gap) * scale
    sheet = Image.new("RGB", ((n * F + (n + 1) * gap), F + 2 * gap), PREVIEW["#"])
    for i, g in enumerate(frames):
        sheet.paste(grid_to_preview(g), (gap + i * (F + gap), gap))
    sheet = sheet.resize((w, h), Image.NEAREST)
    to_p(sheet).save(os.path.join(PREVIEW_DIR, name + "_preview.png"))


def write_gif(name, panels_per_step, durations, scale=6, gap=2):
    """panels_per_step: list of steps; each step is a list of RGB 16x16 panels."""
    n = len(panels_per_step[0])
    size = (n * F + (n + 1) * gap, F + 2 * gap)
    frames = []
    for panels in panels_per_step:
        im = Image.new("RGB", size, PREVIEW_BG)
        for i, p in enumerate(panels):
            im.paste(p, (gap + i * (F + gap), gap))
        im = im.resize((size[0] * scale, size[1] * scale), Image.NEAREST)
        frames.append(to_p(im))
    frames[0].save(os.path.join(PREVIEW_DIR, name + ".gif"), save_all=True,
                   append_images=frames[1:], duration=durations, loop=0,
                   optimize=False, disposal=1)


def write_contact_sheet(scale=4, gap=2):
    names = list(art.STRIPS)
    rows = []
    for bg in (PREVIEW_BG, PREVIEW["o"]):
        for n in names:
            rows.append((n, bg))
    width = 6 * (F + gap) + gap
    im = Image.new("RGB", (width, len(rows) * (F + gap) + gap), PREVIEW["#"])
    for r, (n, bg) in enumerate(rows):
        for i, g in enumerate(art.STRIPS[n]["frames"]):
            im.paste(grid_to_preview(g, bg=bg), (gap + i * (F + gap), gap + r * (F + gap)))
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    im.save(os.path.join(PREVIEW_DIR, "afterhours_contact_sheet.png"))


# ----------------------------------------------------------------------------
# Manifest data
# ----------------------------------------------------------------------------

DIALOGUE = {
    "player": [
        {"path": "project/scenes/outside/triggers/begin.gbsres", "text": "Life is\nmeaningless..."},
        {"path": "project/scenes/outside/triggers/begin.gbsres", "text": "And college sucks!"},
        {"path": "project/scenes/scene_5/actors/mayank.gbsres", "text": "You: I'm gonna\ncheck it out."},
        {"path": "project/scenes/scene_13/triggers/trigger.gbsres",
         "text": "What was that? I\nmust tell Mayank\nimmediately!"},
    ],
    "mayank": [
        {"path": "project/scenes/scene_5/actors/mayank.gbsres", "text": "Something weird is\ngoing on...",
         "note": "unlabelled line inside Mayank's actor script; speaker not asserted"},
        {"path": "project/scenes/scene_5/actors/mayank.gbsres", "text": "Mayank: Hey! Did\nyou\nhear that?"},
        {"path": "project/scenes/scene_5/actors/mayank.gbsres", "text": "came from the B7\nmain gate area."},
        {"path": "project/scenes/scene_5/actors/mayank.gbsres", "text": "Mayank: Ok, I'll\nwait here."},
    ],
    "scholar": [
        {"path": "project/scenes/scene_13/scene.gbsres", "text": "Random MUJ\nscholar: grrrr!"},
    ],
}

CHARACTERS = {
    "player": {
        "display_name": "Player (\"You\")",
        "visual_interpretation": "Tired student: messy hair, side-swept fringe, heavy-lidded eyes, "
                                 "middle-tone hoodie with light backpack straps, dark trousers. "
                                 "Interpretation of the opening lines, not canon.",
    },
    "mayank": {
        "display_name": "Mayank",
        "visual_interpretation": "Alert friend: neat side-parted hair, glasses, light collared shirt, "
                                 "belt, middle-tone trousers. Interpretation, not canon.",
    },
    "scholar": {
        "display_name": "Random MUJ scholar",
        "visual_interpretation": "Uncanny echo / optional zombie study: grey (middle) skin, blank light "
                                 "eyes, gaping mouth, tilted head, light coat with lanyard and card, torn "
                                 "hem, reaching arms and dragging gait. Reads as a zombie for the legacy "
                                 "idea or as a hollowed-out double of a student for the existential "
                                 "direction. Interpretation, not canon.",
    },
}

KIND_NOTES = {
    "walk": "GB Studio walking actor order: down A, down B, up A, up B, right A, right B. Left = flipped right.",
    "idle": "Front-facing dialogue idle loop (separate sprite sheet).",
    "react": "Front-facing dialogue reaction, play once or loop (separate sprite sheet).",
}


def tags_for(name, spec):
    if name.endswith("_walk"):
        return [("walk_down", 0, 1), ("walk_up", 2, 3), ("walk_right", 4, 5)]
    return [(name.split("_", 1)[1], 0, len(spec["frames"]) - 1)]


def build():
    for d in (RUNTIME_DIR, SOURCE_DIR, PREVIEW_DIR):
        os.makedirs(d, exist_ok=True)
    strips = []
    for name, spec in art.STRIPS.items():
        frames, ms, labels = spec["frames"], spec["ms"], spec["labels"]
        char, kind = name.split("_")[1], name.split("_")[2]
        tags = tags_for(name, spec)
        write_runtime(name, frames)
        write_ase(os.path.join(SOURCE_DIR, name + ".ase"), frames, ms, tags)
        write_strip_preview(name, frames)
        if kind == "walk":
            steps, durs = [], []
            for k in (0, 1):  # A then B for every direction at once; GIF loops
                steps.append([grid_to_preview(frames[0 + k]), grid_to_preview(frames[2 + k]),
                              grid_to_preview(frames[4 + k]), grid_to_preview(frames[4 + k], mirror=True)])
                durs.append(ms[k])
            gif_note = "panels: down, up, right, left (right mirrored as GB Studio would)"
        else:
            steps = [[grid_to_preview(g)] for g in frames]
            durs = list(ms)
            gif_note = "single front-facing panel"
        write_gif(name, steps, durs)
        strips.append({
            "name": name,
            "character": char,
            "kind": kind,
            "runtime_png": "assets/sprites/%s.png" % name,
            "source_ase": "art/sprites/source/%s.ase" % name,
            "preview_png": "art/sprites/preview/%s_preview.png" % name,
            "preview_gif": "art/sprites/preview/%s.gif" % name,
            "preview_gif_layout": gif_note,
            "size_px": [F * len(frames), F],
            "frame_count": len(frames),
            "frames": [{"index": i, "label": labels[i], "preview_ms": ms[i]} for i in range(len(frames))],
            "ase_tags": [{"name": t[0], "from": t[1], "to": t[2]} for t in tags],
            "notes": KIND_NOTES[kind],
        })
    write_contact_sheet()

    manifest = {
        "pack": "afterhours_sprite_test",
        "status": "TEST ASSETS. Visual interpretations of existing dialogue, not story canon. "
                  "The owner intends to author final art; original sprites in assets/sprites/ are untouched.",
        "provenance": {
            "author": "Generated with Claude Code (model claude-opus-5-5) on 2026-09-23 at the owner's request.",
            "method": "Original pixel art hand-specified as character grids in tools/sprites/afterhours_art.py "
                      "and rendered by tools/sprites/afterhours_build.py. Not traced or edited from any existing "
                      "or third-party sprite. No antialiasing, no scaling of runtime art.",
            "regenerate": "python3 tools/sprites/afterhours_build.py && python3 tools/sprites/afterhours_validate.py",
            "note": "Rebuilding overwrites the generated files listed here; once the owner edits an .ase by hand, "
                    "treat that .ase as the source and stop regenerating it.",
        },
        "project": {"descriptor": "Dernier.json", "gb_studio": "4.2", "color_mode": "monochrome (unchanged)"},
        "frame_size_px": [F, F],
        "palette": {
            "runtime_import": {"transparent_key": hexc(RUNTIME["."]), "light": hexc(RUNTIME["o"]),
                               "middle": hexc(RUNTIME["+"]), "dark": hexc(RUNTIME["#"])},
            "preview_display": {"light": hexc(PREVIEW["o"]), "middle": hexc(PREVIEW["+"]),
                                "dark": hexc(PREVIEW["#"]), "preview_background": hexc(PREVIEW_BG)},
            "note": "Runtime PNGs contain only the four import colors. Previews map light/middle/dark to the "
                    "After Hours colors and show transparency as #596579 (contact sheet also on #E8DFC8). "
                    "Never import preview PNG/GIF files as sprites.",
        },
        "ase_sources": "RGBA .ase, 16x16 canvas. Layer 'gbs_key_65FF00' (locked background, solid key) under "
                       "layer 'art' (transparent where keyed). Frame durations = preview_ms; tags as listed. "
                       "Export: File > Export Sprite Sheet, horizontal, no padding, both layers visible; or "
                       "libresprite -b SOURCE.ase --sheet OUT.png --sheet-type horizontal.",
        "characters": {k: dict(v, dialogue_sources=DIALOGUE[k]) for k, v in CHARACTERS.items()},
        "strips": strips,
        "gb_studio_import": [
            "GB Studio picks up new PNGs in assets/sprites/ automatically when the project is open/reloaded and "
            "creates its own .gbsres sidecar; this pack does not ship sidecars.",
            "Walk strips: in the Sprite Editor choose an animation type with four directions, assign frames "
            "down=0,1 up=2,3 right=4,5 and enable flipping Right to create Left. Tune animation speed by eye.",
            "Idle/react strips are separate sprite sheets. Use them in dialogue with 'Set Actor Sprite Sheet' "
            "(swap before/after the text) or combine frames into one image yourself if you want them as extra "
            "states of the walking sprite; a PNG strip alone does not configure a state.",
            "Actors currently use their existing sprites; nothing in project/ or Dernier.json was changed.",
        ],
        "not_performed": [
            "No GB Studio import, compile or ROM build was run.",
            "Sprite Editor tile/frame auto-detection for these PNGs was not observed.",
        ],
    }
    with open(MANIFEST, "w") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    build()
    print("built %d strips" % len(art.STRIPS))
