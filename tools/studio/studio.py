"""Dernier Studio - see and edit the game without AI.

    python3 tools/studio/studio.py serve            # web studio on http://localhost:8765
    python3 tools/studio/studio.py scenes           # list scenes
    python3 tools/studio/studio.py dialogue [--scene TEXT] [--grep TEXT]
    python3 tools/studio/studio.py set EVENT_ID "New line|second page"
    python3 tools/studio/studio.py export dialogue.tsv
    python3 tools/studio/studio.py import dialogue.tsv
    python3 tools/studio/studio.py check            # layout audit + generator validation

Edits are written straight into the GB Studio project files (project/scenes/...),
exactly as GB Studio itself stores them. Close GB Studio (or reopen the project)
before and after editing here. Dialogue pages use "|" between pages on the
command line and in TSV files; "\\n" is a line break inside a page.
"""

import csv
import json
import os
import re
import subprocess
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[2]
WEB = Path(__file__).resolve().parent / "web"
LINE = 18

SCRIPT_KEYS = {
    "customscript": ["script"],
    "scene": ["script", "playerHit1Script", "playerHit2Script", "playerHit3Script"],
    "actor": ["script", "startScript", "updateScript", "hit1Script", "hit2Script", "hit3Script"],
    "trigger": ["script", "leaveScript"],
}
SCRIPT_LABEL = {"script": "On Interact / Init", "startScript": "On Init", "updateScript": "On Update",
                "hit1Script": "On Hit 1", "hit2Script": "On Hit 2", "hit3Script": "On Hit 3",
                "leaveScript": "On Leave", "playerHit1Script": "Player Hit 1",
                "playerHit2Script": "Player Hit 2", "playerHit3Script": "Player Hit 3"}


# ---------------------------------------------------------------------------
# Project model
# ---------------------------------------------------------------------------

def load_json(p):
    return json.loads(Path(p).read_text())


def walk(script, path=()):
    for i, e in enumerate(script or []):
        yield e, path + (i,)
        for k, kids in (e.get("children") or {}).items():
            yield from walk(kids, path + (i, k))


