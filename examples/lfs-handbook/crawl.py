#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LFS 6.2 中文版（jinbuguo.com/lfs/lfs62 镜像，DocBook XSL 多页站）→ markdown 导入树

来源：github.com/p-moon/develop-reference-data 的 www.jinbuguo.com/lfs/lfs62 镜像
（源站 works.jinbuguo.com 已 NXDOMAIN，www.jinbuguo.com 502，2026-10-17 实测）

结构：navheader / div.wrap(正文) / navfooter；正文块 = titlepage(h1.sect1/chapter) +
package(segmentedlist 属性) + installation(安装流程, 每小节一个) + note/important 提示 +
pre.userinput(命令) + pre.screen(输出) + variablelist + itemizedlist。

图片只有 5 个装饰 icon（note/important/tip/warning/caution png）→ 全跳过，无 CDN。
"""
import os, re, json, sys
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "pmoon", "www.jinbuguo.com", "lfs", "lfs62")
CLEAN = os.path.join(ROOT, "clean")
ADM = {"note": "注意", "tip": "提示", "important": "重要", "warning": "警告", "caution": "当心", "warning2": "警告"}

# ---------- 页面清单（章名取自各章首页 h1，节序取自 index.html div.toc） ----------
# (输出相对路径, 源文件相对路径)
PAGES = [
    ("00-前言与全书目录.md", "index.html"),
]
# prologue + 章页 + 附录 的运行期扫描：先固定目录骨架，页面由 toc 树生成


def main_container(soup):
    for cls in ("wrap", "chapter", "sect1", "appendix", "preface"):
        d = soup.find("div", class_=cls)
        if d is not None:
            return d
    return soup.find("div", class_="book")   # index.html


BLOCK_NAMES = {"p", "pre", "ul", "ol", "dl", "table", "blockquote", "hr", "img",
               "h1", "h2", "h3", "h4", "h5", "h6"}


def is_internal(href):
    if href.startswith(("#", "javascript:")):
        return True
    if href.startswith("http://") or href.startswith("https://"):
        return False
    return True


def inline(el, page_rel):
    out = []
    for n in el.children:
        if isinstance(n, NavigableString):
            out.append(str(n))
            continue
        if not isinstance(n, Tag):
            continue
        name = n.name
        cls = (n.get("class") or [])
        if name in ("a",):
            href = n.get("href") or ""
            t = inline(n, page_rel).strip()
            if not t:
                continue
            if is_internal(href):
                out.append(t)                     # 站内 xref → 纯文字
            else:
                out.append("[%s](%s)" % (t, href))
        elif name in ("tt", "kbd", "code"):
            t = re.sub(r"\s+", " ", n.get_text()).strip()
            out.append("`%s`" % t if t else "")
        elif name == "span":
            if "command" in cls or "filename" in cls:
                t = re.sub(r"\s+", " ", n.get_text()).strip()
                out.append("`%s`" % t if t else "")
            elif "segtitle" in cls:
                t = re.sub(r"\s+", " ", n.get_text()).strip()
                out.append("**%s**" % t if t else "")
            else:
                out.append(inline(n, page_rel))
        elif name == "strong":
            if "command" in cls:
                t = re.sub(r"\s+", " ", n.get_text()).strip()
                out.append("`%s`" % t if t else "")
            else:
                t = inline(n, page_rel).strip()
                out.append("**%s**" % t if t else "")
        elif name in ("em", "i"):
            t = inline(n, page_rel).strip()
            out.append("*%s*" % t if t else "")
        elif name == "br":
            out.append("  \n")
        elif name in ("sup", "sub"):
            out.append(inline(n, page_rel).strip())
        elif name == "img":
            continue                                  # 装饰 icon 全丢
        elif name == "a":
            continue
        elif name in BLOCK_NAMES:
            blk = "\n".join(render(n, page_rel)).strip()
            if blk:
                out.append("\n" + blk + "\n")
        else:
            out.append(inline(n, page_rel))
    t = "".join(out)
    t = re.sub(r"[ \t]*\n[ \t]*", " ", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()


def render(el, page_rel, _depth=0):
    if _depth > 60:
        return []
    name = el.name
    cls = (el.get("class") or [])
    # ---- 标题 ----
    if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        t = inline(el, page_rel)
        if not t:
            return []
        lvl = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}[name]
        return ["#" * lvl + " " + t]
    # ---- 段落 ----
    if name == "p":
        t = inline(el, page_rel)
        return [t] if t else []
    # ---- 预格式化 ----
    if name == "pre":
        t = el.get_text("", strip=False)
        t = re.sub(r"[ \t]+\n", "\n", t).rstrip("\n")
        if not t.strip():
            return []
        return ["```", t, "```"]
    # ---- 列表 ----
    if name in ("ul", "ol"):
        out = []
        for li in el.find_all("li", recursive=False):
            head, blocks = [], []
            for ch in li.children:
                if isinstance(ch, Tag):
                    if ch.name in BLOCK_NAMES and ch.name not in ("p",):
                        blocks.append("\n".join(render(ch, page_rel)))
                    else:
                        head.append(inline(ch, page_rel))
                elif isinstance(ch, NavigableString):
                    head.append(str(ch))
            hh = re.sub(r"\s+", " ", "".join(head)).strip()
            out.append("- " + hh if hh else "-")
            for b in blocks:
                out += [(("    " + l) if l.strip() else "") for l in b.split("\n")]
        return out
    # ---- 定义/变量列表 ----
    if name == "dl":
        out = []
        for dt in el.find_all("dt", recursive=False):
            t = inline(dt, page_rel).strip("*").strip()
            out.append("**%s**" % t if t else "**?**")
            dd = dt.find_next_sibling("dd")
            if dd is not None:
                t = inline(dd, page_rel)
                out.append("  " + t.replace("\n", "\n  "))
        return out
    # ---- 表格 ----
    if name == "table":
        rows = []
        for tr in el.find_all("tr"):
            cells = []
            for td in tr.find_all(["td", "th"]):
                cells.append(inline(td, page_rel).replace("\n", " ").replace("|", "\\|"))
            if cells:
                rows.append(cells)
        if not rows:
            return []
        n = max(len(r) for r in rows)
        def line(r):
            r = r + [""] * (n - len(r))
            return "| " + " | ".join(r) + " |"
        out = [line(rows[0]), "|" + "|".join("---" for _ in range(n)) + "|"]
        out += [line(r) for r in rows[1:]]
        return out
    # ---- div 分支 ----
    if name == "div":
        if "toc" in cls:
            return []                     # 索引页目录：删
        if "titlepage" in cls:
            out = []
            for ch in el.children:
                if isinstance(ch, Tag):
                    out += render(ch, page_rel, _depth + 1)
            return out
        ad = next((c for c in cls if c in ADM), None)
        if ad:
            label = ADM[ad]
            body_el = el.find("div", class_="admonbody") or el
            body = []
            for ch in body_el.children:
                if isinstance(ch, Tag):
                    body += render(ch, page_rel)
            lines = ["> **%s**" % label, ">"]
            for l in body:
                lines.append(("> " + l) if l.strip() else ">")
            return lines
        if "admonhead" in cls or "admonbody" in cls:
            return []
        if "segmentedlist" in cls or "seglistitem" in cls:
            out = []
            for seg in el.find_all("div", class_="seg", recursive=False):
                t = inline(seg, page_rel)
                if t:
                    out.append(t)
            return out
        if "seg" in cls:
            t = inline(el, page_rel)
            return [t] if t else []
        # 通用容器：递归
        out = []
        for ch in el.children:
            if isinstance(ch, Tag):
                if ch.name in ("script", "style"):
                    continue
                out += render(ch, page_rel)
        return out
    # 其他标签（blockquote 等）
    t = inline(el, page_rel)
    return [t] if t else []


def conv(src_file):
    """单页面 → md 文本。"""
    with open(os.path.join(SRC, src_file), encoding="utf-8", errors="replace") as f:
        h = f.read()
    soup = BeautifulSoup(h, "html.parser")
    for s in soup.find_all(["script", "style"]):
        s.decompose()
    # 老 HTML 表格不闭合 → bs4 会把 navfooter 吸进 wrap；先整体剔导航（2026-10-17 e2fsprogs 实踩）
    for nf in soup.find_all("div", class_=["navfooter", "navheader", "headertitles", "headerlinks"]):
        nf.decompose()
    mc = main_container(soup)
    if mc is None:
        print("  !! 无主容器:", src_file, flush=True)
        return ""
    page_rel = os.path.dirname(src_file)
    lines = []
    for ch in mc.children:
        if isinstance(ch, Tag):
            if ch.name == "div" and "toc" in (ch.get("class") or []):
                continue
            lines += render(ch, page_rel)
    md = "\n".join(lines)
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = re.sub(r"[ \t]+\n", "\n", md)
    return md.strip() + "\n"


def page_h1(src_file):
    """章首页 h1 = 章标题。"""
    import bs4 as _b
    with open(os.path.join(SRC, src_file), encoding="utf-8") as f:
        t = f.read()
    s = _b.BeautifulSoup(t, "html.parser")
    h1 = s.find("h1")
    return h1.get_text().strip() if h1 else ""


def build_plan():
    """扁平方案：index.html 的 div.toc 里所有 <a href> 的出现顺序 = 全书页面阅读顺序。
    章归属 = src 的目录（chapterXX/ / prologue/ / appendices/）。
    （toc 的 ul 嵌套树在本站 HTML 里章 li 会混进后续章节的节，不能按树分组）"""
    with open(os.path.join(SRC, "index.html"), encoding="utf-8") as f:
        h = f.read()
    soup = BeautifulSoup(h, "html.parser")
    toc = soup.find("div", class_="toc")
    order = []
    for a in toc.find_all("a"):
        href = a.get("href") or ""
        src = href.split("#")[0]
        if not src or src in ("index.html", "longindex.html"):
            continue
        title = a.get_text().strip()
        if (src, title) not in order:
            order.append((src, title))
    # 按目录分组：prologue / chapterXX / appendices
    groups = {}
    for src, title in order:
        d = os.path.dirname(src)
        groups.setdefault(d, []).append((src, title))
    jobs = []
    for d, items in groups.items():
        if d == "prologue":
            chdir = "00-序言"
            for i, (src, title) in enumerate(items, 1):
                jobs.append((chdir, i, "%02d-%s.md" % (i, re.sub(r'[\\/:*?"<>|]', "_", title) or "页"), src))
        elif d == "appendices":
            chdir = "11-附录"
            for i, (src, title) in enumerate(items, 1):
                jobs.append((chdir, i, "%02d-%s.md" % (i, re.sub(r'[\\/:*?"<>|]', "_", title) or "页"), src))
        else:
            m = re.match(r"chapter(\d+)", d)
            if not m:
                continue
            ch = int(m.group(1))
            # 章标题取章首页 h1
            ch_src = "chapter%02d/chapter%02d.html" % (ch, ch)
            chapter_title = page_h1(ch_src) or (items[0][1] if items else "第 %d 章" % ch)
            chdir = "chapter%02d-%s" % (ch, re.sub(r'[\\/:*?"<>|]', "_", chapter_title))
            for i, (src, title) in enumerate(items):
                name = ("00-%s.md" % chapter_title) if i == 0 else ("%02d-%s.md" % (i, re.sub(r'[\\/:*?"<>|]', "_", title) or "页"))
                jobs.append((chdir, i, name, src))
    return jobs


def main():
    jobs = build_plan()
    all_jobs = [(None, 0, "00-前言与全书目录.md", "index.html")] + jobs
    seen = set()
    n = 0
    for d, i2, name, src in all_jobs:
        if src in seen:
            continue
        seen.add(src)
        n += 1
        outdir = os.path.join(CLEAN, d) if d else CLEAN
        os.makedirs(outdir, exist_ok=True)
        md = conv(src)
        out = os.path.join(outdir, name)
        with open(out, "w", encoding="utf-8") as f:
            f.write(md)
        print("%-40s %6d chars  %s" % (src, len(md), os.path.relpath(out, CLEAN)), flush=True)
    print("==== 完成，共 %d 篇 ====" % n, flush=True)


if __name__ == "__main__":
    main()