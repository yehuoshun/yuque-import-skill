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
  - 超限自动处理: 二进制文件→占位说明; 文本超 512KB(可调 --max-body)→自动切块+注记(默认 512KB, 2026-10-14 老板定: 1MB 语雀端加载慢)
  - 切分策略(2026-10-14 老板定): 按语义边界切, 禁硬拆——JSON 顶层数组按条目边界(每段可解析), 其余按行边界(不切破行); 每段带头部范围注记
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


def web_api(cfg, login, method, url, body=None, retries=4):
    """Web 内部 API 请求(cookie 认证): 图片上传/batchMove 等不在 v2 的能力.
    返回解析后的 JSON; HTTP 429/5xx 指数退避重试."""
    import ssl
    data = json.dumps(body).encode() if body is not None else None
    for i in range(retries):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Cookie", cfg["cookie"])
        req.add_header("x-csrf-token", cfg["ctoken"])
        req.add_header("x-login", login)
        req.add_header("Content-Type", "application/json")
        req.add_header("X-Requested-With", "XMLHttpRequest")
        req.add_header("Origin", "https://www.yuque.com")
        req.add_header("Referer", "https://www.yuque.com/")
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise RuntimeError(f"Web API 认证失败 HTTP {e.code}(cookie/ctoken 过期?): {e.read().decode()[:200]}")
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** i * 1.5 + 1)
                continue
            raise RuntimeError(f"Web API HTTP {e.code}: {e.read().decode()[:200]}")
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(2 ** i * 1.5 + 1)
    raise RuntimeError("web_api retries exhausted")


def batch_move(cfg, login, book, node_uuids, target_uuid):
    """批量移动节点到目标目录下(Web API /api/catalog_nodes/batch, 2026-10-16 老板抓包确认).
    transfer_action 固定 prependChild; 实测(2026-10-16 测试库)服务端是「整体插到目标最前、
    保持传入数组顺序」——直接传 DFS 正序即可, 千万别逆序(逆序会让兄弟/分片顺序反转)."""
    return web_api(cfg, login, "PUT", "https://www.yuque.com/api/catalog_nodes/batch", {
        "batch_action": "batchMove",
        "node_uuids": list(node_uuids),
        "target_uuid": target_uuid,
        "book_id": book,
        "target_book_id": book,
        "transfer_action": "prependChild",
        "insert_to_catalog": True,
    })


def verify_positions(token, base, book, wants, retries=2, label=""):
    """校验节点实际位置: wants = {node_uuid: 期望parent_uuid(None=根)}.
    写路径有副本延迟(坑67), 首次不满足等 10s 重查一次.
    返回未满足的 node_uuid 列表."""
    for i in range(retries):
        toc = api(token, base, "GET", f"/repos/{book}/toc").get("data", [])
        actual = {n["uuid"]: (n.get("parent_uuid") or None) for n in toc}
        bad = [u for u, want in wants.items()
               if actual.get(u) != want or u not in actual]
        if not bad or i == retries - 1:
            return bad
        log(f"    ⏳ {label}: {len(bad)} 节点位置未刷新(副本延迟), 10s 后重查", flush=True)
        time.sleep(10)
    return bad

def log(*args, **kw):
    """带秒级时间戳的输出(2026-10-16): 长任务事后靠日志分析必须能建时间线."""
    kw.setdefault("flush", True)
    print(f"[{time.strftime('%H:%M:%S')}]", *args, **kw)


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

FENCE_LANG = {
    ".json": "json", ".ts": "ts", ".tsx": "tsx", ".js": "js", ".mjs": "js", ".cjs": "js",
    ".vue": "vue", ".py": "python", ".sh": "bash", ".bash": "bash", ".yml": "yaml",
    ".yaml": "yaml", ".css": "css", ".scss": "scss", ".less": "less", ".html": "html",
    ".xml": "xml", ".sql": "sql", ".java": "java", ".go": "go", ".rs": "rust",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp", ".cs": "csharp", ".rb": "ruby",
    ".php": "php", ".kt": "kotlin", ".swift": "swift", ".toml": "toml", ".ini": "ini",
    ".conf": "conf", ".lock": "", ".txt": "", ".log": "",
}


def _human(n):
    return ("%.1f MB" % (n / 1048576)) if n >= 1048576 else ("%d KB" % max(1, round(n / 1024)))


