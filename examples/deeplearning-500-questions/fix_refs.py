#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""深度学习500问 源仓库图片引用修（Windows 反斜杠 / 绝对路径 / URL 编码）。

只做「让引用指向磁盘上真实存在的文件」，不碰正文其它内容。
"""
import os, re, sys, glob, urllib.parse

MD_RE = re.compile(r'(!\[[^\]]*\]\()((?:[^()]|\([^()]*\))*)(\))')
HTML_RE = re.compile(r'(<img\b[^>]*?\bsrc=)(["\'])([^"\']+)(["\'])')

root = sys.argv[1]
os.chdir(root)

_all_files = []
for dp, _, fns in os.walk('.'):
    for fn in fns:
        _all_files.append(os.path.normpath(os.path.join(dp, fn)))
_byname = {}
for p in _all_files:
    _byname.setdefault(os.path.basename(p).lower(), []).append(p)


def find_local(base, raw):
    cands = []
    for r in (raw, raw.replace('\\', '/'), urllib.parse.unquote(raw),
              urllib.parse.unquote(raw).replace('\\', '/')):
        cands.append(os.path.normpath(os.path.join(base, r)))
    for c in cands:
        if os.path.exists(c):
            return c
    # 绝对路径 / 编码名 → 按 basename 反查（限定在 md 所在目录子树内优先）
    bn = os.path.basename(urllib.parse.unquote(raw).replace('\\', '/')).lower()
    hits = _byname.get(bn, [])
    if len(hits) == 1:
        return hits[0]
    if hits:
        sub = [h for h in hits if h.startswith(base + os.sep)]
        if len(sub) == 1:
            return sub[0]
    return None


changed = []
for md in sorted(glob.glob('**/*.md', recursive=True)):
    text = open(md, encoding='utf-8', errors='replace').read()
    base = os.path.dirname(md)
    out = text
    n = 0

    def fix(raw):
        global n
        if raw.startswith(('http://', 'https://', '//', 'data:', '#')):
            return raw
        # 图片 name 带空格：脚本 split(None,1) 会误判 → 保留原样，交给后置脚本
        loc = find_local(base, raw)
        if loc is None:
            return raw
        rel = os.path.relpath(loc, base).replace(os.sep, '/')
        if rel != raw:
            n += 1
        return rel

    def sub_md(m):
        raw = m.group(2)
        bits = raw.split(None, 1)
        if ' ' in raw and find_local(base, raw) is not None:
            return m.group(0)  # 合法空格名，交给后置脚本
        return m.group(1) + fix(bits[0]) + ((' ' + bits[1]) if len(bits) > 1 else '') + m.group(3)

    out = MD_RE.sub(sub_md, out)
    out = HTML_RE.sub(lambda m: m.group(1) + m.group(2) + fix(m.group(3)) + m.group(4), out)
    if out != text:
        open(md, 'w', encoding='utf-8').write(out)
        changed.append((md, n))

for md, n in changed:
    print(f"  fixed {n:3d}  {md}")
print("total md changed:", len(changed))