# MODE1 EDITOR - STABLE VERSION
# Features:
# - 2-byte SNES map entries
# - palette + flip + priority support
# - block brush + ghost preview
# Locked: 11th May 2026
# By Michael J Archer

import sys
import os
import argparse
import textwrap

import faulthandler
import traceback

HELP_TEXT = textwrap.dedent("""
    Mode1 Editor (Metatile Edition v3)

    This tool edits SNES Mode 1 4bps projects using:
      - one shared palette (.pal, SNES -byte format)
      - one shared character set (.sf4)
      - one shared metatile set (.mtl)
      - one or more map files (.map)

    Supports dynamic metatile sizes (2x2, 4x4, etc)

    --------------------------------------------------
    PROJECT MODE
      python mode1_editor.py test_map

      Loads:
        test_map.m1e

    --------------------------------------------------
    DIRECT FILE MODE
      python mode1_editor.py --palette level.pal --chr level.sf4 --map level.map --width 128 --height 128

    DIRECT MULTI-MAP MODE
      python mode1_editor.py --palette level.pal --chr level.sf4 --map map1.map --map map2.map --width 128 --height 128

    --------------------------------------------------
    .M1E FORMAT
      Example:
        palette=test_map.pal
        tiles=test_map.sf4
        metatiles=test_map.mtl
        maps=test_map_1.map,test_map_2.map
        width=128
        height=128
        metatile_size=2

      Older single-map projects are supported:
        map=test_map.map

    --------------------------------------------------
    MOUSE CONTROLS

    Tile sheet:
      Left click        Select tile
      Click + drag      Select block

    Tile editor:
      Left click        Paint pixel
      Right click       Pick colour
      Alt + Left        Eyedropper

    Map editor:
      Left click        Paint metatile / brush
      Right click       Pick tile / brush
      Right drag        Copy block as brush
      Middle drag       Pan map
      Space + drag      Pan map (alt method)
      Mouse wheel       Zoom in/out
      Left paint        Disabled below 1:1 zoom

    Metatile editor:
      Left click        Select subtile
      Right click       Pick tile / palette / flags

    --------------------------------------------------
    KEYBOARD SHORTCUTS

    General:
      P           Toggle metatile picker
      ESC         Close picker
      - / +       Previous / next metatile
      H           Show help

    Map editor:
      X           Flip X (hover tile or brush)
      Y           Flip Y (hover tile or brush)
      Ctrl+Z      Undo character edit
      U           Undo last map paint

    Tile editor:
      X           Flip X
      Y           Flip Y
      R           Rotate clockwise
      Shift+R     Rotate anticlockwise
      Delete      Clear tile
      I           Invert tile
      C           Copy tile
      V           Paste tile

    Metatile editor:
      X           Toggle X flip on subtile
      Y           Toggle Y flip on subtile
      P           Toggle priority

    --------------------------------------------------
    METATILE PICKER

      Click       Select metatile
      - / +       Step selection
      P / ESC     Close picker

    --------------------------------------------------
    BG PREVIEW WINDOW

      1           Move BG1
      2           Move BG2
      3           Move BOTH
      S           Swap BG priority
      R           Reset position
      Arrow keys  Move layer(s)
      Shift       Snap movement (8px)
      Mouse drag  Move layer(s)

    --------------------------------------------------
    SAVE BUTTONS

      Save Project   Save all files
      Save Map       Save current map
      Save Chr       Save character data
      Save Palette   Save palette

    --------------------------------------------------
    NOTES

      - Colour 0 is treated as transparent in BG preview
      - Grid scales automatically with metatile size
      - Metatile size is fixed per project (not editable at runtime)
      - Large maps may take a moment to render initially
      - Palette values are quantised to SNES 5-bit colour
    """)

MAP_HELP_TEXT = """
<h3>Map Editor Help</h3>

<b>Mouse:</b>
<table>
<tr><td>Left click</td><td>&nbsp;&nbsp;Paint metatile / brush</td></tr>
<tr><td>Right click</td><td>&nbsp;&nbsp;Pick metatile / brush</td></tr>
<tr><td>Right drag</td><td>&nbsp;&nbsp;Copy block as brush</td></tr>
<tr><td>Middle drag</td><td>&nbsp;&nbsp;Pan map</td></tr>
<tr><td>Space + drag</td><td>&nbsp;&nbsp;Pan map</td></tr>
<tr><td>Mouse wheel</td><td>&nbsp;&nbsp;Zoom</td></tr>
</table>

<br>

<b>Keys:</b>
<table>
<tr><td>P</td><td>&nbsp;&nbsp;Toggle picker</td></tr>
<tr><td>- / +</td><td>&nbsp;&nbsp;Previous / next metatile</td></tr>
<tr><td>O</td><td>&nbsp;&nbsp;Toggle SNES screen overlay</td></tr>
<tr><td>X / Y</td><td>&nbsp;&nbsp;Flip hover tile or brush</td></tr>
<tr><td>Ctrl+Z / U</td><td>&nbsp;&nbsp;Undo</td></tr>
<tr><td>E</td><td>&nbsp;&nbsp;Switch to metatile editor</td></tr>
<tr><td>H</td><td>&nbsp;&nbsp;Show this help</td></tr>
</table>
"""

METATILE_HELP_TEXT = """
<h3>Metatile Editor Help</h3>

<b>Mouse:</b>
<table>
<tr><td>Left click</td><td>&nbsp;&nbsp;Select subtile</td></tr>
<tr><td>Right click</td><td>&nbsp;&nbsp;Pick tile / palette / flags</td></tr>
</table>

<br>

<b>Keys:</b>
<table>
<tr><td>X / Y</td><td>&nbsp;&nbsp;Toggle subtile flip</td></tr>
<tr><td>0 - 7</td><td>&nbsp;&nbsp;Set palette group</td></tr>
<tr><td>E</td><td>&nbsp;&nbsp;Switch to map editor</td></tr>
<tr><td>H</td><td>&nbsp;&nbsp;Show this help</td></tr>
</table>
"""

PREVIEW_HELP_TEXT = """
<h3>BG Preview Help</h3>

<b>Mouse:</b>
<table>
<tr><td>Drag</td><td>&nbsp;&nbsp;Move selected BG layer(s)</td></tr>
<tr><td>Shift + drag</td><td>&nbsp;&nbsp;Snap movement to 8 pixels</td></tr>
<tr><td>Ctrl + drag</td><td>&nbsp;&nbsp;Lock horizontal movement</td></tr>
<tr><td>Alt + drag</td><td>&nbsp;&nbsp;Lock vertical movement</td></tr>
</table>

<br>

<b>Keys:</b>
<table>
<tr><td>1</td><td>&nbsp;&nbsp;Move BG1</td></tr>
<tr><td>2</td><td>&nbsp;&nbsp;Move BG2</td></tr>
<tr><td>3</td><td>&nbsp;&nbsp;Move both</td></tr>
<tr><td>4</td><td>&nbsp;&nbsp;Move BG1, with BG2 parallax-linked</td></tr>
<tr><td>S</td><td>&nbsp;&nbsp;Swap BG priority</td></tr>
<tr><td>R</td><td>&nbsp;&nbsp;Reset selected BG position</td></tr>
<tr><td>O</td><td>&nbsp;&nbsp;Toggle SNES screen overlay</td></tr>
<tr><td>Arrow keys</td><td>&nbsp;&nbsp;Move selected BG layer(s)</td></tr>
<tr><td>H</td><td>&nbsp;&nbsp;Show this help</td></tr>
</table>
"""

faulthandler.enable()

def excepthook(exc_type, exc_value, exc_tb):
    print("UNCAUGHT PYTHON EXCEPTION:")
    traceback.print_exception(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QScrollArea, QSizePolicy, QSlider, QMessageBox, QCheckBox
)
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QIcon

from PySide6.QtCore import Qt, QTimer

TILE_SIZE = 8
EDITOR_PIXEL_SIZE = 16
PALETTE_CELL_SIZE = EDITOR_PIXEL_SIZE
VISIBLE_PALETTE_ENTRIES = 128
PALETTE_COLUMNS = 16

def load_metatiles(path, metatile_size=2):
    entry_count = metatile_size * metatile_size
    bytes_per_metatile = entry_count * 2

    data = open(path, "rb").read()

    if len(data) % bytes_per_metatile != 0:
        raise ValueError(
            f"{path} size must be a multiple of {bytes_per_metatile} bytes "
            f"for {metatile_size}x{metatile_size} metatiles"
        )

    out = []

    for i in range(0, len(data), bytes_per_metatile):
        mt = []

        for entry in range(entry_count):
            off = i + entry * 2
            lo = data[off]
            hi = data[off + 1]
            mt.append(lo | (hi << 8))

        out.append(mt)

    return out
    
def save_metatiles(path, metatiles):
    out = bytearray()
    for mt in metatiles:
        for value in mt:
            out.append(value & 0xFF)
            out.append((value >> 8) & 0xFF)
    with open(path, "wb") as f:
        f.write(out)
        
def snes5_to_8(v):
    return (v << 3) | (v >> 2)

def rgb8_to_snes5(v):
    return max(0, min(31, v >> 3))

def load_palette_snes(path):
    data = open(path, "rb").read()
    if len(data) != 256:
        raise ValueError(f"{path} must be 256 bytes for 8 groups of 16 colours SNES palette, got {len(data)}")

    palette = []
    for i in range(0, len(data), 2):
        word = data[i] | (data[i + 1] << 8)

        r5 = word & 0x1F
        g5 = (word >> 5) & 0x1F
        b5 = (word >> 10) & 0x1F

        palette.append((
            snes5_to_8(r5),
            snes5_to_8(g5),
            snes5_to_8(b5)
        ))

    return palette

def save_palette(self):
    save_palette_snes(self.palette_path, self.palette)
    self.modified_pal = False
    self.update_status()

def save_map(self):
    with open(self.map_path, "wb") as f:
        f.write(self.map_data)
    self.modified_map = False
    self.update_status()

def save_chr(self):
    save_tiles(self.tiles_path, self.tiles)
    self.modified_chr = False
    self.update_status()
    
def save_palette_snes(path, palette):
    out = bytearray()

    for r8, g8, b8 in palette:
        r5 = rgb8_to_snes5(r8)
        g5 = rgb8_to_snes5(g8)
        b5 = rgb8_to_snes5(b8)

        word = (b5 << 10) | (g5 << 5) | r5
        out.append(word & 0xFF)
        out.append((word >> 8) & 0xFF)

    with open(path, "wb") as f:
        f.write(out)

def is_empty_tile(tile):
    return all(b == 0 for b in tile)
    
def load_tiles(path):
    data = open(path, "rb").read()
    tiles = [bytearray(data[i:i + 32]) for i in range(0, len(data), 32)]

    while len(tiles) < 1024:
        tiles.append(bytearray(32))

    return tiles[:1024]
    
def save_tiles(path, tiles):
    last = -1

    for i in range(len(tiles) - 1, -1, -1):
        if not is_empty_tile(tiles[i]):
            last = i
            break

    if last == -1:
        last = 0  # always save at least one tile

    out = bytearray()
    for tile in tiles[:last + 1]:
        out.extend(tile)

    with open(path, "wb") as f:
        f.write(out)

def load_map(path):
    return bytearray(open(path, "rb").read())

def ensure_project_filename(name):
    if name.lower().endswith(".m1e"):
        return name
    return f"{name}.m1e"

def load_project(name):
    filename = ensure_project_filename(name)

    data = {}
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip()

    return data

def create_project(name, width=128, height=128):
    project_filename = ensure_project_filename(name)
    project_base, _ = os.path.splitext(project_filename)

    palette_path = f"{project_base}.pal"
    tiles_path = f"{project_base}.sf4"
    metatile_path = f"{project_base}.mtl"
    map_path = f"{project_base}_1.map"

    with open(project_filename, "w") as f:
        f.write(f"palette={palette_path}\n")
        f.write(f"tiles={tiles_path}\n")
        f.write(f"metatiles={metatile_path}\n")
        f.write(f"maps={map_path}\n")
        f.write(f"width={width}\n")
        f.write(f"height={height}\n")
        f.write("map_direction=top_bottom\n")
        f.write("map_index_mask=0x03FF\n")
        f.write("map_h_flip_bit=14\n")
        f.write("map_v_flip_bit=15\n")

    save_default_palette(palette_path)

    # 1024 SNES 4bpp tiles, 32 bytes each
    chr_data = bytearray(1024 * 32)
    with open(tiles_path, "wb") as f:
        f.write(chr_data)

    # default 256 blank 2x2 metatiles, 8 bytes each
    save_metatiles(metatile_path, make_blank_metatiles(256))

    # first map
    with open(map_path, "wb") as f:
        f.write(bytearray(width * height * 2))

def rgb5_to_snes_word(r5, g5, b5):
    return (b5 << 10) | (g5 << 5) | r5

