#!/usr/bin/env python3
"""
m1e_backup.py

Create a tidy backup/export folder for one or more Mode1 Editor .m1e projects.

Usage:
    python m1e_backup.py source destination_folder

Examples:
    python m1e_backup.py Alien3.m1e Backup
    python m1e_backup.py "*.m1e" Backup
    python m1e_backup.py "Projects/*.m1e" Backup

Output layout:
    destination_folder/
        palettes/
        tiles/
        metatiles/
        maps/
        ProjectName.m1e

The script:
- Copies only files referenced by the .m1e project
- Strips source subfolders from asset filenames
- Rewrites .m1e paths to the tidy backup folders
- Supports maps= and old map=
- Supports preview_bg2_map=
- Avoids copying duplicate files repeatedly
"""

import argparse
import glob
import shutil
from pathlib import Path


ASSET_FOLDERS = {
    "palette": "palettes",
    "tiles": "tiles",
    "metatiles": "metatiles",
    "map": "maps",
    "maps": "maps",
    "preview_bg2_map": "maps",
}


def read_project(path: Path) -> tuple[list[str], dict[str, str]]:
    """Read .m1e file preserving line order."""
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    data: dict[str, str] = {}

    for line in lines:
        stripped = line.strip()

        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue

        if "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        data[key.strip()] = value.strip()

    return lines, data


def write_project(path: Path, lines: list[str], replacements: dict[str, str]) -> None:
    """Write .m1e file preserving unknown/comment lines and replacing known keys."""
    out: list[str] = []

    for line in lines:
        stripped = line.strip()

        if not stripped or stripped.startswith("#") or stripped.startswith(";") or "=" not in stripped:
            out.append(line)
            continue

        key, _value = stripped.split("=", 1)
        key = key.strip()

        if key in replacements:
            out.append(f"{key}={replacements[key]}")
        else:
            out.append(line)

    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def resolve_source_path(project_dir: Path, value: str) -> Path:
    """Resolve relative asset path against the .m1e folder."""
    src = Path(value)

    if src.is_absolute():
        return src

    return project_dir / src


def copy_asset(
    project_path: Path,
    value: str,
    dest_root: Path,
    subfolder: str,
    copied: dict[Path, Path],
    missing: list[str],
) -> str:
    """
    Copy one asset to the tidy backup folder.

    Returns the rewritten project-relative path.
    """
    project_dir = project_path.parent
    src = resolve_source_path(project_dir, value)

    filename = src.name
    dest_dir = dest_root / subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = dest_dir / filename

    if not src.exists():
        missing.append(str(src))
        return f"{subfolder}/{filename}"

    src_real = src.resolve()

    if src_real not in copied:
        shutil.copy2(src, dest)
        copied[src_real] = dest

    return f"{subfolder}/{filename}"


def backup_project(project_path: Path, dest_root: Path) -> None:
    lines, data = read_project(project_path)

    copied: dict[Path, Path] = {}
    missing: list[str] = []
    replacements: dict[str, str] = {}

    # Single-file asset entries
    for key in ("palette", "tiles", "metatiles", "preview_bg2_map"):
        if key not in data:
            continue

        value = data[key].strip()

        if not value:
            continue

        replacements[key] = copy_asset(
            project_path=project_path,
            value=value,
            dest_root=dest_root,
            subfolder=ASSET_FOLDERS[key],
            copied=copied,
            missing=missing,
        )

    # maps= modern multi-map entry
    if "maps" in data:
        new_maps = []

        for map_value in split_csv(data["maps"]):
            new_maps.append(
                copy_asset(
                    project_path=project_path,
                    value=map_value,
                    dest_root=dest_root,
                    subfolder="maps",
                    copied=copied,
                    missing=missing,
                )
            )

        replacements["maps"] = ",".join(new_maps)

    # map= old single-map entry
    elif "map" in data:
        replacements["map"] = copy_asset(
            project_path=project_path,
            value=data["map"],
            dest_root=dest_root,
            subfolder="maps",
            copied=copied,
            missing=missing,
        )

    dest_root.mkdir(parents=True, exist_ok=True)
    dest_project = dest_root / project_path.name
    write_project(dest_project, lines, replacements)

    print(f"Backed up: {project_path}")
    print(f"  -> {dest_project}")

    if missing:
        print("  WARNING: Missing referenced files:")
        for item in missing:
            print(f"    {item}")


def expand_sources(pattern: str) -> list[Path]:
    matches = glob.glob(pattern)

    if matches:
        return [Path(m) for m in matches if Path(m).is_file() and Path(m).suffix.lower() == ".m1e"]

    p = Path(pattern)

    if p.is_file() and p.suffix.lower() == ".m1e":
        return [p]

    return []


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a tidy backup/export folder for Mode1 Editor .m1e projects."
    )
    parser.add_argument("source", help="Source .m1e file or wildcard, e.g. project.m1e or \"*.m1e\"")
    parser.add_argument("destination_folder", help="Destination backup folder root")

    args = parser.parse_args()

    sources = expand_sources(args.source)

    if not sources:
        print(f"No .m1e files found for: {args.source}")
        return 1

    dest_root = Path(args.destination_folder)

    for project in sources:
        backup_project(project, dest_root)

    print()
    print(f"Done. Projects backed up: {len(sources)}")
    print(f"Backup folder: {dest_root.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
