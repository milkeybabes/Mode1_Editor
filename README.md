# Mode1 Editor – Feature Reference

A SNES Mode 1 metatile editor focused on practical workflow, large map editing, and real-world game development layouts.

Designed for:
- SNES homebrew
- ROM hacking
- Arcade-to-SNES conversions
- Large scrolling tilemaps
- Multi-layer background workflows
- Metatile-based level construction

---

# Features

## Project System

- Load and save `.m1e` project files
- Multiple maps per project
- Shared:
  - Palette (`.pal`)
  - Character graphics (`.sf4`)
  - Metatiles (`.mtl`)
- Per-map width and height support
- Supports both modern and older single-map project formats

---

# Tile Editing

## Character Editor

- Edit SNES 4bpp character graphics
- Pixel-level drawing
- Palette-aware editing
- Real-time updates

## Tile Operations

- Flip X
- Flip Y
- Rotate clockwise
- Rotate anticlockwise
- Invert tile
- Clear tile
- Copy / paste tile

---

# Metatile Editing

## Dynamic Metatile Sizes

Supports:
- 2×2
- 4×4
- Larger layouts

## Features

- Palette selection
- Flip flags
- Priority flags
- Subtile editing
- Direct visual editing

---

# Map Editing

## Painting

- Single metatile paint
- Multi-tile brush stamping
- Ghost preview before placement
- Drag painting
- Copy area as reusable brush

## Brush System

- Copy rectangular regions
- Preserve:
  - palette
  - flips
  - priority
- Multi-tile stamping

## Picking

- Right-click pick from map
- Copies:
  - tile
  - palette
  - flip flags
  - priority

---

# Map Navigation

## Zoom Levels

Supports:
- Zoom in
- Zoom out
- Fit-to-window
- Fractional zoom
- Large map overview editing

## Panning

- Middle mouse drag
- Space + drag alternative

## Grid Overlay

Toggle between:
- Off
- Metatile grid
- Larger region grid

---

# BG Preview System

## Dual Background Preview

Preview:
- BG1
- BG2
- Combined layers

## Parallax Preview

Supports:
- Independent X/Y scroll ratios
- Linked parallax mode
- Relative BG2 movement

## Movement Modes

- Move BG1
- Move BG2
- Move both
- Move BG1 with linked BG2 parallax

## Position Helpers

- Clamped scrolling
- Snap movement
- Axis locking
- Reset positions

---

# BG2 Support

## Project BG2 Maps

Supports assigning a dedicated map as BG2:
- Shared background map across multiple levels
- Repeating backgrounds
- Decorative background layers

## SNES VRAM Layout Support

Supports:
- Standard layouts
- SNES-style 32×64 storage converted to 64×32 display

Useful for:
- Earthworm Jim
- Contra III
- Similar SNES workflows

---

# Repeat Modes

BG2 supports:
- Fixed repeat counts
- Automatic fill mode
- Horizontal repeat
- Vertical repeat

Useful for:
- Parallax skies
- Forest lines
- Mountains
- Horizon layers

---

# Undo System

Supports:
- Map undo
- Character undo
- Multi-tile paint undo

---

# Palette System

## SNES Native Palette Support

- SNES 15-bit colour
- Quantised editing
- Palette group selection
- Real-time preview

## Palette Controls

- RGB sliders
- Colour preview
- Copy / paste colours

---

# Supported Formats

| Format | Purpose |
|---|---|
| `.m1e` | Project file |
| `.map` | Tilemap |
| `.mtl` | Metatile definitions |
| `.sf4` | SNES 4bpp graphics |
| `.pal` | SNES palette |

---

# Workflow Features

## Designed For Large Projects

- Large scrolling maps
- Multi-map projects
- Shared BG systems
- Reusable metatile libraries

## Fast Editing Workflow

- Hover previews
- Brush reuse
- Quick picking
- Keyboard shortcuts
- Real-time rendering

---

# Keyboard Shortcuts

## General

| Key | Function |
|---|---|
| `H` | Help |
| `P` | Toggle metatile picker |
| `ESC` | Close picker |

---

## Map Editor

| Key | Function |
|---|---|
| `X` | Flip X |
| `Y` | Flip Y |
| `Ctrl+Z` | Undo |
| `U` | Undo map paint |

---

## Tile Editor

