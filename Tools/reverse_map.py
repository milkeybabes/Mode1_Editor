import sys
import os


def reverse_map(path, width):
    if not os.path.isfile(path):
        print(f"File not found: {path}")
        return False

    with open(path, "rb") as f:
        data = bytearray(f.read())

    if len(data) % 2 != 0:
        print("Error: map file must be even length (2 bytes per tile)")
        return False

    total_tiles = len(data) // 2

    if total_tiles % width != 0:
        print(f"Error: width {width} does not divide total tiles {total_tiles}")
        return False

    height = total_tiles // width
    print(f"Map size: {width} x {height}")

    # Create backup
    base, ext = os.path.splitext(path)
    backup_path = f"{base}_backup{ext}"

    with open(backup_path, "wb") as f:
        f.write(data)

    print(f"Backup created: {backup_path}")

    # Reverse rows
    row_size = width * 2
    new_data = bytearray(len(data))

    for y in range(height):
        src_offset = y * row_size
        dst_offset = (height - 1 - y) * row_size

        new_data[dst_offset:dst_offset + row_size] = \
            data[src_offset:src_offset + row_size]

    # Write reversed map back
    with open(path, "wb") as f:
        f.write(new_data)

    print(f"Reversed: {path}")

    return True


def toggle_map_direction(m1e_path):
    if not os.path.isfile(m1e_path):
        print(f".m1e file not found: {m1e_path}")
        return

    with open(m1e_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    found = False
    new_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("map_direction="):
            current = stripped.split("=", 1)[1].strip()

            if current == "top_bottom":
                new_line = "map_direction=bottom_top\n"
            else:
                new_line = "map_direction=top_bottom\n"

            print(f"Toggled map_direction: {current} -> {new_line.strip().split('=')[1]}")

            new_lines.append(new_line)
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append("map_direction=bottom_top\n")
        print("Added: map_direction=bottom_top")

    # Backup .m1e
    base, ext = os.path.splitext(m1e_path)
    backup_path = f"{base}_backup{ext}"

    with open(backup_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"Backup created: {backup_path}")

    with open(m1e_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"Updated: {m1e_path}")


def parse_maps(m1e_path):
    with open(m1e_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    maps = []
    widths = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("maps="):
            maps = [
                x.strip()
                for x in stripped.split("=", 1)[1].split(",")
            ]

        elif stripped.startswith("width="):
            widths = [
                int(x.strip())
                for x in stripped.split("=", 1)[1].split(",")
            ]

    return maps, widths


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python reverse_map.py project.m1e")
        sys.exit(1)

    m1e_file = sys.argv[1]

    if not os.path.isfile(m1e_file):
        print(f"File not found: {m1e_file}")
        sys.exit(1)

    maps, widths = parse_maps(m1e_file)

    if not maps:
        print("No maps= found in .m1e")
        sys.exit(1)

    if not widths:
        print("No width= found in .m1e")
        sys.exit(1)

    if len(widths) == 1 and len(maps) > 1:
        widths = widths * len(maps)

    if len(maps) != len(widths):
        print("Error: maps count does not match width count")
        sys.exit(1)

    project_dir = os.path.dirname(os.path.abspath(m1e_file))

    for map_name, width in zip(maps, widths):
        map_path = os.path.join(project_dir, map_name)

        print()
        print(f"Processing: {map_name}")
        reverse_map(map_path, width)

    print()
    toggle_map_direction(m1e_file)

    print()
    print("Done.")