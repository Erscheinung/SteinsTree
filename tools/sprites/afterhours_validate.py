#!/usr/bin/env python3
"""Validate the After Hours test sprite pack (structure, colors, motion).

Checks every strip listed in art/sprites/afterhours_manifest.json:
  - runtime PNG size = 16*frames x 16 and frame count matches manifest
  - walking strips are exactly 96x16 (6 frames)
  - runtime pixels use only #65FF00 #E0F8CF #86C06C #071821 (no antialiasing)
  - every frame has drawn pixels and differs from its neighbours; walk pairs
    (down/up/right A vs B) differ; no frame is just a translated copy of its
    pair (rejects whole-frame jitter); tiles per frame counted (8x8)
  - previews use only After Hours colors; GIFs decode with expected frames
  - dialogue quotes in the manifest exist verbatim in the cited files
  - optional (--libresprite): LibreSprite opens each .ase, exports a sheet that
    matches the runtime PNG pixel-for-pixel, and re-saves layers/tags/timing
  - original sprites in assets/sprites/ unchanged vs git HEAD (if tracked)

This is a structural check. It does NOT import into or build with GB Studio.
"""
import json
import os
import struct
import subprocess
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MANIFEST = os.path.join(ROOT, "art", "sprites", "afterhours_manifest.json")
LIBRESPRITE = "/Applications/libresprite.app/Contents/MacOS/libresprite"

RUNTIME = {(0x65, 0xFF, 0x00), (0xE0, 0xF8, 0xCF), (0x86, 0xC0, 0x6C), (0x07, 0x18, 0x21)}
KEY = (0x65, 0xFF, 0x00)
PREVIEW = {(0xE8, 0xDF, 0xC8), (0x9B, 0xA5, 0x8D), (0x24, 0x23, 0x37), (0x59, 0x65, 0x79)}

failures = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failures.append(msg)


def frames_of(im, n):
    return [tuple(im.crop((i * 16, 0, i * 16 + 16, 16)).getdata()) for i in range(n)]


def translated_copy(a, b):
    """True if frame b equals frame a shifted by some (dx, dy) != (0,0)."""
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            if (dx, dy) == (0, 0):
                continue
            same = True
            for y in range(16):
                for x in range(16):
                    sx, sy = x - dx, y - dy
                    pa = a[sy * 16 + sx] if 0 <= sx < 16 and 0 <= sy < 16 else KEY
                    if pa != b[y * 16 + x]:
                        same = False
                        break
                if not same:
                    break
            if same:
                return True
    return False


def unique_tiles(im):
    tiles = set()
    for ty in range(0, im.height, 8):
        for tx in range(0, im.width, 8):
            tiles.add(tuple(im.crop((tx, ty, tx + 8, ty + 8)).getdata()))
    return len(tiles)


def run_libresprite(args):
    p = subprocess.run([LIBRESPRITE, "-b"] + args, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=120)
    return p.returncode


def ase_summary(path):
    b = open(path, "rb").read()
    _, magic, nf, w, h, depth = struct.unpack_from("<IHHHHH", b, 0)
    off, layers, tags, durs = 128, [], [], []
    for _ in range(nf):
        fsize, _, old, dur, _, new = struct.unpack_from("<IHHH2sI", b, off)
        durs.append(dur)
        o = off + 16
        for _ in range(new or old):
            cs, ct = struct.unpack_from("<IH", b, o)
            if ct == 0x2004:
                n = struct.unpack_from("<H", b, o + 22)[0]
                layers.append(b[o + 24:o + 24 + n].decode())
            elif ct == 0x2018:
                q = o + 16
                for _ in range(struct.unpack_from("<H", b, o + 6)[0]):
                    a, z, _ = struct.unpack_from("<HHB", b, q)
                    q += 17
                    n = struct.unpack_from("<H", b, q)[0]
                    tags.append((b[q + 2:q + 2 + n].decode(), a, z))
                    q += 2 + n
            o += cs
        off += fsize
    return {"magic": magic, "frames": nf, "size": (w, h), "depth": depth,
            "layers": layers, "tags": tags, "durations": durs}


