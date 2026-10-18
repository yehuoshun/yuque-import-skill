#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mastering Elasticsearch 中文版 导入验收：TOC 结构 / 全路径唯一 / 根级顺序 / 幽灵 / 逐字符回读 / CDN 抽验。"""
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, "/home/admin/.openclaw/workspace/tmp/yuque-import-skill/scripts")
from yuque_tree_import import load_token, api  # noqa

BOOK = 84707668
BASE = "https://www.yuque.com/api/v2"
ROOT = "/home/admin/.openclaw/workspace/tmp/mes-d2b8d61-clean"
LEDGER = "/home/admin/.openclaw/workspace/tmp/mes-d2b8d61-progress.json"
token = load_token("TOKEN_L91")

toc = api(token, BASE, "GET", f"/repos/{BOOK}/toc")["data"]
doc_nodes = [n for n in toc if n.get("type") == "DOC"]
title_nodes = [n for n in toc if n.get("type") == "TITLE"]
print("TOC 节点 %d (DOC %d / TITLE %d)" % (len(toc), len(doc_nodes), len(title_nodes)))

by_uuid = {n["uuid"]: n for n in toc}
kids = {}
for n in toc:
    kids.setdefault(n.get("parent_uuid") or "", []).append(n)


def path_of(n):
    parts, cur = [], n
    while True:
        parts.append(cur["title"])
        pu = cur.get("parent_uuid") or ""
        if not pu:
            break
        cur = by_uuid[pu]
    return "/".join(reversed(parts))


paths = [path_of(n) for n in doc_nodes]
print("全路径唯一:", len(paths) == len(set(paths)), "(%d/%d)" % (len(set(paths)), len(paths)))

local = []
for dp, _, fns in os.walk(ROOT):
    for fn in fns:
        if fn.endswith(".md"):
            local.append(os.path.relpath(os.path.join(dp, fn), ROOT))
print("本地 md %d ; TOC 路径集合==本地集合: %s" % (len(local), set(paths) == set(local)))
print("  仅在 TOC:", sorted(set(paths) - set(local))[:5])
print("  仅在本地:", sorted(set(local) - set(paths))[:5])

root_kids = [k["title"] for k in kids.get("", [])]
print("根级顺序(%d): %s" % (len(root_kids), root_kids))
# 断言：根级顺序必须完全匹配（结构核对不查同层相对顺序，必须单独断言）
_expect = ["00-前言.md", "01-认识Elasticsearch", "02-强大的用户查询语言DSL", "03-索引底层控制.md",
           "04-探究分布式索引架构", "05-管理Elasticsearch", "06-应对突发事件.md", "07-优化用户体验.md",
           "08-ElasticSearch Java API.md", "09-开发ElasticSearch插件.md"]
print("根级顺序断言:", "PASS ✅" if root_kids == _expect else "FAIL ❌ %s" % root_kids)

# 幽灵
docs_total, off = 0, 0
while True:
    d = api(token, BASE, "GET", f"/repos/{BOOK}/docs?offset={off}&limit=100")["data"]
    docs_total += len(d)
    if len(d) < 100:
        break
    off += 100
print("docs 总数 %d / TOC DOC %d → 幽灵 %d" % (docs_total, len(doc_nodes), docs_total - len(doc_nodes)))

# 逐字符回读（doc_id 取账本，勿用 TOC 节点）
nodes = json.load(open(LEDGER, encoding="utf-8"))["nodes"]
todo = [(rel, rec["doc_id"]) for rel, rec in nodes.items()
        if rec.get("type") == "doc" and os.path.exists(os.path.join(ROOT, rel))]
print("账本可核对 %d 篇" % len(todo), flush=True)
mismatch, empties, checked = [], [], 0
for rel, did in todo:
    raw = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    try:
        d = (api(token, BASE, "GET", f"/repos/{BOOK}/docs/{did}") or {}).get("data") or {}
    except Exception as e:
        mismatch.append((rel, "回读失败 %s" % e))
        continue
    body = d.get("body") or ""
    checked += 1
    if not body.strip():
        empties.append(rel)
    if body != raw and body.rstrip("\n") != raw.rstrip("\n"):
        mismatch.append((rel, "len %d vs %d" % (len(body), len(raw))))
    if checked % 50 == 0:
        print("   ...回读 %d/%d" % (checked, len(todo)), flush=True)
    time.sleep(0.1)
print("逐字符回读: 检查 %d 篇, 不等 %d, 空 %d" % (checked, len(mismatch), len(empties)))
for m in mismatch[:15]:
    print("   ✗ %s :: %s" % (m[1], m[0]))
for e in empties[:15]:
    print("   ⚠️ 空: %s" % e)

imgs = []
for dp, _, fns in os.walk(ROOT):
    for fn in fns:
        if fn.endswith(".md"):
            imgs += re.findall(r'https://cdn\.nlark\.com[^)\s"]+',
                               open(os.path.join(dp, fn), encoding="utf-8").read())
uniq = sorted(set(imgs))
ok = 0
for u in uniq[:5]:
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            print("   CDN %s %s" % (r.status, u.split("/")[-1]))
            ok += 1
    except Exception as e:
        print("   ✗ CDN %s %s" % (e, u))
print("CDN 引用 %d 处 / 唯一 %d / 抽验通过 %d" % (len(imgs), len(uniq), ok))
print("RESULT=%s" % ("PASS" if not mismatch and not empties else "CHECK"))