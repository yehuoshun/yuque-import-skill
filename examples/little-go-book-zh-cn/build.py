#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fpb52 #98《Go 简易教程》(songleo/the-little-go-book_ZH_CN @4c124a9) → 语雀 clean 树

仓库 eBook/ 下 48 个已是中文的 md（N.0=章导读，N.M=节），少量前言页 + 结论。
- 每篇首行 `# 标题` 取作文档名；文件末尾 `## 链接`（目录/上一节/下一节，全是仓库相对链）→ 整段剥掉
- getting-started.md 是空壳（只有标题+链接）→ 不收
- directory.md 是导航页（与 TOC 重复）→ 不收
- 图 /images/*.jpg（站点绝对路径）→ 仓库 images/ → CDN
"""
import os, re, sys, shutil, glob

SRC = "/tmp/g98"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/g98-clean"

IMG = {}


def img_local(name):
    if name not in IMG:
        IMG[name] = "../images/" + name
    return IMG[name]


def fix_images(text):
    def rep(m):
        alt, path = m.group(1), m.group(2)
        base = os.path.basename(path)
        if os.path.exists(os.path.join(SRC, "images", base)):
            return "![%s](%s)" % (alt or "图", img_local(base))
        return m.group(0)
    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", rep, text)


def split_doc(raw):
    """返回 (h1_title, body_without_h1)"""
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = raw.split("\n")
    title = None
    keep = []
    for ln in lines:
        if title is None and ln.startswith("# "):
            title = ln[2:].strip()
            continue
        keep.append(ln)
    body = "\n".join(keep)
    # 剥末尾导航段（## 链接 … EOF）
    body = re.split(r"\n##\s*链接\s*\n", body)[0]
    # 有篇目没有 `## 链接` 标题，导航是裸列表（且 CRLF）——从尾部逐行剥
    NAV = re.compile(r"^(\-\s*\[?目录\]?|\.?\-?\s*上一[章节]?[：:]|\s*上一[章节]?[：:]|\s*下一[章节]?[：:]|\-\s*\[.*\]\(.*\.md\)|\s*)")
    ls = body.split("\n")
    while ls and (not ls[-1].strip() or ls[-1].lstrip().startswith(("- [目录]", "- 上一", "- 下一"))):
        ls.pop()
    body = "\n".join(ls)
    body = fix_images(body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip("\n")
    return title, body


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "images"), exist_ok=True)
    made = []

    # 前言页
    pre_dir = os.path.join(OUT, "前言")
    os.makedirs(pre_dir)
    for fn in ["about-this-book.md", "introduction.md"]:
        title, body = split_doc(open(os.path.join(SRC, "eBook", fn), encoding="utf-8").read())
        if not body.strip():
            continue
        with open(os.path.join(pre_dir, title + ".md"), "w", encoding="utf-8") as f:
            f.write("# %s\n\n%s\n" % (title, body))
        made.append("前言/" + title + ".md")

    # 章节
    for n in range(1, 7):
        files = sorted(glob.glob(os.path.join(SRC, "eBook", "%d.*.md" % n)),
                       key=lambda p: int(re.search(r"\.(\d+)\.md$", p).group(1)))
        intro = None
        secs = []
        for p in files:
            idx = int(re.search(r"\.(\d+)\.md$", p).group(1))
            title, body = split_doc(open(p, encoding="utf-8").read())
            if title is None:
                continue
            if idx == 0:
                intro = (title, body)
            else:
                secs.append((idx, title, body))
        if intro is None:
            continue
        t = re.sub(r"^第\s*\d+\s*章[\s:：]*", "", intro[0])
        t = re.sub(r"^\d+\.0\s*", "", t).strip()
        cdir = os.path.join(OUT, "第%02d章 %s" % (n, t))
        os.makedirs(cdir)
        with open(os.path.join(cdir, "00-本章导读.md"), "w", encoding="utf-8") as f:
            f.write("# %s\n\n> 第 %d 章导读\n\n%s\n" % (t, n, intro[1]))
        made.append("第%02d章 %s/00-本章导读.md" % (n, t))
        for idx, title, body in secs:
            fname = title.replace("/", "／") + ".md"
            with open(os.path.join(cdir, fname), "w", encoding="utf-8") as f:
                f.write("# %s\n\n%s\n" % (title, body))
            made.append("第%02d章 %s/%s" % (n, t, fname))

    # 结论
    title, body = split_doc(open(os.path.join(SRC, "eBook", "conclusion.md"), encoding="utf-8").read())
    with open(os.path.join(OUT, "结论.md"), "w", encoding="utf-8") as f:
        f.write("# 结语：继续之前\n\n%s\n" % body)
    made.append("结论.md")

    # 00-说明（README 精简：剥目录段、剥仓库相对链）
    readme = open(os.path.join(SRC, "README.md"), encoding="utf-8").read()
    readme = re.sub(r"^\ufeff", "", readme)
    # 只剥「# 目录」这一段（到下一个 ``# `` 一级标题为止），后面的致谢/授权/支持要保留
    readme = re.sub(r"(?ms)^# 目录\n.*?(?=^# (?!目录))", "", readme)
    readme = fix_images(readme)
    readme = readme.replace("../images/", "images/")   # 根级文档：图在 images/ 下，不是 ../images/
    readme = re.sub(r"\[([^\]]+)\]\((eBook/[^)]+)\)", r"\1", readme)
    readme = re.sub(r"\n{3,}", "\n\n", readme).strip()
    readme = readme.replace("《Go简易教程》\n===================\n", "")
    with open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8") as f:
        f.write("# 说明\n\n## 本书信息\n\n- **书名**：Go 简易教程（The Little Go Book 中文译本）\n- **原作者**：Karl Seguin\n- **译本维护**：songleo（译：Jell 等）\n- **来源**：https://github.com/songleo/the-little-go-book_ZH_CN @ 4c124a9\n- **授权**：CC BY-NC-SA 4.0\n- **导入日期**：2026-10-30\n- **口径**：开源项目口径；未收 `getting-started.md`（空壳，仅标题+导航链）与 `directory.md`（导航页，与语雀目录重复）\n\n" + readme + "\n")
    made.append("00-说明.md")

    # 拷图
    n = 0
    for name in IMG:
        src = os.path.join(SRC, "images", name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(OUT, "images", name))
            n += 1
    print("docs:", len(made), "images:", n)
    for m in made:
        print("  ", m)


main()