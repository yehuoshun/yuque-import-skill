#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mingits/linux-c（《Linux C 编程一站式学习》docsify 源仓库 c6e8593）→ clean tree
口径：开源项目·源仓库。docs/_sidebar.md 全导航 → 3 篇目录 + 5 根文档；
篇目录内 00-<篇名>.md = TOC.md 正文（目录页自身有正文，坑 72 口径）。
"""
import os, re, shutil

SRC = "/tmp/lc67/linux-c-master/docs"   # 改这里
OUT = "/tmp/lc67/lc67-clean"            # 改这里

SAFE = str.maketrans({"/": "／", "\\": "＼", ":": "：", "*": "＊", "?": "？",
                      '"': "＂", "<": "＜", ">": "＞", "|": "｜"})
def safe(s): return s.translate(SAFE).strip().strip(".")

# ---- 1. 解析 _sidebar.md（顺序即根序）----
nodes = []  # (title, path, kind)  kind: doc|dir
for ln in open(f"{SRC}/_sidebar.md", encoding="utf-8"):
    m = re.match(r"^- \[(.+?)\]\((.+?)\)\s*$", ln)
    if not m: continue
    title, path = m.group(1), m.group(2)
    path = path.split("#", 1)[0]
    if not path: continue
    nodes.append((title, f"{path}.md", "dir" if path.endswith("/TOC") else "doc"))

def resolve(p):
    if os.path.exists(f"{SRC}/{p}"): return f"{SRC}/{p}"
    return None

if os.path.exists(OUT): shutil.rmtree(OUT)
os.makedirs(f"{OUT}/imgs")

# ---- 2. 拷图 ----
for fn in os.listdir(f"{SRC}/images"):
    shutil.copy2(f"{SRC}/images/{fn}", f"{OUT}/imgs/{fn}")
img_count = len(os.listdir(f"{OUT}/imgs"))

# ---- 3. 生成树 ----
def strip_h1(b):
    ls = b.split("\n")
    for i, l in enumerate(ls[:6]):
        if l.strip().startswith("# "):
            return "\n".join(ls[i + 1:]).lstrip("\n")
    return b

def fix_imgs(b, rel):
    def rep(m):
        alt, fn = m.group(1), m.group(2)
        return f"![{alt}]({rel}imgs/{fn})"
    # 章节: ../images/x ; 根文档: images/x —— 统一按深度重写到 imgs/
    return re.sub(r"!\[([^\]]*)\]\([^)]*?images/([^)]+)\)", rep, b)

stats = {"docs": 0, "dirs": 0}
for i, (title, path, kind) in enumerate(nodes, 1):
    srcp = resolve(path)
    assert srcp, (title, path)
    body = strip_h1(open(srcp, encoding="utf-8").read())
    base = f"{i:02d}-{safe(title)}"
    if kind == "dir":
        # 篇目录：TOC.md → 00-<篇名>.md（目录自身有正文），其余 ch*.md 直放
        toc_src = f"{SRC}/{'/'.join(path.split('/')[:-1])}/TOC.md"
        d = f"{OUT}/{base}"
        os.makedirs(d); stats["dirs"] += 1
        toc_body = strip_h1(open(toc_src, encoding="utf-8").read())
        toc_body = fix_imgs(toc_body, "../")
        open(f"{d}/00-{safe(title)}.md", "w", encoding="utf-8").write(toc_body)
        stats["docs"] += 1
        for fn in sorted(os.listdir(os.path.dirname(srcp))):
            if fn.endswith(".md") and fn != "TOC.md":
                b = strip_h1(open(f"{os.path.dirname(srcp)}/{fn}", encoding="utf-8").read())
                b = fix_imgs(b, "../")
                open(f"{d}/{fn}", "w", encoding="utf-8").write(b)
                stats["docs"] += 1
    else:
        body = fix_imgs(body, "")
        open(f"{OUT}/{base}.md", "w", encoding="utf-8").write(body)
        stats["docs"] += 1

print("sidebars 根项", len(nodes), "→ 目录", stats["dirs"], "文档", stats["docs"], "图", img_count)