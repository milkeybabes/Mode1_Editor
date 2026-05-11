# Mode1 Editor - Installation Guide

This editor is written in Python and works on:

* Windows
* macOS
* Linux

The editor requires Python 3 and a few Python packages.

---

# 1. Install Python

Download Python from:

https://www.python.org/downloads/

During installation on Windows:

✔ Enable:

"Add Python to PATH"

before clicking Install.

---

# 2. Download the Editor

Either:

* Download ZIP from GitHub

or:

* Clone using Git

Example:

```bash
git clone https://github.com/yourname/yourrepo.git
```

---

# 3. Open a Terminal

## Windows

Open:

* Command Prompt
  or
* PowerShell

Then change to the editor folder:

```bash
cd path\to\editor
```

Example:

```bash
cd G:\SNES\Street\Editor
```

---

## macOS / Linux

Open Terminal and change folder:

```bash
cd /path/to/editor
```

---

# 4. Install Required Python Packages

Run:

```bash
pip install -r requirements.txt
```

If `pip` does not work, try:

```bash
python -m pip install -r requirements.txt
```

or on macOS/Linux:

```bash
python3 -m pip install -r requirements.txt
```

---

# 5. Run the Editor

Example:

```bash
python mode1_editor.py myproject.m1e
```

or:

```bash
python3 mode1_editor.py myproject.m1e
```

---

# Common Problems

## "python is not recognised"

Python is not installed correctly or not added to PATH.

Reinstall Python and enable:

✔ Add Python to PATH

---

## Missing PySide6

Run:

```bash
pip install PySide6
```

---

## Missing Pillow

Run:

```bash
pip install Pillow
```

---

# Requirements

Current required packages:

* PySide6
* Pillow

---

# Notes

* The editor uses SNES 4bpp graphics (.sf4)
* Maps are standard 2-byte SNES tilemaps
* Supports dynamic metatile sizes
* BG Preview supports parallax preview and SNES screen overlay

Enjoy!
