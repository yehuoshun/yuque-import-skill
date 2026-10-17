#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把导入根目录里 .md 的**本地图片引用** → 语雀 CDN URL 并重写（img_map.json 断点续传）。

支持两种写法（2026-10-17 bilibili-API-collect 实战补）：
  1. markdown：`![alt](相对路径)`
  2. HTML：  `<img src="相对路径" ...>`
     —— VuePress/Docusaurus 类文档站的图几乎都写成 HTML img，
        只认 markdown 的旧脚本会整站漏图（漏了就是一堆裂图）

用法:
  python3 scripts/yuque_rewrite_images.py <clean_dir> <img_map.json> [--throttle 3] [--dry]

约定:
  - 外链（http/https/data:）原样跳过，不下载不替换
  - key = 相对 <clean_dir> 的路径 → url 存 img_map.json，重跑只补未传的
  - 语雀附件接口有账号级限流（连传 ~500 张即 429，见 references 坑 24）→ --throttle 控速，
    失败自动等 120s 重试（最多 60 轮）
  - 脚本跑完请把图片目录从导入根**删干净**，否则每张图会变成独立占位文档（SKILL 硬规则 10）
  - img_map.json 本身也不能留在导入根目录里
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yuque_tree_import import load_upload_cfg, upload_image  # noqa: E402

MD_RE = re.compile(r'(!\[[^\]]*\]\()([^)]+)(\))')
HTML_RE = re.compile(r'(<img\b[^>]*?\bsrc=")([^"]+)(")')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="导入根目录（clean_dir）")
    ap.add_argument("img_map", help="img_map.json 路径（缓存 + 断点续传）")
    ap.add_argument("--user-id", default="25689388", help="语雀用户 ID（上传 attachable_id）")
    ap.add_argument("--throttle", type=float, default=3.0, help="每张上传后 sleep 秒数（防 429）")
    ap.add_argument("--cookie-config",
                    default="~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json")
    ap.add_argument("--dry", action="store_true", help="只统计，不上传不重写")
    args = ap.parse_args()

    cfg = load_upload_cfg(args.cookie_config)
    if not cfg and not args.dry:
        print("cookie 不可用（--cookie-config 检查），退出", file=sys.stderr)
        sys.exit(1)

    mp = {}
    if os.path.exists(args.img_map):
        mp = json.load(open(args.img_map, encoding="utf-8"))
    print("已有 img_map 缓存条目: %d" % len(mp), flush=True)

    missing, rewritten, skipped = [], 0, 0
    files = []
    for dp, _, fns in os.walk(args.root):
        for fn in fns:
            if fn.endswith(".md"):
                files.append(os.path.join(dp, fn))
    print("扫描到 md 文件: %d" % len(files), flush=True)

    for fp in sorted(files):
        with open(fp, encoding="utf-8", errors="replace") as f:
            text = f.read()
        base = os.path.dirname(fp)
        dirty = False

        def sub(m):
            nonlocal dirty, rewritten, skipped
            pre, src, post = m.group(1), m.group(2), m.group(3)
            if src.startswith(("http://", "https://", "data:")):
                skipped += 1
                return m.group(0)
            p = os.path.normpath(os.path.join(base, src))
            if not os.path.exists(p):
                missing.append((fp, src))
                return m.group(0)
            key = os.path.relpath(p, args.root)
            if key not in mp and not args.dry:
                for attempt in range(60):
                    url = upload_image(cfg["cookie"], cfg["ctoken"], args.user_id, p)
                    if url:
                        mp[key] = url
                        json.dump(mp, open(args.img_map, "w", encoding="utf-8"),
                                  ensure_ascii=False)
                        print("上传 %s -> %s" % (key, url[:60]), flush=True)
                        time.sleep(args.throttle)
                        break
                    print("上传失败(重试%d): %s — 等 120s（疑似限流）" % (attempt + 1, key),
                          flush=True)
                    time.sleep(120)
            if key in mp:
                dirty = True
                rewritten += 1
                return "%s%s%s" % (pre, mp[key], post)
            return m.group(0)

        new = HTML_RE.sub(sub, text)     # 先 HTML：<img src> 里不会包含 markdown 语法
        new = MD_RE.sub(sub, new)
        if dirty and not args.dry:
            with open(fp, "w", encoding="utf-8") as f:
                f.write(new)

    print("完成: 重写 %d 处, 外链跳过 %d, 本地缺失 %d" % (rewritten, skipped, len(missing)),
          flush=True)
    if missing:
        for fp, src in missing[:30]:
            print("  缺失 %s : %s" % (fp, src), file=sys.stderr)
    json.dump(mp, open(args.img_map, "w", encoding="utf-8"), ensure_ascii=False)
    print("img_map 最终条目: %d" % len(mp), flush=True)


if __name__ == "__main__":
    main()
