/*
 * Galaxian BASIC - Demo program
 * Built when no PROGRAM= is specified. Shows bouncing sprites and scrolling.
 */

#include "runtime.h"

void main(void) {
  byte frame = 0;
  byte y0 = 4, y1 = 12, y2 = 20;
  byte dy0 = 1, dy1 = 1, dy2 = 255;
  byte scroll = 0;

  clrscr();
  putstring(8, 10, "GALAXIAN BASIC");
  putstring(6, 12, "READY");
  putstring(5, 15, "INPUT OK");
  putstring(2, 20, "WATCHDOG OK");

  {
    byte x;
    for (x = 4; x < 28; x++) {
      putchar(x, 24, (x + 1) & 0x0F);
      set_column_attrib(x, 2);
    }
  }

  runtime_init();

  while (1) {
    if ((frame & 3) == 0) {
      y0 += dy0;
      if (y0 >= 26) { y0 = 26; dy0 = 255; }
      else if (y0 <= 2) { y0 = 2; dy0 = 1; }
      y1 += dy1;
      if (y1 >= 24) { y1 = 24; dy1 = 255; }
      else if (y1 <= 4) { y1 = 4; dy1 = 1; }
      y2 += dy2;
      if (y2 >= 22) { y2 = 22; dy2 = 255; }
      else if (y2 <= 6) { y2 = 6; dy2 = 1; }
    }

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
