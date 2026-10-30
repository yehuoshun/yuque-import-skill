#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""coffee-script.org（CoffeeScript 中文站）→ 语雀导入树。

口径：网站口径。单页整站（index 一页承载全书），按 `<h2>` 分主节、`<b class="header">` 分「语言手册」子节。
- 代码块：`<div class='code'>` 内第 1 个 <pre> = coffeescript 源，第 2 个 = javascript 编译输出；独立 <pre> = 无语言围栏
- 跳过：flaybar 导航、REPL 编辑器、`<span class=bookmark>` 锚、`<div class='minibutton'>`、`<script>`、`<br class=clear>`
"""
import os, re, shutil
from bs4 import BeautifulSoup, Tag, NavigableString

SRC = "/home/admin/.openclaw/workspace/tmp/fpb086-index.html"
OUT = "/home/admin/.openclaw/workspace/tmp/fpb086/build"

BASE = "http://coffee-script.org/"

soup = BeautifulSoup(open(SRC, encoding="utf-8", errors="replace").read(), "html5lib")
cont = soup.select_one("div.container")
kids = [k for k in cont.children if isinstance(k, Tag)]
start = next(i for i, k in enumerate(kids) if k.name == "h2")

def ws(s):
    return re.sub(r"\s+", " ", s)

def inline(node):
    out = []
    for ch in node.children:
        if isinstance(ch, NavigableString):
            out.append(ws(str(ch)))
        elif isinstance(ch, Tag):
            n = ch.name
            if n in ("b", "strong"):
                t = inline(ch).strip()
                out.append("**%s**" % t if t else "")
            elif n in ("i", "em"):
                t = inline(ch).strip()
                out.append("*%s*" % t if t else "")
            elif n in ("tt", "code", "kbd"):
                out.append("`%s`" % inline(ch).strip())
            elif n == "a":
                t = inline(ch).strip() or ch.get("href", "")
                href = (ch.get("href") or "").strip()
                if href.startswith("#") or not href:
                    out.append(t)
                else:
                    if not re.match(r"(https?:|mailto:|//)", href):   # 相对链 → 补站点绝对前缀
                        href = BASE + href.lstrip("/")
                    out.append("[%s](%s)" % (t, href))
            elif n == "br":
                out.append("\n")
            elif n == "span":
                out.append(inline(ch))
            else:
                out.append(inline(ch))
    return "".join(out)

def code_of(pre):
    code = pre.find("code")
    txt = (code or pre).get_text()
    return txt.strip("\n")

def render_block(e, lang_hint=None):
    n = e.name
    if n == "p":
        t = inline(e).strip()
        return t + "\n\n" if t else ""
    if n == "pre":
        return "```\n%s\n```\n\n" % code_of(e)
    if n == "div":
        cls = e.get("class") or []
        if "code" in cls:
            parts = []
            pres = [x for x in e.find_all("pre") if x.find_parent("div") is e]
            for i, pre in enumerate(pres):
                lang = "coffeescript" if i == 0 else "javascript"
                parts.append("```%s\n%s\n```\n\n" % (lang, code_of(pre)))
            if not pres:                      # 少数 code div 直接嵌 code
                codes = [x for x in e.find_all("code") if x.find_parent("div") is e]
                for i, cd in enumerate(codes):
                    lang = "coffeescript" if i == 0 else "javascript"
                    parts.append("```%s\n%s\n```\n\n" % (lang, cd.get_text().strip("\n")))
            return "".join(parts)
        if "minibutton" in cls:
            return ""
        # 普通 div：递归
        return "".join(render_block(x) for x in e.children if isinstance(x, Tag))
    if n in ("ul", "ol"):
        lines = []
        for i, li in enumerate(e.find_all("li", recursive=False)):
            t = inline(li).strip()
            t = re.sub(r"\n+", " ", t)
            bullet = "- " if n == "ul" else "%d. " % (i + 1)
            lines.append(bullet + t)
        return "\n".join(lines) + "\n\n"
    if n == "table":
        rows = []
        for tr in e.find_all("tr"):
            cells = [inline(td).strip() for td in tr.find_all(["td", "th"])]
            rows.append(cells)
        if not rows:
            return ""
        has_th = bool(e.find("th"))
        if has_th:
            head = rows[0]
            data = rows[1:]
        else:                                    # 无表头表 → 造空表头（同 awk 口径）
            head = [""] * len(rows[0])
            data = rows
        md = ["| " + " | ".join(head) + " |", "| " + " | ".join(["---"] * len(head)) + " |"]
        for r in data:
            r = (r + [""] * len(head))[: len(head)]
            md.append("| " + " | ".join(r) + " |")
        return "\n".join(md) + "\n\n"
    if n in ("h2", "h3"):
        return ""
    if n == "script":
        return ""
    if n == "span":                     # bookmark 等
        return ""
    return "".join(render_block(x) for x in e.children if isinstance(x, Tag)) if isinstance(e, Tag) else ""

def render(elems):
    out = "".join(render_block(e) for e in elems)
    return re.sub(r"\n{3,}", "\n\n", out).strip() + "\n"

# ---- 分组：主节（h2）----
sections = []
cur = None
for k in kids[start:]:
    if k.name == "h2":
        title = ws(k.get_text(" ", strip=True))
        cur = {"title": title, "elems": []}
        sections.append(cur)
    else:
        if cur is not None:
            cur["elems"].append(k)

# ---- 语言手册：按 b.header 再分子节 ----
def split_subs(sec):
    intro, subs = [], []
    cur = None
    for e in sec["elems"]:
        hdr = None
        if e.name == "p":
            b = e.find("b", class_="header")
            if b is not None and b.find_parent("p") is e:
                hdr = ws(b.get_text(" ", strip=True))
        if hdr:
            b.extract()
            cur = {"title": hdr, "elems": []}
            subs.append(cur)
            if inline(e).strip():
                cur["elems"].append(e)
        elif cur is None:
            intro.append(e)
        else:
            cur["elems"].append(e)
    return intro, subs

# ---- 落盘 ----
if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

def safe(name):
    return name.replace("/", "／").replace('"', "").strip()

note = (
    "# CoffeeScript 中文\n\n"
    "**来源**：http://coffee-script.org（CoffeeScript 中文站，单页整站）\n"
    "**原著**：CoffeeScript（Jeremy Ashkenas，[coffeescript.org](http://coffeescript.org)）中文译本；本站版本 1.7.1\n"
    "**说明**：本站为单页 HTML，下方按站内 `<h2>` 主节与「语言手册」小节拆篇；"
    "代码示例左侧为 CoffeeScript 源码、右侧为编译后 JavaScript，均原样保留；"
    "部分章节（Books/Screencasts/Examples 等）站点未完全汉化，保留英文原文。\n"
    "**导入日期**：2026-10-30\n"
)
open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8").write(note)

idx = 0
for sec in sections:
    idx += 1
    t = sec["title"]
    if "语言手册" in t:
        d = safe("%02d-%s" % (idx, t))
        os.makedirs(os.path.join(OUT, d))
        intro, subs = split_subs(sec)
        open(os.path.join(OUT, d, "00-语言手册导读.md"), "w", encoding="utf-8").write("# 语言手册导读\n\n" + render(intro))
        for j, s in enumerate(subs, 1):
            fn = safe("%02d.%02d-%s.md" % (idx, j, s["title"]))
            open(os.path.join(OUT, d, fn), "w", encoding="utf-8").write("# %s\n\n" % s["title"] + render(s["elems"]))
        print("[DIR] %s  (%d 子节 + 导读)" % (d, len(subs)))
    else:
        fn = safe("%02d-%s.md" % (idx, t))
        body = render(sec["elems"])
        open(os.path.join(OUT, fn), "w", encoding="utf-8").write("# %s\n\n" % t + body)
        print("[DOC] %s" % fn)

# 统计
nd = sum(1 for r, _, fs in os.walk(OUT) for f in fs)
print("总文档:", nd)
