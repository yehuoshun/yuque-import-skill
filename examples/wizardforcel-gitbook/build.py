#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wizardforcel / 老 gitbooks.io 静态站（GitBook 2.x）→ markdown 树（可复用）。

适用：`https://<name>.gitbooks.io/<book>/content/` 这类老 gitbooks.io 渲染站
（页面结构 = `ul.summary` 侧栏 + `section.normal` 正文）。无源仓库时的网站口径。

做法：
  1. 抓 `content/index.html`，解析 `ul.summary li.chapter[data-path]` → 页面清单（顺序 = 侧栏序）
  2. 逐页抓 HTML，取 `section.normal`，bs4 递归渲成 markdown
  3. 正文里的站内图（相对路径）→ 下到临时文件 → 传语雀 CDN → 重写成 CDN URL（img_map 断点续传）

用法：
  python3 build.py --base https://wizardforcel.gitbooks.io/ibm-j-ap/content/ \
      --out ./site --img-map /path/img_map.json --book-name "让开发自动化系列专栏"
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.element import NavigableString

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
from yuque_tree_import import load_upload_cfg, upload_image  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
IMG_MAP = {}
CFG = None
USER_ID = "25689388"


def fetch(url):
    # gitbooks.io 间歇 401（见 references 坑：progit2 同坑）→ 退避重试
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
    return name.replace("/", "／")


def image_md(tag, page_url):
    src = tag.get("src", "")
    alt = tag.get("alt", "") or ""
    if not src or src.startswith("data:"):
        return ""
    if src.startswith(("http://", "https://")):
        return "![%s](%s)" % (alt, src)
    absu = urljoin(page_url, src)
    if absu not in IMG_MAP:
        try:
            data = fetch(absu)
        except Exception as e:  # noqa: BLE001
            print("  图片下载失败 %s : %s" % (absu, e))
            return "![%s](%s)" % (alt, absu)
        tmp = "/tmp/_wz_img_%d%s" % (int(time.time() * 1000), os.path.splitext(absu)[1] or ".png")
        with open(tmp, "wb") as f:
            f.write(data)
        url = None
        for attempt in range(20):
            url = upload_image(CFG["cookie"], CFG["ctoken"], USER_ID, tmp)
            if url:
                break
            print("  上传重试 %d: %s" % (attempt + 1, absu))
            time.sleep(60)
        os.remove(tmp)
        if not url:
            print("  上传失败 %s" % absu)
            return "![%s](%s)" % (alt, absu)
        IMG_MAP[absu] = url
        with open(IMG_MAP_PATH, "w", encoding="utf-8") as f:
            json.dump(IMG_MAP, f, ensure_ascii=False, indent=1)
        print("  图片 -> %s" % url[:70])
        time.sleep(1)
    return "![%s](%s)" % (alt, IMG_MAP[absu])


def inline(el, page_url):
    parts = []
    for c in el.children:
        if isinstance(c, NavigableString):
            parts.append(str(c))
        elif c.name in ("ul", "ol", "table", "pre", "blockquote"):
            continue
        elif c.name == "br":
            parts.append("\n")
        elif c.name in ("strong", "b"):
            t = inline(c, page_url)
            if t:
                parts.append("**" + t + "**")
        elif c.name in ("em", "i"):
            t = inline(c, page_url)
            if t:
                parts.append("*" + t + "*")
        elif c.name in ("code", "tt", "kbd"):
            parts.append("`" + c.get_text().strip() + "`")
        elif c.name == "img":
            parts.append(image_md(c, page_url))
        elif c.name == "a":
            if c.get("class") and "anchor" in c.get("class"):
                continue
            href = c.get("href", "")
            txt = inline(c, page_url)
            if not href or href.startswith("#") or re.search(r"\.html?($|#)", href) \
                    or href.startswith("./") or href.startswith("../"):
                parts.append(txt)
            else:
                parts.append("[%s](%s)" % (txt, href))
        else:
            parts.append(inline(c, page_url))
    t = "".join(parts)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\s*\n\s*", "\n", t)
    return t.strip()


def render_list(lst, out, page_url, depth):
    for i, li in enumerate(lst.find_all("li", recursive=False), 1):
        prefix = "  " * depth + ("- " if lst.name == "ul" else "%d. " % i)
        txt = inline(li, page_url)
        if txt:
            out.append(prefix + txt)
        for child in li.find_all(["ul", "ol"], recursive=False):
            render_list(child, out, page_url, depth + 1)


def table_md(tb, page_url):
    rows = []
    for tr in tb.find_all("tr"):
        cells = [inline(td, page_url).replace("\n", " ") for td in tr.find_all(["td", "th"])]
        rows.append("| " + " | ".join(cells) + " |")
    if len(rows) >= 2:
        n = rows[0].count("|") - 1
        rows.insert(1, "|" + "|".join(["---"] * n) + "|")
    return "\n".join(rows)


