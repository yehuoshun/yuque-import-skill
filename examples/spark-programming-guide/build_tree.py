#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""aiyanbo/spark-programming-guide-zh-cn（GitBook 3.x 源，487c68a）→ 语雀导入用干净目录树。

规则（datamining-guide build_tree.py 的通用化，支持最多 4 层嵌套）：
  - README.md → 00-前言.md（根级文档）
  - SUMMARY.md 缩进 = 树层级（唯一权威，3~4 层嵌套，别按文件名猜）
  - 每层 dir 命名 `prefix-标题/`；若该节点自带文件 → 章首页 `prefix-标题.md` 放 dir 内
    （`-`(0x2D) < `.`(0x2E) 天然排第一）；子节点 `prefix.k-标题.md`
  - 父子链上同路径的重复条目（部署/提交应用程序、更多文档/Spark配置）→ 去重，内容并入章首页
  - 孤儿 md（不在 SUMMARY，属书内容）→ 补进树：
      spark-streaming/basic-concepts/{custom-receiver,flume,kafka,kinesis} → 03.2.11..14
      spark-sql/compatibility-with-other-systems/{hive,shark}             → 04.7-与其他系统兼容/
  - LICENSE / cover.jpg（未引用）→ 不入库；img/ 原样拷入，后续 rewrite 传 CDN 后删除
