#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导入验收器：本地文件树 ↔ 语雀 TOC 全映射 + 超限分片对账（2026-10-15 固化）

用法:
  curl -s -H "X-Auth-Token: $TOKEN_L91" "https://www.yuque.com/api/v2/repos/<book_id>/toc" > tmp/<repo>-<commit>-toc.json
  python3 scripts/yuque_import_verify.py tmp/<repo>-<commit>-toc.json tmp/<repo>-<commit>-clean

输出：本地文件数 / 语雀 DOC 数 / 单文档映射 / 分片映射 / 缺失文件 / 分片号连续 / 全路径唯一 / PASS|FAIL

⚠️ 关键坑（2026-10-15 legado 实战）：超 512KB 会自动分片，标题形如 `x.json (1/14)`，**里面含 `/`**！
  用 `os.path.dirname()` 或 `'/'.join(...)` 拼路径比较会把 `(1/14)` 当目录切，导致「看起来 6 个文件全丢」的假报警。
  正确姿势：按 TITLE 列表（uuid 链）逐层比，不要拼字符串。

另外：**「TOC 节点数 == 本地节点数」这条验收口径只对无分片库成立**；有分片时必须改成
「每个本地文件都能映射到文档（单文档或其 (1/N) 分片），且分片号 1..N 连续」——本脚本就是干这个的。
"""
import json, os, re, sys
from collections import defaultdict

toc_file, root = sys.argv[1], sys.argv[2]
t = json.load(open(toc_file))['data']
by = {n['uuid']: n for n in t}


def chain(n):
    """返回 (TITLE 祖先标题列表, 自身标题, type)"""
    parts, cur = [], n
    while cur:
        parts.append(cur)
        cur = by.get(cur.get('parent_uuid') or '')
    parts.reverse()
    return [x['title'] for x in parts[:-1]], parts[-1]['title'], parts[-1]['type']


docs = [chain(n) for n in t if n['type'] == 'DOC']
SPLIT = re.compile(r'^(?P<base>.+) \((?P<i>\d+)/(?P<n>\d+)\)$')

files = []
for dp, dn, fn in os.walk(root):
    dn[:] = [d for d in dn if d != '.git']
    for f in fn:
        rel = os.path.relpath(os.path.join(dp, f), root)
        files.append(tuple(rel.split(os.sep)))

missing, multi = [], []
single = 0
for f in sorted(files):
    parents, base = list(f[:-1]), f[-1]
    segs = []
    for anc, title, _ in docs:
        if anc != parents:
            continue
        m = SPLIT.match(title)
        if (m.group('base') if m else title) == base:
            segs.append(title)
    if not segs:
        missing.append('/'.join(f))
    elif len(segs) == 1 and not SPLIT.match(segs[0]):
        single += 1
    else:
        multi.append(('/'.join(f), segs))

# 分片完整性
bad = []
for f, segs in multi:
    idx = []
    tot = set()
    for s in segs:
        m = SPLIT.match(s)
        idx.append(int(m.group('i')))
        tot.add(int(m.group('n')))
    if sorted(idx) != list(range(1, len(segs) + 1)) or len(tot) != 1 or tot.pop() != len(segs):
        bad.append((f, sorted(idx)))

titles_all = [tuple(a + [b]) for a, b, _ in docs]
print('本地文件           :', len(files))
print('语雀 DOC 节点      :', len(docs))
print('单文档映射         :', single)
print('分片映射(文件数)   :', len(multi), '→ 分片节点', sum(len(s) for _, s in multi))
print('缺失文件           :', len(missing), missing[:5])
print('分片号连续/总数    :', 'OK' if not bad else bad[:3])
print('全路径唯一         :', len(titles_all) == len(set(titles_all)))
ok = (not missing) and (not bad) and len(titles_all) == len(set(titles_all))
print('结论               :', 'PASS' if ok else 'FAIL')
