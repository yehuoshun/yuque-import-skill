#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Elixir 元编程与 DSL 中文翻译（Ljzn/MetaProgrammingInElixirChinese）→ 语雀导入树。

口径：开源项目（GitHub repo，老 GitBook 书）。扁平 3 章 `N_*.markdown`，无 SUMMARY，按前缀数字定序。
- 标题取每章首个 H1（中文）
- 正文里其余标题整体降一级（`#`→`##`）—— **必须跟代码围栏**（围栏内 `# => 1` / `# 注释` 是注释，不能当标题）
- 顶部「本章内容」缩进列表按列表块最小缩进 dedent（含转义 `\\- ` 列表项；保留真实嵌套）
"""
import os, re, glob, shutil

SRC = "/home/admin/.openclaw/workspace/tmp/fpb090-src"
OUT = "/home/admin/.openclaw/workspace/tmp/fpb090/build"

LIST_RE = re.compile(r"^ +\\?([-*+]|\d+[.)])\s")

def dedent_lists(body):
    lines = body.split("\n")
    out, fence, i = [], False, 0
    while i < len(lines):
        ln = lines[i]
        if ln.lstrip().startswith("```"):
            fence = not fence
            out.append(ln); i += 1; continue
        if not fence and LIST_RE.match(ln):
            block = []
            while i < len(lines) and (LIST_RE.match(lines[i]) or lines[i].strip() == ""):
                block.append(lines[i]); i += 1
            indents = [len(m.group(0)) - len(m.group(0).lstrip()) for m in (re.match(r"^( +)", b) for b in block) if m]
            m0 = min(indents) if indents else 0
            for b in block:
                out.append(b[m0:] if b.strip() else b)
            continue
        out.append(ln); i += 1
    return "\n".join(out)

def shift_headings(body):
    out, fence = [], False
    for ln in body.split("\n"):
        if ln.lstrip().startswith("```"):
            fence = not fence
            out.append(ln); continue
        if not fence:
            m = re.match(r"^(#{1,6})\s*(\S.*)$", ln)
            if m:
                out.append("#" * (len(m.group(1)) + 1) + " " + m.group(2).strip())
                continue
        out.append(ln)
    return "\n".join(out)

if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

note = (
    "# Elixir 元编程与 DSL 中文翻译\n\n"
    "**来源**：https://github.com/Ljzn/MetaProgrammingInElixirChinese @ 5e24e62（Elixir 官网「Metaprogramming in Elixir」中译，GitBook 书）\n"
    "**原著**：Metaprogramming in Elixir（elixir-lang.org）\n"
    "**说明**：3 章按序落为 3 篇；文档标题取各章 H1（中文），正文标题整体降一级（跟代码围栏）。\n"
    "**导入日期**：2026-10-30\n"
)
open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8").write(note)

files = sorted(glob.glob(os.path.join(SRC, "*.markdown")), key=lambda p: int(os.path.basename(p).split("_")[0]))
n = 0
for p in files:
    raw = open(p, encoding="utf-8").read().replace("\r\n", "\n")
    m = re.match(r"^\s*#\s*(\S[^\n]*?)\s*\n", raw)
    if m:
        title, body = m.group(1).strip(), raw[m.end():]
    else:
        title, body = os.path.basename(p).split("_", 1)[1].replace(".markdown", ""), raw
    body = shift_headings(dedent_lists(body))
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    n += 1
    fn = "%02d-%s.md" % (n, title.replace("/", "／"))
    open(os.path.join(OUT, fn), "w", encoding="utf-8").write("# %s\n\n" % title + body + "\n")
    print("[DOC] %s  <= %s" % (fn, os.path.basename(p)))

print("文档数:", n + 1)
