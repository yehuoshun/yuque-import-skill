#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fpb52 #99《Go 命令教程》(hyper-carrot/go_command_tutorial @9a76c06) → 语雀 clean 树

docsify 单章教程：0.0=标准命令详解(章导读)，0.1~0.14=14 个 go 子命令，README=前言。
catalog.md/_sidebar.md/SUMMARY.md = 三种导航（与 TOC 重复）→ 不收。
图 images/0-*.{png,jpg} 被 0.5 / 0.12 引用；文档进章目录后路径要变 ../images/。
"""
import os, re, sys, shutil

SRC = "/tmp/g99"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/g99-clean"
CHDIR = "第0章 标准命令详解"
IMGS = set()


def fix_imgs(text, prefix):
    def rep(m):
        path = m.group(2)
        base = os.path.basename(path)
        if os.path.exists(os.path.join(SRC, "images", base)):
            IMGS.add(base)
            return "![%s](%s/images/%s)" % (m.group(1) or "图", prefix, base)
        return m.group(0)
    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", rep, text)


def split_doc(raw, prefix):
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = raw.split("\n")
    title, keep = None, []
    for ln in lines:
        if title is None and ln.startswith("# "):
            title = ln[2:].strip()
            continue
        keep.append(ln)
    body = fix_imgs("\n".join(keep), prefix)
    body = re.sub(r"\n{3,}", "\n\n", body).strip("\n")
    return title, body


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "images"), exist_ok=True)
    cdir = os.path.join(OUT, CHDIR)
    os.makedirs(cdir)

    # 章导读 0.0
    t, body = split_doc(open(os.path.join(SRC, "0.0.md"), encoding="utf-8").read(), "..")
    with open(os.path.join(cdir, "00-本章导读.md"), "w", encoding="utf-8") as f:
        f.write("# %s\n\n> 第 0 章导读（标准命令详解）\n\n%s\n" % (t or "标准命令详解", body))

    # 0.1 ~ 0.14
    made = ["00-本章导读.md"]
    for i in range(1, 15):
        p = os.path.join(SRC, "0.%d.md" % i)
        if not os.path.exists(p):
            continue
        t, body = split_doc(open(p, encoding="utf-8").read(), "..")
        if not t:
            continue
        fname = "0.%02d %s.md" % (i, t.replace("/", "／"))
        with open(os.path.join(cdir, fname), "w", encoding="utf-8") as f:
            f.write("# %s\n\n%s\n" % (t, body))
        made.append(fname)

    # 00-说明（README）
    raw = open(os.path.join(SRC, "README.md"), encoding="utf-8").read().replace("\r\n", "\n")
    raw = re.sub(r"(?m)^# GO 命令教程\n+", "", raw)
    raw = fix_imgs(raw, ".")
    raw = re.sub(r"\n{3,}", "\n\n", raw).strip()
    with open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8") as f:
        f.write("# 说明\n\n## 本书信息\n\n- **书名**：Go 命令教程\n- **作者**：郝林（hyper0x）\n- **来源**：https://github.com/hyper-carrot/go_command_tutorial @ 9a76c06\n- **导入日期**：2026-10-30\n- **口径**：开源项目口径。原为《Go 并发编程实战》中关于 Go 标准命令的一章，作者单独放出为免费教程；未收 `catalog.md`/`_sidebar.md`/`SUMMARY.md`（三种导航页，与语雀目录重复）\n\n" + raw + "\n")

    n = 0
    for b in IMGS:
        shutil.copy2(os.path.join(SRC, "images", b), os.path.join(OUT, "images", b))
        n += 1
    print("docs:", len(made) + 2, "images:", n)


main()