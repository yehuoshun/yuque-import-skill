#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DataminingGuideBook（GitBook 源，5e05231）→ 语雀导入用干净目录树。

规则：
  - README.md           → 00-前言.md
  - chapter-N/chapter-N-0.md → NN-章名/NN-章名.md   （章首页，`-` < `.` 保证排第一）
  - chapter-N/chapter-N-M.md → NN-章名/NN.M-标题.md （子节，标题取自 SUMMARY.md）
  - SUMMARY.md / book.json 不入库（前者是目录本身、后者是构建配置且为空）
  - img/ 原样拷进来（保持 `../img/...` 引用不变），后续由 yuque_rewrite_images.py 传 CDN 再删
"""
import os
import re
import shutil
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "dmg-probe"
OUT = sys.argv[2] if len(sys.argv) > 2 else "dmg-5e05231-clean"

summary = open(os.path.join(SRC, "SUMMARY.md"), encoding="utf-8").read()

# 按 SUMMARY 顺序取 (缩进层级, 标题, 路径)
entries = []
for line in summary.splitlines():
    m = re.match(r"^(\s*)\* \[(.+?)\]\((.+?)\)\s*$", line)
    if m:
        indent = len(m.group(1))
        entries.append((indent, m.group(2), m.group(3)))

# 顶级条目 = 章
chapters = []  # (章标题, [(子标题, 路径)])
for indent, title, path in entries:
    if indent == 0:
        chapters.append([title, []])
    else:
        chapters[-1][1].append((title, path))

if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

# 前言
shutil.copyfile(os.path.join(SRC, "README.md"), os.path.join(OUT, "00-前言.md"))

plan = []
for i, (ctitle, subs) in enumerate(chapters, 1):
    dname = "%02d-%s" % (i, ctitle)
    dpath = os.path.join(OUT, dname)
    os.makedirs(dpath)
    plan.append((dname, "TITLE", None))
    head_src = None
    items = [("NN", ctitle, None)] + [(("%s.%d" % ("NN", k)), t, p)
                                      for k, (t, p) in enumerate(subs, 1)]
    for num, title, path in items:
        if path is None:  # 章首页
            path = "chapter-%d/chapter-%d-0.md" % (i, i)
        fname = "%s-%s.md" % (num.replace("NN", "%02d" % i), title)
        # 文件名里的 `/` `:` 等清洗
        fname = re.sub(r'[/\\:*?"<>|]', "-", fname)
        body = open(os.path.join(SRC, path), encoding="utf-8").read()
        open(os.path.join(dpath, fname), "w", encoding="utf-8").write(body)
        plan.append((dname + "/" + fname, "DOC", path))

# 图片跟随（保持目录结构，只在根上一层）
if os.path.isdir(os.path.join(SRC, "img")):
    shutil.copytree(os.path.join(SRC, "img"), os.path.join(OUT, "img"))

docs = [p for p in plan if p[1] == "DOC"]
titles = [p for p in plan if p[1] == "TITLE"]
print("目录 %d / 文档 %d / 合计 %d" % (len(titles), len(docs), len(plan)))
print("图片文件 %d" % sum(len(f) for _, _, f in os.walk(os.path.join(OUT, "img"))))
# 源 md 覆盖核对
src_md = set()
for root, _, files in os.walk(SRC):
    if "/.git" in root or root.endswith("/.git"):
        continue
    for f in files:
        if f.endswith(".md") and root != SRC:
            src_md.add(os.path.relpath(os.path.join(root, f), SRC))
used = {p for _, _, p in plan if p}
missing = src_md - used
extra = used - src_md
print("源 md 总数 %d / 已用 %d / 未用 %s / 凭空 %s" % (len(src_md), len(used), sorted(missing), sorted(extra)))
