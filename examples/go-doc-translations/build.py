#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fpb52 #97《Go 官方文档翻译》(golang-china/golangdoc.translations @fe925a2) → 语雀 clean 树

仓库是「golang.org 全站中文化」的半成品翻译工程，三种双语载体，各有明确标记：
  1. doc/zh_CN/*.html         —— 英文块包在 <div class="english">，**删掉它**剩下就是中文
  2. blog/zh_CN/content/*.article —— `.html _tr/div_begin_zh_CN.html` … `.html _tr/div_end.html` 之间是中文
  3. src/**/doc_zh_CN.go      —— 每个 API 先英文注释再中文注释 → 只保留含中文的注释段
只收「确有中文译文」的篇目（tour/talks 全站未翻译 → 不收）。
"""
import os, re, sys, shutil, urllib.parse
import bs4

SRC = "/tmp/g97"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/g97-clean"
CJK = re.compile(r"[\u4e00-\u9fff]")

IMG_CACHE = {}


def sane(name):
    return re.sub(r"[^\w.\-]+", "_", name)


def img_ref(abspath):
    key = abspath
    if key in IMG_CACHE:
        return IMG_CACHE[key]
    local = "../images/" + sane(os.path.basename(os.path.dirname(abspath))) + "_" + sane(os.path.basename(abspath))
    IMG_CACHE[key] = local
    return local


def resolve_img(src, base_dir):
    if src.startswith(("http://", "https://", "data:")):
        return None
    u = urllib.parse.unquote(src)
    cands = [os.path.normpath(os.path.join(base_dir, u)),
             os.path.normpath(os.path.join(SRC, u.lstrip("/"))),
             os.path.normpath(os.path.join(SRC, "doc/zh_CN", u.lstrip("/doc/").lstrip("/"))),
             os.path.normpath(os.path.join(SRC, "blog/zh_CN", u.lstrip("/blog/").lstrip("/"))),
             os.path.normpath(os.path.join(SRC, "blog/zh_CN/content", u.lstrip("/blog/content/").lstrip("/")))]
    for p in cands:
        if os.path.exists(p):
            return p
    # 最后按文件名在仓库里找（原站路径与仓库布局不一致时）
    base = os.path.basename(u)
    hits = [os.path.join(dp, f) for dp, _, fns in os.walk(SRC) if ".git" not in dp for f in fns if f == base]
    return hits[0] if len(hits) == 1 else None


# ---------------- HTML → markdown ----------------
def inline(node, base_dir):
    out = []
    for c in node.children:
        if isinstance(c, bs4.Comment):
            continue
        if isinstance(c, bs4.NavigableString):
            out.append(str(c))
        elif c.name == "img":
            p = resolve_img(c.get("src", ""), base_dir)
            out.append("![图](%s)" % img_ref(p) if p else "")
        elif c.name in ("b", "strong"):
            t = inline(c, base_dir).strip()
            out.append("**%s**" % t if t else "")
        elif c.name in ("i", "em", "cite"):
            t = inline(c, base_dir).strip()
            out.append("*%s*" % t if t else "")
        elif c.name == "code":
            t = c.get_text("", strip=True)
            out.append("`%s`" % t if t else "")
        elif c.name in ("sub",):
            out.append("_{%s}" % inline(c, base_dir).strip())
        elif c.name in ("sup",):
            out.append("^{%s}" % inline(c, base_dir).strip())
        elif c.name == "a":
            href = c.get("href", "")
            t = inline(c, base_dir).strip()
            if href.startswith(("http://", "https://")) and t:
                out.append("[%s](%s)" % (t, href))
            elif href.startswith("#"):
                out.append(t)
            elif href and t:
                out.append("[%s](%s)" % (t, href))
            else:
                out.append(t)
        elif c.name == "br":
            out.append("  \n")
        elif c.name in ("script", "style"):
            continue
        else:
            out.append(inline(c, base_dir))
    s = "".join(out).replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = "\n".join(ln.strip() for ln in s.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def html_to_md(path):
    soup = bs4.BeautifulSoup(open(path, encoding="utf-8", errors="replace").read(), "html5lib")
    for d in soup.find_all("div", class_="english"):
        d.decompose()
    base_dir = os.path.dirname(path)
    body = soup.body or soup
    out = []
    codebuf = []

    def flush():
        if codebuf:
            out.append("```go\n" + "\n".join(codebuf).rstrip() + "\n```")
            codebuf.clear()

    def emit(el):
        if isinstance(el, bs4.Comment):
            return
        if isinstance(el, bs4.NavigableString):
            return
        name = el.name
        if name in ("script", "style", "noscript"):
            return
        if name in ("h1", "h2", "h3", "h4", "h5"):
            flush()
            lvl = int(name[1])
            t = inline(el, base_dir)
            if t:
                out.append("#" * lvl + " " + t)
            return
        if name == "p":
            flush()
            t = inline(el, base_dir)
            if t:
                out.append(t)
            return
        if name == "pre":
            flush()
            t = el.get_text("", False).strip("\n")
            out.append("```go\n" + t.rstrip() + "\n```")
            return
        if name in ("ul", "ol"):
            flush()
            lines = []
            for i, li in enumerate(el.find_all("li", recursive=False), 1):
                t = inline(li, base_dir).replace("\n", " ")
                if t:
                    lines.append(("- " if name == "ul" else "%d. " % i) + t)
            if lines:
                out.append("\n".join(lines))
            return
        if name == "table":
            flush()
            rows = []
            for tr in el.find_all("tr"):
                cells = [inline(c, base_dir).replace("|", "\\|") for c in tr.find_all(["td", "th"])]
                if any(c.strip() for c in cells):
                    rows.append(cells)
            if rows:
                n = max(len(r) for r in rows)
                rows = [r + [""] * (n - len(r)) for r in rows]
                md = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * n) + " |"]
                md += ["| " + " | ".join(r) + " |" for r in rows[1:]]
                out.append("\n".join(md))
            return
        if name == "blockquote":
            flush()
            t = inline(el, base_dir)
            out.append("\n".join("> " + ln for ln in t.split("\n")))
            return
        if name == "hr":
            flush()
            out.append("---")
            return
        if name == "img":
            p = resolve_img(el.get("src", ""), base_dir)
            if p:
                out.append("![图](%s)" % img_ref(p))
            return
        # div / section / center / font / span / dl ... 递归
        for c in el.children:
            emit(c)

    for c in body.children:
        emit(c)
    flush()
    text = "\n\n".join(x for x in out if x.strip())
    return re.sub(r"\n{3,}", "\n\n", text)


# ---------------- .article (blog) → markdown ----------------
def article_to_md(path):
    raw_lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    # 头：第一个 .html _tr/ 标记之前（标题/中文标题/日期/Tags/作者）
    first = next((i for i, l in enumerate(raw_lines) if l.strip().startswith(".html _tr/")), None)
    if first is None:
        return None, None, None
    header = [l.strip() for l in raw_lines[:first] if l.strip()]
    if not any("div_begin_zh_CN" in l for l in raw_lines):
        return None, None, None
    title = (header[0].lstrip("#").strip() if header else os.path.basename(path))
    title_zh = next((l for l in header[1:4] if CJK.search(l) and not l.startswith(("Tags:", "http"))), None)
    date = next((l for l in header[1:5] if re.match(r"^\d{1,2} \w{3} \d{4}$", l)), None)
    tags = next((l[5:].strip() for l in header if l.startswith("Tags:")), None)
    author = next((l for l in header[1:6] if re.match(r"^[A-Z][\w. ]+$", l)), None)
    # 只取中文块
    keep, in_zh = [], False
    for ln in raw_lines[first:]:
        s = ln.strip()
        if s.startswith(".html _tr/div_begin_zh_CN"):
            in_zh = True
            continue
        if s.startswith(".html _tr/div_end") or s.startswith(".html _tr/div_begin_en"):
            in_zh = False
            continue
        if in_zh:
            keep.append(ln)
    meta_line = " ｜ ".join(x for x in [date, author, ("Tags: " + tags) if tags else None] if x)
    md = []
    if meta_line:
        md.append("> " + meta_line)
        md.append("")
    i = 0
    while i < len(keep):
        ln = keep[i]
        s = ln.rstrip()
        if s.strip() == "*":
            i += 1
            continue
        if s.startswith(".code "):
            # .code file /regex1/,/regex2/  或 .code file
            parts = s.split(None, 1)
            spec = parts[1] if len(parts) > 1 else ""
            md.append("<!-- code: %s -->" % spec)
            i += 1
            continue
        if s.startswith(".image "):
            parts = s.split()
            if len(parts) >= 2:
                p = resolve_img(parts[1], os.path.dirname(path)) or resolve_img(parts[1], os.path.join(SRC, "blog/zh_CN"))
                if p:
                    md.append("![图](%s)" % img_ref(p))
            i += 1
            continue
        if s.startswith(".html "):
            i += 1
            continue
        if s.startswith("* "):
            md.append("## " + s[2:].strip())
        elif s.startswith("** "):
            md.append("### " + s[3:].strip())
        elif s.startswith("- "):
            md.append("- " + s[2:].strip())
        elif s.startswith(("    ", "\t")):
            md.append("    " + s.strip())
        else:
            md.append(convert_article_links(s))
        i += 1
    text = "\n".join(md)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return title, title_zh, text


def convert_article_links(s):
    # [[url][text]] / [[url]] ；`code`
    s = re.sub(r"\[\[([^\]]+)\]\[([^\]]*)\]\]", lambda m: "[%s](%s)" % (m.group(2) or m.group(1), m.group(1)), s)
    s = re.sub(r"\[\[([^\]]+)\]\]", lambda m: "[%s](%s)" % (m.group(1), m.group(1)), s)
    return s


# ---------------- src/*/doc_zh_CN.go → markdown ----------------
def godoc_to_md(path, pkg):
    raw = open(path, encoding="utf-8", errors="replace").read()
    lines = raw.split("\n")
    blocks = []       # (kind, payload)
    i = 0
    n = len(lines)
    while i < n:
        ln = lines[i]
        s = ln.strip()
        if s.startswith("//"):
            grp = []
            while i < n and lines[i].strip().startswith("//"):
                grp.append(lines[i])
                i += 1
            blocks.append(("doc", grp))
            continue
        if s.startswith(("func ", "type ", "const (", "var (", "package ")) or re.match(r"^(func|type|var|const)\b", s):
            blocks.append(("decl", s))
            i += 1
            # 跳过函数体/结构体块
            if s.endswith("{"):
                depth = 1
                while i < n and depth > 0:
                    depth += lines[i].count("{") - lines[i].count("}")
                    i += 1
            continue
        i += 1

    md = []
    for kind, payload in blocks:
        if kind == "decl":
            if payload.startswith("package "):
                continue
            md.append("```go\n%s\n```" % payload)
            continue
        grp = payload
        # 找第一处含中文的段落起点
        start = None
        prev_blank = True
        for idx, l in enumerate(grp):
            body = l.strip()[2:].strip()
            if not body:
                prev_blank = True
                continue
            if CJK.search(body):
                start = idx
                break
        if start is None:
            continue
        # 回退到该段落的起始（上一空注释行之后）
        j = start
        while j > 0:
            prev = grp[j - 1].strip()[2:].strip()
            if not prev:
                break
            j -= 1
        chunk = grp[j:]
        text = "\n".join(l.strip()[2:].lstrip(" ") if len(l.strip()) > 2 else "" for l in chunk)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text:
            md.append(text)
    out = ""
    if md:
        out = "\n\n".join(md)
    return out


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "images"), exist_ok=True)
    stats = {"doc": 0, "src": 0, "blog": 0}

    # 1) doc/zh_CN/*.html
    ddir = os.path.join(OUT, "官方文档")
    os.makedirs(ddir, exist_ok=True)
    for f in sorted(os.listdir(os.path.join(SRC, "doc/zh_CN"))):
        if not f.endswith(".html"):
            continue
        md = html_to_md(os.path.join(SRC, "doc/zh_CN", f))
        body_len = max(1, len(md))
        if len(CJK.findall(md)) < 100 or len(CJK.findall(md)) / body_len < 0.05:
            continue
        name = f[:-5]
        with open(os.path.join(ddir, name + ".md"), "w", encoding="utf-8") as fh:
            fh.write("# " + name + "\n\n" + md + "\n")
        stats["doc"] += 1

    # 2) src/**/doc_zh_CN.go
    sroot = os.path.join(OUT, "标准库包文档")
    for dp, _, fns in os.walk(os.path.join(SRC, "src")):
        if "doc_zh_CN.go" not in fns:
            continue
        full = os.path.join(dp, "doc_zh_CN.go")
        rel = os.path.relpath(dp, os.path.join(SRC, "src"))
        pkg = rel.replace(os.sep, "/")
        md = godoc_to_md(full, pkg)
        if len(CJK.findall(md)) < 60 or len(CJK.findall(md)) / max(1, len(md)) < 0.05:
            continue
        dst_dir = os.path.join(sroot, os.path.dirname(pkg)) if "/" in pkg else sroot
        os.makedirs(dst_dir, exist_ok=True)
        with open(os.path.join(dst_dir, os.path.basename(pkg) + ".md"), "w", encoding="utf-8") as fh:
            fh.write("# %s\n\n%s\n" % (pkg, md))
        stats["src"] += 1

    # 3) blog/zh_CN/content/*.article（仅有中文块的）
    bdir = os.path.join(OUT, "博客（中文译文）")
    os.makedirs(bdir, exist_ok=True)
    for f in sorted(os.listdir(os.path.join(SRC, "blog/zh_CN/content"))):
        if not f.endswith(".article"):
            continue
        title, title_zh, md = article_to_md(os.path.join(SRC, "blog/zh_CN/content", f))
        if md is None or len(CJK.findall(md)) < 200:
            continue
        name = f[:-8]
        with open(os.path.join(bdir, name + ".md"), "w", encoding="utf-8") as fh:
            fh.write("# %s\n\n%s\n" % (title_zh or title or name, md))
        stats["blog"] += 1

    print("built:", stats)
    # 拷图进 clean/images（之后由 yuque_rewrite_images.py 传 CDN 并重写）
    n = 0
    for absp, local in IMG_CACHE.items():
        dst = os.path.join(OUT, local.replace("../", ""))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(absp, dst)
        n += 1
    print("images:", n)


main()