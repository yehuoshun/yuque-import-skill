#!/usr/bin/env python3
"""抓 vbird 服务器架设篇全部页面到 pages/ （带缓存，跳过已存在）。"""
import os, sys, time, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
BASE = "http://cn.linux.vbird.org/linux_server/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")
os.makedirs(OUT, exist_ok=True)

urls = [l.strip() for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "links.txt")) if l.strip()]
urls = [u for u in urls if u.startswith(BASE) and u.rstrip('/') != BASE.rstrip('/')]
# 排除旧版说明页
urls = [u for u in urls if not u.endswith(('centos4.php', 'redhat9.php'))]

print(f"待抓 {len(urls)} 页", flush=True)
ok = skip = fail = 0
for i, u in enumerate(urls, 1):
    name = u[len(BASE):]
    fp = os.path.join(OUT, name)
    if os.path.exists(fp) and os.path.getsize(fp) > 500:
        skip += 1
        continue
    for attempt in range(3):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            open(fp, "wb").write(data)
            ok += 1
            break
        except Exception as e:
            if attempt == 2:
                print(f"  FAIL {name}: {e}", flush=True)
                fail += 1
            else:
                time.sleep(2)
    if i % 20 == 0:
        print(f"  进度 {i}/{len(urls)} (ok {ok} skip {skip} fail {fail})", flush=True)
    time.sleep(0.2)
print(f"完成: ok {ok} skip {skip} fail {fail} → {OUT}", flush=True)
