; Galaxian BASIC - CRT0
; Must be at 0x0000 - Z80 reset vector. Links first so this is first in ROM.
; Interrupt at 0x66 (Galaxian vblank) - minimal handler, only increments video_framecount.
; Pitfall pattern: main does wait_for_frame() (HALT), then updatesprites/scroll right after.
	.module crt0
	.area _CODE
	.globl _main
	.globl _video_framecount

_start::
	LD	SP, #0x4800
	DI
	JP	_main

	; Pad to 0x66 - Galaxian hardware triggers interrupt to this address
	.ds	0x66 - (. - _start)

; Vblank interrupt - minimal (Pitfall pattern). Only increment frame counter.
	PUSH	HL
	LD	HL, #_video_framecount
	INC	(HL)
	JR	NZ, _vblank_done
	INC	HL
	INC	(HL)
_vblank_done::
	POP	HL
	EI
	RETI
