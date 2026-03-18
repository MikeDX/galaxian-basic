/*
 * Galaxian BASIC - Skeleton Runtime
 *
 * Minimal runtime for Galaxian/Scramble hardware. Uses gfxtest-style
 * minimal layout (no platform.h). Displays "GALAXIAN BASIC", polls
 * input, services watchdog. Builds to ROM for MAME scramble driver.
 *
 * Inputs:  input0, input1, input2 (joystick, buttons, coin, start)
 * Outputs: watchdog (must be called or hardware resets)
 */

typedef unsigned char byte;
typedef unsigned short word;

/* Hardware layout - Scramble addresses */
#define VRAM   0x4800
#define TRAM   0x5000
#define ORAM   0x5040
#define WATCHDOG_ADDR 0x7000
#define IRQ_ADDR      0x6801
#define INPUT0 0x8100
#define INPUT1 0x8101
#define INPUT2 0x8102

byte __at (VRAM) vram[32][32];
#define VRAM_PTR ((volatile byte *)VRAM)
struct { byte scroll; byte attrib; } __at (TRAM) vcolumns[32];

/* gfxtest-style tile ROM + palette */
#include "gfxdata.h"

/* Sprite RAM at ORAM - hardware reads directly. We write via updatesprites(). */
struct sprite { byte xpos; byte code; byte color; byte ypos; };
struct sprite __at (ORAM) vsprites[8];
struct { byte u1; byte xpos; byte u2; byte ypos; } __at (ORAM + 0x20) vmissiles[8];

/* Our sprite buffer in RAM - main loop writes here, vblank copies to hardware */
static struct sprite sprites[8];
/* Scroll buffer - main loop writes here, vblank copies to vcolumns */
static byte scroll_buf[32];

volatile byte __at (WATCHDOG_ADDR) watchdog_reg;
volatile byte __at (IRQ_ADDR) enable_irq;
volatile byte __at (INPUT0) input0;
volatile word video_framecount = 0;
volatile byte __at (INPUT1) input1;
volatile byte __at (INPUT2) input2;

#define watchdog __asm ld a, (#_watchdog_reg) __endasm

/* gfxdata remap:[3,0,1,2,4,5,6,7,8,9,10] - inverse for digits 0-9 */
static const byte remap_inv[10] = {1, 2, 3, 0, 4, 5, 6, 7, 8, 9};
static byte CHAR(char c) {
  if (c >= '0' && c <= '9') return remap_inv[c - '0'];
  if (c == ' ' || c == '@') return 0x10;
  return (byte)(c - 0x30);
}
#define BLANK 0x10

void memset_safe(void *dest, char ch, word size) {
  byte *d = dest;
  while (size--) *d++ = (byte)ch;
}

/* Pitfall platform.h line 379: vram[29-x][y] = ch */
void putchar(byte x, byte y, byte ch) {
  if (x < 32 && y < 32) VRAM_PTR[(29 - x) * 32 + y] = ch;
}

void putstring(byte x, byte y, const char *s) {
  while (*s) {
    putchar(x++, y, CHAR(*s++));
  }
}

/* Set sprite n (0-7) in our buffer. Call updatesprites() to push to hardware. */
void set_sprite(byte n, byte x, byte y, byte code, byte color) {
  if (n < 8) {
    sprites[n].xpos = x;
    sprites[n].ypos = y;
    sprites[n].code = code;
    sprites[n].color = color;
  }
}

/* Hide sprite n */
void hide_sprite(byte n) {
  if (n < 8) {
    sprites[n].xpos = 0xff;
    sprites[n].ypos = 0xff;
    sprites[n].code = 0x17;
  }
}

/* Match Pitfall platform.h clrscr: vram=BLANK, vcolumns=0 (no attrib=1) */
void clrscr(void) {
  memset_safe((void *)VRAM_PTR, BLANK, 32 * 32);
  memset_safe(vcolumns, 0, 0x100);  /* Pitfall: clears vcolumns + sprites area */
  memset_safe(scroll_buf, 0, 32);
}

