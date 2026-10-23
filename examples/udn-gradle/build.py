#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UDN 开源文档 wiki（doc.yonyoucloud.com/doc/wiki/...）→ markdown 树（网站口径）。

首例：`http://doc.yonyoucloud.com/doc/wiki/project/gradle/`（《Gradle 使用指南》中文翻译，
Gradle 1.x 时代译本，2026-10-23）。站点结构（静态多页 wiki）：
  - 侧栏页面清单 = 每个页面里 `div.left_title > a[href]`（顺序 = 书序，index 是「关于」）
  - 正文容器 = `div.markdown-body`（后面跟 `div.previous-and-next` 上/下篇导航，天然切掉）
  - 页面扁平无层级；标题在侧栏是中文（正文 `<h1>` 与之相同 → 剥）
  - 表格是 `<thead><tr><td>`（表头用 td 不是 th）；代码是 `<pre><code>` 无语言类

做法：
  1. 抓 index.html，解析侧栏 → [(href, title)]（顺序 = 侧栏序）
  2. 逐页抓 HTML，取 `div.markdown-body`，bs4 递归渲成 markdown（表格/代码围栏/引用块）
  3. 正文里的站内图（相对路径 `images/*.png`）→ 下载 → 传语雀 CDN → 重写成 CDN URL（img_map 断点续传）

用法：
  python3 build.py --base http://doc.yonyoucloud.com/doc/wiki/project/gradle/ \
      --out ./site --img-map /path/img_map.json
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
IMG_MAP_PATH = None
CFG = None
USER_ID = "25689388"


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
        tmp = "/tmp/_udn_img_%d%s" % (int(time.time() * 1000), os.path.splitext(absu)[1] or ".png")
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
    """解析侧栏 div.left_title > a → [(href, title)]（顺序 = 侧栏序，去重）"""
    html = fetch(urljoin(base, "index.html")).decode("utf-8", "replace")
    soup = BeautifulSoup(html, "html.parser")
    pages, seen = [], set()
    for a in soup.select("div.left_title > a[href]"):
        href = a.get("href", "")
        if not href or href.startswith("#") or href.startswith("http"):
            continue
        if href in seen:
            continue
        seen.add(href)
        title = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip()
        pages.append((href, title))
    return pages


def main():
    global CFG, IMG_MAP_PATH
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="站点书根 URL（末尾带 /）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--img-map", required=True)
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

    pages = get_pages(args.base)
    print("侧栏页面:", len(pages))
    for idx, (href, title) in enumerate(pages):
        url = urljoin(args.base, href)
        soup = BeautifulSoup(fetch(url).decode("utf-8", "replace"), "html.parser")
        sec = soup.select_one("div.markdown-body")
        if not sec:
            print("!! 未找到 div.markdown-body: %s" % href)
            continue
        if href.startswith("index"):
            fname = "00-关于.md"
        else:
            fname = "%02d-%s.md" % (idx, safe(title) if title else safe(href))
        out = []
        render(sec, out, url)
        md = "\n\n".join(out)
        md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
        # 正文首个 H1 == 侧栏标题 → 剥（语雀侧已有文档标题）
        lines = md.split("\n")
        if lines and lines[0].startswith("# "):
            h1 = lines[0][2:].strip()
            if h1 == title:
                lines = lines[1:]
                while lines and not lines[0].strip():
                    lines.pop(0)
        md = "\n".join(lines).strip() + "\n"
        fp = os.path.join(args.out, fname)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(md)
        print("  %-40s %6d B  imgs=%d  tbl=%d" % (fname, len(md), md.count("!["), md.count("\n| ")))


if __name__ == "__main__":
    main()