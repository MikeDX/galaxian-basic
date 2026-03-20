#!/usr/bin/env python3
"""Intel HEX -> 16 KiB Pac-Man CPU ROM (0x0000-0x3FFF only)."""
import sys


def hex2rom_pacman(hex_file: str, rom_file: str) -> None:
    rom = bytearray(0x4000)
    with open(hex_file, "r") as f:
        for line in f:
            if not line.startswith(":"):
                continue
            length = int(line[1:3], 16)
            addr = int(line[3:7], 16)
            rec_type = int(line[7:9], 16)
            if rec_type != 0:
                if rec_type == 1:
                    break
                continue
            data_hex = line[9 : 9 + length * 2]
            data = bytes.fromhex(data_hex)
            for i, byte_val in enumerate(data):
                a = addr + i
                if a < len(rom):
                    rom[a] = byte_val
    with open(rom_file, "wb") as f:
        f.write(rom)
    print(f"Created Pac-Man CPU ROM: {len(rom)} bytes -> {rom_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.ihx> <output.rom>", file=sys.stderr)
        sys.exit(1)
    hex2rom_pacman(sys.argv[1], sys.argv[2])
