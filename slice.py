#!/usr/bin/env python3
"""Slice ROM for MAME scramble. Run from galaxian-basic/ directory."""
import os

input_file = "build/galaxian-scramble-game.rom"
outputdir = "scramble"

if not os.path.exists(outputdir):
    os.makedirs(outputdir)

slices = [
    ("s1.2d", 0x000, 0x800),
    ("s2.2e", 0x800, 0x1000),
    ("s3.2f", 0x1000, 0x1800),
    ("s4.2h", 0x1800, 0x2000),
    ("s5.2j", 0x2000, 0x2800),
    ("s6.2l", 0x2800, 0x3000),
    ("s7.2m", 0x3000, 0x3800),
    ("s8.2p", 0x3800, 0x4000),
    ("c2.5f", 0x4000, 0x4800),
    ("c1.5h", 0x4800, 0x5000),
    ("c01s.6e", 0x5000, 0x5020),
]

with open(input_file, "rb") as infile:
    for filename, start, end in slices:
        infile.seek(start)
        slice_data = infile.read(end - start)
        if filename == "c01s.6e":
            modified = bytearray()
            for i in range(0, len(slice_data), 4):
                modified.extend([slice_data[i], slice_data[i + 2], slice_data[i + 1], slice_data[i + 3]])
            slice_data = modified
        with open(os.path.join(outputdir, filename), "wb") as outfile:
            outfile.write(slice_data)

print("Slicing and saving completed.")