class Project:
    def __init__(self):
        self.reload()

    def reload(self):
        self.scenes = {}
        for sp in sorted((ROOT / "project" / "scenes").rglob("scene.gbsres")):
            d = load_json(sp)
            d["_dir"] = str(sp.parent.relative_to(ROOT))
            d["_actors"] = []
            d["_triggers"] = []
            for kind in ("actors", "triggers"):
                for p in sorted((sp.parent / kind).glob("*.gbsres")) if (sp.parent / kind).exists() else []:
                    o = load_json(p)
                    o["_file"] = str(p.relative_to(ROOT))
                    d["_" + kind].append(o)
            d["_file"] = str(sp.relative_to(ROOT))
            self.scenes[d["id"]] = d
        self.scripts = []
        for p in sorted((ROOT / "project" / "scripts").rglob("*.gbsres")) if (ROOT / "project" / "scripts").exists() else []:
            d = load_json(p)
            d["_file"] = str(p.relative_to(ROOT))
            self.scripts.append(d)
        self.bgs = {}
        for p in (ROOT / "assets" / "backgrounds").rglob("*.gbsres"):
            d = load_json(p)
            self.bgs[d["id"]] = d
        self.sprites = {}
        for p in (ROOT / "assets" / "sprites").rglob("*.gbsres"):
            d = load_json(p)
            self.sprites[d["id"]] = d
        self.vars = {v["id"]: v["name"] for v in load_json(ROOT / "project" / "variables.gbsres")["variables"]}
        self.palettes = {}
        for p in (ROOT / "project" / "palettes").glob("*.gbsres"):
            d = load_json(p)
            self.palettes[d["id"]] = d
        self.music = {}
        for p in (ROOT / "assets" / "music").glob("*.gbsres"):
            d = load_json(p)
            self.music[d["id"]] = d["name"]

    # ----- helpers
    def preview_for(self, bg_id):
        bg = self.bgs.get(bg_id)
        if not bg:
            return None
        name = Path(bg["filename"]).stem
        folder = Path(bg["filename"]).parent.name
        for cand in (ROOT / "art" / "maps" / "preview" / (name + ".png"),
                     ROOT / "art" / "maps" / "preview" / ("enriched_" + name + ".png")):
            if cand.exists():
                return str(cand.relative_to(ROOT))
        return "assets/backgrounds/" + bg["filename"]

    def owners(self, scene):
        if scene.get("_resourceType") == "script":
            yield "customscript", scene["name"], scene, scene["_file"]
            return
        yield "scene", scene["name"], scene, scene["_file"]
        for a in scene["_actors"]:
            yield "actor", a.get("name") or a["id"][:6], a, a["_file"]
        for t in scene["_triggers"]:
            yield "trigger", t.get("name") or ("trigger %d,%d" % (t["x"], t["y"])), t, t["_file"]

    def lines(self):
        """Every dialogue / choice / menu event in the project."""
        out = []
        for s in list(self.scenes.values()) + self.scripts:
            s.setdefault("id", "")
            for kind, oname, obj, f in self.owners(s):
                for key in SCRIPT_KEYS[kind]:
                    for e, path in walk(obj.get(key, [])):
                        c = e["command"]
                        a = e.get("args", {})
                        if c == "EVENT_TEXT":
                            t = a.get("text", "")
                            pages = t if isinstance(t, list) else [t]
                            out.append({"scene": ("Script: " if kind == "customscript" else "") + s["name"],
                                        "sceneId": s["id"], "owner": oname, "kind": kind,
                                        "script": key, "id": e["id"], "type": "text", "file": f,
                                        "pages": pages, "speaker": speaker(pages)})
                        elif c == "EVENT_CHOICE":
                            out.append({"scene": s["name"], "sceneId": s["id"], "owner": oname, "kind": kind,
                                        "script": key, "id": e["id"], "type": "choice", "file": f,
                                        "pages": [a.get("trueText", ""), a.get("falseText", "")], "speaker": ""})
                        elif c == "EVENT_MENU":
                            n = int(a.get("items", 0))
                            out.append({"scene": s["name"], "sceneId": s["id"], "owner": oname, "kind": kind,
                                        "script": key, "id": e["id"], "type": "menu", "file": f,
                                        "pages": [a.get("option%d" % (i + 1), "") for i in range(n)],
                                        "speaker": ""})
        return out

    def graph(self):
        nodes = []
        edges = []
        for s in self.scenes.values():
            bg = self.bgs.get(s["backgroundId"], {}).get("name", "")
            nodes.append({"id": s["id"], "name": s["name"], "type": s["type"], "x": s.get("x", 0), "bg": bg,
                          "y": s.get("y", 0), "w": s["width"], "h": s["height"],
                          "preview": self.preview_for(s["backgroundId"])})
            for kind, oname, obj, f in self.owners(s):
                for key in SCRIPT_KEYS[kind]:
                    for e, _ in walk(obj.get(key, [])):
                        if e["command"] == "EVENT_SWITCH_SCENE":
                            edges.append({"from": s["id"], "to": e["args"].get("sceneId"), "via": oname})
        return {"nodes": nodes, "edges": edges}

    def find_event(self, event_id):
        for s in list(self.scenes.values()) + self.scripts:
            for kind, oname, obj, f in self.owners(s):
                for key in SCRIPT_KEYS[kind]:
                    for e, _ in walk(obj.get(key, [])):
                        if e.get("id") == event_id:
                            return f, kind, key
        return None, None, None

    def update_event(self, event_id, pages):
        f, kind, key = self.find_event(event_id)
        if not f:
            raise KeyError("event not found: " + event_id)
        data = load_json(ROOT / f)
        for k in SCRIPT_KEYS[kind]:
            for e, _ in walk(data.get(k, [])):
                if e.get("id") == event_id:
                    c = e["command"]
                    if c == "EVENT_TEXT":
                        e["args"]["text"] = pages
                    elif c == "EVENT_CHOICE":
                        e["args"]["trueText"], e["args"]["falseText"] = pages[0], pages[1]
                    elif c == "EVENT_MENU":
                        for i, p in enumerate(pages):
                            e["args"]["option%d" % (i + 1)] = p
                    (ROOT / f).write_text(json.dumps(data, indent=2, ensure_ascii=False))
                    self.reload()
                    return f
        raise KeyError(event_id)