def save_default_palette(path):
    ramps = []

    def make_ramp(mode):
        vals = [round(i * 31 / 15) for i in range(16)]
        out = []

        for v in vals:
            if mode == "gray":
                out.append((v, v, v))
            elif mode == "red":
                out.append((v, 0, 0))
            elif mode == "green":
                out.append((0, v, 0))
            elif mode == "blue":
                out.append((0, 0, v))
            elif mode == "yellow":
                out.append((v, v, 0))
            elif mode == "magenta":
                out.append((v, 0, v))
            elif mode == "cyan":
                out.append((0, v, v))
            elif mode == "orange":
                out.append((v, v // 2, 0))
            elif mode == "purple":
                out.append((v // 2, 0, v))
            elif mode == "lime":
                out.append((v // 2, v, 0))
            elif mode == "rg":
                out.append((v, v, v // 4))
            elif mode == "rb":
                out.append((v, v // 4, v))
            elif mode == "gb":
                out.append((v // 4, v, v))
            elif mode == "warm":
                out.append((v, min(31, int(v * 0.75)), min(31, int(v * 0.5))))
            elif mode == "cool":
                out.append((min(31, int(v * 0.5)), min(31, int(v * 0.75)), v))
            elif mode == "white":
                out.append((v, v, min(31, v + 4)))
        return out

    ramp_names = [
        "gray", "red", "green", "blue",
        "yellow", "magenta", "cyan", "orange",
        "purple", "lime", "rg", "rb",
        "gb", "warm", "cool", "white"
    ]

    for name in ramp_names:
        ramps.extend(make_ramp(name))

    out = bytearray()
    for r5, g5, b5 in ramps[:128]:
        word = rgb5_to_snes_word(r5, g5, b5)
        out.append(word & 0xFF)
        out.append((word >> 8) & 0xFF)

    with open(path, "wb") as f:
        f.write(out) 

def render_tile(tile, palette):
    img = QImage(8, 8, QImage.Format_RGB32)
    for y in range(8):
        for x in range(8):
            c = tile[y * 8 + x]
            r, g, b = palette[c]
            img.setPixel(x, y, (r << 16) | (g << 8) | b)
    return img
 
def render_tile_argb(tile, palette, palette_number=0, h_flip=False, v_flip=False, transparent_zero=False):
    img = QImage(8, 8, QImage.Format_ARGB32)
    pixels = decode_snes_4bpp_tile(tile)

    base = palette_number * 16

    for y in range(8):
        sy = 7 - y if v_flip else y
        for x in range(8):
            sx = 7 - x if h_flip else x
            c = pixels[sy * 8 + sx]

            if transparent_zero and c == 0:
                img.setPixel(x, y, 0x00000000)
            else:
                r, g, b = palette[base + c]
                img.setPixel(x, y, (0xFF << 24) | (r << 16) | (g << 8) | b)

    return img
 
def decode_snes_4bpp_tile(tile_data):
    pixels = bytearray(64)

    for y in range(8):
        p0 = tile_data[y * 2]
        p1 = tile_data[y * 2 + 1]
        p2 = tile_data[16 + y * 2]
        p3 = tile_data[16 + y * 2 + 1]

        for x in range(8):
            mask = 0x80 >> x
            c = 0
            if p0 & mask:
                c |= 1
            if p1 & mask:
                c |= 2
            if p2 & mask:
                c |= 4
            if p3 & mask:
                c |= 8
            pixels[y * 8 + x] = c

    return pixels

def encode_snes_4bpp_tile(pixels):
    out = bytearray(32)

    for y in range(8):
        p0 = 0
        p1 = 0
        p2 = 0
        p3 = 0

        for x in range(8):
            c = pixels[y * 8 + x] & 0x0F
            mask = 0x80 >> x

            if c & 1:
                p0 |= mask
            if c & 2:
                p1 |= mask
            if c & 4:
                p2 |= mask
            if c & 8:
                p3 |= mask

        out[y * 2] = p0
        out[y * 2 + 1] = p1
        out[16 + y * 2] = p2
        out[16 + y * 2 + 1] = p3

    return out
    
def render_tile(tile, palette, palette_number=0, h_flip=False, v_flip=False):
    img = QImage(8, 8, QImage.Format_RGB32)
    pixels = decode_snes_4bpp_tile(tile)

    base = palette_number * 16

    for y in range(8):
        sy = 7 - y if v_flip else y
        for x in range(8):
            sx = 7 - x if h_flip else x
            c = pixels[sy * 8 + sx]
            r, g, b = palette[base + c]
            img.setPixel(x, y, (r << 16) | (g << 8) | b)

    return img

def flip_tile_x(tile):
    out = bytearray(64)
    for y in range(8):
        for x in range(8):
            out[y * 8 + x] = tile[y * 8 + (7 - x)]
    return out

def flip_tile_y(tile):
    out = bytearray(64)
    for y in range(8):
        for x in range(8):
            out[y * 8 + x] = tile[(7 - y) * 8 + x]
    return out

def rotate_tile_cw(tile):
    out = bytearray(64)
    for y in range(8):
        for x in range(8):
            out[y * 8 + x] = tile[(7 - x) * 8 + y]
    return out

def rotate_tile_ccw(tile):
    
    out = bytearray(64)
    for y in range(8):
        for x in range(8):
            out[y * 8 + x] = tile[x * 8 + (7 - y)]
    return out

def parse_hex_or_dec(value):
    value = str(value).strip().lower()
    if value.startswith("$"):
        return int(value[1:], 16)
    if value.startswith("0x"):
        return int(value, 16)
    return int(value, 10)

def parse_int_or_fill(value, default=1):
    value = str(value).strip().lower()
    if value == "fill":
        return "fill"
    if value == "":
        return default
    return int(value)

def validate_project_files(tiles_path, palette_path, map_paths, metatile_path=None):
    missing = []

    if not os.path.isfile(tiles_path):
        missing.append(tiles_path)

    if not os.path.isfile(palette_path):
        missing.append(palette_path)

    for path in map_paths:
        if not os.path.isfile(path):
            missing.append(path)

    if metatile_path:
        if not os.path.isfile(metatile_path):
            missing.append(metatile_path)

    return missing

def get_map_entry(map_data, map_width, x, y, index_mask=0x03FF, h_flip_mask=0x4000, v_flip_mask=0x8000):
    idx = (y * map_width + x) * 2
    lo = map_data[idx]
    hi = map_data[idx + 1]
    value = lo | (hi << 8)

    tile_number = value & index_mask
    palette_number = (value >> 10) & 0x07
    h_flip = bool(value & h_flip_mask)
    v_flip = bool(value & v_flip_mask)
    priority = bool(value & 0x2000)

    return {
        "value": value,
        "tile": tile_number,
        "palette": palette_number,
        "priority": priority,
        "h_flip": h_flip,
        "v_flip": v_flip,
    }

def set_map_entry(map_data, map_width, x, y, value):
    idx = (y * map_width + x) * 2
    map_data[idx] = value & 0xFF
    map_data[idx + 1] = (value >> 8) & 0xFF

def make_map_entry(tile_number, palette_number, priority=False, h_flip=False, v_flip=False,
                   index_mask=0x03FF, h_flip_mask=0x4000, v_flip_mask=0x8000):
    value = tile_number & index_mask
    value |= (palette_number & 0x07) << 10

    if priority:
        value |= 0x2000
    if h_flip:
        value |= h_flip_mask
    if v_flip:
        value |= v_flip_mask

    return value
    
def parse_project_dimension_list(value, map_count, name):
    parts = [p.strip() for p in value.split(",") if p.strip()]

    if len(parts) == 1:
        return [int(parts[0])] * map_count

    if len(parts) != map_count:
        raise ValueError(
            f"{name} must contain either 1 value or {map_count} values, got {len(parts)}"
        )

    return [int(p) for p in parts]

def make_blank_metatiles(count=256, metatile_size=2):
    return [[0] * (metatile_size * metatile_size) for _ in range(count)]
    
class MetatilePicker(QLabel):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.tiles_per_row = max(1, 32 // self.parent.metatile_size)
        self.rows_per_page = self.tiles_per_row
        self.per_page = self.tiles_per_row * self.rows_per_page
        self.tile_scale = 2

        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.build()

    def build(self):
        count = len(self.parent.metatiles)

        cell = self.parent.metatile_pixel_size
        w = self.tiles_per_row * cell
        h = self.rows_per_page * cell

        img = QImage(w, h, QImage.Format_RGB32)
        img.fill(QColor(20, 20, 20))

        painter = QPainter(img)

        start = self.parent.metatile_page * self.per_page
        end = min(start + self.per_page, count)

        for page_i, mt_index in enumerate(range(start, end)):
            x = (page_i % self.tiles_per_row) * cell
            y = (page_i // self.tiles_per_row) * cell

            mt_img = self.parent.render_metatile_image(self.parent.metatiles[mt_index])
            painter.drawImage(x, y, mt_img)

        sel = getattr(self.parent, "selected_metatile", 0)
        if start <= sel < end:
            local_index = sel - start
            sx = (local_index % self.tiles_per_row) * cell
            sy = (local_index // self.tiles_per_row) * cell
            painter.setPen(QPen(Qt.red, 1))
            painter.drawRect(sx, sy, cell - 1, cell - 1)

        painter.end()

        pix = QPixmap.fromImage(img).scaled(
            w * self.tile_scale,
            h * self.tile_scale,
            Qt.KeepAspectRatio,
            Qt.FastTransformation
        )

        self.setPixmap(pix)
        self.resize(pix.size())
        self.adjustSize()

    def mousePressEvent(self, event):
        px = int(event.position().x())
        py = int(event.position().y())

        cell = self.parent.metatile_pixel_size * self.tile_scale
        tx = px // cell
        ty = py // cell

        if tx < 0 or tx >= self.tiles_per_row or ty < 0 or ty >= self.rows_per_page:
            return

        local_index = ty * self.tiles_per_row + tx
        mt_index = self.parent.metatile_page * self.per_page + local_index

        if 0 <= mt_index < len(self.parent.metatiles):
            self.parent.selected_metatile = mt_index
            self.parent.brush_w = 1
            self.parent.brush_h = 1
            self.parent.brush_tiles = [mt_index]

            self.build()
            self.parent.update_status()

        if (
            hasattr(self.parent, "picker_window")
            and self.parent.picker_window is not None
            and self.parent.picker_window.isVisible()
        ):
            self.parent.picker_window.refresh_status()

class TileViewer(QLabel):
    def __init__(self, tiles, palette, parent):
        super().__init__()
        self.tiles = tiles
        self.palette = palette
        self.parent = parent
        self.tiles_per_row = 32
        self.tile_scale = 2

        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.drag_selecting = False
        self.sel_start_index = None
        self.sel_end_index = None

        self.build()

    def build(self):
        rows = (len(self.tiles) + self.tiles_per_row - 1) // self.tiles_per_row
        w = self.tiles_per_row * TILE_SIZE
        h = rows * TILE_SIZE

        img = QImage(w, h, QImage.Format_RGB32)
        painter = QPainter(img)

        for i, tile in enumerate(self.tiles):
            x = (i % self.tiles_per_row) * TILE_SIZE
            y = (i // self.tiles_per_row) * TILE_SIZE
            painter.drawImage( x, y, render_tile(tile, self.palette, self.parent.selected_palette_group))
        painter.setPen(QPen(Qt.red, 1))

        if self.sel_start_index is not None and self.sel_end_index is not None:
            start_col = self.sel_start_index % self.tiles_per_row
            start_row = self.sel_start_index // self.tiles_per_row
            end_col = self.sel_end_index % self.tiles_per_row
            end_row = self.sel_end_index // self.tiles_per_row

            left = min(start_col, end_col)
            right = max(start_col, end_col)
            top = min(start_row, end_row)
            bottom = max(start_row, end_row)

            painter.drawRect(
                left * TILE_SIZE,
                top * TILE_SIZE,
                (right - left + 1) * TILE_SIZE - 1,
                (bottom - top + 1) * TILE_SIZE - 1
            )
        else:
            sel = self.parent.selected_tile
            sx = (sel % self.tiles_per_row) * TILE_SIZE
            sy = (sel // self.tiles_per_row) * TILE_SIZE
            painter.drawRect(sx, sy, TILE_SIZE - 1, TILE_SIZE - 1)

        painter.end()

        pix = QPixmap.fromImage(img).scaled(
            img.width() * self.tile_scale,
            img.height() * self.tile_scale,
            Qt.KeepAspectRatio,
            Qt.FastTransformation
        )
        self.setPixmap(pix)
        self.adjustSize()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        index = self.tile_index_from_event(event)
        if index is None:
            return

        self.drag_selecting = True
        self.sel_start_index = index
        self.sel_end_index = index
        self.build()

    def tile_index_from_event(self, event):
        
        x = int(event.position().x()) // self.tile_scale
        y = int(event.position().y()) // self.tile_scale

        tx = x // TILE_SIZE
        ty = y // TILE_SIZE

        index = ty * self.tiles_per_row + tx
        if 0 <= index < len(self.tiles):
            return index
        return None
        
    def mouseMoveEvent(self, event):
        if not self.drag_selecting:
            return

        index = self.tile_index_from_event(event)
        if index is None:
            return

        if index != self.sel_end_index:
            self.sel_end_index = index
            self.build() 
            
    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self.drag_selecting:
            return

        self.drag_selecting = False

        index = self.tile_index_from_event(event)
        if index is not None:
            self.sel_end_index = index

        if self.sel_start_index is None or self.sel_end_index is None:
            return

        start_col = self.sel_start_index % self.tiles_per_row
        start_row = self.sel_start_index // self.tiles_per_row
        end_col = self.sel_end_index % self.tiles_per_row
        end_row = self.sel_end_index // self.tiles_per_row

        left = min(start_col, end_col)
        right = max(start_col, end_col)
        top = min(start_row, end_row)
        bottom = max(start_row, end_row)

        brush_tiles = []
        for row in range(top, bottom + 1):
            for col in range(left, right + 1):
                idx = row * self.tiles_per_row + col
                if 0 <= idx < len(self.tiles):
                    brush_tiles.append(idx)

        if not brush_tiles:
            return

        self.parent.selected_tile = brush_tiles[0]
        self.parent.brush_w = right - left + 1
        self.parent.brush_h = bottom - top + 1
        self.parent.brush_tiles = brush_tiles

        self.parent.update_status()
        self.parent.tile_editor.build()
        self.parent.palette_controls.refresh_from_selected_colour()
        self.build()    

class PaletteView(QLabel):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.cell_size = PALETTE_CELL_SIZE
        self.cols = PALETTE_COLUMNS
        self.build()

    def build(self):
        palette = self.parent.palette[:VISIBLE_PALETTE_ENTRIES]
        rows = (len(palette) + self.cols - 1) // self.cols

        w = self.cols * self.cell_size
        h = rows * self.cell_size

        img = QImage(w, h, QImage.Format_RGB32)
        painter = QPainter(img)

        for i, (r, g, b) in enumerate(palette):
            x = (i % self.cols) * self.cell_size
            y = (i // self.cols) * self.cell_size
            painter.fillRect(x, y, self.cell_size, self.cell_size, QColor(r, g, b))

        painter.setPen(QPen(Qt.gray, 1))
        for i in range(self.cols + 1):
            painter.drawLine(i * self.cell_size, 0, i * self.cell_size, h)
        for i in range(rows + 1):
            painter.drawLine(0, i * self.cell_size, w, i * self.cell_size)

        group = self.parent.selected_palette_group
        gy = group * self.cell_size
        painter.setPen(QPen(QColor(0, 255, 255), 1))
        painter.drawRect(0, gy, self.cols * self.cell_size - 1, self.cell_size - 1)

        sel = self.parent.selected_color
        sx = (sel % self.cols) * self.cell_size
        sy = (sel // self.cols) * self.cell_size
        painter.setPen(QPen(Qt.red, 2))
        painter.drawRect(sx, sy, self.cell_size - 1, self.cell_size - 1)

        painter.end()

        self.setPixmap(QPixmap.fromImage(img))
        self.adjustSize()

    def mousePressEvent(self, event):
        x = int(event.position().x()) // self.cell_size
        y = int(event.position().y()) // self.cell_size

        if x < 0 or x >= self.cols:
            return

        idx = y * self.cols + x

        if not (0 <= idx < VISIBLE_PALETTE_ENTRIES):
            return

        # --- RIGHT CLICK = COPY ---
        if event.button() == Qt.RightButton:
            self.parent.copied_color = self.parent.palette[idx]
            self.parent.update_status()
            return

        # --- LEFT CLICK ---
        if event.button() == Qt.LeftButton:

            # If clicking SAME colour again → paste
            if idx == self.parent.selected_color and self.parent.copied_color is not None:
                self.parent.palette[idx] = self.parent.copied_color
                self.parent.modified_pal = True
                self.parent.map_view_dirty_full = True

            # Always update selection
            self.parent.selected_color = idx
            self.parent.selected_palette_group = idx // 16
            self.parent.selected_color_in_group = idx % 16

            # Existing metatile palette logic (keep this!)
            if self.parent.editor_mode == "metatile" and not self.parent.direct_tilemap_mode:
                mt_index = self.parent.selected_metatile
                sub = self.parent.selected_subtile

                if 0 <= mt_index < len(self.parent.metatiles):
                    old_value = self.parent.metatiles[mt_index][sub]
                    new_value = (old_value & ~0x1C00) | ((self.parent.selected_palette_group & 0x07) << 10)

                    self.parent.metatiles[mt_index][sub] = new_value
                    self.parent.modified_map = True
                    self.parent.mark_metatile_dirty(mt_index)
                    self.parent.metatile_view.build()

                    if (
                        hasattr(self.parent, "picker_window")
                        and self.parent.picker_window is not None
                        and self.parent.picker_window.isVisible()
                    ):
                        self.parent.picker_window.refresh_status()

            # Refresh UI
            self.parent.update_status()
            self.build()
            self.parent.palette_controls.refresh_from_selected_colour()
            self.parent.tile_view.build()
            self.parent.tile_editor.build()

            if self.parent.editor_mode == "map":
                self.parent.map_view.rebuild_all()
            else:
                self.parent.metatile_view.build()

                if self.parent.direct_tilemap_mode:
                    self.parent.map_view.rebuild_all()
                
class PaletteControls(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.updating = False

        self.setFixedWidth(260)

        self.preview = QLabel()
        self.preview.setFixedSize(48, 48)

        self.r_label = QLabel("R: 0")
        self.g_label = QLabel("G: 0")
        self.b_label = QLabel("B: 0")

        self.r_slider = QSlider(Qt.Horizontal)
        self.g_slider = QSlider(Qt.Horizontal)
        self.b_slider = QSlider(Qt.Horizontal)

        for slider in (self.r_slider, self.g_slider, self.b_slider):
            slider.setRange(0, 255)
            slider.setFixedWidth(170)

        self.r_slider.valueChanged.connect(self.slider_changed)
        self.g_slider.valueChanged.connect(self.slider_changed)
        self.b_slider.valueChanged.connect(self.slider_changed)

        sliders_layout = QVBoxLayout()
        sliders_layout.setAlignment(Qt.AlignTop)
        sliders_layout.setSpacing(4)
        sliders_layout.addWidget(self.r_label)
        sliders_layout.addWidget(self.r_slider)
        sliders_layout.addWidget(self.g_label)
        sliders_layout.addWidget(self.g_slider)
        sliders_layout.addWidget(self.b_label)
        sliders_layout.addWidget(self.b_slider)

        main_layout = QHBoxLayout()
        main_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        main_layout.setSpacing(10)
        main_layout.addWidget(self.preview)
        main_layout.addLayout(sliders_layout)
        self.setLayout(main_layout)

        self.refresh_from_selected_colour()

    def quantise_rgb(self, r8, g8, b8):
        r5 = rgb8_to_snes5(r8)
        g5 = rgb8_to_snes5(g8)
        b5 = rgb8_to_snes5(b8)
        return (
            snes5_to_8(r5),
            snes5_to_8(g5),
            snes5_to_8(b5)
        )

    def set_preview(self, r, g, b):
        img = QImage(48, 48, QImage.Format_RGB32)
        img.fill((r << 16) | (g << 8) | b)
        self.preview.setPixmap(QPixmap.fromImage(img))

    def refresh_from_selected_colour(self):
        self.updating = True

        r, g, b = self.parent.palette[self.parent.selected_color]

        self.r_slider.setValue(r)
        self.g_slider.setValue(g)
        self.b_slider.setValue(b)

        self.r_label.setText(f"R: {r}")
        self.g_label.setText(f"G: {g}")
        self.b_label.setText(f"B: {b}")

        self.set_preview(r, g, b)

        self.updating = False

    def slider_changed(self):
        if self.updating:
            return

        r = self.r_slider.value()
        g = self.g_slider.value()
        b = self.b_slider.value()

        r, g, b = self.quantise_rgb(r, g, b)

        self.updating = True
        self.r_slider.setValue(r)
        self.g_slider.setValue(g)
        self.b_slider.setValue(b)
        self.updating = False

        self.parent.palette[self.parent.selected_color] = (r, g, b)
        self.parent.modified_pal = True
        self.parent.map_view_dirty_full = True
        self.r_label.setText(f"R: {r}")
        self.g_label.setText(f"G: {g}")
        self.b_label.setText(f"B: {b}")
        self.set_preview(r, g, b)

        self.parent.palette_view.build()
        self.parent.tile_editor.build()
        self.parent.tile_view.build()

        if self.parent.editor_mode == "metatile":
            self.parent.metatile_view.build()
            if (
                hasattr(self.parent, "picker_window")
                and self.parent.picker_window is not None
                and self.parent.picker_window.isVisible()
            ):
                self.parent.picker_window.picker.build()
                self.parent.picker_window.refresh_status()
    
        else:
            self.parent.map_view.rebuild_all()
            self.parent.map_view_dirty_full = False
            self.parent.map_view_dirty_metatiles.clear()

        self.parent.update_status()

class TileOps(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.setFixedWidth(160)

        self.flip_x_btn = QPushButton("Flip X")
        self.flip_y_btn = QPushButton("Flip Y")
        self.clear_btn = QPushButton("Clear")
        self.invert_btn = QPushButton("Invert")
        self.copy_btn = QPushButton("Copy")
        self.paste_btn = QPushButton("Paste")
        self.rotate_cw_btn = QPushButton("Rot.CW")
        self.rotate_ccw_btn = QPushButton("Rot.CCW")

        buttons = [
            self.flip_x_btn, self.flip_y_btn,
            self.clear_btn, self.invert_btn,
            self.copy_btn, self.paste_btn,
            self.rotate_cw_btn, self.rotate_ccw_btn
        ]

        for b in buttons:
            b.setFixedSize(60, 20)

        self.flip_x_btn.clicked.connect(self.flip_x)
        self.flip_y_btn.clicked.connect(self.flip_y)
        self.clear_btn.clicked.connect(self.clear_tile)
        self.invert_btn.clicked.connect(self.invert_tile)
        self.copy_btn.clicked.connect(self.copy_tile)
        self.paste_btn.clicked.connect(self.paste_tile)
        self.rotate_cw_btn.clicked.connect(self.rotate_cw)
        self.rotate_ccw_btn.clicked.connect(self.rotate_ccw)

        col1 = QVBoxLayout()
        col1.setSpacing(5)
        col1.addWidget(self.flip_x_btn)
        col1.addWidget(self.clear_btn)
        col1.addWidget(self.copy_btn)
        col1.addWidget(self.rotate_cw_btn)

        col2 = QVBoxLayout()
        col2.setSpacing(5)
        col2.addWidget(self.flip_y_btn)
        col2.addWidget(self.invert_btn)
        col2.addWidget(self.paste_btn)
        col2.addWidget(self.rotate_ccw_btn)

        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.setSpacing(6)
        layout.addLayout(col1)
        layout.addLayout(col2)

        self.setLayout(layout)

    def current_tile(self):
        return self.parent.tiles[self.parent.selected_tile]

    def current_pixels(self):
        return decode_snes_4bpp_tile(self.parent.tiles[self.parent.selected_tile])
        
    def replace_current_tile(self, new_pixels):
        self.parent.tiles[self.parent.selected_tile] = encode_snes_4bpp_tile(new_pixels)
        self.parent.modified_chr = True
        self.parent.map_view_dirty_full = True
        self.parent.tile_editor.build()
        self.parent.tile_view.build()

        if self.parent.editor_mode == "map":
            self.parent.map_view.redraw()
            self.parent.map_view_dirty_full = False
            self.parent.map_view_dirty_metatiles.clear()
        else:
            self.parent.metatile_view.build()
            if (
                hasattr(self.parent, "picker_window")
                and self.parent.picker_window is not None
                and self.parent.picker_window.isVisible()
            ):
                self.parent.picker_window.picker.build()
                self.parent.picker_window.refresh_status()

        self.parent.update_status()

    def flip_x(self):
        self.replace_current_tile(flip_tile_x(self.current_pixels()))

    def flip_y(self):
        self.replace_current_tile(flip_tile_y(self.current_pixels()))

    def rotate_cw(self):
        self.replace_current_tile(rotate_tile_cw(self.current_pixels()))

    def rotate_ccw(self):
        self.replace_current_tile(rotate_tile_ccw(self.current_pixels()))

    def clear_tile(self):
        self.replace_current_tile(bytearray([0] * 64))

    def invert_tile(self):
        pixels = self.current_pixels()
        new_tile = bytearray(64)
        for i in range(64):
            new_tile[i] = 15 - (pixels[i] & 0x0F)
        self.replace_current_tile(new_tile)

    def copy_tile(self):
        self.parent.copied_tile = bytearray(self.current_pixels())

    def paste_tile(self):
        if self.parent.copied_tile is not None:
            self.replace_current_tile(bytearray(self.parent.copied_tile))

class MapView(QLabel):
    ZOOM_LEVELS = [0.125, 0.25, 0.5, 1.0, 2.0, 3.0, 4.0]

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.scale = 1.0
        self.setMouseTracking(True)
        self.setCursor(Qt.ArrowCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.base_image = None
        cell = self.parent.metatile_pixel_size
        self.grid_modes = [0, cell, cell * 2]
        self.grid_index = 0
        self.map_screen_overlay = False
        self.panning = False
        self.pan_start = None
        self.h_scroll_start = 0
        self.v_scroll_start = 0
        self.copy_dragging = False
        self.copy_start = None
        self.copy_end = None
        self.space_panning = False
        self.redraw()

    def toggle_grid(self):
        self.grid_index = (self.grid_index + 1) % len(self.grid_modes)
        self.update()
        self.parent.update_status()
                
    def zoom_text(self):
        if self.scale >= 1.0:
            if float(self.scale).is_integer():
                return f"{int(self.scale)}:1"
            return f"{self.scale:g}:1"

        inv = 1.0 / self.scale
        if float(inv).is_integer():
            return f"1:{int(inv)}"
        return f"1:{inv:g}"

    def current_zoom_index(self):
        try:
            return self.ZOOM_LEVELS.index(self.scale)
        except ValueError:
            return min(range(len(self.ZOOM_LEVELS)), key=lambda i: abs(self.ZOOM_LEVELS[i] - self.scale))

    def set_scale(self, scale, anchor_widget_pos=None):
        if self.base_image is None:
            self.scale = scale
            self.apply_zoom()
            self.parent.update_status()
            return

        old_scale = self.scale
        viewport = self.parent.map_scroll.viewport()
        hbar = self.parent.map_scroll.horizontalScrollBar()
        vbar = self.parent.map_scroll.verticalScrollBar()

        if anchor_widget_pos is None:
            viewport_anchor_x = viewport.width() // 2
            viewport_anchor_y = viewport.height() // 2
            widget_anchor_x = hbar.value() + viewport_anchor_x
            widget_anchor_y = vbar.value() + viewport_anchor_y
        else:
            widget_anchor_x = anchor_widget_pos.x()
            widget_anchor_y = anchor_widget_pos.y()
            viewport_anchor_x = widget_anchor_x - hbar.value()
            viewport_anchor_y = widget_anchor_y - vbar.value()

        image_x = widget_anchor_x / old_scale
        image_y = widget_anchor_y / old_scale

        self.scale = scale
        self.apply_zoom()

        hbar.setValue(int(image_x * self.scale - viewport_anchor_x))
        vbar.setValue(int(image_y * self.scale - viewport_anchor_y))

        self.parent.update_status()
        
    def redraw(self):
        p = self.parent
        w = p.map_width
        h = p.map_height

        cell = p.metatile_pixel_size
        img = QImage(w * cell, h * cell, QImage.Format_RGB32)
        painter = QPainter(img)

        for display_y in range(h):
            if (display_y & 7) == 0:
                QApplication.processEvents()
                
            data_y = p.map_data_y(display_y)

            for mx in range(w):
                entry = p.decode_map_entry(mx, data_y)

                painter.drawImage(
                    mx * cell,
                    display_y * cell,
                    p.render_metatile_image_from_map_entry(entry["value"])
                )

        painter.end()

        self.base_image = img
        self.apply_zoom()

    def apply_zoom(self):
        if self.base_image is None:
            return

        w = max(1, int(round(self.base_image.width() * self.scale)))
        h = max(1, int(round(self.base_image.height() * self.scale)))

        self.resize(w, h)
        self.update()
                
    def zoom_in(self):
        idx = self.current_zoom_index()
        if idx < len(self.ZOOM_LEVELS) - 1:
            self.set_scale(self.ZOOM_LEVELS[idx + 1])

    def zoom_out(self):
        idx = self.current_zoom_index()
        if idx > 0:
            self.set_scale(self.ZOOM_LEVELS[idx - 1])

    def fit_to_window(self):
        if self.base_image is None:
            return

        scroll = self.parent.map_scroll.viewport().size()
        if scroll.width() <= 0 or scroll.height() <= 0:
            return

        scale_x = scroll.width() / self.base_image.width()
        scale_y = scroll.height() / self.base_image.height()
        best = min(scale_x, scale_y)

        candidates = [z for z in self.ZOOM_LEVELS if z <= best]
        if candidates:
            self.set_scale(candidates[-1])
        else:
            self.set_scale(self.ZOOM_LEVELS[0])

    def map_pos_from_event(self, event):
        x = int(event.position().x() / self.scale)
        y = int(event.position().y() / self.scale)
        cell = self.parent.metatile_pixel_size
        tx = x // cell
        ty = y // cell
        return tx, ty

    def mousePressEvent(self, event):
        if getattr(self, "bg_preview_active", False):
            event.ignore()  # ignore any editing input
            return
        p = self.parent
        self.setFocus()
        if event.button() == Qt.LeftButton and self.space_panning:
            self.panning = True
            self.pan_start = event.globalPosition().toPoint()
            self.h_scroll_start = p.map_scroll.horizontalScrollBar().value()
            self.v_scroll_start = p.map_scroll.verticalScrollBar().value()
            self.setCursor(Qt.ClosedHandCursor)
            return
            

        if event.button() == Qt.MiddleButton:
            self.panning = True
            self.pan_start = event.globalPosition().toPoint()
            self.h_scroll_start = p.map_scroll.horizontalScrollBar().value()
            self.v_scroll_start = p.map_scroll.verticalScrollBar().value()
            self.setCursor(Qt.ClosedHandCursor)
            return

        tx, ty = self.map_pos_from_event(event)

        if tx < 0 or ty < 0 or tx >= p.map_width or ty >= p.map_height:
            return

        idx = ty * p.map_width + tx

        if event.button() == Qt.LeftButton:

            p.begin_paint_action()
            self.paint_brush(tx, ty)

            # stamp brushes finish immediately
            if p.brush_w != 1 or p.brush_h != 1:
                p.end_paint_action()

            p.update_status()

        elif event.button() == Qt.RightButton:
            self.copy_dragging = True
            self.copy_start = (tx, ty)
            self.copy_end = (tx, ty)
            self.update()
                    
    def mouseMoveEvent(self, event):
        if getattr(self, "bg_preview_active", False):
            event.ignore()  # ignore any editing input
            return
        if not self.hasFocus():
            self.setFocus()
        p = self.parent

        if self.panning:
            current = event.globalPosition().toPoint()
            delta = current - self.pan_start

            p.map_scroll.horizontalScrollBar().setValue(self.h_scroll_start - delta.x())
            p.map_scroll.verticalScrollBar().setValue(self.v_scroll_start - delta.y())
            return

        tx, ty = self.map_pos_from_event(event)
        
        if self.copy_dragging:
            if 0 <= tx < p.map_width and 0 <= ty < p.map_height:
                if (tx, ty) != self.copy_end:
                    self.copy_end = (tx, ty)
                    self.update()
            return
            
        if 0 <= tx < p.map_width and 0 <= ty < p.map_height:
            p.hover_x = tx
            p.hover_y = ty
            p.update_status()
            self.update()
        else:
            p.hover_x = -1
            p.hover_y = -1
            p.update_status()
            self.update()

        if event.buttons() & Qt.LeftButton:
            if p.brush_w != 1 or p.brush_h != 1:
                return

            if tx < 0 or ty < 0 or tx >= p.map_width or ty >= p.map_height:
                return

            self.paint_brush(tx, ty)
            p.update_status()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.panning and self.space_panning:
            self.panning = False
            self.setCursor(Qt.OpenHandCursor)
            return

        if event.button() == Qt.MiddleButton and self.panning:
            self.panning = False
            self.setCursor(Qt.ArrowCursor)
            return

        if event.button() == Qt.LeftButton:
            if self.parent.brush_w == 1 and self.parent.brush_h == 1:
                self.parent.end_paint_action()
            return

        if event.button() == Qt.RightButton and self.copy_dragging:
            self.copy_dragging = False

            if self.copy_start and self.copy_end:
                x1, y1 = self.copy_start
                x2, y2 = self.copy_end

                left = min(x1, x2)
                right = max(x1, x2)
                top = min(y1, y2)
                bottom = max(y1, y2)

                if left == right and top == bottom:
                    entry = self.parent.decode_map_entry(
                        left,
                        self.parent.map_data_y(top)
                    )

                    picked_tile = entry["tile"]
                    picked_h_flip = entry["h_flip"]
                    picked_v_flip = entry["v_flip"]

                    self.parent.selected_tile = picked_tile
                    self.parent.selected_metatile = picked_tile
                    per_page = self.parent.picker_per_page()
                    self.parent.metatile_page = self.parent.selected_metatile // per_page
                    self.parent.current_h_flip = picked_h_flip
                    self.parent.current_v_flip = picked_v_flip

                    self.parent.tile_view.sel_start_index = picked_tile
                    self.parent.tile_view.sel_end_index = picked_tile

                    self.parent.brush_w = 1
                    self.parent.brush_h = 1

                    if self.parent.direct_tilemap_mode:
                        # Keep full SNES map word, including palette, priority, flips.
                        self.parent.brush_tiles = [entry["value"]]

                        self.parent.selected_palette_group = entry["palette"]
                        self.parent.selected_color = entry["palette"] * 16
                        self.parent.selected_color_in_group = 0
                        self.parent.current_priority = entry["priority"]
                    else:
                        # Normal metatile mode only needs metatile index.
                        self.parent.brush_tiles = [picked_tile]
                else:
                    brush_tiles = []

                    for row in range(top, bottom + 1):
                        for col in range(left, right + 1):
                            entry = self.parent.decode_map_entry(
                                col,
                                self.parent.map_data_y(row)
                            )
                            brush_tiles.append(entry["value"])

                    first_decoded = self.parent.decode_map_entry(
                        left,
                        self.parent.map_data_y(top)
                    )
                    first_tile = first_decoded["tile"]
                    self.parent.current_h_flip = first_decoded["h_flip"]
                    self.parent.current_v_flip = first_decoded["v_flip"]

                    self.parent.selected_tile = first_tile
                    self.parent.selected_metatile = first_tile
                    per_page = self.parent.picker_per_page()
                    self.parent.metatile_page = self.parent.selected_metatile // per_page
    
                    self.parent.tile_view.sel_start_index = first_tile
                    self.parent.tile_view.sel_end_index = first_tile

                    self.parent.brush_w = right - left + 1
                    self.parent.brush_h = bottom - top + 1
                    self.parent.brush_tiles = brush_tiles

                self.parent.update_status()
                
                self.parent.tile_view.build()

                if self.parent.direct_tilemap_mode:
                    self.parent.tile_editor.build()
                    self.parent.palette_view.build()
                    self.parent.palette_controls.refresh_from_selected_colour()
 
                if (
                    hasattr(self.parent, "picker_window")
                    and self.parent.picker_window is not None
                    and self.parent.picker_window.isVisible()
                ):
                    self.parent.picker_window.picker.build()
                    self.parent.picker_window.refresh_status()

            self.update()
            return
        
    def wheelEvent(self, event):
        if self.base_image is None:
            event.accept()
            return

        old_idx = self.current_zoom_index()
        delta = event.angleDelta().y()

        if delta > 0 and old_idx < len(self.ZOOM_LEVELS) - 1:
            new_scale = self.ZOOM_LEVELS[old_idx + 1]
        elif delta < 0 and old_idx > 0:
            new_scale = self.ZOOM_LEVELS[old_idx - 1]
        else:
            event.accept()
            return

        self.set_scale(new_scale, event.position().toPoint())
        event.accept()

    def get_tile_image(self, tile_index, palette_number=0, h_flip=False, v_flip=False):
        if not hasattr(self, "tile_cache"):
            self.tile_cache = {}

        key = (tile_index, palette_number, h_flip, v_flip)

        if key in self.tile_cache:
            return self.tile_cache[key]

        tile = self.parent.tiles[tile_index]
        img = render_tile(tile, self.parent.palette, palette_number, h_flip, v_flip)
        self.tile_cache[key] = img
        return img

    def update_tile(self, mx, my):
        data_y = self.parent.map_data_y(my)
        entry = self.parent.decode_map_entry(mx, data_y)
        
        painter = QPainter(self.base_image)
        mt_img = self.parent.render_metatile_image_from_map_entry(entry["value"])
        cell = self.parent.metatile_pixel_size
        painter.drawImage(mx * cell, my * cell, mt_img)
        painter.end()

        cell = self.parent.metatile_pixel_size

        px = int(mx * cell * self.scale)
        py = int(my * cell * self.scale)
        pw = max(1, int(cell * self.scale))
        ph = max(1, int(cell * self.scale))
    
    def update_all_instances_of_metatile(self, mt_index):
        p = self.parent

        for display_y in range(p.map_height):
            data_y = p.map_data_y(display_y)

            for mx in range(p.map_width):
                entry = p.decode_map_entry(mx, data_y)

                if entry["tile"] == mt_index:
                    self.update_tile(mx, display_y)

            if (display_y & 15) == 0:
                QApplication.processEvents()

        self.update()

    def rebuild_all(self):
        self.tile_cache = {}
        self.redraw()
        
    def paintEvent(self, event):
        if self.base_image is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        painter.scale(self.scale, self.scale)
        painter.drawImage(0, 0, self.base_image)
        
        if getattr(self.parent, "map_screen_overlay", False):
            self.draw_screen_overlay(
                painter,
                self.parent.map_screen_overlay_x,
                self.parent.map_screen_overlay_y
            )
            
        grid_size = self.grid_modes[self.grid_index]
        if grid_size > 0:
            pen = QPen(QColor(255, 255, 255, 80))
            pen.setWidthF(0)
            painter.setPen(pen)

            w = self.base_image.width()
            h = self.base_image.height()

            for x in range(0, w, grid_size):
                painter.drawLine(x, 0, x, h)

            for y in range(0, h, grid_size):
                painter.drawLine(0, y, w, y)
                
        if self.copy_dragging and self.copy_start and self.copy_end:
            pen = QPen(QColor(0, 255, 255, 180))  # cyan
            pen.setWidthF(0)
            painter.setPen(pen)

            x1, y1 = self.copy_start
            x2, y2 = self.copy_end

            left = min(x1, x2)
            right = max(x1, x2)
            top = min(y1, y2)
            bottom = max(y1, y2)

            cell = self.parent.metatile_pixel_size

            x = left * cell
            y = top * cell
            w = (right - left + 1) * cell
            h = (bottom - top + 1) * cell

            painter.fillRect(x, y, w, h, QColor(0, 255, 255, 40))
            painter.drawRect(x, y, w - 1, h - 1)

        if 0 <= self.parent.hover_x < self.parent.map_width and 0 <= self.parent.hover_y < self.parent.map_height:

            cell = self.parent.metatile_pixel_size

            x = self.parent.hover_x * cell
            y = self.parent.hover_y * cell

            brush_w_px = self.parent.brush_w * cell
            brush_h_px = self.parent.brush_h * cell

            max_w_px = (self.parent.map_width - self.parent.hover_x) * cell
            max_h_px = (self.parent.map_height - self.parent.hover_y) * cell

            draw_w = min(brush_w_px, max_w_px)
            draw_h = min(brush_h_px, max_h_px)

            # ghost preview only for stamp brushes bigger than 1x1
            if self.parent.brush_w > 1 or self.parent.brush_h > 1:
                painter.setOpacity(0.5)

                for by in range(self.parent.brush_h):
                    for bx in range(self.parent.brush_w):
                        dx = self.parent.hover_x + bx
                        dy = self.parent.hover_y + by

                        if dx >= self.parent.map_width or dy >= self.parent.map_height:
                            continue

                        src_index = by * self.parent.brush_w + bx
                        val = self.parent.brush_tiles[src_index]

                        # if brush entry is just a raw metatile index, build a full map entry
                        if val < 1024:
                            entry_value = self.parent.make_map_entry_value(
                                tile_number=val,
                                palette_number=self.parent.selected_palette_group,
                                priority=self.parent.current_priority,
                                h_flip=self.parent.current_h_flip,
                                v_flip=self.parent.current_v_flip
                            )
                        else:
                            entry_value = val

                        ghost_img = self.parent.render_metatile_image_from_map_entry(entry_value)
                        painter.drawImage(dx * cell, dy * cell, ghost_img)

                painter.setOpacity(1.0)

            pen = QPen(QColor(255, 0, 0, 180))
            pen.setWidthF(0)
            painter.setPen(pen)

            # keep light fill only for larger brushes, optional but nice
            if self.parent.brush_w > 1 or self.parent.brush_h > 1:
                painter.fillRect(x, y, draw_w, draw_h, QColor(255, 0, 0, 20))
            else:
                painter.fillRect(x, y, draw_w, draw_h, QColor(255, 0, 0, 40))

            painter.drawRect(x, y, draw_w , draw_h )
                
    def leaveEvent(self, event):
        self.parent.hover_x = -1
        self.parent.hover_y = -1
        self.parent.update_status()
        self.update()
        super().leaveEvent(event)
    
    def paint_brush(self, mx, my):
        p = self.parent

        for by in range(p.brush_h):
            for bx in range(p.brush_w):
                dx = mx + bx
                dy = my + by

                # clip at edges (important!)
                if dx >= p.map_width or dy >= p.map_height:
                    continue

                src_index = by * p.brush_w + bx
                val = p.brush_tiles[src_index]

                # If this is a simple tile index (1x1 brush), build full entry
                if val < 1024:
                    entry_value = (
                        p.make_map_entry_value(
                            tile_number=val,
                            palette_number=p.selected_palette_group,
                            priority=p.current_priority,
                            h_flip=p.current_h_flip,
                            v_flip=p.current_v_flip
                        )
                    )
                else:
                    # already a full map entry
                    entry_value = val

                # --- get current map entry ---
                data_y = p.map_data_y(dy)
                entry = p.decode_map_entry(dx, data_y)
                old_value = entry["value"]

                if old_value != entry_value:
                    byte_idx = (data_y * p.map_width + dx) * 2
                    
                    old_lo = p.map_data[byte_idx]
                    old_hi = p.map_data[byte_idx + 1]

                    # record BOTH bytes for undo
                    p.record_map_change(byte_idx, (old_lo, old_hi), entry_value)

                    # write full entry
                    set_map_entry(p.map_data, p.map_width, dx, data_y, entry_value)
 
                    p.modified_map = True
                    self.update_tile(dx, dy)
                    
    def keyPressEvent(self, event):
        if getattr(self, "bg_preview_active", False):
            event.ignore()  # ignore any editing input
            return
        if event.key() == Qt.Key_H:
            self.parent.show_help()
            event.accept()
            return

        if event.key() == Qt.Key_O:
            current = getattr(self.parent, "map_screen_overlay", False)

            if not current:
                cx = getattr(self.parent, "hover_x", 0) * self.parent.metatile_pixel_size
                cy = getattr(self.parent, "hover_y", 0) * self.parent.metatile_pixel_size

                screen_w = 256
                screen_h = 224

                map_w_px = self.parent.map_width * self.parent.metatile_pixel_size
                map_h_px = self.parent.map_height * self.parent.metatile_pixel_size

                x = cx - (screen_w // 2)
                y = cy - (screen_h // 2)

                x = max(0, min(x, map_w_px - screen_w))
                y = max(0, min(y, map_h_px - screen_h))

                self.parent.map_screen_overlay_x = x
                self.parent.map_screen_overlay_y = y

            self.parent.map_screen_overlay = not current
            self.update()
            self.parent.update_status()
            event.accept()
            return
      
        if event.key() == Qt.Key_U:
            self.parent.undo_last_action()
            event.accept()
            return

        if event.key() == Qt.Key_Z and event.modifiers() & Qt.ControlModifier:
            self.parent.undo_last_action()
            event.accept()
            return

        # Direct map mode: P toggles SNES priority instead of picker
        if event.key() == Qt.Key_P:
            if self.parent.direct_tilemap_mode:
                self.parent.toggle_hover_map_priority()
            else:
                self.parent.open_metatile_picker()
            event.accept()
            return

        # Direct map mode: 0-7 set palette on hovered map tile
        if self.parent.direct_tilemap_mode:
            key_to_pal = {
                Qt.Key_0: 0,
                Qt.Key_1: 1,
                Qt.Key_2: 2,
                Qt.Key_3: 3,
                Qt.Key_4: 4,
                Qt.Key_5: 5,
                Qt.Key_6: 6,
                Qt.Key_7: 7,
            }

            if event.key() in key_to_pal:
                if self.parent.brush_w == 1 and self.parent.brush_h == 1:
                    self.parent.set_hover_map_palette(key_to_pal[event.key()])
                event.accept()
                return
                
        if event.key() == Qt.Key_Minus:
            self.parent.step_selected_metatile(-1)
            event.accept()
            return

        if event.key() == Qt.Key_Equal:
            self.parent.step_selected_metatile(1)
            event.accept()
            return

        if event.key() == Qt.Key_X:
            if self.parent.brush_w == 1 and self.parent.brush_h == 1:
                if not self.parent.toggle_hover_map_flip("x"):
                    self.parent.flip_brush_x()
            else:
                self.parent.flip_brush_x()
            event.accept()
            return

        if event.key() == Qt.Key_Y:
            if self.parent.brush_w == 1 and self.parent.brush_h == 1:
                if not self.parent.toggle_hover_map_flip("y"):
                    self.parent.flip_brush_y()
            else:
                self.parent.flip_brush_y()
            event.accept()
            return
            
    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.space_panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return

        super().keyReleaseEvent(event)                
    
    def decode_brush_entry_for_preview(self, val):
        p = self.parent

        if val < 1024:
            return {
                "tile": val,
                "palette": p.selected_palette_group,
                "h_flip": p.current_h_flip,
                "v_flip": p.current_v_flip,
            }

        return {
            "tile": p.map_entry_tile(val),
            "palette": (val >> 10) & 0x07,
            "h_flip": p.map_entry_h_flip(val),
            "v_flip": p.map_entry_v_flip(val),
        }
  
    def show_help(self):
        QMessageBox.information(self, "Help", HELP_TEXT)

    def draw_screen_overlay(self, painter, x, y):
        w = 256
        h = 224
        corner = 16

        right = x + w - 1
        bottom = y + h - 1

        pen = QPen(QColor(255, 255, 255, 220))
        pen.setWidthF(0)
        painter.setPen(pen)

        painter.drawLine(x, y, x + corner, y)
        painter.drawLine(x, y, x, y + corner)

        painter.drawLine(right, y, right - corner, y)
        painter.drawLine(right, y, right, y + corner)

        painter.drawLine(x, bottom, x + corner, bottom)
        painter.drawLine(x, bottom, x, bottom - corner)

        painter.drawLine(right, bottom, right - corner, bottom)
        painter.drawLine(right, bottom, right, bottom - corner)
 
class MetatilePickerWindow(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        px = self.parent.metatile_pixel_size
        ms = self.parent.metatile_size
        self.setWindowTitle(f"Metatile Picker ({ms}x{ms} / {px}x{px}px)")
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)
        self.setLayout(main_layout)

        self.picker = MetatilePicker(parent)
        main_layout.addWidget(self.picker)

        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(6)

        self.prev_btn = QPushButton("<")
        self.prev_btn.setFixedSize(28, 26)
        self.prev_btn.clicked.connect(self.prev_page)

        self.page_label = QLabel("Page 1/1")
        self.page_label.setFixedHeight(26)
        self.page_label.setAlignment(Qt.AlignCenter)

        self.next_btn = QPushButton(">")
        self.next_btn.setFixedSize(28, 26)
        self.next_btn.clicked.connect(self.next_page)

        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.page_label, 1)
        nav_layout.addWidget(self.next_btn)

        main_layout.addLayout(nav_layout)

        self.status_label = QLabel("Tile: 0")
        self.status_label.setFixedHeight(22)
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        main_layout.addWidget(self.status_label)

        self.picker.adjustSize()

        content_w = self.picker.sizeHint().width()
        content_h = self.picker.sizeHint().height()

        nav_h = 26
        status_h = 22
        spacing_total = 6 + 6
        margins_total = 12

        window_width = content_w + margins_total + 0
        window_height = content_h + nav_h + status_h + spacing_total + margins_total

        self.resize(window_width, window_height)
        self.setMinimumWidth(window_width)
        self.setMaximumWidth(window_width)
        self.setMinimumHeight(window_height)

        self.refresh_status()

    def refresh_status(self):
        total = len(self.parent.metatiles)
        per_page = self.picker.per_page
        total_pages = max(1, (total + per_page - 1) // per_page)

        self.parent.metatile_page = max(0, min(self.parent.metatile_page, total_pages - 1))
        current_page = self.parent.metatile_page + 1
        tile_num = getattr(self.parent, "selected_metatile", 0)

        self.page_label.setText(f"Page {current_page}/{total_pages}")
        self.prev_btn.setEnabled(self.parent.metatile_page > 0)
        self.next_btn.setEnabled(self.parent.metatile_page < total_pages - 1)      

        if 0 <= tile_num < len(self.parent.metatiles):
            mt = self.parent.metatiles[tile_num]

            chars = []
            palettes = []
            flips = []

            for value in mt:
                chars.append(value & 0x03FF)
                palettes.append((value >> 10) & 0x07)

                fx = bool(value & 0x4000)
                fy = bool(value & 0x8000)

                if fx and fy:
                    flips.append("xy")
                elif fx:
                    flips.append("x")
                elif fy:
                    flips.append("y")
                else:
                    flips.append("-")

            used_chars = len(set(chars))
            used_pals = sorted(set(palettes))
            flip_count = sum(1 for f in flips if f != "-")
 
            text = (
                f"Tile: {tile_num}   "
                f"Chars: {used_chars}   "
                f"Palettes: {used_pals}   "
                f"Flips: {flip_count}   "
                f"Total: {total}"
            )

            self.status_label.setText(text)
        else:
            self.status_label.setText(f"Tile: {tile_num}   Total: {total}")

    def prev_page(self):
        if self.parent.metatile_page > 0:
            self.parent.metatile_page -= 1
            self.picker.build()
            self.refresh_status()

    def next_page(self):
        per_page = self.picker.per_page
        max_page = max(0, (len(self.parent.metatiles) - 1) // per_page)

        if self.parent.metatile_page < max_page:
            self.parent.metatile_page += 1
            self.picker.build()
            self.refresh_status()

    def closeEvent(self, event):
        if hasattr(self.parent, "picker_window"):
            self.parent.picker_window = None

        if hasattr(self.parent, "update_picker_button_state"):
            QTimer.singleShot(0, self.parent.update_picker_button_state)

        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.NoModifier:
            key = event.key()

            if key == Qt.Key_P or key == Qt.Key_Escape:
                self.close()
                self.parent.update_picker_button_state()
                event.accept()
                return

            if event.key() == Qt.Key_P:
                self.parent.open_metatile_picker()
                event.accept()
                return
                
            if key == Qt.Key_Minus:
                self.parent.step_selected_metatile(-1)
                event.accept()
                return

            if key == Qt.Key_Equal:
                self.parent.step_selected_metatile(1)
                event.accept()
                return

        super().keyPressEvent(event)

class BGPreviewCanvas(QLabel):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self.dragging = False
        self.drag_start = None
        self.bg1_start = (0, 0)
        self.bg2_start = (0, 0)

    def build_combined_image(self):
        view_w = max(1, self.parent.scroll.viewport().width())
        view_h = max(1, self.parent.scroll.viewport().height())

        img = QImage(view_w, view_h, QImage.Format_RGB32)
        img.fill(QColor(0, 0, 0))

        if self.parent.bg1_on_top:
            bottom_img = self.parent.bg2_img_opaque
            bottom_x = self.parent.bg2_x
            bottom_y = self.parent.bg2_y

            top_img = self.parent.bg1_img_trans
            top_x = self.parent.bg1_x
            top_y = self.parent.bg1_y
        else:
            bottom_img = self.parent.bg1_img_opaque
            bottom_x = self.parent.bg1_x
            bottom_y = self.parent.bg1_y

            top_img = self.parent.bg2_img_trans
            top_x = self.parent.bg2_x
            top_y = self.parent.bg2_y

        painter = QPainter(img)
        painter.drawImage(0, 0, bottom_img, bottom_x, bottom_y, view_w, view_h)
        painter.drawImage(0, 0, top_img, top_x, top_y, view_w, view_h)
                    
        painter.end()
        return img

    def rebuild(self):
        img = self.build_combined_image()
        if self.parent.screen_overlay:
            painter = QPainter(img)
            self.draw_screen_overlay(
            painter,
            self.parent.screen_overlay_x,
            self.parent.screen_overlay_y
        )
            painter.end()
        self.setPixmap(QPixmap.fromImage(img))
        self.resize(img.size())
        self.parent.update_status_text()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start = event.globalPosition().toPoint()
            self.bg1_start = (self.parent.bg1_x, self.parent.bg1_y)
            self.bg2_start = (self.parent.bg2_x, self.parent.bg2_y)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.hover_x = int(event.position().x())
        self.hover_y = int(event.position().y())
        if self.dragging:
            current = event.globalPosition().toPoint()
            delta = current - self.drag_start
            
            #snap = bool(event.modifiers() & Qt.ShiftModifier)
            #self.parent.apply_drag_delta(delta.x(), delta.y(), self.bg1_start, self.bg2_start, snap)
            mods = event.modifiers()

            dx = delta.x()
            dy = delta.y()

            # Ctrl = lock X movement, only move Y
            if mods & Qt.ControlModifier:
                dx = 0

            # Alt = lock Y movement, only move X
            if mods & Qt.AltModifier:
                dy = 0

            snap = bool(mods & Qt.ShiftModifier)

            self.parent.apply_drag_delta(dx, dy, self.bg1_start, self.bg2_start, snap)

            self.rebuild()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
 
        if key == Qt.Key_H:
            self.parent.show_help()
            event.accept()
            return

        if event.key() == Qt.Key_O:
            current = getattr(self.parent, "screen_overlay", False)

            if not current:
                cx = getattr(self, "hover_x", self.width() // 2)
                cy = getattr(self, "hover_y", self.height() // 2)

                screen_w = 256
                screen_h = 224

                view_w = self.width()
                view_h = self.height()

                x = cx - (screen_w // 2)
                y = cy - (screen_h // 2)

                x = max(0, min(x, view_w - screen_w))
                y = max(0, min(y, view_h - screen_h))

                self.parent.screen_overlay_x = x
                self.parent.screen_overlay_y = y

            self.parent.screen_overlay = not current
            self.rebuild()
            event.accept()
            return
            
        if key == Qt.Key_1:
            self.parent.move_mode = 1
            self.parent.update_status_text()
            event.accept()
            return

        if key == Qt.Key_2:
            self.parent.move_mode = 2
            self.parent.update_status_text()
            event.accept()
            return

        if key == Qt.Key_3:
            self.parent.move_mode = 3
            self.parent.update_status_text()
            event.accept()
            return

        if key == Qt.Key_4:
            self.parent.move_mode = 4
            self.parent.apply_parallax_bg2()
            self.rebuild()
            event.accept()
            return
            
        if key == Qt.Key_S and event.modifiers() == Qt.NoModifier:
            self.parent.bg1_on_top = not self.parent.bg1_on_top
            self.rebuild()
            event.accept()
            return
            
        if key == Qt.Key_R:
            self.parent.reset_positions()
            self.rebuild()
            event.accept()
            return
            
        dx = 0
        dy = 0

        step = 1

        if event.modifiers() & Qt.ShiftModifier:
            step = 4

        if key == Qt.Key_Left:
            dx = step
        elif key == Qt.Key_Right:
            dx = -step
        elif key == Qt.Key_Up:
            dy = step
        elif key == Qt.Key_Down:
            dy = -step

        if dx != 0 or dy != 0:
            self.parent.nudge(dx, dy)
            self.rebuild()
            event.accept()
            return

        super().keyPressEvent(event)

    def draw_screen_overlay(self, painter, x, y):
        # SNES visible area guide: 256x224 pixels
        w = 256
        h = 224
        corner = 16

        right = x + w - 1
        bottom = y + h - 1

        pen = QPen(QColor(255, 255, 255, 240))
        pen.setWidthF(1.5)
        painter.setPen(pen)

        painter.drawLine(x, y, x + corner, y)
        painter.drawLine(x, y, x, y + corner)

        painter.drawLine(right, y, right - corner, y)
        painter.drawLine(right, y, right, y + corner)

        painter.drawLine(x, bottom, x + corner, bottom)
        painter.drawLine(x, bottom, x, bottom - corner)

        painter.drawLine(right, bottom, right - corner, bottom)
        painter.drawLine(right, bottom, right, bottom - corner)
    
class BGPreviewWindow(QWidget):
    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.screen_overlay = False
        self.screen_overlay_x = 0
        self.screen_overlay_y = 0
        mode = getattr(editor, "preview_bg2_mode", "next_map")

        has_next_map = (
            len(editor.map_data_list) >= 2 and
            editor.map_index < len(editor.map_data_list) - 1
        )

        has_direct_bg2 = (
            mode == "direct"
            and bool(getattr(editor, "preview_bg2_map", None))
        )

        has_project_bg2 = (
            mode == "project_map"
            and bool(getattr(editor, "preview_bg2_map", None))
        )

        project_bg2_index = None

        self.preview_bg2_min_y = preview_bg2_min_y

        if has_project_bg2:
            wanted = os.path.normcase(os.path.abspath(editor.preview_bg2_map))

            for i, path in enumerate(editor.map_paths):
                if os.path.normcase(os.path.abspath(path)) == wanted:
                    project_bg2_index = i
                    break

            if project_bg2_index is None:
                raise ValueError(f"preview_bg2_map is not in project maps: {editor.preview_bg2_map}")

            if project_bg2_index == editor.map_index:
                QMessageBox.information(
                    editor,
                    "BG Preview",
                    "This map is configured as the BG2 preview map, so there is no separate BG2 preview to show."
                )
                raise RuntimeError("BG2 preview cancelled")
                
        if not has_next_map and not has_direct_bg2 and not has_project_bg2:
            raise ValueError("BG Preview requires a next map, project_map BG2, or direct preview_bg2_map.")

        if not has_next_map and not has_preview_bg2:
            raise ValueError("BG Preview requires a next map or preview_bg2_map.")

        self.bg1_index = editor.map_index

        if mode == "project_map":
            self.bg2_index = project_bg2_index
        elif has_next_map:
            self.bg2_index = editor.map_index + 1
        else:
            self.bg2_index = None

        self.bg1_img_opaque = self.render_map_image(self.bg1_index, transparent_zero=False)
        self.bg1_img_trans = self.render_map_image(self.bg1_index, transparent_zero=True)

        if has_direct_bg2:
            self.bg2_img_opaque = self.render_preview_bg2_direct(transparent_zero=False)
            self.bg2_img_trans = self.render_preview_bg2_direct(transparent_zero=True)
        else:
            bg2_opaque = self.render_map_image(self.bg2_index, transparent_zero=False)
            bg2_trans = self.render_map_image(self.bg2_index, transparent_zero=True)

            rx, ry = self.resolve_bg2_repeat(bg2_opaque)

            self.bg2_img_opaque = self.repeat_image(bg2_opaque, repeat_x=rx, repeat_y=ry)
            self.bg2_img_trans = self.repeat_image(bg2_trans, repeat_x=rx, repeat_y=ry)

            rx, ry = self.resolve_bg2_repeat(bg2_opaque)

            self.bg2_img_opaque = self.repeat_image(
                bg2_opaque,
                repeat_x=rx,
                repeat_y=ry
            )

            self.bg2_img_trans = self.repeat_image(
                bg2_trans,
                repeat_x=rx,
                repeat_y=ry
            )
        self.bg1_x = 0
        self.bg1_y = 0
        self.bg2_x = 0
        self.bg2_y = 0

        # Keep track of manual BG2 offset relative to parallax
        self.bg2_offset_x = 0
        self.bg2_offset_y = 0
        
        self.move_mode = 3   # 1=BG1, 2=BG2, 3=Both
        self.bg1_on_top = True

        self.setWindowTitle("BG Preview")
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        #self.resize(1000, 700)
        view_w = 1000
        content_h = max(
            self.bg1_img_opaque.height(),
            self.bg2_img_opaque.height()
        )

        status_h = 0 #10 #70
        border_h = 40

        view_h = min(700, content_h + status_h + border_h)

        self.resize(view_w, view_h)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.canvas = BGPreviewCanvas(self)

        self.scroll = QScrollArea()
        self.scroll.setWidget(self.canvas)
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        layout.addWidget(self.status_label)
        layout.addWidget(self.scroll, 1)
        self.setLayout(layout)

        #self.canvas.rebuild()
        #self.canvas.setFocus()
        QTimer.singleShot(0, self.initial_rebuild)

    def closeEvent(self, event):
        self.editor.bg_preview_active = False

        if hasattr(self.editor, "bg_preview_window"):
            self.editor.bg_preview_window = None

        if hasattr(self.editor, "update_preview_button_state"):
            QTimer.singleShot(0, self.editor.update_preview_button_state)

        super().closeEvent(event)
        
    def initial_rebuild(self):
        self.canvas.rebuild()
        self.canvas.setFocus()
        
    def render_map_image(self, map_index, transparent_zero=False):
        p = self.editor
        map_data = p.map_data_list[map_index]
        map_width = p.map_widths[map_index]
        map_height = p.map_heights[map_index]

        cell = p.metatile_pixel_size
        img = QImage(map_width * cell, map_height * cell, QImage.Format_ARGB32)

        if transparent_zero:
            img.fill(0x00000000)
        else:
            img.fill(QColor(0, 0, 0))

        painter = QPainter(img)

        for display_y in range(map_height):
            if (display_y & 7) == 0:
                QApplication.processEvents()

            # Project maps follow project map_direction
            if p.map_direction == "bottom_top":
                data_y = (map_height - 1) - display_y
            else:
                data_y = display_y

            for mx in range(map_width):
                entry = get_map_entry(
                    map_data,
                    map_width,
                    mx,
                    data_y,
                    p.map_index_mask,
                    p.map_h_flip_mask,
                    p.map_v_flip_mask,
                )

                mt_img = p.render_metatile_image_from_map_entry_argb(
                    entry["value"],
                    transparent_zero
                )

                painter.drawImage(mx * cell, display_y * cell, mt_img)

        painter.end()
        return img

    def get_bottom_layer(self, min_x, min_y, bg1_img, bg2_img):
        if self.bg1_on_top:
            return bg2_img, self.bg2_x - min_x, self.bg2_y - min_y
        return bg1_img, self.bg1_x - min_x, self.bg1_y - min_y

    def get_top_layer(self, min_x, min_y, bg1_img, bg2_img):
        if self.bg1_on_top:
            return bg1_img, self.bg1_x - min_x, self.bg1_y - min_y
        return bg2_img, self.bg2_x - min_x, self.bg2_y - min_y

    def blit_with_transparency(self, dest_img, src_img, dx, dy):
        for y in range(src_img.height()):
            dest_y = dy + y
            if dest_y < 0 or dest_y >= dest_img.height():
                continue

            for x in range(src_img.width()):
                dest_x = dx + x
                if dest_x < 0 or dest_x >= dest_img.width():
                    continue

                rgb = src_img.pixel(x, y)

                # treat pure palette index 0 black as transparent on top layer
                # this assumes color 0 is black in your working palettes
                if rgb == QColor(0, 0, 0).rgb():
                    continue

                dest_img.setPixel(dest_x, dest_y, rgb)

    def apply_drag_delta(self, dx, dy, bg1_start, bg2_start, snap=False):
        if snap:
            dx = self.snap8(dx)
            dy = self.snap8(dy)

        if self.move_mode == 1:
            # BG1 only
            self.bg1_x = bg1_start[0] - dx
            self.bg1_y = bg1_start[1] - dy

        elif self.move_mode == 2:
            # BG2 only, update offset
            self.bg2_x = bg2_start[0] - dx
            self.bg2_y = bg2_start[1] - dy

            # Save offset relative to BG1
            self.bg2_offset_x = self.bg2_x - int(self.bg1_x * self.editor.preview_bg2_scroll_x)
            self.bg2_offset_y = self.bg2_y - int(self.bg1_y * self.editor.preview_bg2_scroll_y)

        elif self.move_mode == 3:
            # Both BG1 and BG2
            self.bg1_x = bg1_start[0] - dx
            self.bg1_y = bg1_start[1] - dy
            self.bg2_x = bg2_start[0] - dx
            self.bg2_y = bg2_start[1] - dy

            self.bg2_offset_x = self.bg2_x - int(self.bg1_x * self.editor.preview_bg2_scroll_x)
            self.bg2_offset_y = self.bg2_y - int(self.bg1_y * self.editor.preview_bg2_scroll_y)

        elif self.move_mode == 4:  # parallax
            self.bg1_x = bg1_start[0] - dx
            self.bg1_y = bg1_start[1] - dy

            # Clamp BG1 using project min_y
            view_w = max(1, self.scroll.viewport().width())
            view_h = max(1, self.scroll.viewport().height())
            min_bg1_y = getattr(self.editor, "preview_bg1_min_y", 0)

            self.bg1_x = max(0, min(self.bg1_x, max(0, self.bg1_img_opaque.width() - view_w)))
            self.bg1_y = max(min_bg1_y, min(self.bg1_y, max(0, self.bg1_img_opaque.height() - view_h)))

            # Apply parallax using BG2 offset
            self.apply_parallax_bg2()

        # Clamp final positions for both BGs
        self.clamp_bg_positions()
    
    def nudge(self, dx, dy):
        if self.move_mode == 1:
            self.bg1_x += dx
            self.bg1_y += dy

        elif self.move_mode == 2:
            self.bg2_x += dx
            self.bg2_y += dy

        elif self.move_mode == 3:
            self.bg1_x += dx
            self.bg1_y += dy
            self.bg2_x += dx
            self.bg2_y += dy

        elif self.move_mode == 4:
            self.bg1_x += dx
            self.bg1_y += dy
            self.apply_parallax_bg2()

        self.bg1_x = max(0, self.bg1_x)
        self.bg1_y = max(0, self.bg1_y)
        self.bg2_x = max(0, self.bg2_x)
        self.bg2_y = max(0, self.bg2_y)
        
        self.clamp_bg_positions()

    def update_status_text(self):
        move_text = {
            1: "BG1",
            2: "BG2",
            3: "BOTH",
            4: f"PARALLAX BG2=BG1*({self.editor.preview_bg2_scroll_x:g},{self.editor.preview_bg2_scroll_y:g})",
        }.get(self.move_mode, "?")

        top_text = "BG1" if self.bg1_on_top else "BG2"

        self.status_label.setText(
            f"Move: {move_text}   |   Top: {top_text}   |   BG1({self.bg1_x},{self.bg1_y}) BG2({self.bg2_x},{self.bg2_y})"
        )

    def snap8(self, v):
        return round(v / 8) * 8

    def reset_positions(self):
        if self.move_mode == 1:
            self.bg1_x = 0
            self.bg1_y = 0

        elif self.move_mode == 2:
            self.bg2_x = 0
            self.bg2_y = 0

        elif self.move_mode == 3:
            self.bg1_x = 0
            self.bg1_y = 0
            self.bg2_x = 0
            self.bg2_y = 0

        elif self.move_mode == 4:
            self.bg1_x = 0
            self.bg1_y = 0
            self.apply_parallax_bg2()

    def show_help(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("BG Preview Help")
        msg.setTextFormat(Qt.RichText)
        msg.setText(PREVIEW_HELP_TEXT)
        msg.exec()     

    def render_preview_bg2_direct(self, transparent_zero=False):
        p = self.editor

        path = p.preview_bg2_map
        map_width = p.preview_bg2_width
        map_height = p.preview_bg2_height
        map_format = getattr(p, "preview_bg2_format", "normal")

        if not path or not os.path.isfile(path):
            raise ValueError(f"preview_bg2_map not found: {path}")

        if p.preview_bg2_mode != "direct":
            raise ValueError("preview_bg2_mode currently only supports direct")

        map_data = load_map(path)

        if map_format == "snes_32x64_to_64x32":
            source_width = map_width // 2
            source_height = map_height * 2
            expected = source_width * source_height * 2
        else:
            source_width = map_width
            source_height = map_height
            expected = map_width * map_height * 2

        if len(map_data) != expected:
            raise ValueError(
                f"{path} is {len(map_data)} bytes, expected {expected} "
                f"for preview {map_width}x{map_height}, format={map_format}"
            )

        cell = 8
        img = QImage(map_width * cell, map_height * cell, QImage.Format_ARGB32)
        img.fill(0x00000000 if transparent_zero else QColor(0, 0, 0))

        painter = QPainter(img)

        for my in range(map_height):
            if (my & 7) == 0:
                QApplication.processEvents()

            for mx in range(map_width):

                if map_format == "snes_32x64_to_64x32":
                    # Display is 64x32.
                    # Source is 32x64:
                    #   source top 32x32    -> display left 32x32
                    #   source bottom 32x32 -> display right 32x32
                    if mx < source_width:
                        sx = mx
                        sy = my
                    else:
                        sx = mx - source_width
                        sy = my + map_height

                    off = (sy * source_width + sx) * 2
                else:
                    off = (my * map_width + mx) * 2

                value = map_data[off] | (map_data[off + 1] << 8)

                tile_number = value & 0x03FF
                palette_number = (value >> 10) & 0x07
                h_flip = bool(value & 0x4000)
                v_flip = bool(value & 0x8000)

                if tile_number >= len(p.tiles):
                    continue

                tile_img = render_tile_argb(
                    p.tiles[tile_number],
                    p.palette,
                    palette_number,
                    h_flip,
                    v_flip,
                    transparent_zero
                )

                painter.drawImage(mx * cell, my * cell, tile_img)

        painter.end()

        rx, ry = self.resolve_bg2_repeat(img)
        return self.repeat_image(img, repeat_x=rx, repeat_y=ry)
        
    def repeat_image(self, src_img, repeat_x=1, repeat_y=0):
        repeat_x = max(1, int(repeat_x))
        repeat_y = max(0, int(repeat_y))

        # repeat_y=0 means no vertical repeat, just original height
        tiles_x = repeat_x
        tiles_y = repeat_y if repeat_y > 0 else 1

        out_w = src_img.width() * tiles_x
        out_h = src_img.height() * tiles_y

        out = QImage(out_w, out_h, src_img.format())
        out.fill(0x00000000)

        painter = QPainter(out)

        for y in range(tiles_y):
            for x in range(tiles_x):
                painter.drawImage(x * src_img.width(), y * src_img.height(), src_img)

        painter.end()
        return out
        
    def apply_parallax_bg2(self):
        # BG2 follows BG1 with stored offset
        self.bg2_x = int(self.bg1_x * self.editor.preview_bg2_scroll_x) + self.bg2_offset_x
        self.bg2_y = int(self.bg1_y * self.editor.preview_bg2_scroll_y) + self.bg2_offset_y

        # Clamp BG2 using project min_y
        view_w = max(1, self.scroll.viewport().width())
        view_h = max(1, self.scroll.viewport().height())
        min_y = getattr(self.editor, "preview_bg2_min_y", 0)

        self.bg2_x = max(0, min(self.bg2_x, max(0, self.bg2_img_opaque.width() - view_w)))
        self.bg2_y = max(min_y, min(self.bg2_y, max(0, self.bg2_img_opaque.height() - view_h)))

    def clamp_bg_positions(self):
        view_w = max(1, self.scroll.viewport().width())
        view_h = max(1, self.scroll.viewport().height())

        # Clamp BG1 using new min_y
        min_bg1_y = getattr(self.editor, "preview_bg1_min_y", 0)
        self.bg1_x = max(0, min(self.bg1_x, max(0, self.bg1_img_opaque.width() - view_w)))
        self.bg1_y = max(min_bg1_y, min(self.bg1_y, max(0, self.bg1_img_opaque.height() - view_h)))

        # Clamp BG2
        min_bg2_y = getattr(self.editor, "preview_bg2_min_y", 0)
        self.bg2_x = max(0, min(self.bg2_x, max(0, self.bg2_img_opaque.width() - view_w)))
        self.bg2_y = max(min_bg2_y, min(self.bg2_y, max(0, self.bg2_img_opaque.height() - view_h)))
    
    def resolve_bg2_repeat(self, img):
        import math

        rx = self.editor.preview_bg2_repeat_x
        ry = self.editor.preview_bg2_repeat_y

        if rx == "fill":
            scroll_x = abs(self.editor.preview_bg2_scroll_x)
            scroll_x = max(1.0, scroll_x)
            needed_w = self.bg1_img_opaque.width() * scroll_x
            rx = max(1, math.ceil(needed_w / img.width()) + 2)

        if ry == "fill":
            scroll_y = abs(self.editor.preview_bg2_scroll_y)
            scroll_y = max(1.0, scroll_y)
            needed_h = self.bg1_img_opaque.height() * scroll_y
            ry = max(1, math.ceil(needed_h / img.height()) + 2)

        return rx, ry


        # SNES visible area guide: 256x224 pixels
        x = 0
        y = 0
        w = 256
        h = 224
        corner = 16

        pen = QPen(QColor(255, 255, 255, 180))
        pen.setWidthF(0)
        painter.setPen(pen)

        painter.drawLine(x, y, x + corner, y)
        painter.drawLine(x, y, x, y + corner)

        painter.drawLine(x + w, y, x + w - corner, y)
        painter.drawLine(x + w, y, x + w, y + corner)

        painter.drawLine(x, y + h, x + corner, y + h)
        painter.drawLine(x, y + h, x, y + h - corner)

        painter.drawLine(x + w, y + h, x + w - corner, y + h)
        painter.drawLine(x + w, y + h, x + w, y + h - corner)
    
class Editor(QWidget):
    def __init__(self, tiles_path, palette_path, map_paths, widths, heights, metatile_path=None, map_direction="top_bottom", metatile_size=2, map_index_mask=0x03FF, map_h_flip_bit=14, map_v_flip_bit=15):       
        super().__init__()

        self.map_view_dirty_full = False
        self.map_view_dirty_metatiles = set()
        self.debug_offsets = args.debug

        self.bg_preview_active = False
        self.map_screen_overlay = False      
        self.map_screen_overlay_x = 0
        self.map_screen_overlay_y = 0
        #self.setWindowIcon(QIcon("mode1_editor.ico"))

        self.map_paths = map_paths
        self.map_widths = widths
        self.map_heights = heights
        self.map_index = 0
        self.copied_color = None
        self.editor_mode = "map"
        
        self.map_width = self.map_widths[self.map_index]
        self.map_height = self.map_heights[self.map_index]

        self.map_direction = map_direction.strip().lower()
        if self.map_direction not in ("top_bottom", "bottom_top"):
            self.map_direction = "top_bottom"

        self.metatile_size = int(metatile_size)
        if self.metatile_size < 1:
            self.metatile_size = 2

        self.metatile_pixel_size = self.metatile_size * 8
        self.metatile_entry_count = self.metatile_size * self.metatile_size
        self.metatile_bytes = self.metatile_entry_count * 2
        # Direct 1x1 SNES tilemap mode:
        # map word is the actual SNES tile word, not a metatile index.
        self.direct_tilemap_mode = (self.metatile_size == 1)

        # Map-level format settings. These apply only to .map entries.
        # SNES tile/metatile words still use fixed SNES bits: $4000/$8000.
        self.map_index_mask = int(map_index_mask) & 0xFFFF
        self.map_h_flip_bit = int(map_h_flip_bit)
        self.map_v_flip_bit = int(map_v_flip_bit)
        self.map_h_flip_mask = 1 << self.map_h_flip_bit
        self.map_v_flip_mask = 1 << self.map_v_flip_bit
            
        self.tiles_path = tiles_path
        self.palette_path = palette_path
        
        # BG2 preview settings
        self.preview_bg2_map = proj.get("preview_bg2_map", "").strip() or None
        self.preview_bg2_width = int(proj.get("preview_bg2_width", 0))
        self.preview_bg2_height = int(proj.get("preview_bg2_height", 0))
        self.preview_bg2_mode = proj.get("preview_bg2_mode", "direct").strip().lower()
        self.preview_bg2_format = proj.get("preview_bg2_format", "normal").strip().lower()
        self.preview_bg2_repeat_x = parse_int_or_fill(proj.get("preview_bg2_repeat_x", 1), 1)
        self.preview_bg2_repeat_y = parse_int_or_fill(proj.get("preview_bg2_repeat_y", 0), 0)
        self.preview_bg2_scroll_x = float(proj.get("preview_bg2_scroll_x", 1.0))
        self.preview_bg2_scroll_y = float(proj.get("preview_bg2_scroll_y", 1.0))
        # Ensure BG2 min Y exists on the Editor object
        self.preview_bg2_min_y = int(proj.get("preview_bg2_min_y", 0))
        # Minimum Y offset for BG1 preview
        self.preview_bg1_min_y = int(proj.get("preview_bg1_min_y", 0))
        
        self.brush_w = 1
        self.brush_h = 1
        self.brush_tiles = [0]

        self.undo_stack = []
        self.current_paint_action = None

        missing = validate_project_files(self.tiles_path, self.palette_path, self.map_paths)
        if missing:
            msg = "The following project file(s) are missing:\n\n" + "\n".join(missing)
            QMessageBox.critical(self, "Missing Project File", msg)
            raise SystemExit(1)

        self.tiles = load_tiles(self.tiles_path)
        self.palette = load_palette_snes(self.palette_path)
        self.metatile_path = metatile_path

        if self.direct_tilemap_mode:
            # Direct tilemap mode: fake 1x1 metatiles so the existing
            # metatile/tile editor becomes a raw CHR tile editor.
            self.metatiles = [[i] for i in range(len(self.tiles))]
        elif self.metatile_path and os.path.isfile(self.metatile_path):
            self.metatiles = load_metatiles(self.metatile_path, self.metatile_size)
        else:
            self.metatiles = make_blank_metatiles(256, self.metatile_size)

        self.metatile_page = 0
        self.metatiles_per_page = 256
        self.selected_metatile = 0
        self.selected_subtile = 0   # 0=TL, 1=TR, 2=BL, 3=BR
 
        self.open_picker_btn = QPushButton("Picker")
        self.open_picker_btn.clicked.connect(self.open_metatile_picker)

        self.add_metatile_btn = QPushButton("Add Tile")
        self.add_metatile_btn.clicked.connect(self.add_metatile)

        self.del_metatile_btn = QPushButton("Del Tile")
        self.del_metatile_btn.clicked.connect(self.delete_metatile)
        
        self.map_data_list = [load_map(p) for p in self.map_paths]
        self.map_data = self.map_data_list[self.map_index]
        self.map_path = self.map_paths[self.map_index]

        undo_btn = QPushButton("Undo")
        undo_btn.clicked.connect(self.undo_last_action)

        prev_map_btn = QPushButton("<")
        prev_map_btn.setFixedWidth(30)
        prev_map_btn.clicked.connect(self.prev_map)

        next_map_btn = QPushButton(">")
        next_map_btn.setFixedWidth(30)
        next_map_btn.clicked.connect(self.next_map)

        self.map_label = QLabel("Map 1/1")

        for i, map_data in enumerate(self.map_data_list):
            expected = self.map_widths[i] * self.map_heights[i] * 2
            if len(map_data) != expected:
                raise ValueError(
                    f"{self.map_paths[i]} is {len(map_data)} bytes, expected {expected}"
                )
        self.undo_tile = None
        self.undo_tile_index = None   

        self.selected_tile = 0
        self.selected_color = 0
        self.selected_palette_group = 0
        self.selected_color_in_group = 0
        self.current_priority = False
        self.current_h_flip = False
        self.current_v_flip = False
        self.copied_tile = None

        self.modified_map = False
        self.modified_chr = False
        self.modified_pal = False

        self.hover_x = -1
        self.hover_y = -1

        self.status = QLabel()
        self.status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.tile_view = TileViewer(self.tiles, self.palette, self)
        self.tile_editor = TileEditor(self)
        self.tile_ops = TileOps(self)

        self.info_tile_label = QLabel("Tile:    0")
        self.info_palette_label = QLabel("Palette: 0")
        self.info_colour_label = QLabel("Colour:  0")

        self.info_xflip = QCheckBox("X Flip")
        self.info_yflip = QCheckBox("Y Flip")
        self.info_priority = QCheckBox("Priority")

        self.info_xflip.setEnabled(True)
        self.info_yflip.setEnabled(True)
        self.info_priority.setEnabled(True)

        self.info_xflip.clicked.connect(self.toggle_selected_subtile_hflip)
        self.info_yflip.clicked.connect(self.toggle_selected_subtile_vflip)
        self.info_priority.clicked.connect(self.toggle_selected_subtile_priority)
        
        info_top_row = QHBoxLayout()
        info_top_row.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        info_top_row.setSpacing(16)
        info_top_row.addWidget(self.info_tile_label)
        info_top_row.addWidget(self.info_palette_label)
        info_top_row.addWidget(self.info_colour_label)

        info_layout = QVBoxLayout()
        info_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        info_layout.setSpacing(6)
        info_layout.addLayout(info_top_row)
        info_layout.addWidget(self.info_xflip)
        info_layout.addWidget(self.info_yflip)
        info_layout.addWidget(self.info_priority)
       
        self.palette_view = PaletteView(self)
        self.palette_controls = PaletteControls(self)
        self.map_view = MapView(self)

        self.metatile_view = MetatileView(self)

        self.map_scroll = QScrollArea()
        self.map_scroll.setWidget(self.map_view)
        self.map_scroll.setWidgetResizable(False)

        self.metatile_scroll = QScrollArea()
        self.metatile_scroll.setWidget(self.metatile_view)
        self.metatile_scroll.setWidgetResizable(True)
        self.metatile_scroll.setAlignment(Qt.AlignLeft | Qt.AlignTop)


        self.tile_scroll = QScrollArea()
        self.tile_scroll.setWidget(self.tile_view)
        self.tile_scroll.setWidgetResizable(False)
        self.tile_scroll.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        tile_panel_width = (32 * TILE_SIZE * self.tile_view.tile_scale) + 4
        self.tile_scroll.setFixedWidth(tile_panel_width)

        tile_rows = (len(self.tiles) + self.tile_view.tiles_per_row - 1) // self.tile_view.tiles_per_row
        tile_panel_height = (tile_rows * TILE_SIZE * self.tile_view.tile_scale) + 4
        self.tile_scroll.setFixedHeight(tile_panel_height)

        load_proj_btn = QPushButton("Load Project")
        load_proj_btn.clicked.connect(self.load_project_dialog)

        save_proj_btn = QPushButton("Save Project")
        save_proj_btn.clicked.connect(self.save_project)

        #save_map_btn = QPushButton("Save Map")
        #save_map_btn.clicked.connect(self.save_map)

        #save_chr_btn = QPushButton("Save Chr")
        #save_chr_btn.clicked.connect(self.save_chr)

        #save_pal_btn = QPushButton("Save Palette")
        #save_pal_btn.clicked.connect(self.save_palette)

        zoom_in_btn = QPushButton("Zoom +")
        zoom_in_btn.clicked.connect(self.handle_zoom_in)

        zoom_out_btn = QPushButton("Zoom -")
        zoom_out_btn.clicked.connect(self.handle_zoom_out)

        fit_btn = QPushButton("Fit")
        fit_btn.clicked.connect(self.map_view.fit_to_window)

        self.preview_btn = QPushButton("Preview")
        self.preview_btn.clicked.connect(self.open_bg_preview)
        
        left_layout = QVBoxLayout()  

        left_layout.addWidget(self.tile_scroll)

        tile_row = QHBoxLayout()
        tile_row.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        tile_row.setSpacing(16)
        tile_row.addWidget(self.tile_editor)
        tile_row.addWidget(self.tile_ops)
        tile_row.addLayout(info_layout)
        left_layout.addLayout(tile_row)

        palette_row = QHBoxLayout()
        palette_row.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        palette_row.setSpacing(10)
        palette_row.addWidget(self.palette_view)
        palette_row.addWidget(self.palette_controls)
        left_layout.addLayout(palette_row)
        
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.map_scroll, 1)
        right_layout.addWidget(self.metatile_scroll, 1)

        self.metatile_scroll.hide()

        self.add_metatile_btn.hide()
        self.del_metatile_btn.hide()
        
        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)  # reduce gap between panels
        top_layout.setContentsMargins(2, 2, 2, 2)

        top_layout.addLayout(left_layout)
        top_layout.addLayout(right_layout, 1)  # map takes remaining space

        
        controls = QHBoxLayout()
        controls.setSpacing(6)
        controls.setContentsMargins(2, 2, 2, 2)

        controls.addWidget(load_proj_btn)
        controls.addWidget(save_proj_btn)
        #controls.addWidget(save_map_btn)
        #controls.addWidget(save_chr_btn)
        #controls.addWidget(save_pal_btn)
        controls.addWidget(undo_btn)
        controls.addWidget(zoom_out_btn)
        controls.addWidget(zoom_in_btn)
        controls.addWidget(fit_btn)

        
        self.grid_btn = QPushButton("Grid")
        self.grid_btn.clicked.connect(self.toggle_grid_current_view)
        controls.addWidget(self.grid_btn)
        
        self.add_width_btn = QPushButton("X+1")
        self.add_width_btn.clicked.connect(self.expand_map_width)

        self.add_height_btn = QPushButton("Y+1")
        self.add_height_btn.clicked.connect(self.expand_map_height)
                
        controls.addWidget(self.status)  
        controls.addWidget(self.open_picker_btn)

        controls.addWidget(self.preview_btn)
        
        controls.addWidget(self.add_width_btn)
        controls.addWidget(self.add_height_btn)


        self.mode_toggle_btn = QPushButton("Edit Tiles")
        self.mode_toggle_btn.clicked.connect(self.toggle_metatile_mode)
                
        controls.addWidget(self.add_metatile_btn)
        controls.addWidget(self.del_metatile_btn)

        controls.addWidget(self.mode_toggle_btn)
        
        controls.addWidget(prev_map_btn)
        controls.addWidget(self.map_label)
        controls.addWidget(next_map_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addLayout(controls)

        #compact_buttons = [
        #    load_proj_btn, save_proj_btn, save_map_btn, save_chr_btn, save_pal_btn,
        #    undo_btn,fit_btn,
        #    zoom_out_btn, zoom_in_btn, prev_map_btn, next_map_btn, self.grid_btn,
        #    self.mode_toggle_btn, self.open_picker_btn, self.preview_btn,
        #    self.add_metatile_btn, self.del_metatile_btn, self.add_width_btn, self.add_height_btn
        #]
        compact_buttons = [
            load_proj_btn, save_proj_btn,
            undo_btn,fit_btn,
            zoom_out_btn, zoom_in_btn, prev_map_btn, next_map_btn, self.grid_btn,
            self.mode_toggle_btn, self.open_picker_btn, self.preview_btn,
            self.add_metatile_btn, self.del_metatile_btn, self.add_width_btn, self.add_height_btn
        ]

        for btn in compact_buttons:
            btn.setFixedHeight(26)
            btn.setStyleSheet("padding-left: 6px; padding-right: 6px; color: #bbb;")
        
        self.grid_btn.setStyleSheet("padding: 6px;")
        self.grid_btn.setFixedWidth(75)
        
        self.status.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        
        self.setLayout(main_layout)
        self.setWindowTitle("Mode1 Editor (Stage 1)")
        self.resize(1400, 900)
        self.showMaximized()
        self.setFocusPolicy(Qt.StrongFocus)
      
        self.tile_scroll.hide()
        self.tile_editor.hide()
        self.tile_ops.hide()
        self.palette_view.hide()
        self.palette_controls.hide()
        self.info_tile_label.hide()
        self.info_palette_label.hide()
        self.info_colour_label.hide()
        self.info_xflip.hide()
        self.info_yflip.hide()
        self.info_priority.hide()
        
        self.refresh_editor_mode()
        # FORCE default zoom to 1:1
        self.map_view.set_scale(1.0)
        self.update_status()

    def update_status(self):
        # --- MAP DEBUG OFFSET ---
        debug_text = ""
        if self.debug_offsets and self.hover_x >= 0 and self.hover_y >= 0:
            offset = ((self.hover_y * self.map_width) + self.hover_x) * 2
            debug_text = f"  MapOff:${offset:04X}"

        # --- HOVER TEXT ---
        hover_text = ""
        if self.hover_x >= 0 and self.hover_y >= 0:
            entry = self.decode_map_entry(
                self.hover_x,
                self.map_data_y(self.hover_y)
            )

            hover_tile = entry["tile"]
            hover_xflip = entry["h_flip"]
            hover_yflip = entry["v_flip"]

            if self.map_direction == "bottom_top":
                display_hover_y = (self.map_height - 1) - self.hover_y
            else:
                display_hover_y = self.hover_y

            flip_text = ""
            if hover_xflip or hover_yflip:
                flip_text = " flip "
                if hover_xflip:
                    flip_text += "X"
                if hover_yflip:
                    flip_text += "Y"

            if self.direct_tilemap_mode:
                hover_pal = entry["palette"]
                hover_pri = entry["priority"]
                hover_val = entry["value"]
                val_text = f" Val:${hover_val:04X}" if self.debug_offsets else ""
                pri_text = " P" if hover_pri else ""

                hover_text = (
                    f" Hover: ({self.hover_x},{display_hover_y})"
                    f" Tile:{hover_tile}"
                    f" Pal:{hover_pal}"
                    f"{pri_text}"
                    f"{flip_text}"
                    f"{val_text}"
                    f"{debug_text}"
                )
            else:
                hover_text = (
                    f" Hover: ({self.hover_x},{display_hover_y})"
                    f" Tile:{hover_tile}"
                    f"{flip_text}"
                    f"{debug_text}"
                )

        # --- ZOOM / MODE ---
        zoom = self.map_view.zoom_text() if hasattr(self, "map_view") else "1:1"
        edit_mode = f" ({self.editor_mode})"

        if self.editor_mode == "metatile":
            zoom = f"{self.metatile_view.display_scale}x"

        # --- BRUSH / METATILE INFO ---
        if self.editor_mode == "metatile":
            mt_debug_text = ""

            if self.debug_offsets:
                entries_per_mt = self.metatile_size * self.metatile_size
                slot = self.selected_subtile

                offset = ((self.selected_metatile * entries_per_mt) + slot) * 2
                value = self.metatiles[self.selected_metatile][slot]

                mt_debug_text = f"  MtlOff:${offset:04X} Val:${value:04X}"

            brush_text = f" Metatile: {self.selected_metatile}{mt_debug_text}"
        else:
            brush_text = f" Brush: {self.brush_w}x{self.brush_h}"

        # --- FINAL STATUS TEXT ---
        self.status.setText(
            f"Zoom: {zoom}{edit_mode}{hover_text}{brush_text}"
        )

        # --- OTHER UI UPDATES ---
        self.refresh_map_tile_info()
        self.update_window_title()

        if self.editor_mode == "map":
            total = len(self.map_paths)
            current = self.map_index + 1
            self.map_label.setText(
                f"Map {current}/{total} ({self.map_width}x{self.map_height})"
            )
        else:
            self.refresh_metatile_paging()

        self.update_picker_button_state()
        self.update_grid_button_state()
        
    def save_map(self):
        path = self.map_paths[self.map_index]
        data = self.map_data_list[self.map_index]

        with open(path, "wb") as f:
            f.write(data)

        self.modified_map = False
        self.update_status()

    def save_chr(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Chr", "chars.chr")
        if path:
            save_tiles(path, self.tiles)
            self.modified_chr = False
            self.update_status()

    def save_palette(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Palette", "palette.pal")
        if path:
            save_palette_snes(path, self.palette)
            self.modified_pal = False
            self.update_status()
               
    def load_project_dialog(self):

        path, _ = QFileDialog.getOpenFileName(self, "Load Project", "", "*.m1e")
        if not path:
            return

        # store project path for Save All reuse
        self.project_path = path

        proj = {}
        with open(path, "r") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    proj[k.strip()] = v.strip()
         
        # store project path for Save All reuse
        self.project_path = path
    
        proj = {}
        with open(path, "r") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    proj[k.strip()] = v.strip()

        # reload data
        tiles_path = proj["tiles"]
        palette_path = proj["palette"]
        
        metatile_path = proj.get("metatiles", "").strip()
        
        if not metatile_path:
            metatile_path = None
        map_direction = proj.get("map_direction", "top_bottom").strip().lower()

        self.map_direction = proj.get("map_direction", "top_bottom").strip().lower()
        if self.map_direction not in ("top_bottom", "bottom_top"):
            self.map_direction = "top_bottom"
            
        if "maps" in proj:
            map_paths = [p.strip() for p in proj["maps"].split(",") if p.strip()]
        elif "map" in proj:
            map_paths = [proj["map"].strip()]
        else:
            map_paths = []

        missing = validate_project_files(tiles_path, palette_path, map_paths)
        if missing:
            print("Missing project file(s):")
            for path in missing:
                print(f"  {path}")
            sys.exit(1)
    
        self.tiles_path = tiles_path
        self.palette_path = palette_path
        self.metatile_path = metatile_path
        self.map_paths = map_paths

        if len(map_paths) == 0:
            raise ValueError("Project does not define any map files")

        if "width" not in proj or "height" not in proj:
            raise ValueError("Project must define width and height")

        self.map_widths = parse_project_dimension_list(proj["width"], len(map_paths), "width")
        self.map_heights = parse_project_dimension_list(proj["height"], len(map_paths), "height")

        self.map_index = 0
        self.map_width = self.map_widths[self.map_index]
        self.map_height = self.map_heights[self.map_index]

        self.tiles = load_tiles(self.tiles_path)
        self.palette = load_palette_snes(self.palette_path)
        self.map_data_list = [load_map(p) for p in self.map_paths]
        self.map_data = self.map_data_list[self.map_index]
        self.map_path = self.map_paths[self.map_index]

        # ensure metatile_size is set BEFORE loading
        self.metatile_size = int(proj.get("metatile_size", 2))
        if self.metatile_size < 1:
            self.metatile_size = 2

        self.metatile_pixel_size = self.metatile_size * 8
        self.metatile_entry_count = self.metatile_size * self.metatile_size
        self.metatile_bytes = self.metatile_entry_count * 2

        if self.metatile_path and os.path.isfile(self.metatile_path):
            self.metatiles = load_metatiles(self.metatile_path, self.metatile_size)
        else:
            self.metatiles = make_blank_metatiles(256, self.metatile_size)

        self.metatile_page = 0
        self.selected_metatile = 0
        self.selected_subtile = 0
        for i, map_data in enumerate(self.map_data_list):
            expected = self.map_widths[i] * self.map_heights[i] * 2
            if len(map_data) != expected:
                raise ValueError(
                    f"{self.map_paths[i]} is {len(map_data)} bytes, expected {expected}"
                )
        # refresh everything
        
        self.metatile_view.reset_zoom()
        
        self.tile_view.tiles = self.tiles
        self.tile_view.palette = self.palette
        self.palette_view.build()
        self.tile_view.build()
        self.tile_editor.build()
        self.map_view.redraw()
        self.position_map_view_for_direction()
        
        self.metatile_view.build()
        
        self.modified_map = False
        self.modified_chr = False
        self.modified_pal = False
        self.hover_x = -1
        self.hover_y = -1

        self.update_status()

    def save_project(self):
        # If a project was loaded or already saved before, save directly to it.
        if hasattr(self, "project_path") and self.project_path:
            name = self.project_path
        else:
            name, _ = QFileDialog.getSaveFileName(
                self,
                "Save All",
                "new_project.m1e",
                "Project Files (*.m1e)"
            )
            if not name:
                return

            if not name.lower().endswith(".m1e"):
                name += ".m1e"

            self.project_path = name

        # --- SAVE ALL DATA FIRST ---
        for i, path in enumerate(self.map_paths):
            with open(path, "wb") as f:
                f.write(self.map_data_list[i])

        save_tiles(self.tiles_path, self.tiles)
        save_palette_snes(self.palette_path, self.palette)

        if self.metatile_path:
            save_metatiles(self.metatile_path, self.metatiles)

        # --- SAVE PROJECT FILE ---
        with open(name, "w") as f:
            f.write(f"palette={self.palette_path}\n")
            f.write(f"tiles={self.tiles_path}\n")

            if self.metatile_path:
                f.write(f"metatiles={self.metatile_path}\n")

            f.write(f"metatile_size={self.metatile_size}\n")

            if len(self.map_paths) == 1:
                f.write(f"map={self.map_paths[0]}\n")
            else:
                f.write("maps=" + ",".join(self.map_paths) + "\n")

            if len(set(self.map_widths)) == 1:
                f.write(f"width={self.map_widths[0]}\n")
            else:
                f.write("width=" + ",".join(str(w) for w in self.map_widths) + "\n")

            if len(set(self.map_heights)) == 1:
                f.write(f"height={self.map_heights[0]}\n")
            else:
                f.write("height=" + ",".join(str(h) for h in self.map_heights) + "\n")

            f.write(f"map_direction={self.map_direction}\n")
            f.write(f"map_index_mask=0x{self.map_index_mask:04X}\n")
            f.write(f"map_h_flip_bit={self.map_h_flip_bit}\n")
            f.write(f"map_v_flip_bit={self.map_v_flip_bit}\n")

        self.modified_map = False
        self.modified_chr = False
        self.modified_pal = False
        self.map_view_dirty_full = False
        self.map_view_dirty_metatiles.clear()
        self.update_status()
    
    def showEvent(self, event):
        super().showEvent(event)
        self.map_view.fit_to_window()

    def apply_shortcut(self, action):
        if action == "flip_x":
            self.tile_ops.flip_x()
        elif action == "flip_y":
            self.tile_ops.flip_y()
        elif action == "rotate_cw":
            self.tile_ops.rotate_cw()
        elif action == "rotate_ccw":
            self.tile_ops.rotate_ccw()
        elif action == "clear":
            self.tile_ops.clear_tile()
        elif action == "invert":
            self.tile_ops.invert_tile()
        elif action == "copy":
            self.tile_ops.copy_tile()
        elif action == "paste":
            self.tile_ops.paste_tile()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_H:
            self.show_help()
            event.accept()
            return

        super().keyPressEvent(event)
        if event.isAutoRepeat():
            event.ignore()
            return

        if event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_Z:
                self.undo_last_action()
                event.accept()
                return

        super().keyPressEvent(event)    
        
        key = event.key()
        mods = event.modifiers()
        
        if mods == Qt.NoModifier and self.editor_mode == "map":
            if key == Qt.Key_X:
                self.flip_brush_x()
                event.accept()
                return

            if key == Qt.Key_Y:
                self.flip_brush_y()
                event.accept()
                return
                
        if key == Qt.Key_E and mods == Qt.NoModifier:
            self.toggle_metatile_mode()
            event.accept()
            return

        if key == Qt.Key_Y and mods == Qt.NoModifier:
            if self.editor_mode == "metatile":
                self.toggle_selected_subtile_vflip()
            elif self.map_view.hasFocus():
                self.flip_brush_y()
            else:
                self.apply_shortcut("flip_y")
            event.accept()
            return

        if key == Qt.Key_P and mods == Qt.NoModifier and self.editor_mode == "map":
            self.open_metatile_picker()
            event.accept()
            return
               
        if mods == Qt.NoModifier and Qt.Key_0 <= key <= Qt.Key_7:
            palette_group = key - Qt.Key_0

            if self.editor_mode == "metatile":
                if self.direct_tilemap_mode:
                    self.selected_palette_group = palette_group
                    self.selected_color = (palette_group * 16) + self.selected_color_in_group

                    self.tile_view.build()
                    self.tile_editor.build()
                    self.metatile_view.build()
                    self.palette_view.build()
                    self.palette_controls.refresh_from_selected_colour()
                    self.refresh_map_tile_info()
                    self.update_status()
                    self.map_view.rebuild_all()
                else:
                    self.update_selected_subtile_entry(palette_group=palette_group)
            else:
                self.selected_palette_group = palette_group
                self.selected_color = (palette_group * 16) + self.selected_color_in_group
                self.tile_view.build()
                self.tile_editor.build()
                self.palette_view.build()
                self.palette_controls.refresh_from_selected_colour()
                self.refresh_map_tile_info()
                self.update_status()

            event.accept()
            return          
          
        if key == Qt.Key_R and mods == Qt.NoModifier:
            self.apply_shortcut("rotate_cw")
            event.accept()
            return

        if key == Qt.Key_R and mods == Qt.ShiftModifier:
            self.apply_shortcut("rotate_ccw")
            event.accept()
            return

        if key == Qt.Key_Delete and mods == Qt.NoModifier:
            self.apply_shortcut("clear")
            event.accept()
            return

        if key == Qt.Key_I and mods == Qt.NoModifier:
            self.apply_shortcut("invert")
            event.accept()
            return

        if key == Qt.Key_C and mods == Qt.NoModifier:
            self.apply_shortcut("copy")
            event.accept()
            return

        if key == Qt.Key_V and mods == Qt.NoModifier:
            self.apply_shortcut("paste")
            event.accept()
            return
            
        super().keyPressEvent(event)

    def push_undo(self):
        self.undo_tile_index = self.selected_tile
        self.undo_tile = bytearray(self.tiles[self.selected_tile])    

    def undo(self):
        if self.undo_tile is not None and self.undo_tile_index is not None:
            self.tiles[self.undo_tile_index] = bytearray(self.undo_tile)
            self.selected_tile = self.undo_tile_index
            self.modified_chr = True
            self.tile_editor.build()
            self.tile_view.build()
            self.map_view.redraw()
            self.palette_controls.refresh_from_selected_colour()
            self.update_status()

    def update_window_title(self):
        name = "Mode1 Tile/Map Editor"

        if hasattr(self, "map_path"):
            base = os.path.splitext(os.path.basename(self.tiles_path))[0]            
            name += f" - {base}"

        if self.modified_map or self.modified_chr or self.modified_pal:
            name += " *"

        self.setWindowTitle(name)
 
    def closeEvent(self, event):
        if (
            hasattr(self, "picker_window")
            and self.picker_window is not None
            and self.picker_window.isVisible()
        ):
            self.picker_window.close()
            
        if self.modified_map or self.modified_chr or self.modified_pal:
            from PySide6.QtWidgets import QMessageBox

            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Save all before exiting?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )

            if reply == QMessageBox.Yes:
                self.save_project()
                event.accept()
            elif reply == QMessageBox.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def update_current_map(self):
        self.map_data = self.map_data_list[self.map_index]
        self.map_path = self.map_paths[self.map_index]
        self.map_width = self.map_widths[self.map_index]
        self.map_height = self.map_heights[self.map_index]
        self.map_view.redraw()
        self.position_map_view_for_direction()
        self.update_status()

    def prev_map(self):
        if self.editor_mode == "map":
            if self.map_index > 0:
                self.map_index -= 1
                self.update_current_map()
        else:
            if self.metatile_page > 0:
                self.metatile_page -= 1
                self.metatile_view.build()
                self.update_status()

    def next_map(self):
        if self.editor_mode == "map":
            if self.map_index < len(self.map_paths) - 1:
                self.map_index += 1
                self.update_current_map()
        else:
            per_page = self.metatile_view.per_page
            max_page = (len(self.metatiles) - 1) // per_page

            if self.metatile_page < max_page:
                self.metatile_page += 1
                self.metatile_view.build()
                self.update_status()

    def begin_paint_action(self):
        self.current_paint_action = []

    def record_map_change(self, idx, old_value, new_value):
        if self.current_paint_action is None:
            self.current_paint_action = []

        # if this tile was already changed in the same action,
        # keep the original old_value but update the final new_value
        for i, (rec_idx, rec_old, rec_new) in enumerate(self.current_paint_action):
            if rec_idx == idx:
                self.current_paint_action[i] = (rec_idx, rec_old, new_value)
                return

        self.current_paint_action.append((idx, old_value, new_value))

    def end_paint_action(self):
        if self.current_paint_action:
            self.undo_stack.append(self.current_paint_action)
        self.current_paint_action = None

    def undo_last_action(self):
        if not self.undo_stack:
            return

        action = self.undo_stack.pop()

        for idx, old_value, new_value in reversed(action):
            old_lo, old_hi = old_value

            self.map_data[idx] = old_lo
            self.map_data[idx + 1] = old_hi

            tile_index = idx // 2
            mx = tile_index % self.map_width
            data_y = tile_index // self.map_width
            display_y = self.map_display_y(data_y)

            self.map_view.update_tile(mx, display_y)

        self.modified_map = True
        self.update_status()
        
    def refresh_map_tile_info(self):
        if self.editor_mode == "metatile" and 0 <= self.selected_metatile < len(self.metatiles):
            mt = self.metatiles[self.selected_metatile]

            value = mt[self.selected_subtile]
            tile_number = value & 0x03FF
            palette = (value >> 10) & 0x07
            h_flip = bool(value & 0x4000)
            v_flip = bool(value & 0x8000)
            priority = bool(value & 0x2000)

            slot_name = self.subtile_label(self.selected_subtile)

            self.info_tile_label.setText(f"Chr: {tile_number}")
            self.info_palette_label.setText(f"Palette: {palette}")
            self.info_colour_label.setText(f"Slot: {slot_name}")

            self.info_xflip.setChecked(h_flip)
            self.info_yflip.setChecked(v_flip)
            self.info_priority.setChecked(priority)
        else:
            self.info_tile_label.setText(f"Tile: {self.selected_tile:>4}")
            self.info_palette_label.setText(f"Palette: {self.selected_palette_group}")
            self.info_colour_label.setText(f"Colour: {self.selected_color_in_group}")

            self.info_xflip.setChecked(self.current_h_flip)
            self.info_yflip.setChecked(self.current_v_flip)
            self.info_priority.setChecked(self.current_priority)

    def flip_brush_x(self):
        if self.brush_w == 1 and self.brush_h == 1:
            self.current_h_flip = not self.current_h_flip
            self.update_status()
            return

        new_tiles = []

        for row in range(self.brush_h):
            row_vals = []
            for col in range(self.brush_w):
                idx = row * self.brush_w + col
                val = self.brush_tiles[idx]

                if val < 1024:
                    # tile-sheet brush entry (tile index only)
                    row_vals.append(val)
                else:
                    # full map entry: toggle configured map H flip bit
                    row_vals.append(self.toggle_map_entry_h_flip(val))

            row_vals.reverse()
            new_tiles.extend(row_vals)

        self.brush_tiles = new_tiles
        self.current_h_flip = not self.current_h_flip
        self.update_status()

    def flip_brush_y(self):
        if self.brush_w == 1 and self.brush_h == 1:
            self.current_v_flip = not self.current_v_flip
            self.update_status()
            return

        rows = []

        for row in range(self.brush_h):
            row_vals = []
            for col in range(self.brush_w):
                idx = row * self.brush_w + col
                val = self.brush_tiles[idx]

                if val < 1024:
                    # tile-sheet brush entry (tile index only)
                    row_vals.append(val)
                else:
                    # full map entry: toggle configured map V flip bit
                    row_vals.append(self.toggle_map_entry_v_flip(val))

            rows.append(row_vals)

        rows.reverse()

        new_tiles = []
        for row_vals in rows:
            new_tiles.extend(row_vals)

        self.brush_tiles = new_tiles
        self.current_v_flip = not self.current_v_flip
        self.update_status()
        
    def toggle_metatile_mode(self):
        #if self.direct_tilemap_mode:
        #    return
        if self.editor_mode == "map":
            self.editor_mode = "metatile"
        else:
            self.editor_mode = "map"

            if self.map_view_dirty_full:
                QApplication.setOverrideCursor(Qt.WaitCursor)
                try:
                    QApplication.processEvents()
                    self.map_view.rebuild_all()
                finally:
                    QApplication.restoreOverrideCursor()

                self.map_view_dirty_full = False
                self.map_view_dirty_metatiles.clear()

            elif self.map_view_dirty_metatiles:
                for mt_index in list(self.map_view_dirty_metatiles):
                    self.map_view.update_all_instances_of_metatile(mt_index)

                self.map_view_dirty_metatiles.clear()

        self.refresh_editor_mode()

    def refresh_views(self):
        self.tile_view.build()
        self.tile_editor.build()
        self.palette_view.build()

        if self.editor_mode == "map":
            if self.map_view_dirty_full:
                self.map_view.rebuild_all()
                self.map_view_dirty_full = False
                self.map_view_dirty_metatiles.clear()
            elif self.map_view_dirty_metatiles:
                for mt_index in list(self.map_view_dirty_metatiles):
                    self.map_view.update_all_instances_of_metatile(mt_index)
                self.map_view_dirty_metatiles.clear()
        else:
            if hasattr(self, "metatile_view"):
                self.metatile_view.build()

        self.update_status()

    def render_metatile_image(self, metatile_words):
        size = self.metatile_size
        pixel_size = self.metatile_pixel_size

        img = QImage(pixel_size, pixel_size, QImage.Format_RGB32)
        img.fill(QColor(0, 0, 0))

        painter = QPainter(img)

        for i, value in enumerate(metatile_words):
            if i >= self.metatile_entry_count:
                break

            tx = i % size
            ty = i // size

            tile_number = value & 0x03FF
            if self.direct_tilemap_mode:
                palette_number = self.selected_palette_group
            else:
                palette_number = (value >> 10) & 0x07
            h_flip = bool(value & 0x4000)
            v_flip = bool(value & 0x8000)

            if tile_number >= len(self.tiles):
                tile_number = 0

            tile_img = render_tile(
                self.tiles[tile_number],
                self.palette,
                palette_number,
                h_flip,
                v_flip
            )

            painter.drawImage(tx * 8, ty * 8, tile_img)

        painter.end()
        return img
        
    def render_metatile_image_from_map_entry(self, map_entry_value):
        if self.direct_tilemap_mode:
            tile_number = map_entry_value & 0x03FF
            palette_number = (map_entry_value >> 10) & 0x07
            h_flip = bool(map_entry_value & 0x4000)
            v_flip = bool(map_entry_value & 0x8000)

            img = QImage(8, 8, QImage.Format_RGB32)
            img.fill(QColor(0, 0, 0))

            if tile_number >= len(self.tiles):
                return img

            return render_tile(
                self.tiles[tile_number],
                self.palette,
                palette_number,
                h_flip,
                v_flip
            )
        mt_index = self.map_entry_tile(map_entry_value)
        map_h_flip = self.map_entry_h_flip(map_entry_value)
        map_v_flip = self.map_entry_v_flip(map_entry_value)

        size = self.metatile_size
        pixel_size = self.metatile_pixel_size

        img = QImage(pixel_size, pixel_size, QImage.Format_RGB32)
        img.fill(QColor(0, 0, 0))

        if mt_index >= len(self.metatiles):
            return img

        mt = self.metatiles[mt_index]

        painter = QPainter(img)

        for src_i, sub_value in enumerate(mt):
            if src_i >= self.metatile_entry_count:
                break

            src_x = src_i % size
            src_y = src_i // size

            dst_x = (size - 1 - src_x) if map_h_flip else src_x
            dst_y = (size - 1 - src_y) if map_v_flip else src_y

            tile_number = sub_value & 0x03FF
            sub_palette = (sub_value >> 10) & 0x07
            sub_h_flip = bool(sub_value & 0x4000)
            sub_v_flip = bool(sub_value & 0x8000)

            final_h_flip = sub_h_flip ^ map_h_flip
            final_v_flip = sub_v_flip ^ map_v_flip

            if tile_number >= len(self.tiles):
                tile_number = 0

            tile_img = render_tile(
                self.tiles[tile_number],
                self.palette,
                sub_palette,
                final_h_flip,
                final_v_flip
            )

            painter.drawImage(dst_x * 8, dst_y * 8, tile_img)

        painter.end()
        return img
        
    def render_metatile_image_from_map_entry_argb(self, map_entry_value, transparent_zero=False):
        mt_index = self.map_entry_tile(map_entry_value)
        map_h_flip = self.map_entry_h_flip(map_entry_value)
        map_v_flip = self.map_entry_v_flip(map_entry_value)

        size = self.metatile_size
        pixel_size = self.metatile_pixel_size

        img = QImage(pixel_size, pixel_size, QImage.Format_ARGB32)
        img.fill(0x00000000 if transparent_zero else QColor(0, 0, 0))

        if mt_index >= len(self.metatiles):
            return img

        mt = self.metatiles[mt_index]
        painter = QPainter(img)

        for src_i, sub_value in enumerate(mt):
            if src_i >= self.metatile_entry_count:
                break

            src_x = src_i % size
            src_y = src_i // size

            dst_x = (size - 1 - src_x) if map_h_flip else src_x
            dst_y = (size - 1 - src_y) if map_v_flip else src_y

            tile_number = sub_value & 0x03FF
            sub_palette = (sub_value >> 10) & 0x07
            sub_h_flip = bool(sub_value & 0x4000)
            sub_v_flip = bool(sub_value & 0x8000)

            final_h_flip = sub_h_flip ^ map_h_flip
            final_v_flip = sub_v_flip ^ map_v_flip

            if tile_number >= len(self.tiles):
                tile_number = 0

            tile_img = render_tile_argb(
                self.tiles[tile_number],
                self.palette,
                sub_palette,
                final_h_flip,
                final_v_flip,
                transparent_zero
            )

            painter.drawImage(dst_x * 8, dst_y * 8, tile_img)

        painter.end()
        return img

    def refresh_editor_mode(self):
        if self.editor_mode == "map":
            self.map_scroll.show()
            self.metatile_scroll.hide()

            self.metatile_view.grid_index = 0

            self.tile_scroll.hide()
            self.tile_editor.hide()
            self.tile_ops.hide()
            self.palette_view.hide()
            self.palette_controls.hide()
            self.info_tile_label.hide()
            self.info_palette_label.hide()
            self.info_colour_label.hide()
            self.info_xflip.hide()
            self.info_yflip.hide()
            self.info_priority.hide()

            self.open_picker_btn.show()

            if self.direct_tilemap_mode:
                self.open_picker_btn.setEnabled(False)
                self.mode_toggle_btn.setEnabled(True)
                self.mode_toggle_btn.setText("Edit Chr")
            else:
                self.open_picker_btn.setEnabled(True)
                self.mode_toggle_btn.setEnabled(True)
                self.mode_toggle_btn.setText("Edit Tiles")

            self.add_metatile_btn.hide()
            self.del_metatile_btn.hide()

            self.map_label.setText(
                f"Map {self.map_index + 1}/{len(self.map_paths)} ({self.map_width}x{self.map_height})"
            )

        else:
            self.map_scroll.hide()
            self.metatile_scroll.show()

            self.map_view.grid_index = 0

            self.tile_scroll.show()
            self.tile_editor.show()
            self.tile_ops.show()
            self.palette_view.show()
            self.palette_controls.show()
            self.info_tile_label.show()
            self.info_palette_label.show()
            self.info_colour_label.show()
            self.info_xflip.show()
            self.info_yflip.show()
            self.info_priority.show()

            self.open_picker_btn.hide()
            self.open_picker_btn.setEnabled(False)

            if (
                hasattr(self, "picker_window")
                and self.picker_window is not None
                and self.picker_window.isVisible()
            ):
                self.picker_window.close()

            if self.direct_tilemap_mode:
                self.add_metatile_btn.hide()
                self.del_metatile_btn.hide()
            else:
                self.add_metatile_btn.show()
                self.del_metatile_btn.show()

            self.mode_toggle_btn.setEnabled(True)
            self.mode_toggle_btn.setText("Edit Map")

            self.metatile_view.reset_zoom()
            self.metatile_view.build()
            self.refresh_metatile_paging()

        self.update_status()
        
    def handle_zoom_in(self):
        if self.editor_mode == "metatile":
            self.metatile_view.zoom_in()
        else:
            self.map_view.zoom_in()

    def handle_zoom_out(self):
        if self.editor_mode == "metatile":
            self.metatile_view.zoom_out()
        else:
            self.map_view.zoom_out()
        
    def refresh_metatile_paging(self):
        if not hasattr(self, "metatile_view"):
            return False

        old_page = self.metatile_page

        per_page = max(1, self.metatile_view.per_page)
        total_pages = max(1, (len(self.metatiles) + per_page - 1) // per_page)
        max_page = total_pages - 1

        if self.metatile_page > max_page:
            self.metatile_page = max_page

        if self.metatile_page < 0:
            self.metatile_page = 0
        max_tiles = len(self.metatiles)

        #self.map_label.setText(f"Tile Set {self.metatile_page + 1}/{total_pages}")
        self.map_label.setText(f"Tiles {self.metatile_page + 1}/{total_pages} (Max {max_tiles})")
        return self.metatile_page != old_page
         
    def update_picker_button_state(self):
        picker_open = (
            hasattr(self, "picker_window")
            and self.picker_window is not None
            and self.picker_window.isVisible()
        )

        if picker_open:
            self.open_picker_btn.setStyleSheet(
                "padding: 6px 10px; color: #111; background-color: #9cf; border: 1px solid #9cf;"
            )
        else:
            self.open_picker_btn.setStyleSheet(
                "padding: 6px 10px; color: #bbb;"
            )

    def update_preview_button_state(self):
        preview_open = (
            hasattr(self, "bg_preview_window")
            and self.bg_preview_window is not None
            and self.bg_preview_window.isVisible()
        )

        if preview_open:
            self.preview_btn.setStyleSheet(
                "padding: 6px 10px; color: #111; background-color: #9cf; border: 1px solid #9cf;"
            )
        else:
            self.preview_btn.setStyleSheet(
                "padding: 6px 10px; color: #bbb;"
            )

    def update_grid_button_state(self):
        if self.editor_mode == "metatile":
            grid_size = self.metatile_view.grid_modes[self.metatile_view.grid_index]
        else:
            grid_size = self.map_view.grid_modes[self.map_view.grid_index]

        if grid_size == 0:
            self.grid_btn.setText("Grid")
            self.grid_btn.setStyleSheet("padding: 6px;")
        else:
            self.grid_btn.setText(f"Grid: {grid_size}x{grid_size}")
            self.grid_btn.setStyleSheet(
                "padding: 6px; color: #111; background-color: #9cf; border: 1px solid #9cf;"
            )  

    def open_metatile_picker(self):
        if (
            hasattr(self, "picker_window")
            and self.picker_window is not None
            and self.picker_window.isVisible()
        ):
            self.picker_window.close()
            self.update_picker_button_state()
            return

        if not hasattr(self, "picker_window") or self.picker_window is None:
            self.picker_window = MetatilePickerWindow(self)

        self.picker_window.picker.build()
        self.picker_window.refresh_status()
        self.picker_window.show()
        self.picker_window.raise_()
        self.picker_window.activateWindow()
        self.update_picker_button_state()
        
    def update_selected_subtile_entry(self, tile_number=None, palette_group=None,
                                     priority=None, h_flip=None, v_flip=None):
        if not (0 <= self.selected_metatile < len(self.metatiles)):
            return

        sub = self.selected_subtile
        value = self.metatiles[self.selected_metatile][sub]

        current_tile = value & 0x03FF
        current_palette = (value >> 10) & 0x07
        current_priority = bool(value & 0x2000)
        current_h_flip = bool(value & 0x4000)
        current_v_flip = bool(value & 0x8000)

        if tile_number is None:
            tile_number = current_tile
        if palette_group is None:
            palette_group = current_palette
        if priority is None:
            priority = current_priority
        if h_flip is None:
            h_flip = current_h_flip
        if v_flip is None:
            v_flip = current_v_flip

        new_value = (
            (tile_number & 0x03FF)
            | ((palette_group & 0x07) << 10)
            | (0x2000 if priority else 0)
            | (0x4000 if h_flip else 0)
            | (0x8000 if v_flip else 0)
        )

        if new_value != value:
            self.metatiles[self.selected_metatile][sub] = new_value
            self.modified_map = True
            self.mark_metatile_dirty(self.selected_metatile)
            # only this metatile needs refreshing in the map view

        self.selected_tile = tile_number
        self.selected_palette_group = palette_group
        self.current_priority = priority
        self.current_h_flip = h_flip
        self.current_v_flip = v_flip
        self.selected_color = (palette_group * 16) + self.selected_color_in_group

        self.tile_view.sel_start_index = self.selected_tile
        self.tile_view.sel_end_index = self.selected_tile

        self.tile_view.build()
        self.tile_editor.build()
        self.palette_view.build()
        self.palette_controls.refresh_from_selected_colour()
        self.metatile_view.build()

        if (
            hasattr(self, "picker_window")
            and self.picker_window is not None
            and self.picker_window.isVisible()
        ):
            self.picker_window.picker.build()
            self.picker_window.refresh_status()

        self.refresh_map_tile_info()
        self.update_status()

    def toggle_selected_subtile_hflip(self):
        self.update_selected_subtile_entry(h_flip=not self.current_h_flip)

    def toggle_selected_subtile_vflip(self):
        self.update_selected_subtile_entry(v_flip=not self.current_v_flip)

    def toggle_selected_subtile_priority(self):
        self.update_selected_subtile_entry(priority=not self.current_priority) 

    def add_metatile(self):
        self.metatiles.append([0] * self.metatile_entry_count)
        self.selected_metatile = len(self.metatiles) - 1
        self.selected_subtile = 0
        if hasattr(self.metatile_view, "per_page"):
            self.metatile_page = self.selected_metatile // self.metatile_view.per_page
        else:
            self.metatile_page = self.selected_metatile // 256

        self.modified_map = True

        if hasattr(self, "metatile_view"):
            self.metatile_view.build()

        if (
            hasattr(self, "picker_window")
            and self.picker_window is not None
            and self.picker_window.isVisible()
        ):
            self.picker_window.picker.build()
            self.picker_window.refresh_status()

        self.refresh_map_tile_info()
        self.update_status()

    def delete_metatile(self):
        if len(self.metatiles) <= 1:
            return

        del self.metatiles[-1]

        if self.selected_metatile >= len(self.metatiles):
            self.selected_metatile = len(self.metatiles) - 1

        if hasattr(self.metatile_view, "per_page"):
            max_page = max(0, (len(self.metatiles) - 1) // self.metatile_view.per_page)
        else:
            max_page = max(0, (len(self.metatiles) - 1) // 256)

        if self.metatile_page > max_page:
            self.metatile_page = max_page

        self.modified_map = True

        if hasattr(self, "metatile_view"):
            self.metatile_view.build()

        if (
            hasattr(self, "picker_window")
            and self.picker_window is not None
            and self.picker_window.isVisible()
        ):
            self.picker_window.picker.build()
            self.picker_window.refresh_status()

        self.refresh_map_tile_info()
        self.update_status()

    def toggle_grid_current_view(self):
        if self.editor_mode == "metatile":
            self.metatile_view.toggle_grid()
        else:
            self.map_view.toggle_grid()      

    def decode_map_entry(self, x, y):
        return get_map_entry(
            self.map_data,
            self.map_width,
            x,
            y,
            self.map_index_mask,
            self.map_h_flip_mask,
            self.map_v_flip_mask,
        )

    def make_map_entry_value(self, tile_number, palette_number=0, priority=False, h_flip=False, v_flip=False):
        if self.direct_tilemap_mode:
            # Direct SNES tilemap mode:
            # map word is a real SNES tile word.
            value = tile_number & 0x03FF
            value |= (palette_number & 0x07) << 10

            if priority:
                value |= 0x2000
            if h_flip:
                value |= 0x4000
            if v_flip:
                value |= 0x8000

            return value

        # Normal metatile mode:
        # map word is metatile index + configurable map-level flip bits.
        value = tile_number & self.map_index_mask

        if h_flip:
            value |= self.map_h_flip_mask
        if v_flip:
            value |= self.map_v_flip_mask

        return value

    def map_entry_tile(self, value):
        return value & self.map_index_mask

    def map_entry_h_flip(self, value):
        return bool(value & self.map_h_flip_mask)

    def map_entry_v_flip(self, value):
        return bool(value & self.map_v_flip_mask)

    def toggle_map_entry_h_flip(self, value):
        return value ^ self.map_h_flip_mask

    def toggle_map_entry_v_flip(self, value):
        return value ^ self.map_v_flip_mask

    def map_data_y(self, display_y):
        if self.map_direction == "bottom_top":
            return (self.map_height - 1) - display_y
        return display_y

    def map_display_y(self, data_y):
        if self.map_direction == "bottom_top":
            return (self.map_height - 1) - data_y
        return data_y
 
    def position_map_view_for_direction(self):
        if self.map_direction == "bottom_top":
            self.map_scroll.verticalScrollBar().setValue(self.map_scroll.verticalScrollBar().maximum())
        else:
            self.map_scroll.verticalScrollBar().setValue(0)

    def picker_per_page(self):
        tiles_per_row = max(1, 32 // self.metatile_size)
        rows_per_page = tiles_per_row
        return tiles_per_row * rows_per_page

    def step_selected_metatile(self, delta):
        if not self.metatiles:
            return

        new_index = self.selected_metatile + delta
        if new_index < 0 or new_index >= len(self.metatiles):
            return

        self.selected_metatile = new_index

        page_size = self.picker_per_page()
        max_page = max(0, (len(self.metatiles) - 1) // page_size)
        self.metatile_page = min(self.selected_metatile // page_size, max_page)

        self.brush_w = 1
        self.brush_h = 1
        self.brush_tiles = [self.selected_metatile]

        if (
            hasattr(self, "picker_window")
            and self.picker_window is not None
            and self.picker_window.isVisible()
        ):
            self.picker_window.picker.build()
            self.picker_window.refresh_status()

        self.update_status()

    def confirm_map_expand(self, axis_name):
        msg = (
            f"Add 1 tile to map {axis_name}?\n\n"
            f"This changes the map size and cannot be undone."
        )

        return QMessageBox.question(
            self,
            "Confirm Map Resize",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        ) == QMessageBox.Yes        

    def expand_map_width(self):
        if self.editor_mode != "map":
            return

        if not self.confirm_map_expand("width"):
            return

        old_w = self.map_width
        old_h = self.map_height
        new_w = old_w + 1

        old_data = self.map_data
        new_data = bytearray(new_w * old_h * 2)

        old_row_bytes = old_w * 2
        new_row_bytes = new_w * 2

        for y in range(old_h):
            old_off = y * old_row_bytes
            new_off = y * new_row_bytes

            # copy existing row
            new_data[new_off:new_off + old_row_bytes] = old_data[old_off:old_off + old_row_bytes]

            # final new tile in row is left as 0,0
            # because bytearray already initialises to zero

        self.map_width = new_w
        self.map_data = new_data
        self.map_data_list[self.map_index] = self.map_data
        self.map_widths[self.map_index] = self.map_width

        self.modified_map = True
        self.hover_x = -1
        self.hover_y = -1

        self.map_view.redraw()
        self.position_map_view_for_direction()
        self.update_status()
    
    def expand_map_height(self):
        if self.editor_mode != "map":
            return

        if not self.confirm_map_expand("height"):
            return

        old_w = self.map_width
        old_h = self.map_height
        new_h = old_h + 1

        old_data = self.map_data
        new_data = bytearray(old_w * new_h * 2)

        old_size = old_w * old_h * 2
        new_data[:old_size] = old_data

        # extra last row is already zero-filled

        self.map_height = new_h
        self.map_data = new_data
        self.map_data_list[self.map_index] = self.map_data
        self.map_heights[self.map_index] = self.map_height

        self.modified_map = True
        self.hover_x = -1
        self.hover_y = -1

        self.map_view.redraw()
        self.position_map_view_for_direction()
        self.update_status()
 
    def open_bg_preview(self):
        if (
            hasattr(self, "bg_preview_window")
            and self.bg_preview_window is not None
            and self.bg_preview_window.isVisible()
        ):
            self.bg_preview_window.close()
            self.update_preview_button_state()
            return

        has_next_map = (
            len(self.map_data_list) >= 2 and
            self.map_index < len(self.map_data_list) - 1
        )

        has_preview_bg2 = bool(self.preview_bg2_map)

        if not has_next_map and not has_preview_bg2:
            QMessageBox.information(
                self,
                "BG Preview",
                "BG Preview needs either a next map or preview_bg2_map in the .m1e file."
            )
            return

        self.bg_preview_active = True
        self.update_preview_button_state()

        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            QApplication.processEvents()

            if not hasattr(self, "bg_preview_window") or self.bg_preview_window is None:
                self.bg_preview_window = BGPreviewWindow(self)

            self.bg_preview_window.show()
            self.bg_preview_window.raise_()
            self.bg_preview_window.activateWindow()
            self.update_preview_button_state()

        finally:
            QApplication.restoreOverrideCursor()
            
    def toggle_hover_map_flip(self, axis):
        
        if self.editor_mode != "map":
            return False

        if self.hover_x < 0 or self.hover_y < 0:
            return False

        if self.hover_x >= self.map_width or self.hover_y >= self.map_height:
            return False

        data_y = self.map_data_y(self.hover_y)
        byte_idx = (data_y * self.map_width + self.hover_x) * 2

        old_lo = self.map_data[byte_idx]
        old_hi = self.map_data[byte_idx + 1]
        old_value = old_lo | (old_hi << 8)

        if axis == "x":
            new_value = self.toggle_map_entry_h_flip(old_value)
        else:
            new_value = self.toggle_map_entry_v_flip(old_value)

        self.begin_paint_action()
        self.record_map_change(byte_idx, (old_lo, old_hi), new_value)

        self.map_data[byte_idx] = new_value & 0xFF
        self.map_data[byte_idx + 1] = (new_value >> 8) & 0xFF

        self.end_paint_action()

        self.modified_map = True
        self.map_view.update_tile(self.hover_x, self.hover_y)
        self.map_view.update()
        self.update_status()

        return True

    def set_hover_map_palette(self, palette_number):
        if not self.direct_tilemap_mode:
            return False

        if self.editor_mode != "map":
            return False

        if self.hover_x < 0 or self.hover_y < 0:
            return False

        if self.hover_x >= self.map_width or self.hover_y >= self.map_height:
            return False

        data_y = self.map_data_y(self.hover_y)
        byte_idx = (data_y * self.map_width + self.hover_x) * 2

        old_lo = self.map_data[byte_idx]
        old_hi = self.map_data[byte_idx + 1]
        old_value = old_lo | (old_hi << 8)

        # Clear palette bits 10-12, then set new palette.
        new_value = (old_value & ~0x1C00) | ((palette_number & 0x07) << 10)

        if new_value == old_value:
            return True

        self.begin_paint_action()
        self.record_map_change(byte_idx, (old_lo, old_hi), new_value)

        self.map_data[byte_idx] = new_value & 0xFF
        self.map_data[byte_idx + 1] = (new_value >> 8) & 0xFF

        self.end_paint_action()

        self.selected_palette_group = palette_number & 0x07
        self.selected_color = self.selected_palette_group * 16
        self.selected_color_in_group = 0

        self.modified_map = True
        self.map_view.update_tile(self.hover_x, self.hover_y)
        self.map_view.update()
        self.palette_view.build()
        self.palette_controls.refresh_from_selected_colour()
        self.update_status()

        return True

    def toggle_hover_map_priority(self):
        if not self.direct_tilemap_mode:
            return False

        if self.editor_mode != "map":
            return False

        if self.hover_x < 0 or self.hover_y < 0:
            return False

        if self.hover_x >= self.map_width or self.hover_y >= self.map_height:
            return False

        data_y = self.map_data_y(self.hover_y)
        byte_idx = (data_y * self.map_width + self.hover_x) * 2

        old_lo = self.map_data[byte_idx]
        old_hi = self.map_data[byte_idx + 1]
        old_value = old_lo | (old_hi << 8)

        new_value = old_value ^ 0x2000

        self.begin_paint_action()
        self.record_map_change(byte_idx, (old_lo, old_hi), new_value)

        self.map_data[byte_idx] = new_value & 0xFF
        self.map_data[byte_idx + 1] = (new_value >> 8) & 0xFF

        self.end_paint_action()

        self.current_priority = bool(new_value & 0x2000)

        self.modified_map = True
        self.map_view.update_tile(self.hover_x, self.hover_y)
        self.map_view.update()
        self.update_status()

        return True
    
    def picker_per_page(self):
        tiles_per_row = max(1, 32 // self.metatile_size)
        return tiles_per_row * tiles_per_row

    def subtile_label(self, index):
        if self.metatile_size == 2:
            return ["TL", "TR", "BL", "BR"][index]
        return f"T{index:02d}"

    def show_help(self):
             
        if self.editor_mode == "metatile":
            text = METATILE_HELP_TEXT
        else:
            text = MAP_HELP_TEXT

        msg = QMessageBox(self)
        msg.setWindowTitle("Help")
        msg.setTextFormat(Qt.RichText)
        msg.setText(text)
        msg.exec()

    def mark_metatile_dirty(self, mt_index):
        if 0 <= mt_index < len(self.metatiles):
            self.map_view_dirty_metatiles.add(mt_index)
 
class TileEditor(QLabel):
    def __init__(self, parent):
        super().__init__()
        self.drag_selecting = False
        self.sel_start_index = None
        self.sel_end_index = None
        self.parent = parent
        self.setMouseTracking(True)
        self.setFixedSize(8 * EDITOR_PIXEL_SIZE, 8 * EDITOR_PIXEL_SIZE)
        self.setCursor(Qt.ArrowCursor)
        self.build()

    def build(self):
        self.parent.selected_palette_group
        tile = self.parent.tiles[self.parent.selected_tile]
        pixels = decode_snes_4bpp_tile(tile)
        palette = self.parent.palette

        img = QImage(
            8 * EDITOR_PIXEL_SIZE,
            8 * EDITOR_PIXEL_SIZE,
            QImage.Format_RGB32
        )
        painter = QPainter(img)

        for y in range(8):
            for x in range(8):
                
                c = pixels[y * 8 + x]
                base = self.parent.selected_palette_group * 16
                r, g, b = palette[base + c]
                painter.fillRect(
                    x * EDITOR_PIXEL_SIZE,
                    y * EDITOR_PIXEL_SIZE,
                    EDITOR_PIXEL_SIZE,
                    EDITOR_PIXEL_SIZE,
                    QColor(r, g, b)
                )

        painter.setPen(QPen(Qt.gray, 1))
        for i in range(9):
            painter.drawLine(i * EDITOR_PIXEL_SIZE, 0, i * EDITOR_PIXEL_SIZE, 8 * EDITOR_PIXEL_SIZE)
            painter.drawLine(0, i * EDITOR_PIXEL_SIZE, 8 * EDITOR_PIXEL_SIZE, i * EDITOR_PIXEL_SIZE)

        painter.end()

        self.setPixmap(QPixmap.fromImage(img))

    def pixel_from_event(self, event):
        x = int(event.position().x()) // EDITOR_PIXEL_SIZE
        y = int(event.position().y()) // EDITOR_PIXEL_SIZE
        return x, y

    def mousePressEvent(self, event):
        mods = event.modifiers() | QApplication.keyboardModifiers()

        x, y = self.pixel_from_event(event)
        if not (0 <= x < 8 and 0 <= y < 8):
            return

        tile = self.parent.tiles[self.parent.selected_tile]
        pixels = decode_snes_4bpp_tile(tile)
        idx = y * 8 + x

        # ALT = pick colour
        if (mods & Qt.AltModifier) and event.button() == Qt.LeftButton:
            self.parent.selected_color_in_group = pixels[idx]
            self.parent.selected_color = (self.parent.selected_palette_group * 16) + self.parent.selected_color_in_group
            self.parent.update_status()
            self.parent.palette_view.build()
            self.parent.palette_controls.refresh_from_selected_colour()
            return

        if event.button() == Qt.LeftButton:
            self.parent.push_undo()

            # only store colour index within current 16-colour palette
            pixels[idx] = self.parent.selected_color_in_group & 0x0F

            self.parent.tiles[self.parent.selected_tile] = encode_snes_4bpp_tile(pixels)
            self.parent.modified_chr = True

            self.build()
            self.parent.tile_view.build()

            if self.parent.editor_mode == "map":
                self.parent.map_view.redraw()
            else:
                self.parent.metatile_view.build()
                if (
                    hasattr(self.parent, "picker_window")
                    and self.parent.picker_window is not None
                    and self.parent.picker_window.isVisible()
                ):
                    self.parent.picker_window.picker.build()
                    self.parent.picker_window.refresh_status()

            self.parent.update_status()

        elif event.button() == Qt.RightButton:
            self.parent.selected_color_in_group = pixels[idx]
            self.parent.selected_color = (self.parent.selected_palette_group * 16) + self.parent.selected_color_in_group
            self.parent.update_status()
            self.parent.palette_view.build()
            self.parent.palette_controls.refresh_from_selected_colour()
           
    def mouseMoveEvent(self, event):
        mods = QApplication.keyboardModifiers()

        # change cursor live
        if mods & Qt.AltModifier:
            self.setCursor(Qt.CrossCursor)
            return
        else:
            self.setCursor(Qt.ArrowCursor)

        if event.buttons() & Qt.LeftButton:
            self.mousePressEvent(event)

class MetatileView(QLabel):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.zoom_levels = [1, 2, 3, 4]
        self.zoom_index = 1
        self.display_scale = self.zoom_levels[self.zoom_index]

        self.metatile_pixel_size = self.parent.metatile_pixel_size

        self.cols = 1
        self.rows = 1
        self.per_page = 1

        self.grid_modes = [0, self.metatile_pixel_size, self.metatile_pixel_size * 2]
        self.grid_index = 0

        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setFocusPolicy(Qt.StrongFocus)

    def calculate_layout(self):
        # Main metatile editor uses visible viewport space.
        # Do not use fixed picker-style 32//metatile_size layout here.
        if hasattr(self.parent, "metatile_scroll") and self.parent.metatile_scroll is not None:
            viewport = self.parent.metatile_scroll.viewport()
            w = max(1, viewport.width())
            h = max(1, viewport.height())
        else:
            w = max(1, self.width())
            h = max(1, self.height())

        cell_w = self.parent.metatile_pixel_size * self.display_scale
        cell_h = self.parent.metatile_pixel_size * self.display_scale

        self.cols = max(1, w // cell_w)
        self.rows = max(1, h // cell_h)
        self.per_page = self.cols * self.rows
        
    def build(self):
        p = self.parent

        if not p.metatiles:
            return

        self.calculate_layout()

        if hasattr(p, "refresh_metatile_paging"):
            p.refresh_metatile_paging()

        cell_w = self.parent.metatile_pixel_size
        cell_h = self.parent.metatile_pixel_size

        img_w = self.cols * cell_w
        img_h = self.rows * cell_h

        img = QImage(img_w, img_h, QImage.Format_RGB32)
        img.fill(QColor(20, 20, 20))  # subtle background

        painter = QPainter(img)

        start = p.metatile_page * self.per_page
        end = min(start + self.per_page, len(p.metatiles))

        for i in range(start, end):
            local_index = i - start

            x = (local_index % self.cols) * cell_w
            y = (local_index // self.cols) * cell_h

            mt = p.metatiles[i]
            mt_img = p.render_metatile_image(mt)

            painter.drawImage(x, y, mt_img)

        grid_size = self.grid_modes[self.grid_index]
        if grid_size > 0:
            painter.setPen(QPen(QColor(255, 255, 255, 80), 1))

            for x in range(0, img_w, grid_size):
                painter.drawLine(x, 0, x, img_h)

            for y in range(0, img_h, grid_size):
                painter.drawLine(0, y, img_w, y)
                
        # draw selection
        sel = p.selected_metatile
        if start <= sel < end:
            local = sel - start
            sx = (local % self.cols) * cell_w
            sy = (local // self.cols) * cell_h

            # red box around whole metatile
            painter.setPen(QPen(Qt.red, 1))
            painter.drawRect(sx, sy, cell_w - 1, cell_h - 1)

            # green box around selected subtile
            sub = self.parent.selected_subtile
            sub_x = (sub % self.parent.metatile_size) * 8
            sub_y = (sub // self.parent.metatile_size) * 8

            painter.setPen(QPen(QColor(0, 255, 128), 1))
            painter.drawRect(sx + sub_x, sy + sub_y, 7, 7)

        painter.end()

        # scale for display
        pix = QPixmap.fromImage(img).scaled(
            img.width() * self.display_scale,
            img.height() * self.display_scale,
            Qt.KeepAspectRatio,
            Qt.FastTransformation
        )

        self.setPixmap(pix)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.build()
        if hasattr(self.parent, "refresh_metatile_paging"):
            changed = self.parent.refresh_metatile_paging()
            if changed:
                self.build()

    def mousePressEvent(self, event):
        p = self.parent

        if self.pixmap() is None:
            return

        px = int(event.position().x())
        py = int(event.position().y())

        cell_w = p.metatile_pixel_size * self.display_scale
        cell_h = p.metatile_pixel_size * self.display_scale

        tx = px // cell_w
        ty = py // cell_h

        if tx < 0 or ty < 0 or tx >= self.cols or ty >= self.rows:
            return

        index = ty * self.cols + tx
        mt_index = p.metatile_page * self.per_page + index

        if mt_index >= len(p.metatiles):
            return

        p.selected_metatile = mt_index

        local_x = px % cell_w
        local_y = py % cell_h

        sub_cell = 8 * self.display_scale

        sub_x = local_x // sub_cell
        sub_y = local_y // sub_cell

        sub_x = max(0, min(p.metatile_size - 1, sub_x))
        sub_y = max(0, min(p.metatile_size - 1, sub_y))

        p.selected_subtile = sub_y * p.metatile_size + sub_x

        # Direct mode: fake metatile view is only a CHR selector.
        # Do not write anything into fake metatile data.
        if p.direct_tilemap_mode:
            p.selected_tile = mt_index
            p.selected_subtile = 0

            p.tile_view.sel_start_index = p.selected_tile
            p.tile_view.sel_end_index = p.selected_tile

            p.tile_view.build()
            p.tile_editor.build()
            p.palette_view.build()
            p.palette_controls.refresh_from_selected_colour()

            self.build()
            p.refresh_map_tile_info()
            p.update_status()
            event.accept()
            return

        # right click = pick underlying character/palette/flags into editor state
        if event.button() == Qt.RightButton:
            value = p.metatiles[p.selected_metatile][p.selected_subtile]

            p.selected_tile = value & 0x03FF
            p.selected_palette_group = (value >> 10) & 0x07
            p.current_priority = bool(value & 0x2000)
            p.current_h_flip = p.map_entry_h_flip(value)
            p.current_v_flip = p.map_entry_v_flip(value)
            p.selected_color = (p.selected_palette_group * 16) + p.selected_color_in_group

            p.tile_view.sel_start_index = p.selected_tile
            p.tile_view.sel_end_index = p.selected_tile

            p.tile_view.build()
            p.tile_editor.build()
            p.palette_view.build()
            p.palette_controls.refresh_from_selected_colour()

        self.build()
        p.refresh_map_tile_info()
        p.update_status()
    
    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def mouseDoubleClickEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        p = self.parent

        if not (0 <= p.selected_metatile < len(p.metatiles)):
            return

        sub = p.selected_subtile
        old_value = p.metatiles[p.selected_metatile][sub]

        new_value = (
            (p.selected_tile & 0x03FF)
            | ((p.selected_palette_group & 0x07) << 10)
            | (0x2000 if p.current_priority else 0)
            | (0x4000 if p.current_h_flip else 0)
            | (0x8000 if p.current_v_flip else 0)
        )

        if old_value != new_value:
            p.metatiles[p.selected_metatile][sub] = new_value
            p.modified_map = True
            p.mark_metatile_dirty(p.selected_metatile)
            
            self.build()
            p.refresh_map_tile_info()
            p.update_status()

            if (
                hasattr(p, "picker_window")
                and p.picker_window is not None
                and p.picker_window.isVisible()
            ):
                p.picker_window.picker.build()
                p.picker_window.refresh_status()
                
    def keyPressEvent(self, event):
        p = self.parent

        if not (0 <= p.selected_metatile < len(p.metatiles)):
            super().keyPressEvent(event)
            return

        moved = False
        current = p.selected_metatile

        if event.key() == Qt.Key_H:
            self.parent.show_help()
            event.accept()
            return

        if event.key() == Qt.Key_U:
            self.parent.undo_last_action()
            event.accept()
            return

        if event.key() == Qt.Key_Z and event.modifiers() & Qt.ControlModifier:
            self.parent.undo_last_action()
            event.accept()
            return
            
        super().keyPressEvent(event)
        
        if event.key() == Qt.Key_Left:
            if p.selected_subtile in (1, 3):
                p.selected_subtile -= 1
                moved = True
            elif current > 0:
                target = current - 1
                if (target // self.per_page) == p.metatile_page:
                    p.selected_metatile = target
                    p.selected_subtile = 1 if p.selected_subtile == 0 else 3
                    moved = True

        elif event.key() == Qt.Key_Right:
            if p.selected_subtile in (0, 2):
                p.selected_subtile += 1
                moved = True
            elif current + 1 < len(p.metatiles):
                target = current + 1
                if (target // self.per_page) == p.metatile_page:
                    p.selected_metatile = target
                    p.selected_subtile = 0 if p.selected_subtile == 1 else 2
                    moved = True

        elif event.key() == Qt.Key_Up:
            if p.selected_subtile in (2, 3):
                p.selected_subtile -= 2
                moved = True
            else:
                target = current - self.cols
                if target >= 0 and (target // self.per_page) == p.metatile_page:
                    p.selected_metatile = target
                    p.selected_subtile += 2
                    moved = True
                else:
                    # move to previous page if possible
                    if p.metatile_page > 0:
                        p.metatile_page -= 1
                        page_start = p.metatile_page * self.per_page
                        page_end = min(page_start + self.per_page, len(p.metatiles)) - 1

                        # same column, bottom row of previous page if possible
                        target = page_end - (self.cols - 1 - (current % self.cols))
                        if target < page_start:
                            target = page_start
                        if target > page_end:
                            target = page_end

                        p.selected_metatile = target
                        p.selected_subtile += 2
                        moved = True

        elif event.key() == Qt.Key_Down:
            if p.selected_subtile in (0, 1):
                p.selected_subtile += 2
                moved = True
            else:
                target = current + self.cols
                if target < len(p.metatiles) and (target // self.per_page) == p.metatile_page:
                    p.selected_metatile = target
                    p.selected_subtile -= 2
                    moved = True
                else:
                    # move to next page if possible
                    max_page = max(0, (len(p.metatiles) - 1) // self.per_page)
                    if p.metatile_page < max_page:
                        p.metatile_page += 1
                        page_start = p.metatile_page * self.per_page
                        page_end = min(page_start + self.per_page, len(p.metatiles)) - 1

                        # same column, top row of next page if possible
                        target = page_start + (current % self.cols)
                        if target > page_end:
                            target = page_end

                        p.selected_metatile = target
                        p.selected_subtile -= 2
                        moved = True

        if moved:
            self.build()
            p.refresh_map_tile_info()
            p.update_status()
            event.accept()
            return

        super().keyPressEvent(event)

    def current_metatile_in_view(self):
        p = self.parent
        return p.metatile_page * self.per_page + p.selected_metatile % self.per_page

    def set_display_scale(self, new_scale, anchor_mt_index=None):
        p = self.parent

        if not p.metatiles:
            return

        if anchor_mt_index is None:
            anchor_mt_index = p.selected_metatile

        # remember old layout position before zoom
        old_page = p.metatile_page
        old_cols = self.cols
        old_rows = self.rows

        old_local_index = anchor_mt_index - (old_page * self.per_page)
        if old_local_index < 0:
            old_local_index = 0
        if old_local_index >= self.per_page:
            old_local_index = self.per_page - 1

        old_col = old_local_index % old_cols
        old_row = old_local_index // old_cols

        # apply new zoom and recalc layout
        self.display_scale = new_scale
        self.calculate_layout()

        # keep selected metatile in roughly same visible slot
        target_col = min(old_col, self.cols - 1)
        target_row = min(old_row, self.rows - 1)
        desired_local_index = target_row * self.cols + target_col

        new_page = (anchor_mt_index - desired_local_index) // self.per_page
        if new_page < 0:
            new_page = 0

        max_page = max(0, (len(p.metatiles) - 1) // self.per_page)
        if new_page > max_page:
            new_page = max_page

        p.metatile_page = new_page

        # if selected tile still somehow falls off the page, clamp page again
        page_start = p.metatile_page * self.per_page
        page_end = min(page_start + self.per_page, len(p.metatiles)) - 1

        if anchor_mt_index < page_start:
            p.metatile_page = anchor_mt_index // self.per_page
        elif anchor_mt_index > page_end:
            p.metatile_page = anchor_mt_index // self.per_page

        self.build()
        p.refresh_map_tile_info()
        p.update_status()

    def zoom_in(self):
        if self.zoom_index < len(self.zoom_levels) - 1:
            self.zoom_index += 1
            self.set_display_scale(self.zoom_levels[self.zoom_index], anchor_mt_index=self.parent.selected_metatile)

    def zoom_out(self):
        if self.zoom_index > 0:
            self.zoom_index -= 1
            self.set_display_scale(self.zoom_levels[self.zoom_index], anchor_mt_index=self.parent.selected_metatile)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
            
    def reset_zoom(self):
        self.zoom_index = 1
        self.display_scale = self.zoom_levels[self.zoom_index]
        
    def toggle_grid(self):
        self.grid_index = (self.grid_index + 1) % len(self.grid_modes)
        self.build()
        self.parent.update_status()
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("mode1_editor.ico"))
 
    parser = argparse.ArgumentParser(
        description="SNES Mode 1 map editor (2-byte tiles, palette, flip, priority support)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=HELP_TEXT
    )

    parser.add_argument("project",nargs="?",help="Project name, with or without .m1e extension")
    parser.add_argument("--palette",help="SNES palette file (.pal, 128 bytes)")
    parser.add_argument("--chr",dest="chr_file",help="Character file (.sf4)")
    parser.add_argument("--map",dest="map_files",action="append",help="Map file (.map). Can be used multiple times for multi-map mode")
    parser.add_argument("--width",type=int,default=128,help="Map width (default: 128)")
    parser.add_argument("--height",type=int,default=128,help="Map height (default: 128)")
    parser.add_argument("--metatiles", help="Metatile file (.mtl)")
    parser.add_argument("--tilesize", type=int,default=2,help="Meta Tile size (default: 2)")
    parser.add_argument("--map-index-mask", default="0x03FF", help="Map entry mask for metatile index. Default: 0x03FF")
    parser.add_argument("--map-h-flip-bit", type=int, default=14, help="Map entry H/X flip bit. Default: 14")
    parser.add_argument("--map-v-flip-bit", type=int, default=15, help="Map entry V/Y flip bit. Default: 15")
    parser.add_argument("--debug", action="store_true",	help="Show map/metatile byte offsets in the status bar")
    args = parser.parse_args()

    # --- PROJECT MODE ---
    if args.project:
        project_name = args.project
        project_filename = ensure_project_filename(project_name)

        if not os.path.exists(project_filename):
            print(f"Project '{project_filename}' not found.")
            try:
                create = input("Create new project? (y/n): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nCancelled. Use --help for usage.")
                sys.exit(0)

            if create == "y":
                create_project(project_name, width=128, height=128)
            else:
                print("Project creation cancelled. Use --help for usage.")
                sys.exit(0)

        proj = load_project(project_name)

        tiles_path = proj["tiles"]
        palette_path = proj["palette"]

        metatile_size = int(proj.get("metatile_size", 2))
        direct_tilemap_mode = (metatile_size == 1)

        metatile_path = proj.get("metatiles", "").strip()
        if direct_tilemap_mode:
            if metatile_path:
                print("NOTICE: metatile_size=1 direct tilemap mode; metatiles= entry ignored.")
            metatile_path = None
        elif not metatile_path:
            metatile_path = None

        map_direction = proj.get("map_direction", "top_bottom").strip().lower()

        raw_mask = proj.get("map_index_mask", None)

        if direct_tilemap_mode:
            print("NOTICE: Direct SNES tilemap mode enabled (metatile_size=1).")
            if raw_mask is not None:
                print("NOTICE: map_index_mask ignored in direct mode; using SNES tile mask $03FF.")
            if "map_h_flip_bit" in proj or "map_v_flip_bit" in proj:
                print("NOTICE: map flip bit settings ignored in direct mode; using SNES bits 14/15.")

            map_index_mask = 0x03FF
            map_h_flip_bit = 14
            map_v_flip_bit = 15
        else:
            if raw_mask is None:
                map_index_mask = 0x03FF
                print("NOTE: No map_index_mask in .m1e (using default $03FF)")
            else:
                map_index_mask = parse_hex_or_dec(raw_mask)

            map_h_flip_bit = int(proj.get("map_h_flip_bit", 14))
            map_v_flip_bit = int(proj.get("map_v_flip_bit", 15))

        if "maps" in proj:
            map_paths = [m.strip() for m in proj["maps"].split(",") if m.strip()]
        elif "map" in proj:
            map_paths = [proj["map"].strip()]
        else:
            raise ValueError("Project must define 'map' or 'maps'")
            raise ValueError("Project must define 'map' or 'maps'")

        map_count = len(map_paths)

        widths = parse_project_dimension_list(
            str(proj.get("width", args.width)),
            map_count,
            "width"
        )

        heights = parse_project_dimension_list(
            str(proj.get("height", args.height)),
            map_count,
            "height"
        )

        if metatile_path:
            metatiles = load_metatiles(metatile_path, metatile_size)
        else:
            metatiles = []

        # --- MAP MASK VALIDATION ---
        # Only applies to normal metatile mode.
        # Direct tilemap mode uses real SNES tile words, so there is no metatile index range to validate.
        if metatile_size != 1:
            metatile_count = len(metatiles)
            max_entries_from_mask = map_index_mask + 1

            if metatile_count > max_entries_from_mask:
                required_bits = (metatile_count - 1).bit_length()
                suggested_mask = (1 << required_bits) - 1

                print("\nWARNING: MAP INDEX MASK TOO SMALL")
                print(f"  Metatiles in project : {metatile_count}")
                print(f"  Mask allows          : {max_entries_from_mask}")
                print(f"  Current mask         : ${map_index_mask:04X}")
                print()
                print("  Map indices WILL be truncated and display incorrectly.")
                print()
                print("  FIX: Add this line to your .m1e file:")
                print()
                print(f"      map_index_mask=0x{suggested_mask:04X}")
                print()

        # Map file to use as BG2 in preview (can be project map or external)
        preview_bg2_map = proj.get("preview_bg2_map", "").strip() or None
        # Width of the BG2 preview (display/logical)
        preview_bg2_width = int(proj.get("preview_bg2_width", 0))
        # Height of the BG2 preview (display/logical)
        preview_bg2_height = int(proj.get("preview_bg2_height", 0))
        # Mode for BG2: 'direct', 'project_map', or 'next_map'
        preview_bg2_mode = proj.get("preview_bg2_mode", "direct").strip().lower()
        # Source data format for BG2: normal, snes_32x64_to_64x32, etc.
        preview_bg2_format = proj.get("preview_bg2_format", "normal").strip().lower()
        # Horizontal repeat count for BG2, or 'fill' to auto-calculate
        preview_bg2_repeat_x = parse_int_or_fill(proj.get("preview_bg2_repeat_x", 1), 1)
        # Vertical repeat count for BG2, or 'fill' to auto-calculate
        preview_bg2_repeat_y = parse_int_or_fill(proj.get("preview_bg2_repeat_y", 0), 0)
        # Horizontal parallax ratio relative to BG1
        preview_bg2_scroll_x = float(proj.get("preview_bg2_scroll_x", 1.0))
        # Vertical parallax ratio relative to BG1
        preview_bg2_scroll_y = float(proj.get("preview_bg2_scroll_y", 1.0))
        # Minimum Y offset for BG1 preview (allow negative offset)
        preview_bg1_min_y = int(proj.get("preview_bg1_min_y", 0))
        # Minimum Y position for BG2 preview (allows negative offset)
        preview_bg2_min_y = int(proj.get("preview_bg2_min_y", 0))

        win = Editor(
            tiles_path=tiles_path,
            palette_path=palette_path,
            map_paths=map_paths,
            widths=widths,
            heights=heights,
            metatile_path=metatile_path,
            map_direction=map_direction,
            metatile_size=metatile_size,
            map_index_mask=map_index_mask,
            map_h_flip_bit=map_h_flip_bit,
            map_v_flip_bit=map_v_flip_bit
        )
        win.preview_bg2_map = preview_bg2_map
        win.preview_bg2_width = preview_bg2_width
        win.preview_bg2_height = preview_bg2_height
        win.preview_bg2_mode = preview_bg2_mode
        win.preview_bg2_format = preview_bg2_format
        win.preview_bg2_repeat_x = preview_bg2_repeat_x
        win.preview_bg2_repeat_y = preview_bg2_repeat_y
        win.preview_bg2_scroll_x = preview_bg2_scroll_x
        win.preview_bg2_scroll_y = preview_bg2_scroll_y

        win.project_path = project_filename

    elif args.palette and args.chr_file and args.map_files:

        map_paths = args.map_files
        map_count = len(map_paths)

        widths = parse_project_dimension_list(
            str(args.width),
            map_count,
            "width"
        )

        heights = parse_project_dimension_list(
            str(args.height),
            map_count,
            "height"
        )

        win = Editor(
            tiles_path=args.chr_file,
            palette_path=args.palette,
            map_paths=map_paths,
            widths=widths,
            heights=heights,
            metatile_path=args.metatiles,
            map_direction="top_bottom",
            metatile_size=args.tilesize,
            map_index_mask=parse_hex_or_dec(args.map_index_mask),
            map_h_flip_bit=args.map_h_flip_bit,
            map_v_flip_bit=args.map_v_flip_bit
        )

    else:
        print("Invalid arguments. Use either project or direct file mode.")
        sys.exit(1)

    win.show()
    sys.exit(app.exec())
    
