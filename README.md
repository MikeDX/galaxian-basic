# Galaxian BASIC

**Write games for classic arcade hardware using BASIC!**

Galaxian BASIC is a retro programming language designed for the iconic Galaxian and Scramble arcade machines. Write simple BASIC programs that compile to C, then to Z80 machine code, and run on real arcade hardware or MAME.

## Why Galaxian BASIC?

- **Authentic retro experience** — Your programs run on actual 1980s arcade hardware (or MAME)
- **Simple BASIC syntax** — Easy to learn, with built-in commands for sprites, scrolling, sound, and input
- **No bytecode interpreter** — Compiles BASIC → C → Z80 for native execution
- **Modern tooling** — Planned IDE with graphics editor, emulator, and debugger built-in

## What's Working Now

The Z80 runtime is complete and running in MAME! The **BASIC → C → Z80 → ROM** pipeline works:

- **gbasic.py** — Compiles BASIC to C with full command set:
  - Display: CLS, PRINT, POKE, COLOR, SCROLL, PUTSHAPE (2×2 tile blocks)
  - Sprites: SPRITE, HIDE, MISSILE (hardware missile layer)
  - Control: LET, IF/THEN/ELSE/ENDIF, FOR/NEXT, GOTO, WAIT
  - Input: JOY(n), INPUT(n)
- **SDCC** — Compiles generated C to native Z80 machine code
- **Runtime engine** — Text, sprites, missiles, scrolling, watchdog
- **Pipeline** — `make PROGRAM=examples/hello.bas` produces a runnable ROM (no bytecode interpreter)
- **renum.py** — Renumber .bas files and update GOTO targets

![Demo running in MAME](screenshots/demo.gif)

**Next up:** Sound, debugger, AI helper.

**Web IDE:** Code editor, help reference, graphics editor, palette editor. Run `make ide` and open http://localhost:8080

See [README_GRAPHICS.md](README_GRAPHICS.md) for details on the unified `.gfx.json` format.

## Quick Start

Want to see it in action? Build and run the demo:

```bash
cd galaxian-basic
make          # Build the ROM (default demo)
make run      # Launch in MAME
```

**Default build** compiles `examples/demo.bas` (bouncing sprites + scrolling):

```bash
make          # BASIC demo → ROM
make run      # Launch in MAME
```

**Other BASIC programs:**

```bash
make PROGRAM=examples/hello.bas
make PROGRAM=examples/sprite.bas run
make PROGRAM=examples/scroll.bas run
make PROGRAM=examples/chase.bas run   # Joystick + moving enemy
make PROGRAM=examples/example.bas run # Full demo (chars, sprites, missiles, explosion)
make PROGRAM=examples/input_test.bas  # Input/button display
make PROGRAM=examples/if_else_test.bas
make PROGRAM=                  # Build C demo (no BASIC)
```

**Renumber a BASIC file:**

```bash
python scripts/renum.py examples/example.bas -n        # Dry run (print only)
python scripts/renum.py examples/example.bas           # Renumber in place
python scripts/renum.py examples/example.bas -o out.bas --start 100 --step 10
```

**Requirements:** 
- SDCC 3.8.0 (Z80 compiler) — default path: `~/Downloads/sdcc-3.8.0`
- MAME (arcade emulator)
- Python 3

**Output files:**
- `build/galaxian-scramble-game.rom` — Complete ROM image
- `scramble/` — Individual ROM chips for MAME (s1.2d–s8.2p, c1.5h, c2.5f, etc.)

**Run manually:** `mame scramble -rompath .` (from the `galaxian-basic/` directory)

**Web IDE:**

```bash
make ide   # Serves IDE at http://localhost:8080
```

Open http://localhost:8080 for the web-based editor with:
- **Code** — BASIC editor with syntax highlighting
- **Help** — Language reference
- **Graphics** — Tile editor (64 tiles, 16×16, 2 bpp) with 8×8 char view
- **Palette** — 32-color palette editor (3-3-2 RGB) with sub-palette selector
- **Load GFX / Save GFX** — Load and save `.gfx.json` files

**Graphics workflow:** 
1. Edit tiles and palette in the IDE
2. Save to `examples/yourprogram.gfx.json`
3. Build with `make PROGRAM=examples/yourprogram.bas` (automatically uses matching `.gfx.json`)

