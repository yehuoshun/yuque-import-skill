#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#117 前端代码规范 (AlloyTeam/CodeGuide @ 2c2864b, gh-pages)
源 = Jekyll 站点：index.html 拼装 _includes/*.html 分片，代码样例再 {% include css/x.css %}。
口径：展开 include → HTML→md，一篇一大区（命名/HTML/CSS/JS/检查），00-说明=README。
"""
import os, re, shutil, html as htmllib
from bs4 import BeautifulSoup, NavigableString, Comment

CLEAN = "CodeGuide-2c2864b-clean"
OUT = "build"
INC = os.path.join(CLEAN, "_includes")


def expand(text, depth=0):
    if depth > 8:
        return text

    def rep(m):
        inc = m.group(1).strip()
        p = os.path.join(INC, inc)
        if not os.path.exists(p):
            return ""
        return expand(open(p, encoding="utf-8").read(), depth + 1)

    text = re.sub(r"\{%\s*include\s+([^%]+?)\s*%\}", rep, text)

    def hl(m):
        lang = m.group(1).strip()
        body = m.group(2).strip("\n")
        return "\n<pre data-lang=%s>%s</pre>\n" % (lang, htmllib.escape(body))

    text = re.sub(r"\{%\s*highlight\s+(\w+)\s*%\}(.*?)\{%\s*endhighlight\s*%\}", hl, text, flags=re.S)
    text = re.sub(r"\{%.*?%\}", "", text)
    return text


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
        if ch.name in ("script", "style"):
            continue
        if ch.name in ("h1", "h2", "h3", "h4"):
            t = clean(inline(ch))
            if t:
                out.append("#" * int(ch.name[1]) + " " + t)
        elif ch.name == "p":
            t = clean(inline(ch))
            if t:
                out.append(t)
        elif ch.name in ("ul", "ol"):
            lines = []
            for i, li in enumerate(ch.find_all("li", recursive=False), 1):
                b = f"{i}. " if ch.name == "ol" else "- "
                lines.append(b + clean(inline(li)))
            if lines:
                out.append("\n".join(lines))
        elif ch.name == "table":
            rows = [[clean(inline(td)) for td in tr.find_all(["td", "th"])] for tr in ch.find_all("tr")]
            rows = [r for r in rows if r]
            if rows:
                n = max(len(r) for r in rows); rows = [r + [""] * (n - len(r)) for r in rows]
                out.append("| " + " | ".join(rows[0]) + " |")
                out.append("| " + " | ".join(["---"] * n) + " |")
                for r in rows[1:]:
                    out.append("| " + " | ".join(r) + " |")
        elif ch.name in ("div", "section", "article"):
            render(ch, out)
        elif ch.name == "pre":
            lang = (ch.get("data-lang") or "").strip()
            out.append("```" + lang + "\n" + ch.get_text().rstrip("\n") + "\n```")
        else:
            t = clean(inline(ch))
            if t:
                out.append(t)


def to_md(html_):
    soup = BeautifulSoup("<body>" + html_ + "</body>", "html5lib")
    out = []
    render(soup.body, out)
    text = "\n\n".join(x for x in out if x.strip())
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def strip_dup_head(body, title):
    lines = body.split("\n")
    for i, ln in enumerate(lines):
        if ln.strip() == "":
            continue
        s = ln.lstrip("#").strip()
        if ln.startswith("#") and (s == title or s.replace("、", ",") == title or title in s):
            return "\n".join(lines[i + 1:]).lstrip("\n")
        break
    return body


def drop_lead_h2(body):
    lines = body.split("\n")
    for i, ln in enumerate(lines):
        if ln.strip() == "":
            continue
        if ln.startswith("## "):
            return "\n".join(lines[i + 1:]).lstrip("\n")
        break
    return body


def shift_down(body):
    return re.sub(r"^(#{2,6}) ", lambda m: "#" * (len(m.group(1)) - 1) + " ", body, flags=re.M)


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    readme = open(os.path.join(CLEAN, "README.md"), encoding="utf-8").read()
    open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8").write(
        "> 来源：https://github.com/AlloyTeam/CodeGuide @ 2c2864b (gh-pages) ｜ "
        "AlloyTeam 前端代码规范站点（原站 https://alloyteam.github.io/CodeGuide/）；"
        "正文按大区拆篇，代码样例来自 _includes 分片。\n\n" + readme.strip() + "\n")

    idx = open(os.path.join(CLEAN, "index.html"), encoding="utf-8").read()
    idx = re.sub(r"^---.*?---\s*", "", idx, flags=re.S)
    m = re.search(r'<div class="section" id="golden-rule">.*?</div>\s*</div>', idx, re.S)
    docs = [("01-最佳原则.md", m.group(0) if m else "")]
    for i, (fn, title) in enumerate(
        [("naming_rules.html", "命名规则"), ("html_rules.html", "HTML 规范"),
         ("css_rules.html", "CSS、SCSS 规范"), ("js_rules.html", "JavaScript 规范"),
         ("check.html", "检查工具")], start=2):
        docs.append((f"{i:02d}-{title}.md", expand(open(os.path.join(INC, fn), encoding="utf-8").read())))

    for name, html_ in docs:
        body = to_md(html_)
        if name != "00-说明.md":
            body = drop_lead_h2(body)
        if name not in ("00-说明.md", "01-最佳原则.md"):
            body = shift_down(body)
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(body)
        print(f"  {name} ({len(body)} chars)")
    print("done")


if __name__ == "__main__":
    main()
