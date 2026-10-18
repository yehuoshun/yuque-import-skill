#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Elasticsearch 权威指南：把 md 里的**绝对外链图**（raw.githubusercontent，沙箱/部分网络不可达）
+ 2 处相对图引用 → 上传语雀 CDN 并重写；elastic.co 外链（实测 200）原样保留。

用法: python3 esdg-images.py [--dry]
"""
import os, re, sys, json, time

ROOT = "/home/admin/.openclaw/workspace/tmp/esdg-ef70bab-clean"
SRC = "/home/admin/.openclaw/workspace/tmp/esdg-src"
MAP = "/home/admin/.openclaw/workspace/tmp/esdg-img_map.json"
sys.path.insert(0, "/home/admin/.openclaw/workspace/tmp/yuque-import-skill/scripts")
from yuque_tree_import import load_upload_cfg, upload_image  # noqa

COOKIE_CFG = "~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json"
USER_ID = "25689388"
MD_RE = re.compile(r'(!\[[^\]]*\]\()([^)]+)(\))')
KEEP_HOSTS = ("www.elastic.co",)

dry = "--dry" in sys.argv
cfg = load_upload_cfg(COOKIE_CFG)
if not cfg and not dry:
    print("cookie 不可用", file=sys.stderr); sys.exit(1)

mp = {}
if os.path.exists(MAP):
    mp = json.load(open(MAP, encoding="utf-8"))
print("img_map 缓存条目: %d" % len(mp))


def locate(src, base):
    """本地图文件相对 SRC 的路径；本地没有 → None"""
    cands = []
    if src.startswith("../images/"):
        cands.append("images/" + src.split("../images/", 1)[1])
    if "/master/" in src:
        cands.append(src.split("/master/", 1)[1])
    if src.startswith("images/"):
        cands.append(src)
    for c in cands:
        if os.path.exists(os.path.join(SRC, c)):
            return c
    return None


files = []
for dp, _, fns in os.walk(ROOT):
    for fn in fns:
        if fn.endswith(".md"):
            files.append(os.path.join(dp, fn))
print("扫描 md: %d" % len(files))

rewritten = 0
plan = {}
for fp in sorted(files):
    text = open(fp, encoding="utf-8").read()
    out = []

    def sub(m):
        global rewritten
        pre, src, post = m.group(1), m.group(2).strip(), m.group(3)
        if not src.startswith("http") and not src.startswith("../images/"):
            return m.group(0)
        if src.startswith("http") and any(h in src for h in KEEP_HOSTS):
            return m.group(0)
        rel = locate(src, os.path.dirname(fp))
        if not rel:
            return m.group(0)
        plan[rel] = plan.get(rel, 0) + 1
        if dry:
            rewritten += 1
            return pre + "“CDN:%s”" % rel + post
        url = mp.get(rel)
        if not url:
            url = upload_image(cfg["cookie"], cfg["ctoken"], USER_ID, os.path.join(SRC, rel))
            if not url:
                print("  ✗ 上传失败 %s" % rel)
                return m.group(0)
            mp[rel] = url
            json.dump(mp, open(MAP, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            time.sleep(3)
            print("  ✓ 上传 %s → %s" % (rel, url.split('/')[-1]), flush=True)
        rewritten += 1
        return pre + url + post

    new = MD_RE.sub(sub, text)
    if not dry and new != text:
        open(fp, "w", encoding="utf-8").write(new)

print("\n待处理引用: %d 处 / 唯一文件 %d 个" % (rewritten, len(plan)))
for k, v in sorted(plan.items()):
    print("   %s  ×%d" % (k, v))
print("dry=%s" % dry)