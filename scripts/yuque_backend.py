#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语雀操作后端（2026-11-07）：MCP 与「直连 v2 HTTP」双通道

为什么有它:
  小说模块原先写死走 mcporter + yuque-mcp，等于强制装 MCP。实际上这些操作
  （建库/建文档/读 TOC/改 TOC）v2 OpenAPI 全都有，只要一个 token 就能干。
  现在两条路都能走，谁方便用谁。

选择顺序:
  1. --transport / 环境变量 YUQUE_TRANSPORT = http | mcp | auto（默认 auto）
  2. auto: mcporter 可用且能解析到 yuque-mcp → mcp；否则有 token → http；都没有 → 报错说清怎么补

HTTP 模式的边界:
  - 建库 / 建文档 / 读 TOC / 改 TOC：只要 token（X-Auth-Token）
  - 分组（stack）只有 Web API（cookie + ctoken）能干，token 不行；
  - 重要（2026-11-12 实测）：语雀的分组映射**只在建库那一刻建立**。
    库一旦建在"未分组"状态，事后没有任何接口能补（PUT /api/mine/book_stack/move
    对这类库返回 200 但不生效，PUT /api/books/{id} 的 stack_id 只是冗余列，界面不认）。
    所以要进分组，必须在建库时就带 stack_id：`yuque_create_repo(..., stack_id=xxx)`
    会走 Web API（POST /api/books 带 stack_id）。cookie 缺失时退化成 v2 建库（进默认/未分组）。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yuque_tree_import import load_token, resolve_token  # noqa: E402

API = "https://www.yuque.com/api/v2"
WEB = "https://www.yuque.com/api"

# ---- cookie 配置自动发现 ----
# 历史包袱：默认值曾写死 ~/.openclaw/... 这个 Linux 路径，本机（Windows）不存在，
# 于是 _cookie_cfg() 永远返回 None、移动分组被静默跳过，库全落在未分组。
# 现在按 "环境变量 → 工作区 config/ → 仓库内 config/ → 旧 openclaw 路径" 顺序找。
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # code/yuque-import-skill
WORKSPACE_DIR = os.path.dirname(os.path.dirname(SKILL_DIR))                  # DeepSeekWorkSpace
DEFAULT_COOKIE_CONFIG = os.path.join(WORKSPACE_DIR, "config", "yuque_cookies.txt")
COOKIE_CONFIG_CANDIDATES = [
    DEFAULT_COOKIE_CONFIG,
    os.path.join(WORKSPACE_DIR, "config", "yuque_cookie.json"),
    os.path.join(SKILL_DIR, "config", "config.json"),
    "~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json",
]
MCP_WORKDIR = os.environ.get("MCP_WORKDIR") or os.path.expanduser("~/.openclaw/workspace")

_MODE = None          # 解析后的 'mcp' | 'http'
_MCP_READY = None     # mcporter 是否可用（缓存）
_LOGIN = None         # HTTP 模式下的 login 缓存


# ---------------------------------------------------------------- 传输层选择
def _mcporter_ready():
    global _MCP_READY
    if _MCP_READY is not None:
        return _MCP_READY
    exe = shutil.which("mcporter")
    if not exe:
        _MCP_READY = False
        return False
    try:
        r = subprocess.run([exe, "list"], capture_output=True, text=True, timeout=45, cwd=MCP_WORKDIR)
        out = ((r.stdout or "") + (r.stderr or "")).lower()
        _MCP_READY = "yuque" in out
    except Exception:  # noqa: BLE001
        _MCP_READY = False
    return _MCP_READY


def _has_token():
    tok, _ = resolve_token()
    return bool(tok)


def mode():
    """返回 'mcp' 或 'http'"""
    global _MODE
    if _MODE:
        return _MODE
    want = (os.environ.get("YUQUE_TRANSPORT") or "auto").strip().lower()
    if want in ("mcp", "http"):
        _MODE = want
        return _MODE
    if _mcporter_ready():
        _MODE = "mcp"
    elif _has_token():
        _MODE = "http"
    else:
        raise SystemExit(
            "两种通道都不可用：\n"
            "  · MCP 通道：没装 mcporter 或没配 yuque-mcp\n"
            "  · HTTP 通道：没有语雀 token（补法见 README「首次配置」）\n"
            "不想装 MCP 就只补 token —— YUQUE_TRANSPORT=http 可强制走直连。"
        )
    return _MODE


# ---------------------------------------------------------------- MCP 通道
def _mcporter_call(tool, args_dict, timeout=60, retries=1):
    args = json.dumps(args_dict, ensure_ascii=False)
    output = ""
    for attempt in range(max(1, retries)):
        result = subprocess.run(
            ["mcporter", "call", f"yuque-mcp.{tool}", "--args", args],
            capture_output=True, text=True, timeout=timeout, cwd=MCP_WORKDIR,
        )
        output = result.stdout.strip() or result.stderr.strip()
        if "MCP error" in output:
            return {"error": output[:300]}
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            m = re.search(r"(\{.*\}|\[.*\])", output, re.S)
            if m:
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    pass
        if attempt < retries - 1:
            time.sleep(2)
    return {"error": f"mcporter 输出无法解析: {output[:200]}"}