The `.gfx.json` format is the single source of truth. See [README_GRAPHICS.md](README_GRAPHICS.md) for details.

## Example Programs

Here's what Galaxian BASIC code looks like:

**Hello World:**
```basic
10 REM Hello Galaxian
20 CLS
30 PRINT 5, 10, "HELLO"
40 PRINT 5, 12, "GALAXIAN"
50 WAIT 120
60 GOTO 20
```
![Hello World](screenshots/hello.gif)

**Sprite Animation:**
```basic
10 REM Sprite demo
20 CLS
30 SPRITE 0, 100, 112, 24, 1
40 PRINT 2, 0, "SPRITE"
50 WAIT 30
60 GOTO 50
```
![Sprite Animation](screenshots/sprite.gif)

**Scrolling Effect:**
```basic
10 REM Scrolling demo
20 CLS
25 LET S = 0
60 PRINT 8, 15, "SCROLL!"
70 WAIT 1
80 LET S = S + 1
90 FOR C = 4 TO 27
100   SCROLL C, S
110 NEXT C
200 GOTO 70
```
![Scrolling Effect](screenshots/scroll.gif)

**Chase (joystick + AI sprite):**
```basic
10 REM Chase - joystick moves player, enemy bounces
20 CLS
30 LET PX = 100
40 LET PY = 120
50 LET PX = PX + JOY(1)
60 LET PX = PX - JOY(0)
70 LET PY = PY + JOY(3)
80 LET PY = PY - JOY(2)
90 SPRITE 0, PX, PY, 24, 1
100 SPRITE 1, EX, EY, 24, 2
110 GOTO 50
```
![Chase](screenshots/chase.gif)

See the `examples/` folder for more sample programs!

## Project Structure

```
galaxian-basic/
├── README.md       # You are here
├── PLAN.md         # Technical design document
├── Makefile        # Build system (supports PROGRAM=file.bas)
├── lib/            # Runtime library
│   ├── runtime.c   # Hardware engine (no main)
│   ├── runtime.h   # Runtime API for compiled programs
│   ├── crt0.asm         # Z80 startup code
│   └── default.gfx.json # Default graphics (tiles + palette)
├── src/            # Application source
│   ├── demo.c      # Default demo (when no PROGRAM=)
│   └── example.c   # Reference C implementation (matches example.bas)
├── scripts/        # Python tools
│   ├── gbasic.py   # BASIC → C compiler
│   ├── renum.py    # Renumber .bas files (updates GOTO targets)
│   └── slice.py    # ROM splitter for MAME
├── examples/       # Sample BASIC programs
│   ├── example.bas # Full demo (chars, sprites, missiles, explosion)
│   ├── chase.bas
│   ├── demo.bas
│   ├── hello.bas
│   ├── scroll.bas
│   ├── sprite.bas
│   ├── input_test.bas
│   └── if_else_test.bas
└── build/          # Generated C and ROM output
    └── program.c   # Generated C from BASIC
```

## Build Commands

| Command | What it does |
|---------|--------------|
| `make` | Build the ROM |
| `make run` | Build and launch in MAME |
| `make clean` | Clean build artifacts |
| `make info` | Show ROM details and symbols |
| `make help` | Display help |

## The Hardware

Galaxian BASIC targets the original arcade hardware:

- **CPU**: Zilog Z80 @ 3.072 MHz
- **Display**: 32×32 tile grid (224×256 pixels, ~32 colors)
- **Sprites**: 8 hardware sprites with independent positioning
- **Scrolling**: Per-column vertical scrolling
- **Sound**: AY-3-8910 programmable sound generator
- **Input**: Joystick, fire buttons, coin slots

## Roadmap

**Current Status:** BASIC → C → Z80 → ROM pipeline complete. Full command set: display, sprites, missiles, scrolling, input (JOY, INPUT), control flow. Compiler optimizations (WAIT 1, labels, COLOR hoisting). `renum.py` for line renumbering.

**Coming Soon:**
- GOSUB/RETURN, sound, more expressions
- Visual IDE (web or desktop)
- Graphics editor
- Built-in emulator and debugger

See [PLAN.md](PLAN.md) for the complete technical roadmap.

## Contributing

This project is in active development. Check out the [PLAN.md](PLAN.md) to see what's being worked on and what's coming next.

## License

Same as parent project.
