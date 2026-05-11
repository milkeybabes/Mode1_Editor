# Mode1 Editor Tools

A collection of helper tools for SNES Mode1 `.m1e` projects.

---

## add_map_to_m1e.py

Adds one or more map files into an existing `.m1e` project.

Updates:
- `maps=`
- `width=`
- `height=`

automatically.

---

## add_sf4_tiles.py

Inserts or replaces SNES `.sf4` character tiles into another `.sf4` file
at a specified tile index.

Useful for:
- animated tile insertion
- expanding character sets
- temporary placeholder graphics

---

## m1e_backup.py

Creates a clean portable backup of an `.m1e` project.

Copies:
- maps
- tiles
- palettes
- metatiles

into organised folders.

Useful before optimization or large edits.

---

## m1e_optimize.py

Optimizes `.m1e` projects by removing unused:
- metatiles
- characters

Automatically rewrites:
- maps
- metatile references

Supports:
- dynamic metatile sizes
- keep lists
- dry-run analysis

Example:

```bash
python m1e_optimize.py project.m1e --all
```

---

## make_metatile_map.py

Converts indexed PNG images into SNES Mode1 projects using generated:
- metatiles
- maps
- character data

Supports larger metatile sizes such as:
- 2x2
- 4x4
- 8x8

Useful for real SNES production workflows.

---

## make_metatile_map_1PNG.py

Converts a single indexed PNG into a complete SNES Mode1 project.

Generates:
- map
- metatiles
- tiles
- palette

in one step.

---

## mode1_map_analyzer.py

Analyzes Mode1 maps and reports:
- metatile usage
- character usage
- duplicates
- palette usage
- optimization statistics

Useful before optimization and ROM planning.

---

## reverse_map.py

Reverses map row order between:
- `top_bottom`
- `bottom_top`

Automatically updates:

```ini
map_direction=
```

inside the `.m1e` project.

Useful for converting vertically stored arcade maps.

---

## snes_video2map.py

Converts SNES VRAM-format tilemaps to linear editor maps and back.

Supports:
- SNES 64x32 screen layout
- editor-friendly layouts
- reverse conversion

Useful for VRAM extraction workflows.

---

## validate_m1e_project.py

Validates `.m1e` projects and checks:
- referenced files
- dimensions
- map sizes
- metatile sizes
- project settings

Useful before sharing projects or committing to GitHub.
