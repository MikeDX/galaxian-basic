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
#include <string.h>
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
volatile byte __at (INPUT1) input1;
volatile byte __at (INPUT2) input2;
volatile word video_framecount = 0;

#define watchdog __asm ld a, (#_watchdog_reg) __endasm

/* gfxdata remap:[3,0,1,2,4,5,6,7,8,9,10] - inverse for digits 0-9 */
/* 012->123: tile N shows digit N, so use identity for digits */
static const byte remap_inv[10] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9};
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

/* Fill rectangle (x,y) size w*h with character ch */
void fill(byte x, byte y, byte w, byte h, byte ch) {
  byte ix;
  if (x >= 32 || y >= 32) return;
  if (x + w > 32) w = 32 - x;
  if (y + h > 32) h = 32 - y;
  for (ix = 0; ix < w; ix++)
    memset(&vram[29 - (x + ix)][y], ch, h);
}

/* 2x2 tile block - matches example.c putshape layout */
void putshape(byte x, byte y, byte ofs) {
  putchar(x, y, ofs + 2);
  putchar(x + 1, y, ofs);
  putchar(x, y + 1, ofs + 3);
  putchar(x + 1, y + 1, ofs + 1);
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

/* Set missile n (0-7) - hardware reads directly from vmissiles */
void set_missile(byte n, byte x, byte y) {
  if (n < 8) {
    vmissiles[n].xpos = x;
    vmissiles[n].ypos = y;
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

/* Joystick 1P - returns 1 if pressed, 0 otherwise. Scramble input bits. */
byte joystick_left(void)  { return (input0 & 0x20) ? 0 : 1; }
byte joystick_right(void) { return (input0 & 0x10) ? 0 : 1; }
byte joystick_up(void)    { return ((input2 & 0x10) && (input0 & 0x01)) ? 0 : 1; }
byte joystick_down(void)  { return (input2 & 0x40) ? 0 : 1; }

/* input_pressed(n) - returns 1 if input n is pressed. n: 0=P1L, 1=P1R, 2=P1U, 3=P1D,
 * 4=P1Fire, 5=P1Bomb, 6=Coin1, 7=Start1, 8=P2L, 9=P2R, 10=P2U, 11=P2D,
 * 12=P2Fire, 13=P2Bomb, 14=Coin2, 15=Start2, 16=Service */
byte input_pressed(byte n) {
  switch (n) {
    case 0:  return (input0 & 0x20) ? 0 : 1;  /* P1 Left */
    case 1:  return (input0 & 0x10) ? 0 : 1;  /* P1 Right */
    case 2:  return ((input2 & 0x10) && (input0 & 0x01)) ? 0 : 1;  /* P1 Up */
    case 3:  return (input2 & 0x40) ? 0 : 1;  /* P1 Down */
    case 4:  return (input0 & 0x08) ? 0 : 1;  /* P1 Fire */
    case 5:  return (input0 & 0x02) ? 0 : 1;  /* P1 Bomb */
    case 6:  return (input0 & 0x80) ? 0 : 1;  /* Coin 1 */
    case 7:  return (input1 & 0x80) ? 0 : 1;  /* Start 1 */
    case 8:  return (input1 & 0x20) ? 0 : 1;  /* P2 Left */
    case 9:  return (input1 & 0x10) ? 0 : 1;  /* P2 Right */
    case 10: return (input0 & 0x01) ? 0 : 1; /* P2 Up */
    case 11: return (input2 & 0x01) ? 0 : 1;  /* P2 Down */
    case 12: return (input1 & 0x08) ? 0 : 1;   /* P2 Fire */
    case 13: return (input1 & 0x04) ? 0 : 1;  /* P2 Bomb */
    case 14: return (input0 & 0x40) ? 0 : 1;   /* Coin 2 */
    case 15: return (input1 & 0x40) ? 0 : 1;   /* Start 2 */
    case 16: return (input0 & 0x04) ? 0 : 1;  /* Service */
    default: return 0;
  }
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

/* runtime_init - enables vblank interrupt. Call from main() at startup. */
void runtime_init(void) {
  enable_irq = 1;
  __asm
    EI
  __endasm;
}

/* main() is provided by the compiled program (program.c or generated.c) */
