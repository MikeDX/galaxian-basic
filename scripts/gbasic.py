#!/usr/bin/env python3
"""
Galaxian BASIC → C compiler
Compiles BASIC source to C that links with the runtime engine.
"""

import re
import sys
from pathlib import Path


def _is_hex_digit(c: str) -> bool:
    return len(c) == 1 and (c.isdigit() or c in "AaBbCcDdEeFf")


def tokenize_line(line: str) -> list:
    """Split a BASIC line into tokens, preserving strings.

    Integer literals:
      - Decimal: digits 0-9 only (e.g. 10, 255).
      - C-style hex: 0x or 0X followed by hex digits (e.g. 0xFF, 0x10).
      - BASIC-style hex: hex digits 0-9A-F then h or H (e.g. 0FFh, 10FFH).
        Must start with a digit so keywords/ids like FOR are unchanged.
    """
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
        # C-style hex 0xNN (before plain "0" so 0xFF is not 0 + id)
        if line[i] == "0" and i + 1 < len(line) and line[i + 1] in "xX":
            i += 2
            start = i
            while i < len(line) and _is_hex_digit(line[i]):
                i += 1
            if start == i:
                raise ValueError("invalid hex literal: 0x must be followed by at least one hex digit")
            tokens.append(("NUM", int(line[start:i], 16)))
            continue
        # Decimal or BASIC-style NNH / NNh
        if line[i].isdigit():
            start = i
            while i < len(line) and _is_hex_digit(line[i]):
                i += 1
            if i < len(line) and line[i] in "Hh":
                if i == start:
                    raise ValueError("invalid hex literal: empty digit run before H")
                tokens.append(("NUM", int(line[start:i], 16)))
                i += 1
                continue
            i = start
            while i < len(line) and line[i].isdigit():
                i += 1
            tokens.append(("NUM", int(line[start:i])))
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
    """Parse simple expr: num, var, JOY(n), var+num, var-num, var*num, var+var, var-var, num+var*num, num+var. Returns (type, args)."""
    if not tokens:
        return None
    t = tokens[0]
    if t[0] == 'NUM':
        # num+var*num (e.g. 48+I*4, 192+X*16)
        if len(tokens) >= 5 and tokens[1][0] == 'PUNCT' and tokens[1][1] == '+' and tokens[2][0] == 'ID' and tokens[3][0] == 'PUNCT' and tokens[3][1] == '*' and tokens[4][0] == 'NUM':
            return ('add', t[1], ('mul', tokens[2][1].lower(), tokens[4][1]))
        # num+var (e.g. 48+I)
        if len(tokens) >= 3 and tokens[1][0] == 'PUNCT' and tokens[1][1] == '+' and tokens[2][0] == 'ID':
            return ('add', t[1], tokens[2][1].lower())
        # num/num, num MOD num, num AND num, num OR num
        if len(tokens) >= 3 and tokens[2][0] == 'NUM':
            op = tokens[1]
            if op[0] == 'PUNCT' and op[1] == '/':
                return ('div', t[1], tokens[2][1])
            if op[0] == 'PUNCT' and op[1] == '%':
                return ('mod', t[1], tokens[2][1])
            if op[0] == 'PUNCT' and op[1] == '&':
                return ('and', t[1], tokens[2][1])
            if op[0] == 'PUNCT' and op[1] == '|':
                return ('or', t[1], tokens[2][1])
        if len(tokens) >= 3 and tokens[1][0] == 'ID' and tokens[2][0] == 'NUM':
            op2 = tokens[1][1]
            if op2 == 'MOD': return ('mod', t[1], tokens[2][1])
            if op2 == 'AND': return ('and', t[1], tokens[2][1])
            if op2 == 'OR': return ('or', t[1], tokens[2][1])
        return ('num', t[1])
    if t[0] == 'ID' and t[1] == 'JOY':
        if len(tokens) >= 4 and tokens[1][1] == '(' and tokens[2][0] == 'NUM' and tokens[3][1] == ')':
            n = tokens[2][1]
            if 0 <= n <= 3:
                return ('joy', n)
    if t[0] == 'ID' and t[1] == 'INPUT':
        if len(tokens) >= 4 and tokens[1][1] == '(' and tokens[2][0] == 'NUM' and tokens[3][1] == ')':
            n = tokens[2][1]
            if 0 <= n <= 16:
                # INPUT(n) or INPUT(n)+num
                if len(tokens) >= 6 and tokens[4][0] == 'PUNCT' and tokens[4][1] == '+' and tokens[5][0] == 'NUM':
                    return ('add', ('input', n), tokens[5][1])
                return ('input', n)
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
                # var*num+var or var*num+num
                if len(tokens) >= 5 and tokens[3][0] == 'PUNCT' and tokens[3][1] == '+':
                    if tokens[4][0] == 'NUM':
                        return ('add', ('mul', var, t2[1]), tokens[4][1])
                    if tokens[4][0] == 'ID':
                        return ('add', ('mul', var, t2[1]), tokens[4][1].lower())
                return ('mul', var, t2[1])
            if op == '/' and t2[0] == 'NUM':
                return ('div', var, t2[1])
            if op == '/' and t2[0] == 'ID':
                return ('divv', var, t2[1].lower())
            if op == '%' and t2[0] == 'NUM':
                return ('mod', var, t2[1])
            if op == '%' and t2[0] == 'ID':
                return ('modv', var, t2[1].lower())
            if op == '&' and t2[0] == 'NUM':
                return ('and', var, t2[1])
            if op == '&' and t2[0] == 'ID':
                return ('andv', var, t2[1].lower())
            if op == '|' and t2[0] == 'NUM':
                return ('or', var, t2[1])
            if op == '|' and t2[0] == 'ID':
                return ('orv', var, t2[1].lower())
            if op == '+' and t2[0] == 'ID':
                if t2[1] == 'JOY' and len(tokens) >= 6 and tokens[3][1] == '(' and tokens[4][0] == 'NUM' and tokens[5][1] == ')':
                    return ('add', var, ('joy', tokens[4][1]))
                if t2[1] == 'INPUT' and len(tokens) >= 6 and tokens[3][1] == '(' and tokens[4][0] == 'NUM' and tokens[5][1] == ')':
                    return ('add', var, ('input', tokens[4][1]))
                return ('addv', var, t2[1].lower())
            if op == '-' and t2[0] == 'ID':
                if t2[1] == 'JOY' and len(tokens) >= 6 and tokens[3][1] == '(' and tokens[4][0] == 'NUM' and tokens[5][1] == ')':
                    return ('sub', var, ('joy', tokens[4][1]))
                if t2[1] == 'INPUT' and len(tokens) >= 6 and tokens[3][1] == '(' and tokens[4][0] == 'NUM' and tokens[5][1] == ')':
                    return ('sub', var, ('input', tokens[4][1]))
                return ('subv', var, t2[1].lower())
        # var MOD num, var AND num, var OR num (two-token operators)
        if len(tokens) >= 3 and tokens[1][0] == 'ID':
            op2 = tokens[1][1]
            t2 = tokens[2]
            if op2 == 'MOD' and t2[0] == 'NUM':
                return ('mod', var, t2[1])
            if op2 == 'MOD' and t2[0] == 'ID':
                return ('modv', var, t2[1].lower())
            if op2 == 'AND' and t2[0] == 'NUM':
                return ('and', var, t2[1])
            if op2 == 'AND' and t2[0] == 'ID':
                return ('andv', var, t2[1].lower())
            if op2 == 'OR' and t2[0] == 'NUM':
                return ('or', var, t2[1])
            if op2 == 'OR' and t2[0] == 'ID':
                return ('orv', var, t2[1].lower())
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
        lhs = expr_to_c(expr[1]) if isinstance(expr[1], tuple) else str(expr[1])
        rhs = expr_to_c(expr[2]) if isinstance(expr[2], tuple) else str(expr[2])
        return f'({lhs} + {rhs})'
    if t == 'sub':
        rhs = expr_to_c(expr[2]) if isinstance(expr[2], tuple) else str(expr[2])
        return f'({expr[1]} - {rhs})'
    if t == 'mul':
        return f'({expr[1]} * {expr[2]})'
    if t == 'div':
        lhs = expr_to_c(expr[1]) if isinstance(expr[1], tuple) else str(expr[1])
        rhs = expr_to_c(expr[2]) if isinstance(expr[2], tuple) else str(expr[2])
        return f'((byte)({lhs} / {rhs}))'
    if t == 'mod':
        lhs = expr_to_c(expr[1]) if isinstance(expr[1], tuple) else str(expr[1])
        rhs = expr_to_c(expr[2]) if isinstance(expr[2], tuple) else str(expr[2])
        return f'({lhs} % {rhs})'
    if t == 'and':
        lhs = expr_to_c(expr[1]) if isinstance(expr[1], tuple) else str(expr[1])
        rhs = expr_to_c(expr[2]) if isinstance(expr[2], tuple) else str(expr[2])
        return f'({lhs} & {rhs})'
    if t == 'or':
        lhs = expr_to_c(expr[1]) if isinstance(expr[1], tuple) else str(expr[1])
        rhs = expr_to_c(expr[2]) if isinstance(expr[2], tuple) else str(expr[2])
        return f'({lhs} | {rhs})'
    if t == 'divv':
        lhs = expr_to_c(expr[1]) if isinstance(expr[1], tuple) else str(expr[1])
        rhs = expr_to_c(expr[2]) if isinstance(expr[2], tuple) else str(expr[2])
        return f'((byte)({lhs} / {rhs}))'
    if t == 'modv':
        lhs = expr_to_c(expr[1]) if isinstance(expr[1], tuple) else str(expr[1])
        rhs = expr_to_c(expr[2]) if isinstance(expr[2], tuple) else str(expr[2])
        return f'({lhs} % {rhs})'
    if t == 'andv':
        lhs = expr_to_c(expr[1]) if isinstance(expr[1], tuple) else str(expr[1])
        rhs = expr_to_c(expr[2]) if isinstance(expr[2], tuple) else str(expr[2])
        return f'({lhs} & {rhs})'
    if t == 'orv':
        lhs = expr_to_c(expr[1]) if isinstance(expr[1], tuple) else str(expr[1])
        rhs = expr_to_c(expr[2]) if isinstance(expr[2], tuple) else str(expr[2])
        return f'({lhs} | {rhs})'
    if t == 'addv':
        return f'({expr[1]} + {expr[2]})'
    if t == 'subv':
        return f'({expr[1]} - {expr[2]})'
    if t == 'joy':
        joy_funcs = ['joystick_left', 'joystick_right', 'joystick_up', 'joystick_down']
        return joy_funcs[expr[1]] + '()' if 0 <= expr[1] <= 3 else '0'
    if t == 'input':
        return f'input_pressed({expr[1]})' if 0 <= expr[1] <= 16 else '0'
    return '0'


