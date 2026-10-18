#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根级顺序归位（toc-md 收尾后根级 DOC 会被排到 TITLE 目录之后，SKILL 坑 29）。

做法：期望顺序列表 → 逐项找节点，把它 prependNode 到「期望列表里紧随其后、且当前存在」的节点前面。
每轮回读校验，最多 3 轮；仍不符则报 FAIL 并打印实际顺序。

用法：python3 fix_root_order.py <book_id>
"""
import os
import sys

sys.path.insert(0, "/home/admin/.openclaw/workspace/tmp/yuque-import-skill/scripts")
from yuque_tree_import import load_token, api  # noqa: E402

BASE = "https://www.yuque.com/api/v2"

EXPECT = ["index.md", "intro.md", "01 Getting started", "02 Lighting", "03 Model Loading",
          "04 Advanced OpenGL", "05 Advanced Lighting", "06 In Practice", "07 PBR",
          "08 Guest Articles", "legacy.md", "code_repo.md"]


def root_order(tok, book):
    toc = api(tok, BASE, "GET", "/repos/%s/toc" % book)["data"]
    kids = [n for n in toc if not (n.get("parent_uuid") or "")]
    return kids


def prepend(tok, book, node_uuid, target_uuid):
    api(tok, BASE, "PUT", "/repos/%s/toc" % book,
        {"action": "prependNode", "action_mode": "sibling",
         "node_uuid": node_uuid, "target_uuid": target_uuid})


def main():
    book = sys.argv[1]
    tok = load_token("TOKEN_L91")
    for rnd in range(1, 21):
        kids = root_order(tok, book)
        titles = [k["title"] for k in kids]
        if titles == EXPECT:
            print("[fix-root] 第 %d 轮：根级顺序已正确 ✅" % rnd)
            print("  ", titles)
            return
        print("[fix-root] 第 %d 轮 实际: %s" % (rnd, titles))
        by_title = {k["title"]: k for k in kids}
        pos = {k["title"]: i for i, k in enumerate(kids)}
        for i, want in enumerate(EXPECT):
            n = by_title.get(want)
            if not n or pos[want] == i:
                continue
            tgt = next((by_title[w] for w in EXPECT[i + 1:] if w in by_title), None)
            if tgt is None:
                # 期望它排最后：用 prependNode 到「当前最后一个」之前会错序，改用 editNode 不支持 → 跳过
                print("  [warn] %s 期望排末尾，跳过" % want)
                continue
            if pos[want] > pos[tgt["title"]]:
                print("  移动 %s → %s 之前" % (want, tgt["title"]))
                prepend(tok, book, n["uuid"], tgt["uuid"])
                break
    kids = root_order(tok, book)
    titles = [k["title"] for k in kids]
    print("[fix-root] 20 轮后: %s" % titles)
    print("  RESULT=%s" % ("PASS ✅" if titles == EXPECT else "FAIL ❌"))

if __name__ == "__main__":
    main()
