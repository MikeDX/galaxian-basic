# Galaxian BASIC - Makefile
# Build runtime for Galaxian/Scramble hardware. Run from galaxian-basic/ directory.
# All output stays in galaxian-basic/ (build/, scramble/).
#
# BASIC -> C -> ROM pipeline:
#   make PROGRAM=examples/hello.bas   # Compile BASIC to ROM
#   make PROGRAM=examples/hello.bas run
#
# Default (no PROGRAM): builds demo with bouncing sprites.

PROJECT_NAME ?= galaxian-scramble-game
PARENT := ..

# PROGRAM=path/to/file.bas compiles BASIC to C and builds ROM
# Default: examples/demo.bas (bouncing sprites + scrolling)
PROGRAM ?= examples/demo.bas

# SDCC 3.8.0
SDCC_HOME ?= $(HOME)/Downloads/sdcc-3.8.0
SDCC_BIN  ?= $(SDCC_HOME)/bin
SDCC_LIB  ?= $(SDCC_HOME)/share/sdcc/lib/z80

CC = $(SDCC_BIN)/sdcc
AS = $(SDCC_BIN)/sdasz80
LD = $(SDCC_BIN)/sdldz80

BUILD_DIR = build
SCRAMBLE_DIR = scramble
ROM_FILE  = $(BUILD_DIR)/$(PROJECT_NAME).rom
MAP_FILE  = $(BUILD_DIR)/$(PROJECT_NAME).map

RUNTIME_C = lib/runtime.c
CRT0_ASM  = lib/crt0.asm
DEMO_C    = src/demo.c
PROGRAM_C = $(BUILD_DIR)/program.c

# When PROGRAM is set: program.rel. Else: demo.rel
ifeq ($(PROGRAM),)
  MAIN_OBJ = $(BUILD_DIR)/demo.rel
  MAIN_SRC = $(DEMO_C)
else
  MAIN_OBJ = $(BUILD_DIR)/program.rel
  MAIN_SRC = $(PROGRAM_C)
endif

OBJECTS   = $(BUILD_DIR)/crt0.rel $(BUILD_DIR)/runtime.rel $(MAIN_OBJ)

# Graphics: always use .gfx.json as source (PROGRAM's or default)
GFXDATA_H = $(BUILD_DIR)/gfxdata.h
GFX_JSON = $(patsubst %.bas,%.gfx.json,$(PROGRAM))
DEFAULT_GFX = lib/default.gfx.json

CFLAGS = --vc --std-sdcc99 -mz80 --less-pedantic --oldralloc --no-peep --nolospre
ASFLAGS = -plosgffwyu
LDFLAGS = -mjwxyu -i $(BUILD_DIR)/main.ihx -b _CODE=0x0 -b _DATA=0x4000 -b _INITIALIZER=0x3C00 -k $(SDCC_LIB) -l z80
INCLUDES = -I$(BUILD_DIR) -I. -Ilib

.PHONY: all run clean check-sdcc info help

all: check-sdcc $(ROM_FILE) post-build

help:
	@echo "Galaxian BASIC - Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  make [all]  - Build ROM (default: examples/demo.bas)"
	@echo "  make run    - Build and run in MAME"
	@echo "  make clean  - Remove build artifacts (keeps crt0.asm)"
	@echo "  make info   - Show ROM info"
	@echo ""
	@echo "BASIC -> ROM pipeline:"
	@echo "  make                          - Build demo.bas (bouncing sprites)"
	@echo "  make PROGRAM=examples/hello.bas"
	@echo "  make PROGRAM=examples/chase.bas run   - Joystick + enemy"
	@echo "  make PROGRAM=examples/sprite.bas run"
	@echo "  make PROGRAM=                  - Build C demo (no BASIC)"
	@echo ""
	@echo "Output: build/$(PROJECT_NAME).rom, scramble/*.2d etc"
	@echo "MAME:   mame scramble -rompath ."
	@echo ""
	@echo "Graphics:"
	@echo "  make gfx-export              - Export default gfx to examples/default.gfx.json"
	@echo "  make PROGRAM=x.bas          - Uses x.gfx.json if present (same dir as .bas)"

check-sdcc:
	@if [ ! -x "$(CC)" ]; then \
		echo "Error: SDCC not found at $(CC)"; \
		exit 1; \
	fi
	@echo "Using SDCC from $(SDCC_HOME)"
	@$(CC) --version | head -1

# BASIC -> C compilation - always rebuild when PROGRAM is set (it may have changed)
.PHONY: .force-program
.force-program:

$(PROGRAM_C): $(PROGRAM) .force-program
	@mkdir -p $(BUILD_DIR)
	@echo "Compiling BASIC: $(PROGRAM) -> $@"
	@python3 scripts/gbasic.py $(PROGRAM) -o $@