def _first_name(obj):
    """从 JSON 元素里挑一个像名字的字段, 给分段注记用。"""
    if isinstance(obj, dict):
        for k in ("bookSourceName", "name", "title", "id", "key", "url"):
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip().replace("\n", " ")[:40]
    return ""


def _json_text(parts, a, b):
    return "[\n" + ",\n".join(parts[a:b]) + "\n]"


def _json_desc(items, a, b, total):
    nm = _first_name(items[a])
    return "第 %d-%d 个条目（共 %d 个）" % (a + 1, b, total) + (" · 首条「%s」" % nm if nm else "")


def _split_json_list(items, limit):
    """JSON 顶层数组 → 按元素边界切: 每段都是完整条目, 绝不切破记录。"""
    total = len(items)
    parts = [json.dumps(it, ensure_ascii=False, indent=2) for it in items]
    out, cur, n, start = [], [], 0, 0
    for idx, s in enumerate(parts):
        sb = len(s.encode("utf-8")) + 2
        if sb > limit:                                  # 单条自身超限: 不切, 单独成段
            if cur:
                out.append((_json_text(cur, start, idx), _json_desc(items, start, idx, total)))
                cur, n, start = [], 0, idx
            out.append((s, "第 %d 个条目（单条超限）" % (idx + 1)))
            start = idx + 1
            continue
        if cur and n + sb > limit:
            out.append((_json_text(cur, start, idx), _json_desc(items, start, idx, total)))
            cur, n, start = [], 0, idx
        cur.append(s)
        n += sb
    if cur:
        out.append((_json_text(cur, start, total), _json_desc(items, start, total, total)))
    return out


def _split_lines(text, limit):
    """按行边界切分: 绝不切破行（单行自身超限时才硬切该行）。"""
    lines = text.splitlines(keepends=True)
    total = len(lines)
    out, cur, n, start = [], [], 0, 0

    def flush(end):
        out.append(("".join(cur), "第 %d-%d 行（共 %d 行）" % (start + 1, end, total)))

    for idx, ln in enumerate(lines):
        lb = len(ln.encode("utf-8"))
        if lb > limit:                                  # 超长单行: 只能硬切, 罕见
            if cur:
                flush(idx)
                cur, n = [], 0
            p = 0
            while p < len(ln):
                q = p
                while q < len(ln) and len(ln[p:q + 1].encode("utf-8")) <= limit:
                    q += 1
                out.append((ln[p:q], "第 %d 行（超长行切片）" % (idx + 1)))
                p = q
            start = idx + 1
            continue
        if cur and n + lb > limit:
            flush(idx)
            cur, n, start = [], 0, idx
        cur.append(ln)
        n += lb
    if cur:
        flush(total)
    return out


def split_semantic(text, limit, ext):
    """按语义边界切分（2026-10-14 老板：硬拆影响观感）。返回 ([(段文本, 范围描述)], 切分方式)。"""
    if ext == ".json":
        try:
            d = json.loads(text)
        except Exception:
            d = None
        if isinstance(d, list) and d:
            return _split_json_list(d, limit), "JSON 条目边界"
    return _split_lines(text, limit), "行边界"


def fmt_content(path, up=None, max_body=524_288):
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
    lang = FENCE_LANG.get(ext, "")
    if ext == ".md":
        wrap = lambda s: s
    else:
        wrap = lambda s: "```%s\n%s\n```" % (lang, s)
    body = wrap(text)
    # 超限自动分段(留余量给 JSON 转义膨胀): 默认 512KB(老板 2026-10-14 定: 1MB 语雀端加载慢), 可 --max-body 调
    MAX_BODY = max_body
    if len(body.encode("utf-8")) <= MAX_BODY:
        return [("", body)]
    # 语义/行边界切分(2026-10-14 老板: 硬拆影响观感): 不切破行、不切破 JSON 记录
    segs, mode = split_semantic(text, MAX_BODY - 1024, ext)
    out = []
    for i, (s, desc) in enumerate(segs):
        note = "\n\n<!-- 分段 %d/%d · %s · 源文件 %s 超限，按 %s 切分，内容零丢失 -->\n" % (
            i + 1, len(segs), desc, _human(size), mode)
        suffix = " (%d/%d)" % (i + 1, len(segs)) if len(segs) > 1 else ""
        out.append((suffix, wrap(s) + note))
    return out

