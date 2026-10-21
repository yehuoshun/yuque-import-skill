#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""幽灵文档检查（2026-10-21 起成为验收第 5 查，老板拍板）

「幽灵」= 知识库里真实存在的 doc 本体，但 TOC 里没有它（挂没上去 / 挂上去又被清掉）。
危害：库容量被占、搜索里能搜到、`docs total` 与 TOC DOC 数对不上 —— 而路径验收、
分片验收**全都拦不住**它。

两个常见来源（2026-10-21 rea d0067ba 双库各中 1 个，见 references 坑 49）：
  ① 断点残留：`kill -9` / 重启那一刻 `POST /docs` 已成功，但 progress 账本还没落盘
  ② 重试双写：创建响应超时/异常 → 脚本重试 → 服务端其实已经建好了

用法:
    python3 scripts/yuque_check_ghosts.py --book <book_id> [--toc <toc.json>] [--delete]

输出: `docs total` / `TOC DOC 数` / 幽灵清单（id + 标题 + word_count + created_at）
退出码: 0 = 无幽灵；1 = 有幽灵

--toc 不给就现拉 `GET /repos/{book}/toc`；--delete 会把幽灵逐个 DELETE 并回查 404。
⚠️ 删前脚本会打印「TOC 里是否有同名 DOC」供人工确认（同名 ≠ 同一条目，见坑 10）；
   正式删除建议先不带 --delete 跑一遍看清单。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yuque_tree_import import api, load_token  # noqa: E402

BASE = "https://www.yuque.com/api/v2"


def fetch_all_docs(token, book):
    """逐页拉全部 doc（GET /repos/{book}/docs，limit=100）"""
    out, offset = [], 0
    while True:
        d = api(token, BASE, "GET", f"/repos/{book}/docs?limit=100&offset={offset}")
        data = d.get("data") or []
        out += data
        if len(data) < 100:
            break
        offset += 100
    return out


def fetch_toc(token, book):
    d = api(token, BASE, "GET", f"/repos/{book}/toc")
    return d.get("data") or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True)
    ap.add_argument("--toc", help="已有的 toc.json（没有就现拉）")
    ap.add_argument("--delete", action="store_true", help="删除幽灵 doc（默认只报）")
    args = ap.parse_args()

    token = load_token("TOKEN_L91")
    if args.toc:
        toc = json.load(open(args.toc))["data"]
    else:
        toc = fetch_toc(token, args.book)
    toc_doc_ids = {n["doc_id"] for n in toc if n.get("type") == "DOC"}

    docs = fetch_all_docs(token, args.book)
    ghost = [d for d in docs if d["id"] not in toc_doc_ids]

    print(f"[ghost] book={args.book}")
    print(f"[ghost] docs total = {len(docs)} (meta 口径)")
    print(f"[ghost] TOC DOC    = {len(toc_doc_ids)}")
    print(f"[ghost] 幽灵       = {len(ghost)}")

    # TOC 里的标题集合，供人工确认「同名已有一份」
    toc_titles = {}
    for n in toc:
        if n.get("type") == "DOC":
            toc_titles.setdefault(n["title"], []).append(n["doc_id"])

    for g in ghost:
        t = g.get("title")
        same = toc_titles.get(t) or []
        flag = f"（TOC 已有同名 doc_id={same}，删前确认）" if same else "（⚠️ TOC 无同名，勿盲删）"
        print(f"  - id={g['id']}  {t!r}  words={g.get('word_count')}  "
              f"created={g.get('created_at')}  {flag}")

    if ghost and args.delete:
        for g in ghost:
            try:
                api(token, BASE, "DELETE", f"/repos/{args.book}/docs/{g['id']}")
                chk = None
                try:
                    api(token, BASE, "GET", f"/repos/{args.book}/docs/{g['id']}")
                    chk = "仍可访问 ❌"
                except RuntimeError as e:
                    chk = "404 ✅" if "404" in str(e) else f"回查异常: {str(e)[:60]}"
                print(f"[delete] {g['id']} → 200, 回查 {chk}")
            except RuntimeError as e:
                print(f"[delete] {g['id']} → 失败: {str(e)[:120]}")
        docs2 = fetch_all_docs(token, args.book)
        print(f"[ghost] 清理后 docs total = {len(docs2)}（应 == TOC DOC {len(toc_doc_ids)}）")

    return 1 if ghost else 0


if __name__ == "__main__":
    sys.exit(main())