def render(el, out, page_url, depth=0):
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
        if re.fullmatch(r"h[1-6]", c.name or ""):
            t = inline(c, page_url)
            if t:
                out.append("\n" + "#" * int(c.name[1]) + " " + t)
        elif c.name == "p":
            t = inline(c, page_url)
            if t:
                out.append(t)
        elif c.name in ("ul", "ol"):
            render_list(c, out, page_url, depth)
        elif c.name == "pre":
            code = c.get_text()
            lang = ""
            code_el = c.find("code")
            if code_el and code_el.get("class"):
                for cl in code_el["class"]:
                    m = re.match(r"lang(?:uage)?-(\w+)", cl)
                    if m:
                        lang = m.group(1)
            out.append("\n```%s\n%s\n```" % (lang, code.strip("\n")))
        elif c.name == "blockquote":
            t = inline(c, page_url)
            if t:
                out.append("\n> " + t.replace("\n", "\n> "))
        elif c.name == "table":
            t = table_md(c, page_url)
            if t:
                out.append("\n" + t)
        elif c.name == "hr":
            out.append("\n---")
        elif c.name == "img":
            t = image_md(c, page_url)
            if t:
                out.append(t)
        elif c.name in ("center", "figure"):
            render(c, out, page_url, depth)
        elif c.name == "figcaption":
            t = inline(c, page_url)
            if t:
                out.append("*" + t + "*")
        elif c.name in ("div", "section", "article", "main", "tbody", "span"):
            has_block = any(
                (ch.name in ("p", "ul", "ol", "pre", "table", "blockquote", "div", "h1", "h2", "h3",
                             "h4", "h5", "h6", "hr", "img")) for ch in c.find_all(recursive=False))
            if has_block:
                render(c, out, page_url, depth)
            else:
                t = inline(c, page_url)
                if t:
                    out.append(t)
        else:
            render(c, out, page_url, depth)


def get_pages(base):
    """解析 ul.summary → [(href, title)]（顺序 = 侧栏序）"""
    html = fetch(urljoin(base, "index.html")).decode("utf-8", "replace")
    soup = BeautifulSoup(html, "html.parser")
    pages = []
    for li in soup.select("ul.summary li.chapter"):
        a = li.find("a")
        if not a:
            continue
        href = (li.get("data-path") or a.get("href") or "").lstrip("./")
        title = a.get_text(" ", strip=True)
        pages.append((href, re.sub(r"\s+", " ", title).strip()))
    return pages


def main():
    global CFG, IMG_MAP_PATH
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="站点 content/ 根 URL")
    ap.add_argument("--out", required=True)
    ap.add_argument("--img-map", required=True)
    ap.add_argument("--book-name", default="", help="书名（用于剥标题前缀 + 给 index 起名）")
    ap.add_argument("--strip", default=None, help="要从标题里剥掉的前缀（默认 书名: ）")
    ap.add_argument("--cookie-config",
                    default="~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json")
    args = ap.parse_args()
    IMG_MAP_PATH = args.img_map

    CFG = load_upload_cfg(os.path.expanduser(args.cookie_config))
    if not CFG:
        print("cookie 不可用", file=sys.stderr)
        sys.exit(1)
    if os.path.exists(args.img_map):
        IMG_MAP.update(json.load(open(args.img_map, encoding="utf-8")))
    os.makedirs(args.out, exist_ok=True)

    strip = args.strip
    if strip is None and args.book_name:
        strip = args.book_name.replace("系列专栏", "") + ": "
    pages = get_pages(args.base)
    print("侧栏页面:", len(pages))
    for idx, (href, title) in enumerate(pages):
        url = urljoin(args.base, href)
        soup = BeautifulSoup(fetch(url).decode("utf-8", "replace"), "html.parser")
        sec = soup.select_one("section.normal")
        if not sec:
            print("!! 未找到 section.normal: %s" % href)
            continue
        # 剥掉标题里的 "N. " 与书名前缀，得副标题
        sub = re.sub(r"^\d+\.\s*", "", title)
        if strip and sub.startswith(strip):
            sub = sub[len(strip):].strip()
        # index 页当 00-系列介绍
        if href.startswith("index"):
            fname = "00-系列介绍.md"
        else:
            fname = "%02d-%s.md" % (idx, safe(sub) if sub else safe(title))
        out = []
        render(sec, out, url)
        md = "\n\n".join(out)
        md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
        # 正文首个 H1 == 标题 → 剥（语雀侧有文档标题）
        lines = md.split("\n")
        if lines and lines[0].startswith("# "):
            h1 = lines[0][2:].strip()
            if h1 == title or h1 == sub or h1.endswith(sub):
                lines = lines[1:]
                while lines and not lines[0].strip():
                    lines.pop(0)
        md = "\n".join(lines).strip() + "\n"
        fp = os.path.join(args.out, fname)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(md)
        print("  %-46s %6d B  imgs=%d" % (fname, len(md), md.count("![")))


if __name__ == "__main__":
    main()