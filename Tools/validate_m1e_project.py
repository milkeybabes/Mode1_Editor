#!/usr/bin/env python3
import argparse
import glob
import os
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None
    ImageDraw = None


MAX_METATILE_W = 32
MAX_METATILE_H = 32

def parse_int(text, default=None):
    if text is None or text == "":
        return default

    text = str(text).strip().lower()

    if text.startswith("$"):
        return int(text[1:], 16)

    if text.startswith("0x"):
        return int(text, 16)

    return int(text, 10)


def get_map_format(m1e):
    map_index_mask = parse_int(m1e.get("map_index_mask"), 0x03FF)
    map_h_flip_bit = parse_int(m1e.get("map_h_flip_bit"), 14)
    map_v_flip_bit = parse_int(m1e.get("map_v_flip_bit"), 15)

    map_h_flip_mask = 1 << map_h_flip_bit
    map_v_flip_mask = 1 << map_v_flip_bit

    return map_index_mask, map_h_flip_bit, map_v_flip_bit, map_h_flip_mask, map_v_flip_mask


def parse_size(text):
    m = re.match(r"^\s*(\d+)\s*x\s*(\d+)\s*$", text, re.IGNORECASE)
    if not m:
        raise ValueError(f"Invalid size '{text}', expected WxH, e.g. 2x2 or 4x4")

    w = int(m.group(1))
    h = int(m.group(2))

    if w < 1 or h < 1:
        raise ValueError("Metatile size must be at least 1x1")

    if w > MAX_METATILE_W or h > MAX_METATILE_H:
        raise ValueError(f"Metatile size too large: {w}x{h}, max is {MAX_METATILE_W}x{MAX_METATILE_H}")

    return w, h


