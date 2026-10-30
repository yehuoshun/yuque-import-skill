#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CSDN 抓取（退避重试；判据=响应含 content_views）"""
import sys, time, urllib.request, urllib.error

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

def fetch(url, tries=6):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Referer": "https://blog.csdn.net/",
                "Accept-Language": "zh-CN,zh;q=0.9",
            })
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
                h = data.decode("utf-8", "replace")
                if "content_views" in h:
                    return h
                last = f"no content_views (len={len(h)})"
        except Exception as e:
            last = repr(e)
        time.sleep(3 * (i + 1))
    raise SystemExit(f"FAIL {url}: {last}")

if __name__ == "__main__":
    url = sys.argv[1]
    out = sys.argv[2]
    h = fetch(url)
    open(out, "w", encoding="utf-8").write(h)
    print(f"OK {url} -> {out} ({len(h)} bytes)")
