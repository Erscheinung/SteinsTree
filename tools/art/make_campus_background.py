#!/usr/bin/env python3
"""Reproduce an original 160x144 courtyard study and its reusable 8px atlas.

This is a fictional campus exercise, not a reconstruction of MUJ. Pillow is
used only for integer-coordinate, unsmoothed pixel primitives. No legacy pixels.
"""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw

COLORS = ('#E8DFC8', '#9BA58D', '#596579', '#242337')


def tree():
    im = Image.new('RGBA', (24, 32))
    d = ImageDraw.Draw(im)
    d.ellipse((3, 24, 23, 31), fill=COLORS[2])
    d.rectangle((10, 19, 13, 28), fill=COLORS[3])
    d.line((11, 20, 11, 27), fill=COLORS[1])
    outline = [(8,0),(15,0),(15,2),(19,2),(19,5),(22,5),(22,9),
               (23,9),(23,18),(21,18),(21,22),(17,22),(17,24),
               (6,24),(6,22),(2,22),(2,18),(0,18),(0,10),(2,10),
               (2,5),(5,5),(5,2),(8,2)]
    d.polygon(outline, fill=COLORS[3])
    d.polygon([(8,2),(14,2),(14,4),(18,4),(18,7),(21,7),(21,16),
               (18,16),(18,20),(14,20),(14,22),(6,21),(3,18),
               (2,11),(4,7),(7,6)], fill=COLORS[2])
    for box in [(8,3,13,5),(5,7,9,10),(12,7,17,11),(3,12,6,15),
                (8,13,12,17),(15,14,18,17),(6,19,9,20)]:
        d.rectangle(box, fill=COLORS[1])
    for x,y in [(8,3),(5,7),(12,7),(8,13)]:
        d.line((x,y,x+2,y), fill=COLORS[0])
    d.line((5,11,9,11), fill=COLORS[3])
    d.line((12,18,16,18), fill=COLORS[3])
    return im


def draw_campus():
    im = Image.new('RGB', (160,144), COLORS[1])
    d = ImageDraw.Draw(im)
    # Repeated sparse grass clusters: texture without noisy single pixels.
    for y in range(0,144,16):
        for x in range(0,160,16):
            d.line((x+3,y+6,x+4,y+7), fill=COLORS[2])
            d.line((x+5,y+5,x+5,y+7), fill=COLORS[2])
            d.line((x+11,y+12,x+13,y+12), fill=COLORS[0])
    # Paving is repeated on an 8px grid; side curbs frame a walkable route.
    d.rectangle((48,64,111,143), fill=COLORS[2])
    d.rectangle((0,72,159,87), fill=COLORS[2])
    for y in range(64,144,8):
        for x in range(0,160,8):
            if 56 <= x < 104 or 72 <= y < 88:
                d.rectangle((x,y,x+6,y+6), fill=COLORS[0])
                d.line((x,y+6,x+6,y+6), fill=COLORS[1])
    # Building shadow, wall, shallow roof and a lit cornice.
    d.rectangle((12,24,155,67), fill=COLORS[3])
    d.rectangle((8,24,151,59), fill=COLORS[1])
    for y in (31,47,55):
        d.line((8,y,151,y), fill=COLORS[2])
    for x in range(8,152,16):
        d.line((x,48,x,54), fill=COLORS[2])
    d.rectangle((8,8,151,23), fill=COLORS[3])
    d.rectangle((12,10,147,19), fill=COLORS[2])
    for x in range(16,148,8):
        d.line((x,10,x,18), fill=COLORS[1])
    d.line((8,22,151,22), fill=COLORS[0])
    d.line((8,25,151,25), fill=COLORS[0])
    # Repeated inset windows with a consistent upper-left highlight.
    for x in (16,40,104,128):
        d.rectangle((x,32,x+15,47), fill=COLORS[3])
        d.rectangle((x+2,33,x+12,43), fill=COLORS[0])
        d.line((x+7,33,x+7,43), fill=COLORS[2])
        d.line((x+2,38,x+12,38), fill=COLORS[2])
        d.line((x,47,x+15,47), fill=COLORS[0])
        d.line((x+1,48,x+16,48), fill=COLORS[3])
    # Blank notice plate and double entrance; the author can draw their signage.
    d.rectangle((64,27,95,34), fill=COLORS[3])
    d.rectangle((66,29,93,32), fill=COLORS[0])
    d.rectangle((68,37,91,59), fill=COLORS[2])
    d.rectangle((72,39,87,59), fill=COLORS[3])
    d.rectangle((74,40,77,49), fill=COLORS[1])
    d.rectangle((82,40,85,49), fill=COLORS[1])
    d.point((77,53), fill=COLORS[0]); d.point((82,53), fill=COLORS[0])
    for y, inset in [(60,0),(63,-2),(66,-4)]:
        d.rectangle((68+inset,y,91-inset,y+2), fill=COLORS[2])
        d.line((68+inset,y,91-inset,y), fill=COLORS[0])
    # Two slatted benches, in matching 32x16 object regions.
    for x in (16,112):
        d.rectangle((x+2,103,x+30,111), fill=COLORS[2])
        d.rectangle((x+3,97,x+5,108), fill=COLORS[3])
        d.rectangle((x+25,97,x+27,108), fill=COLORS[3])
        for y in (96,99,103):
            d.rectangle((x,y,x+31,y+1), fill=COLORS[3])
            d.line((x+1,y,x+29,y), fill=COLORS[0])
    # Small lanterns keep the entrance legible without blocking the path.
    for x in (48,108):
        d.rectangle((x+2,59,x+3,70), fill=COLORS[3])
        d.rectangle((x,55,x+5,60), fill=COLORS[3])
        d.rectangle((x+1,56,x+3,58), fill=COLORS[0])
        d.line((x,71,x+6,71), fill=COLORS[3])
    canopy = tree()
    for position in ((0,40),(136,40),(16,112),(120,112)):
        im.paste(canopy, position, canopy)
    return im


def tile_atlas(im):
    tiles = {}
    for y in range(0,im.height,8):
        for x in range(0,im.width,8):
            tile = im.crop((x,y,x+8,y+8))
            tiles.setdefault(tile.tobytes(), tile)
    atlas = Image.new('RGB', (128, ((len(tiles)+15)//16)*8), COLORS[3])
    for i,tile in enumerate(tiles.values()):
        atlas.paste(tile, ((i%16)*8,(i//16)*8))
    return atlas


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--tiles-output',type=Path)
    args=parser.parse_args()
    im=draw_campus()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    im.save(args.output)
    if args.tiles_output:
        args.tiles_output.parent.mkdir(parents=True,exist_ok=True)
        tile_atlas(im).save(args.tiles_output)

if __name__ == '__main__':
    main()
