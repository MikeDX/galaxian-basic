# Galaxian BASIC

A minimal programming language for Galaxian/Scramble arcade hardware. BASIC-like syntax with built-in commands for graphics, sprites, sound, and input.

## Status

**Runtime working** — Z80 skeleton builds and runs in MAME. Displays text, hardware sprites, and per-column scrolling. See [PLAN.md](PLAN.md) for the full design and implementation roadmap.

## Quick Start

```bash
cd galaxian-basic
make          # Build ROM
make run      # Run in MAME
```

**Requirements:** SDCC 3.8.0 (default: `~/Downloads/sdcc-3.8.0`), MAME, Python 3.

**Output:**
- `build/galaxian-scramble-game.rom` — full ROM
- `scramble/` — sliced ROMs for MAME (s1.2d–s8.2p, c1.5h, c2.5f, c01s.6e, sound)

**Run manually:** `mame scramble -rompath .` (from galaxian-basic/)

## Current Demo

The runtime displays:
- "GALAXIAN BASIC", "READY", "INPUT OK", "WATCHDOG OK"
- 7 bouncing hardware sprites (sprite code 0x18)
- Scrolling strip at row 24 (per-column scroll)

## Project Structure

```
galaxian-basic/
├── PLAN.md      # Design & implementation plan
├── README.md    # This file
├── Makefile     # Self-contained build
├── slice.py     # Slice ROM for MAME
├── crt0.asm     # Z80 reset + vblank interrupt
├── runtime.c    # C runtime (putchar, sprites, scroll)
├── gfxdata.h    # Tile ROM + palette
├── example.c    # Reference (gfxtest-style)
├── src/         # Lexer, parser, compiler (planned)
├── lib/         # Galaxian stubs (planned)
├── examples/    # Sample .bas programs
└── tests/       # Test suite
```

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make` | Build ROM (default) |
| `make run` | Build and run in MAME |
| `make clean` | Remove build artifacts (keeps crt0.asm) |
| `make info` | Show ROM info and symbols |
| `make help` | Show help |

## Hardware Target

- **CPU**: Z80 @ 3.072 MHz
- **Display**: 32×32 character grid (224×256 pixels)
- **Sprites**: 8 hardware sprites (ORAM 0x5040)
- **Scroll**: Per-column (TRAM 0x5000)
- **Sound**: AY-3-8910

## License

Same as parent project.
