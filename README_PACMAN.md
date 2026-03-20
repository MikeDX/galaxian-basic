# Pac-Man hardware target

Galaxian BASIC can build the **CPU ROMs** for Namco Pac-Man (`mame pacman`) using a small runtime (`lib/runtime_pacman.c`) that matches the board’s memory map. **Tile and sprite graphics** still come from the stock ROMs (`pacman.5e`, `pacman.5f`, color/sound PROMs) — the build only replaces `pacman.6e`–`pacman.6j`.

## Build

```bash
make clean
make TARGET=pacman PROGRAM=examples/hello.bas run
```

The `run` target detects `TARGET=pacman` and launches MAME with the correct machine.

You can also use `run-pacman` as a shortcut (forces `TARGET=pacman` and passes through variables):

```bash
make run-pacman PROGRAM=examples/hello.bas
```

Or build without running:

```bash
make TARGET=pacman PROGRAM=examples/hello.bas
```

### VRAM test pattern (debug)

To verify CPU → VRAM/color RAM (no `CLS` in BASIC — that would clear the pattern):

```bash
make TARGET=pacman PACMAN_VRAM_TEST=1 PROGRAM=examples/pacman_ramtest.bas
```

This fills 1 KiB tile RAM with pseudo-random tile codes and **odd** color nibbles so tiles are visible. **Do not** use with programs that start with `CLS` unless you only need to confirm boot.

### Listings and ROM dump

After a Pac-Man build, the Makefile writes:

| File | Contents |
|------|----------|
| `build/crt0.lst`, `runtime.lst`, `program.lst` | Assembler listings (`sdasz80 -l`) |
| `build/pacman-basic-game.merged.lst` | Concatenation of the three |
| `build/pacman-basic-game.rom.flat.lst` | Hex + ASCII dump of the final 16 KiB CPU ROM |
| `build/pacman-basic-game.map` | Linker map (from `sdldz80 -m`) |

### ROM slicing

`scripts/slice_pacman.py` splits the flat 16 KiB image **linearly** to match MAME `ROM_LOAD`:

| File | Offset |
|------|--------|
| `pacman.6e` | `0x0000`–`0x0FFF` |
| `pacman.6f` | `0x1000`–`0x1FFF` |
| `pacman.6h` | `0x2000`–`0x2FFF` |
| `pacman.6j` | `0x3000`–`0x3FFF` |

The script verifies that rejoining the four chips equals the source buffer and prints the first 8 bytes of each chip.

Output:

- `build/pacman-basic-game.rom` — 16 KiB flat CPU image  
- `pacman/` — `pacman.6e` … `pacman.6j` plus copied gfx/PROM files when found  

## Graphics ROMs

`scripts/slice_pacman.py` copies non-CPU ROMs from the first path that contains `pacman.5e`:

1. `$PACMAN_ROM_PATH` (directory)
2. `galaxian-basic/roms/pacman/`
3. `../roms/pacman/` (sibling of repo)
4. `~/.mame/roms/pacman`

If none of these exist, copy into `pacman/` by hand:

- `pacman.5e`, `pacman.5f`
- `82s123.7f`, `82s126.4a`, `82s126.1m`, `82s126.3m`

Then run:

```bash
mame pacman -rompath .
```

from the `galaxian-basic` directory (MAME loads `pacman/pacman.6e`, …).

## BASIC coordinate system and visible area

Pac-Man's visible playfield is **much smaller** than Galaxian's 32×32 grid. The visible tilemap area maps to:

- **Main playfield**: VRAM addresses 0-319 (tilemap columns 2-33, rows 0-7)
- **Side strips**: VRAM addresses 960-1023 (tilemap columns 0-1 and 34-35, rows 0-27)

For BASIC programs, `vram_ofs(x, y)` maps coordinates as follows:

- **x**: 0-31 (BASIC) → tilemap columns 2-33 (visible)
- **y**: 0-7 (BASIC) → tilemap rows 0-7 (visible)
- **y > 7**: Clamped to y=7 (all text beyond row 7 appears on row 7)

This means BASIC programs written for Galaxian that use y coordinates beyond 7 will have their text clamped to row 7. Programs like `hello.bas` that use `PRINT 5, 10` and `PRINT 5, 12` will both render on row 7, with the second overwriting the first.

### Tile visibility and color RAM

Pac-Man tiles are only visible with **odd** palette indices (0x01, 0x03, 0x05, etc.). Even palette indices (0x00, 0x02, 0x04, etc.) render as black. The runtime sets `PACMAN_TILE_COLOR_RAM=1` by default, which makes `CLS` and `putchar()` write color RAM (0x4400-0x47FF) with odd palette values so text is visible.

## Memory map (MAME `pacman` — `pacman_state::pacman_map`)

