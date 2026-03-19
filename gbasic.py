#!/usr/bin/env python3
"""
Galaxian BASIC → C compiler
Compiles BASIC source to C that links with the runtime engine.
"""

import re
import sys
from pathlib import Path


def tokenize_line(line: str) -> list:
    """Split a BASIC line into tokens, preserving strings."""
    tokens = []
    i = 0
    while i < len(line):
        # Skip whitespace
        if line[i].isspace():
            i += 1
            continue
        # String literal
        if line[i] == '"':
            end = line.index('"', i + 1) if '"' in line[i+1:] else len(line)
            tokens.append(('STR', line[i+1:end]))
            i = end + 1
            continue
        # Number
        if line[i].isdigit():
            start = i
            while i < len(line) and line[i].isdigit():
                i += 1
            tokens.append(('NUM', int(line[start:i])))
            continue
        # Identifier or keyword
        if line[i].isalpha():
            start = i
            while i < len(line) and (line[i].isalnum() or line[i] == '_'):
                i += 1
            tok = line[start:i].upper()
            tokens.append(('ID', tok))
            continue
        # Punctuation
        tokens.append(('PUNCT', line[i]))
        i += 1
    return tokens


def parse_expr(tokens: list) -> tuple:
    """Parse simple expr: num, var, JOY(n), var+num, var-num, var*num, var+var, var-var. Returns (type, args)."""
    if not tokens:
        return None
    t = tokens[0]
    if t[0] == 'NUM':
        return ('num', t[1])
    if t[0] == 'ID' and t[1] == 'JOY':
        if len(tokens) >= 4 and tokens[1][1] == '(' and tokens[2][0] == 'NUM' and tokens[3][1] == ')':
            n = tokens[2][1]
            if 0 <= n <= 3:
                return ('joy', n)
    if t[0] == 'ID':
        var = t[1].lower()
        if len(tokens) >= 3 and tokens[1][0] == 'PUNCT':
            op = tokens[1][1]
            t2 = tokens[2]
            if op == '+' and t2[0] == 'NUM':
                return ('add', var, t2[1])
            if op == '-' and t2[0] == 'NUM':
                return ('sub', var, t2[1])
            if op == '*' and t2[0] == 'NUM':
                return ('mul', var, t2[1])
            if op == '+' and t2[0] == 'ID':
                if t2[1] == 'JOY' and len(tokens) >= 6 and tokens[3][1] == '(' and tokens[4][0] == 'NUM' and tokens[5][1] == ')':
                    return ('add', var, ('joy', tokens[4][1]))
                return ('addv', var, t2[1].lower())
            if op == '-' and t2[0] == 'ID':
                if t2[1] == 'JOY' and len(tokens) >= 6 and tokens[3][1] == '(' and tokens[4][0] == 'NUM' and tokens[5][1] == ')':
                    return ('sub', var, ('joy', tokens[4][1]))
                return ('subv', var, t2[1].lower())
        return ('var', var)
    return None


def expr_to_c(expr: tuple) -> str:
    """Convert parsed expr to C expression string."""
    if not expr:
        return '0'
    t = expr[0]
    if t == 'num':
        return str(expr[1])
    if t == 'var':
        return expr[1]
    if t == 'add':
        rhs = expr_to_c(expr[2]) if isinstance(expr[2], tuple) else str(expr[2])
        return f'({expr[1]} + {rhs})'
    if t == 'sub':
        rhs = expr_to_c(expr[2]) if isinstance(expr[2], tuple) else str(expr[2])
        return f'({expr[1]} - {rhs})'
    if t == 'mul':
        return f'({expr[1]} * {expr[2]})'
    if t == 'addv':
        return f'({expr[1]} + {expr[2]})'
    if t == 'subv':
        return f'({expr[1]} - {expr[2]})'
    if t == 'joy':
        joy_funcs = ['joystick_left', 'joystick_right', 'joystick_up', 'joystick_down']
        return joy_funcs[expr[1]] + '()' if 0 <= expr[1] <= 3 else '0'
    return '0'