# ---------------------------------------------------------------- HTTP 通道
def _api(method, path, payload=None, retries=4, base=API, auth=True):
    """v2 API（token）；错误不抛异常，返回 {'error': ...} 交给上层重试/报错"""
    url = base + path
    data = json.dumps(payload).encode() if payload is not None else None
    token = load_token() if auth else None
    for i in range(retries):
        req = urllib.request.Request(url, data=data, method=method)
        if token:
            req.add_header("X-Auth-Token", token)
        if payload is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            if e.code in (429, 500, 502, 503, 504) and i < retries - 1:
                time.sleep(2 ** i * 1.5 + 1)
                continue
            return {"error": f"HTTP {e.code}: {body}"}
        except Exception as e:  # noqa: BLE001
            if i < retries - 1:
                time.sleep(2 ** i * 1.5 + 1)
                continue
            return {"error": f"{type(e).__name__}: {e}"}
    return {"error": "retries exhausted"}


def _web_api(cookie_cfg, method, url, payload=None, retries=4):
    data = json.dumps(payload).encode() if payload is not None else None
    for i in range(retries):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Cookie", cookie_cfg["cookie"])
        if cookie_cfg.get("ctoken"):
            req.add_header("X-Csrf-Token", cookie_cfg["ctoken"])
        if payload is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and i < retries - 1:
                time.sleep(2 ** i * 1.5 + 1)
                continue
            return {"error": f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"}
        except Exception as e:  # noqa: BLE001
            if i < retries - 1:
                time.sleep(2 ** i * 1.5 + 1)
                continue
            return {"error": f"{type(e).__name__}: {e}"}
    return {"error": "retries exhausted"}


def login():
    """从 token 反查 login（不依赖写死的用户名）"""
    global _LOGIN
    if _LOGIN:
        return _LOGIN
    d = _api("GET", "/user")
    if isinstance(d, dict) and d.get("data"):
        _LOGIN = d["data"].get("login") or d["data"].get("name")
    if not _LOGIN:
        raise SystemExit(f"取账号信息失败（token 无效？）: {str(d)[:200]}")
    return _LOGIN


def login_or_none():
    """能拿到 login 就给，拿不到（没 token/网络不通）返回 None——MCP 通道用"""
    try:
        return login()
    except SystemExit:
        return None


def _slugify(name):
    s = re.sub(r"[^0-9a-zA-Z]+", "-", name).strip("-").lower()
    return s[:60] or None


def _cookie_cfg(path=None):
    """读 cookie/ctoken。两种格式都认：
    1) JSON：{"cookie": "...", "ctoken": "..."}（CI 里 workdir/cookie.json 就是这种）
    2) 纯文本：一行或多行 Cookie 串（本机 config/yuque_cookies.txt 这种，ctoken 从中提取）
    查找顺序：显式参数 → YUQUE_COOKIE_CONFIG → COOKIE_CONFIG_CANDIDATES。
    """
    explicit = path or os.environ.get("YUQUE_COOKIE_CONFIG")
    for p in ([explicit] if explicit else []) + COOKIE_CONFIG_CANDIDATES:
        if not p:
            continue
        p = os.path.expanduser(p)
        if not os.path.isfile(p):
            continue
        try:
            raw = open(p, encoding="utf-8").read()
        except Exception:  # noqa: BLE001
            continue
        if p.lower().endswith(".json"):
            try:
                cfg = json.loads(raw)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(cfg, dict) and cfg.get("cookie"):
                return cfg
            continue
        cookie = " ".join(x.strip() for x in raw.splitlines() if x.strip())
        if cookie.lower().startswith("cookie:"):
            cookie = cookie.split(":", 1)[1].strip()
        if "yuque_ctoken" not in cookie and "_yuque_session" not in cookie:
            continue
        m = re.search(r"yuque_ctoken=([^;\s]+)", cookie)
        return {"cookie": cookie, "ctoken": m.group(1) if m else None}
    return None


# ---------------------------------------------------------------- HTTP 版各操作
def _http_create_repo(name, description, slug=None, public=0, login_name=None, stack_id=None):
    """建库。给了 stack_id 且能读到 cookie 时走 Web API（POST /api/books 带 stack_id）——
    语雀的分组映射只在建库那一刻建立，事后再也补不上（见模块头注释）。"""
    slug = slug or _slugify(name)
    if stack_id:
        cfg = _cookie_cfg()
        if cfg:
            body = {"name": name, "type": "Book", "public": int(public),
                    "description": description or "", "stack_id": int(stack_id)}
            if slug:
                body["slug"] = slug
            d = _web_api(cfg, "POST", f"{WEB}/books", body)
            if isinstance(d, dict) and d.get("data"):
                return d["data"]
            return d
    body = {"name": name, "description": description or "", "public": int(public),
            "type": "Book"}
    if slug:
        body["slug"] = slug
    d = _api("POST", f"/users/{login_name or login()}/repos", body)
    if isinstance(d, dict) and d.get("data"):
        return d["data"]
    return d


def _stack_of(stacks, book_id):
    """在 book_stacks 返回里找某库当前所在的分组；找不到（未分组/读取失败）返回 None"""
    data = stacks.get("data") if isinstance(stacks, dict) else stacks
    for s in data or []:
        if not isinstance(s, dict):
            continue
        for b in s.get("books") or []:
            if str(b.get("id")) == str(book_id):
                return s
    return None


def _http_update_stack(book_id, stack_id, cookie_config=None):
    cfg = _cookie_cfg(cookie_config)
    if not cfg:
        return {"success": False, "skipped": True,
                "reason": "HTTP 模式移动分组需要 cookie/ctoken（token 无此能力），已跳过"}
    for attempt in range(10):
        if attempt:
            time.sleep(20)
        _web_api(cfg, "PUT", f"{WEB}/mine/book_stack/move",
                 {"targetStackId": int(stack_id), "targetBookIds": [int(book_id)]})
        time.sleep(1.3)                      # web API 限 1 QPS，别刷进风控
        stacks = _web_api(cfg, "GET", f"{WEB}/mine/book_stacks")
        if not isinstance(stacks, dict) or "error" in stacks:
            continue                         # 读失败别误判，下一轮重试
        s = _stack_of(stacks, book_id)
        if s and str(s.get("id")) == str(stack_id):
            return {"success": True, "stack": s.get("name")}
        if attempt == 0 and not s:
            # 库还在"未分组"且 move 没反应 → 语雀不会给已建好的库补映射，重试 10 轮纯属白等
            return {"success": False, "reason": (
                "语雀接口无法给已建好的未分组库补分组：分组映射只在建库时建立，"
                "move 对这类库返回 200 但不生效。请改用建库时带 stack_id"
                "（yuque_create_repo 的 stack_id 参数），或到语雀界面手动拖拽")}
    return {"success": False, "reason": "验证失败：库尚未落到目标分组（稍后重试或手动拖）"}


# ---------------------------------------------------------------- 统一入口
def call(tool, args_dict, timeout=60, retries=1):
    """工具名 → 当前通道。返回结构与 yuque-mcp 一致（调用点不用改）。"""
    m = mode()
    if m == "mcp":
        # MCP 的 yuque_create_repo 要求 login 是字符串：没传就先用 token 反查（拿不到就交回让 MCP 报错）
        if tool == "yuque_create_repo" and not (args_dict or {}).get("login"):
            args_dict = dict(args_dict or {})
            lg = login_or_none()
            if lg:
                args_dict["login"] = lg
        return _mcporter_call(tool, args_dict, timeout=timeout, retries=retries)

    a = args_dict or {}
    if tool == "yuque_create_repo":
        d = _http_create_repo(a.get("name", ""), a.get("description", ""),
                              slug=a.get("slug"), public=a.get("public", 0),
                              login_name=a.get("login"), stack_id=a.get("stack_id"))
        return d if isinstance(d, dict) else {"error": str(d)[:300]}
    if tool == "yuque_update_book_stack":
        return _http_update_stack(a.get("book_id"), a.get("stack_id"), a.get("cookie_config"))
    if tool == "yuque_create_doc":
        d = _api("POST", f"/repos/{a.get('book_id')}/docs",
                 {"title": a.get("title", ""), "body": a.get("body", ""),
                  "format": a.get("format", "markdown"), "public": int(a.get("public", 0))})
        return d.get("data") if isinstance(d, dict) and d.get("data") else d
    if tool == "yuque_get_toc":
        d = _api("GET", f"/repos/{a.get('book_id')}/toc")
        return d.get("data") if isinstance(d, dict) and "data" in d else d
    if tool == "yuque_update_toc":
        payload = {k: v for k, v in a.items() if k != "book_id"}
        return _api("PUT", f"/repos/{a.get('book_id')}/toc", payload)
    return {"error": f"未知操作: {tool}"}


def describe():
    """给人看的当前通道说明（doctor 用）"""
    try:
        m = mode()
    except SystemExit as e:
        return "none", str(e)
    if m == "mcp":
        return m, "mcporter + yuque-mcp"
    return m, "v2 HTTP 直连（只需 token）"


if __name__ == "__main__":
    m, why = describe()
    print(f"transport = {m} ({why})")