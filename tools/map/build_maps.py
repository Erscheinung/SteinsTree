"""Build every campus background: world map, exteriors, interiors.

    python3 tools/map/build_maps.py            # everything
    python3 tools/map/build_maps.py ab1 dome   # just these

Writes assets/backgrounds/muj/*.png (+ .gbsres), art/maps/*.json (meta) and
art/maps/preview/*.png. Refuses to overwrite a runtime PNG that was edited
by hand since it was generated (tracked in art/maps/.generated.json) unless
--force is given.
"""

import json
import sys

import gbc
import interior
import local
import maps_local
import osm
import special
import world

GEN = gbc.ROOT / "art" / "maps" / ".generated.json"


def _guard(name, force):
    rec = json.loads(GEN.read_text()) if GEN.exists() else {}
    png = gbc.ROOT / "assets" / "backgrounds" / "muj" / (name + ".png")
    if png.exists() and name in rec and rec[name] != gbc.checksum(png) and not force:
        print("  SKIP %s: runtime PNG was edited by hand (use --force to regenerate)" % name)
        return False
    return True


def _record(name):
    rec = json.loads(GEN.read_text()) if GEN.exists() else {}
    rec[name] = gbc.checksum(gbc.ROOT / "assets" / "backgrounds" / "muj" / (name + ".png"))
    GEN.write_text(json.dumps(rec, indent=1, sort_keys=True))


def build_interior(spec):
    cv, doors = interior.build(spec)
    def inside(d):
        # step one tile into the room from the door, whichever side is open
        order = ((0, -1), (-1, -1), (1, 0), (-1, 0), (0, 1))
        if d["x"] == 0:
            order = ((1, 0),) + order
        elif d["x"] == cv.wt - 1:
            order = ((-2, 0),) + order
        for dx, dy in order:
            x, y = d["x"] + dx, d["y"] + dy
            if 0 <= x < cv.wt - 1 and 0 <= y < cv.ht and not cv.solid[y][x] and not cv.solid[y][x + 1]:
                return [x, y]
        return [d["x"], d["y"]]
    meta = local.finish(cv, dict(spec, exits=[], spawn=inside(doors[0]) if doors else None),
                        [{"label": "Exit", "target": None, "x": d["x"], "y": d["y"], "spawn": inside(d)}
                         for d in doors])
    meta["kind"] = "interior"
    if getattr(cv, "owner_source_patches", None):
        meta["source_patches"] = cv.owner_source_patches
    return cv, meta


def main(argv):
    force = "--force" in argv
    names = [a for a in argv if not a.startswith("--")]
    feats = osm.load_features()
    report = []
    if not names or "world_campus" in names:
        if _guard("world_campus", force):
            cv, meta = world.build(feats)
            meta["unique_before_reduce"] = cv.unique_tiles()
            meta["tiles_merged"] = cv.reduce_tiles(world.TILE_BUDGET)
            meta["unique_tiles"] = cv.unique_tiles()
            gbc.write_background(cv, "world_campus")
            (gbc.ROOT / "art" / "maps" / "world_campus.json").write_text(json.dumps(meta, indent=1))
            _record("world_campus")
            report.append(meta)
    for spec in maps_local.EXTERIORS:
        if names and spec["name"] not in names:
            continue
        if not _guard(spec["name"], force):
            continue
        cv, meta = local.build(spec, feats)
        meta["kind"] = "exterior"
        local.save(cv, meta)
        _record(spec["name"])
        report.append(meta)
    for spec in maps_local.INTERIORS:
        if names and spec["name"] not in names:
            continue
        if not _guard(spec["name"], force):
            continue
        cv, meta = build_interior(spec)
        local.save(cv, meta)
        _record(spec["name"])
        report.append(meta)
    for name, fn in special.SPECIALS.items():
        if names and name not in names:
            continue
        if not _guard(name, force):
            continue
        cv, extra = fn()
        meta = local.finish(cv, {"name": name, "exits": [], "spawn": [1, 1]}, [])
        meta.update(extra)
        meta.pop("unreachable_doors", None)
        local.save(cv, meta)
        _record(name)
        report.append(meta)
    for m in report:
        flags = []
        if m.get("tiles_merged"):
            flags.append("merged %d" % m["tiles_merged"])
        if m.get("palette_conflicts"):
            flags.append("conflicts %d" % m["palette_conflicts"])
        if m.get("unreachable_doors"):
            flags.append("UNREACHABLE %s" % m["unreachable_doors"])
        missing = [d["label"] for d in m.get("doors", []) if d.get("missing")]
        if missing:
            flags.append("MISSING DOORS %s" % missing)
        print("%-18s %3dx%-3d tiles %3d  %s" % (m["name"], m["cols"], m["rows"], m["unique_tiles"], " ".join(flags)))


if __name__ == "__main__":
    main(sys.argv[1:])
    if len([a for a in sys.argv[1:] if not a.startswith("--")]) == 0:
        import tilesheet
        tilesheet.main()
