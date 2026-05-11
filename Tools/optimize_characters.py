import argparse
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


def read_file(filename):
    with open(filename, "rb") as f:
        return f.read()


def write_file(filename, data):
    with open(filename, "wb") as f:
        f.write(data)


def read_metatile_words(filename):
    data = read_file(filename)

    if len(data) % 2 != 0:
        raise ValueError(f"{filename}: metatile file size is not divisible by 2")

    count = len(data) // 2
    return list(struct.unpack("<" + "H" * count, data))


def write_metatile_words(filename, words):
    with open(filename, "wb") as f:
        f.write(struct.pack("<" + "H" * len(words), *words))


def split_characters(data, char_size):
    if len(data) % char_size != 0:
        raise ValueError(
            f"Character file size {len(data)} is not divisible by character size {char_size}"
        )

    chars = []
    for i in range(0, len(data), char_size):
        chars.append(data[i:i + char_size])
    return chars


def main():
    parser = argparse.ArgumentParser(
        description="Optimize SNES Mode1 character set by scanning 2x2 metatile data and rewriting character indices"
    )

    parser.add_argument("characters", help="Character binary file")
    parser.add_argument("metatiles", help="Metatile binary file")
    parser.add_argument("--char-size", type=int, default=32,
                        help="Bytes per character (default: 32 for 4bpp 8x8 SNES tiles)")
    parser.add_argument("--outdir", default="optimized", help="Output directory")
    parser.add_argument("--keep-zero", action="store_true", help="Always keep character 0")
    parser.add_argument("--dry-run", action="store_true", help="Do not write output files")
    args = parser.parse_args()

    # SNES Mode1 baseline assumptions:
    # - metatile = 2x2 = 4 tile entries
    # - tile entry = 16-bit little-endian
    # - character number is in low 10 bits
    # - upper bits preserved
    CHAR_MASK = 0x03FF
    ATTR_MASK = 0xFC00
    METATILE_SIZE = 8

    metatile_data = read_file(args.metatiles)
    if len(metatile_data) % METATILE_SIZE != 0:
        raise ValueError(
            f"{args.metatiles}: metatile file size {len(metatile_data)} is not divisible by {METATILE_SIZE}"
        )

    metatile_words = read_metatile_words(args.metatiles)
    total_metatiles = len(metatile_data) // METATILE_SIZE
    total_entries = len(metatile_words)

    print(f"Metatile file       : {args.metatiles}")
    print(f"Total metatiles      : {total_metatiles}")
    print(f"Total tile entries   : {total_entries}")

    used_chars = set()

    for word in metatile_words:
        char_id = word & CHAR_MASK
        used_chars.add(char_id)

    if args.keep_zero:
        used_chars.add(0)

    if not used_chars:
        print("No character references found")
        return

    used_chars = sorted(used_chars)

    print("\nCharacter usage:")
    print(f"  Unique used chars  : {len(used_chars)}")
    print(f"  Lowest used ID     : {used_chars[0]}")
    print(f"  Highest used ID    : {used_chars[-1]}")

    char_data = read_file(args.characters)
    characters = split_characters(char_data, args.char_size)
    total_chars = len(characters)

    print(f"  Total available    : {total_chars}")

    max_used = max(used_chars)
    if max_used >= total_chars:
        raise ValueError(
            f"Metatile data references character {max_used}, but character file only contains {total_chars} entries"
        )

    remap = {}
    new_characters = []

    for new_id, old_id in enumerate(used_chars):
        remap[old_id] = new_id
        new_characters.append(characters[old_id])

    print(f"  Optimized total    : {len(new_characters)}")

    new_metatile_words = []
    for word in metatile_words:
        old_char = word & CHAR_MASK
        attrs = word & ATTR_MASK
        new_char = remap[old_char]
        new_word = attrs | new_char
        new_metatile_words.append(new_word)

    if args.dry_run:
        print("\nDry run complete. No files written.")
        return

    os.makedirs(args.outdir, exist_ok=True)

    print("\nCreating backups...")
    make_backup(args.characters)
    make_backup(args.metatiles)

    chars_out = os.path.join(args.outdir, "characters_optimized.bin")
    with open(chars_out, "wb") as f:
        for ch in new_characters:
            f.write(ch)
    print(f"\nWrote: {chars_out}")

    metatiles_out = os.path.join(args.outdir, "metatiles_optimized.bin")
    write_metatile_words(metatiles_out, new_metatile_words)
    print(f"Wrote: {metatiles_out}")

    report_path = os.path.join(args.outdir, "report_characters.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("Character Optimization Report\n")
        f.write("=============================\n\n")
        f.write(f"Source character file : {args.characters}\n")
        f.write(f"Source metatile file  : {args.metatiles}\n")
        f.write(f"Character size        : {args.char_size}\n")
        f.write(f"Original characters   : {total_chars}\n")
        f.write(f"Used characters       : {len(used_chars)}\n")
        f.write(f"Optimized characters  : {len(new_characters)}\n")
        f.write(f"Metatiles processed   : {total_metatiles}\n\n")

        f.write("Remap (old -> new):\n")
        for old_id in used_chars:
            f.write(f"{old_id} -> {remap[old_id]}\n")

    print(f"Wrote: {report_path}")


if __name__ == "__main__":
    main()