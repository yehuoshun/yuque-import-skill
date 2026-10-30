#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#111 Network programming with Go 中文翻译版本 (astaxie/NPWG_zh @ 50b2885)
源 = 仓库 zh/ 下的双语 HTML 书（en/zh 同级姊妹块）→ 只保留中文，转 markdown。
一章一篇（index.html 给章序），NN- 前缀免归位。
"""
import os, re, shutil, sys
from bs4 import BeautifulSoup, NavigableString, Comment

SRC = "NPWG_zh-50b2885-clean/zh"
OUT = "build"

def is_en(tag):
    c = tag.get("class") or []
    return "en" in c

FOOTER_RE = re.compile(
    r"Copyright Jan Newmarch|please contribute using Flattr|donate using PayPal|"
    r"版权所有.*Jan Newmarch|如果你喜欢本书.*Flattr")

def skip_tag(tag):
    if tag.name in ("script", "style", "head", "title", "form"):
        return True
    c = tag.get("class") or []
    if "FlattrButton" in c or "generate_from_h2" in c:
        return True
    if "en" in c:
        return True
    if tag.name == "p" and FOOTER_RE.search(tag.get_text()):
        return True
    return False

# ---------- inline ----------
def inline(node):
    out = []
    for ch in node.children:
        if isinstance(ch, Comment):
            continue
        if isinstance(ch, NavigableString):
            out.append(str(ch))
            continue
        n = ch.name
        if n in ("script", "style"):
            continue
        if n == "br":
            out.append("\n"); continue
        if n in ("em", "i"):
            out.append("*" + inline(ch).strip() + "*"); continue
        if n in ("strong", "b"):
            out.append("**" + inline(ch).strip() + "**"); continue
        if n in ("code", "tt", "kbd", "samp"):
            t = ch.get_text()
            out.append("`" + t + "`"); continue
        if n == "a":
            txt = inline(ch).strip()
            href = ch.get("href", "")
            if not href or href.startswith("#") or not re.match(r"(https?:|mailto:)", href):
                out.append(txt); continue
            out.append(f"[{txt}]({href})"); continue
        if n in ("sup", "sub"):
            out.append(("^" if n == "sup" else "_") + inline(ch).strip()); continue
        if n == "img":
            out.append(img_md(ch)); continue
        # span / others
        out.append(inline(ch))
    return "".join(out)

def clean(text):
    # collapse whitespace but keep intentional newlines from <br>
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(lines).strip()

def img_md(tag):
    src = (tag.get("src") or "").strip()
    alt = (tag.get("alt") or "").strip()
    if not src or src.startswith("http") or src.startswith("data:") or "paypalobjects" in src:
        return ""   # 外链/paypal 追踪像素 一律丢
    src = src.replace("../Images/", "Images/")
    return f"![{alt}]({src})"

# ---------- block ----------
def guess_lang(code):
    c = code
    if re.search(r"\bpackage \w+|\bfunc \w+|\bimport \(|:=|go func|chan ", c):
        return "go"
    if re.search(r"^\s*[\$#>] ", c, re.M):
        return "bash"
    return ""

def render_block(tag, out):
    n = tag.name
    if n == "h1":
        return  # 章标题 = 文档标题，丢弃
    if n in ("h2", "h3", "h4", "h5", "h6"):
        lvl = int(n[1])
        txt = clean(inline(tag))
        if txt:
            out.append("#" * lvl + " " + txt)
        return
    if n == "p":
        txt = clean(inline(tag))
        if txt:
            out.append(txt)
        return
    if n == "pre":
        code = tag.get_text()
        lang = guess_lang(code)
        out.append(f"```{lang}\n{code.rstrip(chr(10))}\n```")
        return
    if n in ("ul", "ol"):
        ordered = (n == "ol")
        i = 0
        lines = []
        for li in tag.find_all("li", recursive=False):
            i += 1
            parts = []
            nested = []
            for ch in li.children:
                if isinstance(ch, NavigableString):
                    parts.append(str(ch))
                elif ch.name in ("ul", "ol"):
                    nested.append(ch)
                else:
                    parts.append(inline(ch))
            txt = clean("".join(parts))
            bullet = f"{i}. " if ordered else "- "
            lines.append(bullet + txt)
            for nl in nested:
                sub = []
                render_block(nl, sub)
                for s in sub:
                    lines.append("  " + s)
        out.append("\n".join(lines))
        return
    if n == "blockquote":
        txt = clean(inline(tag))
        for ln in txt.split("\n"):
            out.append("> " + ln)
        return
    if n == "table":
        rows = []
        for tr in tag.find_all("tr"):
            cells = [clean(inline(td)) for td in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)
        if not rows:
            return
        ncol = max(len(r) for r in rows)
        rows = [r + [""] * (ncol - len(r)) for r in rows]
        out.append("| " + " | ".join(rows[0]) + " |")
        out.append("| " + " | ".join(["---"] * ncol) + " |")
        for r in rows[1:]:
            out.append("| " + " | ".join(r) + " |")
        return
    if n == "img":
        m = img_md(tag)
        if m:
            out.append(m)
        return
    if n == "hr":
        out.append("---")
        return
    if n == "div":
        c = tag.get("class") or []
        if "generate_from_h2" in c:
            return
        if "warning" in c:
            txt = clean(inline(tag))
            for ln in txt.split("\n"):
                out.append("> ⚠️ " + ln)
            return
        # generic wrapper → recurse
        render_kids(tag, out)
        return
    # fallback: recurse
    render_kids(tag, out)

def render_kids(root, out):
    for ch in root.children:
        if isinstance(ch, Comment):
            continue
        if isinstance(ch, NavigableString):
            t = clean(str(ch))
            if t:
                out.append(t)
            continue
        if skip_tag(ch):
            continue
        if ch.name in ("div", "section", "article", "span"):
            c = ch.get("class") or []
            if ch.name == "div":
                render_block(ch, out)
            else:
                t = clean(inline(ch))
                if t:
                    out.append(t)
            continue
        render_block(ch, out)

HRE = re.compile(r"^(#{1,6}) (.*)$")
def has_cjk(s):
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)

def render_doc(html):
    soup = BeautifulSoup(html, "html5lib")
    out = []
    render_kids(soup.body, out)
    out = [x for x in out if x.strip() != ""]
    # 折叠「英文标题 + 中文标题」相邻同级对（class-less 的那种）
    cleaned = []
    i = 0
    while i < len(out):
        m = HRE.match(out[i])
        if m and i + 1 < len(out):
            m2 = HRE.match(out[i + 1])
            if m2 and m2.group(1) == m.group(1) and has_cjk(m2.group(2)) and not has_cjk(m.group(2)):
                i += 1  # 丢掉英文那条
                continue
        cleaned.append(out[i])
        i += 1
    text = "\n\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"

def chapter_title(html):
    soup = BeautifulSoup(html, "html5lib")
    h1s = soup.body.find_all("h1")
    for tag in h1s:
        c = tag.get("class") or []
        if ("zh" in c or "cn" in c):
            return clean(inline(tag))
    for tag in h1s:
        if has_cjk(clean(inline(tag))):
            return clean(inline(tag))
    if h1s:
        return clean(inline(h1s[0]))
    return None

def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    # chapter order from index.html
    idx = BeautifulSoup(open(os.path.join(SRC, "index.html"), encoding="utf-8").read(), "html5lib")
    order = []
    for a in idx.find_all("a"):
        href = a.get("href", "")
        m = re.search(r"Text/(chapter-[\w-]+\.html)$", href)
        if m and m.group(1) not in order:
            order.append(m.group(1))
    print("chapter order:", len(order))
    # 00-说明
    rm = open("NPWG_zh-50b2885-clean/README.md", encoding="utf-8").read().strip()
    open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8").write(
        "> 来源：https://github.com/astaxie/NPWG_zh @ 50b2885 ｜ "
        "《Network Programming with Go》(Jan Newmarch) 中文翻译版；"
        "原书为 en/zh 双语 HTML，本库只保留中文；正文一章一篇。\n\n" + rm + "\n")
    nn = 1
    for fn in order:
        html = open(os.path.join(SRC, "Text", fn), encoding="utf-8").read()
        title = chapter_title(html) or fn
        title = title.replace("/", "／")
        body = render_doc(html)
        name = f"{nn:02d}-{title}.md"
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(body)
        print(f"  {nn:02d} {fn:30} -> {name} ({len(body)} chars)")
        nn += 1
    # errata
    er = open("NPWG_zh-50b2885-clean/Errata.md", encoding="utf-8").read().strip()
    open(os.path.join(OUT, "90-勘误.md"), "w", encoding="utf-8").write(er + "\n")
    # images
    shutil.copytree(os.path.join(SRC, "Images"), os.path.join(OUT, "Images"))
    print("done")

if __name__ == "__main__":
    main()