Authoritative reference: [mame/src/mame/pacman/pacman.cpp](https://github.com/mamedev/mame/blob/master/src/mame/pacman/pacman.cpp) (`pacman_map`).

| Range | Purpose |
|-------|---------|
| `0x0000`–`0x3FFF` | Program ROM (mirrored at `0x8000`–`0xBFFF` on boards without A15) |
| `0x4000`–`0x43FF` | Video RAM (tile codes), mirrored `+0xA000` |
| `0x4400`–`0x47FF` | Color RAM, mirrored `+0xA000` |
| `0x4800`–`0x4BFF` | Read returns open-bus (`0xBF` in MAME); **writes ignored** on original Pac-Man |
| `0x4C00`–`0x4FEF` | Work RAM (SDCC **`-b _DATA=0x4C00`**; globals must fit below **0x4FF0**) |
| `0x4FF0`–`0x4FFF` | Sprite attributes (8×2 bytes) |
| `0x5000`–`0x5007` | Addressable latch (IRQ enable, flip, etc.) — **read** `0x5000` = IN0 |
| `0x5040`–`0x505F` | Namco sound |
| `0x5060`–`0x506F` | Sprite X/Y |
| `0x50C0` | **Watchdog reset** (write; MAME watchdog ≈ every 16 vblanks without a write) |
| `0x5000` / `0x5040` / `0x5080` / `0x50C0` | Input / DSW reads (mirrored) |

**Other sets** use different maps (e.g. **Ms. Pac-Man** `mspacman_map` banks ROM; **Alibaba** ties the watchdog to **`0x5000`** writes instead of `0x50C0`; **Woodpecker** adds upper ROM). This runtime targets the canonical **`pacman`** parent driver only.

**Visible VRAM:** Pac-Man hardware only scans **bytes 0–319** and **960–1023** of the 1024-byte VRAM/color RAM space (384 bytes total). Bytes 320–959 exist in RAM but are **never displayed**. The visible layout is: **top 2 rows** (960–1023), **main playfield columns** (64–319), **bottom 2 rows** (0–63). See [walkofmind Pac-Man memory map](http://www.euro-arcade.de/files/pacman_mm/pacman_mm.htm).

**Tile color RAM (0x4400):** By default the runtime **does not write** color RAM (`PACMAN_TILE_COLOR_RAM=0`) so only **VRAM** (tile codes) is driven — useful to confirm text without palette overwrites. MAME keeps whatever color bytes were already in memory (or use a savestate). Re-enable with **`make TARGET=pacman PACMAN_TILE_COLOR_RAM=1`**.

**Color / palette (when `PACMAN_TILE_COLOR_RAM=1`):** Odd palette indices are visible; even indices often read as black. **`CLS`** fills color RAM with **0x01** and VRAM with **0x40** (space). **`COLOR col, a`** maps through `pacman_color_hw` (non-zero `a` forced odd). Column attr 0 defaults to palette **0x01** for visibility. **Sprites use the same palette** but follow the same odd=visible convention.

**Watchdog:** The vblank ISR writes `0x50C0` every frame in addition to `wait_for_frame()`, so MAME’s 16-frame watchdog window is satisfied even under IRQ glitches.

## Behaviour vs Galaxian

| Feature | Galaxian/Scramble | Pac-Man (this runtime) |
|--------|--------------------|-------------------------|
| Tile **address** | `(29-x)*32+y` into VRAM | MAME **`pacman_scan_rows`**: map BASIC cell to tilemap `col=x+2`, `row=y`, then same formula as [pacman_v.cpp](https://github.com/mamedev/mame/blob/master/src/mame/pacman/pacman_v.cpp) (`row+=2; col-=2;` then branch on `col & 0x20`). Not linear. |
| `SCROLL` | Hardware column scroll | Stored only (no hardware scroll) |
| `MISSILE` | Missile layer | No-op |
| `COLOR col, a` | Column attribute RAM | Per-cell color RAM in that column |
| `PRINT` letters | Scramble tile/font (`c - 0x30`, blank **0x10**) | Pac-Man **.5e**: **0x00–0x0F** = hex **0–F**; **0x30–0x39** = decimal **0–9**; **0x40** = space; **0x41–0x5A** = **A–Z** |
| `CLS` | Clears logical grid | **VRAM** `0x40` (space) in visible ranges **0–319** and **960–1023**. **Color** `0x4400` written only if **`PACMAN_TILE_COLOR_RAM=1`**. **PRINT** uses **0x40**–**0x5A** / **0x30**–**0x39** via `CHAR()`. |
| IRQ | NMI @ 0x66 | IM 1 IRQ @ 0x38 |

**Note:** MAME draws the background with a **36×28** tilemap; CPU VRAM is still **1024 bytes**. `y` is clamped to **29** when indexing so the mapper never overflows 1024 (rows **30–31** in BASIC map to row **29**’s hardware line — a minor compromise).

Work RAM for C globals is linked at **0x4C00**–**0x4FFF** (`LDFLAGS` **`-b _DATA=0x4C00`**); keep **.bss** small enough that it does not overlap the sprite attribute area at **0x4FF0** (stack is set at **0x4F00** in `crt0_pacman.asm`).

## C-only minimal demo (no BASIC)

`examples/pacman_minimal.c` fills the **36×28 tilemap** via `pacman_scan_rows` and animates four sprites. Demonstrates proper VRAM addressing and sprite animation at 60fps.

```bash
make TARGET=pacman PACMAN_C_MAIN=examples/pacman_minimal.c
# or build + MAME:
make run-pacman-minimal
```

## Examples

Good first tests:

- `examples/hello.bas` — text + `WAIT`
- `examples/demo.bas` — sprites + `COLOR` + `SCROLL` (scroll is cosmetic only)
- `examples/chase.bas` — joystick (4-way Pac-Man layout)
