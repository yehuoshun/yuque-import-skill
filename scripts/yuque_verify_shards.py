#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yuque_verify_shards.py — 分片文档「内容零丢失」验收（2026-10-17 加）
====================================================================
为什么需要它：`yuque_import_verify.py` 只验『路径映射』（节点在不在、分片号连不连续），
**不看分片正文**。2026-10-17 发现 `_split_json_list` 有 bug（绝对下标切段内列表 → 第 2 片起正文全丢），
legado 多个库中招，而路径验收全 PASS 没拦住。本脚本补上这一层。

判定（两种方法，命中任一即 PASS，方法写进输出）：
  A. 拼回文本：逐片剥围栏与尾注后直接拼接，与本地文件**逐字符相等**（覆盖行边界切分）
  B. 数组回拼：各片都能 `json.loads` → 拼回列表与本地 `json.loads` 结果**逐条相等**
     （覆盖 JSON 条目边界切分；「单条超限」片是裸对象，会自动包成单元素列表）

用法:
    python3 scripts/yuque_verify_shards.py --root <clean_dir> --book <book_id> --progress <progress.json>

退出码: 0 = 全 PASS；1 = 有不一致（会列出）
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yuque_tree_import import api, load_token  # noqa: E402

BASE = "https://www.yuque.com/api/v2"


def strip_shard(body):
    """去掉 ```lang 围栏 + 尾部 `<!-- 分段 -->` 注记，还原该片正文（精确逆运算）。

    正文构造固定为：`wrap(s) + "\n\n<!-- 分段 ... -->\n"`，其中
      wrap(s) = s          （.md）
      wrap(s) = "```lang\n" + s + "\n```"（其他）
    所以倒着剥：先切尾注并吃掉它的前导两个换行，再去围栏首行与行首的 "\n```" 尾巴。
    （2026-10-17 踩：先剥围栏再剥尾注 → 每片多 6 字符（"\n```\n\n" 残留）→ 全库假失败）
    """
    t = body.strip()
    i = t.rfind("<!-- 分段")
    if i != -1:
        t = t[:i]
        if t.endswith("\n\n"):
            t = t[:-2]
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.endswith("\n```"):
            t = t[:-4]
        elif t.endswith("```"):
            t = t[:-3]
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="本地 clean_dir")
    ap.add_argument("--book", required=True, help="语雀知识库 ID")
    ap.add_argument("--progress", required=True, help="progress.json 账本")
    ap.add_argument("--token-env", default="TOKEN_L91")
    args = ap.parse_args()

    token = load_token(args.token_env)
    nodes = json.load(open(args.progress, encoding="utf-8"))["nodes"]
    seg_files = {k: v["segments"] for k, v in nodes.items() if len(v.get("segments") or []) > 1}
    if not seg_files:
        print("本地无需分片的文件 → 跳过（0 项）")
        return 0

    print("分片文件 %d 个，开始逐片回拉比对…" % len(seg_files), flush=True)
    bad = []
    for p, segs in sorted(seg_files.items()):
        fp = os.path.join(args.root, p)
        local = open(fp, "rb").read().decode("utf-8", errors="replace")
        chunks, fetch_err = [], None
        for s in segs:
            try:
                d = api(token, BASE, "GET", "/repos/%s/docs/%s" % (args.book, s["doc_id"]))
            except Exception as ex:          # noqa: BLE001
                fetch_err = "拉取 %s 失败: %s" % (s["title"], ex)
                break
            chunks.append(strip_shard((d.get("data") or {}).get("body") or ""))

        if fetch_err:
            print("  ❌ %s: %s" % (p, fetch_err), flush=True)
            bad.append(p)
            continue

        # A. 拼回文本逐字符比
        joined = "".join(chunks)
        if joined == local:
            print("  ✅ %s: %d 片 · 拼回文本与本地逐字符相等（%d 字符）"
                  % (p, len(segs), len(local)), flush=True)
            continue

        # B. JSON 数组回拼逐条比
        if p.lower().endswith(".json"):
            got, err = [], None
            for i, c in enumerate(chunks):
                try:
                    v = json.loads(c)
                except Exception as ex:      # noqa: BLE001
                    err = "第 %d 片不是合法 JSON（%s）" % (i + 1, ex)
                    break
                got.extend(v if isinstance(v, list) else [v])
            if err is None:
                try:
                    want = json.loads(local)
                except Exception as ex:      # noqa: BLE001
                    want, err = None, "本地文件不是合法 JSON（%s）" % ex
                if err is None and got == want:
                    print("  ✅ %s: %d 片 · 数组回拼 %d 条与本地逐条相等"
                          % (p, len(segs), len(got)), flush=True)
                    continue
                if err is None:
                    err = "数组回拼 %d 条 ≠ 本地 %d 条" % (
                        len(got), len(want) if want is not None else -1)
            print("  ❌ %s: %d 片 · %s（拼回文本 %d 字符 vs 本地 %d 字符）"
                  % (p, len(segs), err, len(joined), len(local)), flush=True)
        else:
            print("  ❌ %s: %d 片 · 拼回文本 %d 字符 ≠ 本地 %d 字符"
                  % (p, len(segs), len(joined), len(local)), flush=True)
        bad.append(p)

    if bad:
        print("\n❌ 分片内容校验失败 %d 个: %s" % (len(bad), bad))
        return 1
    print("\n✅ 分片内容零丢失验收 PASS（%d 个文件）" % len(seg_files))
    return 0


if __name__ == "__main__":
    sys.exit(main())