"""
import os
import re
import shutil
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "spark-probe"
OUT = sys.argv[2] if len(sys.argv) > 2 else "spark-487c68a-clean"

# 孤儿：源相对路径 → 归属 (章节序号, 子目录序号或 None, 手动标题)
ORPHANS = [
    # (src_rel, chapter_no, subdir_no_or_None)
    ("spark-streaming/basic-concepts/custom-receiver.md", 3, 2),
    ("spark-streaming/basic-concepts/flume-integration-guide.md", 3, 2),
    ("spark-streaming/basic-concepts/kafka-integration-guide.md", 3, 2),
    ("spark-streaming/basic-concepts/kinesis-integration.md", 3, 2),
    ("spark-sql/compatibility-with-other-systems/compatibility-with-apache-hive.md", 4, None),
    ("spark-sql/compatibility-with-other-systems/migration-guide-shark-user.md", 4, None),
]

def first_heading(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^#\s+(.+?)\s*$", line)
            if m:
                return m.group(1).strip()
    return os.path.splitext(os.path.basename(path))[0]

def clean_name(s):
    s = re.sub(r'[/\\:*?"<>|]', "-", s)
    s = s.strip(" .")
    return s

# ---- 1. 解析 SUMMARY.md 成嵌套树 ----
entries = []
for line in open(os.path.join(SRC, "SUMMARY.md"), encoding="utf-8"):
    m = re.match(r"^(\s*)\* \[(.+?)\]\((.+?)\)\s*$", line)
    if m:
        entries.append((len(m.group(1)), m.group(2), m.group(3)))

root = []          # 顶层节点列表
stack = []         # [(indent, node)]
for indent, title, path in entries:
    if indent == 0 and title == "Introduction":
        continue  # Introduction = README.md，单独处理为 00-前言.md
    node = {"title": title, "path": path, "children": []}
    while stack and stack[-1][0] >= indent:
        stack.pop()
    if stack:
        stack[-1][1]["children"].append(node)
    else:
        root.append(node)
    stack.append((indent, node))

# ---- 2. 渲染树 ----
if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

shutil.copyfile(os.path.join(SRC, "README.md"), os.path.join(OUT, "00-前言.md"))
plan = [("00-前言.md", "DOC")]
used_paths = set()
used_paths.add("README.md")

def render_node(node, prefix, outdir):
    """node 有 children → dir；自带 path → 该 dir 的章首页。返回 (是否被去重)。"""
    title = node["title"]
    if node.get("_skip"):             # 去重标记：内容并入祖先，不生成节点
        return
    if node["children"]:
        dname = "%s-%s" % (prefix, clean_name(title))
        dpath = os.path.join(outdir, dname)
        os.makedirs(dpath, exist_ok=True)
        plan.append((os.path.relpath(dpath, OUT), "TITLE"))
        if node["path"]:              # 有文件的目录 → 章首页
            fname = "%s-%s.md" % (prefix, clean_name(title))
            body = open(os.path.join(SRC, node["path"]), encoding="utf-8").read()
            open(os.path.join(dpath, fname), "w", encoding="utf-8").write(body)
            plan.append((os.path.relpath(os.path.join(dpath, fname), OUT), "DOC"))
            used_paths.add(node["path"])
        for k, child in enumerate(node["children"], 1):
            render_node(child, "%s.%d" % (prefix, k), dpath)
    else:
        fname = "%s-%s.md" % (prefix, clean_name(title))
        body = open(os.path.join(SRC, node["path"]), encoding="utf-8").read()
        open(os.path.join(outdir, fname), "w", encoding="utf-8").write(body)
        plan.append((os.path.relpath(os.path.join(outdir, fname), OUT), "DOC"))
        used_paths.add(node["path"])

# 预处理：标记父子链上同路径的重复节点
reused_parent = set()  # 去重掉的父子同路径

def mark_dups(node, seen):
    if node["path"] in seen:
        node["_skip"] = True
        reused_parent.add(node["path"])
    else:
        seen.add(node["path"])
    for c in node["children"]:
        mark_dups(c, set(seen))

def flatten(node):
    """被去重节点的子节点提升到父级（内容已并入祖先章首页，但子孙还得渲染）。"""
    kids = []
    for c in node["children"]:
        flatten(c)
        if c.get("_skip"):
            kids.extend(c["children"])   # 提升
        else:
            kids.append(c)
    node["children"] = kids

# 章节 = 顶层节点（Title 为 None 的 Introduction 已在 root 里过滤）
chapters = [n for n in root]
for i, node in enumerate(chapters, 1):
    mark_dups(node, set())
for node in chapters:
    flatten(node)
for i, node in enumerate(chapters, 1):
    render_node(node, "%02d" % i, OUT)

# ---- 3. 孤儿补树 ----

def title_base(rel):
    # 由源路径猜目录名（仅用于孤儿新建子目录的命名）
    d = os.path.basename(os.path.dirname(rel))
    return {"compatibility-with-other-systems": "与其他系统兼容"}.get(d, d)

created_dirs = set()
for src_rel, ch, sub in ORPHANS:
    title = first_heading(os.path.join(SRC, src_rel))
    if sub is None:
        # 章下新建子目录：04.7-与其他系统兼容/
        chap = chapters[ch - 1]
        prefix = "%02d.%d" % (ch, len(chap["children"]) + 1)
        dname = "%s-%s" % (prefix, clean_name(title_base(src_rel)))
        dpath = os.path.join(OUT, "%02d-%s" % (ch, clean_name(chapters[ch-1]["title"])), dname)
        os.makedirs(dpath, exist_ok=True)
        if dpath not in created_dirs:
            created_dirs.add(dpath)
            plan.append((os.path.relpath(dpath, OUT), "TITLE"))
        orphans_in_dir = [o for o in ORPHANS if o[1] == ch and o[2] is None]
        j = orphans_in_dir.index((src_rel, ch, sub)) + 1
        fname = "%s.%d-%s.md" % (prefix, j, clean_name(title))
        shutil.copyfile(os.path.join(SRC, src_rel), os.path.join(dpath, fname))
        plan.append((os.path.relpath(os.path.join(dpath, fname), OUT), "DOC"))
        used_paths.add(src_rel)
    else:
        # 章下已有子目录（如 03.2-基本概念）追加文档：找该子目录最后一个存在的子节点号
        p = os.path.join(OUT, "%02d-%s" % (ch, clean_name(chapters[ch-1]["title"])),
                         "%02d.%d-%s" % (ch, sub, clean_name(chapters[ch-1]["children"][sub-1]["title"])))
        # 取该子目录下现有最大序号
        existing = [d for d in os.listdir(p)]
        nums = [int(re.match(r"^(\d+)\.(\d+)\.(\d+)-", d).group(3)) for d in existing
                if re.match(r"^(\d+)\.(\d+)\.(\d+)-", d)]
        k = (max(nums) + 1) if nums else 1
        fname = "%02d.%d.%d-%s.md" % (ch, sub, k, clean_name(title))
        shutil.copyfile(os.path.join(SRC, src_rel), os.path.join(p, fname))
        plan.append((os.path.relpath(os.path.join(p, fname), OUT), "DOC"))
        used_paths.add(src_rel)

# ---- 4. 图片跟随 ----
if os.path.isdir(os.path.join(SRC, "img")):
    shutil.copytree(os.path.join(SRC, "img"), os.path.join(OUT, "img"))

# ---- 5. 覆盖核对 ----
docs = [p for p in plan if p[1] == "DOC"]
titles = [p for p in plan if p[1] == "TITLE"]
print("目录 %d / 文档 %d / 合计 %d" % (len(titles), len(docs), len(plan)))
print("图片文件 %d" % len(os.listdir(os.path.join(OUT, "img"))))

src_md = set()
for root_dir, _, files in os.walk(SRC):
    if "/.git" in root_dir or root_dir.endswith("/.git"):
        continue
    for f in files:
        if f.endswith(".md") and root_dir != SRC:
            src_md.add(os.path.relpath(os.path.join(root_dir, f), SRC))
if os.path.exists(os.path.join(SRC, "README.md")):
    src_md.add("README.md")
missing = src_md - used_paths
print("源 md 总数 %d / 已用 %d / 未用 %s" % (len(src_md), len(used_paths), sorted(missing)))