def find_node(toc, parent_uuid, title=None, doc_id=None):
    want = parent_uuid or ""
    for n in toc:
        if (n.get("parent_uuid") or "") != want:
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
                log(f"    清理残留节点: {title} (parent={pu!r})", flush=True)
            except Exception:
                pass

def create_node(token, base, book, root, rel, is_dir, up, parent_uuid, max_body=524_288, root_only=False):
    """创建并挂载单个节点, 返回 progress 记录块; 失败抛异常。
    root_only=True(batch 模式): 挂载一律挂根(不带 target_uuid), 后续由 batch_move 批量归位。"""
    if is_dir:
        toc = api(token, base, "PUT", f"/repos/{book}/toc", {
            "action": "appendNode", "action_mode": "child",
            "type": "TITLE", "title": os.path.basename(rel),
            **({} if root_only else ({"target_uuid": parent_uuid} if parent_uuid else {})),
        })["data"]
        n = find_node(toc, (None if root_only else parent_uuid), title=os.path.basename(rel))
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
            **({} if root_only else ({"target_uuid": parent_uuid} if parent_uuid else {})),
        })["data"]
        n = find_node(toc, (None if root_only else parent_uuid), doc_id=doc_id)
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

def flush_group(cfg, login, token, base, book, items, parent_uuid, batch_size, parent_label=""):
    """items: [(rel, [uuids...])]; 把全部 uuid 移动到 parent_uuid 下, 保持 DFS 正序.
    batchMove 的 prependChild = 整体插到目标最前且保持数组内顺序(2026-10-16 实测);
    同父多批时若按序逐批 flush, 后批会插到前批前面 → 顺序反转.
    解法: 按 DFS 序切片后「逆序逐片 flush」(最后一片先挂), prepend 叠加后整体正序.
    batchMove 失败/校验未过 → 降级逐节点 v2 移动."""
    all_items = [(rel, u) for rel, uuids in items for u in uuids]
    chunks = [all_items[i:i + batch_size] for i in range(0, len(all_items), batch_size)]
    ok, bad = [], []
    nchunks = len(chunks)
    for ci, chunk in enumerate(reversed(chunks), 1):  # 逆序: 最后一片先挂
        seq = nchunks - ci + 1  # 正序片号(便于人读: 实际挂载顺序是倒序)
        uuids = [u for _, u in chunk]
        tag = f"归位片 {seq}/{nchunks} → {parent_label or parent_uuid[:8]} ({len(chunk)} 节点)"
        t0 = time.time()
        try:
            batch_move(cfg, login, book, uuids, parent_uuid)
        except Exception as e:
            log(f"  ⚠ [batch] {tag}: batchMove 失败({str(e)[:200]}) → 降级单节点; 节点样本: {uuids[:3]}", )
            for rel, u in chunk:
                bad.append((rel, f"batchMove 失败: {str(e)[:200]} (uuid={u}, parent={parent_label or parent_uuid})"))
            continue
        miss = verify_positions(token, base, book, {u: parent_uuid for _, u in chunk}, label=tag)
        if miss:
            missu = set(miss)
            log(f"  ⚠ [batch] {tag}: {len(miss)} 节点位置校验未过 → 降级单节点移动", flush=True)
            for rel, u in chunk:
                if u not in missu:
                    ok.append(rel)
                    continue
                try:
                    api(token, base, "PUT", f"/repos/{book}/toc", {
                        "action": "appendNode", "action_mode": "child",
                        "target_uuid": parent_uuid, "node_uuid": u})
                    ok.append(rel)
                except Exception as e:
                    bad.append((rel, f"{type(e).__name__}: {str(e)[:200]} (移动 uuid={u} → {parent_label or parent_uuid})"))
        else:
            ok.extend(rel for rel, _ in chunk)
        log(f"  ✓ [batch] {tag} ({time.time() - t0:.1f}s)", flush=True)
    return ok, bad

def node_uuids_of(record):
    """progress 记录的全部 TOC 节点 uuid(含分片)。"""
    uuids = [record["uuid"]]
    for s in record.get("segments", [])[1:]:
        uuids.append(s["uuid"])
    return uuids


