#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
make_metatile_map.py

Convert one or more PNG images into a SNES Mode 1 style project:
- .sf4  : shared SNES 4bpp character graphics
- .pal  : shared SNES palette data (8 palettes x 16 colours)
- .mtl  : shared 2x2 metatile data (standard SNES tile words)
- .map  : one map per input PNG
- .m1e  : one project file listing all maps
- _preview.png : one preview per input PNG
- _report.txt  : shared analysis report

Rules:
- Every image width/height must be divisible by 16
- Each 8x8 tile must use <= 16 colours
- Whole combined image set must fit into <= 8 SNES palettes of 16 colours
- Unique characters must fit into <= 1024 after flip-aware dedupe
- Metatile entries use SNES tile word format:
    bits  0-9   = character number
    bits 10-12  = palette
    bit  13     = priority
    bit  14     = X flip
    bit  15     = Y flip

Usage Eg.:
    python make_metatile_map.py commando_level.png
    python make_metatile_map.py AREA1.png AREA5.png --name commando
    python make_metatile_map.py AREA1.png AREA5.png --analyze-only
"""

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
METATILE_SIZE = 16


class ConvertError(Exception):
    pass


@dataclass(frozen=True)
class TileRef:
    char_index: int
    palette_index: int
    xflip: int
    yflip: int
    priority: int = 0


def fail(msg: str):
    raise ConvertError(msg)


def rgb_to_snes(r: int, g: int, b: int) -> int:
    """Convert 8-bit RGB to SNES BGR555."""
    r5 = (r >> 3) & 0x1F
    g5 = (g >> 3) & 0x1F
    b5 = (b >> 3) & 0x1F
    return (b5 << 10) | (g5 << 5) | r5


def pack_snes_tile_word(char_num: int, palette: int, priority: int, xflip: int, yflip: int) -> int:
    if not (0 <= char_num <= 1023):
        fail(f"Character index out of range for SNES tile word: {char_num}")
    if not (0 <= palette <= 7):
        fail(f"Palette index out of range: {palette}")
    word = char_num & 0x03FF
    word |= (palette & 0x07) << 10
    word |= (1 if priority else 0) << 13
    word |= (1 if xflip else 0) << 14
    word |= (1 if yflip else 0) << 15
    return word


def write_u16_le(f, value: int):
    f.write(bytes((value & 0xFF, (value >> 8) & 0xFF)))


def flatten_palette(raw: List[int]) -> List[Tuple[int, int, int]]:
    """Pillow indexed palette comes as flat RGB list."""
    out = []
    for i in range(0, len(raw), 3):
        if i + 2 < len(raw):
            out.append((raw[i], raw[i + 1], raw[i + 2]))
    return out


def ensure_indexed_image(img: Image.Image, force_quantize: bool) -> Image.Image:
    """
    Prefer indexed PNG.
    If not indexed and --quantize supplied, quantize to 256 colours first.
    """
    if img.mode == "P":
        return img

    if not force_quantize:
        fail(
            f"Input image is mode '{img.mode}', not indexed.\n"
            f"Use --quantize to allow conversion to indexed mode first."
        )

    return img.convert("RGBA").convert("P", palette=Image.ADAPTIVE, colors=256)


def get_indexed_pixels_and_palette(img: Image.Image) -> Tuple[List[int], int, int, List[Tuple[int, int, int]]]:
    if img.mode != "P":
        fail("Internal error: expected indexed image (mode P).")

    w, h = img.size

    # Pillow deprecation-safe flattened pixel read
    if hasattr(img, "get_flattened_data"):
        pixels = list(img.get_flattened_data())
    else:
        pixels = list(img.getdata())

    pal = flatten_palette(img.getpalette() or [])
    if not pal:
        fail("Indexed image has no palette.")
    return pixels, w, h, pal


def get_tile_pixels(pixels: List[int], image_w: int, tx: int, ty: int) -> List[int]:
    """
    Return an 8x8 tile as a flat list of 64 palette indices.
    tx, ty are tile coordinates in 8x8 units.
    """
    out = []
    px0 = tx * TILE_SIZE
    py0 = ty * TILE_SIZE
    for yy in range(TILE_SIZE):
        base = (py0 + yy) * image_w + px0
        out.extend(pixels[base:base + TILE_SIZE])
    return out


def tile_unique_colours(tile_pixels: List[int]) -> Set[int]:
    return set(tile_pixels)


def greedy_pack_palettes(tile_colour_sets: List[Set[int]]):
    """
    Build up to 8 palettes of <=16 colours using greedy merging of unique tile colour sets.

    Returns:
      ordered_palettes      : list of palette colour index lists
      remapped_set_to_palidx: map from unique set ordinal -> palette index
      unique_sets           : list of unique colour sets
      seen                  : dict tuple(sorted(set)) -> unique set ordinal
    """
    unique_sets = []
    seen = {}
    for s in tile_colour_sets:
        key = tuple(sorted(s))
        if key not in seen:
            seen[key] = len(unique_sets)
            unique_sets.append(set(s))

    order = sorted(
        range(len(unique_sets)),
        key=lambda i: (-len(unique_sets[i]), tuple(sorted(unique_sets[i])))
    )

    palettes: List[Set[int]] = []
    set_to_palidx: Dict[int, int] = {}

    for set_idx in order:
        colours = unique_sets[set_idx]

        if len(colours) > PALETTE_SIZE:
            fail(f"A tile colour set exceeds {PALETTE_SIZE} colours, impossible to map.")

        best_pal = -1
        best_growth = None

        for pi, pset in enumerate(palettes):
            merged = pset | colours
            if len(merged) <= PALETTE_SIZE:
                growth = len(merged) - len(pset)
                if best_growth is None or growth < best_growth:
                    best_growth = growth
                    best_pal = pi

        if best_pal >= 0:
            palettes[best_pal] |= colours
            set_to_palidx[set_idx] = best_pal
        else:
            if len(palettes) >= MAX_PALETTES:
                fail(f"Image set requires more than {MAX_PALETTES} palettes of {PALETTE_SIZE} colours.")
            palettes.append(set(colours))
            set_to_palidx[set_idx] = len(palettes) - 1

    ordered_palettes: List[List[int]] = []
    old_to_new = {}
    for old_idx, pset in enumerate(palettes):
        ordered = sorted(pset)
        ordered_palettes.append(ordered)
        old_to_new[old_idx] = len(ordered_palettes) - 1

    remapped = {}
    for key, uniq_idx in seen.items():
        old_pal = set_to_palidx[uniq_idx]
        remapped[uniq_idx] = old_to_new[old_pal]

    return ordered_palettes, remapped, unique_sets, seen


def build_palette_lookup(palette_colours: List[int]) -> Dict[int, int]:
    """Map source palette colour index -> local SNES palette entry 0..15"""
    return {src_idx: i for i, src_idx in enumerate(palette_colours)}


def remap_tile_to_local_indices(tile_pixels: List[int], palette_lookup: Dict[int, int], tx: int, ty: int) -> List[int]:
    out = []
    for c in tile_pixels:
        if c not in palette_lookup:
            fail(f"Tile ({tx}, {ty}) could not be remapped into its assigned SNES palette.")
        out.append(palette_lookup[c])
    return out


def flip_tile_x(tile_local: List[int]) -> List[int]:
    out = []
    for y in range(TILE_SIZE):
        row = tile_local[y * TILE_SIZE:(y + 1) * TILE_SIZE]
        out.extend(row[::-1])
    return out


def flip_tile_y(tile_local: List[int]) -> List[int]:
    out = []
    for y in range(TILE_SIZE - 1, -1, -1):
        row = tile_local[y * TILE_SIZE:(y + 1) * TILE_SIZE]
        out.extend(row)
    return out


def flip_tile_xy(tile_local: List[int]) -> List[int]:
    return flip_tile_y(flip_tile_x(tile_local))


def encode_4bpp_snes(tile_local: List[int]) -> bytes:
    """
    Encode one 8x8 tile of local indices 0..15 into SNES 4bpp planar format (32 bytes).
    """
    if len(tile_local) != 64:
        fail("Internal error: tile_local must be 64 pixels.")

    out = bytearray()

    for y in range(8):
        row = tile_local[y * 8:(y + 1) * 8]

        p0 = p1 = 0
        for x, px in enumerate(row):
            bit = 7 - x
            p0 |= ((px >> 0) & 1) << bit
            p1 |= ((px >> 1) & 1) << bit

        out.append(p0)
        out.append(p1)

    for y in range(8):
        row = tile_local[y * 8:(y + 1) * 8]

        p2 = p3 = 0
        for x, px in enumerate(row):
            bit = 7 - x
            p2 |= ((px >> 2) & 1) << bit
            p3 |= ((px >> 3) & 1) << bit

        out.append(p2)
        out.append(p3)

    return bytes(out)


def decode_4bpp_snes(tile_bytes: bytes) -> List[int]:
    """
    Decode SNES 4bpp planar tile back to local 0..15 indices.
    Used only for preview rendering.
    """
    if len(tile_bytes) != 32:
        fail("Internal error: SNES tile bytes must be 32 bytes.")

    pixels = [0] * 64

    for y in range(8):
        p0 = tile_bytes[y * 2 + 0]
        p1 = tile_bytes[y * 2 + 1]
        p2 = tile_bytes[16 + y * 2 + 0]
        p3 = tile_bytes[16 + y * 2 + 1]

        for x in range(8):
            bit = 7 - x
            c = (((p0 >> bit) & 1) << 0) \
                | (((p1 >> bit) & 1) << 1) \
                | (((p2 >> bit) & 1) << 2) \
                | (((p3 >> bit) & 1) << 3)
            pixels[y * 8 + x] = c

    return pixels


def write_sf4(path: str, char_bytes_list: List[bytes]):
    with open(path, "wb") as f:
        for tb in char_bytes_list:
            if len(tb) != 32:
                fail("Internal error: encoded tile is not 32 bytes.")
            f.write(tb)


def write_mtl(path: str, metatiles: List[Tuple[TileRef, TileRef, TileRef, TileRef]]):
    with open(path, "wb") as f:
        for mt in metatiles:
            for tref in mt:
                word = pack_snes_tile_word(
                    tref.char_index,
                    tref.palette_index,
                    tref.priority,
                    tref.xflip,
                    tref.yflip
                )
                write_u16_le(f, word)


def write_map(path: str, metatile_indices: List[int]):
    with open(path, "wb") as f:
        for idx in metatile_indices:
            write_u16_le(f, idx)


def write_snes_palette(path: str, snes_palette_words: List[int]):
    with open(path, "wb") as f:
        for w in snes_palette_words:
            write_u16_le(f, w)


def write_m1e_multi(path: str, stem: str, maps_info: List[dict]):
    map_names = []
    widths = []
    heights = []

    for m in maps_info:
        map_names.append(f"{m['map_name']}.map")
        widths.append(str(m["mt_w"]))
        heights.append(str(m["mt_h"]))

    lines = [
        f"palette={stem}.pal",
        f"tiles={stem}.sf4",
        f"metatiles={stem}.mtl",
        f"maps={','.join(map_names)}",
        f"width={','.join(widths)}",
        f"height={','.join(heights)}",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def build_preview_image(
    out_path: str,
    image_w: int,
    image_h: int,
    tile_grid_refs: List[TileRef],
    tile_grid_w: int,
    char_bytes_list: List[bytes],
    snes_palettes_rgb: List[List[Tuple[int, int, int]]]
):
    """
    Rebuild a preview from final tile refs and final palettes.
    """
    img = Image.new("RGB", (image_w, image_h))
    px = img.load()

    for ty in range(image_h // 8):
        for tx in range(image_w // 8):
            tref = tile_grid_refs[ty * tile_grid_w + tx]
            tile = decode_4bpp_snes(char_bytes_list[tref.char_index])

            if tref.xflip and tref.yflip:
                tile = flip_tile_xy(tile)
            elif tref.xflip:
                tile = flip_tile_x(tile)
            elif tref.yflip:
                tile = flip_tile_y(tile)

            pal = snes_palettes_rgb[tref.palette_index]

            for yy in range(8):
                for xx in range(8):
                    c = tile[yy * 8 + xx]
                    r, g, b = pal[c]
                    px[tx * 8 + xx, ty * 8 + yy] = (r, g, b)

    img.save(out_path)

def load_images_shared_quantized(paths: List[str]) -> List[dict]:
    """
    Load multiple images, combine vertically, quantize once, then split back out.
    This ensures all images share the same indexed palette and palette index meanings.
    """
    rgba_images = []
    widths = []
    heights = []

    for path in paths:
        img = Image.open(path).convert("RGBA")
        rgba_images.append(img)
        widths.append(img.width)
        heights.append(img.height)

    combined_w = max(widths)
    combined_h = sum(heights)

    combined = Image.new("RGBA", (combined_w, combined_h), (0, 0, 0, 0))

    y = 0
    regions = []
    for path, img in zip(paths, rgba_images):
        combined.paste(img, (0, y))
        regions.append({
            "path": path,
            "x": 0,
            "y": y,
            "w": img.width,
            "h": img.height,
            "stem": os.path.splitext(os.path.basename(path))[0],
        })
        y += img.height

    combined_p = combined.convert("P", palette=Image.ADAPTIVE, colors=256)

    shared_palette = flatten_palette(combined_p.getpalette() or [])
    if not shared_palette:
        fail("Shared quantized image has no palette.")

    out = []
    for r in regions:
        cropped = combined_p.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))
        pixels, image_w, image_h, _ = get_indexed_pixels_and_palette(cropped)

        out.append({
            "path": r["path"],
            "stem": r["stem"],
            "pixels": pixels,
            "image_w": image_w,
            "image_h": image_h,
            "source_palette": shared_palette,
        })

    return out

def analyse_prepared_indexed_image(path: str, stem: str, pixels: List[int], image_w: int, image_h: int,
                                   source_palette: List[Tuple[int, int, int]]) -> dict:
    if image_w % METATILE_SIZE != 0 or image_h % METATILE_SIZE != 0:
        fail(
            f"Image '{os.path.basename(path)}' dimensions must be divisible by {METATILE_SIZE}. "
            f"Got {image_w}x{image_h}."
        )

    tile_w = image_w // TILE_SIZE
    tile_h = image_h // TILE_SIZE
    mt_w = image_w // METATILE_SIZE
    mt_h = image_h // METATILE_SIZE

    all_tile_pixels: List[List[int]] = []
    tile_colour_sets: List[Set[int]] = []

    for ty in range(tile_h):
        for tx in range(tile_w):
            tp = get_tile_pixels(pixels, image_w, tx, ty)
            colours = tile_unique_colours(tp)
            if len(colours) > PALETTE_SIZE:
                fail(
                    f"Image '{os.path.basename(path)}' tile ({tx}, {ty}) uses "
                    f"{len(colours)} colours, exceeds 16."
                )
            all_tile_pixels.append(tp)
            tile_colour_sets.append(colours)

    return {
        "path": path,
        "stem": stem,
        "pixels": pixels,
        "image_w": image_w,
        "image_h": image_h,
        "tile_w": tile_w,
        "tile_h": tile_h,
        "mt_w": mt_w,
        "mt_h": mt_h,
        "source_palette": source_palette,
        "used_source_colours": sorted(set(pixels)),
        "all_tile_pixels": all_tile_pixels,
        "tile_colour_sets": tile_colour_sets,
    }
    

def analyse_single_image(path: str, force_quantize: bool) -> dict:
    img = Image.open(path)
    img = ensure_indexed_image(img, force_quantize=force_quantize)

    pixels, image_w, image_h, source_palette = get_indexed_pixels_and_palette(img)

    stem = os.path.splitext(os.path.basename(path))[0]
    return analyse_prepared_indexed_image(path, stem, pixels, image_w, image_h, source_palette)

def main():
    parser = argparse.ArgumentParser(description="Convert one or more PNG images into a shared Mode 1 metatile project.")
    parser.add_argument("input_png", nargs="+", help="Input PNG image(s)")
    parser.add_argument("--quantize", action="store_true",
                        help="If an input is not indexed, quantize it to indexed mode first")
    parser.add_argument("--analyze-only", action="store_true",
                        help="Analyze and report only, do not write output files")
    parser.add_argument("--name", help="Base name for shared output files (.sf4, .pal, .mtl, .m1e)")
    args = parser.parse_args()

    input_paths = args.input_png
    for path in input_paths:
        if not os.path.isfile(path):
            fail(f"Input file not found: {path}")

    shared_stem = args.name if args.name else os.path.splitext(os.path.basename(input_paths[0]))[0]
    out_dir = os.path.dirname(os.path.abspath(input_paths[0]))
    base = os.path.join(out_dir, shared_stem)

    report_lines = []
    flip_reuse_count = 0

    # -------------------------------------------------------------------------
    # Stage 1: analyse each image individually
    # -------------------------------------------------------------------------
    images_info = []

    if args.quantize and len(input_paths) > 1:
        prepared = load_images_shared_quantized(input_paths)
        for item in prepared:
            info = analyse_prepared_indexed_image(
                item["path"],
                item["stem"],
                item["pixels"],
                item["image_w"],
                item["image_h"],
                item["source_palette"],
            )
            images_info.append(info)
    else:
        for path in input_paths:
            info = analyse_single_image(path, force_quantize=args.quantize)
            images_info.append(info)

    report_lines.append(f"Project name         : {shared_stem}")
    report_lines.append(f"Images processed     : {len(images_info)}")

    for info in images_info:
        report_lines.append(f"")
        report_lines.append(f"[{os.path.basename(info['path'])}]")
        report_lines.append(f"Size                 : {info['image_w']} x {info['image_h']}")
        report_lines.append(f"Tiles (8x8)          : {info['tile_w']} x {info['tile_h']}")
        report_lines.append(f"Metatiles (16x16)    : {info['mt_w']} x {info['mt_h']}")
        report_lines.append(f"Source colours       : {len(info['used_source_colours'])}")

    # -------------------------------------------------------------------------
    # Stage 2: verify source palettes are compatible enough to share
    #         For indexed images, palette index meanings must match across files.
    # -------------------------------------------------------------------------
    reference_palette = images_info[0]["source_palette"]

    for info in images_info[1:]:
        other_palette = info["source_palette"]
        max_len = max(len(reference_palette), len(other_palette))
        for i in range(max_len):
            ref = reference_palette[i] if i < len(reference_palette) else None
            oth = other_palette[i] if i < len(other_palette) else None
            if ref != oth:
                fail(
                    f"Indexed palette mismatch between '{os.path.basename(images_info[0]['path'])}' "
                    f"and '{os.path.basename(info['path'])}' at palette index {i}. "
                    f"Shared import assumes consistent palette index meanings across PNGs."
                )

    shared_source_palette = reference_palette

    # -------------------------------------------------------------------------
    # Stage 3: gather all tile colour sets from all images and build shared palettes
    # -------------------------------------------------------------------------
    combined_tile_colour_sets: List[Set[int]] = []
    for info in images_info:
        combined_tile_colour_sets.extend(info["tile_colour_sets"])

    ordered_palettes, remapped_set_to_palidx, unique_sets, seen_set_lookup = greedy_pack_palettes(combined_tile_colour_sets)

    report_lines.append(f"")
    report_lines.append(f"Shared palettes used : {len(ordered_palettes)} / {MAX_PALETTES}")
    for i, pal in enumerate(ordered_palettes):
        report_lines.append(f"Palette {i} colours  : {len(pal)}")

    palette_lookups = [build_palette_lookup(pal) for pal in ordered_palettes]

    snes_palettes_rgb: List[List[Tuple[int, int, int]]] = []
    snes_palette_words: List[int] = []

    for pal in ordered_palettes:
        rgb_entries = []
        for src_idx in pal:
            if src_idx >= len(shared_source_palette):
                fail(f"Source palette index out of range: {src_idx}")
            rgb = shared_source_palette[src_idx]
            rgb_entries.append(rgb)
            snes_palette_words.append(rgb_to_snes(*rgb))

        while len(rgb_entries) < PALETTE_SIZE:
            rgb_entries.append((0, 0, 0))
            snes_palette_words.append(rgb_to_snes(0, 0, 0))

        snes_palettes_rgb.append(rgb_entries)

    while len(snes_palettes_rgb) < MAX_PALETTES:
        snes_palettes_rgb.append([(0, 0, 0)] * PALETTE_SIZE)
        for _ in range(PALETTE_SIZE):
            snes_palette_words.append(rgb_to_snes(0, 0, 0))

    # -------------------------------------------------------------------------
    # Stage 4: shared character dedupe across all images
    # -------------------------------------------------------------------------
    char_bytes_list: List[bytes] = []
    char_lookup: Dict[bytes, int] = {}

    for info in images_info:
        tile_grid_refs: List[TileRef] = []

        for ty in range(info["tile_h"]):
            for tx in range(info["tile_w"]):
                idx = ty * info["tile_w"] + tx
                tp = info["all_tile_pixels"][idx]
                colour_set_key = tuple(sorted(info["tile_colour_sets"][idx]))
                uniq_idx = seen_set_lookup[colour_set_key]
                pal_idx = remapped_set_to_palidx[uniq_idx]
                pal_lookup = palette_lookups[pal_idx]

                tile_local = remap_tile_to_local_indices(tp, pal_lookup, tx, ty)

                tile_n = encode_4bpp_snes(tile_local)
                tile_x = encode_4bpp_snes(flip_tile_x(tile_local))
                tile_y = encode_4bpp_snes(flip_tile_y(tile_local))
                tile_xy = encode_4bpp_snes(flip_tile_xy(tile_local))

                if tile_n in char_lookup:
                    char_index = char_lookup[tile_n]
                    xflip = 0
                    yflip = 0
                elif tile_x in char_lookup:
                    char_index = char_lookup[tile_x]
                    xflip = 1
                    yflip = 0
                    flip_reuse_count += 1
                elif tile_y in char_lookup:
                    char_index = char_lookup[tile_y]
                    xflip = 0
                    yflip = 1
                    flip_reuse_count += 1
                elif tile_xy in char_lookup:
                    char_index = char_lookup[tile_xy]
                    xflip = 1
                    yflip = 1
                    flip_reuse_count += 1
                else:
                    char_index = len(char_bytes_list)
                    if char_index >= MAX_CHARS:
                        fail(f"Unique characters exceed SNES limit: {char_index + 1} > {MAX_CHARS}")
                    char_bytes_list.append(tile_n)
                    char_lookup[tile_n] = char_index
                    xflip = 0
                    yflip = 0

                tile_grid_refs.append(TileRef(char_index, pal_idx, xflip, yflip, 0))

        info["tile_grid_refs"] = tile_grid_refs

    report_lines.append(f"")
    report_lines.append(f"Shared characters    : {len(char_bytes_list)} / {MAX_CHARS}")
    report_lines.append(f"Flip reuse           : {flip_reuse_count} matches")

    # -------------------------------------------------------------------------
    # Stage 5: shared metatile dedupe across all images, separate maps per image
    # -------------------------------------------------------------------------
    metatile_lookup: Dict[Tuple[TileRef, TileRef, TileRef, TileRef], int] = {}
    metatiles: List[Tuple[TileRef, TileRef, TileRef, TileRef]] = []
    maps_info: List[dict] = []

    for info in images_info:
        metatile_map_indices: List[int] = []

        for my in range(info["mt_h"]):
            for mx in range(info["mt_w"]):
                tx = mx * 2
                ty = my * 2

                tl = info["tile_grid_refs"][(ty + 0) * info["tile_w"] + (tx + 0)]
                tr = info["tile_grid_refs"][(ty + 0) * info["tile_w"] + (tx + 1)]
                bl = info["tile_grid_refs"][(ty + 1) * info["tile_w"] + (tx + 0)]
                br = info["tile_grid_refs"][(ty + 1) * info["tile_w"] + (tx + 1)]

                mt = (tl, tr, bl, br)

                if mt in metatile_lookup:
                    mt_idx = metatile_lookup[mt]
                else:
                    mt_idx = len(metatiles)
                    metatile_lookup[mt] = mt_idx
                    metatiles.append(mt)

                metatile_map_indices.append(mt_idx)

        maps_info.append({
            "image_path": info["path"],
            "map_name": info["stem"],
            "mt_w": info["mt_w"],
            "mt_h": info["mt_h"],
            "indices": metatile_map_indices,
            "tile_w": info["tile_w"],
            "tile_h": info["tile_h"],
            "tile_grid_refs": info["tile_grid_refs"],
            "image_w": info["image_w"],
            "image_h": info["image_h"],
        })

    report_lines.append(f"Shared metatiles     : {len(metatiles)}")

    for m in maps_info:
        report_lines.append(f"{m['map_name']} map size      : {m['mt_w']} x {m['mt_h']}")

    report_lines.append("Status               : OK")

    report_path = base + "_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

    if args.analyze_only:
        print("\n".join(report_lines))
        print(f"\nAnalyze-only mode. Report written: {report_path}")
        return

    # -------------------------------------------------------------------------
    # Write shared outputs
    # -------------------------------------------------------------------------
    sf4_path = base + ".sf4"
    pal_path = base + ".pal"
    mtl_path = base + ".mtl"
    m1e_path = base + ".m1e"

    write_sf4(sf4_path, char_bytes_list)
    write_snes_palette(pal_path, snes_palette_words)
    write_mtl(mtl_path, metatiles)
    write_m1e_multi(m1e_path, shared_stem, maps_info)

    # Write per-image maps and previews
    written_map_paths = []
    written_preview_paths = []

    for m in maps_info:
        map_path = os.path.join(out_dir, m["map_name"] + ".map")
        preview_path = os.path.join(out_dir, m["map_name"] + "_preview.png")

        write_map(map_path, m["indices"])
        build_preview_image(
            preview_path,
            m["image_w"],
            m["image_h"],
            m["tile_grid_refs"],
            m["tile_w"],
            char_bytes_list,
            snes_palettes_rgb
        )

        written_map_paths.append(map_path)
        written_preview_paths.append(preview_path)

    print("\n".join(report_lines))
    print("")
    print(f"Wrote: {sf4_path}")
    print(f"Wrote: {pal_path}")
    print(f"Wrote: {mtl_path}")
    print(f"Wrote: {m1e_path}")
    for p in written_map_paths:
        print(f"Wrote: {p}")
    for p in written_preview_paths:
        print(f"Wrote: {p}")
    print(f"Wrote: {report_path}")


if __name__ == "__main__":
    try:
        main()
    except ConvertError as e:
        print(f"FAILED: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("Aborted.", file=sys.stderr)
        sys.exit(1)