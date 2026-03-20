; Pac-Man (Namco) - CRT0
; Z80 reset at 0x0000. IRQ (vblank) uses IM 1 -> RST 0x38.
; Work RAM 0x4C00-0x4FEF; stack below hardware sprite regs at 0x4FF0.
	.module crt0
	.area _CODE
	.globl _main
	.globl _video_framecount

_start::
	LD	SP, #0x4F00
	DI
	IM	1
	; Set interrupt vector (required for Pac-Man hardware)
	LD	A, #0xFF
	OUT	(#0x00), A
	; Enable IRQ hardware (write 1 to 0x5000)
	LD	A, #0x01
	LD	(#0x5000), A
	; Kick watchdog before enabling interrupts
	XOR	A
	LD	(#0x50C0), A
	EI
	JP	_main

	; Pad to 0x38 (IM 1 IRQ vector)
	.ds	0x38 - (. - _start)

_vblank_isr::
	PUSH	AF
	PUSH	HL
	DI
	; Disable IRQ hardware
	XOR	A
	LD	(#0x5000), A
	; Pet watchdog
	LD	(#0x50C0), A
	; Increment frame counter
	LD	HL, #_video_framecount
	INC	(HL)
	JR	NZ, _vf_done
	INC	HL
	INC	(HL)
_vf_done::
	; Re-enable IRQ hardware
	LD	A, #0x01
	LD	(#0x5000), A
	POP	HL
	POP	AF
	EI
	RETI
