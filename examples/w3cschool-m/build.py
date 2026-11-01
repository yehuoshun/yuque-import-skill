#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w3cschool electronmanual（Electron 中文文档 w3cschool 镜像）→ markdown 树。

特性：
- ypre cookie 挑战：页面首次返回 `abcd(a,b)=5*|3a-2b|` JS，需算 ypre_token2 + 固定
  ypre_authtoken，带 cookie 重试；token2 每次刷新都变 → 每请求先解挑战。
- 目录 = #nestable_handbook 内 a[href]（62 条，顺序=侧栏序）
- 正文容器 = div.view-body.think-editor-content（与 #73 thinkcpp 同站同款）
"""
import argparse
import os
import re
import sys
import time
import urllib.request
import urllib.error

from bs4 import BeautifulSoup
from bs4.element import NavigableString

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
      "AppleWebKit/605.1.15")
BASE = "https://m.w3cschool.cn"


class W3C:
    def get(self, path):
        url = BASE + path
        for attempt in range(10):
            headers = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9",
                       "Accept": "text/html,application/xhtml+xml"}
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=40) as r:
                    body = r.read().decode("utf-8", "replace")
                    self.last_url = r.geturl()
            except urllib.error.HTTPError as e:
                if e.code in (403, 429, 503):
                    time.sleep(6 + 3 * attempt)
                    continue
                raise
            # 挑战页特征：<script>…abcd(a,b)…location.href</script> 或长度 < 2KB
            if len(body) < 2000 and ("abcd(" in body or "setCookie" in body):
                time.sleep(6 + 2 * attempt)
                continue
            return body
        raise RuntimeError("w3cschool fetch fail: %s" % path)


def safe(name):
    name = re.sub(r"\s+", " ", name).strip()
    return name.replace("/", "／").replace("\\", "／").replace("<", "").replace(">", "")


def inline(el, page_url, out):
    for c in el.children:
        if isinstance(c, NavigableString):
            out.append(str(c))
        elif c.name == "br":
            out.append("\n")
        elif c.name in ("strong", "b"):
            t = []
            inline(c, page_url, t)
            tt = "".join(t).strip()
            if tt:
                out.append("**" + tt + "**")
        elif c.name in ("em", "i"):
            t = []
            inline(c, page_url, t)
            tt = "".join(t).strip()
            if tt:
                out.append("*" + tt + "*")
        elif c.name in ("code", "tt", "kbd"):
            out.append("`" + c.get_text().strip() + "`")
        elif c.name == "img":
            src = c.get("src", "")
            alt = c.get("alt", "") or ""
            if src:
                out.append("![%s](%s)" % (alt, src))
        elif c.name == "a":
            href = c.get("href", "")
            t = []
            inline(c, page_url, t)
            txt = "".join(t).strip()
            if not href or href.startswith("#") or href.startswith("javascript"):
                out.append(txt)
            else:
                out.append("[%s](%s)" % (txt, href))
        else:
            inline(c, page_url, out)


def render_list(lst, out, page_url, depth):
    for i, li in enumerate(lst.find_all("li", recursive=False), 1):
        prefix = "  " * depth + ("- " if lst.name == "ul" else "%d. " % i)
        t = []
        inline(li, page_url, t)
        txt = "".join(t).strip()
        if txt:
            out.append(prefix + txt)
        for child in li.find_all(["ul", "ol"], recursive=False):
            render_list(child, out, page_url, depth + 1)


def table_md(tb, page_url):
    rows = []
    for tr in tb.find_all("tr"):
        cells = []
        for td in tr.find_all(["td", "th"]):
            t = []
            inline(td, page_url, t)
            cells.append("".join(t).replace("\n", " ").strip())
        rows.append("| " + " | ".join(cells) + " |")
    if len(rows) >= 2:
        n = rows[0].count("|") - 1
        rows.insert(1, "|" + "|".join(["---"] * n) + "|")
    return "\n".join(rows)


def render(el, out, page_url, depth=0):
    for c in el.children:
        if isinstance(c, NavigableString):
            t = str(c).strip()
            if t:
                out.append(t)
            continue
        if c.name in ("script", "style"):
            continue
        name = c.name or ""
        if re.fullmatch(r"h[1-6]", name):
            t = []
            inline(c, page_url, t)
            tt = "".join(t).strip()
            if tt:
                out.append("\n" + "#" * int(name[1]) + " " + tt)
        elif name == "p":
            t = []
            inline(c, page_url, t)
            tt = "".join(t).strip()
            if tt:
                out.append(tt)
        elif name in ("ul", "ol"):
            render_list(c, out, page_url, depth)
        elif name == "pre":
            code = c.get_text()
            lang = ""
            code_el = c.find("code")
            if code_el and code_el.get("class"):
                for cl in code_el["class"]:
                    m = re.match(r"lang(?:uage)?-(\w+)", cl)
                    if m:
                        lang = m.group(1)
            out.append("\n```%s\n%s\n```" % (lang, code.strip("\n")))
        elif name == "blockquote":
            t = []
            inline(c, page_url, t)
            tt = "".join(t).strip()
            if tt:
                out.append("\n> " + tt.replace("\n", "\n> "))
        elif name == "table":
            t = table_md(c, page_url)
            if t:
                out.append("\n" + t)
        elif name == "hr":
            out.append("\n---")
        elif name == "img":
            t = []
            inline(c, page_url, t)
            if t:
                out.append("".join(t))
        elif name in ("div", "section", "article", "main", "tbody", "span", "center",
                      "figure", "figcaption", "dl", "dt", "dd"):
            has_block = any(
                (ch.name in ("p", "ul", "ol", "pre", "table", "blockquote", "div",
                             "h1", "h2", "h3", "h4", "h5", "h6", "hr", "img"))
                for ch in c.find_all(recursive=False))
            if has_block:
                render(c, out, page_url, depth)
            else:
                t = []
                inline(c, page_url, t)
                tt = "".join(t).strip()
                if tt:
                    out.append(tt)
        else:
            render(c, out, page_url, depth)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/fpb178-electron/site")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    w = W3C()

    idx = w.get("/electronmanual/")
    soup = BeautifulSoup(idx, "html.parser")
    box = soup.select_one("#nestable_handbook") or soup.select_one(".content-block")
    if not box:
        print("!! 未找到目录容器", file=sys.stderr)
        sys.exit(1)
    pages = []
    seen = set()
    for a in box.find_all("a", href=True):
        href = a.get("href", "")
        m = re.search(r"(/electronmanual/[^\"]+)", href)
        if not m or href.endswith("/list/"):
            continue
        href = m.group(1)
        title = a.get_text(" ", strip=True)
        if href in seen:
            continue
        seen.add(href)
        pages.append((href, title))
    print("目录条目:", len(pages))

    total = 0
    for i, (href, title) in enumerate(pages, 1):
        if "list" in href:
            continue
        body = w.get(href)
        soup = BeautifulSoup(body, "html.parser")
        sec = soup.select_one("div.content-intro") or soup.select_one("div.view-body.think-editor-content")
        if not sec:
            print("!! 无正文容器 %s %s" % (href, title))
            continue
        out = []
        render(sec, out, w.last_url or (BASE + href))
        md = "\n\n".join(out)
        md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
        lines = md.split("\n")
        if lines and lines[0].startswith("# "):
            lines = lines[1:]
            while lines and not lines[0].strip():
                lines.pop(0)
        md = "\n".join(lines).strip() + "\n"
        fname = "%02d-%s.md" % (i, safe(title))
        with open(os.path.join(args.out, fname), "w", encoding="utf-8") as f:
            f.write(md)
        total += 1
        print("  %-44s %6dB imgs=%d" % (fname, len(md), md.count("![")))
        time.sleep(1.2)
    print("TOTAL:", total)


if __name__ == "__main__":
    main()