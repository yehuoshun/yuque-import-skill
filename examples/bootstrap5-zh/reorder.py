#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根级节点归位：按站点顺序重排（toc-md 按 Unicode 排序，顺序会乱）

用法: TOKEN_L91=... python3 reorder.py <book_id> "标题1" "标题2" ...
      （标题必须与 TOC 根级 title 完全一致；DOC 的 title 含 .md 后缀）
原理: 先把第一个目标节点 prependNode 到根最前 → 再逐个 appendNode 到「前一个之后」，
     未列出的节点自然漂到后面（不依赖任何固定锚点）。
"""
import json, os, sys, time, urllib.request

BASE = "https://www.yuque.com/api/v2"


def main():
    book = sys.argv[1]
    order = sys.argv[2:]
    assert order, "usage: reorder.py <book_id> <title> [title...]"
    token = os.environ["TOKEN_L91"]

    def api(method, path, body=None):
        req = urllib.request.Request(BASE + path,
                                     data=json.dumps(body).encode() if body else None,
                                     method=method)
        req.add_header("X-Auth-Token", token)
        req.add_header("Content-Type", "application/json")
        for i in range(4):
            try:
                with urllib.request.urlopen(req, timeout=40) as r:
                    return json.loads(r.read().decode())
            except Exception as e:
                print("  retry", i, e)
                time.sleep(2 + i * 3)
        raise RuntimeError(path)

    def toc():
        return api("GET", f"/repos/{book}/toc")["data"]

    nodes = {n["title"]: n for n in toc() if not n.get("parent_uuid")}
    missing = [t for t in order if t not in nodes]
    assert not missing, f"根级找不到: {missing}"
    roots = [n for n in toc() if not n.get("parent_uuid")]
    if roots[0]["title"] != order[0]:
        api("PUT", f"/repos/{book}/toc", {"action": "prependNode", "action_mode": "sibling",
                                          "node_uuid": nodes[order[0]]["uuid"],
                                          "target_uuid": roots[0]["uuid"]})
    for i in range(1, len(order)):
        api("PUT", f"/repos/{book}/toc", {"action": "appendNode", "action_mode": "sibling",
                                          "node_uuid": nodes[order[i]]["uuid"],
                                          "target_uuid": nodes[order[i - 1]]["uuid"]})
        time.sleep(0.3)
    now = [n["title"] for n in toc() if not n.get("parent_uuid")]
    print("NOW:", now)
    print("OK" if now == order else "MISMATCH")


if __name__ == "__main__":
    main()