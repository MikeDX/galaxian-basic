#!/usr/bin/env python3
"""
Renumber a Galaxian BASIC (.bas) file.

Usage:
  renum.py <file.bas> [options]
  renum.py <file.bas> -o <output.bas>   # write to different file
  renum.py <file.bas> --start 100 --step 10   # start at 100, increment by 10

Updates GOTO and IF...THEN GOTO targets to match new line numbers.
"""

import argparse
import re
import sys
from pathlib import Path


def parse_bas(path: Path) -> list[tuple[int, str]]:
    """Parse .bas file into (line_num, rest) tuples."""
    lines = []
    for raw in path.read_text().splitlines():
        raw = raw.rstrip()
        if not raw:
            continue
        m = re.match(r'^(\d+)\s+(.*)$', raw)
        if m:
            lines.append((int(m.group(1)), m.group(2).rstrip()))
        else:
            # Line without number - skip or treat as continuation (we skip)
            pass
    return lines


def build_old_to_new(lines: list[tuple[int, str]], start: int, step: int) -> dict[int, int]:
    """Build mapping from old line numbers to new ones."""
    return {old: start + i * step for i, (old, _) in enumerate(lines)}


def renumber_statement(rest: str, old_to_new: dict[int, int]) -> str:
    """Replace line number references in statement text."""
    def replace_ref(m: re.Match) -> str:
        prefix, num_str = m.group(1), m.group(2)
        old_num = int(num_str)
        new_num = old_to_new.get(old_num, old_num)
        return f"{prefix}{new_num}"

    # GOTO <num> or THEN GOTO <num>
    pattern = r'\b((?:THEN\s+)?GOTO\s+)(\d+)\b'
    return re.sub(pattern, replace_ref, rest, flags=re.IGNORECASE)


def renum(path: Path, start: int = 10, step: int = 10, out_path: Path | None = None) -> str:
    """Renumber a .bas file. Returns the new content."""
    lines = parse_bas(path)
    if not lines:
        return path.read_text()

    old_to_new = build_old_to_new(lines, start, step)

    out_lines = []
    for old_num, rest in lines:
        new_num = old_to_new[old_num]
        new_rest = renumber_statement(rest, old_to_new)
        out_lines.append(f"{new_num} {new_rest}")

    result = "\n".join(out_lines) + "\n"

    if out_path:
        out_path.write_text(result)
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Renumber a Galaxian BASIC file")
    ap.add_argument("file", type=Path, help="Input .bas file")
    ap.add_argument("-o", "--output", type=Path, help="Output file (default: overwrite input)")
    ap.add_argument("--start", type=int, default=10, help="First line number (default: 10)")
    ap.add_argument("--step", type=int, default=10, help="Increment (default: 10)")
    ap.add_argument("-n", "--dry-run", action="store_true", help="Print result, don't write")
    args = ap.parse_args()

    if not args.file.exists():
        print(f"Error: {args.file} not found", file=sys.stderr)
        return 1

    out_path = args.output if args.output else (None if args.dry_run else args.file)
    result = renum(args.file, start=args.start, step=args.step, out_path=out_path)

    if args.dry_run:
        print(result, end="")
    elif args.output:
        print(f"Renumbered {args.file} -> {args.output}")
    else:
        print(f"Renumbered {args.file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
