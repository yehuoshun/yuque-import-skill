#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Elixir Getting Started 中文翻译（Ljzn/ElixrGettingStartedChinese）→ 语雀导入树。

口径：开源项目（GitHub repo，老 GitBook 书）。扁平 22 章 `N_*.markdown`，SUMMARY.md 定序。
- 标题取每章首个 H1（中文标题，SUMMARY 是英文，以 H1 为准）
- 正文里其余标题整体降一级（`#`→`##`），首 H1 换成文档标题
- 顶部「本章内容」缩进列表按各列表块最小缩进 dedent（保留真实嵌套）
"""
import os, re, glob, shutil

SRC = "/home/admin/.openclaw/workspace/tmp/fpb089-src"
OUT = "/home/admin/.openclaw/workspace/tmp/fpb089/build"

def dedent_lists(body):
    lines = body.split("\n")
    out, fence, i = [], False, 0
    while i < len(lines):
        ln = lines[i]
        if ln.lstrip().startswith("```"):
            fence = not fence
            out.append(ln); i += 1; continue
        if not fence and re.match(r"^ {1,}([-*+]|\d+[.)])\s", ln):
            block = []
            while i < len(lines) and (re.match(r"^ {1,}([-*+]|\d+[.)])\s", lines[i]) or lines[i].strip() == ""):
                block.append(lines[i]); i += 1
            indents = [len(m.group(1)) for m in (re.match(r"^( +)", b) for b in block) if m]
            m0 = min(indents) if indents else 0
            for b in block:
                out.append(b[m0:] if b.strip() else b)
            continue
        out.append(ln); i += 1
    return "\n".join(out)

def shift_headings(body):
    def rep(m):
        return "#" * (len(m.group(1)) + 1) + " " + m.group(2).strip()
    return re.sub(r"(?m)^(#{1,6})\s*(\S.*)$", rep, body)

if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

note = (
    "# Elixir Getting Started 中文翻译\n\n"
    "**来源**：https://github.com/Ljzn/ElixrGettingStartedChinese @ 1f517ec（Elixir 官网入门教程中译，GitBook 书；作者声明可随意使用）\n"
    "**原著**：Elixir Getting Started（elixir-lang.org）\n"
    "**说明**：扁平 22 章按 SUMMARY.md 顺序落为 22 篇；文档标题取各章 H1（中文），正文标题整体降一级。\n"
    "**导入日期**：2026-10-30\n"
)
open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8").write(note)

files = sorted(glob.glob(os.path.join(SRC, "*.markdown")), key=lambda p: int(os.path.basename(p).split("_")[0]))
n = 0
for p in files:
    raw = open(p, encoding="utf-8").read().replace("\r\n", "\n")
    # 首个 H1 = 标题
    m = re.match(r"^\s*#\s*(\S[^\n]*?)\s*\n", raw)
    if m:
        title = m.group(1).strip()
        body = raw[m.end():]
    else:
        title = os.path.basename(p).split("_", 1)[1].replace(".markdown", "")
        body = raw
    body = shift_headings(dedent_lists(body))
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    n += 1
    fn = "%02d-%s.md" % (n, title.replace("/", "／"))
    open(os.path.join(OUT, fn), "w", encoding="utf-8").write("# %s\n\n" % title + body + "\n")
    print("[DOC] %s  <= %s" % (fn, os.path.basename(p)))

print("文档数:", n + 1)