def rebuild_pending_batches(prog, token, base, book):
    """batch 模式中断恢复: 扫描 progress 已有节点, 实际位置 != 期望父的重新入队.
    返回 {parent_uuid: [(rel, [uuid])]} (只含非根目标)."""
    if not prog["nodes"]:
        return {}
    toc = api(token, base, "GET", f"/repos/{book}/toc").get("data", [])
    actual = {n["uuid"]: (n.get("parent_uuid") or "") for n in toc}
    q = {}
    for rel, rec in prog["nodes"].items():
        parent_rel = os.path.dirname(rel)
        want = (prog["nodes"].get(parent_rel, {}).get("uuid") if parent_rel else None) or ""
        if not want:
            continue  # 根级节点挂根即最终位置
        misplaced = [u for u in node_uuids_of(rec) if actual.get(u, "MISSING") != want]
        if misplaced:
            q.setdefault(want, []).append((rel, misplaced))
    return q


def create_doc_only(token, base, book, root, rel, up, max_body=524_288):
    """官方一次性目录模式(2026-10-16): 只建文档(POST /docs, 语雀自动挂到 TOC 根), 不挂 TOC。
    返回 {type:doc, segments:[{title,slug,doc_id}], doc_id, slug, uuid:''}"""
    segs = fmt_content(os.path.join(root, rel), up, max_body)
    records = []
    for suffix, body in segs:
        title = os.path.basename(rel) + suffix
        created = api(token, base, "POST", f"/repos/{book}/docs",
                      {"title": title, "format": "markdown", "body": body})["data"]
        slug = created.get("slug")
        if not slug:
            raise RuntimeError(f"POST /docs 未返回 slug: {title}")
        sb = body.strip()
        if sb and not sb.startswith(("<!--", "![")):
            wc = created.get("word_count") or 0
            if wc <= 0:
                raise RuntimeError(f"内容校验失败: {title} 发送 {len(body)} 字符但 word_count={wc}")
        records.append({"title": title, "slug": slug, "doc_id": created["id"]})
    return {"type": "doc", "uuid": "", "doc_id": records[0]["doc_id"],
            "slug": records[0]["slug"], "segments": records}


# ---------- 官方 v2 一次性目录模式(2026-10-16) ----------
# 依据官方 OAS(20260722): PUT /api/v2/repos/{book_id} 的 toc 字段 = Markdown 目录树,
# 原文"可利用此字段批量更新知识库的目录"。文档经 POST /repos/{book}/docs 建好后自动挂到 TOC 根,
# 因此"逐文件建文档 + 一次 PUT toc"即可完成整棵树, 无需逐节点 appendNode 或 batchMove。
def md_esc(t):
    """标题原样输出——**不要转义**。
    2026-10-16 实测(一次性库): 语雀目录解析器按最后一个 `](slug)` 切分, 下列恶心标题全部原样正确:
    `x]` / `a]b` / `a](b` / `p[q](r` / `尾]` / `(paren]` / `】中文】` / `a\\b`(7/7 ✅)。
    反而 `\\[`/`\\]`(反斜杠转义) 与 `&#91;`(HTML 实体) 会被当字面量写进标题 → 标题变脏。
    """
    return t


def build_toc_md(root, prog, excludes, token=None, base=None, book=None):
    """按本地树 DFS 序(目录在前/各自按名排序)生成 Markdown 目录树。

    slug 兜底（2026-10-16 elinux 实战坑）：混合流程下（先跑 `--test N`（非 toc-md）建几个文献，
    再全量 --toc-md）测试阶段落的账目只有 uuid/doc_id 没有 slug → 直拼目录树 KeyError: 'slug'。
    这里缺 slug 时按 doc_id 回查 API 补上。
    """
    out = []
    _slug_cache = {}

    def _slug_of(doc_id, title):
        if doc_id in _slug_cache:
            return _slug_cache[doc_id]
        if not (token and book):
            raise RuntimeError(f"账目缺 slug 且无 token 回查: {title}")
        d = api(token, base, "GET", f"/repos/{book}/docs/{doc_id}")["data"]
        _slug_cache[doc_id] = d["slug"]
        return d["slug"]

    def rec_dir(absdir, depth, relprefix):
        names = sorted(os.listdir(absdir))
        dirs = [n for n in names if os.path.isdir(os.path.join(absdir, n))]
        files = [n for n in names if not os.path.isdir(os.path.join(absdir, n))]
        for name in dirs:
            p = os.path.join(absdir, name)
            if p in excludes:
                continue
            rel = f"{relprefix}/{name}" if relprefix else name
            out.append((depth, f"- [{md_esc(name)}]()"))
            rec_dir(p, depth + 1, rel)
        for name in files:
            p = os.path.join(absdir, name)
            if p in excludes:
                continue
            rel = f"{relprefix}/{name}" if relprefix else name
            node = prog["nodes"].get(rel)
            if not node:
                raise RuntimeError(f"缺少文档记录, 无法生成目录: {rel}")
            segs = node.get("segments") or [{"title": name, "slug": node.get("slug"),
                                              "doc_id": node.get("doc_id")}]
            for s in segs:
                slug = s.get("slug") or _slug_of(s.get("doc_id"), s.get("title") or name)
                out.append((depth, f"- [{md_esc(s['title'])}]({slug})"))

    rec_dir(root, 0, "")
    return "\n".join("  " * d + line for d, line in out) + "\n"


