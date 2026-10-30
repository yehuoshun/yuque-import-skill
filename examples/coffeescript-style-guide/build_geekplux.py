#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CoffeeScript 编码风格指南（geekplux/coffeescript-style-guide @ b87e527）→ 语雀导入树。

口径：开源项目（GitHub repo）。README.md 即中文正本，单文档型。
- 按 `## ` 拆文档（必须跟代码围栏，坑 82：围栏内 `# 好`/`# 差` 是注释行）
- 文档之前的引言 → 00-说明.md；剔首个 H1（标题已由文件名承载）
- 剔 codesponsor.io 赞助横幅（`<a target='_blank'>…<img/></a>`）
- 剔 `<a name="x"/>` 锚点行；剔 `## 目录`（语雀自带 TOC + 锚点是死链）
- 内联引用式链接 `[t][r]` → `[t](url)`，丢弃文末定义块
"""
import os
import re
import shutil

SRC = "/home/admin/.openclaw/workspace/tmp/fpb085-src/README.md"
OUT = "/home/admin/.openclaw/workspace/tmp/fpb085/build"

src = open(SRC, encoding="utf-8").read()

# 1) 收集并内联引用式链接（文末定义块拆篇后成死链）
REF_RE = re.compile(r"^\[([^\]]+)\]:\s*<?(\S+?)>?\s*$", re.M)
refs = {m.group(1): m.group(2) for m in REF_RE.finditer(src)}
src = REF_RE.sub("", src)
src = re.sub(r"\[([^\]]+)\]\[([^\]]+)\]",
             lambda m: "[%s](%s)" % (m.group(1), refs.get(m.group(2), m.group(2))), src)

# 2) 剔赞助横幅 + 锚点行
src = re.sub(r"^<a[^>]*codesponsor\.io[^>]*>.*?</a>\s*$", "", src, flags=re.M)
src = re.sub(r"^<a name=\"[^\"]*\"/>\s*$", "", src, flags=re.M)
src = re.sub(r"\n{3,}", "\n\n", src)

lines = src.split("\n")

# 3) 跟围栏按 `## ` 拆分
head, sections, cur_title, cur = [], [], None, []
fence = False
for ln in lines:
    s = ln.lstrip()
    if s.startswith("```") or s.startswith("~~~"):
        fence = not fence
        cur.append(ln)
        continue
    m = None if fence else re.match(r"^##\s+(.*\S)\s*$", ln)
    if m:
        if cur_title is None:
            head = cur
        else:
            sections.append((cur_title, cur))
        cur_title = m.group(1).strip()
        cur = []
    else:
        cur.append(ln)
if cur_title is not None:
    sections.append((cur_title, cur))
assert not fence, "围栏未闭合"

# 4) 落盘
if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

CH = "http://jashkenas.github.com/coffee-script/"
head_txt = "\n".join(ln for ln in head if not re.match(r"^#\s+\S", ln)).strip()
note = (
    "# CoffeeScript 编码风格指南\n\n"
    "**来源**：https://github.com/geekplux/coffeescript-style-guide @ b87e527（README.md 中文正本）\n"
    "**原著**：CoffeeScript Style Guide（社区整理，灵感见「灵感」篇）\n"
    "**语言**：CoffeeScript（[coffeescript](" + CH + ")）\n\n"
    "---\n\n" + head_txt + "\n"
)
open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8").write(note)

seen = set()
n = 0
for title, body in sections:
    if title == "目录":      # 语雀自带 TOC，且内部锚点是死链
        continue
    assert title not in seen, "重复小节名: %s" % title
    seen.add(title)
    n += 1
    text = "\n".join(body).strip()
    assert text, "空小节: %s" % title
    fn = "%02d-%s.md" % (n, title.replace("/", "／"))
    open(os.path.join(OUT, fn), "w", encoding="utf-8").write(text + "\n")
    print("  %s  <=  %s" % (fn, title))

print("目录数: 0  文档数:", n + 1)