def _parse_condition(expr_tok: list) -> tuple:
    """Parse condition: INPUT(n) op num or var op num. Returns ('input', n, op, num) or ('var', var, op, num) or None."""
    if not expr_tok:
        return None
    # INPUT(n) op num
    if (len(expr_tok) >= 6 and expr_tok[0][0] == 'ID' and expr_tok[0][1] == 'INPUT'
            and expr_tok[1][1] == '(' and expr_tok[2][0] == 'NUM' and expr_tok[3][1] == ')'
            and expr_tok[4][0] == 'PUNCT' and expr_tok[5][0] == 'NUM'):
        inp_n, op, num = expr_tok[2][1], expr_tok[4][1], expr_tok[5][1]
        if 0 <= inp_n <= 16 and op in ('>=', '<=', '<>', '>', '<', '='):
            return ('input', inp_n, op, num)
    # var op num
    if len(expr_tok) >= 3 and expr_tok[0][0] == 'ID' and expr_tok[-1][0] == 'NUM':
        var = expr_tok[0][1].lower()
        num = expr_tok[-1][1]
        op = expr_tok[1][1] if len(expr_tok) == 3 else (expr_tok[1][1] + expr_tok[2][1])
        if op in ('>=', '<=', '<>', '>', '<', '='):
            return ('var', var, op, num)
    return None


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
            # IF INPUT(n) op num THEN GOTO line
            # IF expr THEN ... (block form, no GOTO)
            then_idx = next((i for i, t in enumerate(rest) if t[0] == 'ID' and t[1] == 'THEN'), -1)
            if then_idx >= 0:
                expr_tok = rest[:then_idx]
                # Block form: IF expr THEN (nothing or no GOTO after)
                has_goto = (then_idx + 2 < len(rest) and rest[then_idx + 1][1] == 'GOTO'
                            and rest[then_idx + 2][0] == 'NUM')
                cond = _parse_condition(expr_tok)
                if cond:
                    if has_goto:
                        target = rest[then_idx + 2][1]
                        if cond[0] == 'input':
                            return ('IF_INPUT', [cond[1], cond[2], cond[3], target])
                        return ('IF', [cond[1], cond[2], cond[3], target])
                    else:
                        # Block form: IF expr THEN
                        return ('IF_BLOCK', cond)
        if kw == 'ELSE':
            return ('ELSE', [])
        if kw == 'ENDIF':
            return ('ENDIF', [])
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
        if kw == 'GOSUB':
            if rest and rest[0][0] == 'NUM':
                return ('GOSUB', [rest[0][1]])
        if kw == 'RETURN':
            return ('RETURN', [])
        if kw == 'HIDE':
            if rest and (rest[0][0] == 'NUM' or rest[0][0] == 'ID'):
                n = rest[0][1] if rest[0][0] == 'NUM' else rest[0][1].lower()
                return ('HIDE', [n])
        if kw == 'COLOR':
            # COLOR col, val - args can be expr (num, var, var+num, etc.)
            parts = []
            current = []
            for t in rest:
                if t[0] == 'PUNCT' and t[1] == ',':
                    parts.append(current)
                    current = []
                else:
                    current.append(t)
            if current:
                parts.append(current)
            if len(parts) == 2:
                colv, valv = parse_expr(parts[0]), parse_expr(parts[1])
                if colv and valv:
                    return ('COLOR', [colv, valv])
        if kw == 'POKE':
            # POKE x, y, ch - args can be expr (num, var, INPUT(n), etc.)
            parts = []
            current = []
            for t in rest:
                if t[0] == 'PUNCT' and t[1] == ',':
                    parts.append(current)
                    current = []
                else:
                    current.append(t)
            if current:
                parts.append(current)
            if len(parts) == 3:
                xv, yv, chv = parse_expr(parts[0]), parse_expr(parts[1]), parse_expr(parts[2])
                if xv and yv and chv:
                    return ('POKE', [xv, yv, chv])
        if kw == 'FILL':
            # FILL x, y, w, h, ch - fill rectangle
            parts = []
            current = []
            for t in rest:
                if t[0] == 'PUNCT' and t[1] == ',':
                    parts.append(current)
                    current = []
                else:
                    current.append(t)
            if current:
                parts.append(current)
            if len(parts) == 5:
                xv, yv, wv, hv, chv = (parse_expr(p) for p in parts)
                if all((xv, yv, wv, hv, chv)):
                    return ('FILL', [xv, yv, wv, hv, chv])
        if kw == 'PUTSHAPE':
            # PUTSHAPE x, y, ofs - 2x2 tile block, args are expr
            parts = []
            current = []
            for t in rest:
                if t[0] == 'PUNCT' and t[1] == ',':
                    parts.append(current)
                    current = []
                else:
                    current.append(t)
            if current:
                parts.append(current)
            if len(parts) == 3:
                xv, yv, ofsv = parse_expr(parts[0]), parse_expr(parts[1]), parse_expr(parts[2])
                if xv and yv and ofsv:
                    return ('PUTSHAPE', [xv, yv, ofsv])
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
        if kw == 'MISSILE':
            # MISSILE n, x, y - hardware missile layer
            parts = []
            current = []
            for t in rest:
                if t[0] == 'PUNCT' and t[1] == ',':
                    parts.append(current)
                    current = []
                else:
                    current.append(t)
            if current:
                parts.append(current)
            if len(parts) == 3:
                nv, xv, yv = parse_expr(parts[0]), parse_expr(parts[1]), parse_expr(parts[2])
                if nv and xv and yv:
                    return ('MISSILE', [nv, xv, yv])
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
            def _let_expr_vars(e):
                if isinstance(e, tuple):
                    if e[0] == 'var': all_vars.add(e[1])
                    elif e[0] in ('mul', 'div', 'divv', 'mod', 'modv', 'and', 'andv', 'or', 'orv'):
                        if isinstance(e[1], str): all_vars.add(e[1])
                        if len(e) >= 3 and isinstance(e[2], str): all_vars.add(e[2])
                    elif e[0] in ('add', 'sub', 'addv', 'subv'):
                        if isinstance(e[1], str): all_vars.add(e[1])
                        elif isinstance(e[1], tuple): _let_expr_vars(e[1])
                        if len(e) >= 3:
                            if isinstance(e[2], str): all_vars.add(e[2])
                            elif isinstance(e[2], tuple): _let_expr_vars(e[2])
            _let_expr_vars(args[1])
        elif cmd == 'IF':
            all_vars.add(args[0])
        elif cmd == 'IF_BLOCK':
            if args[0] == 'var':
                all_vars.add(args[1])
        elif cmd == 'SPRITE':
            def _vars_from_expr(e):
                if isinstance(e, tuple):
                    if e[0] == 'var':
                        all_vars.add(e[1])
                    elif e[0] == 'mul' and isinstance(e[1], str):
                        all_vars.add(e[1])
                    elif e[0] in ('add', 'sub', 'addv', 'subv'):
                        if isinstance(e[1], str): all_vars.add(e[1])
                        else: _vars_from_expr(e[1])
                        if len(e) >= 3:
                            if isinstance(e[2], str): all_vars.add(e[2])
                            else: _vars_from_expr(e[2])
            for a in args:
                if isinstance(a, tuple):
                    _vars_from_expr(a)
        elif cmd == 'MISSILE':
            def _missile_vars(e):
                if isinstance(e, tuple):
                    if e[0] == 'var': all_vars.add(e[1])
                    elif e[0] == 'mul' and isinstance(e[1], str): all_vars.add(e[1])
                    elif e[0] in ('add', 'sub', 'addv', 'subv'):
                        if isinstance(e[1], str): all_vars.add(e[1])
                        elif isinstance(e[1], tuple): _missile_vars(e[1])
                        if len(e) >= 3 and isinstance(e[2], str): all_vars.add(e[2])
            for a in args:
                if isinstance(a, tuple):
                    _missile_vars(a)
        elif cmd == 'SCROLL':
            for a in args[:2]:
                if isinstance(a, str) and len(a) == 1 and a.isalpha():
                    all_vars.add(a)
        elif cmd == 'COLOR':
            def _color_vars(e):
                if isinstance(e, tuple):
                    if e[0] == 'var': all_vars.add(e[1])
                    elif e[0] == 'mul' and isinstance(e[1], str): all_vars.add(e[1])
                    elif e[0] in ('add', 'sub', 'addv', 'subv'):
                        if isinstance(e[1], str): all_vars.add(e[1])
                        elif isinstance(e[1], tuple): _color_vars(e[1])
                        if len(e) >= 3 and isinstance(e[2], str): all_vars.add(e[2])
            for a in args:
                if isinstance(a, tuple): _color_vars(a)
        elif cmd == 'POKE':
            def _poke_vars(e):
                if isinstance(e, tuple):
                    if e[0] == 'var': all_vars.add(e[1])
                    elif e[0] == 'mul' and isinstance(e[1], str): all_vars.add(e[1])
                    elif e[0] in ('add', 'sub', 'addv', 'subv'):
                        if isinstance(e[1], str): all_vars.add(e[1])
                        elif isinstance(e[1], tuple): _poke_vars(e[1])
                        if len(e) >= 3 and isinstance(e[2], str): all_vars.add(e[2])
            for a in args:
                if isinstance(a, tuple): _poke_vars(a)
        elif cmd == 'FILL':
            def _fill_vars(e):
                if isinstance(e, tuple):
                    if e[0] == 'var': all_vars.add(e[1])
                    elif e[0] == 'mul' and isinstance(e[1], str): all_vars.add(e[1])
                    elif e[0] in ('add', 'sub', 'addv', 'subv', 'div', 'mod', 'and', 'or'):
                        if isinstance(e[1], str): all_vars.add(e[1])
                        elif isinstance(e[1], tuple): _fill_vars(e[1])
                        if len(e) >= 3 and isinstance(e[2], str): all_vars.add(e[2])
            for a in args:
                if isinstance(a, tuple): _fill_vars(a)
        elif cmd == 'PUTSHAPE':
            def _putshape_vars(e):
                if isinstance(e, tuple):
                    if e[0] == 'var': all_vars.add(e[1])
                    elif e[0] == 'mul' and isinstance(e[1], str): all_vars.add(e[1])
                    elif e[0] in ('add', 'sub', 'addv', 'subv'):
                        if isinstance(e[1], str): all_vars.add(e[1])
                        elif isinstance(e[1], tuple): _putshape_vars(e[1])
                        if len(e) >= 3 and isinstance(e[2], str): all_vars.add(e[2])
            for a in args:
                if isinstance(a, tuple): _putshape_vars(a)

    # Check if we need GOSUB/RETURN (switch-based dispatch)
    has_gosub = any(cmd in ('GOSUB', 'RETURN') for _, (cmd, _) in lines)

    # Build next_line map for GOSUB mode
    line_nums = sorted({ln for ln, _ in lines})
    ln_to_next = {}
    for i, ln in enumerate(line_nums):
        ln_to_next[ln] = line_nums[i + 1] if i + 1 < len(line_nums) else 0

    out.append('void main(void) {')
    for v in sorted(all_vars):
        out.append(f'  byte {v} = 0;')
    if has_gosub:
        out.append('  byte _g[16];')
        out.append('  byte _sp = 0;')
        out.append('  byte _ln = ' + str(line_nums[0]) + ';')
    out.append('')
    out.append('  runtime_init();')
    out.append('')

    if has_gosub:
        out.append('  for (;;) {')
        out.append('    switch (_ln) {')
        out.append('      case 0: return;')
        out.append('')

    # Collect branch targets (GOTO, IF...GOTO, IF_INPUT...GOTO)
    branch_targets = set()
    for ln, (cmd, args) in lines:
        if cmd == 'GOTO':
            branch_targets.add(args[0])
        elif cmd == 'IF':
            branch_targets.add(args[3])
        elif cmd == 'IF_INPUT':
            branch_targets.add(args[3])

    line_labels = {ln: f'line_{ln}' for ln, _ in lines}
    indent = 2
    if has_gosub:
        indent += 1  # inside switch
    for_stack = []  # track FOR line numbers for GOSUB mode
    no_break_cmds = ('GOTO', 'GOSUB', 'RETURN', 'IF', 'IF_INPUT', 'IF_BLOCK', 'ELSE', 'ENDIF', 'FOR')
    for ln, (cmd, args) in lines:
        pad = '  ' * indent
        pad_inner = '  ' * (indent + 1)
        needs_label = ln in branch_targets
        if has_gosub and cmd not in ('NEXT', 'ELSE', 'ENDIF'):
            out.append(f'{pad}case {ln}:')
            pad = '  ' * (indent + 1)
            pad_inner = '  ' * (indent + 2)
        elif cmd != 'NEXT' and needs_label and not has_gosub:
            label_pad = '  ' * (indent - 1) if cmd in ('ELSE', 'ENDIF') else pad
            out.append(f'{label_pad}{line_labels[ln]}:')
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
            if n == 1:
                out.append(f'{pad_inner}wait_for_frame();')
            else:
                out.append(f'{pad_inner}{{ byte _i; for (_i = 0; _i < {n}; _i++) wait_for_frame(); }}')
        elif cmd == 'GOTO':
            target = args[0]
            if has_gosub:
                out.append(f'{pad_inner}_ln = {target}; break;')
            else:
                out.append(f'{pad_inner}goto line_{target};')
        elif cmd == 'LET':
            var, expr = args
            out.append(f'{pad_inner}{var} = {expr_to_c(expr)};')
        elif cmd == 'GOSUB':
            target = args[0]
            next_ln = ln_to_next.get(ln, 0)
            out.append(f'{pad_inner}_g[_sp++] = {next_ln}; _ln = {target}; break;')
        elif cmd == 'RETURN':
            out.append(f'{pad_inner}_ln = _g[--_sp]; break;')
        elif cmd == 'IF':
            var, op, num, target = args
            c_op = {'>=': '>=', '<=': '<=', '<>': '!=', '>': '>', '<': '<', '=': '=='}[op]
            if has_gosub:
                next_ln = ln_to_next.get(ln, 0)
                out.append(f'{pad_inner}if ({var} {c_op} {num}) _ln = {target}; else _ln = {next_ln}; break;')
            else:
                out.append(f'{pad_inner}if ({var} {c_op} {num}) goto line_{target};')
        elif cmd == 'IF_INPUT':
            inp_n, op, num, target = args
            c_op = {'>=': '>=', '<=': '<=', '<>': '!=', '>': '>', '<': '<', '=': '=='}[op]
            if has_gosub:
                next_ln = ln_to_next.get(ln, 0)
                out.append(f'{pad_inner}if (input_pressed({inp_n}) {c_op} {num}) _ln = {target}; else _ln = {next_ln}; break;')
            else:
                out.append(f'{pad_inner}if (input_pressed({inp_n}) {c_op} {num}) goto line_{target};')
        elif cmd == 'IF_BLOCK':
            cond = args  # ('input', n, op, num) or ('var', var, op, num)
            c_op = {'>=': '>=', '<=': '<=', '<>': '!=', '>': '>', '<': '<', '=': '=='}[cond[2]]
            if cond[0] == 'input':
                c_cond = f'input_pressed({cond[1]}) {c_op} {cond[3]}'
            else:
                c_cond = f'{cond[1]} {c_op} {cond[3]}'
            out.append(f'{pad_inner}if ({c_cond}) {{')
            indent += 1
        elif cmd == 'ELSE':
            indent -= 1
            pad_outer = '  ' * indent
            out.append(f'{pad_outer}}} else {{')
            indent += 1
        elif cmd == 'ENDIF':
            indent -= 1
            pad_outer = '  ' * indent
            out.append(f'{pad_outer}}}')
        elif cmd == 'COLOR':
            colv, valv = args
            out.append(f'{pad_inner}set_column_attrib({expr_to_c(colv)}, {expr_to_c(valv)});')
        elif cmd == 'POKE':
            xv, yv, chv = args
            out.append(f'{pad_inner}putchar({expr_to_c(xv)}, {expr_to_c(yv)}, {expr_to_c(chv)});')
        elif cmd == 'FILL':
            xv, yv, wv, hv, chv = args
            out.append(f'{pad_inner}fill({expr_to_c(xv)}, {expr_to_c(yv)}, {expr_to_c(wv)}, {expr_to_c(hv)}, {expr_to_c(chv)});')
        elif cmd == 'PUTSHAPE':
            xv, yv, ofsv = args
            out.append(f'{pad_inner}putshape({expr_to_c(xv)}, {expr_to_c(yv)}, {expr_to_c(ofsv)});')
        elif cmd == 'HIDE':
            n = args[0]
            out.append(f'{pad_inner}hide_sprite({n});')
        elif cmd == 'SPRITE':
            out.append(f'{pad_inner}set_sprite({expr_to_c(args[0])}, {expr_to_c(args[1])}, {expr_to_c(args[2])}, {expr_to_c(args[3])}, {expr_to_c(args[4])});')
        elif cmd == 'MISSILE':
            out.append(f'{pad_inner}set_missile({expr_to_c(args[0])}, {expr_to_c(args[1])}, {expr_to_c(args[2])});')
        elif cmd == 'SCROLL':
            col, val = args[0], args[1]
            out.append(f'{pad_inner}set_scroll({col}, {val});')
        elif cmd == 'FOR':
            var, start, end = args
            if has_gosub:
                for_stack.append(ln)
            out.append(f'{pad_inner}for ({var} = {start}; {var} <= {end}; {var}++) {{')
            indent += 1
        elif cmd == 'NEXT':
            indent -= 1
            pad_next = '  ' * indent
            if has_gosub and for_stack:
                for_ln = for_stack.pop()
                next_ln = ln_to_next.get(for_ln, 0)
                if needs_label:
                    out.append(f'{pad_next}{line_labels[ln]}: ;')
                else:
                    out.append(f'{pad_next};')
                out.append(f'{pad_next}}}')
                out.append(f'{pad_next}_ln = {next_ln}; break;')
            else:
                if needs_label:
                    out.append(f'{pad_next}{line_labels[ln]}: ;')
                else:
                    out.append(f'{pad_next};')
                out.append(f'{pad_next}}}')
        if has_gosub and cmd not in no_break_cmds and cmd != 'NEXT':
            next_ln = ln_to_next.get(ln, 0)
            out.append(f'{pad_inner}_ln = {next_ln}; break;')
        out.append('')

    if has_gosub:
        out.append('    }')
        out.append('  }')
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