/* Set scroll offset for column col (0-31). Buffered - applied in wait_for_frame. */
void set_scroll(byte col, byte val) {
  if (col < 32) scroll_buf[col] = val;
}

/* Set column attrib (color) for column col */
void set_column_attrib(byte col, byte attr) {
  if (col < 32) vcolumns[col].attrib = attr;
}

/* Pitfall pattern: wait for vblank (HALT until interrupt), then copy to hardware.
 * "Copying the sprites here prevents any tearing" - shoot2.c wait_for_frame */
static word framecount = 0;
void wait_for_frame(void) {
  framecount++;
  watchdog;
  enable_irq = 0;
  enable_irq = 1;
  while (video_framecount < framecount) {
    __asm
      HALT
    __endasm;
  }
  if (video_framecount == 32768) {
    video_framecount = 0;
    framecount = 0;
  }
  /* Copy buffers to hardware - we just woke from vblank, safe to update */
  {
    byte i;
    for (i = 0; i < 8; i++) {
      vsprites[i].xpos = sprites[i].xpos;
      vsprites[i].ypos = sprites[i].ypos;
      vsprites[i].code = sprites[i].code;
      vsprites[i].color = sprites[i].color;
    }
    for (i = 0; i < 32; i++) {
      vcolumns[i].scroll = scroll_buf[i];
    }
  }
}

void main(void);

/* Entry point is crt0.asm (_start at 0x0000) - links first so Z80 runs it on reset */

void main(void) {
  byte frame = 0;
  byte y0 = 4, y1 = 12, y2 = 20;   /* tile y positions */
  byte dy0 = 1, dy1 = 1, dy2 = 255;  /* 1=down, 255=up */
  byte scroll = 0;  /* horizontal scroll offset */

  clrscr();

  putstring(8, 10, "GALAXIAN BASIC");
  putstring(6, 12, "READY");
  putstring(5, 15, "INPUT OK");
  putstring(2, 20, "WATCHDOG OK");

  /* Scrolling strip: fill row 24 with a pattern across columns 4-27 */
  {
    byte x;
    for (x = 4; x < 28; x++) {
      putchar(x, 24, (x + 1) & 0x0F);  /* tile pattern 0-F */
      set_column_attrib(x, 2);  /* color for scroll area */
    }
  }

  /* Enable vblank interrupt, enable CPU interrupts (Pitfall pattern) */
  enable_irq = 1;
  __asm
    EI
  __endasm;

  /* Main loop: compute into buffers, wait_for_frame copies to hardware at vblank */
  while (1) {
    /* Update position every 4 frames so movement is visible */
    if ((frame & 3) == 0) {
    /* Bounce y0 between 2 and 26 */
    y0 += dy0;
    if (y0 >= 26) { y0 = 26; dy0 = 255; }
    else if (y0 <= 2) { y0 = 2; dy0 = 1; }
    /* Bounce y1 between 4 and 24 */
    y1 += dy1;
    if (y1 >= 24) { y1 = 24; dy1 = 255; }
    else if (y1 <= 4) { y1 = 4; dy1 = 1; }
    /* Bounce y2 between 6 and 22 */
    y2 += dy2;
    if (y2 >= 22) { y2 = 22; dy2 = 255; }
    else if (y2 <= 6) { y2 = 6; dy2 = 1; }
    }

    /* Tile coords: x fixed (4, 12, 20), y bounces. Pixel = tile * 8 */
    set_sprite(0, 4 * 8, y0 * 8, 0x18, 1);
    set_sprite(1, 8 * 8, y1 * 8, 0x18, 2);
    set_sprite(2, 12 * 8, y0 * 8, 0x18, 3);
    set_sprite(3, 16 * 8, y1 * 8, 0x18, 4);
    set_sprite(4, 20 * 8, y2 * 8, 0x18, 5);
    set_sprite(5, 24 * 8, y0 * 8, 0x18, 6);
    set_sprite(6, 28 * 8, y1 * 8, 0x18, 7);

    hide_sprite(7);

    scroll++;
    {
      byte col;
      for (col = 4; col < 28; col++) {
        set_scroll(col, scroll);
      }
    }

    wait_for_frame();
    frame++;
  }
}