def parse_statement(tokens: list) -> tuple:
    """Parse a statement from tokens. Returns (cmd, args) or None."""
    if not tokens:
        return None
    first = tokens[0]
    if first[0] == 'ID':
        kw = first[1]
        rest = tokens[1:]
        if kw == 'REM':
            return ('REM', [])
        if kw == 'CLS':
            return ('CLS', [])
        if kw == 'LET':
            # LET var = expr
            if len(rest) >= 3 and rest[0][0] == 'ID' and rest[1][1] == '=':
                var = rest[0][1].lower()
                expr = parse_expr(rest[2:])
                if expr:
                    return ('LET', [var, expr])
        if kw == 'IF':
            # IF var op num THEN GOTO line (op: >=, <=, <>, >, <, =)
            then_idx = next((i for i, t in enumerate(rest) if t[0] == 'ID' and t[1] == 'THEN'), -1)
            if then_idx >= 0 and then_idx + 2 < len(rest) and rest[then_idx + 1][1] == 'GOTO' and rest[then_idx + 2][0] == 'NUM':
                expr_tok = rest[:then_idx]
                target = rest[then_idx + 2][1]
                if len(expr_tok) >= 3 and expr_tok[0][0] == 'ID' and expr_tok[-1][0] == 'NUM':
                    var = expr_tok[0][1].lower()
                    num = expr_tok[-1][1]
                    if len(expr_tok) == 3:  # var op num
                        op = expr_tok[1][1]
                    elif len(expr_tok) == 4:  # var >= num or var <= num or var <> num
                        op = expr_tok[1][1] + expr_tok[2][1]
                    else:
                        op = None
                    if op in ('>=', '<=', '<>', '>', '<', '='):
                        return ('IF', [var, op, num, target])
        if kw == 'PRINT':
            # PRINT x, y, "str"
            if len(rest) >= 5 and rest[0][0] == 'NUM' and rest[1][1] == ',' and rest[2][0] == 'NUM' and rest[3][1] == ',' and rest[4][0] == 'STR':
                return ('PRINT', [rest[0][1], rest[2][1], rest[4][1]])
            if len(rest) >= 3 and rest[0][0] == 'NUM' and rest[1][1] == ',' and rest[2][0] == 'NUM':
                # PRINT x, y (no string - maybe just position?)
                return ('PRINT', [rest[0][1], rest[2][1], ''])
        if kw == 'WAIT':
            if rest and rest[0][0] == 'NUM':
                return ('WAIT', [rest[0][1]])
        if kw == 'GOTO':
            if rest and rest[0][0] == 'NUM':
                return ('GOTO', [rest[0][1]])
        if kw == 'HIDE':
            if rest and (rest[0][0] == 'NUM' or rest[0][0] == 'ID'):
                n = rest[0][1] if rest[0][0] == 'NUM' else rest[0][1].lower()
                return ('HIDE', [n])
        if kw == 'COLOR':
            if len(rest) >= 3 and rest[1][1] == ',':
                col, val = rest[0], rest[2]
                if col[0] == 'NUM' and val[0] == 'NUM':
                    return ('COLOR', [col[1], val[1]])
                if col[0] == 'ID' and val[0] == 'NUM':
                    return ('COLOR', [col[1].lower(), val[1]])
                if col[0] == 'NUM' and val[0] == 'ID':
                    return ('COLOR', [col[1], val[1].lower()])
                if col[0] == 'ID' and val[0] == 'ID':
                    return ('COLOR', [col[1].lower(), val[1].lower()])
        if kw == 'POKE':
            if len(rest) >= 5 and rest[1][1] == ',' and rest[3][1] == ',':
                x, y, ch = rest[0], rest[2], rest[4]
                def get_val(t):
                    if t[0] == 'NUM': return ('num', t[1])
                    if t[0] == 'ID': return ('var', t[1].lower())
                    return None
                xv, yv, chv = get_val(x), get_val(y), get_val(ch)
                if xv and yv and chv:
                    return ('POKE', [xv, yv, chv])
        if kw == 'SPRITE':
            # SPRITE n, x, y, code, color - parse 5 comma-separated args
            parts = []
            i = 0
            while i < len(rest) and len(parts) < 5:
                chunk = []
                while i < len(rest):
                    if rest[i][0] == 'PUNCT' and rest[i][1] == ',':
                        i += 1
                        break
                    chunk.append(rest[i])
                    i += 1
                if chunk:
                    expr = parse_expr(chunk)
                    parts.append(expr if expr else ('num', 0))
            if len(parts) == 5:
                return ('SPRITE', parts)
        if kw == 'SCROLL':
            # SCROLL col, val (col and val can be NUM or ID/variable)
            if len(rest) >= 3 and rest[1][1] == ',':
                col = rest[0]
                val = rest[2]
                if col[0] == 'NUM' and val[0] == 'NUM':
                    return ('SCROLL', [col[1], val[1], 'lit', 'lit'])
                if col[0] == 'ID' and val[0] == 'ID':
                    return ('SCROLL', [col[1].lower(), val[1].lower(), 'var', 'var'])
                if col[0] == 'NUM' and val[0] == 'ID':
                    return ('SCROLL', [col[1], val[1].lower(), 'lit', 'var'])
                if col[0] == 'ID' and val[0] == 'NUM':
                    return ('SCROLL', [col[1].lower(), val[1], 'var', 'lit'])
        if kw == 'FOR':
            # FOR var = start TO end
            if len(rest) >= 5 and rest[0][0] == 'ID' and rest[1][1] == '=' and rest[2][0] == 'NUM' and rest[3][1] == 'TO' and rest[4][0] == 'NUM':
                var = rest[0][1].lower()
                if len(var) == 1:
                    return ('FOR', [var, rest[2][1], rest[4][1]])
        if kw == 'NEXT':
            if rest and rest[0][0] == 'ID':
                return ('NEXT', [rest[0][1].lower()])
    return None


