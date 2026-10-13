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
  - 超限自动处理: 二进制文件→占位说明; 文本超 1MB(可调 --max-body)→自动切块+注记(默认 1MB: 代码文件硬拆太伤, 2026-10-13 老板定; 后期渲染仍卡再调小)
"""
import argparse, json, os, sys, time, urllib.request, urllib.error, uuid

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}


def upload_image(cookie, ctoken, user_id, path):
    """语雀 Web API 上传图片 → CDN URL。失败返回 None(回退占位说明)."""
    ext = os.path.splitext(path)[1].lower()
    boundary = "----YuqueImport" + uuid.uuid4().hex
    with open(path, "rb") as f:
        data = f.read()
    parts = []
    parts.append(('--' + boundary).encode())
    parts.append(('Content-Disposition: form-data; name="file"; filename="%s"' % os.path.basename(path)).encode())
    parts.append(("Content-Type: image/%s" % ext.lstrip(".")).encode())
    parts.append(b"")
    parts.append(data)
    parts.append(('--' + boundary + '--').encode())
    body = b"\r\n".join(parts)
    url = "https://www.yuque.com/api/upload/attach?attachable_type=User&attachable_id=%s&type=image&ctoken=%s" % (user_id, ctoken)
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)
    req.add_header("Cookie", cookie)
    req.add_header("Referer", "https://www.yuque.com/")
    req.add_header("Origin", "https://www.yuque.com")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode())
        return d.get("data", {}).get("url") or None
    except Exception:
        return None


def load_upload_cfg(cookie_config):
    """读语雀 MCP config.json 的 cookie/ctoken; 失败返回 None(图片回退占位)."""
    try:
        c = json.load(open(os.path.expanduser(cookie_config), encoding="utf-8"))
        if c.get("cookie") and c.get("ctoken"):
            return c
    except Exception:
        pass
    return None

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

def walk(root, excludes=None):
    """同级内目录在前、文件在后，各自按名称排序（Windows 资源管理器习惯）.
    excludes: 绝对路径集合，遍历时跳过（用于排除自身账本/临时文件，防自污染）."""
    excludes = excludes or set()
    nodes = []
    names = sorted(os.listdir(root))
    dirs = [n for n in names if os.path.isdir(os.path.join(root, n))]
    files = [n for n in names if not os.path.isdir(os.path.join(root, n))]
    for name in dirs:
        p = os.path.join(root, name)
        if p in excludes:
            continue
        nodes.append((p, True))
        nodes.extend(walk(p, excludes))
    for name in files:
        p = os.path.join(root, name)
        if p in excludes:
            continue
        nodes.append((p, False))
    return nodes

def fmt_content(path, up=None, max_body=1_000_000):
    """返回 [(标题后缀, body), ...]: 超限文本自动多段拆分, 二进制→占位说明."""
    ext = os.path.splitext(path)[1].lower()
    raw = open(path, "rb").read()
    size = len(raw)
    # 空文件: 语雀 body 必填, 直接占位注释(实遇 free-programming-books 的空 md 撞 422)
    if size == 0:
        return [("", "<!-- 源仓库中该文件为空 -->\n")]
    # 二进制检测: NUL 字节或解码失败 → 二进制。
    # ⚠️ 2026-10-12 删掉 hi-byte>0.9 启发式: 中文 UTF-8 三字节全 >127, 中文密集文本(.md/.cs 注释)比例轻易超 0.9
    #    被误判成二进制 → 占位文档(HowToCook 23 篇/Nulab 12 篇/sts2 45 篇等 10+ 库中招)。
    #    能正常 UTF-8 解码且无 NUL 就是文本; 真二进制(图片/压缩包)由 NUL/解码失败捕获。
    try:
        text = raw.decode("utf-8")
        binary = "\x00" in text
    except UnicodeDecodeError:
        binary = True
    if binary:
        if ext in IMAGE_EXTS and up and up.get("cfg"):
            url = upload_image(up["cfg"]["cookie"], up["cfg"]["ctoken"], up["user_id"], path)
            if url:
                name = os.path.basename(path)
                return [("", "![%s](%s)\n\n<!-- 图片 %d MB 已上传语雀 CDN, 展示见上 -->\n" % (name, url, size // 1048576))]
        return [("", "<!-- 二进制文件 %d MB, 跳过内容导入(语雀 body 上限 4MB), 原文件见 GitHub -->\n" % (size // 1048576))]
    if ext == ".md":
        wrap = lambda s: s
    elif ext == ".cs":
        wrap = lambda s: "```csharp\n" + s + "\n```"
    else:
        wrap = lambda s: "```\n" + s + "\n```"
    body = wrap(text)
    # 超限自动分段(留余量给 JSON 转义膨胀): 默认 1MB(代码硬拆太伤, 老板 2026-10-13 定), 可 --max-body 调
    MAX_BODY = max_body
    if len(body.encode("utf-8")) <= MAX_BODY:
        return [("", body)]
    # 按字符边界切段, 每段(含包装+注记)不超 MAX_BODY
    limit = MAX_BODY - 512
    segs, cur, cur_bytes = [], [], 0
    for ch in text:
        b = len(ch.encode("utf-8"))
        if cur_bytes + b > limit and cur:
            segs.append("".join(cur)); cur, cur_bytes = [], 0
        cur.append(ch); cur_bytes += b
    if cur:
        segs.append("".join(cur))
    out = []
    for i, s in enumerate(segs):
        unit, val = ("MB", round(MAX_BODY / 1048576)) if MAX_BODY >= 1_000_000 else ("KB", round(MAX_BODY / 1024))
        note = "\n\n<!-- 分段 %d/%d: 原文件 %d MB 超 %d%s 阈值, 已拆分为多文档 -->\n" % (i + 1, len(segs), size // 1048576, val, unit)
        suffix = " (%d/%d)" % (i + 1, len(segs)) if len(segs) > 1 else ""
        out.append((suffix, wrap(s) + note))
    return out

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

def cleanup_leftover(token, base, book, rel, is_dir, parent_uuid):
    """静置重试前清理可能残留的同名节点(避免重复创建)。
    只清「目标父下」和「根」的同名节点; 父链其他地方的同名(理论上不可能)不动。"""
    import urllib.request as _u
    title = os.path.basename(rel)
    try:
        d = api(token, base, "GET", f"/repos/{book}/toc")
        toc = d.get("data", [])
    except Exception:
        return
    for n in toc:
        if n.get("title") != title:
            continue
        pu = n.get("parent_uuid") or ""
        if pu == (parent_uuid or "") or pu == "":
            try:
                api(token, base, "PUT", f"/repos/{book}/toc", {
                    "action": "removeNode", "action_mode": "child", "node_uuid": n["uuid"]})
                print(f"    清理残留节点: {title} (parent={pu!r})", flush=True)
            except Exception:
                pass

def create_node(token, base, book, root, rel, is_dir, up, parent_uuid, max_body=1_000_000):
    """创建并挂载单个节点, 返回 progress 记录块; 失败抛异常。"""
    if is_dir:
        toc = api(token, base, "PUT", f"/repos/{book}/toc", {
            "action": "appendNode", "action_mode": "child",
            "type": "TITLE", "title": os.path.basename(rel),
            **({"target_uuid": parent_uuid} if parent_uuid else {}),
        })["data"]
        n = find_node(toc, parent_uuid, title=os.path.basename(rel))
        if not n:
            raise RuntimeError("TITLE 节点未在返回目录中找到")
        return {"type": "dir", "uuid": n["uuid"]}
    segs = fmt_content(os.path.join(root, rel), up, max_body)
    records = []
    for suffix, body in segs:
        title = os.path.basename(rel) + suffix
        created = api(token, base, "POST", f"/repos/{book}/docs", {
            "title": title, "format": "markdown", "body": body,
        })
        doc_id = created["data"]["id"]
        # 单篇内容校验(2026-10-13 老板定): 创建/更新响应都带 word_count,
        # 真实文本正文必须 >0, 否则正文没进去(曾静默丢成占位注释: hi-byte 误判事故)。
        # 占位/图片段(以 <!-- 或 ![ 开头)与纯空白允许 0。
        sb = body.strip()
        if sb and not sb.startswith(("<!--", "![")):
            wc = (created.get("data", {}).get("word_count") or 0)
            if wc <= 0:
                raise RuntimeError(f"内容校验失败: {title} 发送 {len(body)} 字符但 word_count={wc}")
        toc = api(token, base, "PUT", f"/repos/{book}/toc", {
            "action": "appendNode", "action_mode": "child",
            "type": "DOC", "doc_ids": [doc_id],
            **({"target_uuid": parent_uuid} if parent_uuid else {}),
        })["data"]
        n = find_node(toc, parent_uuid, doc_id=doc_id)
        if not n:
            raise RuntimeError("DOC 节点未挂载成功")
        records.append({"uuid": n["uuid"], "doc_id": doc_id, "title": title})
    return {"type": "doc", "uuid": records[0]["uuid"],
            "doc_id": records[0]["doc_id"], "segments": records}

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
    ap.add_argument("--cookie-config", default="~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json", help="语雀 MCP config.json(含 cookie/ctoken), 图片自动上传 CDN 用")
    ap.add_argument("--user-id", default="25689388", help="语雀用户 ID(上传 attachable_id)")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--test", type=int, default=0, help="只导前 N 个节点(试水)")
    ap.add_argument("--pend-sleep", type=float, default=600, help="失败静置基础秒数, 按轮次递增(第n次等待 = pend_sleep×n, 默认 600 → 10/20/30 分钟)")
    ap.add_argument("--max-body", type=int, default=1_000_000, help="单文档 body 上限(字节), 超限自动切块; 默认 1MB=代码文件硬拆太伤(2026-10-13 老板定), 后期渲染仍卡可调小如 200_000")
    ap.add_argument("--pend-retries", type=int, default=3, help="失败静置重试最大轮数(超出则记 fail 跳过)")
    args = ap.parse_args()

    token = load_token(args.token_env)
    cfg = load_upload_cfg(args.cookie_config)
    up = {"cfg": cfg, "user_id": args.user_id} if cfg else None
    if up:
        print("图片自动上传: 已启用(cookie 就绪)", flush=True)
    else:
        print("图片自动上传: 未启用(无 cookie/ctoken, 图片回退占位说明)", flush=True)
    # 自身产物防自污染: 账本(及其 .tmp)落在导入树内时排除, 不再被当文档导入
    excludes = set()
    root_abs, prog_abs = os.path.abspath(args.root), os.path.abspath(args.progress)
    if prog_abs.startswith(root_abs + os.sep):
        excludes.add(prog_abs)
        excludes.add(prog_abs + ".tmp")
        print(f"已排除自身账本: {args.progress} (位于导入树内, 防止被当文档导入)", flush=True)
    rels = [(os.path.relpath(p, args.root), d) for p, d in walk(args.root, excludes)]
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
        record = None
        last_err = None
        for attempt in range(1, args.pend_retries + 1):
            try:
                record = create_node(token, args.base, args.book, args.root, rel, is_dir, up, parent_uuid, args.max_body)
                break
            except Exception as e:
                last_err = str(e)[:150]
                if attempt < args.pend_retries:
                    wait = args.pend_sleep * attempt  # 递增: 600/1200/1800 (10/20/30 分钟)
                    print(f"  ⚠ 失败 [{rel}] → {last_err}; 静置 {wait}s 后重试 ({attempt}/{args.pend_retries})", flush=True)
                    time.sleep(wait)
                    # 静置后清理可能残留的同名节点(避免重复创建), 断点续传账本不动
                    cleanup_leftover(token, args.base, args.book, rel, is_dir, parent_uuid)
        if record is None:
            stats["fail"].append((rel, last_err))
            continue
        if record["type"] == "dir":
            prog["nodes"][rel] = record
            stats["dir"] += 1
        else:
            prog["nodes"][rel] = record
            stats["doc"] += 1
        save_prog(prog, args.progress)  # 每节点落盘一次(防中断丢批)
        if (stats["dir"] + stats["doc"]) % 25 == 0:
            print(f"  进度: 目录{stats['dir']} 文档{stats['doc']} 跳过{stats['skip']} 失败{len(stats['fail'])}", flush=True)

    print("=== 完成 ===", json.dumps(stats, ensure_ascii=False), flush=True)
    for rel, err in stats["fail"][:10]:
        print("FAIL:", rel, "→", err, flush=True)

if __name__ == "__main__":
    main()