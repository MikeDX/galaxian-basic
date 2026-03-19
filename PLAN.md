# Galaxian BASIC — Technical Plan

**Goal:** Create a BASIC programming language that compiles to native Z80 code for Galaxian/Scramble arcade hardware.

This document outlines the technical design, architecture, and implementation roadmap. If you're looking for a quick overview, see [README.md](README.md).

---

## Overview

Galaxian BASIC brings modern development tools to classic arcade hardware. Write programs in a simple BASIC dialect, compile to C, then to Z80 machine code, and run on real arcade boards or MAME.

**Key Features:**
- BASIC syntax optimized for arcade game development
- Direct hardware access (sprites, scrolling, sound, input)
- **BASIC → C → Z80 → ROM** — no bytecode interpreter, native execution
- Modern IDE with graphics editor and debugger (planned)
- Runs on actual 1980s arcade hardware

---

## 1. Hardware Context

Target: **Galaxian/Scramble** (Z80, 3.072 MHz)

| Resource | Address | Description |
|----------|---------|-------------|
| RAM | 0x4000 | General purpose |
| VRAM | 0x4800 | 32×32 character grid (8×8 tiles) |
| TRAM | 0x5000 | Column attributes (scroll, colour per column) |
| ORAM | 0x5040 | 8 sprites (xpos, code, color, ypos) |
| ORAM+0x20 | 0x5060 | 8 missiles (xpos, ypos) |
| INPUT0/1/2 | 0x8100+ | Joystick, buttons, coin, start |
| AY-3-8910 | 0x8200 | Sound (tone, noise, envelope) |

Display: 224×256 pixels, 32×32 tiles, ~32 colours.

---

## 2. Language Design

### 2.1 Core Syntax (BASIC-like)

```
10 PRINT "HELLO"
20 LET X = 42
30 IF X > 10 THEN GOTO 50
40 GOTO 20
50 END
```

- Line numbers (1–9999)
- Variables: single letters (A–Z) or A0–A9 style
- Numeric literals: decimal (0–255 for byte)
- Strings: "quoted"

### 2.2 Built-in Commands

**Implemented**

**Display**
- `CLS` — clear screen
- `PRINT x, y, "text"` — draw text at (x,y)
- `POKE x, y, ch` — write char to vram (expressions supported)
- `COLOR col, attr` — set column colour (expressions: F+2, etc.)
- `SCROLL col, val` — set column scroll (variable or literal)
- `PUTSHAPE x, y, ofs` — 2×2 tile block (ofs+2,ofs; ofs+3,ofs+1)

**Sprites**
- `SPRITE n, x, y, code, color` — set sprite n (0–7)
- `HIDE n` — hide sprite n
- `MISSILE n, x, y` — hardware missile layer (8 missiles at ORAM+0x20)

**Input**
- `JOY(n)` — joystick (0=left, 1=right, 2=up, 3=down)
- `INPUT(n)` — input_pressed (0–16: P1/P2 controls, coin, start, service)

**Control**
- `WAIT n` — wait n frames (n=1 optimizes to single wait_for_frame)
- `GOTO n` — jump to line
- `IF expr THEN` / `ELSE` / `ENDIF` — block form
- `IF var op num THEN GOTO n` — conditional jump
- `FOR var = start TO end` / `NEXT var`

**Planned**
- `GOSUB n` / `RETURN` — subroutine
- `SOUND`, `BEEP` — sound
- `FILL x, y, w, h, ch` — block fill

### 2.3 Expressions (implemented)

- Arithmetic: `+`, `-`, `*` (var+num, var-num, var*num, num+var*num)
- Comparisons: `=`, `<>`, `<`, `>`, `<=`, `>=` (in IF conditions)
- Functions: `JOY(n)`, `INPUT(n)` (in expressions)

---

## 3. Architecture

