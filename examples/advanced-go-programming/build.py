#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fpb52 #103 《Go语言高级编程》(chai2010/advanced-go-programming-book @ 4447d09) → 语雀 clean 目录。

GitBook 3.x 源仓（SUMMARY.md + chN-xxx/chN-MM-title.md）。
- index.md → 00-Go语言高级编程.md（保留封面图）；preface.md → 01-前言.md；errata/README.md → 02-勘误（第一版第一次印刷）.md
- chN-*/readme.md → `第N章 <章名>/00-本章导读.md`；章内节 → `NN-<SUMMARY 标题>.md`（零填充按 SUMMARY 序）
- appendix/readme.md → `附录/00-本章导读.md`；附录A/B/C → `NN-附录X：…md`
- 剥每篇首个 H1；标题里 `/` → `／`、`:` → `：`
- 图片 `../images/x.png`：按章收集被引用的图 → 拷进 `<章目录>/images/` 并把引用改 `images/x.png`；根级封面单独拷
- 不收：README.md（仓库首页/二维码）、preface-pdf.md、examples/ 源码树、book.ini/Makefile/docs/、其它宣传图
"""
import os, re, shutil, collections

SRC = "/home/admin/.openclaw/workspace/tmp/fpb103-src"
DST = "/home/admin/.openclaw/workspace/tmp/fpb103"

ROOT_RE = re.compile(r"^\[(?P<t>.+?)\]\((?P<p>.+?)\)\s*$")
CH_RE = re.compile(r"^-\s+\[(?P<t>.+?)\]\((?P<p>.+?)\)\s*$")
SEC_RE = re.compile(r"^\s+-\s+\[(?P<t>.+?)\]\((?P<p>.+?)\)\s*$")
IMG_RE = re.compile(r"(!\[[^\]]*\]\()(\.\./images/)([^)\s]+?)((?:\s+\"[^\"]*\")?\))")
IMG_HTML_RE = re.compile(r'(<img\b[^>]*?\bsrc=)(["\'])(\.\./images/)([^"\']+)(\4)')


def sane(t):
    return t.replace("/", "／").replace(":", "：").rstrip("： ").strip()


def body(path):
    t = open(path, encoding="utf-8").read()
    lines = t.split("\n")
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        if ln.startswith("# "):
            lines = lines[i + 1:]
        break
    return "\n".join(lines).strip() + "\n"


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")


def main():
    if os.path.isdir(DST):
        shutil.rmtree(DST)
    os.makedirs(DST)
    used_imgs = collections.defaultdict(set)  # dir -> set(fname)

    def emit(dst_path, src_path, rel_dir):
        t = body(src_path)
        for m in IMG_RE.finditer(t):
            used_imgs[rel_dir].add(m.group(3))
        t = IMG_RE.sub(lambda m: m.group(1) + "images/" + m.group(3) + m.group(4), t)
        write(dst_path, t)

    # 根级文档
    emit(os.path.join(DST, "00-Go语言高级编程.md"), os.path.join(SRC, "index.md"), "")
    emit(os.path.join(DST, "01-前言.md"), os.path.join(SRC, "preface.md"), "")
    emit(os.path.join(DST, "02-勘误（第一版第一次印刷）.md"), os.path.join(SRC, "errata", "README.md"), "")

    chapter_dir = None
    rel_dir = None
    n = 0
    for ln in open(os.path.join(SRC, "SUMMARY.md"), encoding="utf-8").read().split("\n"):
        if not ln.strip():
            continue
        m = ROOT_RE.match(ln)
        if m:
            continue
        m = CH_RE.match(ln)
        if m:
            title = m.group("t")
            if m.group("p").startswith("appendix/"):
                name = "附录"
            else:
                num = re.match(r"ch(\d+)-", m.group("p")).group(1)
                name = "第%s章 %s" % (num, re.sub(r"^第.+?章\s*", "", title))
            rel_dir = name
            chapter_dir = os.path.join(DST, name)
            os.makedirs(chapter_dir, exist_ok=True)
            n = 0
            emit(os.path.join(chapter_dir, "00-本章导读.md"),
                 os.path.join(SRC, m.group("p")), rel_dir)
            continue
        m = SEC_RE.match(ln)
        if m and chapter_dir:
            n += 1
            emit(os.path.join(chapter_dir, sane("%02d-%s.md" % (n, m.group("t")))),
                 os.path.join(SRC, m.group("p")), rel_dir)

    # 每章图片目录
    for d, files in used_imgs.items():
        target = os.path.join(DST, d, "images") if d else os.path.join(DST, "images")
        os.makedirs(target, exist_ok=True)
        for fn in files:
            src = os.path.join(SRC, "images", fn)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(target, fn))
            else:
                print("[miss-img] %s" % fn)

    # 根级本地图（封面）
    for fn in ("cover-20190714.jpg",):
        src = os.path.join(SRC, fn)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(DST, fn))

    print("[done]")


if __name__ == "__main__":
    main()