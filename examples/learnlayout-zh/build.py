#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#119 学习CSS布局 (zh.learnlayout.com, learnlayout.com 中文版) — 网站口径
静态多页站：页面清单= /toc 顺序；正文容器 #container（剥 style/nav-wrapper/footer/#menu）。
图：frameworks 页 10 张框架 logo（/images/*）→ 下载本地化后传 CDN。
"""
import os, re, time, shutil, urllib.request
from bs4 import BeautifulSoup, NavigableString, Comment

BASE = "https://zh.learnlayout.com"
OUT = "build"
UA = {"User-Agent": "Mozilla/5.0 (learnlayout-fetch)"}

PAGES = [
    ("index.html", "首页"),
    ("no-layout.html", None), ("display.html", None), ("margin-auto.html", None),
    ("max-width.html", None), ("box-model.html", None), ("box-sizing.html", None),
    ("position.html", None), ("position-example.html", None), ("float.html", None),
    ("clear.html", None), ("clearfix.html", None), ("float-layout.html", None),
    ("percent.html", None), ("media-queries.html", None), ("inline-block.html", None),
    ("inline-block-layout.html", None), ("column.html", None), ("flexbox.html", None),
    ("frameworks.html", None), ("about.html", "关于本站"),
]


def get(url, tries=5):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise SystemExit(f"FAIL {url}: {last}")


def inline(node):
    out = []
    for ch in node.children:
        if isinstance(ch, Comment):
            continue
        if isinstance(ch, NavigableString):
            out.append(str(ch)); continue
        n = ch.name
        cls = ch.get("class") or []
        if n in ("script", "style", "footer") or "nav-wrapper" in cls or ch.get("id") == "translations":
            continue
        if n in ("script", "style"):
            continue
        if n == "br":
            out.append("\n"); continue
        if n in ("em", "i"):
            out.append("*" + inline(ch).strip() + "*"); continue
        if n in ("strong", "b"):
            out.append("**" + inline(ch).strip() + "**"); continue
        if n in ("code", "tt"):
            out.append("`" + ch.get_text() + "`"); continue
        if n == "img":
            src = (ch.get("src") or "").strip()
            if src:
                out.append("![](" + norm_img(src) + ")")
            continue
        if n == "a":
            t = inline(ch).strip(); href = ch.get("href", "")
            if href and re.match(r"https?:", href):
                out.append(f"[{t}]({href})")
            else:
                out.append(t)
            continue
        out.append(inline(ch))
    return "".join(out)


def norm_img(src):
    if src.startswith("/"):
        return "images/" + src.rsplit("/", 1)[1]
    return src


def clean(s):
    return re.sub(r"[ \t]+", " ", s).replace("\n ", "\n").strip()


def render(node, out):
    for ch in node.children:
        if isinstance(ch, Comment):
            continue
        if isinstance(ch, NavigableString):
            t = clean(str(ch))
            if t:
                out.append(t)
            continue
        n = ch.name
        cls = ch.get("class") or []
        if n in ("script", "style"):
            continue
        if "nav-wrapper" in cls or n == "footer" or ch.get("id") == "translations":
            continue
        if n == "h1":
            continue
        if n in ("h2", "h3", "h4"):
            t = clean(inline(ch))
            if t:
                out.append("#" * int(n[1]) + " " + t)
        elif n == "p":
            t = clean(inline(ch))
            if t:
                out.append(t)
        elif n in ("ul", "ol"):
            lines = []
            for i, li in enumerate(ch.find_all("li", recursive=False), 1):
                lines.append((f"{i}. " if n == "ol" else "- ") + clean(inline(li)))
            if lines:
                out.append("\n".join(lines))
        elif n == "table":
            rows = [[clean(inline(td)) for td in tr.find_all(["td", "th"])] for tr in ch.find_all("tr")]
            rows = [r for r in rows if r]
            if rows:
                m = max(len(r) for r in rows); rows = [r + [""] * (m - len(r)) for r in rows]
                out.append("| " + " | ".join(rows[0]) + " |")
                out.append("| " + " | ".join(["---"] * m) + " |")
                for r in rows[1:]:
                    out.append("| " + " | ".join(r) + " |")
        elif n == "figure":
            pre = ch.find("pre")
            if pre:
                lang = ""
                code = pre.find("code")
                if code:
                    m = re.search(r"language-(\w+)", " ".join(code.get("class") or []))
                    lang = m.group(1) if m else ""
                out.append("```" + lang + "\n" + pre.get_text().rstrip("\n") + "\n```")
            else:
                render(ch, out)
        elif n == "pre":
            out.append("```\n" + ch.get_text().rstrip("\n") + "\n```")
        elif n in ("div", "section", "blockquote", "span"):
            # span.label/endlabel（demo 盒子的标签）单独成行代码
            if "span" == n and ("label" in cls or "endlabel" in cls):
                t = clean(inline(ch))
                if t:
                    out.append("`" + t + "`")
                continue
            render(ch, out)
        else:
            t = clean(inline(ch))
            if t:
                out.append(t)


def to_md(container):
    out = []
    render(container, out)
    text = "\n\n".join(x for x in out if x.strip())
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    imgs = set()
    nn = 0
    for fn, title in PAGES:
        html = get(f"{BASE}/{fn.replace('index.html','')}")
        soup = BeautifulSoup(html, "html.parser")
        c = soup.find(id="container")
        if c is None:
            print("  NO container", fn); continue
        h1 = c.find("h1")
        t = title or (clean(inline(h1)) if h1 else fn)
        # 收集图
        for i in c.find_all("img"):
            src = (i.get("src") or "").strip()
            if src.startswith("/"):
                imgs.add(src)
        body = to_md(c)
        name = f"{nn:02d}-{t}.md"
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(
            body.replace("/images/", "images/") if False else body)
        print(f"  {nn:02d} {fn:22} -> {name} ({len(body)} chars)")
        nn += 1
    # 下载图
    os.makedirs(os.path.join(OUT, "images"), exist_ok=True)
    for src in sorted(imgs):
        data = get(BASE + src)
        open(os.path.join(OUT, "images", os.path.basename(src)), "wb").write(data)
        print("  img", src, len(data))
    print("done")


if __name__ == "__main__":
    main()
