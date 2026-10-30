#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#118 通用 CSS 笔记、建议与指导 (chadluo/CSS-Guidelines @ eb01cb0)
源 = 单文件 README.md（csswizardry/CSS-Guidelines 的 zh-CN 译本，仓库只有 1 个 md）。
口径：00-说明 = 前言段(首个 ## 之前) + 来源；正文按 `##` 拆篇（NN- 前缀）。
"""
import os, re, shutil

CLEAN = "CSS-Guidelines-eb01cb0-clean"
OUT = "build"

def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    text = open(os.path.join(CLEAN, "README.md"), encoding="utf-8").read()
    lines = text.split("\n")
    # 首个 ## 之前 = 前言
    head = []
    i = 0
    hm = re.compile(r"^##\s+")
    while i < len(lines) and not hm.match(lines[i]):
        head.append(lines[i])
        i += 1
    intro = "\n".join(head).strip()
    # 去掉首行 H1（= 书名）
    intro = re.sub(r"^#\s+.*\n", "", intro, count=1).strip()
    intro = intro.replace("---\n", "").strip()
    open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8").write(
        "> 来源：https://github.com/chadluo/CSS-Guidelines @ eb01cb0 ｜ "
        "《通用 CSS 笔记、建议与指导》(csswizardry/CSS-Guidelines 的 zh-CN 译本)；"
        "原文 https://github.com/csswizardry/CSS-Guidelines；正文按 `##` 拆篇。\n\n"
        + intro + "\n")
    # 按 ## 拆篇（跳过「目录」）
    rest = lines[i:]
    sections = []
    cur = None
    for ln in rest:
        m = re.match(r"^##\s+(.*)$", ln)
        if m:
            if cur:
                sections.append(cur)
            cur = [m.group(1).strip(), []]
        else:
            if cur:
                cur[1].append(ln)
    if cur:
        sections.append(cur)
    nn = 1
    for title, body in sections:
        if title.strip() == "目录":
            continue
        t = title.replace("/", "／").replace("`", "").replace("*", "＊").strip()
        b = "\n".join(body).strip() + "\n"
        name = f"{nn:02d}-{t}.md"
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(b)
        print(f"  {name} ({len(b)} chars)")
        nn += 1
    print("done")

if __name__ == "__main__":
    main()
