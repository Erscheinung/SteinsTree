#!/usr/bin/env python3
"""Apply a small indexed palette and report GB Studio's 8x8 tile budget.

The conversion deliberately uses luminance, rather than a nearest RGB colour,
so colourful source art keeps its light/dark shapes when it is brought into a
four-colour Game Boy palette.  Palette files accepted here are the plain HEX,
GIMP GPL, and JASC PAL files emitted in art/palettes/.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image


HEX_RE = re.compile(r"^(?:#)?([0-9a-fA-F]{6})$")
GB_BACKGROUND_MIN_WIDTH = 160
GB_BACKGROUND_MIN_HEIGHT = 144
GB_BACKGROUND_MAX_AXIS = 2040
GB_BACKGROUND_MAX_AREA = 1_048_320
GB_BACKGROUND_COLORS = {(224, 248, 207), (134, 192, 108), (48, 104, 80), (7, 24, 33)}


def parse_hex(value: str) -> tuple[int, int, int]:
    match = HEX_RE.match(value.strip())
    if not match:
        raise ValueError(f"invalid colour: {value!r}")
    raw = match.group(1)
    return tuple(int(raw[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def read_palette(path: Path) -> list[tuple[int, int, int]]:
    """Read colours from HEX, GPL, or JASC PAL text."""

    colours: list[tuple[int, int, int]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(";"):
            continue
        hex_match = HEX_RE.match(stripped)
        if hex_match:
            colours.append(parse_hex(stripped))
            continue
        parts = stripped.split()
        if len(parts) >= 3 and all(part.isdigit() for part in parts[:3]):
            values = tuple(int(part) for part in parts[:3])
            if all(0 <= value <= 255 for value in values):
                colours.append(values)  # type: ignore[arg-type]
    if not colours:
        raise ValueError(f"no colours found in palette {path}")
    return colours


def luminance(colour: tuple[int, int, int]) -> float:
    red, green, blue = colour
    return 0.299 * red + 0.587 * green + 0.114 * blue


def colour_hex(colour: tuple[int, int, int]) -> str:
    return "#%02X%02X%02X" % colour


def remap_pixels(
    image: Image.Image,
    palette: Sequence[tuple[int, int, int]],
    *,
    mode: str = "luminance",
    source_palette: Sequence[tuple[int, int, int]] | None = None,
) -> tuple[Image.Image, dict[str, int]]:
    """Remap pixels by luminance or by exact source/target palette index."""

    if not palette:
        raise ValueError("target palette is empty")
    if mode not in {"luminance", "index"}:
        raise ValueError(f"unsupported remap mode: {mode}")
    if mode == "index":
        if source_palette is None:
            raise ValueError("index mode requires --source-palette")
        if len(source_palette) != len(palette):
            raise ValueError(
                "index mode requires source and target palettes with the same number of colours"
            )
        if len(set(source_palette)) != len(source_palette):
            raise ValueError("source palette contains duplicate colours; index mapping is ambiguous")

    source = image.convert("RGBA")
    targets = [luminance(colour) for colour in palette]
    index_map = dict(zip(source_palette or (), palette))
    cache: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    unknown: set[tuple[int, int, int]] = set()
    mapped: list[tuple[int, int, int, int]] = []
    transparent = 0
    for red, green, blue, alpha in source.getdata():
        if alpha == 0:
            transparent += 1
            mapped.append((0, 0, 0, 0))
            continue
        source_colour = (red, green, blue)
        target = cache.get(source_colour)
        if target is None:
            if mode == "index":
                target = index_map.get(source_colour)
                if target is None:
                    unknown.add(source_colour)
                    continue
            else:
                target = palette[
                    min(
                        range(len(palette)),
                        key=lambda index: abs(luminance(source_colour) - targets[index]),
                    )
                ]
            cache[source_colour] = target
        mapped.append((*target, alpha))
    if unknown:
        examples = ", ".join(colour_hex(colour) for colour in sorted(unknown)[:8])
        raise ValueError(
            f"index mode found {len(unknown)} source colours outside the source palette "
            f"(examples: {examples})"
        )
    output = Image.new("RGBA", source.size)
    output.putdata(mapped)
    return output, {
        "source_colors": len(cache),
        "transparent_pixels": transparent,
    }


def image_stats(path: Path) -> dict[str, object]:
    image = Image.open(path).convert("RGBA")
    width, height = image.size
    tiles: set[bytes] = set()
    for tile_y in range(height // 8):
        for tile_x in range(width // 8):
            tile = image.crop((tile_x * 8, tile_y * 8, tile_x * 8 + 8, tile_y * 8 + 8))
            tiles.add(tile.tobytes())
    pixels = list(image.getdata())
    colours = image.getcolors(maxcolors=16_777_216)
    rgb_colours = sorted({colour_hex(pixel[:3]) for pixel in pixels})
    return {
        "file": str(path),
        "width": width,
        "height": height,
        "area": width * height,
        "colors": len(colours) if colours is not None else None,
        "rgb_colors": rgb_colours,
        "unique_8x8_tiles": len(tiles),
        "tile_grid": [width // 8, height // 8],
        "partial_edge_pixels": {"right": width % 8, "bottom": height % 8},
        "transparent_pixels": sum(1 for pixel in pixels if pixel[3] == 0),
        "non_opaque_pixels": sum(1 for pixel in pixels if pixel[3] != 255),
    }


def validation_failures(
    report: dict[str, object],
    palette: Sequence[tuple[int, int, int]],
    max_tiles: int,
) -> list[str]:
    """Return actionable failures for a canonical GB Studio background."""

    width = int(report["width"])
    height = int(report["height"])
    area = int(report["area"])
    failures: list[str] = []
    if width < GB_BACKGROUND_MIN_WIDTH or height < GB_BACKGROUND_MIN_HEIGHT:
        failures.append(
            f"dimensions must be at least {GB_BACKGROUND_MIN_WIDTH}x{GB_BACKGROUND_MIN_HEIGHT}; "
            f"got {width}x{height}"
        )
    if width % 8 or height % 8:
        failures.append(f"dimensions must be multiples of 8; got {width}x{height}")
    if width > GB_BACKGROUND_MAX_AXIS or height > GB_BACKGROUND_MAX_AXIS:
        failures.append(
            f"each axis must be at most {GB_BACKGROUND_MAX_AXIS}px; got {width}x{height}"
        )
    if area > GB_BACKGROUND_MAX_AREA:
        failures.append(
            f"area must be at most {GB_BACKGROUND_MAX_AREA} pixels; got {area}"
        )
    if int(report["non_opaque_pixels"]):
        failures.append(
            f"background must be fully opaque; found {report['non_opaque_pixels']} non-opaque pixels"
        )
    if set(palette) != GB_BACKGROUND_COLORS or len(palette) != 4:
        failures.append("validation palette must be the four canonical GB Studio background colours")
    expected = {colour_hex(colour) for colour in GB_BACKGROUND_COLORS}
    actual = set(report["rgb_colors"])
    unexpected = sorted(actual - expected)
    if unexpected:
        failures.append("noncanonical colours: " + ", ".join(unexpected[:8]))
    if int(report["unique_8x8_tiles"]) > max_tiles:
        failures.append(
            f"unique 8x8 tile budget exceeded: {report['unique_8x8_tiles']} > {max_tiles}"
        )
    return failures


def write_json(path: Path | None, payload: object) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path is None:
        print(rendered, end="")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")


def palette_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--palette",
        type=Path,
        required=True,
        help="HEX, GPL, or JASC PAL palette file",
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    remap = commands.add_parser("remap", help="write a luminance-remapped PNG")
    remap.add_argument("--input", type=Path, required=True)
    remap.add_argument("--output", type=Path, required=True)
    palette_argument(remap)
    remap.add_argument(
        "--mode",
        choices=("luminance", "index"),
        default="luminance",
        help="luminance mapping for full-colour art, or exact palette-index mapping",
    )
    remap.add_argument(
        "--source-palette",
        type=Path,
        help="source palette for --mode index; colours map by matching list position",
    )
    remap.add_argument("--stats-json", type=Path)

    stats = commands.add_parser("stats", help="report dimensions and unique 8x8 tiles")
    stats.add_argument("--input", type=Path, action="append", required=True)
    stats.add_argument("--json-out", type=Path)

    validate = commands.add_parser("validate", help="check images against a tile budget")
    validate.add_argument("--input", type=Path, action="append", required=True)
    validate.add_argument("--palette", type=Path, help="optional canonical palette file; never a display palette")
    validate.add_argument("--max-tiles", type=int, default=192)
    validate.add_argument("--json-out", type=Path)

    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "validate" and args.max_tiles < 1:
        parser.error("--max-tiles must be positive")
    if args.command == "remap":
        if args.input.resolve() == args.output.resolve() or (
            args.output.exists() and args.input.samefile(args.output)
        ):
            print("error: input and output must be different paths; refusing to overwrite the source", file=sys.stderr)
            return 2
        try:
            palette = read_palette(args.palette)
            source_palette = read_palette(args.source_palette) if args.source_palette else None
            source = Image.open(args.input)
            output, conversion = remap_pixels(
                source,
                palette,
                mode=args.mode,
                source_palette=source_palette,
            )
        except (OSError, ValueError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
        args.output.parent.mkdir(parents=True, exist_ok=True)
        output.save(args.output, format="PNG", optimize=True)
        report = {"input": str(args.input), "output": str(args.output), **conversion, **image_stats(args.output)}
        write_json(args.stats_json, report)
        return 0

    reports = [image_stats(path) for path in args.input]
    payload: object = {"images": reports}
    if args.command == "validate":
        palette = read_palette(args.palette) if args.palette else sorted(GB_BACKGROUND_COLORS)
        failures = {
            str(report["file"]): validation_failures(report, palette, args.max_tiles)
            for report in reports
        }
        failed_files = [file for file, reasons in failures.items() if reasons]
        payload = {
            "max_unique_8x8_tiles": args.max_tiles,
            "canonical_palette": [colour_hex(colour) for colour in palette],
            "images": reports,
            "failures": failures,
        }
    write_json(args.json_out, payload)
    if args.command == "validate" and failed_files:
        for file in failed_files:
            for reason in failures[file]:
                print(f"{file}: {reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
