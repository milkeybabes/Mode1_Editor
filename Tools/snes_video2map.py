#!/usr/bin/env python3
import argparse
import glob
import os
import sys


EXPECTED_SIZE = 4096          # 64 * 32 * 2
SCREEN_W = 32
SCREEN_H = 32
FULL_W = 64
FULL_H = 32
WORD_SIZE = 2


def read_words_le(data):
    return [data[i] | (data[i + 1] << 8) for i in range(0, len(data), 2)]


def write_words_le(words):
    out = bytearray()
    for v in words:
        out.append(v & 0xFF)
        out.append((v >> 8) & 0xFF)
    return out


def snes_to_map(words):
    out = [0] * (FULL_W * FULL_H)

    for y in range(SCREEN_H):
        for x in range(SCREEN_W):
            # left 32x32 screen
            src = y * SCREEN_W + x
            dst = y * FULL_W + x
            out[dst] = words[src]

            # right 32x32 screen
            src = (SCREEN_W * SCREEN_H) + y * SCREEN_W + x
            dst = y * FULL_W + (x + SCREEN_W)
            out[dst] = words[src]

    return out


def map_to_snes(words):
    out = [0] * (FULL_W * FULL_H)

    for y in range(SCREEN_H):
        for x in range(SCREEN_W):
            # left half of editor map -> first SNES screen
            src = y * FULL_W + x
            dst = y * SCREEN_W + x
            out[dst] = words[src]

            # right half of editor map -> second SNES screen
            src = y * FULL_W + (x + SCREEN_W)
            dst = (SCREEN_W * SCREEN_H) + y * SCREEN_W + x
            out[dst] = words[src]

    return out


def output_name(path, suffix, out_dir):
    base = os.path.basename(path)
    name, ext = os.path.splitext(base)

    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        return os.path.join(out_dir, f"{name}{suffix}{ext}")

    return os.path.join(os.path.dirname(path), f"{name}{suffix}{ext}")


def process_file(path, mode, out_dir, overwrite):
    if not os.path.isfile(path):
        print(f"SKIP: not a file: {path}")
        return False

    data = open(path, "rb").read()

    if len(data) != EXPECTED_SIZE:
        print(f"SKIP: {path} size {len(data)} bytes, expected {EXPECTED_SIZE}")
        return False

    words = read_words_le(data)

    if mode == "snes2map":
        new_words = snes_to_map(words)
        suffix = "_linear"
    else:
        new_words = map_to_snes(words)
        suffix = "_snes"

    out_path = output_name(path, suffix, out_dir)

    if os.path.exists(out_path) and not overwrite:
        print(f"SKIP: output exists: {out_path}")
        return False

    with open(out_path, "wb") as f:
        f.write(write_words_le(new_words))

    print(f"OK: {path} -> {out_path}")
    return True


def expand_files(patterns):
    files = []

    for pattern in patterns:
        matches = glob.glob(pattern)

        if matches:
            files.extend(matches)
        else:
            files.append(pattern)

    return sorted(set(files))


def main():
    parser = argparse.ArgumentParser(
        description="Convert 64x32 SNES two-screen VRAM tilemaps to/from linear 64x32 editor maps."
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--snes2map", action="store_true", help="Convert SNES VRAM layout to linear 64x32 map")
    mode.add_argument("--map2snes", action="store_true", help="Convert linear 64x32 map to SNES VRAM layout")

    parser.add_argument("files", nargs="+", help="Input .map files, wildcards supported")
    parser.add_argument("--out-dir", default="", help="Optional output folder")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files")

    args = parser.parse_args()

    mode_name = "snes2map" if args.snes2map else "map2snes"
    files = expand_files(args.files)

    if not files:
        print("No files found.")
        return 1

    done = 0
    skipped = 0

    for path in files:
        if process_file(path, mode_name, args.out_dir, args.overwrite):
            done += 1
        else:
            skipped += 1

    print()
    print(f"Converted : {done}")
    print(f"Skipped   : {skipped}")

    return 0 if done else 1


if __name__ == "__main__":
    sys.exit(main())