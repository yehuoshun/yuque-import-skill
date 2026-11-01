#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wizardforcel electron-doc（GitBook 2.x 嵌套树）→ markdown 树。

书：《Electron 中文文档》（wizardforcel.gitbooks.io/electron-doc/content/）
结构：ul.summary 侧栏 = 嵌套树（组节点 = 空壳页 + 子节点）；正文容器 section.normal
无图（全站 0 img）→ 不涉及 CDN。

树形重建：组节点（带子节点）→ TITLE 目录 + 00-本章导读.md（组页正文，通常只剩标题+链接列表）；
叶子页 → NN-标题.md（零填充前缀，剥编号前缀与反引号）。
"""
import argparse
import os
import re
import time
import urllib.request

from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
BASE = "https://wizardforcel.gitbooks.io/electron-doc/content/"


def fetch(url):
    last = None
    for i in range(6):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 + 2 * i)
    raise RuntimeError("fetch fail %s: %r" % (url, last))


def safe(name):
    name = re.sub(r"\s+", " ", name).strip()
    name = name.replace("/", "／")
    name = name.replace("`", "")
    name = name.replace("\\", "／")
    name = name.replace("<", "").replace(">", "")
    return name


def strip_num(title):
    """'2.1. 支持平台' -> '支持平台'；'4.5.2. `<webview>` 标签' -> 'webview 标签'"""
    t = re.sub(r"^\s*\d+(\.\d+)*\s*\.?\s*", "", title).strip()
    t = t.replace("`", "").strip()
    return t or title


def inline(el, page_url, out):
    from bs4.element import NavigableString
    for c in el.children:
        if isinstance(c, NavigableString):
            out.append(str(c))
        elif c.name == "br":
            out.append("\n")
        elif c.name in ("strong", "b"):
            t = []
            inline(c, page_url, t)
            if "".join(t).strip():
                out.append("**" + "".join(t).strip() + "**")
        elif c.name in ("em", "i"):
            t = []
            inline(c, page_url, t)
            if "".join(t).strip():
                out.append("*" + "".join(t).strip() + "*")
        elif c.name in ("code", "tt", "kbd"):
            out.append("`" + c.get_text().strip() + "`")
        elif c.name == "img":
            src = c.get("src", "")
            alt = c.get("alt", "") or ""
            out.append("![%s](%s)" % (alt, src))
        elif c.name == "a":
            href = c.get("href", "")
            t = []
            inline(c, page_url, t)
            txt = "".join(t).strip()
            if not href or href.startswith("#") or re.search(r"\.html?($|#)", href) \
                    or href.startswith("./") or href.startswith("../"):
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
    from bs4.element import NavigableString
    for c in el.children:
        if isinstance(c, NavigableString):
            t = str(c).strip()
            if t:
                out.append(t)
            continue
        if c.name in ("script", "style"):
            continue
        if c.get("class") and "anchor" in (c.get("class") or []):
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


def page_to_md(url, title):
    soup = BeautifulSoup(fetch(url).decode("utf-8", "replace"), "html.parser")
    sec = soup.select_one("section.normal")
    if not sec:
        return None
    out = []
    render(sec, out, url)
    md = "\n\n".join(out)
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
    # 剥首个 H1（标题由文件名承担）；组页只剩标题+链接列表也保留列表
    lines = md.split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines.pop(0)
    md = "\n".join(lines).strip() + "\n"
    return md


def build_tree(root_ul, out_root):
    """递归建树：返回节点数。组（有子 ul）→ TITLE 目录；叶子 → 文档
    编号规则：每个 ul 内 li 从 1 独立编号（与 summary 序一致），非页面项不占编号。"""
    n = 0
    idx = [0]

    def _li_to_node(li, base, counter):
        nonlocal n
        a = li.find("a")
        href = (li.get("data-path") or (a.get("href") if a else "") or "").lstrip("./")
        title = a.get_text(" ", strip=True) if a else ""
        child_uls = li.find_all("ul", recursive=False)
        if not href or title.startswith("Electron 中文文档"):
            for cu in child_uls:
                _ul_walk(cu, base, counter)
            return
        counter[0] += 1
        c = counter[0]
        sub = strip_num(title)
        if child_uls:
            dname = "%02d-%s" % (c, safe(sub) if sub else safe(title))
            dpath = os.path.join(base, dname)
            os.makedirs(dpath, exist_ok=True)
            md = page_to_md(BASE + href, title)
            if md is not None and md.strip():
                with open(os.path.join(dpath, "00-本章导读.md"), "w", encoding="utf-8") as f:
                    f.write(md)
                n += 1
                print("  [DIR] %s +导读 %dB" % (dname, len(md)))
            for cu in child_uls:
                _ul_walk(cu, dpath, [0])
        else:
            md = page_to_md(BASE + href, title)
            if md is not None:
                fn = "%02d-%s.md" % (c, safe(sub) if sub else safe(title))
                with open(os.path.join(base, fn), "w", encoding="utf-8") as f:
                    f.write(md)
                n += 1
                print("  [DOC] %s %dB" % (fn, len(md)))

    def _ul_walk(ul, base, counter):
        for li in ul.find_all("li", recursive=False):
            _li_to_node(li, base, counter)

    _ul_walk(root_ul, out_root, idx)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/fpb177-electron/site")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    idx = fetch(BASE + "index.html").decode("utf-8", "replace")
    soup = BeautifulSoup(idx, "html.parser")
    summary = soup.select_one("ul.summary")
    n = build_tree(summary, args.out)
    print("TOTAL NODES:", n)


if __name__ == "__main__":
    main()