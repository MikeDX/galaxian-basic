/*
 * Minimal runtime for Pac-Man (Namco) hardware — MAME driver "pacman".
 * Uses stock tile/sprite ROMs (pacman.5e / pacman.5f); program replaces CPU ROMs only.
 *
 * I/O (memory-mapped, see MAME pacman_state::pacman_map):
 *   Read  0x5000 = IN0 (joystick/coin), 0x5040 = IN1, 0x5080 = DSW1, 0x50C0 = DSW2
 *   Write 0x5000 = IRQ enable latch D0; 0x50C0 = watchdog reset; 0x5040-0x505F = sound
 *
 * Memory: VRAM 0x4000-0x43FF, color RAM 0x4400-0x47FF, work RAM 0x4C00-0x4FFF
 * (link _DATA at 0x4C00). 0x4800-0x4BFF is open bus / unused on stock Pac-Man.
 * Sprite attrs 0x4FF0-0x4FFF, sprite XY 0x5060-0x506F.
 */
typedef unsigned char byte;
typedef unsigned short word;

#define VRAM_BASE   0x4000
#define COLOR_BASE  0x4400
#define SPRITE_ATTR 0x4FF0
#define SPRITE_XY   0x5060
#define IRQ_EN      0x5000
#define IN0         0x5000
#define IN1         0x5040
#define WDOG        0x50C0

#define VRAM_PTR   ((volatile byte *)VRAM_BASE)
#define COLOR_PTR  ((volatile byte *)COLOR_BASE)
#define SPATTR     ((volatile byte *)SPRITE_ATTR)
#define SPXY       ((volatile byte *)SPRITE_XY)

/* 1 = write tile color RAM (0x4400) for CLS/putchar; 0 = skip (for debug/isolation). */
#ifndef PACMAN_TILE_COLOR_RAM
#define PACMAN_TILE_COLOR_RAM 1
#endif
#if PACMAN_TILE_COLOR_RAM
#define PUT_TILE_COLOR(o, v) do { COLOR_PTR[(word)(o)] = (byte)(v); } while(0)
#else
#define PUT_TILE_COLOR(o, v) do { } while(0)
#endif

/*
 * Logical grid: x,y in 0..31 like Galaxian BASIC. Map to MAME tilemap (36×28) as
 * col = x+2, row = y, then apply pacman_scan_rows (see mame/pacman/pacman_v.cpp).
 * NOT the Galaxian formula (29-x)*32+y — Pac-Man VRAM is scrambled on screen.
 */
/* Stock pacman.5e: 0x00-0x0F = hex 0-F; 0x30-0x39 = decimal digits; 0x40 = space; 0x41-0x5A = A-Z */
#define BLANK_TILE     0x40U
/* Used only when PACMAN_TILE_COLOR_RAM=1 (CLS / putchar / COLOR column refresh). */
#define CLR_COLOR_RAM  0x01U

/* Color RAM: on stock Pac-Man, palette entries with even index read as black;
 * odd indices are visible. Map BASIC attr 0 -> 0 (blank), else force odd. */
static byte pacman_color_hw(byte a) {
  if (a == 0)
    return 0;
  return (byte)((a | 1U) & 0x0FU);
}

struct sprite {
  byte xpos;
  byte ypos;
  byte code;
  byte color;
};

static struct sprite sprites[8];
static byte scroll_buf[32];
static byte col_attr[32];

#if PACMAN_TILE_COLOR_RAM
static byte color_for_tile(byte x, byte ch) {
  byte c = pacman_color_hw(col_attr[x] & 0x0FU);
  if (c == 0)
    c = CLR_COLOR_RAM;
  (void)ch;
  return c;
}
#endif

volatile word video_framecount = 0;

static void pet_watchdog(void) {
  *(volatile byte *)WDOG = 0;
}

static void pacman_hide_all_sprites_hw(void) {
  byte i;
  for (i = 0; i < 8; i++) {
    SPATTR[(word)i * 2U] = 0;
    SPATTR[(word)i * 2U + 1U] = 0;
    SPXY[(word)i * 2U] = 0;
    SPXY[(word)i * 2U + 1U] = 0xD0U;
  }
}

