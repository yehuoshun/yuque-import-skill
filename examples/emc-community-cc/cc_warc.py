#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""站点整体下线时的兜底抓取器：从 Common Crawl 的 WARC 里还原原页 HTML。

场景（2026-10-18 EMC 中文支持论坛《SAN 管理入门系列》实战）：
  源站社区页 302 到厂商新站 + Akamai 403，archive.org 又被墙 →
  用 Common Crawl（index.commoncrawl.org / data.commoncrawl.org，免 key）取历史快照。

用法:
  python3 cc_warc.py --pages pages.txt --out ./raw [--prefix community.emc.com/docs/DOC-160] [--collections CC-MAIN-2019-47,CC-MAIN-2019-39]

pages.txt 每行一个「原始 URL」；输出 raw/<末段>.html
"""
import argparse, gzip, json, os, subprocess, sys, time, zlib

COLLINFO = "https://index.commoncrawl.org/collinfo.json"
INDEX = "https://index.commoncrawl.org/{coll}-index"
DATA = "https://data.commoncrawl.org/"


def curl(url, extra=None, timeout=40):
    cmd = ["curl", "-sS", "--max-time", str(timeout)] + (extra or []) + [url]
    return subprocess.run(cmd, capture_output=True).stdout


def curl_retry(url, tries=4, timeout=40):
    for i in range(tries):
        out = curl(url, timeout=timeout)
        if out.strip():
            return out
        time.sleep(2 + 2 * i)
    return b""


def cdindex(coll, url, match_type=None, limit=None):
    """查询某 collection 的索引；返回 list[dict]；'No Captures' → []；查询失败 → None"""
    q = INDEX.format(coll=coll) + "?url=" + url + "&output=json"
    if match_type:
        q += "&matchType=" + match_type
    if limit:
        q += "&limit=%d" % limit
    raw = curl_retry(q).decode("utf-8", "replace").strip()
    if not raw:
        return None
    if raw.startswith("{") and "No Captures" in raw:
        return []
    out = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out or None


def fetch_record(rec):
    off, ln = int(rec["offset"]), int(rec["length"])
    raw = curl(DATA + rec["filename"], ["-H", "Range: bytes=%d-%d" % (off, off + ln - 1)], timeout=120)
    for dec in (gzip.decompress, lambda r: zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(r)):
        try:
            return dec(raw)
        except Exception:
            pass
    return None


def warc_body_html(data):
    p = data.find(b"\r\n\r\n")           # WARC 头
    body = data[p + 4:]
    q = body.find(b"\r\n\r\n")           # HTTP 头
    return body[q + 4:].decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True, help="每行一个原始 URL")
    ap.add_argument("--out", required=True)
    ap.add_argument("--prefix", help="索引 prefix 查询串（如 community.emc.com%%2Fdocs%%2FDOC-160）；给了就一次查全")
    ap.add_argument("--collections", help="逗号分隔的 collection 白名单（默认全量扫描）")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    pages = [l.strip() for l in open(a.pages, encoding="utf-8") if l.strip()]

    colls = [x["id"] for x in json.loads(curl(COLLINFO).decode("utf-8"))]
    if a.collections:
        want = set(a.collections.split(","))
        colls = [c for c in colls if c in want]

    # 1) 收集抓取记录
    hits = {}   # url -> [record]
    if a.prefix:
        want = {"DOC-" + u.rstrip("/").split("DOC-")[-1] for u in pages if "DOC-" in u}
        for c in colls:
            recs = cdindex(c, a.prefix, match_type="prefix", limit=200)
            if not recs:
                continue
            for d in recs:
                if d.get("status") == "200" and any(w in d.get("url", "") for w in want):
                    hits.setdefault(d["url"], []).append(d)
            time.sleep(0.5)
    else:
        for c in colls:
            for u in pages:
                recs = cdindex(c, u.replace("/", "%2F"))
                if not recs:
                    continue
                for d in recs:
                    if d.get("status") == "200":
                        hits.setdefault(u, []).append(d)
            time.sleep(0.5)

    # 2) 逐条取 WARC 记录还原 HTML
    for url, recs in hits.items():
        doc = url.rstrip("/").split("/")[-1] or "index"
        fp = os.path.join(a.out, doc + ".html")
        if os.path.exists(fp) and os.path.getsize(fp) > 5000:
            print(doc, "cached")
            continue
        for r in recs:
            data = fetch_record(r)
            if not data:
                continue
            html = warc_body_html(data)
            if len(html) < 5000:
                continue
            open(fp, "w").write(html)
            print(doc, "OK", r["timestamp"], len(html))
            break
    print("命中 %d / 目标 %d" % (len(hits), len(pages)))


if __name__ == "__main__":
    main()
