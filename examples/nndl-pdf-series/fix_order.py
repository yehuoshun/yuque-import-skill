#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根级顺序归位 + 根级 TITLE 顺序修正（toc-md 收尾后根级 DOC 落到 TITLE 之后，SKILL 坑 29）。

用法：python3 fix_order.py <book_id> "<期望根级标题1>" "<期望根级标题2>" ...
"""
import sys

sys.path.insert(0, "/home/admin/.openclaw/workspace/code/yuque-import-skill/scripts")
from yuque_tree_import import load_token, api  # noqa: E402

BASE = "https://www.yuque.com/api/v2"


def root_kids(tok, book):
    toc = api(tok, BASE, "GET", "/repos/%s/toc" % book)["data"]
    return [n for n in toc if not (n.get("parent_uuid") or "")]


def prepend(tok, book, node_uuid, target_uuid):
    return api(tok, BASE, "PUT", "/repos/%s/toc" % book,
               {"action": "prependNode", "action_mode": "sibling",
                "node_uuid": node_uuid, "target_uuid": target_uuid})


def main():
    book = sys.argv[1]
    expect = sys.argv[2:]
    tok = load_token("TOKEN_L91")
    for rnd in range(1, 31):
        kids = root_kids(tok, book)
        titles = [k["title"] for k in kids]
        if titles == expect:
            print("[fix] 第 %d 轮：根级顺序正确 ✅" % rnd)
            for t in titles:
                print("   ", t)
            return
        print("[fix] 第 %d 轮 实际: %s" % (rnd, titles))
        by = {k["title"]: k for k in kids}
        pos = {k["title"]: i for i, k in enumerate(kids)}
        moved = False
        for i, want in enumerate(expect):
            n = by.get(want)
            if not n or pos[want] == i:
                continue
            tgt = next((by[w] for w in expect[i + 1:] if w in by), None)
            if tgt is None:
                continue
            if pos[want] > pos[tgt["title"]]:
                print("   移动「%s」→「%s」之前" % (want, tgt["title"]))
                prepend(tok, book, n["uuid"], tgt["uuid"])
                moved = True
                break
        if not moved:
            print("   [warn] 本轮未找到可移动项")
            break
    titles = [k["title"] for k in root_kids(tok, book)]
    print("[fix] 结束: %s" % titles)
    print("   RESULT=%s" % ("PASS ✅" if titles == expect else "FAIL ❌"))


if __name__ == "__main__":
    main()