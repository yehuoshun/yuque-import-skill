#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语雀导入环境自检（新机器/新使用者第一件事跑这个）

用法:
  python3 scripts/yuque_doctor.py            # 只查本地配置，不联网
  python3 scripts/yuque_doctor.py --net      # 额外用 token 调一次 /user 验证可用性
  python3 scripts/yuque_doctor.py --token-env MY_TOKEN

输出:
  ✅/⚠️/❌ 逐项结论 + 缺什么怎么补（Windows / Linux / macOS 都给）
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yuque_tree_import import TOKEN_ENV_FALLBACKS, TOKEN_FILE_CANDIDATES, resolve_token  # noqa: E402

BASE = "https://www.yuque.com/api/v2"


def mask(t):
    return t[:4] + "*" * max(0, len(t) - 8) + t[-4:] if len(t) > 8 else "*" * len(t)


def check_token(env):
    tok, src = resolve_token(env)
    if tok:
        print(f"✅ token: 找到（来源 {src}，{mask(tok)}）")
        return tok
    print("❌ token: 没找到")
    print("   已查环境变量: " + " / ".join([env] + [k for k in TOKEN_ENV_FALLBACKS if k != env]))
    print("   已查文件    : " + "、".join(TOKEN_FILE_CANDIDATES))
    print("   Linux/macOS : export YUQUE_TOKEN=\"<token>\"")
    print("                 或 echo 'export YUQUE_TOKEN=\"<token>\"' >> ~/.openclaw/secrets/credentials.env")
    print("   Windows PS  : $env:YUQUE_TOKEN=\"<token>\"")
    print('                 永久: \'YUQUE_TOKEN="<token>"\' | Add-Content "$env:USERPROFILE\\.openclaw\\secrets\\credentials.env"')
    print("   其他位置    : YUQUE_TOKEN_FILE=<任意文件路径>，或 --token-env <变量名>")
    print("   token 申请  : 语雀 → 个人设置 → Token（https://www.yuque.com/settings/tokens）")
    return None


def check_net(tok):
    if not tok:
        print("⏭️  联网验证: 跳过（没 token）")
        return
    req = urllib.request.Request(f"{BASE}/user")
    req.add_header("X-Auth-Token", tok)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        d = data.get("data") or {}
        print(f"✅ 联网验证: token 可用（账号 {d.get('login') or d.get('name') or '?'}）")
    except Exception as e:  # noqa: BLE001
        print(f"❌ 联网验证失败: {e}（token 可能失效，或网络/代理不通）")


def check_cookie():
    p = os.path.expanduser("~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json")
    if os.path.isfile(p):
        try:
            cfg = json.load(open(p, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            cfg = {}
        ok = bool(cfg.get("cookie") or cfg.get("ctoken"))
        print(("✅" if ok else "⚠️ ") + f" cookie/ctoken: {p}" + ("" if ok else "（文件在但没读到 cookie/ctoken）"))
        return
    print(f"⚠️  cookie/ctoken: 未找到 {p}")
    print("   影响: 仅图片上传 CDN / batch 模式的 TOC 归位；纯 toc-md 导入不需要")
    print("   补法: --cookie-config <你的 config.json>，或按 SKILL.md 抄一份 cookie/ctoken")


def check_novel_path():
    exe = shutil.which("mcporter")
    if not exe:
        print("⚠️  小说链路: 没装 mcporter（小说导入 yuque_novel_import.py 依赖它 + yuque-mcp）")
        print("   补法: npm i -g mcporter，并在 OpenClaw 里配好 yuque-mcp（token 在 MCP 配置里，不读 TOKEN_L91）")
        return
    try:
        r = subprocess.run([exe, "list"], capture_output=True, text=True, timeout=60)
        out = ((r.stdout or "") + (r.stderr or "")).lower()
        has = "yuque" in out
    except Exception:  # noqa: BLE001
        out, has = "", False
    if has:
        print(f"✅ 小说链路: mcporter 已装（{exe}），能看到 yuque 相关的 MCP server")
    else:
        print(f"⚠️  小说链路: mcporter 已装（{exe}），但没解析到 yuque-mcp")
        print("   补法: 在 OpenClaw 里配好 yuque-mcp（token 写在 MCP server 配置里，不读 TOKEN_L91）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token-env", default="TOKEN_L91", help="自定义 token 环境变量名（默认 TOKEN_L91）")
    ap.add_argument("--net", action="store_true", help="用 token 调一次 /user 验证")
    args = ap.parse_args()

    print(f"平台: {sys.platform} | Python {sys.version.split()[0]} | cwd {os.getcwd()}")
    print("-" * 60)
    tok = check_token(args.token_env)
    if args.net:
        check_net(tok)
    check_cookie()
    check_novel_path()
    print("-" * 60)
    if tok:
        print("token 就绪，可直接跑: python3 scripts/yuque_tree_import.py --root <目录> --book <id> --dry")
    else:
        print("先按上面任一方式补 token，再跑同样的命令")
        sys.exit(1)


if __name__ == "__main__":
    main()