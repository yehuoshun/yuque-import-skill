#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NCCL (limingth/NCCL @2fae5f0) 新概念 C 语言 -> 语雀导入树构建
口径：
  - 00-前言.md           <- README.md（全书大纲/96 课规划）
  - Unit 1/2 TITLE       <- 00-导读.md（原 Unit-N/README.md，去掉重复标题、相对 .md 链接转纯文本）+ 24 节课
  - Unit 3 TITLE         <- 00-导读.md（原 Unit-3/README.md，剔 50-72 空条目）+ Lesson 49 + Lesson 49 代码/ + 90-附加-语法分析树
  - Unit 4 不建（仓库内只有空 README，原书未写）
  - images/ 拷到导入根，保留 ../images/ 相对引用（Unit-N/ 下正好能解析）
  - 跳过：enrollment.md（招生广告）、slides/（pandoc 课件，Lesson-1..14 的 PDF 派生品）、Unit-4、二进制(a.out/demo/*.o)
  - CRLF -> LF
"""
import os, re, shutil, sys, unicodedata

SRC = "/home/admin/.openclaw/workspace/tmp/nccl-src"
OUT = "/home/admin/.openclaw/workspace/tmp/nccl-2fae5f0-lib"


def norm(text: str) -> str:
    if text.startswith("\ufeff"):
        text = text[1:]
    return text.replace("\r\n", "\n").replace("\r", "\n")


def strip_setext_title(text: str) -> str:
    """去掉开头的 '标题\\n====' setext H1 块"""
    lines = text.split("\n")
    out, i = [], 0
    while i + 1 < len(lines) and (not lines[i].strip() or lines[i].strip().startswith("#")):
        i += 1
    if i + 1 < len(lines) and re.fullmatch(r"={3,}|\-{3,}", lines[i + 1].strip()):
        i += 2
    out = "\n".join(lines[i:])
    return out.lstrip("\n")


def delink_md(text: str) -> str:
    """站内相对 .md 链接 -> 纯文本；保留外链"""
    def f(m):
        label, url = m.group(1), m.group(2)
        if re.search(r"\.md(#.*)?$", url) and not url.startswith("http"):
            return label
        return m.group(0)
    return re.sub(r"\[([^\]]*)\]\(([^)]*)\)", f, text)


def sanitize(name: str) -> str:
    name = name.replace("/", "／").replace("\\", "＼").replace("*", "＊")
    name = name.replace(":", "：").replace("|", "｜")
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name


def lesson_files(unit_dir: str):
    d = os.path.join(SRC, unit_dir)
    items = []
    for fn in os.listdir(d):
        m = re.fullmatch(r"Lesson-(\d+)\.md", fn)
        if m:
            items.append((int(m.group(1)), fn))
    return sorted(items)


def build_unit(unit_dir, out_dir, base_prefix=""):
    os.makedirs(out_dir, exist_ok=True)
    for num, fn in lesson_files(unit_dir):
        raw = norm(open(os.path.join(SRC, unit_dir, fn), encoding="utf-8", errors="replace").read())
        lines = raw.split("\n")
        # 找第一处 H1/H2 'Lesson N ...'
        idx = None
        for i, ln in enumerate(lines):
            if re.match(r"^#{1,3}\s*\**\s*Lesson\s*%d\b" % num, ln.strip()):
                idx = i
                break
        if idx is None:
            title = "Lesson %d" % num
            body = raw
        else:
            title = lines[idx].strip().lstrip("#").strip()
            title = re.sub(r"^Lesson\s*%d\s*[-–—]?\s*" % num, "", title).strip()
            body = "\n".join(lines[idx + 1:])
        title = title.replace("**", "")
        fn_out = "%s%02d-%s.md" % (base_prefix, num, sanitize(title))
        open(os.path.join(out_dir, fn_out), "w", encoding="utf-8").write(delink_md(body).strip() + "\n")
        print("  DOC %s" % fn_out)


def write_doc(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text.strip() + "\n")
    print("  DOC %s" % os.path.relpath(path, OUT))


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    # 00-前言
    readme = norm(open(os.path.join(SRC, "README.md"), encoding="utf-8").read())
    readme = strip_setext_title(readme)
    write_doc(os.path.join(OUT, "00-前言.md"), readme)

    # Unit 1
    u1 = os.path.join(OUT, "Unit-1")
    os.makedirs(u1)
    u1r = strip_setext_title(norm(open(os.path.join(SRC, "Unit-1/README.md"), encoding="utf-8").read()))
    write_doc(os.path.join(u1, "00-Unit-1 导读.md"), delink_md(u1r))
    build_unit("Unit-1", u1)

    # Unit 2
    u2 = os.path.join(OUT, "Unit-2")
    os.makedirs(u2)
    u2r = strip_setext_title(norm(open(os.path.join(SRC, "Unit-2/README.md"), encoding="utf-8").read()))
    write_doc(os.path.join(u2, "00-Unit-2 导读.md"), delink_md(u2r))
    build_unit("Unit-2", u2)

    # Unit 3
    u3 = os.path.join(OUT, "Unit-3")
    os.makedirs(u3)
    u3r = norm(open(os.path.join(SRC, "Unit-3/README.md"), encoding="utf-8").read())
    u3r = strip_setext_title(u3r)
    u3r = re.sub(r"^##\s*Lesson\s*(5[0-9]|6[0-9]|7[0-2])\s*$\n?", "", u3r, flags=re.M)
    u3r = u3r.strip() + "\n\n> ⚠️ 原书 Unit 3 规划 Lesson 49–72，仓库中仅有 Lesson 49 一篇；Unit 4（Lesson 73–96，C 编译器）尚未编写。\n"
    write_doc(os.path.join(u3, "00-Unit-3 导读.md"), delink_md(u3r))
    build_unit("Unit-3", u3)

    # Lesson 49 代码
    code_out = os.path.join(u3, "49-代码")
    os.makedirs(code_out)
    for fn in ("readfile.c", "state.c", "test.c", "Makefile"):
        shutil.copy2(os.path.join(SRC, "Unit-3/Lesson-49", fn), os.path.join(code_out, fn))
        print("  DOC 49-代码/%s" % fn)

    # 附加：语法分析树（原编号 Lesson 37，放在 Unit-3 目录下）
    pt = norm(open(os.path.join(SRC, "Unit-3/parser-tree.md"), encoding="utf-8").read())
    pt = re.sub(r"^#{1,3}\s*Lesson\s*37\s*[-–—]?\s*", "", pt.strip(), flags=re.M)
    write_doc(os.path.join(u3, "90-附加-语法分析树（原编号 Lesson 37）.md"), delink_md(pt))

    # 图片
    img_out = os.path.join(OUT, "images")
    os.makedirs(img_out)
    n_img = 0
    for fn in sorted(os.listdir(os.path.join(SRC, "images"))):
        if fn.startswith("."):
            continue
        shutil.copy2(os.path.join(SRC, "images", fn), os.path.join(img_out, fn))
        n_img += 1
    print("  IMG %d -> images/" % n_img)


if __name__ == "__main__":
    main()