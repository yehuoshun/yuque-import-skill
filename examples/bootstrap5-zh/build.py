#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""#121 Bootstrap 5 繁體中文手冊 (bootstrap5.hexschool.com, docs/5.1)

站点是 twbs/bootstrap v5.1 文档的繁中译本（六角學院），无公开 md 源仓库
→ 网站口径：抓 docs/5.1/*/ 页面 HTML，正文取 div.bd-content，按其结构转 md。
分组/篇名/顺序全部来自站点侧栏 nav#bd-docs-nav。
"""
import os, re, json, shutil, sys, time, urllib.request

BASE = "https://bootstrap5.hexschool.com"
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
OUT = os.path.join(HERE, "build")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36")


def fetch(url, cache):
    path = os.path.join(RAW, cache)
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        return open(path, encoding="utf-8").read()
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read().decode("utf-8", "replace")
            os.makedirs(RAW, exist_ok=True)
            open(path, "w", encoding="utf-8").write(data)
            return data
        except Exception as e:
            print("  retry", i, url, e)
            time.sleep(2 + i * 3)
    raise RuntimeError(url)


# ---------- inline ----------
def inline(el):
    from bs4 import NavigableString, Tag
    out = []
    for ch in el.children:
        if isinstance(ch, NavigableString):
            out.append(re.sub(r"[ \t\r\n]+", " ", str(ch)))
        elif isinstance(ch, Tag):
            n = ch.name
            t = ch.get_text(" ", strip=False) if n not in ("br", "img") else ""
            if n in ("strong", "b"):
                out.append("**" + inline(ch).strip() + "**")
            elif n in ("em", "i"):
                out.append("*" + inline(ch).strip() + "*")
            elif n == "code":
                c = ch.get_text("", strip=False)
                out.append("`" + c + "`")
            elif n == "a":
                txt = inline(ch).strip()
                href = ch.get("href", "")
                if href.startswith("#") or not href:
                    out.append(txt)
                elif href.startswith("/docs/"):
                    out.append(f"[{txt}]({BASE}{href})")
                else:
                    out.append(f"[{txt}]({href})")
            elif n == "br":
                out.append("\n")
            elif n == "img":
                src = ch.get("src", "")
                alt = ch.get("alt", "")
                out.append(f"![{alt}]({norm_img(src)})" if src else "")
            elif n in ("span", "small", "mark", "kbd", "sup", "sub", "abbr", "u", "s", "del", "ins", "var", "samp"):
                out.append(inline(ch))
            else:
                out.append(inline(ch))
    s = "".join(out)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" *\n *", " ", s)
    return s


def norm_img(src):
    if src.startswith("/docs/5.1/assets/"):
        return "assets/" + src[len("/docs/5.1/assets/"):]
    if src.startswith("/docs/5.1/"):
        return "assets/" + src[len("/docs/5.1/"):]
    return src


IMG_REFS = set()


def block(el, depth=0):
    """把一个 block 元素转 md 文本"""
    from bs4 import Tag
    n = el.name
    cls = " ".join(el.get("class") or [])
    if n in ("script", "style", "svg", "nav", "footer", "button"):
        return ""
    if "bd-example" in cls:
        return ""
    if "bd-clipboard" in cls:
        return ""
    if n == "h1":
        return ""
    if n in ("h2", "h3", "h4", "h5", "h6"):
        lvl = int(n[1])
        lvl = min(lvl, 6)
        return "#" * lvl + " " + inline(el).strip().replace("\n", " ") + "\n\n"
    if n == "p":
        t = inline(el).strip()
        return (t + "\n\n") if t else ""
    if n == "hr":
        return "---\n\n"
    if n == "pre":
        return code_block(el)[0]
    if n == "table":
        return table_md(el)
    if n in ("ul", "ol"):
        lines = []
        for i, li in enumerate(el.find_all("li", recursive=False), 1):
            txt = inline(li).strip()
            sub = "\n".join(block(x).strip() for x in li.find_all(["ul", "ol"], recursive=False))
            bullet = f"{i}." if n == "ol" else "-"
            lines.append(f"{bullet} {txt}")
            if sub:
                lines += ["  " + ln for ln in sub.split("\n")]
        return "\n".join(lines) + "\n\n"
    if n == "blockquote":
        inner = "".join(block(c) for c in el.children if isinstance(c, Tag))
        return "\n".join("> " + ln for ln in inner.strip().split("\n")) + "\n\n"
    if n == "div":
        if "list-group" in cls and el.find("img"):
            lines = []
            for a in el.find_all("a", recursive=False):
                lines.append("- " + inline(a).strip())
            return "\n".join(lines) + "\n\n"
        if "highlight" in cls or "chroma" in cls:
            return code_block(el.find("pre"))[0]
        if "bd-callout" in cls:
            return callout(el)
        inner = "".join(block(c) for c in el.children if isinstance(c, Tag))
        return inner
    if n == "figure":
        return "".join(block(c) for c in el.children if isinstance(c, Tag))
    if n == "img":
        src = el.get("src", "")
        return f"![{el.get('alt','')}]({norm_img(src)})\n\n" if src else ""
    if n in ("section", "main", "article", "span", "a", "strong", "b", "em", "i", "code", "small", "dl", "dt", "dd"):
        if n in ("dl", "dt", "dd"):
            return inline(el).strip() + "\n\n"
        return inline(el)
    inner = "".join(block(c) for c in el.children if isinstance(c, Tag))
    return inner


def code_block(pre):
    from bs4 import Tag
    if pre is None or not isinstance(pre, Tag):
        return ("", "")
    code = pre.find("code")
    lang = ""
    if code is not None:
        for c in code.get("class") or []:
            if c.startswith("language-"):
                lang = c[len("language-"):]
        body = code.get_text("", strip=False)
    else:
        body = pre.get_text("", strip=False)
    body = body.replace("\r\n", "\n").strip("\n")
    return ("```" + lang + "\n" + body + "\n```\n\n", lang)


def table_md(tb):
    rows = []
    for tr in tb.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        vals = []
        for c in cells:
            t = inline(c).strip().replace("\n", " ").replace("|", "\\|")
            vals.append(t)
        rows.append(vals)
    if not rows:
        return ""
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |", "|" + "|".join(["---"] * ncol) + "|"]
    for r in rows[1:]:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out) + "\n\n"


def callout(el):
    from bs4 import Tag
    title = ""
    body = []
    for ch in el.children:
        if not isinstance(ch, Tag):
            continue
        if ch.name in ("h3", "h4", "h5", "strong") and not title:
            title = inline(ch).strip()
            continue
        t = block(ch)
        if t.strip():
            body.append(t.strip())
    lines = []
    if title:
        lines.append("> **" + title + "**")
        lines.append(">")
    for b in body:
        for ln in b.split("\n"):
            lines.append("> " + ln if ln.strip() else ">")
    return "\n".join(lines) + "\n\n"


def convert_page(html):
    from bs4 import BeautifulSoup
    s = BeautifulSoup(html, "html5lib")
    for t in s.find_all(["script", "style", "nav", "footer"]):
        t.decompose()
    h1 = s.find("h1", class_="bd-title")
    title = h1.get_text(" ", strip=True) if h1 else ""
    lead = ""
    lp = s.find("p", class_="bd-lead")
    if lp:
        lead = inline(lp).strip()
    content = s.find("div", class_="bd-content")
    if content is None:
        return title, lead, ""
    parts = []
    for ch in content.children:
        from bs4 import Tag
        if isinstance(ch, Tag):
            parts.append(block(ch))
    md = "".join(parts)
    md = re.sub(r"\n{3,}", "\n\n", md)
    # 收集图片
    for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", md):
        src = m.group(1)
        if not src.startswith("http"):
            IMG_REFS.add(src)
    return title, lead, md.strip() + "\n"


def main():
    nav_html = fetch(BASE + "/docs/5.1/getting-started/introduction/", "intro.html")
    from bs4 import BeautifulSoup
    s = BeautifulSoup(nav_html, "html5lib")
    nav = s.find("nav", {"id": "bd-docs-nav"})
    groups = []
    for li in nav.find("ul").find_all("li", recursive=False):
        btn = li.find("button")
        ul = li.find("ul")
        if not btn or not ul:
            continue
        g = btn.get_text(strip=True)
        pages = [(a.get("href"), a.get_text(" ", strip=True)) for a in ul.find_all("a")]
        groups.append((g, pages))

    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    open(os.path.join(OUT, "00-說明.md"), "w", encoding="utf-8").write(
        "> 来源：https://bootstrap5.hexschool.com/docs/5.1/ ｜ Bootstrap 5.1 官方文件繁體中文手冊"
        "（六角學院 hexschool 译本，上游 twbs/bootstrap v5.1）｜ 抓取 2026-10-31\n>\n"
        "> 站点侧栏 10 个分区、97 篇正文全部收录；「Examples」實例示範頁（30 个纯演示页）与 /docs/versions/ 未收。\n"
        "> 正文按站点结构转 Markdown：`bd-example` 预览块丢弃、`highlight` 代码块保留原文、`bd-callout` 转引用块。\n")

    total = 0
    for g, pages in groups:
        gdir = os.path.join(OUT, g)
        os.makedirs(gdir, exist_ok=True)
        for i, (href, ptitle) in enumerate(pages, 1):
            slug = href.strip("/").split("/")[-1]
            cache = f"{g}-{slug}.html"
            html = fetch(BASE + href, cache)
            title, lead, md = convert_page(html)
            name = f"{i:02d}-{ptitle.replace('/', '／')}.md"
            head = f"> {lead}\n\n" if lead else ""
            md = md.replace("](assets/", "](../assets/").replace('src="assets/', 'src="../assets/')
            open(os.path.join(gdir, name), "w", encoding="utf-8").write(head + md)
            total += 1
            print(f"  {href:60} -> {g}/{name} ({len(md)}B)")
    # 根级：迁移指南
    try:
        html = fetch(BASE + "/docs/5.1/migration/", "migration.html")
        title, lead, md = convert_page(html)
        head = f"> {lead}\n\n" if lead else ""
        open(os.path.join(OUT, "90-" + (title or "遷移指南").replace("/", "／") + ".md"),
             "w", encoding="utf-8").write(head + md)
        total += 1
        print("  root -> 90-", title)
    except Exception as e:
        print("  migration skip", e)

    # 图片本地化
    for r in sorted(IMG_REFS):
        s_url = BASE + "/docs/5.1/" + r
        dst = os.path.join(OUT, r)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            req = urllib.request.Request(s_url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as resp:
                open(dst, "wb").write(resp.read())
        except Exception as e:
            print("  img fail", s_url, e)
    print("docs:", total, "images:", len(IMG_REFS))


if __name__ == "__main__":
    main()