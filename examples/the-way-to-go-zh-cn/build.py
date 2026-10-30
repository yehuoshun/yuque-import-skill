#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fpb52 #100《Go 入门指南》(Unknwon/the-way-to-go_ZH_CN @7a54d34) → 语雀 clean 树

《The Way To Go》中文译本。eBook/ 下 211 个 md：NN.M.md（M>=1 节，M=0 章导读）+ preface + directory(导航，不收)。
结构取自 eBook/directory.md（完整覆盖 21 章 / 190 节 / 4 个部分 / 附录）。
目录层级：部分 → 第NN章 → 文档；节文件名零填充成 `01.01 标题.md`（否则 1.10 会排到 1.2 前）。
"""
import os, re, sys, shutil, glob

SRC = "/tmp/g100"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/g100-clean"
IMGS = set()


def load_directory():
    txt = open(os.path.join(SRC, "eBook", "directory.md"), encoding="utf-8").read()
    part = None
    chapters = {}   # n -> (part, title, intro_file)
    sections = {}   # basename -> (ch, sec, title)
    for ln in txt.split("\n"):
        s = ln.strip()
        if ln.startswith("## "):
            part = ln[3:].strip()
            continue
        m = re.match(r"^- 第\s*(\d+)\s*章[：:]\s*(?:\[([^\]]+)\]\(([^)]+)\)|(.+))", s)
        if m:
            n = int(m.group(1))
            chapters[n] = (part, (m.group(2) or m.group(4) or "").strip(), m.group(3))
            continue
        m = re.match(r"^- (\d+)\.(\d+) \[([^\]]+)\]\(([^)]+)\)", s)
        if m:
            sections[m.group(4)] = (int(m.group(1)), int(m.group(2)), m.group(3).strip())
    return chapters, sections


def fix_imgs(text, prefix):
    def rep(m):
        alt, path = m.group(1), m.group(2)
        base = os.path.basename(path.split("?")[0])
        if os.path.exists(os.path.join(SRC, "eBook", "images", base)):
            IMGS.add(base)
            return "![%s](%s/images/%s)" % (alt or "图", prefix, base)
        return "*（原书插图缺失：%s）*" % base

    def rep_html(m):
        path = m.group(1)
        base = os.path.basename(path.split("?")[0])
        if os.path.exists(os.path.join(SRC, "eBook", "images", base)):
            IMGS.add(base)
            return "![图](%s/images/%s)" % (prefix, base)
        return "*（原书插图缺失：%s）*" % base

    text = re.sub(r'<img[^>]*src="([^"]+)"[^>]*/?>', rep_html, text)
    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", rep, text)


def split_doc(raw, prefix):
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = raw.split("\n")
    title, keep = None, []
    for ln in lines:
        t = ln.strip()
        if title is None and re.match(r"^#{1,2} \d+\.\d+", t):
            title = t.lstrip("# ").strip()
            continue
        if title is None and t.startswith("# "):
            title = t[2:].strip()
            continue
        keep.append(ln)
    body = fix_imgs("\n".join(keep), prefix)
    body = re.sub(r"\n{3,}", "\n\n", body).strip("\n")
    return title, body


def main():
    chapters, sections = load_directory()
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "images"), exist_ok=True)

    # 前言
    t, body = split_doc(open(os.path.join(SRC, "eBook", "preface.md"), encoding="utf-8").read(), "..")
    with open(os.path.join(OUT, "00-前言.md"), "w", encoding="utf-8") as f:
        f.write("# 前言\n\n%s\n" % body)

    # 章节
    for n in sorted(chapters):
        part, ctitle, intro = chapters[n]
        pdir = os.path.join(OUT, re.sub(r"[：:]", " ", part))
        cdir = os.path.join(pdir, "第%02d章 %s" % (n, ctitle.replace("/", "／")))
        os.makedirs(cdir, exist_ok=True)
        # 章导读
        if intro and os.path.exists(os.path.join(SRC, "eBook", intro)):
            t, body = split_doc(open(os.path.join(SRC, "eBook", intro), encoding="utf-8").read(), "../..")
            with open(os.path.join(cdir, "00-本章导读.md"), "w", encoding="utf-8") as f:
                f.write("# %s\n\n> 第 %d 章导读\n\n%s\n" % (ctitle, n, body))
        # 节
        for base, (ch, sec, stitle) in sorted(sections.items()):
            if ch != n:
                continue
            p = os.path.join(SRC, "eBook", base)
            if not os.path.exists(p):
                continue
            t, body = split_doc(open(p, encoding="utf-8").read(), "../..")
            stitle = re.sub(r"^%d\.%d\s*" % (ch, sec), "", (t or stitle)).strip()
            fname = "%02d.%02d %s.md" % (ch, sec, stitle.replace("/", "／"))
            with open(os.path.join(cdir, fname), "w", encoding="utf-8") as f:
                f.write("# %d.%d %s\n\n%s\n" % (ch, sec, stitle, body))

    # 16.10 讨论附文
    p = os.path.join(SRC, "eBook", "Discussion_about_16.10.md")
    if os.path.exists(p):
        part, ctitle, _ = chapters[16]
        cdir = os.path.join(OUT, re.sub(r"[：:]", " ", part), "第16章 %s" % ctitle)
        body = fix_imgs(open(p, encoding="utf-8").read(), "../..")
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        with open(os.path.join(cdir, "16.10 附：糟糕错误处理的讨论.md"), "w", encoding="utf-8") as f:
            f.write("# 附：关于 16.10「糟糕的错误处理」的讨论\n\n%s\n" % body)

    # 00-说明
    raw = open(os.path.join(SRC, "README.md"), encoding="utf-8").read().replace("\r\n", "\n")
    raw = re.sub(r"(?m)^#.*\n+", "", raw, count=1)
    raw = fix_imgs(raw, ".")
    raw = raw.replace("../images/", "images/")
    raw = re.sub(r"\n{3,}", "\n\n", raw).strip()
    with open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8") as f:
        f.write("# 说明\n\n## 本书信息\n\n- **书名**：Go 入门指南（《The Way To Go》中文译本）\n- **原作者**：Ivo Balbaert\n- **翻译**：Unknwon（无闻）等\n- **来源**：https://github.com/Unknwon/the-way-to-go_ZH_CN @ 7a54d34\n- **导入日期**：2026-10-30\n- **口径**：开源项目口径。结构取自仓库 `eBook/directory.md`（4 个部分 / 21 章 / 190 节）；`directory.md` 本身是导航页，未收；书末附录 A–H（代码引用、FAQ、习题答案等）上游无对应译文，未收\n\n" + raw + "\n")

    n = 0
    for b in IMGS:
        shutil.copy2(os.path.join(SRC, "eBook", "images", b), os.path.join(OUT, "images", b))
        n += 1
    docs = sum(1 for dp, _, fns in os.walk(OUT) for f in fns if f.endswith(".md"))
    dirs = sum(1 for dp, _, fns in os.walk(OUT))
    print("docs:", docs, "dirs:", dirs, "images:", n)


main()