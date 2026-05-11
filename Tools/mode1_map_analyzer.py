import sys
import os
import argparse


DEFAULT_INDEX_MASK = 0x0FFF
DEFAULT_X_FLIP_BIT = 0x4000
DEFAULT_Y_FLIP_BIT = 0x8000


def parse_hex_or_dec(value):
    value = value.strip().lower()
    if value.startswith("$"):
        return int(value[1:], 16)
    if value.startswith("0x"):
        return int(value, 16)
    return int(value, 10)


def fmt_hex(value, digits=4):
    return f"${value:0{digits}X}"


def make_ranges(values):
    if not values:
        return []

    values = sorted(values)
    ranges = []

    start = prev = values[0]

    for v in values[1:]:
        if v == prev + 1:
            prev = v
        else:
            ranges.append((start, prev))
            start = prev = v

    ranges.append((start, prev))
    return ranges


def print_ranges(title, values, max_lines=40):
    ranges = make_ranges(values)

    print(title)
    if not ranges:
        print("  None")
        return

    for n, (start, end) in enumerate(ranges):
        if n >= max_lines:
            print(f"  ... {len(ranges) - max_lines} more ranges not shown")
            break

        if start == end:
            print(f"  {fmt_hex(start, 3)} / {start}")
        else:
            print(f"  {fmt_hex(start, 3)}-{fmt_hex(end, 3)} / {start}-{end}")


def analyze_map(path, index_mask, x_flip_bit, y_flip_bit, max_index):
    if not os.path.isfile(path):
        print(f"ERROR: file not found: {path}")
        return 1

    with open(path, "rb") as f:
        data = f.read()

    if len(data) % 2 != 0:
        print(f"ERROR: file size must be even: {len(data)} bytes")
        return 1

    total_entries = len(data) // 2

    used = set()
    raw_values = set()

    x_flip_count = 0
    y_flip_count = 0
    both_flip_count = 0
    nonzero_extra_bits = 0

    extra_mask = 0xFFFF & ~(index_mask | x_flip_bit | y_flip_bit)

    for i in range(0, len(data), 2):
        raw = data[i] | (data[i + 1] << 8)

        index = raw & index_mask
        x_flip = bool(raw & x_flip_bit)
        y_flip = bool(raw & y_flip_bit)

        used.add(index)
        raw_values.add(raw)

        if x_flip:
            x_flip_count += 1
        if y_flip:
            y_flip_count += 1
        if x_flip and y_flip:
            both_flip_count += 1

        if raw & extra_mask:
            nonzero_extra_bits += 1

    if not used:
        print("No entries found.")
        return 0

    lowest = min(used)
    highest = max(used)

    if max_index is None:
        max_index = highest

    used_in_range = {v for v in used if 0 <= v <= max_index}
    unused_0_to_max = set(range(0, max_index + 1)) - used_in_range
    unused_low_to_high = set(range(lowest, highest + 1)) - used

    print(f"File                  : {path}")
    print(f"Size                  : {len(data)} bytes")
    print(f"Entries               : {total_entries}")
    print()
    print(f"Index mask            : {fmt_hex(index_mask)}")
    print(f"X flip bit            : {fmt_hex(x_flip_bit)}")
    print(f"Y flip bit            : {fmt_hex(y_flip_bit)}")
    print(f"Extra bits mask       : {fmt_hex(extra_mask)}")
    print()
    print(f"Lowest metatile used  : {fmt_hex(lowest, 3)} / {lowest}")
    print(f"Highest metatile used : {fmt_hex(highest, 3)} / {highest}")
    print(f"Unique metatiles used : {len(used)}")
    print(f"Unused 0-highest      : {len(set(range(0, highest + 1)) - used)}")
    print(f"Unused 0-max          : {len(unused_0_to_max)}   max={fmt_hex(max_index, 3)} / {max_index}")
    print()
    print(f"X flip entries        : {x_flip_count}")
    print(f"Y flip entries        : {y_flip_count}")
    print(f"Both flip entries     : {both_flip_count}")
    print(f"Entries with extra bits: {nonzero_extra_bits}")

    print()
    print_ranges("Unused metatiles between lowest and highest:", unused_low_to_high)

    print()
    print_ranges(f"Unused metatiles from 0 to {fmt_hex(max_index, 3)}:", unused_0_to_max)

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Mode1 metatile map usage, ignoring map flip bits."
    )

    parser.add_argument("map_file", help="Input .map file")
    parser.add_argument(
        "--index-mask",
        default="0x0FFF",
        help="Mask used to extract metatile index. Default: 0x0FFF",
    )
    parser.add_argument(
        "--xflip-bit",
        default="0x4000",
        help="X flip bit in map word. Default: 0x4000",
    )
    parser.add_argument(
        "--yflip-bit",
        default="0x8000",
        help="Y flip bit in map word. Default: 0x8000",
    )
    parser.add_argument(
        "--max-index",
        default=None,
        help="Optional maximum metatile number to check for unused entries.",
    )

    args = parser.parse_args()

    index_mask = parse_hex_or_dec(args.index_mask)
    x_flip_bit = parse_hex_or_dec(args.xflip_bit)
    y_flip_bit = parse_hex_or_dec(args.yflip_bit)
    max_index = parse_hex_or_dec(args.max_index) if args.max_index else None

    return analyze_map(
        args.map_file,
        index_mask,
        x_flip_bit,
        y_flip_bit,
        max_index,
    )


if __name__ == "__main__":
    sys.exit(main())