| Key | Function |
|---|---|
| `X` | Flip X |
| `Y` | Flip Y |
| `R` | Rotate clockwise |
| `Shift+R` | Rotate anticlockwise |
| `Delete` | Clear tile |
| `I` | Invert tile |
| `C` | Copy tile |
| `V` | Paste tile |

---

## BG Preview

| Key | Function |
|---|---|
| `1` | Move BG1 |
| `2` | Move BG2 |
| `3` | Move both |
| `4` | Move BG1 with BG2 parallax |
| `S` | Swap BG priority |
| `R` | Reset positions |

---

# Notes

- Colour 0 is treated as transparent in BG preview
- Supports direct tilemap mode
- Supports SNES-style map entry flags
- Built around practical SNES workflows rather than generic tile editing
- Designed for responsiveness even with large maps

---

# .m1e Project File Examples

This section shows real-world `.m1e` project examples used by the editor.

The examples below demonstrate:
- Multi-map projects
- Shared graphics/palette workflows
- SNES metatile projects
- BG2 parallax preview systems
- Direct SNES tilemap support
- Custom flip bit layouts
- Shared background maps

---

# Example 1 — Standard Multi-Map Project

```ini
palette=Alien3.pal
```

SNES palette file used by the project.

```ini
tiles=Alien3.sf4
```

SNES 4bpp character graphics file.

```ini
metatiles=Alien3.mtl
```

Metatile definition file.

```ini
metatile_size=4
```

Each metatile is 4×4 SNES tiles (32×32 pixels).

Supported values:
- 1 = direct SNES tilemap mode
- 2 = 2×2 metatiles
- 4 = 4×4 metatiles

```ini
maps=maps/Area1.map,maps/Area2.map,maps/Area3.map
```

Multiple maps in a single project.

All maps share:
- tiles
- palettes
- metatiles

```ini
width=128,96,64
```

Width of each map in metatiles.

Each entry corresponds to the matching map.

```ini
height=32,32,32
```

Height of each map in metatiles.

```ini
map_direction=top_bottom
```

Defines map storage direction.

Supported values:
- `top_bottom`
- `bottom_top`

Useful for matching original game storage layouts.

```ini
map_index_mask=0x03FF
```

Mask used to extract the metatile index from map entries.

Example:
- `0x03FF` = lower 10 bits used for tile index

Important when games store:
- flip bits
- priority bits
- palette bits

inside the same word.

```ini
map_h_flip_bit=14
map_v_flip_bit=15
```

Defines which bits contain:
- horizontal flip
- vertical flip

Default SNES layout:
- bit 14 = X flip
- bit 15 = Y flip

Can be changed for non-standard engines.

---

# Example 2 — Shared BG2 Parallax Project

```ini
palette=Barrel_Cannon_Canyon.pal
tiles=Barrel_Cannon_Canyon.sf4
metatiles=Barrel_Cannon_Canyon.mtl
```

Shared project assets.

---

```ini
metatile_size=4
```

4×4 metatile editing mode.

---

```ini
maps=maps/Barrel_Cannon_Canyon.map,maps/Jungle_BG2.map,maps/Jungle_Hijinxs.map,maps/Jungle_Hijinxs_Bonus_2.map,maps/Orang_utan_Gang.map,maps/Ropey_Rampage.map
```

Project contains:
- gameplay maps
- a dedicated shared BG2 map

In this setup:
- `Jungle_BG2.map` is reused as the parallax background for multiple levels.

---

```ini
width=334,16,168,8,303,260
height=16
```

Map dimensions.

If only one height value is supplied:
- it is reused for all maps.

---

```ini
map_direction=top_bottom
```

Maps are stored column-by-column.

---

```ini
map_index_mask=0x03FF
map_h_flip_bit=14
map_v_flip_bit=15
```

Standard SNES-style tile entry layout.

---

# BG2 Preview System

```ini
preview_bg2_mode=project_map
```

Uses another project map as BG2.

Supported modes:
- `direct`
- `project_map`

`project_map` allows:
- shared parallax backgrounds
- reusable sky layers
- repeating forest backgrounds
- decorative BG layers

---

```ini
preview_bg2_map=maps/Jungle_BG2.map
```

Defines which map should be used as BG2.

---

```ini
preview_bg2_scroll_x=0.5
preview_bg2_scroll_y=0.25
```

Parallax scroll ratios.

Examples:
- `1.0` = same speed as BG1
- `0.5` = half speed
- `0.25` = quarter speed

Useful for:
- depth simulation
- distant backgrounds
- horizon layers

