#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""#174 楚狂人的D3教程（博客园 winleisure D3.js 标签 7 篇）
网站口径：7 篇学习笔记（译自 dashingd3js.com 的 D3.js 教程）+ 00-说明。
dashingd3js.com 图床已死（404）→ 原图缺失标注；cnblogs 图床 1 张下载传 CDN。
"""
import html as H
import os, re, shutil, subprocess, urllib.request

RAW = "/home/admin/.openclaw/workspace/tmp/fpb174-raw"
OUT = "/home/admin/.openclaw/workspace/tmp/fpb174-site"
IMGDIR = "/home/admin/.openclaw/workspace/tmp/fpb174-imgs"
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT, exist_ok=True)
os.makedirs(IMGDIR, exist_ok=True)

PAGES = [
    ("3512890", "01-DOM上的数据绑定"),
    ("3514451", "02-使用绑定在DOM上的数据"),
    ("3515128", "03-创建基于数据的SVG元素"),
    ("3516320", "04-使用SVG坐标空间"),
    ("3517047", "05-将数据结构化为D3.js可处理的"),
    ("3517998", "06-SVG基础图形和D3.js"),
    ("3522305", "07-动态SVG坐标空间"),
]

def extract_body(h):
    i = h.find('<div id="cnblogs_post_body"')
    if i == -1:
        return ""
    j, depth = i, 0
    while j < len(h):
        o = h.find('<div', j)
        c = h.find('</div>', j)
        if o != -1 and (c == -1 or o < c):
            depth += 1
            j = o + 4
        else:
            depth -= 1
            j = c + 6
            if depth == 0:
                return h[i:j]
    return h[i:]

def render(el):
    """HTML 片段 → markdown（递归处理块级/行内）。"""
    m = re.match(r'<([a-zA-Z0-9]+)([^>]*)>(.*)</\1>', el, re.S)
    if not m:
        return strip_tags(el)
    tag, attrs_s, inner = m.group(1), m.group(2), m.group(3)
    attrs = dict(re.findall(r'([a-zA-Z-]+)="([^"]*)"', attrs_s))
    body = render_children(inner) if inner else ""
    t = tag.lower()
    if t in ("p", "div", "section", "article", "center"):
        return body.strip() + "\n\n" if body.strip() else ""
    if t in ("h1", "h2", "h3", "h4", "h5"):
        return "#" * int(t[1]) + " " + body.strip() + "\n\n"
    if t == "pre":
        # 代码块：剥 span 高亮，取纯文本
        code = strip_tags(inner)
        code = H.unescape(code)
        if "javascript" in attrs.get("class", "") or "lang" in attrs.get("class", ""):
            lang = "javascript"
        else:
            lang = detect_lang(code)
        return "```" + lang + "\n" + code.rstrip() + "\n```\n\n"
    if t in ("ul", "ol"):
        items = re.findall(r'<li[^>]*>(.*?)</li>', inner, re.S)
        out = []
        for it in items:
            # 剥嵌套列表
            sub = re.search(r'<(ul|ol)[^>]*>.*?</\1>', it, re.S)
            itxt = re.sub(r'<(ul|ol)[^>]*>.*?</\1>', '', it, flags=re.S)
            prefix = "- " if t == "ul" else "1. "
            out.append(prefix + render_children(itxt).strip())
            if sub:
                out.append("  " + render(sub.group(0)).strip().replace("\n", "\n  "))
        return "\n".join(out) + "\n\n"
    if t == "li":
        return render_children(inner).strip()
    if t == "table":
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', inner, re.S)
        mdrows = []
        for r in rows:
            cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', r, re.S)
            mdrows.append("| " + " | ".join(strip_tags(c).strip() for c in cells) + " |")
        if mdrows:
            head = mdrows[0]
            sep = "| " + " | ".join(["---"] * (head.count("|") - 1)) + " |"
            return "\n".join([head, sep] + mdrows[1:]) + "\n\n"
        return ""
    if t == "blockquote":
        return "> " + body.strip().replace("\n", "\n> ") + "\n\n"
    if t == "img":
        src = attrs.get("data-src") or attrs.get("src") or ""
        alt = attrs.get("alt", "")
        if src.startswith("//"):
            src = "https:" + src
        return f"![{alt}]({src})"
    if t in ("a",):
        href = attrs.get("href", "")
        if not href or href.startswith("#"):
            return body
        if body.strip().startswith("!["):
            # 博客园「点图看大图」包装：图已是全尺寸，剥链接防死链
            return body
        return f"[{body}]({href})"
    if t in ("code", "tt", "kbd", "samp"):
        return "`" + strip_tags(inner) + "`"
    if t in ("b", "strong"):
        return "**" + body + "**"
    if t in ("i", "em"):
        return "*" + body + "*"
    if t in ("br", "hr"):
        return "\n"
    if t == "script" or t == "style":
        return ""
    if t in ("font", "span", "small", "big", "sup", "sub", "u", "del", "s"):
        return body
    return body


def render_children(inner):
    out = []
    # 自闭合标签（img/br/hr）先行处理
    inner = re.sub(r'<img\s+([^>]*?)/?>',
                   lambda m: img_md(m.group(1)), inner)
    inner = re.sub(r'<br\s*/?>', '\n', inner)
    # 块级分割：按顶层标签
    pos = 0
    for m in re.finditer(r'<([a-zA-Z0-9]+)([^>]*)>(.*?)</\1>', inner, re.S):
        if m.start() > pos:
            txt = inner[pos:m.start()]
            txt = strip_tags(txt)
            if txt.strip():
                out.append(H.unescape(txt))
        out.append(render(m.group(0)))
        pos = m.end()
    if pos < len(inner):
        txt = strip_tags(inner[pos:])
        if txt.strip():
            out.append(H.unescape(txt))
    return "\n".join(x for x in out if x)


def img_md(attrs_s):
    attrs = dict(re.findall(r'([a-zA-Z-]+)="([^"]*)"', attrs_s))
    src = attrs.get("data-src") or attrs.get("src") or ""
    alt = attrs.get("alt", "")
    if src.startswith("//"):
        src = "https:" + src
    return f"![{alt}]({src})"

def strip_tags(s):
    s = re.sub(r'<script.*?</script>', '', s, flags=re.S)
    s = re.sub(r'<style.*?</style>', '', s, flags=re.S)
    s = re.sub(r'<br\s*/?>', '\n', s)
    s = re.sub(r'<[^>]+>', '', s)
    return s

def detect_lang(code):
    if re.search(r'\b(function|var|var |console\.|\$\()|\{', code) and '{' in code:
        return "javascript"
    if re.search(r'<!doctype html|<html|<body', code, re.I):
        return "html"
    return ""

# 主流程
for pid, name in PAGES:
    h = open(f"{RAW}/{pid}.html", encoding="utf-8", errors="replace").read()
    body = extract_body(h)
    md = render(body) if body else ""
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    # 死图标注：dashingd3js.com 已关闭，全部 404
    md = re.sub(r'!\[([^\]]*)\]\(https://www\.dashingd3js\.com/[^)]*\)',
                r'> 🖼 原图缺失（原站 dashingd3js.com 已关闭）：\1', md)
    with open(f"{OUT}/{name}.md", "w", encoding="utf-8") as f:
        f.write(md + "\n")

# 00-说明
with open(f"{OUT}/00-说明.md", "w", encoding="utf-8") as f:
    f.write("> 来源：https://www.cnblogs.com/winleisure/tag/D3.js/（博客园·楚狂人） ｜ 楚狂人《D3.js学习笔记》系列 7 篇（2014-01~02，译自 dashingd3js.com 的 D3.js 教程） ｜ 导入 2026-11-01\n\n"
            "楚狂人（博客园 winleisure）的 D3.js 学习笔记系列，共 7 篇：DOM 数据绑定 → 使用绑定数据 → 创建 SVG 元素 → SVG 坐标空间 → 数据结构化 → SVG 基础图形 → 动态 SVG 坐标空间。\n\n"
            "原文站 dashingd3js.com 已关闭（图片全部 404），配图已标注缺失；1 张博客园图床图已转语雀 CDN。\n")

# 下载 cnblogs 图床 1 张
img_url = "https://images0.cnblogs.com/blog/472695/201401/131515170174.png"
try:
    req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    fn = os.path.join(IMGDIR, "131515170174.png")
    open(fn, "wb").write(data)
    # 重写引用
    for f in os.listdir(OUT):
        p = os.path.join(OUT, f)
        txt = open(p, encoding="utf-8").read()
        if "131515170174.png" in txt:
            txt = txt.replace(img_url, "images/131515170174.png")
            open(p, "w", encoding="utf-8").write(txt)
    print("[#174] cnblogs 图下载:", len(data), "B")
except Exception as e:
    print("[#174] cnblogs 图下载失败:", e)

files = sorted(os.listdir(OUT))
print(f"[#174] 节点 {len(files)}")
for f in files:
    print("  ", f, os.path.getsize(f"{OUT}/{f}"), "B")