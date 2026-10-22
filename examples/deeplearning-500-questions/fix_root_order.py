#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根级顺序归位（toc-md 收尾后根级 DOC 会被排到 TITLE 目录之后，SKILL 坑 29）。"""
import os
import sys

# 用法: python3 fix_root_order.py <book_id>
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "scripts"))
from yuque_tree_import import load_token, api  # noqa: E402

BASE = "https://www.yuque.com/api/v2"
BOOK = sys.argv[1] if len(sys.argv) > 1 else "84856909"
EXPECT = ["README.md", "目录预览.md"] + [n for n in [
    "ch01_数学基础", "ch02_机器学习基础", "ch03_深度学习基础", "ch04_经典网络",
    "ch05_卷积神经网络(CNN)", "ch06_循环神经网络(RNN)", "ch07_生成对抗网络(GAN)",
    "ch08_目标检测", "ch09_图像分割", "ch10_强化学习", "ch11_迁移学习",
    "ch12_网络搭建及训练", "ch13_优化算法", "ch14_超参数调整", "ch15_GPU和框架选型",
    "ch16_自然语言处理(NLP)", "ch17_模型压缩、加速及移动端部署",
    "ch18_后端架构选型、离线及实时计算", "ch18_后端架构选型及应用场景",
    "ch19_软件专利申请及权利保护"]]

tok = load_token("TOKEN_L91")


def root_kids():
    toc = api(tok, BASE, "GET", "/repos/%s/toc" % BOOK)["data"]
    return [n for n in toc if not (n.get("parent_uuid") or "")]


def prepend(node_uuid, target_uuid):
    api(tok, BASE, "PUT", "/repos/%s/toc" % BOOK,
        {"action": "prependNode", "action_mode": "sibling",
         "node_uuid": node_uuid, "target_uuid": target_uuid})


for rnd in range(1, 21):
    kids = root_kids()
    titles = [k["title"] for k in kids]
    if titles == EXPECT:
        print("[fix-root] 第 %d 轮：根级顺序已正确 ✅" % rnd)
        for t in titles:
            print("  ", t)
        sys.exit(0)
    by_title = {k["title"]: k for k in kids}
    pos = {k["title"]: i for i, k in enumerate(kids)}
    moved = False
    for i, want in enumerate(EXPECT):
        n = by_title.get(want)
        if not n or pos.get(want) == i:
            continue
        tgt = next((by_title[w] for w in EXPECT[i + 1:] if w in by_title), None)
        if tgt is None:
            continue
        if pos[want] > pos[tgt["title"]]:
            print("  第 %d 轮 移动 %s → %s 之前" % (rnd, want, tgt["title"]))
            prepend(n["uuid"], tgt["uuid"])
            moved = True
            break
    if not moved:
        print("[fix-root] 无法进一步收敛；实际：", titles)
        sys.exit(1)
print("[fix-root] FAIL 未收敛")
sys.exit(1)