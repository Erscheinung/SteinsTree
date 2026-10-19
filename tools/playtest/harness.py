"""Headless playtest harness for the built ROM (PyBoy).

    python3 -m pip install pyboy pillow
    python3 tools/playtest/harness.py ROM.gb SYMFILE.sym OUTDIR [route]

Reads GB Studio variables straight from WRAM (`_script_memory` in the .sym
file + 2 bytes per variable id, names from project/variables.gbsres), so a
route can assert story state (Chapter, Phase, HP...) and saves screenshots.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class Game:
    def __init__(self, rom, sym, outdir, speed=0):
        from pyboy import PyBoy
        self.pb = PyBoy(str(rom), window="null", sound_emulated=False, cgb=True)
        self.pb.set_emulation_speed(speed)
        self.out = Path(outdir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.base = None
        for line in Path(sym).read_text().splitlines():
            if line.strip().endswith("_script_memory"):
                bank_addr = line.split()[0]
                self.base = int(bank_addr.split(":")[1], 16)
        self.actors = None
        for line in Path(sym).read_text().splitlines():
            if line.strip().endswith(" _actors"):
                self.actors = int(line.split()[0].split(":")[1], 16)
        vars_ = json.loads((ROOT / "project" / "variables.gbsres").read_text())["variables"]
        # GB Studio packs used variables into slots listed in globals.i
        glob = Path(sym).with_name("globals.i")
        slots = {}
        if glob.exists():
            for line in glob.read_text().splitlines():
                if line.startswith("VAR_") and "=" in line:
                    k, v = line.split("=")
                    slots[k.strip()] = int(v)
        self.vid = {}
        for v in vars_:
            sym_name = "VAR_" + v["symbol"][4:].upper() if v["symbol"].startswith("var_") else v["symbol"].upper()
            if sym_name in slots:
                self.vid[v["name"]] = slots[sym_name]
        self.n = 0
        self.log = []

    # ---- memory
    def var(self, name):
        a = self.base + self.vid[name] * 2
        v = self.pb.memory[a] | (self.pb.memory[a + 1] << 8)
        return v - 65536 if v >= 32768 else v

    def set_var(self, name, value):
        a = self.base + self.vid[name] * 2
        value &= 0xFFFF
        self.pb.memory[a] = value & 0xFF
        self.pb.memory[a + 1] = value >> 8

    # ---- time and input
    def wait(self, frames=60):
        for _ in range(frames):
            self.pb.tick()

    def press(self, button, frames=6, after=10):
        self.pb.button_press(button)
        self.wait(frames)
        self.pb.button_release(button)
        self.wait(after)

    def hold(self, button, frames):
        self.pb.button_press(button)
        self.wait(frames)
        self.pb.button_release(button)
        self.wait(4)

    def mash(self, button="a", times=10, gap=20):
        for _ in range(times):
            self.press(button, 4, gap)

    UI = {(200, 192, 168), (248, 240, 224), (24, 24, 40), (104, 96, 120)}

    def dialog_open(self):
        """True when GB Studio's dialogue/menu window covers the bottom rows."""
        im = self.pb.screen.image.convert("RGB")
        hits = sum(1 for x in range(0, 160, 4) for y in (130, 136, 142) if im.getpixel((x, y)) in self.UI)
        return hits > 60

    def clear(self, max_presses=40, button="a"):
        """Advance dialogue until the window closes (or max presses)."""
        n = 0
        while n < max_presses:
            closed = 0
            for _ in range(12):
                self.wait(10)
                closed = closed + 1 if not self.dialog_open() else 0
                if closed == 0:
                    break
            if closed >= 12:
                return n
            self.press(button, 4, 16)
            n += 1
        return n

    # ---- player position (actors[0].pos is in 1/32 px; tile = >> 8)
    def player_tile(self):
        m = self.pb.memory
        a = self.actors + 1
        x = m[a] | (m[a + 1] << 8)
        y = m[a + 2] | (m[a + 3] << 8)
        return x >> 8, y >> 8

    def step(self, direction, timeout=60):
        start = self.player_tile()
        self.pb.button_press(direction)
        for _ in range(timeout):
            self.pb.tick()
            if self.player_tile() != start:
                break
        self.pb.button_release(direction)
        self.wait(2)
        return self.player_tile() != start

    def walk_path(self, path, max_retry=3):
        """path: list of (x,y) tiles; steps one tile at a time."""
        for (x, y) in path[1:]:
            for _ in range(max_retry):
                px, py = self.player_tile()
                if (px, py) == (x, y):
                    break
                d = "right" if x > px else "left" if x < px else "down" if y > py else "up"
                if not self.step(d):
                    if self.dialog_open():
                        self.clear()
            if self.player_tile() != (x, y):
                return False
        return True

    def settle(self, quiet=40, limit=900):
        """Wait until the screen stops changing (text finished printing)."""
        last = None
        same = 0
        for _ in range(limit // 5):
            self.wait(5)
            cur = self.pb.screen.image.tobytes()
            same = same + 5 if cur == last else 0
            last = cur
            if same >= quiet:
                return True
        return False

    def shot(self, name):
        self.n += 1
        p = self.out / ("%03d_%s.png" % (self.n, name))
        self.pb.screen.image.convert("RGB").save(p)
        self.log.append((p.name, {k: self.var(k) for k in ("Chapter", "Phase", "Step", "Objective")
                                  if k in self.vid}))
        return p

    def until(self, pred, max_frames=3600, step=10, mash=None):
        f = 0
        while f < max_frames:
            if pred():
                return True
            if mash:
                self.press(mash, 3, step)
                f += step + 3
            else:
                self.wait(step)
                f += step
        return False

    def stop(self):
        self.pb.stop(save=False)


if __name__ == "__main__":
    rom, sym, out = sys.argv[1:4]
    g = Game(rom, sym, out)
    g.wait(300)
    g.shot("boot")
    g.stop()


def scene_grid(scene_dir):
    """Walkable grid of a project scene (True = open) from its collisions."""
    import sys as _s
    _s.path.insert(0, str(ROOT / "tools" / "map"))
    import gbc
    d = json.loads((Path(scene_dir) / "scene.gbsres").read_text())
    c = gbc.decompress8(d["collisions"]) if d["collisions"] else [0] * (d["width"] * d["height"])
    w, h = d["width"], d["height"]
    return [[c[y * w + x] == 0 for x in range(w)] for y in range(h)], w, h


def bfs(grid, w, h, start, goal, wide=2, tall=1):
    """Shortest tile path for an actor `wide` x `tall` tiles (tall rows end at y)."""
    from collections import deque

    def ok(x, y):
        return 0 <= x and x + wide - 1 < w and tall - 1 <= y < h and \
            all(grid[y - r][x + k] for k in range(wide) for r in range(tall))
    prev = {start: None}
    q = deque([start])
    while q:
        c = q.popleft()
        if c == goal:
            break
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + dx, c[1] + dy)
            if n not in prev and ok(*n):
                prev[n] = c
                q.append(n)
    if goal not in prev:
        return None
    path = []
    c = goal
    while c is not None:
        path.append(c)
        c = prev[c]
    return path[::-1]
