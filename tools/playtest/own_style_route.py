"""Play the owner-style opening route in a built Dernier ROM.

The route is deliberately data driven.  Scene folders are allowed to move as
the map generator evolves; the router resolves scene symbols/names and walks
the switch-scene triggers found in the project at runtime.  This keeps the
playtest useful while the story and map workers are replacing draft-1 scene
ids.

Normal run (writes ``art/maps/preview/ingame`` by default)::

    python3 tools/playtest/own_style_route.py game.gb dernier.sym out/ \
        --coverage

``--coverage`` starts a fresh New Game for each requested map and is explicitly
labelled ``warp`` in the screenshot names and manifest.  The opening route is
labelled ``continuous`` and always starts at the title screen.

``--check`` only loads project data and verifies that the route's scene aliases,
collision grids, and trigger graph are structurally usable.  It does not need a
ROM or PyBoy, which makes it suitable for running before the final ROM exists.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


HERE = Path(__file__).resolve().parent
# ``.../<worktree>/tools/playtest`` -> worktree.
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))


# These are the map keys in tools/map/maps_local.py.  A few aliases are kept
# here because the owner-style generator may name a scene after its title.
NEW_MAPS = (
    "ab1",
    "ab2",
    "ab3",
    "quess_mess_in",
    "workshop",
    "cricket_ground",
    "dome",
    "underpass",
    "scrub_trail",
    "nbc",
    # The interiors are part of the same map pass and are useful evidence that
    # a door really lands in the intended compact scene.
    "physics_class",
    "maths_class",
    "chem_lab",
    "workshop_in",
    "dome_in",
)

MAP_ALIASES = {
    "ab1": ("ab1", "academic block 1", "block 1 academic", "ab1 exterior"),
    "ab2": ("ab2", "academic block 2", "ab2 amphitheatre", "ab2 & amphitheatre"),
    "ab3": ("ab3", "academic block 3", "ab3 labs", "ab3 & labs"),
    "quess_mess_in": ("quess_mess_in", "quess mess", "quess mess interior", "quess mess in"),
    "workshop": ("workshop", "workshop exterior"),
    "cricket_ground": ("cricket_ground", "cricket ground", "cricket"),
    "dome": ("dome", "the dome", "admin block", "administrative block"),
    "underpass": ("underpass", "the underpass", "hostel gate underpass"),
    "scrub_trail": ("scrub_trail", "scrub trail", "scrub forest", "forest behind b7"),
    "nbc": ("nbc", "nbc & baba", "nbc food court", "food court", "baba"),
    "physics_class": ("physics_class", "physics", "ab1 classroom", "ab1-101"),
    "maths_class": ("maths_class", "maths", "mathematics", "ab2 room 214"),
    "chem_lab": ("chem_lab", "chemistry", "chemistry lab", "ab3 lab"),
    "workshop_in": ("workshop_in", "workshop floor", "workshop interior"),
    "dome_in": ("dome_in", "dome rotunda", "dome interior", "library"),
}

HANDHELD_RE = re.compile(r"handheld|pocket|game\s*boy|gameboy|pocketboy|device", re.I)
HANGOUT_RE = re.compile(r"hangout|hang\s*out", re.I)
SLEEP_RE = re.compile(r"sleep|bed|lights?\s*off", re.I)


def norm(value: object) -> str:
    """Normalize a human-facing scene name for alias lookup."""

    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def flatten_events(events: Iterable[dict]) -> Iterable[dict]:
    """Yield events in a script, including all GB Studio child branches."""

    for event in events or ():
        yield event
        for children in (event.get("children") or {}).values():
            yield from flatten_events(children)


def event_value(value: object, default: object = None) -> object:
    if isinstance(value, dict):
        return value.get("value", default)
    return value if value is not None else default


@dataclass(frozen=True)
class Edge:
    source: "Scene"
    target: "Scene"
    trigger: dict
    arrival: Optional[tuple[int, int]]


class Scene:
    def __init__(self, path: Path, data: dict, actors: list[dict], triggers: list[dict]):
        self.path = path
        self.data = data
        self.actors = actors
        self.triggers = triggers
        self.key = path.parent.name
        self.id = data.get("id", "")
        self.aliases = {
            norm(self.key),
            norm(data.get("name")),
            norm(data.get("symbol")),
        }

    @property
    def width(self) -> int:
        return int(self.data.get("width", 0))

    @property
    def height(self) -> int:
        return int(self.data.get("height", 0))

    def player_script_positions(self) -> set[tuple[int, int]]:
        """Return authored player positions used by the scene startup script."""

        positions = set()
        for event in flatten_events(self.data.get("script", [])):
            if event.get("command") not in {"EVENT_ACTOR_SET_POSITION", "EVENT_ACTOR_MOVE_TO"}:
                continue
            args = event.get("args") or {}
            if args.get("actorId") != "player":
                continue
            x, y = event_value(args.get("x")), event_value(args.get("y"))
            if x is not None and y is not None:
                positions.add((int(x), int(y)))
        return positions


class SceneIndex:
    """Project-side scene and trigger index used by both route modes."""

    def __init__(self, project: Path):
        self.project = project
        scenes_root = project / "project" / "scenes"
        if not scenes_root.is_dir():
            raise FileNotFoundError(f"missing project scenes directory: {scenes_root}")
        self.scenes: list[Scene] = []
        self.by_id: dict[str, Scene] = {}
        self.by_alias: dict[str, Scene] = {}
        for scene_file in sorted(scenes_root.rglob("scene.gbsres")):
            data = json.loads(scene_file.read_text())
            folder = scene_file.parent
            actors = [json.loads(p.read_text()) for p in sorted((folder / "actors").glob("*.gbsres"))]
            triggers = [json.loads(p.read_text()) for p in sorted((folder / "triggers").glob("*.gbsres"))]
            scene = Scene(scene_file, data, actors, triggers)
            scene.aliases.add(norm(folder.relative_to(scenes_root)))
            self.scenes.append(scene)
            if scene.id:
                self.by_id[scene.id] = scene
            for alias in scene.aliases:
                if alias and alias not in self.by_alias:
                    self.by_alias[alias] = scene
        self.edges = self._build_edges()
        self.outgoing: dict[Scene, list[Edge]] = {}
        for edge in self.edges:
            self.outgoing.setdefault(edge.source, []).append(edge)

    def resolve(self, value: str | Scene) -> Scene:
        if isinstance(value, Scene):
            return value
        want = norm(value)
        aliases = [want]
        for alias in MAP_ALIASES.get(value, ()):
            aliases.append(norm(alias))
        for alias in aliases:
            scene = self.by_alias.get(alias)
            if scene:
                return scene
        # Symbols may carry the map name as a suffix after a generated prefix.
        matches = [s for s in self.scenes if any(want and want in a for a in s.aliases)]
        if len(matches) == 1:
            return matches[0]
        available = ", ".join(sorted(s.key for s in self.scenes))
        raise KeyError(f"scene {value!r} not found (available: {available})")

    @staticmethod
    def _switches(script: Iterable[dict]) -> Iterable[dict]:
        return (e for e in flatten_events(script) if e.get("command") == "EVENT_SWITCH_SCENE")

    def _build_edges(self) -> list[Edge]:
        edges: list[Edge] = []
        for source in self.scenes:
            for trigger in source.triggers:
                for event in self._switches(trigger.get("script", [])):
                    args = event.get("args") or {}
                    target = self.by_id.get(str(event_value(args.get("sceneId"), "")))
                    if target is None or target is source:
                        continue
                    x = event_value(args.get("x"))
                    y = event_value(args.get("y"))
                    arrival = (int(x), int(y)) if x is not None and y is not None else None
                    edges.append(Edge(source, target, trigger, arrival))
        return edges

    def find_actor(self, scene: Scene, pattern: re.Pattern[str]) -> Optional[dict]:
        return next((a for a in scene.actors if pattern.search(str(a.get("name", "")))), None)

    def find_trigger(self, scene: Scene, pattern: re.Pattern[str]) -> Optional[dict]:
        return next((t for t in scene.triggers if pattern.search(str(t.get("name", "")))), None)

    def plan(self, start: str | Scene, target: str | Scene) -> list[Edge]:
        source, goal = self.resolve(start), self.resolve(target)
        previous: dict[Scene, tuple[Optional[Scene], Optional[Edge]]] = {source: (None, None)}
        queue = deque([source])
        while queue:
            current = queue.popleft()
            if current is goal:
                break
            for edge in self.outgoing.get(current, ()):
                if edge.target not in previous:
                    previous[edge.target] = (current, edge)
                    queue.append(edge.target)
        if goal not in previous:
            raise RuntimeError(f"no trigger path from {source.key!r} to {goal.key!r}")
        route: list[Edge] = []
        cur = goal
        while previous[cur][1] is not None:
            parent, edge = previous[cur]
            assert parent is not None and edge is not None
            route.append(edge)
            cur = parent
        return list(reversed(route))

    def grid(self, scene: Scene) -> tuple[list[list[bool]], int, int]:
        # Keep this import local: --check should still work when PyBoy is not
        # installed, while the collision codec is part of the map tools.
        sys.path.insert(0, str(self.project / "tools" / "map"))
        import gbc  # type: ignore

        collisions = scene.data.get("collisions")
        cells = gbc.decompress8(collisions) if collisions else [0] * (scene.width * scene.height)
        if len(cells) != scene.width * scene.height:
            raise ValueError(f"{scene.key}: collision grid has {len(cells)} cells, expected {scene.width * scene.height}")
        return [[cells[y * scene.width + x] == 0 for x in range(scene.width)] for y in range(scene.height)], scene.width, scene.height


def bfs(grid: list[list[bool]], width: int, height: int, start: tuple[int, int], goals: set[tuple[int, int]],
        blocked: Optional[set[tuple[int, int]]] = None) -> Optional[list[tuple[int, int]]]:
    """BFS for GB Studio's two-tile-wide player footprint."""

    blocked = blocked or set()

    def okay(x: int, y: int) -> bool:
        return 0 <= x and x + 1 < width and 0 <= y < height and grid[y][x] and grid[y][x + 1] and \
            (x, y) not in blocked and (x + 1, y) not in blocked

    if not okay(*start):
        # A transition can leave the player on the first row; search for the
        # nearest open player tile instead of failing before the first edge.
        candidates = [(x, y) for y in range(height) for x in range(max(0, width - 1)) if okay(x, y)]
        start = min(candidates, key=lambda p: abs(p[0] - start[0]) + abs(p[1] - start[1])) if candidates else start
    if not okay(*start):
        return None
    previous: dict[tuple[int, int], Optional[tuple[int, int]]] = {start: None}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        if current in goals:
            path = []
            while current is not None:
                path.append(current)
                current = previous[current]
            return list(reversed(path))
        x, y = current
        for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if nxt not in previous and okay(*nxt):
                previous[nxt] = current
                queue.append(nxt)
    return None


