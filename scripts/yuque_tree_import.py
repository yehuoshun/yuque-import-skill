#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语雀知识库全量目录导入（通用版）
本地目录树 → 语雀知识库：文件夹=TITLE 节点（toc），文件=文档（DOC），
节点顺序 = DFS 先序、层内目录+文件按名称混排。

用法:
  python3 yuque_tree_import.py --root /path/to/dir --book <book_id> [--token-env TOKEN_L91]
  python3 yuque_tree_import.py --root ... --book ... --dry        # 只打印节点清单
  python3 yuque_tree_import.py --root ... --book ... --test 6     # 只导入前 6 个节点

特性:
  - 断点续传: progress.json 记账（默认输出到 --progress 指定路径），中断后重跑自动跳过已完成
  - 每节点落盘一次: 中断最多丢 1 个节点（血泪教训: 批量落盘会丢一批节点+挂错父级）
  - 限流重试: 429/5xx 指数退避
  - 内容格式: .md 原样 / .cs → ```csharp / 其余 → ``` 纯文本
  - 超限自动处理: 二进制文件→占位说明; 文本超 3.4MB→自动截断+注记(语雀 body 上限 4MB)
"""
import argparse, json, os, sys, time, urllib.request, urllib.error

def load_token(env):
    t = os.environ.get(env)
    if t:
        return t
    # 兜底: 从 ~/.openclaw/secrets/credentials.env 读 export <env>="..."
    p = os.path.expanduser("~/.openclaw/secrets/credentials.env")
    if os.path.exists(p):
        for line in open(p):
            if line.startswith(f"export {env}="):
                return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"找不到 token: 设置环境变量 {env} 或写入 credentials.env")

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

def walk(root):
    nodes = []
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if os.path.isdir(p):
            nodes.append((p, True))
            nodes.extend(walk(p))
        else:
            nodes.append((p, False))
    return nodes

def fmt_content(path):
    ext = os.path.splitext(path)[1].lower()
    raw = open(path, "rb").read()
    size = len(raw)
    # 二进制检测: NUL 字节或无效 UTF-8 比例过高 → 占位说明(乱码文本化会膨胀超限且无意义)
    try:
        text = raw.decode("utf-8")
        binary = "\x00" in text or sum(1 for _ in raw if _ > 127) / max(size, 1) > 0.9
    except UnicodeDecodeError:
        binary = True
    if binary:
        return "<!-- 二进制文件 %d MB, 跳过内容导入(语雀 body 上限 4MB), 原文件见 GitHub -->\n" % (size // 1048576)
    if ext == ".md":
        body = text
    elif ext == ".cs":
        body = "```csharp\n" + text + "\n```"
    else:
        body = "```\n" + text + "\n```"
    # 超限自动截断(留 20% 余量给 JSON 转义膨胀, 实测 3MB 内安全)
    if len(body.encode("utf-8")) > 3_400_000:
        keep = 3_300_000
        body = body[:keep] + "\n\n<!-- 超限截断: 原文件 %d MB 超语雀 4MB body 上限, 仅导入前部 -->\n" % (size // 1048576)
    return body

def find_node(toc, parent_uuid, title=None, doc_id=None):
    for n in toc:
        if n.get("parent_uuid") != parent_uuid:
            continue
        if title is not None and n.get("title") == title:
            return n
        if doc_id is not None and n.get("doc_id") == doc_id:
            return n
    return None

def load_prog(path):
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return {"nodes": {}}

def save_prog(prog, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    json.dump(prog, open(tmp, "w"), ensure_ascii=False)
    os.replace(tmp, path)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--book", required=True, help="语雀知识库 ID")
    ap.add_argument("--base", default="https://www.yuque.com/api/v2")
    ap.add_argument("--token-env", default="TOKEN_L91")
    ap.add_argument("--progress", required=True, help="进度文件路径,如 ./progress.json")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--test", type=int, default=0, help="只导前 N 个节点(试水)")
    args = ap.parse_args()

    token = load_token(args.token_env)
    rels = [(os.path.relpath(p, args.root), d) for p, d in walk(args.root)]
    print(f"节点总数: {len(rels)} (目录 {sum(1 for _, d in rels if d)} / 文件 {sum(1 for _, d in rels if not d)})", flush=True)

    if args.dry:
        for rel, is_dir in rels[:50]:
            print(("DIR " if is_dir else "FILE"), rel)
        sys.exit(0)
    if args.test:
        rels = rels[: args.test]
        print(f"[TEST] 只导前 {args.test} 个节点", flush=True)

    prog = load_prog(args.progress)
    stats = {"dir": 0, "doc": 0, "skip": 0, "fail": []}
    for rel, is_dir in rels:
        if rel in prog["nodes"]:
            stats["skip"] += 1
            continue
        parent_rel = os.path.dirname(rel)
        parent = prog["nodes"].get(parent_rel) if parent_rel else None
        parent_uuid = parent.get("uuid") if parent else None
        if parent_rel and parent is None:
            stats["fail"].append((rel, "缺父节点映射"))
            continue
        try:
            if is_dir:
                toc = api(token, args.base, "PUT", f"/repos/{args.book}/toc", {
                    "action": "appendNode", "action_mode": "child",
                    "type": "TITLE", "title": os.path.basename(rel),
                    **({"target_uuid": parent_uuid} if parent_uuid else {}),
                })["data"]
                n = find_node(toc, parent_uuid, title=os.path.basename(rel))
                if not n:
                    raise RuntimeError("TITLE 节点未在返回目录中找到")
                prog["nodes"][rel] = {"type": "dir", "uuid": n["uuid"]}
                stats["dir"] += 1
            else:
                body = fmt_content(os.path.join(args.root, rel))
                created = api(token, args.base, "POST", f"/repos/{args.book}/docs", {
                    "title": os.path.basename(rel), "format": "markdown", "body": body,
                })
                doc_id = created["data"]["id"]
                toc = api(token, args.base, "PUT", f"/repos/{args.book}/toc", {
                    "action": "appendNode", "action_mode": "child",
                    "type": "DOC", "doc_ids": [doc_id],
                    **({"target_uuid": parent_uuid} if parent_uuid else {}),
                })["data"]
                n = find_node(toc, parent_uuid, doc_id=doc_id)
                if not n:
                    raise RuntimeError("DOC 节点未挂载成功")
                prog["nodes"][rel] = {"type": "doc", "uuid": n["uuid"], "doc_id": doc_id}
                stats["doc"] += 1
        except Exception as e:
            stats["fail"].append((rel, str(e)[:150]))
            time.sleep(1)
        save_prog(prog, args.progress)  # 每节点落盘一次(防中断丢批)
        if (stats["dir"] + stats["doc"]) % 25 == 0:
            print(f"  进度: 目录{stats['dir']} 文档{stats['doc']} 跳过{stats['skip']} 失败{len(stats['fail'])}", flush=True)

    print("=== 完成 ===", json.dumps(stats, ensure_ascii=False), flush=True)
    for rel, err in stats["fail"][:10]:
        print("FAIL:", rel, "→", err, flush=True)

if __name__ == "__main__":
    main()