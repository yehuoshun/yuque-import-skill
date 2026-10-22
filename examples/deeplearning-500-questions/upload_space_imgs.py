#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""空格文件名图片单独传 CDN 并替换引用。

为什么需要它：`scripts/yuque_rewrite_images.py` 为支持 `![alt](path "title")` 写法，
对 markdown 图片做了 `raw.split(None, 1)` —— **文件名里带空格**时会把路径截断
（`img/ch8/Mask R-CNN-01.png` → `img/ch8/Mask`）→ 判成本地缺失、整条漏传。
本脚本扫出「本地真实存在、且路径含空格」的图片引用，直接 `upload_image` 传 CDN
并替换成 CDN URL（替换后是 https → 主脚本会自动跳过）。

用法:
  python3 upload_space_imgs.py <root> <img_map.json> [--user-id 25689388] [--dry]

跑完再跑主脚本 `yuque_rewrite_images.py`（两者共用同一个 img_map.json，断点续传）。
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "scripts"))
from yuque_tree_import import load_upload_cfg, upload_image  # noqa: E402

MD_RE = re.compile(r'(!\[[^\]]*\]\()((?:[^()]|\([^()]*\))*)(\))')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("img_map")
    ap.add_argument("--user-id", default="25689388")
    ap.add_argument("--throttle", type=float, default=3.0)
    ap.add_argument("--cookie-config",
                    default="~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    root = os.path.abspath(a.root)
    cfg = load_upload_cfg(a.cookie_config)
    if not cfg and not a.dry:
        print("cookie 不可用，退出", file=sys.stderr)
        sys.exit(1)
    mp = json.load(open(a.img_map, encoding="utf-8")) if os.path.exists(a.img_map) else {}

    n = 0
    for dp, _, fns in os.walk(root):
        for fn in sorted(fns):
            if not fn.endswith(".md"):
                continue
            fp = os.path.join(dp, fn)
            text = open(fp, encoding="utf-8", errors="replace").read()
            base = os.path.dirname(fp)

            def sub(m):
                nonlocal n
                raw = m.group(2)
                if " " not in raw or raw.startswith(("http://", "https://", "data:")):
                    return m.group(0)
                p = os.path.normpath(os.path.join(base, raw))
                if not os.path.exists(p):
                    return m.group(0)
                key = os.path.relpath(p, root)
                if a.dry:
                    print("  [dry] 空格引用:", key)
                    n += 1
                    return m.group(0)
                if key not in mp:
                    url = upload_image(cfg["cookie"], cfg["ctoken"], a.user_id, p)
                    if not url:
                        print("  上传失败:", key, file=sys.stderr)
                        return m.group(0)
                    mp[key] = url
                    json.dump(mp, open(a.img_map, "w", encoding="utf-8"), ensure_ascii=False)
                    print("上传", key, "->", url[:70])
                    time.sleep(a.throttle)
                n += 1
                return m.group(1) + mp[key] + m.group(3)

            out = MD_RE.sub(sub, text)
            if out != text and not a.dry:
                open(fp, "w", encoding="utf-8").write(out)
    print("空格引用处理数:", n, "| img_map 条目:", len(mp))


if __name__ == "__main__":
    main()