```
galaxian-basic/
├── PLAN.md           # This file
├── README.md
├── Makefile          # Build system (PROGRAM=file.bas)
├── gbasic.py         # BASIC → C compiler
├── renum.py          # Renumber .bas files (updates GOTO targets)
├── slice.py          # Slice ROM for MAME scramble
├── crt0.asm          # Z80 reset + vblank interrupt at 0x66
├── runtime.c         # Hardware engine (no main)
├── runtime.h         # Runtime API for compiled programs
├── example.c         # Reference C implementation (matches example.bas)
├── demo.c            # C demo (when PROGRAM=)
├── gfxdata.h         # Tile ROM + palette
├── examples/
│   ├── example.bas   # Full demo (chars, sprites, missiles, explosion)
│   ├── chase.bas
│   ├── demo.bas
│   ├── hello.bas
│   ├── scroll.bas
│   ├── sprite.bas
│   ├── input_test.bas
│   └── if_else_test.bas
└── build/            # Generated C and ROM output
    └── program.c     # Generated C from BASIC
```

### 3.1 Skeleton Runtime (implemented)

A minimal Z80 runtime builds and runs under the MAME `scramble` driver. **Self-contained build** — run `make` from `galaxian-basic/`.

**Build:**
```bash
cd galaxian-basic
make          # Build ROM
make run      # Build and run in MAME
make clean    # Remove build artifacts (preserves crt0.asm)
```

**Output:** `build/galaxian-scramble-game.rom`, `scramble/*.2d` etc. Run MAME with `mame scramble -rompath .` from `galaxian-basic/`.

**Hardware mapping:**
| Resource | Address | Description |
|----------|---------|-------------|
| VRAM | 0x4800 | 32×32 character grid |
| TRAM | 0x5000 | vcolumns (scroll, attrib per column) |
| ORAM | 0x5040 | 8 hardware sprites + 8 missiles (0x5060) |
| IRQ | 0x6801 | enable_irq |
| Watchdog | 0x7000 | Must tick or hardware resets |
| Input | 0x8100–0x8102 | input0, input1, input2 |

**Vblank synchronization:**
- Interrupt at 0x66: minimal handler that increments `video_framecount`
- `wait_for_frame()`: HALT until vblank, then copies buffered sprite/scroll data to hardware registers
- Prevents tearing — all visual updates happen during vertical blank

**Runtime API (C):**
- `putchar(x, y, ch)`, `putstring(x, y, s)` — text (CHAR remap for digits)
- `putshape(x, y, ofs)` — 2×2 tile block
- `clrscr()` — clear VRAM + vcolumns
- `set_sprite(n, x, y, code, color)`, `hide_sprite(n)` — buffered, applied in wait_for_frame
- `set_missile(n, x, y)` — hardware missile layer (8 missiles at ORAM+0x20)
- `set_scroll(col, val)`, `set_column_attrib(col, attr)` — per-column scroll/color
- `wait_for_frame()` — sync to vblank, copy buffers to hardware

### 3.2 Compilation Pipeline

**BASIC → C → Z80 → ROM**

1. **gbasic.py** — Compiles BASIC source to C that calls the runtime API
2. **SDCC** — Compiles generated C to Z80 machine code
3. **Linker** — Links with runtime library (crt0 + runtime.c)
4. **hex2rom + slice.py** — Produces ROM image for MAME

No bytecode or interpreter. Direct native Z80 execution.

---

## 4. Implementation Phases

### Current Status (Latest)

- **example.bas** — Full demo matching example.c: draw_all_chars (256 tiles), draw_sprites (5 rows), draw_explosion, draw_missiles (8 sprites + 8 missiles), draw_corners, text
- **MISSILE** — Hardware missile layer (8 missiles at ORAM+0x20)
- **Compiler optimizations** — WAIT 1 → `wait_for_frame()`; labels only for GOTO/IF targets; COLOR hoisted outside loops (source-level)
- **renum.py** — Renumber .bas files, update GOTO/IF...GOTO targets

### Phase 0: Z80 Runtime ✓ Complete
- [x] crt0.asm — reset vector, vblank interrupt handler
- [x] runtime.c — text rendering, sprite control, scrolling
- [x] Hardware abstraction — VRAM, ORAM, TRAM access
- [x] Vblank synchronization — tear-free graphics updates
- [x] Build system — Makefile, ROM slicing, MAME integration
- [x] Working demo — text, bouncing sprites, scrolling effects