def basic_var_to_c(name: str) -> str:
    """Convert BASIC variable name to C (A->a, A0->a0)."""
    return name.lower()


def compile_basic_to_c(source: str) -> str:
    """Compile BASIC source to C code."""
    lines = []
    for raw_line in source.strip().split('\n'):
        line = raw_line.strip()
        if not line:
            continue
        # Line number and statement
        match = re.match(r'^(\d+)\s+(.*)$', line)
        if not match:
            continue
        ln, stmt = match.groups()
        line_num = int(ln)
        stmt = stmt.strip()

        tokens = tokenize_line(stmt)
        parsed = parse_statement(tokens)
        if parsed:
            lines.append((line_num, parsed))

    # Build C output
    out = ['/* Generated from BASIC - do not edit */', '#include "runtime.h"', '']

    # Collect all variables (FOR, LET, IF, SPRITE, etc.)
    all_vars = set()
    for ln, (cmd, args) in lines:
        if cmd == 'FOR':
            all_vars.add(args[0])
        elif cmd == 'LET':
            all_vars.add(args[0])
        elif cmd == 'IF':
            all_vars.add(args[0])
        elif cmd == 'SPRITE':
            for a in args:
                if isinstance(a, tuple) and a[0] == 'var':
                    all_vars.add(a[1])
                elif isinstance(a, tuple) and len(a) >= 2:
                    if isinstance(a[1], str):
                        all_vars.add(a[1])
                    if len(a) >= 3 and isinstance(a[2], str):
                        all_vars.add(a[2])
        elif cmd == 'SCROLL':
            for a in args[:2]:
                if isinstance(a, str) and len(a) == 1 and a.isalpha():
                    all_vars.add(a)
        elif cmd == 'COLOR':
            for a in args:
                if isinstance(a, str) and len(a) == 1 and a.isalpha():
                    all_vars.add(a)
        elif cmd == 'POKE':
            for a in args:
                if isinstance(a, tuple) and a[0] == 'var':
                    all_vars.add(a[1])

    out.append('void main(void) {')
    for v in sorted(all_vars):
        out.append(f'  byte {v} = 0;')
    out.append('')
    out.append('  runtime_init();')
    out.append('')

    # Emit labels for GOTO targets, with FOR/NEXT nesting
    line_labels = {ln: f'line_{ln}' for ln, _ in lines}
    indent = 2
    for ln, (cmd, args) in lines:
        pad = '  ' * indent
        pad_inner = '  ' * (indent + 1)
        if cmd != 'NEXT':
            out.append(f'{pad}{line_labels[ln]}:')
        if cmd == 'REM':
            out.append(f'{pad_inner}/* REM */')
        elif cmd == 'CLS':
            out.append(f'{pad_inner}clrscr();')
        elif cmd == 'PRINT':
            x, y, s = args
            if s:
                s_esc = s.replace('\\', '\\\\').replace('"', '\\"')
                out.append(f'{pad_inner}putstring({x}, {y}, "{s_esc}");')
            else:
                out.append(f'{pad_inner}/* PRINT {x},{y} */')
        elif cmd == 'WAIT':
            n = args[0]
            out.append(f'{pad_inner}{{ byte _i; for (_i = 0; _i < {n}; _i++) wait_for_frame(); }}')
        elif cmd == 'GOTO':
            target = args[0]
            out.append(f'{pad_inner}goto line_{target};')
        elif cmd == 'LET':
            var, expr = args
            out.append(f'{pad_inner}{var} = {expr_to_c(expr)};')
        elif cmd == 'IF':
            var, op, num, target = args
            c_op = {'>=': '>=', '<=': '<=', '<>': '!=', '>': '>', '<': '<', '=': '=='}[op]
            out.append(f'{pad_inner}if ({var} {c_op} {num}) goto line_{target};')
        elif cmd == 'COLOR':
            col, val = args
            out.append(f'{pad_inner}set_column_attrib({col}, {val});')
        elif cmd == 'POKE':
            xv, yv, chv = args
            def to_c(a):
                return str(a[1]) if a[0] == 'num' else a[1]
            out.append(f'{pad_inner}putchar({to_c(xv)}, {to_c(yv)}, {to_c(chv)});')
        elif cmd == 'HIDE':
            n = args[0]
            out.append(f'{pad_inner}hide_sprite({n});')
        elif cmd == 'SPRITE':
            out.append(f'{pad_inner}set_sprite({expr_to_c(args[0])}, {expr_to_c(args[1])}, {expr_to_c(args[2])}, {expr_to_c(args[3])}, {expr_to_c(args[4])});')
        elif cmd == 'SCROLL':
            col, val = args[0], args[1]
            out.append(f'{pad_inner}set_scroll({col}, {val});')
        elif cmd == 'FOR':
            var, start, end = args
            out.append(f'{pad_inner}for ({var} = {start}; {var} <= {end}; {var}++) {{')
            indent += 1
        elif cmd == 'NEXT':
            indent -= 1
            pad_next = '  ' * indent
            out.append(f'{pad_next}{line_labels[ln]}: ;')
            out.append(f'{pad_next}}}')
        out.append('')

    out.append('}')

    return '\n'.join(out)


def main():
    if len(sys.argv) < 2:
        print('Usage: gbasic.py <file.bas> [-o output.c]')
        print('  Compiles BASIC to C. With -o, writes to file; else stdout.')
        sys.exit(1)

    src_path = Path(sys.argv[1])
    if not src_path.exists():
        print(f'Error: {src_path} not found', file=sys.stderr)
        sys.exit(1)

    source = src_path.read_text()
    c_code = compile_basic_to_c(source)

    if '-o' in sys.argv:
        idx = sys.argv.index('-o')
        if idx + 1 < len(sys.argv):
            out_path = Path(sys.argv[idx + 1])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(c_code)
            print(f'Compiled {src_path} -> {out_path}')
        else:
            print('Error: -o requires output path', file=sys.stderr)
            sys.exit(1)
    else:
        print(c_code)


if __name__ == '__main__':
    main()
