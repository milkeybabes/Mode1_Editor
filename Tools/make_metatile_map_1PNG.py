#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set
from PIL import Image

MAX_PALETTES = 8
PALETTE_SIZE = 16
MAX_CHARS = 1024
TILE_SIZE = 8

class ConvertError(Exception):
    pass

@dataclass(frozen=True)
class TileRef:
    char_index: int
    palette_index: int
    xflip: int
    yflip: int
    priority: int = 0

def fail(msg):
    raise ConvertError(msg)

def rgb_to_snes(r, g, b):
    return ((b >> 3) << 10) | ((g >> 3) << 5) | (r >> 3)

def write_u16_le(f, value):
    f.write(bytes((value & 0xFF, value >> 8)))

def flatten_palette(raw):
    return [(raw[i], raw[i+1], raw[i+2]) for i in range(0, len(raw), 3)]

def ensure_indexed_image(img, quantize):
    if img.mode == "P":
        return img
    if not quantize:
        fail("Image must be indexed or use --quantize")
    return img.convert("RGBA").convert("P", palette=Image.ADAPTIVE, colors=256)

def get_pixels(img):
    if hasattr(img, "get_flattened_data"):
        return list(img.get_flattened_data())
    return list(img.getdata())

def get_tile_pixels(pixels, w, tx, ty):
    out = []
    px = tx * 8
    py = ty * 8
    for y in range(8):
        base = (py + y) * w + px
        out.extend(pixels[base:base+8])
    return out

def flip_x(t):
    return sum([t[y*8:(y+1)*8][::-1] for y in range(8)], [])

def flip_y(t):
    return sum([t[y*8:(y+1)*8] for y in reversed(range(8))], [])

def flip_xy(t):
    return flip_y(flip_x(t))

def encode_4bpp(tile):
    out = bytearray()
    for y in range(8):
        row = tile[y*8:(y+1)*8]
        p0=p1=0
        for x,v in enumerate(row):
            b=7-x
            p0 |= ((v>>0)&1)<<b
            p1 |= ((v>>1)&1)<<b
        out+=bytes([p0,p1])
    for y in range(8):
        row = tile[y*8:(y+1)*8]
        p2=p3=0
        for x,v in enumerate(row):
            b=7-x
            p2 |= ((v>>2)&1)<<b
            p3 |= ((v>>3)&1)<<b
        out+=bytes([p2,p3])
    return bytes(out)

def greedy_palettes(tile_sets):
    palettes=[]
    mapping={}
    for s in tile_sets:
        assigned=False
        for i,p in enumerate(palettes):
            if len(p|s)<=16:
                palettes[i]|=s
                mapping[tuple(sorted(s))]=i
                assigned=True
                break
        if not assigned:
            if len(palettes)>=8:
                fail("Too many palettes")
            palettes.append(set(s))
            mapping[tuple(sorted(s))]=len(palettes)-1
    return [sorted(p) for p in palettes], mapping

def build_metatiles(tile_refs, tw, th, size):
    if tw % size or th % size:
        fail("Not divisible by metatile size")

    mts=[]
    lookup={}
    out=[]

    mw = tw//size
    mh = th//size

    for my in range(mh):
        for mx in range(mw):
            block=[]
            for y in range(size):
                for x in range(size):
                    block.append(tile_refs[(my*size+y)*tw + (mx*size+x)])
            t=tuple(block)
            if t not in lookup:
                lookup[t]=len(mts)
                mts.append(t)
            out.append(lookup[t])
    return mts,out,mw,mh

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("png")
    parser.add_argument("--quantize", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--metatile-tiles", type=int, default=2, choices=[2,4,8,16])
    parser.add_argument("--compare-sizes", action="store_true")
    args = parser.parse_args()

    img = Image.open(args.png)
    img = ensure_indexed_image(img, args.quantize)

    pixels = get_pixels(img)
    w,h = img.size
    pal = flatten_palette(img.getpalette())

    if w%8 or h%8:
        fail("Must be multiple of 8")

    tw,th = w//8, h//8

    tiles=[]
    tile_sets=[]
    for ty in range(th):
        for tx in range(tw):
            t = get_tile_pixels(pixels,w,tx,ty)
            s=set(t)
            if len(s)>16:
                fail("Tile >16 colours")
            tiles.append(t)
            tile_sets.append(s)

    palettes, map_pal = greedy_palettes(tile_sets)

    char_data=[]
    lookup={}
    tile_refs=[]
    flips=0

    for i,t in enumerate(tiles):
        key = tuple(sorted(tile_sets[i]))
        pidx = map_pal[key]
        lut = {c:i for i,c in enumerate(palettes[pidx])}

        local = [lut[c] for c in t]

        enc = encode_4bpp(local)
        encx = encode_4bpp(flip_x(local))
        ency = encode_4bpp(flip_y(local))
        encxy= encode_4bpp(flip_xy(local))

        if enc in lookup:
            idx=lookup[enc]; xf=yf=0
        elif encx in lookup:
            idx=lookup[encx]; xf=1; yf=0; flips+=1
        elif ency in lookup:
            idx=lookup[ency]; xf=0; yf=1; flips+=1
        elif encxy in lookup:
            idx=lookup[encxy]; xf=1; yf=1; flips+=1
        else:
            idx=len(char_data)
            if idx>=MAX_CHARS:
                fail("Too many chars")
            char_data.append(enc)
            lookup[enc]=idx
            xf=yf=0

        tile_refs.append(TileRef(idx,pidx,xf,yf,0))

    print(f"Chars: {len(char_data)} / {MAX_CHARS}")
    print(f"Flip reuse: {flips}")

    if args.compare_sizes:
        print("\nCompare:")
        best=None
        for s in [2,4,8,16]:
            if tw%s or th%s:
                print(f"{s}x{s}: invalid")
                continue
            mts,mapi,mw,mh = build_metatiles(tile_refs,tw,th,s)
            map_bytes = len(mapi)*2
            mtl_bytes = len(mts)*(s*s)*2
            total = map_bytes+mtl_bytes
            print(f"{s}x{s}: map={map_bytes} mtl={mtl_bytes} total={total}")
            if not best or total<best[0]:
                best=(total,s)
        print(f"Best: {best[1]}x{best[1]}")
        return

    mts,mapi,mw,mh = build_metatiles(tile_refs,tw,th,args.metatile_tiles)

    print(f"Metatile size: {args.metatile_tiles}x{args.metatile_tiles}")
    print(f"Map: {mw} x {mh}")
    print(f"Metatiles: {len(mts)}")

if __name__ == "__main__":
    try:
        main()
    except ConvertError as e:
        print("FAILED:",e)