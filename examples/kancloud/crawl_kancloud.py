#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《程序员的自我修养》(kancloud) → clean 树

看云 SEO 副本：div.seo > div.content = **markdown 源码**（HTML 转义）→ unescape 即落盘。
目录：124 篇（20 个主章 + 子节），主章清单取自书首页的目录链接。
"""
import html as H
import json
import os
import re
import sys
import time
import urllib.request

from bs4 import BeautifulSoup

BASE = "http://www.kancloud.cn/kancloud/a-programmer-prepares/"
OUT = "/home/admin/.openclaw/workspace/tmp/programmer-prepares-clean"
CACHE = "/home/admin/.openclaw/workspace/tmp/pp-cache"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120 Safari/537.36"}

MAIN_IDS = [78160, 78161, 78171, 78177, 78185, 78188, 78190, 78193, 78198, 78200,
            78203, 78207, 78215, 78218, 78233, 78235, 78237, 78241, 78243, 78281]


def fetch(pid):
    path = os.path.join(CACHE, "%d.html" % pid)
    if os.path.exists(path) and os.path.getsize(path) > 5000:
        return open(path, encoding="utf-8", errors="replace").read()
    req = urllib.request.Request(BASE + str(pid), headers=UA)
    h = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    open(path, "w", encoding="utf-8").write(h)
    time.sleep(0.4)
    return h


def extract(h):
    s = BeautifulSoup(h, "html.parser")
    seo = s.select_one("div.seo")
    c = seo.select_one("div.content") if seo else None
    if not c:
        return None, None
    title = s.title.get_text().split("·")[0].strip() if s.title else ""
    body = c.decode_contents()
    body = H.unescape(body)
    lines = [l.rstrip() for l in body.splitlines()]
    # 去首尾空行 + 去掉统一左缩进
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if lines:
        indents = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
        cut = min(indents) if indents else 0
        lines = [l[cut:] if len(l) > cut else l for l in lines]
    md = "\n".join(lines)
    md = re.sub(r"\n{4,}", "\n\n\n", md).strip() + "\n"
    return title, md


def main():
    os.makedirs(CACHE, exist_ok=True)
    toc = json.load(open("/tmp/kc_toc.json", encoding="utf-8"))
    ids = [int(x["id"]) for x in toc]
    names = {int(x["id"]): x["title"] for x in toc}
    print("总篇数:", len(ids))

    import shutil
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)

    # 分组：主章 → 自己的目录
    groups = []
    cur = None
    for pid in ids:
        if pid in MAIN_IDS:
            cur = {"main": pid, "title": names[pid], "subs": []}
            groups.append(cur)
        elif cur is not None:
            cur["subs"].append(pid)

    ok = miss = 0
    for gi, g in enumerate(groups, 1):
        mtitle = re.sub(r'[/\\:*?"<>|]', "-", g["title"])
        gdir = os.path.join(OUT, "%02d-%s" % (gi, mtitle))
        os.makedirs(gdir, exist_ok=True)
        entries = [(g["main"], "%02d-%s" % (gi, mtitle), True)]
        for si, pid in enumerate(g["subs"], 1):
            st = re.sub(r'[/\\:*?"<>|]', "-", names[pid])
            entries.append((pid, "%02d.%d-%s" % (gi, si, st), False))
        for pid, fname, is_main in entries:
            try:
                h = fetch(pid)
                title, md = extract(h)
            except Exception as e:  # noqa: BLE001
                print("ERR %d %s" % (pid, e))
                miss += 1
                continue
            if md is None:
                print("!! 无正文 %d %s" % (pid, names[pid]))
                miss += 1
                continue
            if not md.strip() or len(md.strip()) < 3:
                # 原页正文为空（看云里有几个空篇）→ 用标题占位，避免语雀空文档
                md = "# %s\n" % names[pid]
            open(os.path.join(gdir, fname + ".md"), "w", encoding="utf-8").write(md)
            ok += 1
            print("%-8s %-52s %6d chars" % (("MAIN" if is_main else "sub"), os.path.join("%02d-%s" % (gi, mtitle), fname + ".md"), len(md)))
    print("完成 ok=%d miss=%d" % (ok, miss))


if __name__ == "__main__":
    main()