# Galaxian BASIC — Technical Plan

**Goal:** Create a BASIC programming language that compiles to native Z80 code for Galaxian/Scramble arcade hardware.

This document outlines the technical design, architecture, and implementation roadmap. If you're looking for a quick overview, see [README.md](README.md).

---

## Overview

Galaxian BASIC brings modern development tools to classic arcade hardware. Write programs in a simple BASIC dialect, compile to Z80 machine code, and run on real arcade boards or MAME.

**Key Features:**
- BASIC syntax optimized for arcade game development
- Direct hardware access (sprites, scrolling, sound, input)
- Compiles to native Z80 code — no emulation overhead
- Modern IDE with graphics editor and debugger
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

**Display**
- `CLS` — clear screen
- `PRINT x, y, "text"` — draw text at (x,y)
- `POKE x, y, ch` — write char to vram
- `COLOR col, attr` — set column colour/scroll
- `SCROLL col, val` — set column scroll
- `FILL x, y, w, h, ch` — fill block

**Sprites**
- `SPRITE n, x, y, code, color` — set sprite n (0–7)
- `SPRITE n, -1, -1, 0, 0` — hide sprite

**Sound**
- `SOUND cmd` — send command to AY chip
- `BEEP freq, dur` — simple tone

**Input**
- `JOY n` — read joystick n (0=1P, 1=2P)
- `BUTTON n` — read button
- `WAIT key` — wait for key/button

**Control**
- `WAIT n` — wait n frames
- `GOTO n` — jump to line
- `GOSUB n` / `RETURN` — subroutine
- `END` — stop

### 2.3 Expressions

- Arithmetic: `+`, `-`, `*`, `/`, `MOD`
- Comparisons: `=`, `<>`, `<`, `>`, `<=`, `>=`
- Logical: `AND`, `OR`, `NOT`
- Functions: `RND(n)`, `PEEK(x,y)`, `JOY(0)`

---

## 3. Architecture