---

```ini
preview_bg2_repeat_x=fill
```

Automatically repeats BG2 horizontally until the preview window is filled.

Supported values:
- integer repeat count
- `fill`

---

```ini
preview_bg2_repeat_y=1
```

Vertical repeat count.

---

```ini
preview_bg2_min_y=-32
```

Allows BG2 to move above normal zero position.

Useful because many real games:
- offset backgrounds vertically
- keep sky layers higher than gameplay maps
- avoid wasting map rows on empty space

---

# Direct Tilemap Mode

```ini
metatile_size=1
```

Special mode:
- disables metatiles
- uses raw SNES tilemap entries directly

In this mode:
- metatiles are ignored
- SNES tile bits are used directly
- map entries behave like native SNES tilemap words

Useful for:
- direct VRAM editing
- debugging
- raw SNES tilemaps
- engines without metatile systems

---

# Notes

## Width / Height Rules

If fewer width or height values are supplied than maps:
- the final value is repeated automatically.

---

## Map Validation

The editor automatically checks:
- map sizes
- metatile limits
- invalid masks
- incompatible settings

Warnings are shown when:
- masks are too small
- maps are wrong sizes
- unsupported values are used

---

## Recommended Workflow

Typical setup:
- shared tiles
- shared palettes
- shared metatiles
- multiple maps
- optional shared BG2 map

This mirrors many real SNES game workflows.


---

# Example 3 — Direct SNES BG2 Layout Mode

This example demonstrates using a raw SNES-style BG2 tilemap directly from VRAM-style data.

Useful for games which store BG2 backgrounds as:
- 32×64 tilemaps in VRAM order
- two stacked 32×32 screens
- raw SNES screen layouts

Examples found using this layout:
- Earthworm Jim
- Contra III

---

```ini
palette=Level 5.pal
tiles=Level 5.sf4
metatiles=Level 5.mtl
```

Standard shared project assets.

---

```ini
metatile_size=2
```

Uses 2×2 metatiles.

This gives:
- 16×16 pixel metatiles
- traditional SNES-style metatile editing

---

```ini
maps=Level 5.map,Level 5_2.map
```

Multiple gameplay maps sharing the same assets.

---

```ini
width=302,50
height=60,156
```

Per-map dimensions.

Each width and height entry matches the map order.

---

```ini
map_direction=top_bottom
```

Maps stored in column order.

---

```ini
map_index_mask=0x1FFF
```

Uses 13 bits for map tile indices.

This allows:
- larger metatile ranges
- bigger tilesets
- extended tile addressing

Useful for engines exceeding normal SNES 10-bit tile ranges.

---

```ini
map_h_flip_bit=14
map_v_flip_bit=15
```

SNES-compatible flip bit layout.

---

# Direct BG2 Preview Mode

```ini
preview_bg2_map = Level 5_bg2.map
```

Dedicated BG2 map file used only for preview rendering.

This BG2 map is independent from gameplay maps.

---

```ini
preview_bg2_mode = direct
```

Direct mode means:
- BG2 is loaded directly from the specified file
- BG2 does not come from another project map
- Useful for raw SNES VRAM dumps

Supported modes:
- `direct`
- `project_map`

---

```ini
preview_bg2_width = 64
preview_bg2_height = 32
```

Defines the final visible BG2 dimensions.

Important:
the source data itself is actually stored as:
- 32×64

but displayed as:
- 64×32

This mirrors how SNES VRAM screen blocks are arranged internally.

---

```ini
preview_bg2_format=snes_32x64_to_64x32
```

Special layout conversion mode.

Converts:
- SNES VRAM-style 32×64 storage

into:
- editor-friendly 64×32 display

This automatically rearranges:
- left screen
- right screen

into the correct visual order.

---

```ini
preview_bg2_repeat_x = fill
preview_bg2_repeat_y = fill
```

Automatically repeats the BG2 background:
- horizontally
- vertically

until the preview window is filled.

Very useful for:
- skies
- mountains
- distant backgrounds
- repeating scenery

---

```ini
preview_bg2_scroll_x = 0.5
preview_bg2_scroll_y = 0.5
```

Parallax scroll ratios.

BG2 moves at half speed relative to BG1.

Creates:
- depth
- distant scenery effect
- smoother parallax illusion

Typical values:
- `1.0` = same speed
- `0.5` = half speed
- `0.25` = distant background
