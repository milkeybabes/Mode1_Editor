#!/usr/bin/env python3
import argparse
import shutil
from pathlib import Path


TILE_SIZE = 32


def parse_int(value: str) -> int:
    value = value.strip()
    if value.startswith("$"):
        return int(value[1:], 16)
    return int(value, 0)


def check_sf4_size(path: Path, data: bytes):
    if len(data) % TILE_SIZE != 0:
        raise ValueError(
            f"{path} size is {len(data)} bytes, not a multiple of {TILE_SIZE}"
        )


def make_backup(path: Path) -> Path:
    backup = path.with_name(path.stem + "_backup" + path.suffix)
    shutil.copy2(path, backup)
    return backup


def main():
    parser = argparse.ArgumentParser(
        description="Insert/overwrite a limited number of SNES .sf4 tiles into another .sf4 at a character slot."
    )

    parser.add_argument("larger_sf4", help="Target .sf4 file to modify in-place")
    parser.add_argument("insert_sf4", help="Source .sf4 file to insert")
    parser.add_argument("char_number", help="Destination character number. Decimal, 0xHEX, or $HEX")
    parser.add_argument("quantity", help="Number of tiles to copy from insert file. Decimal, 0xHEX, or $HEX")

    parser.add_argument(
        "--source-offset",
        type=parse_int,
        default=0,
        help="Optional starting tile inside insert_sf4. Default: 0"
    )

    parser.add_argument(
        "--max-chars",
        type=parse_int,
        default=1024,
        help="Maximum allowed characters after insert. Default: 1024"
    )

    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create Larger_backup.sf4"
    )

    args = parser.parse_args()

    larger_path = Path(args.larger_sf4)
    insert_path = Path(args.insert_sf4)

    char_number = parse_int(args.char_number)
    quantity = parse_int(args.quantity)
    source_offset = args.source_offset

    if not larger_path.is_file():
        raise FileNotFoundError(f"Target file not found: {larger_path}")

    if not insert_path.is_file():
        raise FileNotFoundError(f"Insert file not found: {insert_path}")

    if char_number < 0:
        raise ValueError("Character number cannot be negative")

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero")

    if source_offset < 0:
        raise ValueError("Source offset cannot be negative")

    larger_data = bytearray(larger_path.read_bytes())
    insert_data = insert_path.read_bytes()

    check_sf4_size(larger_path, larger_data)
    check_sf4_size(insert_path, insert_data)

    original_tiles = len(larger_data) // TILE_SIZE
    insert_total_tiles = len(insert_data) // TILE_SIZE

    if source_offset >= insert_total_tiles:
        raise ValueError(
            f"Source offset {source_offset} is beyond insert file tile count {insert_total_tiles}"
        )

    available = insert_total_tiles - source_offset

    if quantity > available:
        raise ValueError(
            f"Quantity {quantity} exceeds available insert tiles {available} "
            f"from source offset {source_offset}"
        )

    start_tile = char_number
    end_tile = start_tile + quantity

    if end_tile > args.max_chars:
        raise ValueError(
            f"Insert would exceed max chars: end tile {end_tile} > {args.max_chars}"
        )

    needed_size = end_tile * TILE_SIZE

    if len(larger_data) < needed_size:
        pad_bytes = needed_size - len(larger_data)
        larger_data.extend(b"\x00" * pad_bytes)
    else:
        pad_bytes = 0

    source_byte_offset = source_offset * TILE_SIZE
    insert_bytes = insert_data[source_byte_offset:source_byte_offset + quantity * TILE_SIZE]

    dest_byte_offset = start_tile * TILE_SIZE
    larger_data[dest_byte_offset:dest_byte_offset + len(insert_bytes)] = insert_bytes

    if not args.no_backup:
        backup_path = make_backup(larger_path)
        print(f"Backup written : {backup_path}")

    larger_path.write_bytes(larger_data)

    final_tiles = len(larger_data) // TILE_SIZE

    print(f"Target          : {larger_path}")
    print(f"Insert          : {insert_path}")
    print(f"Original tiles  : {original_tiles}")
    print(f"Insert total    : {insert_total_tiles}")
    print(f"Source offset   : ${source_offset:03X} ({source_offset})")
    print(f"Quantity copied : {quantity}")
    print(f"Insert slot     : ${start_tile:03X} ({start_tile})")
    print(f"End slot        : ${end_tile - 1:03X} ({end_tile - 1})")
    print(f"Padded bytes    : {pad_bytes}")
    print(f"Final tiles     : {final_tiles}")
    print("Status          : OK")


if __name__ == "__main__":
    main()