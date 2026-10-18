#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UNIX TOOLBOX 中文版（cb.vu）→ markdown（按 h1 拆成 23 篇 + 前言）

站点：http://cb.vu/unixtoolbox_zh_CN.xhtml（单页 XHTML，21 万字节；archive.org 版超时，直接用原站）
结构：div.title + div.abstract + div.menu(目录/丢弃) + div.main(正文) + footer(丢弃)
     正文块：h1(23 章) / h2 / h3 / h4 / pre(316 代码块) / p / ul / table
     行内：span.cmt(注释) span.fn span.pp span.keyword / a.xrefp(内部锚点) / a[href] 外链
"""
import html as H
import os
import re
import sys
import urllib.request

URL = "http://cb.vu/unixtoolbox_zh_CN.xhtml"
OUT = "/home/admin/.openclaw/workspace/tmp/unixtoolbox-clean"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120 Safari/537.36"}


def fetch():
    cache = "/tmp/utb.html"
    if os.path.exists(cache) and os.path.getsize(cache) > 100000:
        return open(cache, encoding="utf-8", errors="replace").read()
    req = urllib.request.Request(URL, headers=UA)
    data = urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "replace")
    open(cache, "w", encoding="utf-8").write(data)
    return data


def inline(t):
    t = re.sub(r'<span class="cmt">(.*?)</span>', r"\1", t, flags=re.S)
    t = re.sub(r'<span class="(?:fn|pp|keyword|web)">(.*?)</span>', r"`\1`", t, flags=re.S)
    t = re.sub(r"<br\s*/?>", "\n", t)
    t = re.sub(r'<a[^>]*href="#[^"]*"[^>]*>(.*?)</a>', r"\1", t, flags=re.S)
    t = re.sub(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"[\2](\1)", t, flags=re.S)
    t = re.sub(r"<(?:b|strong)>(.*?)</(?:b|strong)>", r"**\1**", t, flags=re.S)
    t = re.sub(r"<(?:i|em)>(.*?)</(?:i|em)>", r"*\1*", t, flags=re.S)
    t = re.sub(r"<(?:code|tt)>(.*?)</(?:code|tt)>", r"`\1`", t, flags=re.S)
    t = re.sub(r"<[^>]+>", "", t)
    t = H.unescape(t).replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def render_pre(inner):
    txt = re.sub(r'<span class="cmt">(.*?)</span>', r"\1", inner, flags=re.S)
    txt = re.sub(r'<span class="(?:fn|pp|keyword|web)">(.*?)</span>', r"\1", txt, flags=re.S)
    txt = re.sub(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"\2 <\1>", txt, flags=re.S)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = H.unescape(txt).replace("\xa0", " ")
    return "```bash\n" + txt.strip("\n") + "\n```"


def render_list(inner):
    out = []
    for li in re.findall(r"<li[^>]*>(.*?)</li>", inner, re.S):
        t = inline(li)
        if t:
            out.append("- " + re.sub(r"\s+", " ", t))
    return "\n".join(out)


def render_table(inner):
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", inner, re.S):
        cells = [inline(td) for td in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if any(cells):
            rows.append("| " + " | ".join(cells) + " |")
    if len(rows) >= 2:
        n = rows[0].count("|") - 1
        rows.insert(1, "|" + "|".join(["---"] * n) + "|")
    return "\n".join(rows)


BLOCK = re.compile(r"<(h1|h2|h3|h4|pre|p[^>]*|ul|ol|table)(?:>|\s[^>]*>)(.*?)(?=</(?:h1|h2|h3|h4|pre|p|ul|ol|table)>)", re.S)


def render_blocks(seg):
    """按块顺序渲染（用 lookahead 收尾，避免嵌套截断）"""
    out = []
    pos = 0
    pat = re.compile(r"<(h1|h2|h3|h4|pre|p|ul|ol|table)(?:\s[^>]*)?>(.*?)</\1>", re.S)
    # 手工扫描：遇 <pre> 直接到 </pre>；其余用非贪婪（这些块内无同名嵌套）
    while pos < len(seg):
        m = pat.search(seg, pos)
        if not m:
            break
        tag, inner = m.group(1), m.group(2)
        if m.start() > pos:
            t = inline(seg[pos:m.start()])
            if t:
                out.append(t)
        pos = m.end()
        if tag == "h1":
            out.append("\n# " + inline(inner))
        elif tag in ("h2", "h3", "h4"):
            out.append("\n" + "#" * int(tag[1]) + " " + inline(inner))
        elif tag == "pre":
            out.append("\n" + render_pre(inner))
        elif tag == "p":
            t = inline(inner)
            if t:
                out.append(t)
        elif tag in ("ul", "ol"):
            t = render_list(inner)
            if t:
                out.append("\n" + t)
        elif tag == "table":
            t = render_table(inner)
            if t:
                out.append("\n" + t)
    tail = inline(seg[pos:])
    if tail:
        out.append(tail)
    md = "\n\n".join(x.strip() for x in out if x and x.strip())
    md = re.sub(r"\n{3,}", "\n\n", md)
    # 残留的版式 div（footer / pb / changestyle 等）整块丢掉
    md = re.sub(r'<div[^>]*class="(?:footerfirst|footerlast|pb|changestyle|menu)"[^>]*>.*?</div>', "", md, flags=re.S)
    md = re.sub(r"<div[^>]*>", "", md)
    md = re.sub(r"</div>", "", md)
    # 原站 XHTML 注释尾巴（"end main -->" / 孤立 "-->" / 未闭合 "<div"）
    md = re.split(r"\nend main", md)[0]
    md = "\n".join(l for l in md.splitlines()
                   if not re.fullmatch(r"\s*(?:-->?|<!---?|<div\s*|</div>)\s*", l))
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip() + "\n"


def main():
    h = fetch()
    i = h.find('class="main"')
    seg = h[i:]
    j = seg.find('class="footer')
    if j < 0:
        j = seg.find("</main>")
    seg = seg[:j]
    seg = seg[seg.find(">") + 1:]

    # 按 h1 切章
    parts = re.split(r"(?=<h1[\s>])", seg)
    head = parts[0]
    chapters = parts[1:]
    os.makedirs(OUT, exist_ok=True)

    # 前言：书名 + 摘要 + 章节清单
    title = re.search(r'<div class="title">(.*?)</div>', h, re.S)
    abstract = re.search(r'<div class="abstract">(.*?)</div>', h, re.S)
    names = []
    for c in chapters:
        t = re.search(r"<h1[^>]*>(.*?)</h1>", c, re.S)
        names.append(inline(t.group(1)) if t else "?")
    pre = ["# UNIX TOOLBOX（中文版）", ""]
    if abstract:
        pre.append(inline(abstract.group(1)))
        pre.append("")
    pre += ["---", "", "## 章节目录", ""]
    for k, nm in enumerate(names, 1):
        pre.append("- %02d %s" % (k, nm))
    pre += ["", "本站（cb.vu）已归档；源页面：<%s> ｜ 原版英文：<https://cb.vu/unixtoolbox.xhtml>" % URL]
    open(os.path.join(OUT, "00-前言.md"), "w", encoding="utf-8").write("\n".join(pre) + "\n")

    for k, c in enumerate(chapters, 1):
        md = render_blocks(c)
        name = names[k - 1]
        safe = re.sub(r'[/\\:*?"<>|]', "-", name)
        open(os.path.join(OUT, "%02d-%s.md" % (k, safe)), "w", encoding="utf-8").write(md)
        print("%02d-%-22s %6d chars" % (k, safe, len(md)))
    print("章节:", len(chapters), "+ 前言")


if __name__ == "__main__":
    main()