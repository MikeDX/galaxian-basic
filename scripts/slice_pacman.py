#!/usr/bin/env python3
"""Split 16 KiB CPU ROM into pacman.6e-6j and merge with stock Pac-Man gfx ROMs."""
import os
import shutil
import sys
from typing import Optional

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "pacman")
INPUT_ROM = os.path.join(ROOT, "build", "pacman-basic-game.rom")

CHIPS = [
    ("pacman.6e", 0x0000),
    ("pacman.6f", 0x1000),
    ("pacman.6h", 0x2000),
    ("pacman.6j", 0x3000),
]

GFX = [
    "pacman.5e",
    "pacman.5f",
    "82s123.7f",
    "82s126.4a",
    "82s126.1m",
    "82s126.3m",
]


def find_rom_dir() -> Optional[str]:
    env = os.environ.get("PACMAN_ROM_PATH", "").strip()
    if env and os.path.isdir(env):
        return env
    candidates = [
        os.path.join(ROOT, "roms", "pacman"),
        os.path.join(ROOT, "..", "roms", "pacman"),
        os.path.expanduser("~/.mame/roms/pacman"),
    ]
    for c in candidates:
        if os.path.isfile(os.path.join(c, "pacman.5e")):
            return c
    return None


def main() -> None:
    if not os.path.isfile(INPUT_ROM):
        print(f"slice_pacman: missing {INPUT_ROM}", file=sys.stderr)
        sys.exit(1)
    with open(INPUT_ROM, "rb") as f:
        data = f.read()
    if len(data) < 0x4000:
        print(f"slice_pacman: ROM too small ({len(data)} bytes)", file=sys.stderr)
        sys.exit(1)
    data = data[:0x4000]
    os.makedirs(OUT, exist_ok=True)
    rebuilt = bytearray()
    for name, off in CHIPS:
        chunk = data[off : off + 0x1000]
        if len(chunk) != 0x1000:
            print(f"slice_pacman: bad chunk len for {name}", file=sys.stderr)
            sys.exit(1)
        rebuilt.extend(chunk)
        path = os.path.join(OUT, name)
        with open(path, "wb") as wf:
            wf.write(chunk)
        h = " ".join(f"{b:02X}" for b in chunk[:8])
        print(f"  wrote {path}  (first 8 bytes: {h} ...)")
    if bytes(rebuilt) != data:
        print("slice_pacman: internal error: rejoin != source", file=sys.stderr)
        sys.exit(1)
    print("  verify: pacman.6e||6f||6h||6j == 16 KiB CPU image (OK)")

    src = find_rom_dir()
    if src:
        for g in GFX:
            s = os.path.join(src, g)
            d = os.path.join(OUT, g)
            if os.path.isfile(s):
                shutil.copy2(s, d)
                print(f"  gfx: {g} <- {src}")
            else:
                print(f"  warning: missing {s}", file=sys.stderr)
    else:
        print(
            "  No Pac-Man gfx ROMs found. Copy pacman.5e, pacman.5f, "
            "82s123.7f, 82s126.4a, 82s126.1m, 82s126.3m into pacman/ "
            "or set PACMAN_ROM_PATH to a folder containing them.",
            file=sys.stderr,
        )
    print("slice_pacman: done.")


if __name__ == "__main__":
    main()