def read_m1e(path):
    data = {}

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            if line.startswith("#") or line.startswith(";"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            data[key.strip().lower()] = value.strip()

    return data


def project_path(project_file, value):
    if not value:
        return None

    p = Path(value)

    if p.is_absolute():
        return p

    return Path(project_file).parent / p


def convert_dkc_horizontal_map_to_linear(raw, width, height=16):
    # raw is column-major: x outer, y inner
    words = [raw[i] | (raw[i+1] << 8) for i in range(0, len(raw), 2)]

    out = bytearray()

    for y in range(height):
        for x in range(width):
            v = words[x * height + y]
            out += bytes((v & 0xff, v >> 8))

    return bytes(out)


def read_u16_le(data, offset):
    return data[offset] | (data[offset + 1] << 8)


def read_snes_palette(path):
    data = Path(path).read_bytes()

    colours = []

    for i in range(0, len(data) - 1, 2):
        v = read_u16_le(data, i)

        r = (v >> 0) & 0x1F
        g = (v >> 5) & 0x1F
        b = (v >> 10) & 0x1F

        r = (r << 3) | (r >> 2)
        g = (g << 3) | (g >> 2)
        b = (b << 3) | (b >> 2)

        colours.append((r, g, b, 255))

    while len(colours) < 128:
        colours.append((0, 0, 0, 255))

    return colours


def decode_4bpp_tile(tile_data, palette, palette_index):
    img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    px = img.load()

    pal_base = palette_index * 16

    for y in range(8):
        p0 = tile_data[y * 2 + 0]
        p1 = tile_data[y * 2 + 1]
        p2 = tile_data[16 + y * 2 + 0]
        p3 = tile_data[16 + y * 2 + 1]

        for x in range(8):
            bit = 7 - x
            colour_index = (
                (((p0 >> bit) & 1) << 0) |
                (((p1 >> bit) & 1) << 1) |
                (((p2 >> bit) & 1) << 2) |
                (((p3 >> bit) & 1) << 3)
            )

            if colour_index == 0:
                px[x, y] = (0, 0, 0, 0)
            else:
                px[x, y] = palette[pal_base + colour_index]

    return img


def draw_char(chars, tile_count, value, palette):
    char_num = value & 0x03FF
    pal = (value >> 10) & 0x07
    xflip = bool(value & 0x4000)
    yflip = bool(value & 0x8000)

    if char_num >= tile_count:
        return Image.new("RGBA", (8, 8), (255, 0, 255, 255))

    tile_data = chars[char_num * 32:char_num * 32 + 32]
    img = decode_4bpp_tile(tile_data, palette, pal)

    if xflip:
        img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    if yflip:
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    return img


def read_metatiles(path, mt_w, mt_h):
    if path is None or not path.exists():
        return []

    data = path.read_bytes()
    bytes_per_metatile = mt_w * mt_h * 2

    if bytes_per_metatile <= 0:
        raise ValueError("Invalid metatile byte size")

    if len(data) % bytes_per_metatile != 0:
        print(f"ERROR: metatile file size is not a multiple of {bytes_per_metatile}: {len(data)}")

    metatiles = []

    usable = len(data) - (len(data) % bytes_per_metatile)

    for i in range(0, usable, bytes_per_metatile):
        mt = []

        for j in range(0, bytes_per_metatile, 2):
            mt.append(read_u16_le(data, i + j))

        metatiles.append(mt)

    return metatiles


def validate_project(project_file, args):
    m1e = read_m1e(project_file)

    name = m1e.get("name", Path(project_file).stem)

    map_path = project_path(project_file, m1e.get("map", ""))
    chr_path = project_path(project_file, m1e.get("tiles", ""))
    pal_path = project_path(project_file, m1e.get("palette", ""))
    mtl_value = m1e.get("metatiles", "")

    if mtl_value:
        mtl_path = project_path(project_file, mtl_value)
    else:
        mtl_path = None

    if args.tileset:
        mt_w, mt_h = parse_size(args.tileset)
        size_source = "--tileset"
    elif "metatile_size" in m1e:
        mt_w, mt_h = parse_size(m1e["metatile_size"])
        size_source = "m1e"
    else:
        mt_w, mt_h = 1, 1
        size_source = "default"

    width = int(m1e.get("width", "0") or "0")
    height = int(m1e.get("height", "0") or "0")
    
    map_index_mask, map_h_flip_bit, map_v_flip_bit, map_h_flip_mask, map_v_flip_mask = get_map_format(m1e)

    print()
    print("=" * 72)
    print(f"Project        : {project_file}")
    print(f"Name           : {name}")
    print(f"Metatile size  : {mt_w}x{mt_h} ({size_source})")
    print(f"Map size       : {width}x{height}" if width and height else "Map size       : not specified")
    print(f"CHR            : {chr_path}")
    print(f"Palette        : {pal_path}")
    print(f"Map            : {map_path}")
    print(f"Metatiles      : {mtl_path if mtl_path else '(none / 1x1 mode)'}")
    print(f"Map index mask : ${map_index_mask:04X}")
    print(f"Map H flip bit : {map_h_flip_bit} (${map_h_flip_mask:04X})")
    print(f"Map V flip bit : {map_v_flip_bit} (${map_v_flip_mask:04X})")
    
    errors = 0

    if not chr_path or not chr_path.exists():
        print("ERROR: missing .sf4 / tiles file")
        return 1

    if not map_path or not map_path.exists():
        print("ERROR: missing .map file")
        return 1

    if not pal_path or not pal_path.exists():
        print("ERROR: missing .pal file")
        errors += 1

    chr_data = chr_path.read_bytes()
    chr_size = len(chr_data)

    if chr_size % 32 != 0:
        print(f"ERROR: .sf4 size is not multiple of 32: {chr_size}")
        errors += 1

    tile_count = chr_size // 32

    if mtl_path and mtl_path.exists():
        metatiles = read_metatiles(mtl_path, mt_w, mt_h)
    else:
        metatiles = []

    no_metatile_mode = len(metatiles) == 0

    if no_metatile_mode:
        mt_count = tile_count
    else:
        mt_count = len(metatiles)

    map_data = map_path.read_bytes()

    if len(map_data) % 2 != 0:
        print(f"ERROR: .map size is not even: {len(map_data)}")
        errors += 1

    map_entries = len(map_data) // 2

    if width and height:
        expected_entries = width * height
        if expected_entries != map_entries:
            print(f"ERROR: map entries mismatch: file has {map_entries}, m1e says {expected_entries}")
            errors += 1

    print()
    print("Counts")
    print("------")
    print(f"CHR bytes      : {chr_size}")
    print(f"CHR tiles      : {tile_count}")
    print(f"Metatile bytes : {0 if not mtl_path or not mtl_path.exists() else mtl_path.stat().st_size}")
    print(f"Metatiles      : {mt_count}" + (" (1x1 direct char mode)" if no_metatile_mode else ""))
    print(f"Map bytes      : {len(map_data)}")
    print(f"Map entries    : {map_entries}")

    bad_meta_chars = 0

    if not no_metatile_mode:
        for mt_i, mt in enumerate(metatiles):
            for slot, value in enumerate(mt):
                char_num = value & 0x03FF

                if char_num >= tile_count:
                    if bad_meta_chars < args.max_errors:
                        print(f"BAD METATILE: mt {mt_i} slot {slot} char {char_num} >= CHR tiles {tile_count} value=${value:04X}")
                    bad_meta_chars += 1

    bad_map_refs = 0
    map_pal_bits = 0
    map_priority_bits = 0
    map_flip_bits = 0
    max_map_ref = 0

    for i in range(0, len(map_data) - 1, 2):
        entry_i = i // 2
        value = read_u16_le(map_data, i)

        ref_num = value & map_index_mask

        # These only make sense in direct 1x1 SNES tilemap mode.
        pal = (value >> 10) & 0x07 if no_metatile_mode else 0
        pri = bool(value & 0x2000) if no_metatile_mode else False

        xflip = bool(value & map_h_flip_mask)
        yflip = bool(value & map_v_flip_mask)

        max_map_ref = max(max_map_ref, ref_num)

        if ref_num >= mt_count:
            if bad_map_refs < args.max_errors:
                if no_metatile_mode:
                    print(f"BAD MAP: entry {entry_i} char {ref_num} >= CHR tiles {tile_count} value=${value:04X}")
                else:
                    print(f"BAD MAP: entry {entry_i} metatile {ref_num} >= metatiles {mt_count} value=${value:04X}")
            bad_map_refs += 1

        if pal:
            map_pal_bits += 1
        if pri:
            map_priority_bits += 1
        if xflip or yflip:
            map_flip_bits += 1

    print()
    print("Summary")
    print("-------")
    print(f"Bad metatile character refs : {bad_meta_chars}")
    print(f"Bad map refs                : {bad_map_refs}")
    print(f"Highest map ref             : {max_map_ref}")
    print(f"Map entries with pal bits   : {map_pal_bits}")
    print(f"Map entries with priority   : {map_priority_bits}")
    print(f"Map entries with flip bits  : {map_flip_bits}")

    if args.png:
        if Image is None:
            print("ERROR: Pillow is not installed. Install with: pip install Pillow")
            errors += 1
        elif not pal_path or not pal_path.exists():
            print("ERROR: cannot create PNG without palette")
            errors += 1
        else:
            png_path = make_png(
                project_file=project_file,
                name=name,
                chr_data=chr_data,
                tile_count=tile_count,
                pal_path=pal_path,
                map_data=map_data,
                metatiles=metatiles,
                mt_w=mt_w,
                mt_h=mt_h,
                width=width,
                height=height,
                no_metatile_mode=no_metatile_mode,
                args=args,
            )
            print(f"PNG written                  : {png_path}")

    errors += bad_meta_chars
    errors += bad_map_refs

    if errors:
        print(f"Result                       : FAILED ({errors} issue(s))")
    else:
        print("Result                       : OK")

    return 1 if errors else 0


def make_png(project_file, name, chr_data, tile_count, pal_path, map_data, metatiles, mt_w, mt_h, width, height, no_metatile_mode, args, map_index_mask, map_h_flip_mask, map_v_flip_mask):
    palette = read_snes_palette(pal_path)

    entries = len(map_data) // 2

    if not width or not height:
        width = args.width if args.width else entries
        height = args.height if args.height else 1

    if width * height > entries:
        height = max(1, entries // width)

    if no_metatile_mode:
        pixel_w = width * 8
        pixel_h = height * 8
    else:
        pixel_w = width * mt_w * 8
        pixel_h = height * mt_h * 8

    img = Image.new("RGBA", (pixel_w, pixel_h), (0, 0, 0, 255))

    for entry in range(min(entries, width * height)):
        value = read_u16_le(map_data, entry * 2)

        map_ref = value & map_index_mask
        map_xflip = bool(value & map_h_flip_mask)
        map_yflip = bool(value & map_v_flip_mask)

        mx = entry % width
        my = entry // width

        if no_metatile_mode:
            tile_img = draw_char(chr_data, tile_count, value, palette)
            img.alpha_composite(tile_img, (mx * 8, my * 8))
        else:
            if map_ref >= len(metatiles):
                continue

            mt = metatiles[map_ref]

            mt_img = Image.new("RGBA", (mt_w * 8, mt_h * 8), (0, 0, 0, 0))

            for slot, tile_value in enumerate(mt):
                tx = slot % mt_w
                ty = slot // mt_w

                tile_img = draw_char(chr_data, tile_count, tile_value, palette)
                mt_img.alpha_composite(tile_img, (tx * 8, ty * 8))

            if map_xflip:
                mt_img = mt_img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if map_yflip:
                mt_img = mt_img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

            img.alpha_composite(mt_img, (mx * mt_w * 8, my * mt_h * 8))

    if args.grid:
        draw = ImageDraw.Draw(img)

        if no_metatile_mode:
            cell_w = 8
            cell_h = 8
        else:
            cell_w = mt_w * 8
            cell_h = mt_h * 8

        for x in range(0, pixel_w, cell_w):
            draw.line((x, 0, x, pixel_h), fill=(255, 255, 255, 80))

        for y in range(0, pixel_h, cell_h):
            draw.line((0, y, pixel_w, y), fill=(255, 255, 255, 80))

    out_dir = Path(args.png_dir) if args.png_dir else Path(project_file).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{Path(project_file).stem}.png"
    img.save(out_path)

    return out_path


def expand_patterns(patterns):
    files = []

    for pattern in patterns:
        matches = glob.glob(pattern)

        if matches:
            files.extend(matches)
        elif Path(pattern).exists():
            files.append(pattern)
        else:
            print(f"WARNING: no match: {pattern}")

    return sorted(set(files))


def main():
    parser = argparse.ArgumentParser(
        description="Validate .m1e Mode1/SNES metatile projects and optionally render PNG previews."
    )

    parser.add_argument("projects", nargs="+", help="One or more .m1e files, supports wildcards")
    parser.add_argument("--tileset", help="Fallback/override metatile size WxH, e.g. 2x2, 4x4, 32x32")
    parser.add_argument("--png", action="store_true", help="Generate PNG preview for each project")
    parser.add_argument("--png-dir", default="", help="Optional output folder for PNG previews")
    parser.add_argument("--grid", action="store_true", help="Overlay metatile grid on PNG")
    parser.add_argument("--width", type=int, default=0, help="Fallback PNG/map width if not present in .m1e")
    parser.add_argument("--height", type=int, default=0, help="Fallback PNG/map height if not present in .m1e")
    parser.add_argument("--max-errors", type=int, default=20, help="Maximum detailed errors to print per category")

    args = parser.parse_args()

    project_files = expand_patterns(args.projects)

    if not project_files:
        print("No .m1e projects found.")
        return 1

    failed = 0

    for project in project_files:
        failed += validate_project(project, args)

    print()
    print("=" * 72)
    print(f"Projects checked : {len(project_files)}")
    print(f"Projects failed  : {failed}")
    print(f"Projects OK      : {len(project_files) - failed}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())