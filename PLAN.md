# Galaxian BASIC — Project Plan

A minimal programming language for Galaxian/Scramble arcade hardware. BASIC-like syntax with built-in commands for graphics, sound, and input.

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

**Vblank sync (Pitfall pattern):**
- Interrupt at 0x66: minimal handler, only increments `video_framecount`
- `wait_for_frame()`: HALT until vblank, then copies `sprites[]` → vsprites and `scroll_buf` → vcolumns
- Prevents tearing — sprite/scroll updates happen right after vblank

**Runtime API (C):**
- `putchar(x, y, ch)`, `putstring(x, y, s)` — text (CHAR remap for digits)
- `clrscr()` — clear VRAM + vcolumns
- `set_sprite(n, x, y, code, color)`, `hide_sprite(n)` — buffered, applied in wait_for_frame
- `set_scroll(col, val)`, `set_column_attrib(col, attr)` — per-column scroll/color
- `wait_for_frame()` — sync to vblank, copy buffers to hardware

### 3.2 Compilation Strategy

**Phase 1: Interpreted (C runtime)**  
- Compile to bytecode
- Run on SDL2/terminal with Galaxian-compatible runtime
- Validate language and commands

**Phase 2: Z80 native**  
- Emit Z80 assembly or machine code
- Link with minimal runtime
- Produce ROM for Galaxian

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

### Phase 0: Z80 Runtime (done)
- [x] crt0.asm — reset vector, vblank interrupt at 0x66
- [x] runtime.c — putchar, putstring, clrscr, set_sprite, hide_sprite
- [x] set_scroll, set_column_attrib — per-column scroll/color
- [x] wait_for_frame — Pitfall-style vblank sync, no tearing
- [x] Makefile — self-contained build, slice.py, scramble/ output
- [x] Hardware sprites (ORAM), scrolling (TRAM vcolumns)
- [x] Demo: bouncing sprites + scrolling strip

### Phase 1: Lexer & Parser (1–2 days)
- [ ] Lexer: tokens for keywords, numbers, identifiers, strings
- [ ] Parser: line-based, statement list, expressions
- [ ] AST: nodes for each statement/expression type

### Phase 2: Compiler → Bytecode (1–2 days)
- [ ] Compile expressions to stack machine
- [ ] Compile statements
- [ ] Line number → bytecode address table

### Phase 3: C Runtime / Interpreter (1 day)
- [ ] Bytecode interpreter loop
- [ ] Galaxian I/O stubs (vram, sprites, input, sound)
- [ ] SDL2 or terminal front-end for testing

### Phase 4: Built-in Commands (2–3 days)
- [ ] PRINT, POKE, CLS
- [ ] COLOR, SCROLL, FILL
- [ ] SPRITE
- [ ] SOUND, BEEP
- [ ] JOY, BUTTON, WAIT

### Phase 5: Z80 Backend (optional, 3–5 days)
- [ ] Bytecode → Z80 asm
- [ ] Runtime in Z80
- [ ] ROM build integration

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

## 6. Dependencies

- **Host**: C99 compiler (for lexer, parser, compiler, interpreter)
- **Target**: SDCC for Z80 (if doing native ROM)
- **Optional**: SDL2 for visual testing

---

## 7. Success Criteria

1. Parse and run `10 PRINT 5,5,"HI" : END`
2. Run on SDL2 with correct vram mapping
3. All built-in commands work in interpreter
4. (Stretch) Produce runnable Galaxian ROM
