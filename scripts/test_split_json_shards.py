#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_split_json_shards.py — JSON 分片切分回归单测（2026-10-17 加）
================================================================
背景：`_split_json_list` 曾把 `_json_text(cur, start, idx)` 里的**文件级绝对下标**
当成段内下标用，导致第 2 片起正文整段丢失（只留 `[\\n\\n]` 空壳）。
legado 的 `sources/b778fe6b.json`（20.9MB）实测只进去 0.79MB。
本测试断言：**切分后再拼回去，必须与原数组逐条相等**（内容零丢失）。

不联网：只调 fmt_content / split_semantic 纯函数。

用法:
    python3 test_split_json_shards.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yuque_tree_import as Y  # noqa: E402

LIMIT = 4096


def _items_from_segments(segs):
    """把 fmt_content 产出的分片正文（```json 围栏 + 尾注）还原成条目列表。"""
    out = []
    for _suffix, body in segs:
        t = body.strip()
        assert t.startswith("```json"), "分片应带 ```json 围栏"
        t = t[len("```json"):]
        t = t.rsplit("```", 1)[0]                      # 掐掉围栏尾巴
        t = t.split("<!-- 分段", 1)[0]                 # 掐掉尾注
        out.extend(json.loads(t))
    return out


# ---------- 测试 1：多片数组，拼回来必须逐条相等 ----------
items = [{"bookSourceName": "源%d" % i, "bookSourceUrl": "https://e%d.com/" % i,
          "blob": "x" * 300} for i in range(120)]
segs = [("", "```json\n" + json.dumps(items, ensure_ascii=False, indent=2) + "\n```")]
raw = json.dumps(items, ensure_ascii=False, indent=2)
assert len(raw.encode()) > LIMIT, "构造数据要超限才会分片"

parts, mode = Y.split_semantic(raw, LIMIT, ".json")
assert mode == "JSON 条目边界", mode
assert len(parts) > 3, "应切成多片，实际 %d" % len(parts)
for i, (s, _d) in enumerate(parts):
    assert s not in ("[\n\n]", "[\n]", ""), "第 %d 片是空壳（bug 复现）" % (i + 1)
    json.loads(s)                                   # 每片都是合法 JSON
got = []
for s, _d in parts:
    got.extend(json.loads(s))
assert got == items, "拼回来与原数组不等 → 内容丢失"
print("✅ 测试 1：%d 条目 → %d 片，逐条拼回完全一致" % (len(items), len(parts)))

# ---------- 测试 2：fmt_content 端到端（含围栏 + 尾注） ----------
with tempfile.TemporaryDirectory() as td:
    fp = os.path.join(td, "big.json")
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    segs = Y.fmt_content(fp, None, LIMIT)
assert len(segs) > 3, "应多片，实际 %d" % len(segs)
assert all(b.strip() for _s, b in segs), "不能有空分片"
assert _items_from_segments(segs) == items, "fmt_content 分片丢内容"
print("✅ 测试 2：fmt_content 端到端还原 %d 条目 / %d 片" % (len(items), len(segs)))

# ---------- 测试 3：单条自身超限 → 单独成段且不切破 ----------
big = [{"bookSourceName": "huge", "blob": "y" * (LIMIT * 2)},
       {"bookSourceName": "small", "blob": "z" * 50}]
parts3, _ = Y.split_semantic(json.dumps(big, ensure_ascii=False), LIMIT, ".json")
assert len(parts3) == 2, "超大单条应单独成段，实际 %d 片" % len(parts3)
assert "单条超限" in parts3[0][1], parts3[0][1]
assert json.loads(parts3[0][0]) == big[0], "超限单条内容被破坏"
assert json.loads(parts3[1][0]) == [big[1]], "后续正常条目内容被破坏"
print("✅ 测试 3：单条超限单独成段，内容完整")

# ---------- 测试 4：不超限 → 单片原样 ----------
raw4 = json.dumps([{"a": 1}], ensure_ascii=False)
assert Y.split_semantic(raw4, LIMIT, ".json")[1] == "JSON 条目边界"
with tempfile.TemporaryDirectory() as td:
    fp = os.path.join(td, "small.json")
    open(fp, "w", encoding="utf-8").write(raw4)
    assert len(Y.fmt_content(fp, None, LIMIT)) == 1
print("✅ 测试 4：未超限不分片")

print("\n🎉 全部 4 项测试通过")