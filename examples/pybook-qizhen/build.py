#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fpb52 #249 Python 教程 — ruanqizhen/python_book（py.qizhen.xyz，Docusaurus）

sidebars.js 定序：前言 README + 6 分区（编程基础/函数式/面向对象/并发/数据结构与算法/无所不能）+ 尾声。
只吃 docs/ 中文 md；剔 i18n/en 英文版、src/static 脚手架、Microsoft/（Windows 相关杂项？先看）。
"""
import os, re, json, shutil

SRC = "../pybook-src/docs"
OUT = "site"
os.makedirs(OUT, exist_ok=True)

# ---- sidebars.js 解析（简化：按 category/doc 结构手动建序）----
# 结构: 前言 README → [编程基础(ide+15) → 函数式(functional+6) → 面向对象(oop+10) → 并发(3) → 数据结构与算法(algorithm+6) → 无所不能(all_powerful+14)] → epilogue
PLAN = [
    ("00-前言.md", "README"),
    ("01-编程基础", ["ide", "hello_world", "fundamentals", "variable", "calculation",
                     "string", "list", "condition", "loop", "dict", "function",
                     "module", "exception", "file_io", "debug"]),
    ("02-函数式编程", ["functional", "recursive", "first_class_func", "comprehension",
                    "generator", "high_order", "decorator"]),
    ("03-面向对象编程", ["oop", "class", "multiple_inheritance", "objects", "iterator",
                      "magic_methods", "oop_design", "coding_style", "type_hinting"]),
    ("04-并发与并行", ["asyncio", "multithread", "multiprocess"]),
    ("05-数据结构与算法", ["algorithm", "counter", "array", "linked_list", "deque",
                       "tree", "hashtable"]),
    ("06-无所不能", ["all_powerful", "time", "regex", "pytest", "numpy", "pandas",
                   "matplotlib", "tkinter", "pygame", "pyspark", "folium", "requests",
                   "fastapi", "ai_api", "miscellaneous"]),
    ("07-尾声.md", "epilogue"),
]

def read_md(name):
    p = os.path.join(SRC, name + ".md")
    if not os.path.exists(p):
        print("MISSING:", name)
        return None
    return open(p, encoding="utf-8").read()

def clean(txt):
    # 剥 frontmatter
    if txt.startswith("---"):
        end = txt.find("---", 3)
        if end != -1:
            txt = txt[end+3:].lstrip("\n")
    # 剥首个 H1（文档标题由文件名给）
    lines = txt.split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith("# "):
            lines.pop(i)
            break
    txt = "\n".join(lines).strip()
    return txt

manifest = {"groups": {}, "files": []}

# 根级 00-前言
md = read_md("README")
if md:
    open(os.path.join(OUT, "00-前言.md"), "w", encoding="utf-8").write("# 前言\n\n" + clean(md) + "\n")
    manifest["files"].append("00-前言.md")

for gname, items in PLAN:
    if gname.endswith(".md"):
        name = gname[:-3]
        md = read_md(items if isinstance(items, str) else "")
        if md:
            open(os.path.join(OUT, gname), "w", encoding="utf-8").write(f"# {name}\n\n" + clean(md) + "\n")
            manifest["files"].append(gname)
        continue
    gpath = os.path.join(OUT, gname)
    os.makedirs(gpath, exist_ok=True)
    manifest["groups"][gname] = gpath
    for i, item in enumerate(items):
        md = read_md(item)
        if md is None:
            continue
        # 标题 = 首个 H1（若有）或文件名
        m = re.search(r'^# (.+)$', md, re.M)
        title = m.group(1).strip() if m else item
        title = re.sub(r'[\\/:*?"<>|]', "／", title)
        fname = f"{i+1:02d}-{title}.md"
        open(os.path.join(gpath, fname), "w", encoding="utf-8").write(f"# {title}\n\n" + clean(md) + "\n")
        manifest["files"].append(f"{gname}/{fname}")

# 图片：docs/images/* → site 各分组下 images/（按引用路径）
img_refs = set()
for root, dirs, files in os.walk(SRC):
    for fn in files:
        if fn.endswith((".png", ".jpg", ".gif", ".jpeg", ".svg")):
            img_refs.add(fn)
# 拷贝到每个需要的地方？简化：拷到 site/images/ 根，md 里 images/xxx 相对自身目录 → 需每个分组下有 images/
# 更稳：把图拷到 site/ 下所有分组目录的 images/（引用是 images/xxx 相对 md 所在目录）
for gname, items in PLAN:
    if gname.endswith(".md"):
        continue
    gpath = os.path.join(OUT, gname)
    os.makedirs(os.path.join(gpath, "images"), exist_ok=True)
    for fn in img_refs:
        src = os.path.join(SRC, "images", fn)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(gpath, "images", fn))
# 根级文档的 images（00-前言 等）
os.makedirs(os.path.join(OUT, "images"), exist_ok=True)
for fn in img_refs:
    src = os.path.join(SRC, "images", fn)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(OUT, "images", fn))

with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=1)
print("files:", len(manifest["files"]), "imgs:", len(img_refs))
