#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""opengl-tutorials（GitBook 源）→ 语雀 方案 B 结构重建（可复用模板）

适用形状：SUMMARY.md 定义层级 + 每章一个无语义目录（`tutNN/`）且自带 `tutNN/res/` 图，
         可读标题只存在 SUMMARY.md 里。

口径（2026-10-18 老板拍板）：
  README.md            → 00-前言.md
  SUMMARY 第 i 分部     → 0i-<分部名>/   （文档号 = 课号，全局连续）
  [第N课：标题](tutNN/zh.md) → 0i-<分部名>/NN-<标题剥「第N课[:：]」>.md
  SUMMARY.md 本身不入库（=目录本身）；不 copy 任何图片

⚠️ 铁律：本脚本吃的是**已完成 CDN 重写**的 md —— 顺序必须是
   ① 在原布局跑 yuque_rewrite_images.py（`./res/x.png` 按 md 目录天然解析）
   ② 再跑本脚本重建树
   反序会踩「同名图串台」（本仓库 icon_smile.gif 同时存在于 tut08/res 与 tut13/res）。

用法：python3 build_tree.py [--apply]   默认 dry-run
"""
import os, re, sys, shutil

SRC = os.environ.get('OT_SRC', '/home/admin/.openclaw/workspace/tmp/opengl-tutorials-4500ac6-clean')
DST = os.environ.get('OT_DST', '/home/admin/.openclaw/workspace/tmp/opengl-tutorials-4500ac6-book')

GROUP_RE = re.compile(r'^\*\s+(?!\[)(.+?)\s*$')
ITEM_RE = re.compile(r'^\s+\*\s+\[(.+?)\]\((.+?)\)\s*$')
LESSON_RE = re.compile(r'^第[一二三四五六七八九十百]+课\s*[:：]\s*')


def parse_summary(path):
    groups = []
    for line in open(path, encoding='utf-8'):
        m = ITEM_RE.match(line)
        if m:
            if not groups:
                raise SystemExit("SUMMARY 结构异常：条目出现在分组之前")
            groups[-1][1].append((m.group(1).strip(), m.group(2).strip()))
            continue
        m = GROUP_RE.match(line)
        if m and not m.group(1).startswith('#'):
            groups.append((m.group(1).strip(), []))
    return groups


def safe(name):
    for ch in '/\\:*?"<>|':
        name = name.replace(ch, '-')
    return name.strip()


def main(apply=False):
    groups = parse_summary(os.path.join(SRC, 'SUMMARY.md'))
    plan, total = [], 0
    for gi, (gname, items) in enumerate(groups, 1):
        gdir = f"{gi:02d}-{safe(gname)}"
        print(f"  {gdir}/  ({len(items)} 课)")
        for title, relpath in items:
            src_md = os.path.join(SRC, relpath)
            if not os.path.isfile(src_md):
                raise SystemExit(f"缺文件: {relpath}")
            n = int(re.search(r'tut(\d+)', relpath).group(1))
            doc = f"{n:02d}-{safe(LESSON_RE.sub('', title).strip())}.md"
            plan.append((src_md, os.path.join(gdir, doc), title))
            total += 1
    print(f"[build] 节点 {total + 1 + len(groups)}（文档 {total + 1} / 目录 {len(groups)}）")
    if not apply:
        print("[build] DRY"); return
    if os.path.isdir(DST):
        shutil.rmtree(DST)
    os.makedirs(DST)
    shutil.copyfile(os.path.join(SRC, 'README.md'), os.path.join(DST, '00-前言.md'))
    for src_md, rel, _ in plan:
        out = os.path.join(DST, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        shutil.copyfile(src_md, out)
    bad = [f for r, _, fs in os.walk(DST) for f in fs if not f.endswith('.md')]
    if bad:
        raise SystemExit(f"目标树混入非 md 文件: {bad[:5]}")
    left = [(os.path.join(r, f), m.group(1))
            for r, _, fs in os.walk(DST) for f in fs
            for m in re.finditer(r'!\[[^\]]*\]\(([^)]+)\)', open(os.path.join(r, f), encoding='utf-8').read())
            if not m.group(1).startswith('http')]
    if left:
        raise SystemExit(f"残留本地图引用: {left[:5]}")
    print(f"[build] 已写出 {DST}")


if __name__ == '__main__':
    main(apply='--apply' in sys.argv)