def main():
    use_ls = "--libresprite" in sys.argv
    m = json.load(open(MANIFEST))
    tmp = tempfile.mkdtemp(prefix="afterhours_")

    for s in m["strips"]:
        name, n = s["name"], s["frame_count"]
        print(name)
        png = os.path.join(ROOT, s["runtime_png"])
        im = Image.open(png).convert("RGB")
        check(im.size == (16 * n, 16) and tuple(s["size_px"]) == im.size,
              "runtime size %sx%s for %d frames" % (im.width, im.height, n))
        if s["kind"] == "walk":
            check(im.size == (96, 16) and n == 6, "walk strip is 96x16 with 6 frames")
        colors = set(im.getdata())
        check(colors <= RUNTIME, "runtime colors only canonical: %s" % sorted("#%02X%02X%02X" % c for c in colors))
        check(KEY in colors, "transparent key #65FF00 present")
        fr = frames_of(im, n)
        check(all(any(p != KEY for p in f) for f in fr), "every frame has drawn pixels")
        check(all(f[0] == KEY for f in fr), "top-left of each frame is key (background transparent)")
        check(all(fr[i] != fr[(i + 1) % n] for i in range(n)), "no two consecutive frames identical")
        check(len(set(fr)) == n, "all %d frames distinct" % n)
        if s["kind"] == "walk":
            for d, (a, b) in zip(("down", "up", "right"), ((0, 1), (2, 3), (4, 5))):
                diff = sum(1 for x, y in zip(fr[a], fr[b]) if x != y)
                check(diff >= 4 and not translated_copy(fr[a], fr[b]),
                      "%s A/B differ by %d px and are not a shifted copy" % (d, diff))
            bottom = [max(y for y in range(16) for x in range(16) if f[y * 16 + x] != KEY) for f in fr]
            check(all(b == 15 for b in bottom), "grounded baseline: lowest drawn row = 15 in all walk frames")
        print("       unique 8x8 tiles in strip: %d (%d tile slots)" % (unique_tiles(im), (im.width // 8) * 2))
        check([f["index"] for f in s["frames"]] == list(range(n)), "manifest frame order 0..%d" % (n - 1))

        pv = Image.open(os.path.join(ROOT, s["preview_png"])).convert("RGB")
        check(set(pv.getdata()) <= PREVIEW, "preview PNG uses only After Hours colors")
        gif = Image.open(os.path.join(ROOT, s["preview_gif"]))
        gif_frames, gif_colors = 0, set()
        try:
            while True:
                gif_colors |= set(gif.convert("RGB").getdata())
                gif_frames += 1
                gif.seek(gif.tell() + 1)
        except EOFError:
            pass
        expect = 2 if s["kind"] == "walk" else n  # walk GIF: A/B for 4 directions side by side
        check(gif_frames == expect and gif_colors <= PREVIEW,
              "GIF decodes %d frames (expect %d), After Hours colors only" % (gif_frames, expect))

        ase = os.path.join(ROOT, s["source_ase"])
        info = ase_summary(ase)
        check(info["magic"] == 0xA5E0 and info["frames"] == n and info["size"] == (16, 16),
              ".ase header: %d frames 16x16" % info["frames"])
        check(info["durations"] == [f["preview_ms"] for f in s["frames"]], ".ase durations match manifest")
        check([t for t in info["tags"]] == [(t["name"], t["from"], t["to"]) for t in s["ase_tags"]],
              ".ase tags match manifest")
        if use_ls:
            out = os.path.join(tmp, name + ".png")
            run_libresprite([ase, "--sheet", out, "--sheet-type", "horizontal"])
            ok = os.path.exists(out)
            if ok:
                ls = Image.open(out).convert("RGB")
                ok = ls.size == im.size and list(ls.getdata()) == list(im.getdata())
            check(ok, "LibreSprite export of .ase == runtime PNG (pixel exact)")
            resaved = os.path.join(tmp, name + "_resaved.ase")
            run_libresprite([ase, "--save-as", resaved])
            ok = os.path.exists(resaved)
            if ok:
                r = ase_summary(resaved)
                ok = (r["layers"] == info["layers"] and r["tags"] == info["tags"]
                      and r["durations"] == info["durations"])
            check(ok, "LibreSprite re-save keeps layers %s, tags, durations" % info["layers"])

    print("dialogue sources")
    for char, c in m["characters"].items():
        for d in c["dialogue_sources"]:
            text = open(os.path.join(ROOT, d["path"])).read()
            check(json.dumps(d["text"]) in text, "%s: %r in %s" % (char, d["text"], d["path"]))

    print("originals untouched")
    tracked = subprocess.run(["git", "ls-files", "assets/sprites"], cwd=ROOT,
                             stdout=subprocess.PIPE, text=True).stdout.split()
    dirty = subprocess.run(["git", "status", "--porcelain", "--"] + tracked, cwd=ROOT,
                           stdout=subprocess.PIPE, text=True).stdout.strip()
    check(tracked and not dirty, "%d tracked files in assets/sprites unchanged" % len(tracked))

    print("\n%s (%d failures). No GB Studio import/build performed by this script."
          % ("PASS" if not failures else "FAIL", len(failures)))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
