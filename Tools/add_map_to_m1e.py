#!/usr/bin/env python3
import argparse
import os
import shutil
import sys


def backup_file(path):
    base, ext = os.path.splitext(path)
    backup = f"{base}_backup{ext}"
    shutil.copy2(path, backup)
    return backup


def split_csv(value):
    return [p.strip() for p in value.split(",") if p.strip()]


def validate_map(map_path, width):
    size = os.path.getsize(map_path)

    if size % 2 != 0:
        raise ValueError(f"map size is not even: {size} bytes")

    row_bytes = width * 2

    if size % row_bytes != 0:
        raise ValueError(
            f"map size {size} is not divisible by width {width} "
            f"({row_bytes} bytes per row)"
        )

    height = size // row_bytes
    return size, height


def find_key_line(lines, key):
    key_l = key.lower()
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if stripped.startswith(key_l + "="):
            return i
    return None


def get_key_values(lines, key):
    i = find_key_line(lines, key)
    if i is None:
        return []
    return split_csv(lines[i].split("=", 1)[1])


def set_key_line(lines, key, values):
    text = f"{key}={','.join(values)}"

    # replace map or maps with maps
    if key == "maps":
        i_maps = find_key_line(lines, "maps")
        i_map = find_key_line(lines, "map")

        if i_maps is not None:
            lines[i_maps] = text
            if i_map is not None:
                del lines[i_map]
            return

        if i_map is not None:
            lines[i_map] = text
            return

    i = find_key_line(lines, key)
    if i is not None:
        lines[i] = text
    else:
        lines.append(text)


def update_project(project_path, new_map_path, new_width):
    with open(project_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    size, new_height = validate_map(new_map_path, new_width)

    maps = get_key_values(lines, "maps")

    if not maps:
        maps = get_key_values(lines, "map")

    widths = get_key_values(lines, "width")
    heights = get_key_values(lines, "height")

    if not maps:
        raise ValueError("no map= or maps= line found in project")

    if len(widths) == 1 and len(maps) > 1:
        widths = widths * len(maps)

    if len(heights) == 1 and len(maps) > 1:
        heights = heights * len(maps)

    if widths and len(widths) != len(maps):
        raise ValueError(
            f"width count mismatch: {len(widths)} width value(s), {len(maps)} map(s)"
        )

    if heights and len(heights) != len(maps):
        raise ValueError(
            f"height count mismatch: {len(heights)} height value(s), {len(maps)} map(s)"
        )

    new_map_name = os.path.basename(new_map_path)

    maps.append(new_map_name)
    widths.append(str(new_width))
    heights.append(str(new_height))

    set_key_line(lines, "maps", maps)
    set_key_line(lines, "width", widths)
    set_key_line(lines, "height", heights)

    backup = backup_file(project_path)

    with open(project_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Project : {project_path}")
    print(f"Backup  : {backup}")
    print(f"Added   : {new_map_name}")
    print(f"Width   : {new_width}")
    print(f"Height  : {new_height}")
    print(f"Size    : {size} bytes")
    print("Done.")


def main():
    parser = argparse.ArgumentParser(
        description="Add a map to an existing .m1e project maps/width/height lists."
    )
    parser.add_argument("project", help="Existing .m1e file")
    parser.add_argument("mapfile", help="New .map file to add")
    parser.add_argument("width", type=int, help="Width of the new map in entries")

    args = parser.parse_args()

    if not os.path.isfile(args.project):
        print(f"ERROR: project not found: {args.project}")
        return 1

    if not os.path.isfile(args.mapfile):
        print(f"ERROR: map file not found: {args.mapfile}")
        return 1

    try:
        update_project(args.project, args.mapfile, args.width)
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())