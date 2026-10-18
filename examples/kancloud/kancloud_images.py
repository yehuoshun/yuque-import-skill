#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""看云图床（box.kancloud.cn 有防盗链，需 Referer）→ 语雀 CDN，并重写 md 引用。"""
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, "/home/admin/.openclaw/workspace/code/yuque-import-skill/scripts")
from yuque_tree_import import load_upload_cfg, upload_image  # noqa: E402

ROOT = "/home/admin/.openclaw/workspace/tmp/programmer-prepares-clean"
MAP = "/home/admin/.openclaw/workspace/tmp/programmer-prepares-img_map.json"
COOKIE = "~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json"
REFERER = "http://www.kancloud.cn/kancloud/a-programmer-prepares"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36",
      "Referer": REFERER}
URL_RE = re.compile(r"https?://box\.kancloud\.cn/[^\s)\"']+")


def main():
    cfg = load_upload_cfg(os.path.expanduser(COOKIE))
    if not cfg:
        print("cookie 不可用", file=sys.stderr)
        sys.exit(1)
    mp = {}
    if os.path.exists(MAP):
        mp = json.load(open(MAP, encoding="utf-8"))
    files = [os.path.join(dp, f) for dp, _, fns in os.walk(ROOT) for f in fns if f.endswith(".md")]
    rewritten = 0
    for fp in sorted(files):
        t = open(fp, encoding="utf-8").read()
        urls = URL_RE.findall(t)
        if not urls:
            continue
        new = t
        for u in sorted(set(urls)):
            if u not in mp:
                try:
                    req = urllib.request.Request(u, headers=UA)
                    data = urllib.request.urlopen(req, timeout=60).read()
                except Exception as e:  # noqa: BLE001
                    print("下载失败 %s : %s" % (u, e))
                    continue
                tmp = "/tmp/_kc_img%s" % os.path.splitext(u)[1][:5]
                open(tmp, "wb").write(data)
                cdn = None
                for attempt in range(10):
                    cdn = upload_image(cfg["cookie"], cfg["ctoken"], "25689388", tmp)
                    if cdn:
                        break
                    print("上传重试 %d %s" % (attempt + 1, u))
                    time.sleep(30)
                os.remove(tmp)
                if not cdn:
                    print("上传失败 %s" % u)
                    continue
                mp[u] = cdn
                json.dump(mp, open(MAP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                print("图片 -> %s" % cdn[:70])
                time.sleep(1)
            if u in mp:
                new = new.replace(u, mp[u])
                rewritten += 1
        if new != t:
            open(fp, "w", encoding="utf-8").write(new)
    print("重写处数: %d | img_map: %d" % (rewritten, len(mp)))


if __name__ == "__main__":
    main()