$(GFXDATA_H):
	@mkdir -p $(BUILD_DIR)
	@if [ -n "$(GFX_JSON)" ] && [ -f "$(GFX_JSON)" ]; then \
		echo "Graphics: $(GFX_JSON) -> $@"; \
		python3 scripts/gfxmanager.py to-header $(GFX_JSON) -o $@; \
	else \
		echo "Graphics: $(DEFAULT_GFX) -> $@"; \
		python3 scripts/gfxmanager.py to-header $(DEFAULT_GFX) -o $@; \
	fi

$(BUILD_DIR)/runtime.asm: $(RUNTIME_C) $(GFXDATA_H)
	@mkdir -p $(BUILD_DIR)
	@echo "Compiling $(RUNTIME_C) ..."
	$(CC) -S $(CFLAGS) $(INCLUDES) -o $@ $<

$(BUILD_DIR)/program.asm: $(PROGRAM_C)
	@mkdir -p $(BUILD_DIR)
	@echo "Compiling $(PROGRAM_C) ..."
	$(CC) -S $(CFLAGS) $(INCLUDES) -o $@ $<

$(BUILD_DIR)/program.rel: $(BUILD_DIR)/program.asm
	@echo "Assembling program.asm ..."
	$(AS) $(ASFLAGS) -o $@ $<

$(BUILD_DIR)/demo.rel: $(DEMO_C)
	@mkdir -p $(BUILD_DIR)
	@echo "Compiling $(DEMO_C) ..."
	$(CC) -S $(CFLAGS) $(INCLUDES) -o $(BUILD_DIR)/demo.asm $<
	$(AS) $(ASFLAGS) -o $@ $(BUILD_DIR)/demo.asm

$(BUILD_DIR)/crt0.rel: $(CRT0_ASM)
	@mkdir -p $(BUILD_DIR)
	@echo "Assembling $(CRT0_ASM) ..."
	$(AS) $(ASFLAGS) -o $@ $<

$(BUILD_DIR)/runtime.rel: $(BUILD_DIR)/runtime.asm
	@echo "Assembling runtime.asm ..."
	$(AS) $(ASFLAGS) -o $@ $<

$(BUILD_DIR)/main.ihx: $(OBJECTS)
	@echo "Linking ..."
	$(LD) $(LDFLAGS) $(OBJECTS)

$(ROM_FILE): $(BUILD_DIR)/main.ihx
	@mkdir -p $(BUILD_DIR)
	@echo "Creating ROM ..."
	@python3 $(PARENT)/hex2rom.py $(BUILD_DIR)/main.ihx $@ || (echo "hex2rom.py failed"; exit 1)
	@echo "ROM: $@"
	@ls -la $@

post-build: $(ROM_FILE)
	@echo "Slicing ROM for MAME scramble ..."
	@mkdir -p $(SCRAMBLE_DIR)
	@python3 scripts/slice.py
	@if [ -f "$(PARENT)/sound.bin" ]; then \
		echo "Extracting sound ROMs ..."; \
		(cd $(PARENT) && python3 slicesound.py); \
		cp $(PARENT)/ot1.5c $(PARENT)/ot2.5d $(PARENT)/ot3.5e $(SCRAMBLE_DIR)/; \
		echo "Sound ROMs copied to $(SCRAMBLE_DIR)/"; \
	else \
		for dir in $(PARENT)/roms/pitfall $(PARENT)/roms_backup/pitfall; do \
			if [ -f "$$dir/ot1.5c" ]; then \
				echo "Copying sound ROMs from $$dir ..."; \
				cp "$$dir/ot1.5c" "$$dir/ot2.5d" "$$dir/ot3.5e" $(SCRAMBLE_DIR)/; \
				break; \
			fi; \
		done; \
	fi
	@echo ""
	@echo "Build complete. Run: mame scramble -rompath ."

run: all
	@echo "Running MAME scramble ..."
	mame scramble -rompath . -window

# Clean: remove generated files. Source in lib/, src/, scripts/ preserved.
clean:
	@echo "Cleaning build artifacts ..."
	rm -rf $(BUILD_DIR)
	rm -f *.lst *.sym *.map *.ihx *.lk *.rst *.noi
	@echo "Clean done."

info: $(ROM_FILE)
	@echo "=== Galaxian BASIC Build ==="
	@echo "ROM: $(ROM_FILE)"
	@echo "Size: $(shell wc -c < $(ROM_FILE)) bytes"
	@echo "Scramble: $(SCRAMBLE_DIR)/ ($(shell ls $(SCRAMBLE_DIR) 2>/dev/null | wc -l) files)"
	@if [ -f $(MAP_FILE) ]; then echo ""; echo "=== Symbols ==="; cat $(MAP_FILE); fi

# Web IDE - serve on http://localhost:8080
ide:
	@echo "Starting IDE at http://localhost:8080"
	cd ide && python3 -m http.server 8080

# Legacy: export gfxdata.h to .gfx.json (only needed for migration)
gfx-export:
	@echo "Exporting lib/gfxdata.h -> lib/default.gfx.json"
	@python3 scripts/gfxmanager.py from-header lib/gfxdata.h -o lib/default.gfx.json
	@echo "Note: .gfx.json is now the source format. lib/gfxdata.h is deprecated."
