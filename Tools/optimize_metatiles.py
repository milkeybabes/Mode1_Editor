import argparse
import glob
import os
import shutil
import struct


def make_backup(filepath):
    if not os.path.exists(filepath):
        return

    base, ext = os.path.splitext(filepath)
    backup_path = base + "_backup" + ext

    if not os.path.exists(backup_path):
        shutil.copy2(filepath, backup_path)
        print(f"Backup created: {backup_path}")
        return

    i = 1
    while True:
        backup_path = f"{base}_backup_{i:03d}{ext}"
        if not os.path.exists(backup_path):
            shutil.copy2(filepath, backup_path)
            print(f"Backup created: {backup_path}")
            return
        i += 1


def read_map(filename):
    with open(filename, "rb") as f:
        data = f.read()

    if len(data) % 2 != 0:
        raise ValueError(f"{filename}: map size not divisible by 2")

    count = len(data) // 2
    return list(struct.unpack("<" + "H" * count, data))


def write_map(filename, values):
    with open(filename, "wb") as f:
        f.write(struct.pack("<" + "H" * len(values), *values))


def read_metatiles(filename, metatile_size):
    with open(filename, "rb") as f:
        data = f.read()

    if len(data) % metatile_size != 0:
        raise ValueError(
            f"{filename}: metatile file size {len(data)} is not divisible by metatile size {metatile_size}"
        )

    count = len(data) // metatile_size
    metatiles = []

    for i in range(count):
        start = i * metatile_size
        end = start + metatile_size
        metatiles.append(data[start:end])

    return metatiles


def write_metatiles(filename, metatiles):
    with open(filename, "wb") as f:
        for m in metatiles:
            f.write(m)


def main():
    parser = argparse.ArgumentParser(
        description="Optimize 2x2 SNES Mode1 metatiles by scanning one or more 16-bit map files"
    )

    parser.add_argument("metatiles", help="Metatile binary file")
    parser.add_argument("maps", help='Map wildcard, e.g. "maps\\*.bin"')
    parser.add_argument("--outdir", default="optimized", help="Output directory")
    parser.add_argument("--keep-zero", action="store_true", help="Always keep metatile 0")
    parser.add_argument("--dry-run", action="store_true", help="Do not write output files")
    args = parser.parse_args()

    # Baseline format:
    # - maps use 16-bit little-endian metatile indices
    # - metatiles are 2x2 tiles
    # - each tile entry is 16-bit
    # - 4 entries per metatile = 8 bytes
    METATILE_SIZE = 8

    map_files = sorted(glob.glob(args.maps))
    if not map_files:
        print("No map files found")
        return

    print("Maps found:")
    for m in map_files:
        print(" ", m)

    # Read all maps and collect used metatiles
    used = set()
    map_data = {}

    for m in map_files:
        values = read_map(m)
        map_data[m] = values
        used.update(values)

    if args.keep_zero:
        used.add(0)

    if not used:
        print("No metatile references found in maps")
        return

    used = sorted(used)

    print("\nMetatile usage:")
    print(f"  Unique used metatiles: {len(used)}")
    print(f"  Lowest used ID       : {used[0]}")
    print(f"  Highest used ID      : {used[-1]}")

    metatiles = read_metatiles(args.metatiles, METATILE_SIZE)
    total_metatiles = len(metatiles)

    print(f"  Total available      : {total_metatiles}")

    max_used = max(used)
    if max_used >= total_metatiles:
        raise ValueError(
            f"Map references metatile {max_used}, but metatile file only contains {total_metatiles} entries"
        )

    # Build remap in ascending old ID order
    remap = {}
    new_metatiles = []

    for new_id, old_id in enumerate(used):
        remap[old_id] = new_id
        new_metatiles.append(metatiles[old_id])

    print(f"  Optimized total      : {len(new_metatiles)}")

    if args.dry_run:
        print("\nDry run complete. No files written.")
        return

    os.makedirs(args.outdir, exist_ok=True)

    print("\nCreating backups...")
    make_backup(args.metatiles)
    for m in map_files:
        make_backup(m)

    # Write optimized metatile file
    metatile_out = os.path.join(args.outdir, "metatiles_optimized.bin")
    write_metatiles(metatile_out, new_metatiles)
    print(f"\nWrote: {metatile_out}")

    # Rewrite all maps
    for m, values in map_data.items():
        new_values = [remap[v] for v in values]
        out_name = os.path.join(args.outdir, os.path.basename(m))
        write_map(out_name, new_values)
        print(f"Wrote: {out_name}")

    # Write report
    report_path = os.path.join(args.outdir, "report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("Metatile Optimization Report\n")
        f.write("============================\n\n")
        f.write(f"Source metatile file : {args.metatiles}\n")
        f.write(f"Map wildcard         : {args.maps}\n")
        f.write(f"Maps processed       : {len(map_files)}\n")
        f.write(f"Original metatiles   : {total_metatiles}\n")
        f.write(f"Used metatiles       : {len(used)}\n")
        f.write(f"Optimized metatiles  : {len(new_metatiles)}\n\n")

        f.write("Maps:\n")
        for m in map_files:
            f.write(f"  {m}\n")

        f.write("\nRemap (old -> new):\n")
        for old_id in used:
            f.write(f"{old_id} -> {remap[old_id]}\n")

    print(f"Wrote: {report_path}")


if __name__ == "__main__":
    main()