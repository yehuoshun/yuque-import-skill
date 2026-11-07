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
  - 把库移进分组（stack）：语雀只有 Web API（cookie + ctoken），token 干不了；
    cookie 缺失时跳过并提示，不阻断导入（库先落在默认分组，回头手动拖一下即可）
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
DEFAULT_COOKIE_CONFIG = "~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json"
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
    p = os.path.expanduser(path or os.environ.get("YUQUE_COOKIE_CONFIG") or DEFAULT_COOKIE_CONFIG)
    if not os.path.isfile(p):
        return None
    try:
        cfg = json.load(open(p, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return cfg if cfg.get("cookie") else None


# ---------------------------------------------------------------- HTTP 版各操作
def _http_create_repo(name, description, slug=None, public=0, login_name=None):
    body = {"name": name, "description": description or "", "public": int(public),
            "type": "Book"}
    slug = slug or _slugify(name)
    if slug:
        body["slug"] = slug
    d = _api("POST", f"/users/{login_name or login()}/repos", body)
    if isinstance(d, dict) and d.get("data"):
        return d["data"]
    return d


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
        time.sleep(3)
        stacks = _web_api(cfg, "GET", f"{WEB}/mine/book_stacks")

        def find(o):
            if isinstance(o, dict):
                if o.get("id") == int(stack_id):
                    return o
                for v in o.values():
                    r = find(v)
                    if r:
                        return r
            elif isinstance(o, list):
                for v in o:
                    r = find(v)
                    if r:
                        return r
            return None

        s = find(stacks)
        books = s.get("books", []) if isinstance(s, dict) else []
        if any(str(b.get("id")) == str(book_id) for b in books):
            return {"success": True, "stack": s.get("name")}
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
                              login_name=a.get("login"))
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