```
galaxian-basic/
├── PLAN.md           # This file
├── README.md
├── Makefile          # Self-contained build (SDCC, slice, MAME)
├── slice.py          # Slice ROM for MAME scramble
├── crt0.asm          # Z80 reset + vblank interrupt at 0x66
├── runtime.c         # C runtime (putchar, sprites, scroll, wait_for_frame)
├── gfxdata.h         # Tile ROM + palette (from parent gfx.h)
├── example.c         # Reference implementation (gfxtest-style)
├── src/
│   ├── lexer.c       # Tokenizer (planned)
│   ├── parser.c      # AST builder (planned)
│   └── ...
├── lib/
├── examples/
│   ├── hello.bas
│   ├── scroll.bas
│   └── sprite.bas
└── tests/
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
| ORAM | 0x5040 | 8 hardware sprites |
| IRQ | 0x6801 | enable_irq |
| Watchdog | 0x7000 | Must tick or hardware resets |
| Input | 0x8100–0x8102 | input0, input1, input2 |

**Vblank synchronization:**
- Interrupt at 0x66: minimal handler that increments `video_framecount`
- `wait_for_frame()`: HALT until vblank, then copies buffered sprite/scroll data to hardware registers
- Prevents tearing — all visual updates happen during vertical blank

**Runtime API (C):**
- `putchar(x, y, ch)`, `putstring(x, y, s)` — text (CHAR remap for digits)
- `clrscr()` — clear VRAM + vcolumns
- `set_sprite(n, x, y, code, color)`, `hide_sprite(n)` — buffered, applied in wait_for_frame
- `set_scroll(col, val)`, `set_column_attrib(col, attr)` — per-column scroll/color
- `wait_for_frame()` — sync to vblank, copy buffers to hardware

### 3.2 Compilation Strategy

**Phase 1: Bytecode interpreter**  
- Compile BASIC to bytecode
- Bytecode interpreter runs on Z80
- Validate language design and commands

**Phase 2: Native Z80 compilation (optional)**  
- Direct BASIC → Z80 assembly translation
- Link with minimal runtime library
- Optimized ROM for maximum performance

### 3.3 Bytecode (interpreter)

| Opcode | Args | Description |
|--------|------|-------------|
| PUSH | byte | Push literal |
| ADD, SUB, MUL, DIV | — | Arithmetic |
| LOAD, STORE | var | Variable access |
| PRINT | — | Pop x,y,str; draw |
| POKE | — | Pop x,y,ch; vram |
| SPRITE | — | Pop n,x,y,code,col |
| GOTO | line | Jump |
| GOSUB | line | Call |
| RETURN | — | Return |
| IF | — | Pop; branch if true |
| WAIT | — | Pop frames |
| END | — | Halt |

---

## 4. Implementation Phases

### Phase 0: Z80 Runtime ✓ Complete
- [x] crt0.asm — reset vector, vblank interrupt handler
- [x] runtime.c — text rendering, sprite control, scrolling
- [x] Hardware abstraction — VRAM, ORAM, TRAM access
- [x] Vblank synchronization — tear-free graphics updates
- [x] Build system — Makefile, ROM slicing, MAME integration
- [x] Working demo — text, bouncing sprites, scrolling effects

### Phase 1: Lexer & Parser
- [ ] Tokenizer — keywords, numbers, identifiers, strings
- [ ] Line-based parser — BASIC statement structure
- [ ] Expression parser — arithmetic, comparisons, logic
- [ ] AST generation — abstract syntax tree for compilation

### Phase 2: Bytecode Compiler
- [ ] Expression compilation — stack-based bytecode
- [ ] Statement compilation — control flow, commands
- [ ] Line number resolution — GOTO/GOSUB targets
- [ ] Symbol table — variable tracking

### Phase 3: Bytecode Interpreter
- [ ] Interpreter loop — fetch, decode, execute
- [ ] Stack machine — expression evaluation
- [ ] Runtime integration — call into hardware API
- [ ] Error handling — runtime error messages

### Phase 4: Built-in Commands
- [ ] Display commands — PRINT, POKE, CLS, FILL
- [ ] Graphics commands — COLOR, SCROLL
- [ ] Sprite commands — SPRITE (show/hide/position)
- [ ] Sound commands — SOUND, BEEP
- [ ] Input commands — JOY, BUTTON
- [ ] Control commands — WAIT, GOTO, GOSUB, RETURN, END

### Phase 5: IDE Development
- [ ] Code editor — syntax highlighting, line numbers
- [ ] Graphics editor — tile/sprite editing
- [ ] Emulator integration — built-in Z80 emulator
- [ ] Debugger — breakpoints, step, inspect
- [ ] Project management — save/load, export ROM

### Phase 6: Native Compiler (optional)
- [ ] Z80 code generation — direct BASIC → assembly
- [ ] Optimization passes — peephole, dead code elimination
- [ ] Linking — combine with runtime library

---

## 5. Example Programs

### Hello World
```
10 CLS
20 PRINT 10, 15, "HELLO GALAXIAN"
30 WAIT 60
40 GOTO 20
```

### Scrolling Text
```
10 CLS
20 FOR C = 0 TO 31
30   SCROLL C, C
40 NEXT C
50 PRINT 5, 10, "SCROLL!"
60 WAIT 1
70 GOTO 50
```

### Sprite Demo
```
10 CLS
20 SPRITE 0, 100, 112, 24, 1
30 WAIT 30
40 GOTO 30
```

---

## 6. Development Tools

**Required:**
- **SDCC 3.8.0** — Z80 cross-compiler
- **MAME** — Arcade emulator for testing
- **Python 3** — Build scripts
- **C99 compiler** — For compiler/interpreter development

**Planned:**
- **Web IDE** — Browser-based development environment
- **Desktop IDE** — Standalone application (Electron or native)
- **Built-in emulator** — Z80 emulator with debugging support

---

## 7. Success Milestones

### Milestone 1: Runtime ✓
- Z80 code runs on MAME
- Hardware sprites, scrolling, text working

### Milestone 2: Language Core
- Parse and compile BASIC programs
- Bytecode interpreter functional
- Basic commands working (PRINT, GOTO, END)

### Milestone 3: Full Language
- All built-in commands implemented
- Example programs running
- Error handling and debugging

### Milestone 4: IDE
- Visual editor with syntax highlighting
- Graphics/sprite editor
- Built-in emulator and debugger
- Export to ROM

### Milestone 5: Advanced Features
- Node-based visual programming
- Performance optimization
- Native Z80 compilation
- Community library of programs
