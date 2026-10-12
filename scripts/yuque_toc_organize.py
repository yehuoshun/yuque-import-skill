#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语雀 TOC 整理：把平铺文档归入目录分组（2026-10-13 固化，老板「内容全是平铺」反馈）

用法:
  python3 yuque_toc_organize.py --book <id> --plan <plan.json>

plan.json 格式:
{
  "root_docs": ["01-简介.md"],              # 留在根级的文档标题(可选)
  "groups": [
    {"title": "01-Git基础", "docs": ["02-Git是什么.md", "03-Git的诞生.md"]},
    ...
  ]
}

流程: 建 TITLE 分组(根级, sibling 模式防坏节点) → node_uuid 形式把文档移入分组 →
      GET /toc 复查(铁律: 移动后必须重新 GET /toc 验证 parent_uuid, 不信移动响应)。

坑（2026-10-12/13 实踩固化）:
- 根级 TITLE 不带 target_uuid → 坏节点, 挂子静默落根 → 根级分组用 sibling + target_uuid=前一根节点
- doc_ids 形式挂载会无视 target_uuid 落根 → 移动用 node_uuid 形式
- removeNode/appendNode 乐观回显 → 操作后必须 GET /toc 复查
"""
import argparse, json, os, sys, time

sys.path.insert(0, "/home/admin/.openclaw/workspace/code/yuque-import-skill/scripts")
from yuque_tree_import import load_token, api  # noqa: E402

BASE = "https://www.yuque.com/api/v2"


def get_toc(token, book):
    d = api(token, BASE, "GET", f"/repos/{book}/toc")
    return d.get("data", d) if isinstance(d, dict) else d


def toc_index(toc):
    """title→node, uuid→node, 根级节点列表"""
    by_title, by_uuid = {}, {}
    for n in toc:
        by_uuid[n["uuid"]] = n
        by_title.setdefault(n.get("title", ""), []).append(n)
    roots = [n for n in toc if not n.get("parent_uuid")]
    return by_title, by_uuid, roots


def create_root_group(token, book, title, sibling_uuid):
    """根级 TITLE: sibling 模式挂到 sibling_uuid 之后(防坏节点)"""
    d = api(token, BASE, "PUT", f"/repos/{book}/toc", {
        "action": "appendNode", "action_mode": "sibling",
        "type": "TITLE", "title": title,
        "target_uuid": sibling_uuid,
    })
    toc = d.get("data", d) if isinstance(d, dict) else d
    for n in toc:
        # 响应里根节点 parent_uuid 是 null 不是 ""（GET 才是 ""）
        if n.get("type") == "TITLE" and n.get("title") == title and not n.get("parent_uuid"):
            return n
    raise RuntimeError(f"分组创建失败: {title}")


def move_doc(token, book, group_uuid, doc_uuid, title):
    """node_uuid 形式移动文档到分组下"""
    d = api(token, BASE, "PUT", f"/repos/{book}/toc", {
        "action": "appendNode", "action_mode": "child",
        "type": "DOC", "target_uuid": group_uuid, "node_uuid": doc_uuid,
    })
    toc = d.get("data", d) if isinstance(d, dict) else d
    moved = any(n.get("uuid") == doc_uuid and n.get("parent_uuid") == group_uuid for n in toc)
    if not moved:
        raise RuntimeError(f"移动未生效(响应未见): {title}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True)
    ap.add_argument("--plan", required=True)
    args = ap.parse_args()
    plan = json.load(open(args.plan, encoding="utf-8"))
    token = load_token("TOKEN_L91")

    toc = get_toc(token, args.book)
    by_title, by_uuid, roots = toc_index(toc)
    print(f"当前 TOC: {len(toc)} 节点, 根级 {len(roots)}", flush=True)

    # 校验 plan 里文档都存在
    all_docs = [d for g in plan.get("groups", []) for d in g["docs"]] + plan.get("root_docs", [])
    missing = [t for t in all_docs if t not in by_title]
    if missing:
        raise SystemExit(f"plan 文档不存在: {missing}")

    # 根级顺序基准: 最后一个根级节点(移动前)
    last_root = roots[-1]["uuid"] if roots else ""

    created_groups = []
    for g in plan.get("groups", []):
        # 幂等: 根级已有同名 TITLE 则复用(不重复建)
        existing = [n for n in roots if n.get("type") == "TITLE" and n.get("title") == g["title"]]
        if existing:
            node = existing[0]
            print(f"  分组(复用): {g['title']} ({node['uuid']})", flush=True)
        else:
            sibling = created_groups[-1]["uuid"] if created_groups else last_root
            node = create_root_group(token, args.book, g["title"], sibling)
            print(f"  分组: {g['title']} ({node['uuid']})", flush=True)
        created_groups.append(node)  # 复用也要进列表(复查 zip 对齐)
        time.sleep(0.5)
        # 移文档
        for title in g["docs"]:
            doc_node = by_title[title][0]
            if doc_node.get("parent_uuid") == node["uuid"]:
                continue  # 已在分组下
            move_doc(token, args.book, node["uuid"], doc_node["uuid"], title)
            print(f"    → {title}", flush=True)
            time.sleep(0.8)

    # 复查(铁律): 重新 GET /toc
    toc2 = get_toc(token, args.book)
    by_title2, by_uuid2, roots2 = toc_index(toc2)
    ok = True
    for g, node in zip(plan.get("groups", []), created_groups):
        actual = [n for n in toc2 if n.get("parent_uuid") == node["uuid"]]
        want = set(g["docs"])
        got = {n.get("title") for n in actual}
        if got != want:
            ok = False
            print(f"  分组 {g['title']}: 期望 {len(want)} 实际 {len(got)} → 缺 {want-got} 多 {got-want}")
    for t in plan.get("root_docs", []):
        n = by_title2[t][0]
        if n.get("parent_uuid"):
            ok = False
            print(f"  根级文档 {t} 被移动了!")
    if ok:
        print(f"✅ 复查通过: 分组 {len(created_groups)} 个, 文档全部就位, TOC {len(toc2)} 节点")
    else:
        raise SystemExit("❌ 复查失败, 见上方差异")


if __name__ == "__main__":
    main()