#ifdef PACMAN_VRAM_TEST
/* LFSR tile bytes + odd color nibbles so the pattern is visible (even palette = black). */
static void pacman_fill_vram_test(void) {
  word i;
  word s = 0xB5A3u;
  for (i = 0; i < 1024; i++) {
    byte t;
    byte c;
    s ^= s << 7;
    s ^= s >> 11;
    s ^= s << 9;
    t = (byte)(s ^ (s >> 8) ^ (byte)i);
    c = (byte)(((i >> 2) & 7U) * 2U + 1U);
    VRAM_PTR[i] = t;
    PUT_TILE_COLOR(i, c & 0x0FU);
  }
}
#endif

/*
 * Tile codes for stock Pac-Man gfx (pacman.5e):
 *   0x00-0x0F = hex display 0-F; 0x30-0x39 = decimal digits 0-9; 0x40 = space; 0x41-0x5A = A-Z.
 * (Galaxian used c-0x30 and blank 0x10 — wrong here: 0x10 is not space on Pac-Man.)
 */
static byte CHAR(char c) {
  if (c >= '0' && c <= '9')
    return (byte)(0x30U + (unsigned char)(c - '0'));
  if (c == ' ' || c == '@')
    return BLANK_TILE;
  if (c >= 'A' && c <= 'Z')
    return (byte)c;
  if (c >= 'a' && c <= 'z')
    return (byte)(c - 0x20);
  return (byte)(c - 0x30);
}

/* MAME TILEMAP_MAPPER_MEMBER(pacman_state::pacman_scan_rows) — signed col/row.
 * Screen rotated & mirrored: BASIC x→tilemap row (reversed), y→tilemap col. */
static word vram_ofs(byte x, byte y) {
  int col_tm, row_tm;  /* tilemap coordinates */
  int c, r;            /* pacman_scan_rows internal */
  if (x > 27) x = 27;  /* Only 28 tilemap rows */
  col_tm = (int)y + 2; /* BASIC y=0..31 -> tilemap col=2..33 */
  row_tm = 27 - (int)x; /* BASIC x=0..27 -> tilemap row=27..0 (reversed for left-to-right text) */
  /* Apply MAME pacman_scan_rows(col_tm, row_tm) */
  r = row_tm + 2;
  c = col_tm - 2;
  if (c & 0x20)
    return (word)(r + ((c & 0x1f) << 5));
  return (word)(c + (r << 5));
}

void memset_safe(void *dest, char ch, word size) {
  byte *d = dest;
  while (size--)
    *d++ = (byte)ch;
}

void putchar(byte x, byte y, byte ch) {
  if (x < 32 && y < 32) {
    word o = vram_ofs(x, y);
    VRAM_PTR[o] = ch;
#if PACMAN_TILE_COLOR_RAM
    PUT_TILE_COLOR(o, color_for_tile(x, ch));
#endif
  }
}

void fill(byte x, byte y, byte w, byte h, byte ch) {
  byte ix, iy;
  if (x >= 32 || y >= 32)
    return;
  if (x + w > 32)
    w = 32 - x;
  if (y + h > 32)
    h = 32 - y;
  for (ix = 0; ix < w; ix++)
    for (iy = 0; iy < h; iy++)
      putchar(x + ix, y + iy, ch);
}

void putshape(byte x, byte y, byte ofs) {
  putchar(x, y, ofs + 2);
  putchar(x + 1, y, ofs);
  putchar(x, y + 1, ofs + 3);
  putchar(x + 1, y + 1, ofs + 1);
}

void putstring(byte x, byte y, const char *s) {
  while (*s)
    putchar(x++, y, CHAR(*s++));
}

void set_sprite(byte n, byte x, byte y, byte code, byte color) {
  if (n < 8) {
    sprites[n].xpos = x;
    sprites[n].ypos = y;
    sprites[n].code = code;
    sprites[n].color = color;
  }
}

void hide_sprite(byte n) {
  if (n < 8) {
    sprites[n].xpos = 0;
    sprites[n].ypos = 0xD0U;
    sprites[n].code = 0x1FU;
    sprites[n].color = 0;
  }
}

void set_missile(byte n, byte x, byte y) {
  (void)n;
  (void)x;
  (void)y;
}

