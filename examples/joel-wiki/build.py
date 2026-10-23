#!/usr/bin/env python3
"""CC 快照 (local.joelonsoftware.com wiki 页 Chinese (Simplified)) -> 语雀 md。
MediaWiki Monobook: 正文在 div#bodyContent, 12 个 h2 章节 = 12 篇中文译本, 按 h2 拆篇。
"""
import os, re, html as H
from bs4 import BeautifulSoup, NavigableString, Tag

SRC = os.path.join(os.path.dirname(__file__), "page.html")
OUT = os.path.join(os.path.dirname(__file__), "site")

INLINE_MAP = {"b": "**", "strong": "**", "i": "*", "em": "*"}


def inline(node):
    if isinstance(node, NavigableString):
        return re.sub(r"\s+", " ", str(node))
    if not isinstance(node, Tag):
        return ""
    t = node.name
    if t == "br":
        return "\n"
    if t == "img":
        return ""  # 源站已下线 + CC 快照无图 -> 丢弃（正文末统一注明）
    if t == "a":
        txt = "".join(inline(c) for c in node.children).strip()
        href = node.get("href") or ""
        if not txt:
            return ""
        if href.startswith("#") or href.startswith("/mediawiki/index.php?title=Chinese"):
            return txt
        return f"[{txt}]({href})"
    if t in INLINE_MAP:
        txt = "".join(inline(c) for c in node.children).strip()
        if not txt:
            return ""
        m = INLINE_MAP[t]
        return f"{m}{txt}{m}"
    if t == "span":
        return "".join(inline(c) for c in node.children)
    if t in ("sup", "sub"):
        return f"<{t}>" + "".join(inline(c) for c in node.children) + f"</{t}>"
    return "".join(inline(c) for c in node.children)


def blocks(container):
    out = []
    for el in container.children:
        if isinstance(el, NavigableString):
            s = str(el).strip()
            continue
        if not isinstance(el, Tag):
            continue
        n = el.name
        if n == "p":
            txt = inline(el).strip()
            txt = re.sub(r"\n{2,}", "\n", txt)
            if txt:
                out.append(txt)
        elif n in ("h1", "h2", "h3", "h4", "h5", "h6"):
            txt = inline(el).strip()
            lvl = min(6, int(n[1]))
            if txt:
                out.append("#" * lvl + " " + txt)
        elif n == "ul":
            lines = []
            for li in el.find_all("li", recursive=False):
                txt = inline(li).strip()
                if txt:
                    lines.append("- " + txt)
            if lines:
                out.append("\n".join(lines))
        elif n == "ol":
            lines = []
            for i, li in enumerate(el.find_all("li", recursive=False), 1):
                txt = inline(li).strip()
                if txt:
                    lines.append(f"{i}. " + txt)
            if lines:
                out.append("\n".join(lines))
        elif n == "pre":
            txt = el.get_text()
            out.append("```\n" + txt.strip("\n") + "\n```")
        elif n in ("blockquote",):
            txt = "\n".join("> " + ln for ln in inline(el).strip().split("\n"))
            out.append(txt)
        elif n == "table":
            rows = []
            for tr in el.find_all("tr"):
                cells = [inline(td).strip() for td in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)
            if rows:
                w = max(len(r) for r in rows)
                rows = [r + [""] * (w - len(r)) for r in rows]
                md = ["| " + " | ".join(rows[0]) + " |",
                      "|" + "|".join([" --- "] * w) + "|"]
                for r in rows[1:]:
                    md.append("| " + " | ".join(r) + " |")
                out.append("\n".join(md))
        elif n == "div":
            if el.get("id") in ("toc", "toctitle"):
                continue
            out.extend(blocks(el))
        elif n == "dl":
            for dt in el.find_all("dt"):
                out.append("**" + inline(dt).strip() + "**")
            for dd in el.find_all("dd"):
                out.append(inline(dd).strip())
        # skip script/style/others
    return [b for b in out if b.strip()]


def main():
    raw = open(SRC, encoding="utf-8", errors="replace").read()
    start = raw.find('<div id="bodyContent">')
    end = raw.find('<div class="printfooter">')
    if end < 0:
        end = raw.find('<div id="footer"')
    soup = BeautifulSoup(raw[start:end], "html.parser")
    body = soup.find("div", id="bodyContent")
    for junk in body.select("#siteSub, #contentSub, #jump-to-nav, #toc, #toctitle"):
        junk.decompose()

    # 按 h2 切章节
    sections = []
    cur_title, cur_nodes = None, []
    for el in body.children:
        if isinstance(el, Tag) and el.name == "h2":
            title = inline(el).strip()
            if title == "Contents":
                if cur_title is not None:
                    sections.append((cur_title, cur_nodes))
                cur_title, cur_nodes = None, []
                continue
            if cur_title is not None:
                sections.append((cur_title, cur_nodes))
            cur_title, cur_nodes = title, []
        elif cur_title is not None:
            cur_nodes.append(el)
    if cur_title is not None:
        sections.append((cur_title, cur_nodes))

    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".md"):
            os.remove(os.path.join(OUT, f))

    manifest = []
    for i, (title, nodes) in enumerate(sections, 1):
        frag = BeautifulSoup("<div></div>", "html.parser").div
        for nd in nodes:
            frag.append(nd)
        bs = blocks(frag)
        content = "\n\n".join(bs)
        content = content.replace("<a>", "\\<a>")  # 正文里的字面 <a> 需转义
        if title == "给计算机系学生的建议":
            content += ("\n\n> 注：原文本节含 5 张插图（CA1–CA5.jpg），"
                        "源站已下线、Common Crawl 快照未收录图片，故省略。")
        safe = title.replace("/", "／").replace("\\", "＼")
        fname = f"{i:02d}-{safe}.md"
        open(os.path.join(OUT, fname), "w", encoding="utf-8").write(content + "\n")
        manifest.append((fname, len(content)))
        print(f"{fname}  chars={len(content)}")
    print("total sections:", len(sections))


if __name__ == "__main__":
    main()