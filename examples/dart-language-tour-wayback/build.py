#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dart 语言导览（MediaWiki 单页，Wayback 快照）→ 语雀导入树。

口径：网站口径。单页 wiki（Language_Tour），按 h2 主节拆篇（h3/h4 留作小节标题）。
- 正文容器 `div.mw-parser-output`；剔 mw-editsection（编辑链接）、目录节
- `<pre class="prettyprint lang-xxx">` → 围栏（语言取自 lang-xxx）
- 站内 `/wiki/...` 链（站点已死）→ 只留文字；外链保留
"""
import os, re, shutil
from bs4 import BeautifulSoup, Tag, NavigableString

SRC = "/home/admin/.openclaw/workspace/tmp/fpb087-dl/fpb087-out/00-6fe150ad.bin"
OUT = "/home/admin/.openclaw/workspace/tmp/fpb087/build"

soup = BeautifulSoup(open(SRC, "rb").read().decode("utf-8", "replace"), "html5lib")
cont = soup.select_one("div.mw-parser-output")

def ws(s):
    return re.sub(r"\s+", " ", s)

def drop_junk(root):
    for sel in [".mw-editsection", ".reference", "sup.noprint", ".mw-empty-elt"]:
        for e in root.select(sel):
            e.decompose()

def inline(node):
    out = []
    for ch in node.children:
        if isinstance(ch, NavigableString):
            out.append(ws(str(ch)))
        elif isinstance(ch, Tag):
            n = ch.name
            cls = ch.get("class") or []
            if "mw-editsection" in cls or "reference" in cls:
                continue
            if n in ("b", "strong"):
                t = inline(ch).strip(); out.append("**%s**" % t if t else "")
            elif n in ("i", "em"):
                t = inline(ch).strip(); out.append("*%s*" % t if t else "")
            elif n in ("code", "tt", "kbd", "samp"):
                out.append("`%s`" % ws(ch.get_text()))
            elif n == "a":
                t = inline(ch).strip()
                href = (ch.get("href") or "").strip()
                if not t:
                    out.append("")
                elif href.startswith("/") or href.startswith("#") or "lidian.info" in href or not href:
                    out.append(t)                       # 站内/锚点/死站链 → 纯文字
                else:
                    out.append("[%s](%s)" % (t, href))
            elif n == "br":
                out.append("\n")
            elif n == "img":
                out.append("")
            else:
                out.append(inline(ch))
    return "".join(out)

def code_of(pre):
    return pre.get_text().strip("\n")

def render_block(e):
    n = e.name
    if n == "p":
        t = inline(e).strip()
        return t + "\n\n" if t else ""
    if n == "pre":
        cls = " ".join(e.get("class") or [])
        lang = ""
        m = re.search(r"lang-([a-z0-9]+)", cls)
        if m:
            lang = m.group(1)
        return "```%s\n%s\n```\n\n" % (lang, code_of(e))
    if n in ("h1", "h2", "h3", "h4", "h5", "h6"):
        t = ws(e.get_text(" ", strip=True))
        lvl = int(n[1])
        return "#" * max(3, lvl) + " " + t + "\n\n"
    if n in ("ul", "ol"):
        lines = []
        for i, li in enumerate(e.find_all("li", recursive=False)):
            t = inline(li).strip()
            t = re.sub(r"\n+", " ", t)
            lines.append(("- " if n == "ul" else "%d. " % (i + 1)) + t)
        return "\n".join(lines) + "\n\n"
    if n == "dl":
        lines = []
        for c in e.find_all(["dt", "dd"], recursive=False):
            t = inline(c).strip()
            lines.append(("**%s**" % t) if c.name == "dt" else ("  " + t))
        return "\n".join(lines) + "\n\n"
    if n == "table":
        rows = [[inline(td).strip() for td in tr.find_all(["td", "th"])] for tr in e.find_all("tr")]
        rows = [r for r in rows if any(r)]
        if not rows:
            return ""
        has_th = bool(e.find("th"))
        head, data = (rows[0], rows[1:]) if has_th else ([""] * len(rows[0]), rows)
        md = ["| " + " | ".join(head) + " |", "| " + " | ".join(["---"] * len(head)) + " |"]
        for r in data:
            r = (r + [""] * len(head))[: len(head)]
            md.append("| " + " | ".join(r) + " |")
        return "\n".join(md) + "\n\n"
    if n in ("div", "span", "section"):
        return "".join(render_block(x) for x in e.children if isinstance(x, Tag))
    if n == "script" or n == "style":
        return ""
    # 其他：递归
    return "".join(render_block(x) for x in e.children if isinstance(x, Tag))

drop_junk(cont)

# 顶层分组（按 h2）
kids = [k for k in cont.children if isinstance(k, Tag)]
sections = []
cur = None
for k in kids:
    if k.name == "h2":
        cur = {"title": ws(k.get_text(" ", strip=True)), "elems": []}
        sections.append(cur)
    elif cur is not None:
        cur["elems"].append(k)

if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

def safe(name):
    return name.replace("/", "／").replace('"', "").strip()

note = (
    "# Dart 语言导览\n\n"
    "**来源**：https://web.archive.org/web/20200415002731/http://dart.lidian.info/wiki/Language_Tour"
    "（Dart 中文 wiki「Dart 语言导览」，MediaWiki 单页；原站 dart.lidian.info 已无法解析，正文取自 Wayback 2020-04-15 快照）\n"
    "**原著**：Dart Language Tour（dartlang.org）中文译本\n"
    "**说明**：整页按站内 `<h2>` 主节拆篇；`h3`/`h4` 保留为小节标题；站内 `/wiki/...` 链接因原站已死转为纯文字。\n"
    "**导入日期**：2026-10-30\n"
)
open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8").write(note)

n = 0
for sec in sections:
    if sec["title"] == "目录":   # 页面自带 TOC，与语雀侧栏重复
        continue
    n += 1
    txt = "".join(render_block(e) for e in sec["elems"])
    txt = re.sub(r"\n{3,}", "\n\n", txt).strip() + "\n"
    fn = safe("%02d-%s.md" % (n, sec["title"]))
    open(os.path.join(OUT, fn), "w", encoding="utf-8").write("# %s\n\n" % sec["title"] + txt)
    print("[DOC] %s  (%d chars)" % (fn, len(txt)))

print("总文档:", n + 1)
