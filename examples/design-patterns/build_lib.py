#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""me115/design_patterns《图说设计模式》→ 语雀 clean 树（2026-10-22 固化）。

特性：
  1. 吃源仓库的 reST 书稿（Sphinx 工程），复用 `scripts/yuque_rst_convert.py`
     （其中 literalinclude 内联、`.. contents::` 剥离、doctitle_xform=False 保层级、
      块间空行分隔都在主脚本里，见 references 坑 55）
  2. 重建中文树：`NN-中文标题.md`（标题取转换后 md 的首个 H1，剥掉后不再重复）
  3. 图：`/_static/X` 绝对路径 → 相对 `_static/`（根）/`../_static/`（子目录）；
     State1.png/State2.png 上游大小写写错（站点 404，磁盘是小写）→ 按大小写不敏感纠正
  4. 脚手架一律不入库：conf.py/Makefile/make.bat/sphinx_rtd_theme/_static/
     design_patterns.EAP/state_diagram.vsd/dp_tmp.txt/code/（示例源码已由 literalinclude 内联）

用法：
  python3 build_lib.py --clean <repo clean 目录> --out <输出 clean 树>
  # 之后：yuque_rewrite_images.py <out> <img_map> → 删 <out>/_static → tree_import --toc-md
"""
import argparse
import importlib.util
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(SKILL, "scripts"))

_spec = importlib.util.spec_from_file_location("yrc", os.path.join(SKILL, "scripts", "yuque_rst_convert.py"))
yrc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(yrc)

# 源 rst（相对 repo 根）→ 目标相对路径（数字前缀让字典序天然正确）
# 目录 landings 用 00-xxx.md；根级 doc 00/01，仓库说明 99 收尾
TREE = [
    ("index.rst",                       "00-前言.md"),
    ("read_uml.rst",                    "01-{t}"),      # 01-看懂UML类图和时序图.md
    ("creational_patterns/creational.rst", "02-创建型模式/00-{t}"),
    ("creational_patterns/simple_factory.rst",   "02-创建型模式/01-{t}"),
    ("creational_patterns/factory_method.rst",   "02-创建型模式/02-{t}"),
    ("creational_patterns/abstract_factory.rst", "02-创建型模式/03-{t}"),
    ("creational_patterns/builder.rst",          "02-创建型模式/04-{t}"),
    ("creational_patterns/singleton.rst",        "02-创建型模式/05-{t}"),
    ("structural_patterns/structural.rst",  "03-结构型模式/00-{t}"),
    ("structural_patterns/adapter.rst",     "03-结构型模式/01-{t}"),
    ("structural_patterns/bridge.rst",      "03-结构型模式/02-{t}"),
    ("structural_patterns/decorator.rst",   "03-结构型模式/03-{t}"),
    ("structural_patterns/facade.rst",      "03-结构型模式/04-{t}"),
    ("structural_patterns/flyweight.rst",   "03-结构型模式/05-{t}"),
    ("structural_patterns/proxy.rst",       "03-结构型模式/06-{t}"),
    ("behavioral_patterns/behavioral.rst",  "04-行为型模式/00-{t}"),
    ("behavioral_patterns/command.rst",     "04-行为型模式/01-{t}"),
    ("behavioral_patterns/mediator.rst",    "04-行为型模式/02-{t}"),
    ("behavioral_patterns/observer.rst",    "04-行为型模式/03-{t}"),
    ("behavioral_patterns/state.rst",       "04-行为型模式/04-{t}"),
    ("behavioral_patterns/strategy.rst",    "04-行为型模式/05-{t}"),
    ("readme.rst",                      "99-仓库说明.md"),
]

# 注：上游 rst 把两张图写成 State1/State2.png，磁盘是小写 state1/state2.png（站点同错=404）。
# 口径：**保留上游写法**（alt/引用名照抄），拷图时按大小写不敏感解析真身（内容对就行）。


def norm_title(h1):
    t = re.sub(r"\s+", " ", h1).strip()
    t = t.replace("/", "／")          # 文件系统不让带半角斜杠
    return t


def first_h1(md):
    m = re.search(r"^# (.+)$", md, re.M)
    return m.group(1).strip() if m else ""


def strip_first_h1(md):
    return re.sub(r"^# .+\n+", "", md, count=1, flags=re.M)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", required=True, help="repo clean 目录（prep 产物）")
    ap.add_argument("--out", required=True, help="输出 clean 树目录")
    args = ap.parse_args()
    clean, out = os.path.abspath(args.clean), os.path.abspath(args.out)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)

    n = 0
    for src_rel, dst_tpl in TREE:
        src = os.path.join(clean, src_rel)
        md = yrc.rst_to_md(src, clean)
        h1 = first_h1(md)
        title = norm_title(h1)
        # index 去掉 "Indices and tables" 伪章节（genindex/search 垃圾）
        if src_rel == "index.rst":
            md = re.split(r"^#+ Indices and tables\s*$", md, flags=re.M)[0].rstrip() + "\n"
            title = "前言"
        if "{t}" in dst_tpl:
            dst_rel = dst_tpl.format(t=title + ".md")
            md = strip_first_h1(md)          # 首个 H1 == 文件名标题 → 剥掉，避免语雀双标题
        else:
            dst_rel = dst_tpl
            title = re.sub(r"^\d+-", "", os.path.splitext(os.path.basename(dst_rel))[0])
            md = strip_first_h1(md)
        dst = os.path.join(out, dst_rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        # 图引用 → 相对 _static（根级 0 层、子目录 1 层）
        depth = dst_rel.count("/")
        prefix = "../" * depth + "_static/"
        md = re.sub(r"\]\(/_static/([^)]+)\)", lambda m: "](%s%s)" % (prefix, m.group(1)), md)
        open(dst, "w", encoding="utf-8").write(md)
        n += 1
        print("  %-70s <- %s" % (dst_rel, src_rel))

    # 拷贝被引用的图（大小写不敏感解析）
    static_src = os.path.join(clean, "_static")
    have = {f.lower(): f for f in os.listdir(static_src)}
    refs = set()
    for root, _, files in os.walk(out):
        for f in files:
            if not f.endswith(".md"):
                continue
            for m in re.finditer(r"\]\((\.\./)*_static/([^)]+)\)", open(os.path.join(root, f), encoding="utf-8").read()):
                refs.add(m.group(2))
    dst_static = os.path.join(out, "_static")
    os.makedirs(dst_static, exist_ok=True)
    miss = []
    for r in sorted(refs):
        real = have.get(r.lower())
        if not real:
            miss.append(r)
            continue
        shutil.copy(os.path.join(static_src, real), os.path.join(dst_static, r))
    print("md 文档 %d 篇；引用图片 %d 张（缺失 %s）" % (n, len(refs), miss or "无"))
    print("下一步：yuque_rewrite_images.py <%s> <img_map.json> → 删 _static → tree_import --toc-md" % out)


if __name__ == "__main__":
    main()