### Phase 1: BASIC → C Compiler ✓ Complete
- [x] gbasic.py — tokenizer, parser, C code emission
- [x] Core commands — CLS, PRINT, POKE, COLOR, LET, IF/THEN/ELSE/ENDIF, WAIT, GOTO
- [x] Sprites — SPRITE, HIDE, MISSILE (with variable expressions)
- [x] Scrolling — SCROLL, FOR/NEXT with variables
- [x] Display — PUTSHAPE (2×2 tile blocks)
- [x] Input — JOY(n), INPUT(n)
- [x] Expressions — var+num, var-num, var*num, num+var*num
- [x] Pipeline — BASIC → C → SDCC → ROM
- [x] Compiler optimizations — WAIT 1 → wait_for_frame(), labels only for branch targets

### Phase 2: More Language Features
- [ ] GOSUB / RETURN — subroutines
- [ ] More expressions — /, MOD, AND, OR
- [ ] FILL — block fill command
- [ ] Sound — SOUND, BEEP
- [ ] Error handling — compile-time and runtime messages

### Phase 3: IDE Development
- [ ] Code editor — syntax highlighting, line numbers
- [ ] Graphics editor — tile/sprite editing
- [ ] Emulator integration — built-in Z80 emulator
- [ ] Debugger — breakpoints, step, inspect
- [ ] Project management — save/load, export ROM

### Phase 4: Advanced (optional)
- [ ] Direct BASIC → Z80 (skip C) — for size/speed optimization
- [ ] Node-based visual programming
- [ ] Community library of programs

---

## 5. Example Programs

### Hello World
```
10 REM Hello Galaxian
20 CLS
30 PRINT 5, 10, "HELLO"
40 PRINT 5, 12, "GALAXIAN"
50 WAIT 120
60 GOTO 20
```

### Scrolling Effect
```
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

### Sprite Demo
```
10 REM Sprite demo
20 CLS
30 SPRITE 0, 100, 112, 24, 1
40 PRINT 2, 0, "SPRITE"
50 WAIT 30
60 GOTO 50
```

### Full Demo (example.bas)
The `examples/example.bas` program demonstrates all features, matching the reference `example.c`:
- **draw_all_chars** — 256 tiles in 8 rows with COLOR and SCROLL
- **draw_sprites** — 5 rows of 2×2 tile blocks via PUTSHAPE
- **draw_explosion** — 4×4 putshape pattern
- **draw_missiles** — 8 sprites + 8 hardware missiles (SPRITE, MISSILE)
- **draw_corners** — animated corner tiles
- **PRINT** — text display

---

## 6. Development Tools

**Required:**
- **SDCC 3.8.0** — Z80 cross-compiler (compiles generated C to machine code)
- **MAME** — Arcade emulator for testing
- **Python 3** — gbasic.py compiler and build scripts

**Available:**
- **renum.py** — Renumber .bas files; updates GOTO and IF...THEN GOTO targets. Usage: `renum.py file.bas [-o out.bas] [--start 10] [--step 10] [-n]`

**Planned:**
- **Web IDE** — Browser-based development environment
- **Desktop IDE** — Standalone application (Electron or native)
- **Built-in emulator** — Z80 emulator with debugging support

---

## 7. Success Milestones

### Milestone 1: Runtime ✓
- Z80 code runs on MAME
- Hardware sprites, scrolling, text working

### Milestone 2: BASIC Compiler ✓
- BASIC → C → Z80 → ROM pipeline working
- Full command set: display (CLS, PRINT, POKE, COLOR, SCROLL, PUTSHAPE), sprites (SPRITE, HIDE, MISSILE), input (JOY, INPUT), control flow (LET, IF/ELSE/ENDIF, FOR/NEXT, GOTO, WAIT)
- Example programs running in MAME (example.bas matches example.c reference)
- renum.py for line renumbering

### Milestone 3: Full Language
- GOSUB/RETURN, sound, more expressions
- Error handling and debugging

### Milestone 4: IDE
- Visual editor with syntax highlighting
- Graphics/sprite editor
- Built-in emulator and debugger
- Export to ROM

### Milestone 5: Advanced
- Direct BASIC → Z80 (optional optimization)
- Node-based visual programming
- Community library of programs
