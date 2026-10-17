#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yuque_verify_shards.py — 分片文档「内容零丢失」验收（2026-10-17 加）
====================================================================
为什么需要它：`yuque_import_verify.py` 只验『路径映射』（节点在不在、分片号连不连续），
**不看分片正文**。2026-10-17 发现 `_split_json_list` 有 bug（绝对下标切段内列表 → 第 2 片起正文全丢），
legado 4 个库、rea 4 个库、kairisei-ma-ch 1 个库全部中招，而路径验收全 PASS 没拦住。
本脚本补上这一层：**把语雀上的分片正文拉回来拼好，跟本地文件逐条/逐字符比对**。

用法:
    python3 scripts/yuque_verify_shards.py --root <clean_dir> --book <book_id> --progress <progress.json>

判定:
  - .json 且按「JSON 条目边界」切 → 逐片 json.loads、拼回、与本地数组 `==`
  - 其余（行边界/单条超限裸对象）→ 逐片剥围栏与尾注后拼回，与本地文本逐字符 `==`
退出码: 0 = 全 PASS；1 = 有文件不一致（会列出）
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yuque_tree_import import api, load_token  # noqa: E402

BASE = "https://www.yuque.com/api/v2"


def strip_shard(body):
    """去掉 ```lang 围栏 + 尾部 `<!-- 分段 -->` 注记，还原该片正文。"""
    t = body.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        t = t.rsplit("```", 1)[0]
    return t.split("<!-- 分段", 1)[0]


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
        raw_local = open(fp, "rb").read()
        chunks = []
        for s in segs:
            d = api(token, BASE, "GET", "/repos/%s/docs/%s" % (args.book, s["doc_id"]))
            chunks.append(strip_shard((d.get("data") or {}).get("body") or ""))

        if p.lower().endswith(".json"):
            got = []
            broken = False
            for c in chunks:
                try:
                    v = json.loads(c)
                except Exception as e:
                    broken = True
                    break
                got.extend(v if isinstance(v, list) else [v])   # 「单条超限」片是裸对象
            if not broken:
                want = json.loads(raw_local.decode("utf-8"))
                ok = got == want
                detail = "拼回 %d 条 / 本地 %d 条" % (len(got), len(want))
            else:
                ok, detail = False, "有分片不是合法 JSON（%s）" % e
        else:
            text = "".join(chunks)
            want = raw_local.decode("utf-8", errors="replace")
            ok = text == want
            detail = "拼回 %d 字符 / 本地 %d 字符（逐字符 %s）" % (
                len(text), len(want), "相等" if ok else "不等")
        print("  %s %s: %d 片 · %s" % ("✅" if ok else "❌", p, len(segs), detail), flush=True)
        if not ok:
            bad.append(p)

    if bad:
        print("\n❌ 分片内容校验失败 %d 个: %s" % (len(bad), bad))
        return 1
    print("\n✅ 分片内容零丢失验收 PASS（%d 个文件）" % len(seg_files))
    return 0


if __name__ == "__main__":
    sys.exit(main())