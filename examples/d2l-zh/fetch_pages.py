#!/usr/bin/env python3
"""抓取 zh.d2l.ai 全站页面（只用于重建 numref/cite 编号与标题 oracle）。"""
import json, os, re, sys, time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://zh.d2l.ai/"
OUT = os.environ.get("SITE_OUT", os.path.join(HERE, "site"))
nav = json.load(open(os.environ.get("NAV_JSON", os.path.join(HERE, "d2l_nav.json"))))
os.makedirs(OUT, exist_ok=True)

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

def fetch(path):
    dst = os.path.join(OUT, path.replace("/", "__"))
    if os.path.exists(dst) and os.path.getsize(dst) > 5000:
        return path, "skip"
    for attempt in range(5):
        try:
            req = urllib.request.Request(BASE + path, headers={"User-Agent": UA})
            data = urllib.request.urlopen(req, timeout=60).read()
            open(dst, "wb").write(data)
            time.sleep(0.2)
            return path, f"ok {len(data)}"
        except Exception as e:
            time.sleep(2 * (attempt + 1))
    return path, "FAIL"

paths = [u for u, t in nav]
with ThreadPoolExecutor(max_workers=4) as ex:
    for p, st in ex.map(fetch, paths):
        if st.startswith("FAIL"):
            print("FAIL", p, flush=True)
print("done", len(paths))