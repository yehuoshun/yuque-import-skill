#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CoffeeScript 风格指南（elrrrrrrr/coffeescript-style-guide @ 7b7fd79）→ 语雀导入树。

口径：开源项目（GitHub repo）。中文译本 README-ZH.md 单文档型。
- 按 `## ` 拆文档（跟代码围栏）；文档之前的引言 → 00-说明.md
- 剔 `<a name="x"/>` 锚点行；剔 `## 目录`（语雀自带 TOC + 锚点是死链）
- 内联引用式链接定义 `[t][r]` → `[t](url)`，丢弃文末定义块
- 重名 `## 注释`（comments / annotations）→ 后者改「注解」
"""
import os
import re
import shutil

SRC = "/home/admin/.openclaw/workspace/tmp/coffeescript-style-guide-7b7fd79-clean"
OUT = "/home/admin/.openclaw/workspace/tmp/fpb084/build"
RENAME = {"注释": ["注释", "注解"]}  # 同名出现顺序 → 依次改名

src = open(os.path.join(SRC, "README-ZH.md"), encoding="utf-8").read()

# 1) 收集并内联引用式链接
REF_RE = re.compile(r"^\[([^\]]+)\]:\s*<?(\S+?)>?\s*$", re.M)
refs = {m.group(1): m.group(2) for m in REF_RE.finditer(src)}
src = REF_RE.sub("", src)
src = re.sub(r"\[([^\]]+)\]\[([^\]]+)\]",
             lambda m: "[%s](%s)" % (m.group(1), refs.get(m.group(2), m.group(2))), src)

# 2) 去锚点行
src = re.sub(r"^<a name=\"[^\"]*\"/>\s*$", "", src, flags=re.M)
src = re.sub(r"\n{3,}", "\n\n", src)

lines = src.split("\n")

# 3) 法围栏拆分 `## `
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

# 4) 落盘
if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

CH = "http://jashkenas.github.com/coffee-script/"
note = (
    "# CoffeeScript 风格指南\n\n"
    "**来源**：https://github.com/elrrrrrrr/coffeescript-style-guide @ 7b7fd79（README-ZH.md 中文译本）\n"
    "**原著**：CoffeeScript Style Guide（社区整理，灵感见「灵感」篇）\n"
    "**语言**：CoffeeScript（[coffeescript](" + CH + ")）\n\n"
    "本指南整理了一系列 CoffeeScript 编程语言的最佳实践；本项目仍在编写中，"
    "部分内容会根据实际情况修改或删除。\n\n"
    "---\n\n" + "\n".join(
        ln for ln in head if not re.match(r"^#\s+\S", ln)).strip() + "\n"
)
open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8").write(note)

seen = {}
n = 0
for title, body in sections:
    if title == "目录":      # 语雀自带 TOC，且内部锚点是死链
        continue
    name = title
    if title in RENAME:
        idx = seen.get(title, 0)
        name = RENAME[title][idx] if idx < len(RENAME[title]) else title
        seen[title] = idx + 1
    n += 1
    text = "\n".join(body).strip()
    assert text, "空小节: %s" % title
    fn = "%02d-%s.md" % (n, name.replace("/", "／"))
    open(os.path.join(OUT, fn), "w", encoding="utf-8").write(text + "\n")
    print("  %s  <=  %s" % (fn, title))

print("文档数:", n + 1)