void clrscr(void) {
  word i;

  memset_safe(col_attr, 0, 32);
  memset_safe(scroll_buf, 0, 32);
  /*
   * Pac-Man visible VRAM: bytes 0-319 (bottom strip + main columns) and 960-1023 (top strip).
   * Middle range 320-959 is not scanned by video hardware.
   */
  for (i = 0; i < 320; i++) {
    VRAM_PTR[i] = BLANK_TILE;
    PUT_TILE_COLOR(i, CLR_COLOR_RAM);
  }
  for (i = 960; i < 1024; i++) {
    VRAM_PTR[i] = BLANK_TILE;
    PUT_TILE_COLOR(i, CLR_COLOR_RAM);
  }
}

void set_scroll(byte col, byte val) {
  // if (col < 32)
  //   scroll_buf[col] = val;
}

void set_column_attrib(byte col, byte attr) {
  if (col >= 32)
    return;
  col_attr[col] = attr & 0x0FU;
#if PACMAN_TILE_COLOR_RAM
  {
    byte row;
    for (row = 0; row < 32; row++) {
      word o = vram_ofs(col, row);
      PUT_TILE_COLOR(o, color_for_tile(col, VRAM_PTR[o]));
    }
  }
#endif
}

static void flush_sprites(void) {
  byte i;
  for (i = 0; i < 8; i++) {
    byte c = sprites[i].code & 0x3FU;
    byte hw_y, hw_x;
    SPATTR[(word)i * 2U] = (byte)((c << 2) & 0xFCU);
    SPATTR[(word)i * 2U + 1U] =sprites[i].color;
    /* Pac-Man sprite coords: rotated screen, swap and invert both axes
     * BASIC x -> hw_y (255-x), BASIC y -> hw_x (272-y) */
    hw_y = (byte)(255U - sprites[i].xpos);
    hw_x = (byte)(272U - sprites[i].ypos);
    SPXY[(word)i * 2U] = hw_y;
    SPXY[(word)i * 2U + 1U] = hw_x;
  }
}

byte joystick_left(void) {
  return *(volatile byte *)IN0 & 0x02U ? 0U : 1U;
}
byte joystick_right(void) {
  return *(volatile byte *)IN0 & 0x04U ? 0U : 1U;
}
byte joystick_up(void) {
  return *(volatile byte *)IN0 & 0x01U ? 0U : 1U;
}
byte joystick_down(void) {
  return *(volatile byte *)IN0 & 0x08U ? 0U : 1U;
}

byte input_pressed(byte n) {
  volatile byte in0v = *(volatile byte *)IN0;
  volatile byte in1v = *(volatile byte *)IN1;
  switch (n) {
  case 0:
    return (in0v & 0x02U) ? 0U : 1U;
  case 1:
    return (in0v & 0x04U) ? 0U : 1U;
  case 2:
    return (in0v & 0x01U) ? 0U : 1U;
  case 3:
    return (in0v & 0x08U) ? 0U : 1U;
  case 4:
    return 0U;
  case 5:
    return 0U;
  case 6:
    return (in0v & 0x20U) ? 0U : 1U;
  case 7:
    return (in1v & 0x20U) ? 0U : 1U;
  case 8:
    return (in1v & 0x02U) ? 0U : 1U;
  case 9:
    return (in1v & 0x04U) ? 0U : 1U;
  case 10:
    return (in1v & 0x01U) ? 0U : 1U;
  case 11:
    return (in1v & 0x08U) ? 0U : 1U;
  case 12:
    return 0U;
  case 13:
    return 0U;
  case 14:
    return (in0v & 0x40U) ? 0U : 1U;
  case 15:
    return (in1v & 0x40U) ? 0U : 1U;
  case 16:
    return (in0v & 0x80U) ? 0U : 1U;
  default:
    return 0U;
  }
}

static word framecount = 0;

void wait_for_frame(void) {
  framecount++;
  pet_watchdog();
  while (video_framecount < framecount) {
    pet_watchdog();
    __asm HALT __endasm;
  }
  if (video_framecount == 32768) {
    video_framecount = 0;
    framecount = 0;
  }
  flush_sprites();
  (void)scroll_buf;
}

void runtime_init(void) {
  pacman_hide_all_sprites_hw();
#ifdef PACMAN_VRAM_TEST
  pacman_fill_vram_test();
#endif
  volatile byte *irq = (volatile byte *)IRQ_EN;
  irq[0] = 0x01U;
  (void)*(volatile byte *)IN0;
  (void)*(volatile byte *)IN1;
  __asm
    EI
  __endasm;
}
