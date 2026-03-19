/*
 * Galaxian BASIC - Runtime API
 * Declarations for programs compiled from BASIC.
 */

#ifndef RUNTIME_H
#define RUNTIME_H

typedef unsigned char byte;
typedef unsigned short word;

/* Call once at start of main() - enables vblank interrupt */
void runtime_init(void);

/* Display */
void clrscr(void);
void putchar(byte x, byte y, byte ch);
void putstring(byte x, byte y, const char *s);

/* Sprites */
void set_sprite(byte n, byte x, byte y, byte code, byte color);
void hide_sprite(byte n);

/* Scrolling */
void set_scroll(byte col, byte val);
void set_column_attrib(byte col, byte attr);

/* Frame sync - call each frame, handles watchdog */
void wait_for_frame(void);

/* Joystick 1P - returns 1 if pressed, 0 otherwise. JOY(0)=left, 1=right, 2=up, 3=down */
byte joystick_left(void);
byte joystick_right(void);
byte joystick_up(void);
byte joystick_down(void);

#endif