def toc_path_map(toc):
    by = {n["uuid"]: n for n in toc}
    paths = {}
    for n in toc:
        parts, cur = [], n
        while cur:
            parts.append(cur["title"])
            cur = by.get(cur.get("parent_uuid") or "")
        paths[n["uuid"]] = "/".join(reversed(parts))
    return paths


def expected_paths(root, prog, excludes):
    """本地树 → 期望的 TOC 路径集合(分片文件按 seg 标题展开)。"""
    want = {}

    def rec_dir(absdir, relprefix):
        for name in sorted(os.listdir(absdir)):
            p = os.path.join(absdir, name)
            if p in excludes:
                continue
            rel = f"{relprefix}/{name}" if relprefix else name
            if os.path.isdir(p):
                want[rel] = "TITLE"
                rec_dir(p, rel)
            else:
                node = prog["nodes"].get(rel)
                if not node:
                    continue
                segs = node.get("segments") or [{"title": name}]
                for s in segs:
                    want[f"{relprefix}/{s['title']}" if relprefix else s["title"]] = "DOC"

    rec_dir(root, "")
    return want


def backfill_and_verify(token, base, book, prog, root, excludes):
    """PUT toc 后回读一次: 回填 uuid 到账本 + 结构核对。返回 (缺失路径列表, TOC 节点数)。"""
    toc = api(token, base, "GET", f"/repos/{book}/toc")["data"]
    paths = toc_path_map(toc)
    got = {}
    for n in toc:
        got.setdefault(paths[n["uuid"]], []).append(n)
    want = expected_paths(root, prog, excludes)
    missing = [p for p in want if p not in got]
    for rel, node in prog["nodes"].items():
        if node.get("type") == "dir":
            ns = got.get(rel) or []
        else:
            segs = node.get("segments") or []
            parent = os.path.dirname(rel)
            for s in segs:
                wp = f"{parent}/{s['title']}" if parent else s["title"]
                ns2 = got.get(wp) or []
                if ns2:
                    s["uuid"] = ns2[0]["uuid"]
            first = segs[0]["title"] if segs else os.path.basename(rel)
            ns = got.get(f"{parent}/{first}" if parent else first) or []
        if ns:
            node["uuid"] = ns[0]["uuid"]
    return missing, len(toc)


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
    ap.add_argument("--max-body", type=int, default=524_288, help="单文档 body 上限(字节), 超限自动切块; 默认 512KB(2026-10-14 老板定: 1MB 语雀端加载慢)")
    ap.add_argument("--pend-retries", type=int, default=3, help="失败静置重试最大轮数(超出则记 fail 跳过)")
    ap.add_argument("--batch-mode", action="store_true", help="批处理模式(2026-10-16): 节点统一挂根+攒批 batchMove 到目标目录, 规避高频子树挂载积压(坑67); 需 cookie 有效")
    ap.add_argument("--toc-md", action="store_true", help="官方一次性目录模式(2026-10-16): 逐文件 POST /docs + 一次 PUT /repos/{id} 设 markdown 目录树(官方 OAS 20260722 能力), 请求数与收尾耗时比 batch 模式低一个数量级")
    ap.add_argument("--batch-size", type=int, default=50, help="batch 模式每批节点数(默认 50)")
    ap.add_argument("--x-login", default="yehuoshun", help="Web API x-login 用户名(batch 模式用)")
    args = ap.parse_args()

    if args.batch_mode and args.toc_md:
        raise SystemExit("--batch-mode 与 --toc-md 互斥, 二选一")
    token = load_token(args.token_env)
    cfg = load_upload_cfg(args.cookie_config)
    if args.batch_mode and not cfg:
        raise SystemExit("--batch-mode 需要 --cookie-config 提供有效 cookie/ctoken(Web API 认证)")
    if cfg:
        log("图片自动上传: 已启用(cookie 就绪)", flush=True)
    else:
        log("图片自动上传: 未启用(无 cookie/ctoken, 图片回退占位说明)", flush=True)
    up = {"cfg": cfg, "user_id": args.user_id} if cfg else None
    # 自身产物防自污染: 账本(及其 .tmp)落在导入树内时排除, 不再被当文档导入
    excludes = set()
    root_abs, prog_abs = os.path.abspath(args.root), os.path.abspath(args.progress)
    if prog_abs.startswith(root_abs + os.sep):
        excludes.add(prog_abs)
        excludes.add(prog_abs + ".tmp")
        log(f"已排除自身账本: {args.progress} (位于导入树内, 防止被当文档导入)", flush=True)
    rels = [(os.path.relpath(p, args.root), d) for p, d in walk(args.root, excludes)]
    log(f"节点总数: {len(rels)} (目录 {sum(1 for _, d in rels if d)} / 文件 {sum(1 for _, d in rels if not d)})", flush=True)

    if args.dry:
        for rel, is_dir in rels[:50]:
            log(("DIR " if is_dir else "FILE"), rel)
        sys.exit(0)
    if args.test:
        rels = rels[: args.test]
        log(f"[TEST] 只导前 {args.test} 个节点", flush=True)

    prog = load_prog(args.progress)
    stats = {"dir": 0, "doc": 0, "skip": 0, "fail": []}
    batch_q = rebuild_pending_batches(prog, token, args.base, args.book) if args.batch_mode else None
    if batch_q:
        tot = sum(len(u) for v in batch_q.values() for _, u in v)
        log(f"[batch] 中断恢复: {tot} 个已记节点待重新归位 (涉及 {len(batch_q)} 个父目录)", flush=True)
        for pu, items in list(batch_q.items())[:10]:
            lbl = os.path.dirname(items[0][0]) or "(根)"
            cnt = sum(len(u) for _, u in items)
            log(f"    - {lbl}: {cnt} 节点", flush=True)

    def do_flush(parent_uuid, items):
        p_label = os.path.dirname(items[0][0]) or "(根)"
        ok_rel, bad = flush_group(cfg, args.x_login, token, args.base, args.book,
                                  items, parent_uuid, args.batch_size, parent_label=p_label)
        if bad:
            stats["fail"].extend(bad)
        return ok_rel

    for rel, is_dir in rels:
        if rel in prog["nodes"]:
            stats["skip"] += 1
            continue
        parent_rel = os.path.dirname(rel)
        record = None
        last_err = None
        if args.toc_md:
            # 官方一次性目录模式: 目录无需建节点(由 markdown 目录树生成), 文件只建文档
            if is_dir:
                record = {"type": "dir", "uuid": "", "title": os.path.basename(rel)}
            else:
                for attempt in range(1, args.pend_retries + 1):
                    try:
                        record = create_doc_only(token, args.base, args.book, args.root, rel, up, args.max_body)
                        break
                    except Exception as e:
                        last_err = f"{type(e).__name__}: {str(e)[:300]} (parent={parent_rel or 'ROOT'})"
                        if attempt < args.pend_retries:
                            wait = args.pend_sleep * attempt
                            log(f"  ⚠ 失败 [{rel}] → {last_err}; 静置 {wait}s 后重试 ({attempt}/{args.pend_retries})", flush=True)
                            time.sleep(wait)
        else:
            parent = prog["nodes"].get(parent_rel) if parent_rel else None
            parent_uuid = parent.get("uuid") if parent else None
            if parent_rel and parent is None:
                stats["fail"].append((rel, "缺父节点映射"))
                continue
            for attempt in range(1, args.pend_retries + 1):
                try:
                    record = create_node(token, args.base, args.book, args.root, rel, is_dir, up, parent_uuid, args.max_body, root_only=args.batch_mode)
                    break
                except Exception as e:
                    last_err = f"{type(e).__name__}: {str(e)[:300]} (parent={parent_rel or 'ROOT'})"
                    if attempt < args.pend_retries:
                        wait = args.pend_sleep * attempt  # 递增: 600/1200/1800 (10/20/30 分钟)
                        log(f"  ⚠ 失败 [{rel}] → {last_err}; 静置 {wait}s 后重试 ({attempt}/{args.pend_retries})", flush=True)
                        time.sleep(wait)
                        # 静置后清理可能残留的同名节点(避免重复创建), 断点续传账本不动
                        cleanup_leftover(token, args.base, args.book, rel, is_dir, parent_uuid)
        if record is None:
            stats["fail"].append((rel, last_err))
            continue
        prog["nodes"][rel] = record
        if record["type"] == "dir":
            stats["dir"] += 1
        else:
            stats["doc"] += 1
        save_prog(prog, args.progress)  # 每节点落盘一次(防中断丢批)
        if not args.batch_mode:
            # 非 batch 模式: 节点在 create_node 内已挂到真实父, 直接计数完成
            pass
        else:
            # batch 模式: 已挂根; 非根节点攒批等待收尾统一归位
            # (同父分批 flush 会因 prependChild 语义乱序, 2026-10-16 实测 → 只攒不中途 flush)
            if parent_uuid:
                batch_q.setdefault(parent_uuid, []).append((rel, node_uuids_of(record)))
        if (stats["dir"] + stats["doc"]) % 25 == 0:
            pend = ""
            if args.batch_mode:
                pend_nodes = sum(len(u) for v in batch_q.values() for _, u in v)
                pend = f" 待归位{pend_nodes}"
            log(f"  进度: 目录{stats['dir']} 文档{stats['doc']} 跳过{stats['skip']}{pend} 失败{len(stats['fail'])}", flush=True)

    # 官方一次性目录模式收尾: 拼 markdown 目录树 → 一次 PUT 设目录 → 回读核对
    if args.toc_md:
        try:
            md = build_toc_md(args.root, prog, excludes, token, args.base, args.book)
        except Exception as e:
            stats["fail"].append(("(toc-md)", f"生成目录树失败: {str(e)[:200]}"))
            md = None
        if md:
            lines = md.splitlines()
            log(f"[toc-md] 目录树: {len(lines)} 行 / {len(md.encode('utf-8'))} 字节 → 一次 PUT /repos/{args.book}", flush=True)
            t0 = time.time()
            try:
                api(token, args.base, "PUT", f"/repos/{args.book}", {"toc": md})
                log(f"[toc-md] PUT 完成 ({time.time() - t0:.1f}s), 回读核对…", flush=True)
                missing, n = backfill_and_verify(token, args.base, args.book, prog, args.root, excludes)
                save_prog(prog, args.progress)
                log(f"[toc-md] TOC {n} 节点; 结构缺失 {len(missing)} 项", flush=True)
                if missing:
                    for p in missing[:20]:
                        log("  缺失:", p)
                    stats["fail"].extend((p, "TOC 结构缺失") for p in missing)
                else:
                    log("[toc-md] 结构核对 PASS ✅", flush=True)
            except Exception as e:
                stats["fail"].append(("(toc-md)", f"PUT toc 失败: {type(e).__name__}: {str(e)[:200]}"))

    # batch 模式收尾: flush 全部剩余批次
    if args.batch_mode:
        for parent_uuid, items in list(batch_q.items()):
            ok_rel = do_flush(parent_uuid, items)
            if ok_rel:
                stats["ok_flush"] = stats.get("ok_flush", 0) + len(ok_rel)
            batch_q.pop(parent_uuid, None)
        log(f"[batch] 归位完成: {stats.get('ok_flush', 0)} 节点确认到位; 失败 {len(stats['fail'])} 项")

    log("=== 完成 ===", json.dumps(stats, ensure_ascii=False), flush=True)
    for rel, err in stats["fail"][:10]:
        log("FAIL:", rel, "→", err)
    if len(stats["fail"]) > 10:
        log(f"  ... 另有 {len(stats['fail']) - 10} 项失败(完整列表见 === 完成 === 的 stats)")

if __name__ == "__main__":
    main()