def trigger_goals(scene: Scene, trigger: dict, grid: list[list[bool]], width: int, height: int) -> set[tuple[int, int]]:
    """Return walkable cells that activate a trigger or its doorstep."""

    x, y = int(trigger.get("x", 0)), int(trigger.get("y", 0))
    tw, th = int(trigger.get("width", 1)), int(trigger.get("height", 1))
    inside = {(xx, yy) for yy in range(y, min(height, y + th)) for xx in range(x, min(width - 1, x + tw))
              if grid[yy][xx] and grid[yy][xx + 1]}
    # GB Studio fires a trigger when the player's feet enter its cell.  Some
    # hand-authored doors have a solid trigger cell, so retain the adjacent
    # doorstep fallback only when no inside cell can be occupied.
    if inside:
        return inside
    cells = {(x - 1, y), (x + tw, y), (x, y - 1), (x, y + th)}
    return {(xx, yy) for xx, yy in cells if 0 <= xx < width - 1 and 0 <= yy < height and grid[yy][xx] and grid[yy][xx + 1]}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def var_value(game, *names: str, default: Optional[int] = None) -> Optional[int]:
    for name in names:
        if name in game.vid:
            return game.var(name)
    return default


def wait_dialogue(game, frames: int = 180, presses: int = 24) -> None:
    """Drain a blocking GB Studio text box without moving the player."""

    for _ in range(presses):
        game.wait(frames // 6)
        if not game.dialog_open():
            return
        game.press("a", 4, 10)


def wait_for(game, predicate, frames: int, mash: Optional[str] = None) -> bool:
    elapsed = 0
    while elapsed < frames:
        if predicate():
            return True
        if game.dialog_open():
            game.press("a", 4, 10)
            elapsed += 14
        elif mash:
            game.press(mash, 4, 12)
            elapsed += 16
        else:
            game.wait(10)
            elapsed += 10
    return bool(predicate())


class Recorder:
    """Screenshot and assertion log shared by continuous and warp runs."""

    def __init__(self, game, outdir: Path, kind: str, manifest: list[dict]):
        self.game = game
        self.outdir = outdir
        self.kind = kind
        self.manifest = manifest
        self.seen_maps: set[str] = set()

    def shot(self, label: str, scene: Optional[Scene] = None, map_name: Optional[str] = None) -> Path:
        path = self.game.shot(f"{self.kind}_{label}")
        entry = {
            "kind": self.kind,
            "label": label,
            "path": str(path),
            "scene": scene.key if scene else None,
            "map": map_name,
            "tile": list(self.game.player_tile()),
            "variables": {k: self.game.var(k) for k in ("Chapter", "Phase", "Objective", "PrologueBattle", "MemCount") if k in self.game.vid},
        }
        self.manifest.append(entry)
        return path

    def map_shot(self, scene: Scene, canonical: Optional[str] = None) -> Optional[Path]:
        key = canonical or next((name for name in NEW_MAPS if self._is_map_scene(scene, name)), None)
        if key is None or key in self.seen_maps:
            return None
        self.seen_maps.add(key)
        return self.shot(key, scene, key)

    @staticmethod
    def _is_map_scene(scene: Scene, name: str) -> bool:
        aliases = {norm(name), *(norm(a) for a in MAP_ALIASES.get(name, ()))}
        return bool(aliases & scene.aliases)


class Router:
    def __init__(self, index: SceneIndex, game, recorder: Recorder):
        self.index, self.game, self.recorder = index, game, recorder

    def _path_for_edge(self, edge: Edge, start: tuple[int, int]) -> Optional[list[tuple[int, int]]]:
        """Find a trigger-safe path for an edge from a concrete player tile."""

        source = edge.source
        grid, width, height = self.index.grid(source)
        goals = trigger_goals(source, edge.trigger, grid, width, height)
        blocked = set()
        for actor in source.actors:
            if HANDHELD_RE.search(str(actor.get("name", ""))):
                ax, ay = int(actor.get("x", 0)), int(actor.get("y", 0))
                blocked.update({(ax, ay), (ax + 1, ay)})
        # Do not route through another switch trigger on the way to the
        # selected edge.  The static graph may contain several exits whose
        # walkable approaches overlap, and the first one reached wins at
        # runtime (sending the player to a different scene).
        for other in source.triggers:
            if other is edge.trigger or not any(self.index._switches(other.get("script", []))):
                continue
            # Multiple graph edges can represent branches of one authored
            # trigger (the destination is selected by story variables).  They
            # share the same rectangle and must remain reachable together.
            if all(other.get(key, 0) == edge.trigger.get(key, 0) for key in ("x", "y", "width", "height")):
                continue
            # Adjacent door triggers can be separate rectangles with the same
            # destination.  Their fallback doorstep cells overlap, so keep
            # both alternatives available to the planner.
            edge_targets = {
                str(event_value((event.get("args") or {}).get("sceneId"), ""))
                for event in self.index._switches(edge.trigger.get("script", []))
            }
            other_targets = {
                str(event_value((event.get("args") or {}).get("sceneId"), ""))
                for event in self.index._switches(other.get("script", []))
            }
            if edge_targets & other_targets:
                continue
            blocked.update(trigger_goals(source, other, grid, width, height))
        return bfs(grid, width, height, start, goals, blocked=blocked)

    def _runtime_plan(self, start: Scene, target: Scene) -> list[Edge]:
        """Plan over scene edges whose trigger is reachable from the current tile.

        A scene can contain overlapping exits.  A scene-only BFS may choose a
        direct edge whose shortest geometric approach crosses another exit,
        while the running game follows the first trigger encountered.  Carrying
        the expected arrival tile through the search lets the router discover
        small, authored detours around those overlaps.
        """

        initial = self.game.player_tile()
        queue = deque([(start, initial)])
        previous: dict[tuple[Scene, tuple[int, int]], tuple[Optional[tuple[Scene, tuple[int, int]]], Optional[Edge]]] = {
            (start, initial): (None, None)
        }
        goal_state: Optional[tuple[Scene, tuple[int, int]]] = None
        while queue:
            scene, position = queue.popleft()
            state = (scene, position)
            if scene is target:
                goal_state = state
                break
            for edge in self.index.outgoing.get(scene, ()):
                if self._path_for_edge(edge, position) is None:
                    continue
                arrival = edge.arrival or position
                next_state = (edge.target, arrival)
                if next_state in previous:
                    continue
                previous[next_state] = (state, edge)
                queue.append(next_state)
        if goal_state is None:
            raise RuntimeError(f"no trigger-safe path from {start.key!r} to {target.key!r}")
        route: list[Edge] = []
        current = goal_state
        while previous[current][1] is not None:
            parent, edge = previous[current]
            assert parent is not None and edge is not None
            route.append(edge)
            current = parent
        return list(reversed(route))

    def _walk_to_edge(self, edge: Edge) -> None:
        source = edge.source
        start = self.game.player_tile()
        path = self._path_for_edge(edge, start)
        require(path is not None, f"no walkable path to {source.key}:{edge.trigger.get('name', '')!r} from {start}")
        # A scene can open an automatic text trigger exactly when the player
        # first tries to leave a spawn tile.  Keep the same step pending until
        # that text is drained, then retry it; treating the unchanged tile as
        # a transition would produce a misleading arrival failure.
        step_index = 0
        while step_index < len(path) - 1:
            current, nxt = path[step_index], path[step_index + 1]
            px, py = self.game.player_tile()
            if (px, py) != current:
                if self.game.dialog_open():
                    wait_dialogue(self.game)
                    continue
                # A previous press may have activated a scene transition.
                break
            direction = "right" if nxt[0] > px else "left" if nxt[0] < px else "down" if nxt[1] > py else "up"
            moved = self.game.step(direction)
            actual = self.game.player_tile()
            if actual == nxt:
                step_index += 1
                continue
            if self.game.dialog_open():
                wait_dialogue(self.game)
                continue
            # A previous press may have activated a scene transition.
            break
        self.game.wait(50)
        # Text/choice triggers can open a few frames after the player enters
        # their cell.  Keep activating the edge for a short grace period so a
        # delayed choice (for example, a campus-map "Enter" prompt) is not
        # mistaken for a failed scene transition.  A presses are harmless
        # while the trigger is still settling.
        if edge.arrival is not None:
            for _ in range(40):
                actual = self.game.player_tile()
                if abs(actual[0] - edge.arrival[0]) <= 1 and abs(actual[1] - edge.arrival[1]) <= 1:
                    break
                self.game.press("a", 4, 12)
        wait_dialogue(self.game)
        if edge.arrival is not None:
            actual = self.game.player_tile()
            # A scene transition may still be fading.  Give it a short grace
            # period; strict equality catches wrong doors while ±1 handles the
            # two-tile player footprint used by some hand-authored maps.
            if actual != edge.arrival:
                self.game.wait(70)
                actual = self.game.player_tile()
            accepted = {edge.arrival, *edge.target.player_script_positions()}
            require(any(abs(actual[0] - x) <= 1 and abs(actual[1] - y) <= 1 for x, y in accepted),
                    f"{source.key}->{edge.target.key} arrived at {actual}, expected {edge.arrival}")
        self.recorder.map_shot(edge.target)

    def route(self, start: str | Scene, target: str | Scene) -> list[Edge]:
        edges = self._runtime_plan(self.index.resolve(start), self.index.resolve(target))
        for edge in edges:
            self._walk_to_edge(edge)
        return edges


def new_game(game_cls, rom: Path, sym: Path, outdir: Path):
    return game_cls(rom, sym, outdir)


def boot_new_game(game) -> None:
    game.wait(700)
    game.press("start")
    game.wait(90)
    game.press("a")
    game.wait(220)
    wait_dialogue(game, frames=240, presses=40)


def path_to_interaction(index: SceneIndex, game, scene: Scene, x: int, y: int) -> tuple[list[tuple[int, int]], str]:
    grid, width, height = index.grid(scene)
    options = ((x, y + 2, "up"), (x, y - 1, "down"), (x - 2, y, "right"), (x + 2, y, "left"))
    candidates = {(xx, yy) for xx, yy, _ in options if 0 <= xx < width - 1 and 0 <= yy < height and grid[yy][xx] and grid[yy][xx + 1]}
    path = bfs(grid, width, height, game.player_tile(), candidates)
    require(path is not None, f"no path to interaction at {scene.key}:{x},{y}")
    destination = path[-1]
    direction = next(d for xx, yy, d in options if (xx, yy) == destination)
    return path, direction


def interact_handheld(index: SceneIndex, game, scene: Scene) -> None:
    actor = index.find_actor(scene, HANDHELD_RE)
    trigger = index.find_trigger(scene, HANDHELD_RE)
    if actor is not None:
        x, y = int(actor.get("x", 23)), int(actor.get("y", 20))
    elif trigger is not None:
        x, y = int(trigger.get("x", 23)), int(trigger.get("y", 20))
    else:
        # Owner's room contract: the player starts at (22,20), and the
        # handheld is immediately adjacent.  This fallback keeps the route
        # useful during the brief interval before the actor sidecar is added.
        x, y = 23, 20
    path, direction = path_to_interaction(index, game, scene, x, y)
    require(game.walk_path(path), f"could not reach handheld at {scene.key}:{x},{y}")
    game.press(direction, 1, 12)
    game.press("a", 4, 30)


def assert_start(game) -> None:
    require(game.player_tile() == (22, 20), f"New Game did not start Outside at (22,20): {game.player_tile()}")
    require(var_value(game, "Chapter") == 0, f"New Game Chapter reset failed: {var_value(game, 'Chapter')}")
    require(var_value(game, "Phase") == 0, f"New Game Phase reset failed: {var_value(game, 'Phase')}")


def run_continuous(index: SceneIndex, game_cls, rom: Path, sym: Path, outdir: Path, manifest: list[dict]) -> None:
    game = new_game(game_cls, rom, sym, outdir)
    recorder = Recorder(game, outdir, "continuous", manifest)
    try:
        boot_new_game(game)
        outside = index.resolve("outside")
        assert_start(game)
        recorder.shot("outside_start", outside, "outside")

        interact_handheld(index, game, outside)
        recorder.shot("handheld_interaction", outside, "outside")
        require(wait_for(game, lambda: var_value(game, "PrologueBattle") == 0 and var_value(game, "EnHP", default=0) > 0,
                         900, mash="a"), "handheld interaction did not start the pocket battle")
        recorder.shot("pocket_battle", index.resolve("battle_pocket") if _can_resolve(index, "battle_pocket") else None)

        require(wait_for(game, lambda: var_value(game, "PrologueBattle") == 1, 7200, mash="a"),
                "pocket battle did not complete")
        wait_dialogue(game, frames=300, presses=50)
        recorder.shot("outside_after_battle", outside, "outside")
        require(var_value(game, "PrologueBattle") == 1, "battle completion flag was lost on return to Outside")

        require(wait_for(game, lambda: var_value(game, "Chapter") == 1 and var_value(game, "Phase") == 0,
                         2400), "return from battle did not reach Day 1 morning")
        wait_dialogue(game, frames=360, presses=60)
        recorder.shot("day1_morning", outside, "outside")
        require(var_value(game, "Objective") in (1, None), f"Day 1 objective is not physics: {var_value(game, 'Objective')}")

        router = Router(index, game, recorder)
        physics = index.resolve("physics_class")
        router.route(outside, physics)
        recorder.shot("physics_arrival", physics, "physics_class")
        require(wait_for(game, lambda: (var_value(game, "Phase") or 0) >= 1, 4800, mash="a"),
                "physics scene did not finish and advance Phase")
        recorder.shot("physics_complete", physics, "physics_class")

        dinner = index.resolve("quess_mess_in")
        router.route(physics, dinner)
        recorder.shot("dinner_arrival", dinner, "quess_mess_in")
        require(wait_for(game, lambda: (var_value(game, "Phase") or 0) >= 2, 4800, mash="a"),
                "dinner scene did not finish and advance Phase")
        recorder.shot("dinner_complete", dinner, "quess_mess_in")

        # The authored Day 1 flow may offer an evening hangout before sleep.
        # If it does, leave the dinner scene and let the first available
        # hangout complete normally.  A rebuilt story that goes straight to
        # sleep simply skips this branch.
        if (var_value(game, "Chapter") or 0) < 2 and (var_value(game, "Phase") or 0) < 3:
            _finish_evening_or_report(index, game, recorder)
        if (var_value(game, "Chapter") or 0) < 2 and (var_value(game, "Phase") or 0) < 3:
            # The owner-style route's acceptance point is the sleep transition;
            # avoid silently changing variables if a worker has not wired it.
            raise AssertionError(f"dinner completed but sleep was not reachable (Phase={var_value(game, 'Phase')})")

        room = index.resolve("outside")
        wait_for(game, lambda: var_value(game, "Chapter") == 2 and var_value(game, "Phase") == 0, 3600, mash="a")
        recorder.shot("day1_sleep_complete", room, "outside")
        require(var_value(game, "Chapter") == 2 and var_value(game, "Phase") == 0,
                f"sleep did not advance to Day 2: Chapter={var_value(game, 'Chapter')} Phase={var_value(game, 'Phase')}")
        print("continuous route: PASS", flush=True)
    finally:
        game.stop()


def _finish_evening_or_report(index: SceneIndex, game, recorder: Recorder) -> None:
    """Complete the authored evening branch when Day 1 still has one."""

    # A direct sleep implementation usually returns to Outside immediately.
    # The current authored Day 1 flow offers a social-link actor first, so
    # choose the first generated hangout actor and play it normally.  Looking
    # up the actor from project data means this survives map layout changes.
    current = index.resolve("quess_mess_in")
    hangout = next(((scene, actor) for scene in index.scenes for actor in scene.actors if HANGOUT_RE.search(str(actor.get("name", "")))), None)
    if hangout is not None:
        target_scene, actor = hangout
        Router(index, game, recorder).route(current, target_scene)
        x, y = int(actor.get("x", 1)), int(actor.get("y", 1))
        path, direction = path_to_interaction(index, game, target_scene, x, y)
        require(game.walk_path(path), f"could not reach evening hangout at {target_scene.key}:{x},{y}")
        game.press(direction, 1, 12)
        game.press("a", 4, 30)
        wait_dialogue(game, frames=900, presses=80)
        recorder.shot("evening_hangout", target_scene, target_scene.key)
        require(wait_for(game, lambda: (var_value(game, "Phase") or 0) >= 3 or (var_value(game, "Chapter") or 0) >= 2,
                         2400, mash="a"),
                "evening hangout did not return the player to the sleep phase")
        return

    # If the owner-style story has no hangout actor, follow the map back to
    # Outside and interact with a named sleep/bed actor if one exists.
    try:
        route = index.plan(current, "outside")
    except RuntimeError:
        return
    router = Router(index, game, recorder)
    router.route(current, "outside")
    outside = index.resolve("outside")
    actor = index.find_actor(outside, SLEEP_RE)
    trigger = index.find_trigger(outside, SLEEP_RE)
    if actor is None and trigger is None:
        # Existing owner's room script starts on room entry once Phase==3; if
        # the worker changed dinner to set Phase=3 this is the intended path.
        wait_dialogue(game, frames=240, presses=32)
        return
    target = actor or trigger
    x, y = int(target.get("x", 22)), int(target.get("y", 20))
    path, direction = path_to_interaction(index, game, outside, x, y)
    require(game.walk_path(path), f"could not reach sleep interaction at Outside:{x},{y}")
    game.press(direction, 1, 12)
    game.press("a", 4, 30)
    wait_dialogue(game, frames=360, presses=48)


def _can_resolve(index: SceneIndex, value: str) -> bool:
    try:
        index.resolve(value)
        return True
    except KeyError:
        return False


def run_coverage(index: SceneIndex, game_cls, rom: Path, sym: Path, outdir: Path, manifest: list[dict], names: list[str]) -> None:
    for canonical in names:
        target = index.resolve(canonical)
        game = new_game(game_cls, rom, sym, outdir)
        recorder = Recorder(game, outdir, "warp", manifest)
        try:
            boot_new_game(game)
            start = index.resolve("outside")
            # Coverage is deliberately separate from the real route.  It only
            # verifies that an owner-style scene can be reached and rendered;
            # story variables are left at their normal New Game values.
            Router(index, game, recorder).route(start, target)
            recorder.shot(canonical, target, canonical)
            print(f"coverage {canonical}: PASS", flush=True)
        finally:
            game.stop()


def check_project(index: SceneIndex, names: list[str]) -> None:
    require(_can_resolve(index, "outside"), "missing original Outside scene")
    for canonical in names:
        scene = index.resolve(canonical)
        grid, width, height = index.grid(scene)
        require(width > 0 and height > 0 and grid, f"{canonical}: empty collision grid")
        require(any(index.outgoing.get(scene, ())), f"{canonical}: no switch-scene trigger edges") if canonical not in {"physics_class", "maths_class", "chem_lab", "workshop_in", "dome_in"} else None
    index.resolve("outside")
    print(f"project check: {len(index.scenes)} scenes, {len(index.edges)} trigger edges, aliases OK", flush=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path)
    parser.add_argument("sym", nargs="?", type=Path)
    parser.add_argument("outdir_pos", nargs="?", type=Path)
    parser.add_argument("--outdir", dest="outdir_opt", type=Path,
                        help="screenshot directory (also accepted as the third positional argument)")
    parser.add_argument("--project", type=Path, default=ROOT)
    parser.add_argument("--coverage", action="store_true", help="capture every owner-style map using fresh dev coverage runs")
    parser.add_argument("--maps", nargs="*", default=list(NEW_MAPS), help="canonical map keys for --coverage")
    parser.add_argument("--check", action="store_true", help="validate project scenes and trigger graph without a ROM")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    project = args.project.resolve()
    index = SceneIndex(project)
    names = list(args.maps)
    if args.check:
        check_project(index, names)
        return 0
    if not args.rom or not args.sym:
        raise SystemExit("ROM and .sym are required unless --check is used")
    output_arg = args.outdir_opt or args.outdir_pos
    if output_arg is None:
        outdir = project / "art" / "maps" / "preview" / "ingame"
    else:
        outdir = output_arg if output_arg.is_absolute() else project / output_arg
    outdir.mkdir(parents=True, exist_ok=True)
    # Importing PyBoy only for a real run keeps --check useful in a plain
    # project checkout.
    from harness import Game

    manifest: list[dict] = []
    run_continuous(index, Game, args.rom.resolve(), args.sym.resolve(), outdir, manifest)
    if args.coverage:
        run_coverage(index, Game, args.rom.resolve(), args.sym.resolve(), outdir, manifest, names)
    manifest_path = outdir / "own_style_route_manifest.json"
    manifest_path.write_text(json.dumps({"project": str(project), "screenshots": manifest}, indent=2) + "\n")
    print(f"wrote {len(manifest)} screenshot records to {manifest_path}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, RuntimeError, ValueError, FileNotFoundError) as exc:
        print(f"own-style route: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
