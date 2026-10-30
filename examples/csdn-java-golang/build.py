#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#110 Java程序员的Golang入门指南(上) — CSDN 博客 dc_726/article/details/46565241
CSDN 直连被 WAF(521) 拦、runner 出口也 521；r.jina 亦 521；(下) 无 Wayback 快照。
→ 正文取 Wayback 20250511150824 快照(上)。网站口径(文章收集)。
"""
import os, re, shutil
from bs4 import BeautifulSoup, NavigableString, Comment

SRC = "a.html"
OUT = "build"


def inline(node):
    out = []
    for ch in node.children:
        if isinstance(ch, Comment):
            continue
        if isinstance(ch, NavigableString):
            out.append(str(ch)); continue
        n = ch.name
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
        if n == "a":
            t = inline(ch).strip(); href = ch.get("href", "")
            if href and re.match(r"https?:", href):
                out.append(f"[{t}]({href})")
            else:
                out.append(t)
            continue
        out.append(inline(ch))
    return "".join(out)


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
        if n in ("script", "style"):
            continue
        if n in ("h1", "h2", "h3", "h4"):
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
        elif n == "pre":
            lang = ""
            code = ch.find("code")
            if code and code.get("class"):
                m = re.search(r"language-(\w+)", " ".join(code.get("class")))
                lang = m.group(1) if m else ""
            if not lang:
                lang = "go"
            out.append("```" + lang + "\n" + ch.get_text().rstrip("\n") + "\n```")
        elif n in ("div", "section", "blockquote"):
            render(ch, out)
        else:
            t = clean(inline(ch))
            if t:
                out.append(t)


def to_md(node):
    out = []
    render(node, out)
    text = "\n\n".join(x for x in out if x.strip())
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    soup = BeautifulSoup(open(SRC, encoding="utf-8").read(), "html.parser")
    cv = soup.find(id="content_views")
    # 章节 = h2（首个 h2 是文章标题，跳过）
    sections = []   # (title, [elements])
    cur = None
    for el in cv.children:
        if isinstance(el, NavigableString):
            if cur and el.strip():
                cur[1].append(el)
            continue
        if el.name == "h2":
            if cur:
                sections.append(cur)
            cur = [clean(inline(el)), []]
        else:
            if cur:
                cur[1].append(el)
    if cur:
        sections.append(cur)
    # 首个 h2（文章标题）作为整篇标题
    title = sections[0][0] if sections else "Java程序员的Golang入门指南"
    body_sections = sections[1:]
    open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8").write(
        "> 来源：https://blog.csdn.net/dc_726/article/details/46565241（CSDN dc_726）｜ "
        "正文取自 Internet Archive Wayback 快照（2025-05-11）。\n"
        ">\n"
        "> ⚠️ 本文为《Java程序员的Golang入门指南》系列**(上)**篇（CSDN 直连被 WAF 拦截、"
        "runner 出口同样 521、r.jina 亦 521；**(下)**篇 https://blog.csdn.net/dc_726/article/details/46745947 "
        "无 Wayback 快照）→ 本库只收录 (上) 篇。\n\n"
        "《" + title + "》\n")
    nn = 1
    for t, els in body_sections:
        frag = soup.new_tag("div")
        for e in els:
            frag.append(e)
        md = to_md(frag)
        name = f"{nn:02d}-{t.replace('/', '／')}.md"
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(md)
        print(f"  {name} ({len(md)} chars)")
        nn += 1
    print("done")


if __name__ == "__main__":
    main()
