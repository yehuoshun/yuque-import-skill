#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#112 Revel 框架手册 (gorevel.cn/docs/manual) — 网站口径（原站已死，走 Wayback 2019 快照）
正文容器 div.span10（剥离 div.page-header 的 h1）；分组取自页面 leftnav。
"""
import os, re, json, glob, shutil
from bs4 import BeautifulSoup, NavigableString, Comment

OUT = "build"

GROUPS = [
    ("概要", [("concepts", "概念"), ("organization", "结构")]),
    ("控制器", [("controllers", "概要"), ("routing", "路由"), ("binding", "参数绑定"),
               ("validation", "验证"), ("sessionflash", "Session／Flash"), ("results", "结果"),
               ("templates", "模板"), ("interceptors", "拦截器"), ("filters", "过滤器"),
               ("websockets", "Websockets"), ("i18n-messages", "国际化"), ("cache", "缓存")]),
    ("模块", [("modules", "概要"), ("testing", "测试"), ("jobs", "计划任务")]),
    ("操作", [("versions", "版本"), ("logging", "日志"), ("deployment", "部署")]),
    ("参考", [("appconf", "app.conf"), ("tool", "命令行工具"), ("faq", "FAQ")]),
]


def collect():
    m = {}
    for d in ("gA", "gB", "gC"):
        p = os.path.join(d, "manifest.json")
        if not os.path.exists(p):
            continue
        for e in json.load(open(p)):
            if e.get("file"):
                slug = e["url"].rsplit("/", 1)[1].replace(".html", "")
                m[slug] = os.path.join(d, e["file"])
    return m


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
        if n == "img":
            src = ch.get("src", "")
            if src:
                out.append("![](" + src.replace("../images/", "images/").replace("/docs/manual/", "") + ")")
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
        cls = ch.get("class") or []
        if n in ("script", "style"):
            continue
        if "page-header" in cls:
            continue
        if n == "img":
            m = inline(ch)
            if m:
                out.append(m); continue
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
        elif n == "table":
            rows = [[clean(inline(td)) for td in tr.find_all(["td", "th"])] for tr in ch.find_all("tr")]
            rows = [r for r in rows if r]
            if rows:
                m = max(len(r) for r in rows); rows = [r + [""] * (m - len(r)) for r in rows]
                tl = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * m) + " |"]
                for r in rows[1:]:
                    tl.append("| " + " | ".join(r) + " |")
                out.append("\n".join(tl))
        elif n == "pre":
            lang = ""
            code = ch.find("code")
            if code and code.get("class"):
                mm = re.search(r"lang-(\w+)", " ".join(code.get("class")))
                lang = mm.group(1) if mm else ""
            out.append("```" + lang + "\n" + ch.get_text().rstrip("\n") + "\n```")
        elif n == "div" and "alert" in cls:
            t = clean(inline(ch))
            if t:
                for ln in t.split("\n"):
                    out.append("> " + ln)
        elif n in ("div", "section", "article", "span", "blockquote"):
            render(ch, out)
        else:
            t = clean(inline(ch))
            if t:
                out.append(t)


def to_md(span10):
    out = []
    render(span10, out)
    text = "\n\n".join(x for x in out if x.strip())
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def build_doc(path):
    s = BeautifulSoup(open(path, encoding="utf-8", errors="replace").read(), "html.parser")
    c = s.find("div", class_="span10")
    return to_md(c) if c else ""


def main():
    files = collect()
    print("pages:", sorted(files))
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    # 00-说明 = 介绍 (index)
    if "index" in files:
        open(os.path.join(OUT, "00-說明.md"), "w", encoding="utf-8").write(
            "> 来源：http://gorevel.cn/docs/manual/（Revel 框架中文手册，原站已死）｜ "
            "正文取自 Internet Archive Wayback 2019-06-10 快照；gorevel.cn 域名现已被抢注为停放页。\n\n"
            + build_doc(files["index"]).lstrip("# ").strip() + "\n")
    nn = 1
    for gtitle, pages in GROUPS:
        gdir = os.path.join(OUT, f"{nn:02d}-{gtitle}")
        os.makedirs(gdir)
        i = 1
        for slug, title in pages:
            if slug not in files:
                print("  MISSING", slug); continue
            md = build_doc(files[slug])
            name = f"{i:02d}-{title}.md"
            open(os.path.join(gdir, name), "w", encoding="utf-8").write(md)
            print(f"  {gtitle}/{name} ({len(md)})")
            i += 1
        nn += 1
    print("done")


if __name__ == "__main__":
    main()
