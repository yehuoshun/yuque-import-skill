#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""极简 Liquid 引擎（覆盖 Bootstrap docs 用到的子集）。"""
import os, re, yaml

TOKEN = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})", re.S)
BLOCK = {"for", "if", "unless", "capture", "highlight", "comment"}
ENDBLOCK = {"endfor", "endif", "endunless", "endcapture", "endhighlight", "endcomment",
            "else", "elsif"}


def lex(text):
    return [t for t in TOKEN.split(text)]


def parse(tokens, i=0):
    nodes = []
    while i < len(tokens):
        t = tokens[i]
        if t.startswith("{%"):
            raw = t[2:-2].strip()
            kw = raw.split()[0] if raw.split() else ""
            if kw in ENDBLOCK:
                return nodes, i + 1, raw
            if kw == "comment":
                depth = 1; i += 1
                while i < len(tokens) and depth > 0:
                    tt = tokens[i]
                    if tt.startswith("{%"):
                        k = tt[2:-2].strip().split()[0]
                        if k == "comment": depth += 1
                        elif k == "endcomment": depth -= 1
                    i += 1
                continue
            if kw in BLOCK:
                body, i, endraw = parse(tokens, i + 1)
                node = {"kind": kw, "raw": raw, "body": body}
                if kw in ("if", "unless"):
                    branches = [("__first__", body)]
                    cur = endraw
                    while cur and cur.split()[0] in ("elsif", "else"):
                        b2, i, cur2 = parse(tokens, i)
                        branches.append((cur, b2)); cur = cur2
                    node["branches"] = branches
                nodes.append(node); continue
            nodes.append({"kind": "tag", "raw": raw}); i += 1; continue
        if t.startswith("{{"):
            nodes.append({"kind": "var", "raw": t[2:-2].strip()}); i += 1; continue
        if t:
            nodes.append({"kind": "text", "text": t})
        i += 1
    return nodes, i, None


# ---------- expression ----------
def split_filters(expr):
    parts, buf, depth, q = [], "", 0, None
    for ch in expr:
        if q:
            buf += ch
            if ch == q: q = None
            continue
        if ch in "\"'":
            q = ch; buf += ch; continue
        if ch in "([": depth += 1
        if ch in ")]": depth -= 1
        if ch == "|" and depth == 0:
            parts.append(buf); buf = ""
        else:
            buf += ch
    parts.append(buf)
    return [p.strip() for p in parts]


def lookup(path, ctx):
    path = path.strip()
    if not path:
        return ""
    if (path[0] == "'" and path[-1] == "'") or (path[0] == '"' and path[-1] == '"'):
        return path[1:-1]
    if re.fullmatch(r"-?\d+", path):
        return int(path)
    if path == "true": return True
    if path == "false": return False
    if path in ("nil", "null", ""): return None
    cur = ctx
    for seg in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(seg)
        else:
            return None
    return cur


def apply_filter(val, f):
    m = re.match(r"(\w+)\s*(?::\s*(.*))?$", f.strip())
    if not m:
        return val
    name = m.group(1); arg = m.group(2)
    args = []
    if arg is not None:
        args = [a.strip().strip("'\"") for a in split_args(arg)]
    if name == "default":
        return val if val not in (None, "", False) else (args[0] if args else "")
    if name == "capitalize": return str(val).capitalize()
    if name == "upcase": return str(val).upper()
    if name == "downcase": return str(val).lower()
    if name == "strip": return str(val).strip()
    if name == "size": return len(val) if hasattr(val, "__len__") else 0
    if name == "replace" and len(args) >= 2: return str(val).replace(args[0], args[1])
    if name == "replace_first" and len(args) >= 2: return str(val).replace(args[0], args[1], 1)
    if name == "markdownify": return val
    if name == "join": return (args[0] if args else "").join(str(x) for x in val)
    if name == "split": return str(val).split(args[0] if args else "")
    if name == "first": return val[0] if val else ""
    if name == "last": return val[-1] if val else ""
    if name == "append": return str(val) + (args[0] if args else "")
    if name == "prepend": return (args[0] if args else "") + str(val)
    return val


def split_args(s):
    out, buf, q = [], "", None
    for ch in s:
        if q:
            buf += ch
            if ch == q: q = None
            continue
        if ch in "\"'": q = ch; buf += ch; continue
        if ch == ",": out.append(buf); buf = ""
        else: buf += ch
    out.append(buf)
    return out


def resolve(expr, ctx):
    parts = split_filters(expr)
    val = lookup(parts[0], ctx)
    for f in parts[1:]:
        val = apply_filter(val, f)
    return val


def eval_cond(cond, ctx):
    cond = cond.strip()
    # or / and (left-assoc, low precedence for or)
    for op in (" or ",):
        if op in cond:
            return any(eval_cond(c, ctx) for c in cond.split(op))
    for op in (" and ",):
        if op in cond:
            return all(eval_cond(c, ctx) for c in cond.split(op))
    m = re.match(r"^(.*?)\s*(==|!=|contains|>|<)\s*(.*)$", cond)
    if m:
        a = resolve(m.group(1), ctx); b = resolve(m.group(3), ctx); o = m.group(2)
        if o == "==": return a == b
        if o == "!=": return a != b
        if o == "contains": return (b in a) if a is not None else False
        if o == ">": return (a or 0) > (b or 0)
        if o == "<": return (a or 0) < (b or 0)
    v = resolve(cond, ctx)
    return bool(v)
