#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fpb52 #101 《Go 语法树入门》(chai2010/go-ast-book @ 6bb3a6f) → 语雀 clean 目录。

GitBook 3.x 源仓库：SUMMARY.md 只列 章(readme.md)，无子节层级 → 一章一篇。
用法：改 SRC/DST 后 `python3 build.py`（DST 会被整个重建，本脚本请放在 DST 之外）。

口径：
- index.md      → 00-Go语言定制指南.md（剥首 H1 书名、剥「微信公众号」二维码段、内层 H1→##，保留封面图与购买链接）
- preface.md    → 01-前言.md（三篇序言合并，内层 H1 → ##）
- chN/readme.md → NN-第N章 xxx.md（章号零填充两位，剥与文件名重复的首 H1）
- appendix/*/readme.md → 18-附录A goyacc / 19-附录B ANTLR4
- chN≥12：正文因出版社版权未开源（只剩简介），剥每章重复的封面图，保留为简介文档
- 不收：ch7/x.md 孤儿片段、examples/ 源码树、book.ini/Makefile/style.css/README/cover 之外的宣传物料
- 图：`../images/x.png` → `images/x.png`（扁平根），交 yuque_rewrite_images.py 传 CDN 后连目录删净
"""
import os, re, shutil

SRC = "/home/admin/.openclaw/workspace/tmp/fpb101-src"
DST = "/home/admin/.openclaw/workspace/tmp/fpb101"

CHAPTERS = [
    (1, "Token"), (2, "基础面值"), (3, "基础表达式"), (4, "代码结构"),
    (5, "通用声明"), (6, "函数声明"), (7, "复合类型"), (8, "复合面值"),
    (9, "复合表达式"), (10, "语句块和语句"), (11, "类型检查"), (12, "语义信息"),
    (13, "SSA形式"), (14, "凹语言"), (15, "LLVM简介"), (16, "LLVM实例"),
]
APPENDIX = [("a-goyacc", "附录A goyacc"), ("b-antlr4", "附录B ANTLR4")]


def strip_lead_h1(text, title):
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        if ln.startswith("# ") and ln[2:].strip() == title:
            rest = lines[i + 1:]
            while rest and not rest[0].strip():
                rest.pop(0)
            return "\n".join(rest)
        break
    return text


def demote_h1(text):
    return "\n".join("#" + ln if ln.startswith("# ") else ln for ln in text.split("\n"))


def fix_img_refs(text):
    return text.replace("](../images/", "](images/").replace("](../cover.jpg", "](cover.jpg")


def write(path, text):
    text = text.rstrip() + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("[write] %-46s %6d B" % (os.path.basename(path), len(text.encode())))


def main():
    if os.path.isdir(DST):
        shutil.rmtree(DST)
    os.makedirs(DST)

    shutil.copytree(os.path.join(SRC, "images"), os.path.join(DST, "images"))
    shutil.copy(os.path.join(SRC, "cover.jpg"), os.path.join(DST, "cover.jpg"))

    idx = open(os.path.join(SRC, "index.md"), encoding="utf-8").read()
    idx = re.sub(r"\n*# 微信公众号\n+!\[\]\(weixin-guanggu-coder\.jpeg\)\n*", "\n\n", idx)
    if idx.lstrip().startswith("# "):
        idx = idx.lstrip().split("\n", 1)[1].lstrip("\n")
    write(os.path.join(DST, "00-Go语言定制指南.md"), fix_img_refs(demote_h1(idx)))

    pre = open(os.path.join(SRC, "preface.md"), encoding="utf-8").read()
    write(os.path.join(DST, "01-前言.md"), fix_img_refs(demote_h1(pre)))

    for n, name in CHAPTERS:
        t = open(os.path.join(SRC, "ch%d" % n, "readme.md"), encoding="utf-8").read()
        title = "第%d章 %s" % (n, name)
        t = strip_lead_h1(t, title)
        t = fix_img_refs(t)
        if n >= 12:
            t = re.sub(r"\n*\[!\[\]\(cover\.jpg\)\]\([^)]*\)\n*", "\n\n", t)
        write(os.path.join(DST, "%02d-%s.md" % (n + 1, title)), t)

    for i, (d, title) in enumerate(APPENDIX):
        t = open(os.path.join(SRC, "appendix", d, "readme.md"), encoding="utf-8").read()
        write(os.path.join(DST, "%02d-%s.md" % (18 + i, title)), fix_img_refs(strip_lead_h1(t, title)))

    print("[skip] ch7/x.md（孤儿片段）")


if __name__ == "__main__":
    main()
