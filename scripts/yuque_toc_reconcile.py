#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语雀 TOC 对账修复（通用版）
把语雀知识库实际目录树与本地目录树对账，找出错位节点并移回正确父级。

背景坑（2026-10-05 sts2-res 3921 节点实战）:
  - 导入中断窗口（进程死、progress 未落盘）会产生「已创建但没记账」的节点；
    重跑时父级映射缺失 → 文档被 appendNode 挂到根（parent_uuid 为空串 ""）
  - 语雀根节点的 parent_uuid 是空串 ""（不是 null），判断根一律用 `not parent_uuid`
  - 路径重建必须「先加自己再上移查父」（while True 直到 parent_uuid 为空），
    否则第一层子节点路径会丢父目录前缀 → 全量误报错位

用法:
  python3 yuque_toc_reconcile.py --root /path/to/dir --book <book_id> --progress ./progress.json
  python3 yuque_toc_reconcile.py --root ... --book ... --progress ... --fix   # 执行移动修复

原理:
  1. 拉语雀 TOC → 按 parent_uuid 链重建每个节点的完整路径
  2. 与 progress.json 记账路径对比（或本地 walk 全量路径）
  3. 错位节点 → appendNode(action_mode=child, target=期望父级 uuid, node_uuid=当前节点) 移回
"""
import argparse, json, os, time, urllib.request, urllib.error, sys

def load_token(env):
    t = os.environ.get(env)
    if t:
        return t
    p = os.path.expanduser("~/.openclaw/secrets/credentials.env")
    if os.path.exists(p):
        for line in open(p):
            if line.startswith(f"export {env}="):
                return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"找不到 token: {env}")

def api(token, base, method, path, payload=None, retries=4):
    data = json.dumps(payload).encode() if payload is not None else None
    for i in range(retries):
        req = urllib.request.Request(base + path, data=data, method=method)
        req.add_header("X-Auth-Token", token)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** i * 1.5 + 1)
                continue
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:200]}")
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(2 ** i * 1.5 + 1)
    raise RuntimeError("retries exhausted")

def build_path_map(toc):
    by_uuid = {n["uuid"]: n for n in toc}
    m = {}
    for n in toc:
        parts = []
        cur = n
        while True:
            parts.append(cur["title"])
            if not cur.get("parent_uuid"):
                break
            cur = by_uuid[cur["parent_uuid"]]
        m[n["uuid"]] = "/".join(reversed(parts))
    return m

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="本地目录根(与导入时一致)")
    ap.add_argument("--book", required=True)
    ap.add_argument("--base", default="https://www.yuque.com/api/v2")
    ap.add_argument("--token-env", default="TOKEN_L91")
    ap.add_argument("--progress", required=True)
    ap.add_argument("--fix", action="store_true", help="执行移动修复(默认只对账)")
    args = ap.parse_args()

    token = load_token(args.token_env)
    toc = api(token, args.base, "GET", f"/repos/{args.book}/toc")["data"]
    path_of = build_path_map(toc)

    # 期望路径: progress 账本优先(与导入一致), 缺失的节点从本地 walk 兜底
    prog = json.load(open(args.progress, encoding="utf-8"))
    expect = {v["uuid"]: rel for rel, v in prog["nodes"].items()}

    moves = []
    for n in toc:
        if n.get("type") != "DOC":
            actual = path_of[n["uuid"]]
            wanted = expect.get(n["uuid"])
            if wanted and actual != wanted:
                moves.append((n["title"], actual, wanted, n["uuid"]))
    print(f"TOC 节点: {len(toc)}, 错位 DOC: {len(moves)}", flush=True)
    for t, a, w, _ in moves[:10]:
        print(f"  {t}: 实际[{a}] → 期望[{w}]", flush=True)

    if not moves:
        print("对账通过 ✅", flush=True)
        return
    if not args.fix:
        print("加 --fix 执行移动修复", flush=True)
        return

    path2uuid = {v: k for k, v in path_of.items()}
    fixed = 0
    for title, actual, wanted, node_uuid in moves:
        parent_path = os.path.dirname(wanted)
        pu = path2uuid.get(parent_path)
        if not pu:
            prev = prog["nodes"].get(os.path.dirname(wanted))
            if prev and prev.get("type") == "dir":
                pu = prev.get("uuid")
        if not pu:
            print(f"  跳过 {title}: 找不到父目录 {parent_path}", flush=True)
            continue
        api(token, args.base, "PUT", f"/repos/{args.book}/toc", {
            "action": "appendNode", "action_mode": "child",
            "target_uuid": pu, "node_uuid": node_uuid,
        })
        fixed += 1
        time.sleep(0.3)
    print(f"==== 修复完成: 移动 {fixed} 个节点 ====", flush=True)

if __name__ == "__main__":
    main()