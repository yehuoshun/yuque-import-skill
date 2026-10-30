#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#114 Groovy 教程 (w3cschool.cn/groovy) — 网站口径
正文容器 div.content-intro；页面清单/顺序取自首页侧栏链接。代码 pre.prettyprint/pre.result；表 table.reference。
图 atts.w3cschool.cn 外链 → 下载本地化。
"""
import os, re, time, shutil, urllib.request, urllib.parse
from bs4 import BeautifulSoup, NavigableString, Comment

OUT = "build"
UA = {"User-Agent": "Mozilla/5.0 (Groovy-crawl)"}
PAGES = [
    "groovy_overview", "groovy_environment", "groovy_basic_syntax", "groovy_data_types",
    "groovy_variables", "groovy_operators", "groovy_loops", "groovy_decision_making",
    "groovy_methods", "groovy_file_io", "groovy_optionals", "groovy_numbers",
    "groovy_strings", "groovy_ranges", "groovy_lists", "groovy_maps",
    "groovy_dates_times", "groovy_regular_expressions", "groovy_exception_handling",
    "groovy_object_oriented", "groovy_generics", "groovy_traits", "groovy_closures",
    "groovy_annotations", "groovy_xml", "groovy_jmx", "groovy_json", "groovy_dsls",
    "groovy_database", "groovy_builders", "groovy_command_line", "groovy_unit_testing",
    "groovy_template_engines", "groovy_meta_object_programming",
    "groovy-qjid3it8", "groovy-945w3it9",
]


def get(url, tries=4, binary=False):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    print("  FAIL", url, last)
    return None


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
        if n == "img":
            src = ch.get("src", "")
            if src:
                out.append("![](" + IMG.get(src, src) + ")")
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
        if n == "img":
            src = ch.get("src", "")
            if src:
                out.append("![](" + IMG.get(src, src) + ")")
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
        elif n == "table":
            rows = []
            for tr in ch.find_all("tr"):
                cells = [clean(inline(td)) for td in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)
            rows = [r for r in rows if any(r)]
            if rows:
                m = max(len(r) for r in rows); rows = [r + [""] * (m - len(r)) for r in rows]
                tl = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * m) + " |"]
                for r in rows[1:]:
                    tl.append("| " + " | ".join(r) + " |")
                out.append("\n".join(tl))
        elif n == "pre":
            cls = ch.get("class") or []
            lang = "text" if "result" in cls else ""
            out.append("```" + lang + "\n" + ch.get_text().rstrip("\n") + "\n```")
        elif n in ("div", "section", "blockquote", "span", "article"):
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


IMG = {}


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    os.makedirs(os.path.join(OUT, "images"), exist_ok=True)
    nn = 1
    for slug in PAGES:
        url = f"https://www.w3cschool.cn/groovy/{slug}.html"
        html = get(url)
        if not html:
            print("  skip", slug); continue
        soup = BeautifulSoup(html.decode("utf-8", "replace"), "html.parser")
        c = soup.find("div", class_="content-intro")
        if c is None:
            print("  no container", slug); continue
        t = soup.find("h1")
        title = clean(inline(t)) if t else slug
        # 图本地化
        for im in c.find_all("img"):
            src = im.get("src", "")
            if src.startswith("http") and src not in IMG:
                data = get(src, binary=True)
                if data:
                    base = src.rsplit("/", 1)[1] or "img"
                    base = re.sub(r"[^A-Za-z0-9._-]", "_", base)
                    fn = f"{len(IMG):02d}-{base}"
                    open(os.path.join(OUT, "images", fn), "wb").write(data)
                    IMG[src] = "images/" + fn
        body = to_md(c)
        name = f"{nn:02d}-{title.replace('/', '／')}.md"
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(body)
        print(f"  {nn:02d} {slug:36} -> {name} ({len(body)})")
        nn += 1
    print("images:", len(IMG))


if __name__ == "__main__":
    main()
