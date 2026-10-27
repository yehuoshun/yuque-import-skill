#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把导入根目录里 .md 的**本地图片引用** → 语雀 CDN URL 并重写（img_map.json 断点续传）。

支持两种写法（2026-10-17 bilibili-API-collect 实战补）：
  1. markdown：`![alt](相对路径)`
  2. HTML：  `<img src="相对路径" ...>`（**单/双引号都吃**）
     —— VuePress/Docusaurus 类文档站的图几乎都写成 HTML img，
        只认 markdown 的旧脚本会整站漏图（漏了就是一堆裂图）
     —— 单引号形式 `<img src='..'>` 也要吃：2026-10-17 linux-doc 实踩，
        旧正则写死 `src="` → 单引号那条整条漏传（引用留在正文里成裂图）

用法:
  python3 scripts/yuque_rewrite_images.py <clean_dir> <img_map.json> [--throttle 3] [--dry]

约定:
  - 外链（http/https/data:）原样跳过，不下载不替换
  - key = 相对 <clean_dir> 的路径 → url 存 img_map.json，重跑只补未传的
  - 语雀附件接口有账号级限流（连传 ~500 张即 429，见 references 坑 24）→ --throttle 控速；
    失败按 429 三分法处置（classify_429）：Retry-After<=30s 秒级快等重试 / v2 配额退出(码 3) /
    附件无头风控短退避后退出(码 3)——退出前 img_map 已实时落盘，等窗口重跑只补未传的（断点续传）
  - ⚠️ **传图完成判据（2026-10-27 fpb-057 实踩）**：img_map 缓存数 ≥ 本地唯一 key 数 ≠ 传完（
    489≥463 后整树重跑又传 259 张）——**唯一可靠判据 = `--dry` 重跑报「本地缺失 0」**；
    统计口径以 md 引用面为准，别用 key 数对比自欺
  - 退出码：0=完成；3=配额/风控退出（断点已存，reset/自愈后可重跑续传）
  - 脚本跑完请把图片目录从导入根**删干净**，否则每张图会变成独立占位文档（SKILL 硬规则 10）
  - img_map.json 本身也不能留在导入根目录里
  - markdown 图片带 title 的写法 `![alt](path "title")` 也吃（2026-10-18 ucore 实踩：旧版把 path+title 整体当 src → 报本地缺失）
  - `--dry` 如实报「重写 N 处 / 本地缺失 M」不写盘（2026-10-18 修：旧版 dry 短路了缓存填值，统计恒为 0/0/0，
    会让人误判「一张图都没扫到」；datamining-guide 实踩）
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yuque_tree_import import classify_429, load_upload_cfg, upload_image  # noqa: E402

# path 部分允许「一层成对括号」（菜谱/图片命名常见 `石凉粉(冰粉)成品1.jpg`）：
# 旧写法 `[^)]+` 会在第一个 `)` 处截断 → 判成「本地缺失」整条漏传（2026-10-20 HowToCook 实踩，4 处）
MD_RE = re.compile(r'(!\[[^\]]*\]\()((?:[^()]|\([^()]*\))*)(\))')
# 4 组：前缀(含引号) / 引号 / src / 闭合引号——单双引号都能匹配
HTML_RE = re.compile(r'(<img\b[^>]*?\bsrc=)(["\'])([^"\']+)(["\'])')


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

        def resolve(src):
            """本地图 → CDN URL；外链/缺失返回 None（原样保留）"""
            nonlocal skipped
            if src.startswith(("http://", "https://", "data:")):
                skipped += 1
                return None
            p = os.path.normpath(os.path.join(base, src))
            if not os.path.exists(p):
                missing.append((fp, src))
                return None
            key = os.path.relpath(p, args.root)
            if args.dry:
                # 2026-10-18 修：旧版 dry 会把 mp 永远当空 → resolve 恒返回 None →
                # 统计恒为 0/0/0（datamining-guide 实踩，差点误判「一张图都没找到」）
                return "DRY:" + src
            if key not in mp:
                err = {}
                for attempt in range(60):
                    url = upload_image(cfg["cookie"], cfg["ctoken"], args.user_id, p, err_sink=err)
                    if url:
                        mp[key] = url
                        json.dump(mp, open(args.img_map, "w", encoding="utf-8"),
                                  ensure_ascii=False)
                        print("上传 %s -> %s" % (key, url[:60]), flush=True)
                        time.sleep(args.throttle)
                        break
                    code = err.get("code")
                    hdrs = err.get("headers", {})
                    if code == 429:
                        kind = classify_429(hdrs)
                        if kind == "hifreq":
                            ra = int(hdrs.get("retry-after", 1))
                            print("高频限速(Retry-After %ds) 等 %ds 重试: %s" % (ra, ra + 1, key),
                                  flush=True)
                            time.sleep(ra + 1)
                            continue
                        if kind == "quota":
                            reset = hdrs.get("x-ratelimit-reset", "?")
                            print("配额耗尽(reset=%s) 保存断点退出(码3)，窗口开可重跑续传: %s"
                                  % (reset, key), flush=True)
                            json.dump(mp, open(args.img_map, "w", encoding="utf-8"),
                                      ensure_ascii=False)
                            sys.exit(3)
                        # cdn：附件端无头风控（~40 分钟自愈）——短退避 3 次仍失败则退出
                        if attempt < 3:
                            wait = min(5 * (2 ** attempt), 30)
                            print("附件风控(疑似 429 无头) 退避 %ds: %s" % (wait, key), flush=True)
                            time.sleep(wait)
                            continue
                        print("附件风控(疑似 ~40min 自愈) 保存断点退出(码3): %s" % key, flush=True)
                        json.dump(mp, open(args.img_map, "w", encoding="utf-8"),
                                  ensure_ascii=False)
                        sys.exit(3)
                    # 非 429（5xx/网络/其它）：指数退避 8 次，仍失败则记缺失不阻塞全批
                    if attempt < 8:
                        time.sleep(min(5 * (2 ** attempt), 60))
                        continue
                    missing.append((fp, src))
                    print("连续失败放弃(记缺失): %s" % key, file=sys.stderr)
                    break
            return mp.get(key)

        def sub_md(m):
            nonlocal dirty, rewritten
            # markdown 图片可带 title：![alt](path "title") → 只重写 path，title 原样保留
            raw = m.group(2)
            bits = raw.split(None, 1)
            url = resolve(bits[0])
            if url is None:
                return m.group(0)
            tail = (" " + bits[1]) if len(bits) > 1 else ""
            dirty = True
            rewritten += 1
            return "%s%s%s%s" % (m.group(1), url, tail, m.group(3))

        def sub_html(m):
            nonlocal dirty, rewritten
            url = resolve(m.group(3))
            if url is None:
                return m.group(0)
            dirty = True
            rewritten += 1
            return "%s%s%s%s" % (m.group(1), m.group(2), url, m.group(4))

        new = HTML_RE.sub(sub_html, text)   # 先 HTML：<img src> 里不会包含 markdown 语法
        new = MD_RE.sub(sub_md, new)
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
