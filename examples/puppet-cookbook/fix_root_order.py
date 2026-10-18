#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根级顺序归位（toc-md 收尾后根级 DOC 会被排到 TITLE 目录之后，SKILL 坑 29）。

做法：期望顺序列表 → 逐项找节点，把它 prependNode 到「期望列表里紧随其后、且当前存在」的节点前面。
每轮回读校验，最多 3 轮；仍不符则报 FAIL 并打印实际顺序。

用法：python3 fix_root_order.py <book_id>
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
from yuque_tree_import import load_token, api  # noqa: E402

BASE = "https://www.yuque.com/api/v2"

EXPECT = ["00-书名页.md", "01-中文翻译版.md", "02-译者序", "03-原书版权页.md", "04-关于作者.md",
          "05-前言", "06-Puppet 基础设施", "07-监控、报告和排错", "08-Puppet 语言及其写作风格",
          "09-书写更优质的配置清单", "10-使用文件和软件包", "11-用户和虚拟资源", "12-应用程序",
          "13-服务器和云基础设施", "14-外部工具和 Puppet 生态环境"]


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
