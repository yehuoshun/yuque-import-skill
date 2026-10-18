#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Elasticsearch 权威指南（中文版）源码仓库 → 语雀导入干净副本重建。

源：looly/elasticsearch-definitive-guide-cn @ ef70bab（GitBook 源，NNN_Chapter/NN_Title.md 扁平编号，层级只在 SUMMARY.md）
规则：
  - SUMMARY 顺序 = 阅读顺序（源文件名编号非单调，不按文件名排）
  - 章节目录 = NN-章名/  （NN 按 SUMMARY 顺序 01..N）
  - 章首页 = NN-章名/NN-章名.md（'-'<'.' 天然排第一）
  - 章节子节 = NN-章名/NN.MM-节名.md
  - 根级：README.md → 00-前言.md；Changelog.md → 00-版本变动.md
  - 目录里未被 SUMMARY 引用的 md → 收尾补进所属章节目录（NN.99-原名.md）
  - 导出：images/ cover/ cover.* push.sh update.sh TOC.md README_Wiki.md config.json .gitignore 不进库
"""
import os, re, shutil, sys

SRC = "/home/admin/.openclaw/workspace/tmp/esdg-src"
OUT = "/home/admin/.openclaw/workspace/tmp/esdg-ef70bab-clean"

SUM_RE = re.compile(r'^(\s*)\*\s+\[([^\]]*)\]\(([^)]*)\)\s*$')


def sanitize(t):
    t = t.replace("/", "-").replace("\u00a0", " ")
    t = re.sub(r'\s+', " ", t).strip()
    return t


def case_index():
    """小写路径 → 真实相对路径（SUMMARY 大小写与文件系统不符：500_Cluster_Admin 全小写）"""
    idx = {}
    for dp, _, fns in os.walk(SRC):
        if "/.git" in dp:
            continue
        for fn in fns:
            rel = os.path.relpath(os.path.join(dp, fn), SRC)
            idx[rel.lower()] = rel
    return idx


IDX = case_index()
INTRO_RE = re.compile(r'(intro|overview|readme)', re.I)


def resolve(path):
    if os.path.exists(os.path.join(SRC, path)):
        return path
    return IDX.get(path.lower())


def load_summary():
    chapters = []
    for ln in open(os.path.join(SRC, "SUMMARY.md"), encoding="utf-8"):
        m = SUM_RE.match(ln.rstrip("\n"))
        if not m:
            continue
        depth, title, path = len(m.group(1)), m.group(2), m.group(3)
        if depth == 0:
            chapters.append({"title": title, "landing": resolve(path), "raw_landing": path, "subs": []})
        else:
            chapters[-1]["subs"].append((title, resolve(path)))
    return chapters


def main():
    chapters = load_summary()
    print("SUMMARY 顶层条目: %d" % len(chapters))

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    # Introduction（无子节的 README）→ 根级 00-前言.md
    root_docs = []
    book_chapters = []
    for c in chapters:
        if c["landing"] == "README.md" and not c["subs"]:
            root_docs.append(("00-前言.md", c["landing"]))
        else:
            book_chapters.append(c)
    print("章节: %d / 根级文档: %d" % (len(book_chapters), len(root_docs)))

    used = set()
    total_files = 0
    for i, c in enumerate(book_chapters, 1):
        ctitle = sanitize(c["title"])
        d = "%02d-%s" % (i, ctitle)
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
        # 章首页：SUMMARY 断链/大小写不合时，提升首个 intro 类子节 或 目录内 intro 类文件
        land = c["landing"]
        subs = [x for x in c["subs"] if x[1]]
        if not land:
            for k, (st, sp) in enumerate(subs):
                if sp and INTRO_RE.search(os.path.basename(sp)):
                    land = sp
                    subs.pop(k)
                    print("  章首页提升(子节) %s ← %s" % (d, sp))
                    break
        if not land:
            src_dir = os.path.dirname(c["raw_landing"])
            for fn in sorted(os.listdir(os.path.join(SRC, src_dir))):
                if fn.endswith(".md") and INTRO_RE.search(fn):
                    rel = "%s/%s" % (src_dir, fn)
                    if rel not in [s[1] for s in subs] and rel not in used:
                        land = IDX.get(rel.lower(), rel)
                        print("  章首页提升(目录) %s ← %s" % (d, land))
                        break
        if land:
            shutil.copy2(os.path.join(SRC, land), os.path.join(OUT, d, "%02d-%s.md" % (i, ctitle)))
            used.add(land)
            total_files += 1
        else:
            print("  ⚠️ 无章首页（纯 TITLE）: %s" % d)
        for j, (st, sp) in enumerate(subs, 1):
            sname = "%02d.%02d-%s.md" % (i, j, sanitize(st))
            shutil.copy2(os.path.join(SRC, sp), os.path.join(OUT, d, sname))
            used.add(sp)
            total_files += 1
        # 该章目录里未被引用的 md
        src_dir = os.path.dirname(c["raw_landing"])
        orphans = []
        if src_dir and os.path.isdir(os.path.join(SRC, src_dir)):
            for fn in sorted(os.listdir(os.path.join(SRC, src_dir))):
                rel = "%s/%s" % (src_dir, fn)
                if fn.endswith(".md") and rel not in used:
                    orphans.append(rel)
        for k, rel in enumerate(orphans, 1):
            os.makedirs(os.path.join(OUT, d), exist_ok=True)
            shutil.copy2(os.path.join(SRC, rel), os.path.join(OUT, d, "%02d.99%d-孤儿-%s" % (i, k, os.path.basename(rel))))
            used.add(rel)
            total_files += 1
        if orphans:
            print("  孤儿补树 %s: %s" % (d, orphans))

    for out_name, src_rel in root_docs:
        shutil.copy2(os.path.join(SRC, src_rel), os.path.join(OUT, out_name))
        used.add(src_rel)
        total_files += 1

    # Changelog → 根级
    chg = os.path.join(SRC, "Changelog.md")
    if os.path.exists(chg):
        shutil.copy2(chg, os.path.join(OUT, "00-版本变动.md"))
        used.add("Changelog.md")
        total_files += 1

    # 统计
    dirs = [d for d in sorted(os.listdir(OUT)) if os.path.isdir(os.path.join(OUT, d))]
    root_files = [f for f in sorted(os.listdir(OUT)) if os.path.isfile(os.path.join(OUT, f))]
    print("\n=== 目标树 ===")
    print("顶层目录: %d" % len(dirs))
    for d in dirs:
        n = len([f for f in os.listdir(os.path.join(OUT, d)) if f.endswith(".md")])
        print("  %s/  (%d md)" % (d, n))
    print("根级文件: %s" % root_files)
    print("文件总数: %d" % total_files)

    # 源里所有 md 是否都被覆盖
    all_md = []
    for dp, _, fns in os.walk(SRC):
        if "/.git" in dp:
            continue
        for fn in fns:
            if fn.endswith(".md"):
                all_md.append(os.path.relpath(os.path.join(dp, fn), SRC))
    unmapped = sorted(set(all_md) - used)
    print("\n源 md 总数 %d / 已映射 %d" % (len(all_md), len(used)))
    print("未进库（人工确认）: %s" % unmapped)
    print("节点总数（dir+file）= %d" % (len(dirs) + len(root_files) + total_files))
    print("OUT=%s" % OUT)


if __name__ == "__main__":
    main()