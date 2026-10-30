#!/usr/bin/env python3
"""fpb52 #105 Go语言实战笔记 — 按仓库 README 索引抓 flysnow.org 正文"""
import os, re, time, json, sys, urllib.request

OUT = "/home/admin/.openclaw/workspace/tmp/fpb105/raw"
os.makedirs(OUT, exist_ok=True)

README = "/home/admin/.openclaw/workspace/tmp/go-in-action-notes-3da951a-clean/README.md"

def parse_index():
    """README → [(series, title, url)]"""
    series, out, cur = None, [], None
    for line in open(README, encoding="utf-8"):
        line = line.rstrip("\n")
        m = re.match(r"^##\s+(.+)$", line)
        if m:
            cur = m.group(1).strip()
            continue
        m = re.match(r"^\d+\.\s+\[(.+?)\]\((https?://[^)]+)\)", line.strip())
        if m and cur:
            out.append((cur, m.group(1).strip(), m.group(2).strip()))
    return out

def fetch(url, dest):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
                if len(data) < 3000:
                    raise RuntimeError("too small %d" % len(data))
                open(dest, "wb").write(data)
                return len(data)
        except Exception as e:
            print("   retry %d %s" % (attempt + 1, e))
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("fail " + url)

def main():
    idx = parse_index()
    print("index items:", len(idx))
    man = []
    for i, (series, title, url) in enumerate(idx, 1):
        slug = url.rstrip("/").split("/")[-1]
        dest = os.path.join(OUT, "%02d-%s.html" % (i, slug))
        if os.path.exists(dest) and os.path.getsize(dest) > 3000:
            print("%02d cached %s" % (i, slug))
        else:
            n = fetch(url, dest)
            print("%02d %6d %s" % (i, n, slug))
            time.sleep(1.2)
        man.append({"seq": i, "series": series, "title": title, "url": url, "file": os.path.basename(dest)})
    json.dump(man, open("/home/admin/.openclaw/workspace/tmp/fpb105/manifest.json", "w"),
              ensure_ascii=False, indent=1)
    print("done", len(man))

if __name__ == "__main__":
    main()