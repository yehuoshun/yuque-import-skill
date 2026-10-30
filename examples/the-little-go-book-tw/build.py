#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#113 The Little Go Book 繁體中文翻譯版 (kevingo/the-little-go-book @ 62ff35a)
GitBook 源仓（README + SUMMARY + 章 .md，无子目录、无图）。一章一篇，NN- 前缀免归位。
发布面 = SUMMARY 收录的 10 篇（about/introduction/getting-started/chapter1-6/conclusion）。
"""
import os, re, shutil

CLEAN = "the-little-go-book-62ff35a-clean"
OUT = "build"

ORDER = [
    ("about.md", "關於本書"),
    ("introduction.md", "簡介"),
    ("getting-started.md", "入門"),
    ("chapter1.md", "第一章 - 基本概念"),
    ("chapter2.md", "第二章 - 結構"),
    ("chapter3.md", "第三章 - Map、Array、和 Slice"),
    ("chapter4.md", "第四章 - 組織程式碼和介面"),
    ("chapter5.md", "第五章 - 花絮"),
    ("chapter6.md", "第六章 - 並行"),
    ("conclusion.md", "結論"),
]

def strip_first_h1(text):
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if ln.strip() == "":
            continue
        if ln.startswith("# "):
            return "\n".join(lines[i + 1:]).lstrip("\n")
        break
    return text

def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    # 00-说明：README 去掉首个 H1 + 「# 目錄」段（与语雀 TOC 重复）
    readme = open(os.path.join(CLEAN, "README.md"), encoding="utf-8").read()
    readme = strip_first_h1(readme)
    readme = re.sub(r"# 目錄\n(?:.*\n)*?(?=\n# |\Z)", "", readme)
    header = ("> 来源：https://github.com/kevingo/the-little-go-book @ 62ff35a ｜ "
              "《The Little Go Book》(Karl Seguin) 繁體中文翻譯版；"
              "原书 https://github.com/karlseguin/the-little-go-book；"
              "正文一章一篇（6 章 + 關於本書/簡介/入門/結論）。\n\n")
    open(os.path.join(OUT, "00-說明.md"), "w", encoding="utf-8").write(header + readme.strip() + "\n")

    nn = 1
    for fn, title in ORDER:
        text = open(os.path.join(CLEAN, fn), encoding="utf-8").read()
        body = strip_first_h1(text).strip() + "\n"
        name = f"{nn:02d}-{title}.md"
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(body)
        print(f"  {nn:02d} {fn:18} -> {name} ({len(body)} chars)")
        nn += 1
    print("done")

if __name__ == "__main__":
    main()
