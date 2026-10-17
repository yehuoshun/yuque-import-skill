#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FreeBSD 使用手册（docs.freebsd.org/zh-cn/books/handbook/）
步骤一：解析侧边栏目录树 → plan.json；抓全站页面 → pages/<slug>.html（带退避重试）。
"""
import re, os, json, time, sys, urllib.request, urllib.error

BASE = "https://docs.freebsd.org/zh-cn/books/handbook/"
ROOT = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(ROOT, "pages")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"}


def fetch(url, tries=6):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(min(2 ** i, 30))
    raise last


def parse_menu(html):
    """侧边栏 <nav id=MenuContents>：只取【顶层 ul 的直接 li】的第一个有文本的 <a> = 顶级节点顺序。
    （v1 用裸正则扫全部 li → 342 条（含各节锚点）错，改用 bs4 按层级取）"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    nav = soup.find("nav", id="MenuContents")
    if not nav:
        raise SystemExit("nav#MenuContents 未找到")
    top_ul = nav.find("ul")
    items = []
    for li in top_ul.find_all("li", recursive=False):
        for a in li.find_all("a"):
            text = re.sub(r"\s+", " ", a.get_text()).strip()
            if text:
                items.append((text, a.get("href") or ""))
                break
    return items


def slug_of(href):
    p = href.split("/handbook/")[-1].split("#")[0].strip("/")
    return p


def main():
    os.makedirs(PAGES, exist_ok=True)
    idx = os.path.join(ROOT, "index.html")
    if not os.path.exists(idx):
        open(idx, "wb").write(fetch(BASE))
    html = open(idx, encoding="utf-8").read()
    items = parse_menu(html)
    plan = []
    for t, h in items:
        s = slug_of(h)
        if not s or s.startswith("handbook_zh-cn"):
            continue          # PDF 链接 / 杂项
        kind = "part" if t.startswith("部分 ") else "doc"
        plan.append({"title": t, "slug": s, "kind": kind, "url": BASE + s + "/"})
    json.dump(plan, open(os.path.join(ROOT, "plan.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("计划节点: %d (part %d / doc %d)" % (len(plan), sum(1 for p in plan if p["kind"] == "part"),
                                              sum(1 for p in plan if p["kind"] == "doc")), flush=True)
    for p in plan:
        print("  %-6s %-45s %s" % (p["kind"], p["slug"], p["title"]), flush=True)
    total_img = 0
    for n, p in enumerate(plan, 1):
        fp = os.path.join(PAGES, p["slug"] + ".html")
        if not os.path.exists(fp) or os.path.getsize(fp) < 5000:
            try:
                raw = fetch(p["url"])
                open(fp, "wb").write(raw)
            except Exception as e:
                print("ERR %s: %s" % (p["slug"], e), flush=True)
                continue
        h = open(fp, encoding="utf-8", errors="replace").read()
        imgs = len(re.findall(r"<img\b", h))
        total_img += imgs
        print("[%2d/%d] %-45s %7d B  img=%-4d" % (n, len(plan), p["slug"], len(h), imgs), flush=True)
        time.sleep(0.3)
    print("==== 抓取完成，img 标签总数(含站点 logo 等) =", total_img, flush=True)


if __name__ == "__main__":
    main()