def speaker(pages):
    first = pages[0] if pages else ""
    m = re.match(r"^([A-Za-z .'()]{1,20}):", first.replace("\n", " "))
    return m.group(1) if m else ""


def warn_lines(pages):
    out = []
    for p in pages:
        for line in p.split("\n"):
            shown = re.sub(r"\$(L\d|T\d|V\d|\d+)\$", "00", line)
            if len(shown) > LINE:
                out.append("line over %d chars: %r" % (LINE, line))
        if p.count("\n") > 2:
            out.append("more than 3 lines in one box")
    return out


def wrap_pages(text):
    """Turn free text into GB Studio pages (18 chars, 3 lines)."""
    import textwrap
    lines = []
    for para in text.split("\n"):
        lines += textwrap.wrap(para, LINE) or [""]
    return ["\n".join(lines[i:i + 3]) for i in range(0, len(lines), 3)]


# ---------------------------------------------------------------------------
# Web server
# ---------------------------------------------------------------------------

class Handler(SimpleHTTPRequestHandler):
    project = None

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        p = unquote(u.path)
        P = Handler.project
        if p == "/" or p == "/index.html":
            return self._file(WEB / "index.html")
        if p.startswith("/web/"):
            return self._file(WEB / p[5:])
        if p.startswith("/files/"):
            f = (ROOT / p[7:]).resolve()
            if ROOT in f.parents and f.exists():
                return self._file(f)
            return self._json({"error": "not found"}, 404)
        if p == "/api/project":
            P.reload()
            scenes = [{"id": s["id"], "name": s["name"], "type": s["type"], "w": s["width"], "h": s["height"],
                       "preview": P.preview_for(s["backgroundId"]), "file": s["_file"],
                       "actors": len(s["_actors"]), "triggers": len(s["_triggers"])}
                      for s in P.scenes.values()]
            sprites = [{"id": k, "name": v["name"], "file": "assets/sprites/" + v["filename"],
                        "preview": _sprite_preview(v)} for k, v in P.sprites.items()]
            palettes = [{"id": k, "name": v["name"], "colors": v["colors"]} for k, v in P.palettes.items()]
            return self._json({"scenes": scenes, "sprites": sprites, "vars": P.vars, "palettes": palettes,
                               "music": P.music})
        if p.startswith("/api/scene/"):
            sid = p.split("/")[-1]
            s = P.scenes.get(sid)
            if not s:
                return self._json({"error": "no scene"}, 404)
            out = dict(s)
            out["preview"] = P.preview_for(s["backgroundId"])
            out["sceneNames"] = {k: v["name"] for k, v in P.scenes.items()}
            out["spriteFiles"] = {k: _sprite_preview(v) for k, v in P.sprites.items()}
            out["vars"] = P.vars
            out["music"] = P.music
            return self._json(out)
        if p == "/api/dialogue":
            return self._json(P.lines())
        if p == "/api/graph":
            return self._json(P.graph())
        if p == "/api/world":
            f = ROOT / "art" / "maps" / "world_campus.json"
            return self._json(load_json(f) if f.exists() else {})
        if p == "/api/doc":
            name = parse_qs(u.query).get("name", ["EDITING_GUIDE"])[0]
            f = ROOT / "docs" / (re.sub(r"[^A-Za-z_]", "", name) + ".md")
            return self._json({"text": f.read_text() if f.exists() else "(missing)"})
        if p == "/api/check":
            return self._json({"output": run_check()})
        return self._json({"error": "unknown"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        P = Handler.project
        if self.path == "/api/event":
            try:
                pages = body.get("pages")
                if body.get("autowrap"):
                    pages = wrap_pages("\n".join(pages))
                f = P.update_event(body["id"], pages)
                return self._json({"ok": True, "file": f, "pages": pages, "warnings": warn_lines(pages)})
            except Exception as e:  # noqa: BLE001
                return self._json({"ok": False, "error": str(e)}, 400)
        return self._json({"error": "unknown"}, 404)

    def _file(self, f):
        f = Path(f)
        if not f.exists():
            return self._json({"error": "missing"}, 404)
        data = f.read_bytes()
        ctype = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".png": "image/png",
                 ".json": "application/json", ".md": "text/plain"}.get(f.suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _sprite_preview(v):
    name = Path(v["filename"]).stem
    for cand in (ROOT / "art" / "sprites" / "cast" / "preview" / (name + ".png"),
                 ROOT / "art" / "sprites" / "preview" / (name + "_preview.png")):
        if cand.exists():
            return str(cand.relative_to(ROOT))
    return "assets/sprites/" + v["filename"]


def run_check():
    out = []
    for cmd in ([sys.executable, str(ROOT / "tools" / "game" / "check_maps.py")],
                [sys.executable, str(ROOT / "tools" / "game" / "build_game.py"), "--check"]):
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        out.append("$ " + " ".join(Path(c).name for c in cmd) + "\n" + r.stdout[-6000:] + r.stderr[-2000:])
    return "\n".join(out)


def serve(port=8765, open_browser=True):
    Handler.project = Project()
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = "http://localhost:%d" % port
    print("Dernier Studio running at %s  (Ctrl+C to stop)" % url)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


# ---------------------------------------------------------------------------
# Terminal commands
# ---------------------------------------------------------------------------

def cmd_scenes(P):
    for s in sorted(P.scenes.values(), key=lambda s: s["name"]):
        print("%-48s %-10s %3dx%-3d actors %2d triggers %2d  %s" % (s["name"][:48], s["type"], s["width"],
                                                                    s["height"], len(s["_actors"]),
                                                                    len(s["_triggers"]), s["id"]))


def cmd_dialogue(P, scene=None, grep=None):
    for l in P.lines():
        if scene and scene.lower() not in l["scene"].lower():
            continue
        text = " | ".join(l["pages"]).replace("\n", "\\n")
        if grep and grep.lower() not in text.lower():
            continue
        print("[%s] %s / %s (%s)\n    %s\n    %s" % (l["type"], l["scene"], l["owner"], SCRIPT_LABEL.get(l["script"],
                                                                                              l["script"]),
                                               text, l["id"]))


def cmd_set(P, event_id, text, autowrap=True):
    pages = text.split("|")
    if autowrap and "\\n" not in text:
        pages = [p2 for p in pages for p2 in wrap_pages(p)]
    else:
        pages = [p.replace("\\n", "\n") for p in pages]
    f = P.update_event(event_id, pages)
    print("updated", f)
    for w in warn_lines(pages):
        print("  warning:", w)


def cmd_export(P, path):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["id", "type", "scene", "owner", "text (| between pages, \\n inside a page)"])
        for l in P.lines():
            w.writerow([l["id"], l["type"], l["scene"], l["owner"],
                        " | ".join(p.replace("\n", "\\n") for p in l["pages"])])
    print("wrote", path)


def cmd_import(P, path):
    current = {l["id"]: l for l in P.lines()}
    changed = 0
    with open(path, newline="") as fh:
        r = csv.reader(fh, delimiter="\t")
        next(r, None)
        for row in r:
            if len(row) < 5:
                continue
            eid, text = row[0], row[4]
            pages = [p.strip().replace("\\n", "\n") for p in text.split(" | ")]
            if eid in current and pages != current[eid]["pages"]:
                P.update_event(eid, pages)
                changed += 1
                for wmsg in warn_lines(pages):
                    print("  %s: %s" % (eid[:8], wmsg))
    print("updated %d lines" % changed)


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "serve":
        port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 8765
        serve(port, "--no-browser" not in argv)
        return 0
    P = Project()
    if cmd == "scenes":
        cmd_scenes(P)
    elif cmd == "dialogue":
        scene = argv[argv.index("--scene") + 1] if "--scene" in argv else None
        grep = argv[argv.index("--grep") + 1] if "--grep" in argv else None
        cmd_dialogue(P, scene, grep)
    elif cmd == "set":
        cmd_set(P, argv[1], argv[2], autowrap="--raw" not in argv)
    elif cmd == "export":
        cmd_export(P, argv[1] if len(argv) > 1 else "dialogue.tsv")
    elif cmd == "import":
        cmd_import(P, argv[1] if len(argv) > 1 else "dialogue.tsv")
    elif cmd == "check":
        print(run_check())
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
