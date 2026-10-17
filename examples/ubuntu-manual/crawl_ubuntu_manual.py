#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《Ubuntu 参考手册》(wiki.ubuntu.org.cn/UbuntuManual) → markdown

MediaWiki 1.42 站（api.php 被 Cloudflare 拦，只能抓页面 HTML）。
正文容器 = div.mw-parser-output；页面顶部的「UbuntuManual导航」ul + 导航 table + div.toc 要丢掉
（从第一个正文 h2 开始才算正文）。站内链接（/UbuntuManual:xxx#anchor）剥成纯文本。
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup
from bs4.element import NavigableString

sys.path.insert(0, "/home/admin/.openclaw/workspace/code/yuque-import-skill/scripts")
from yuque_tree_import import load_upload_cfg, upload_image  # noqa: E402

BASE = "http://wiki.ubuntu.org.cn/"
OUT = "/home/admin/.openclaw/workspace/tmp/ubuntu-manual/site"
IMG_MAP_FILE = "/home/admin/.openclaw/workspace/tmp/ubuntu-manual/img_map.json"
COOKIE_CFG = "~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json"
USER_ID = "25689388"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120 Safari/537.36"}

PAGES = [
    ("00-前言.md", "UbuntuManual"),
    ("01-序言.md", "UbuntuManual:序言"),
    ("02-Ubuntu 基础.md", "UbuntuManual:Ubuntu 基础"),
    ("03-Ubuntu 系统安装提示.md", "UbuntuManual:Ubuntu 系统安装提示"),
    ("04-Ubuntu指南.md", "UbuntuManual:Ubuntu指南"),
    ("05-发行版升级.md", "UbuntuManual:发行版升级"),
    ("06-Ubuntu 软件包管理.md", "UbuntuManual:Ubuntu 软件包管理"),
    ("07-Ubuntu下的 Linux 内核.md", "UbuntuManual:Ubuntu下的 Linux 内核"),
    ("08-Ubuntu 小技巧.md", "UbuntuManual:Ubuntu 小技巧"),
    ("09-Ubuntu 系统微调.md", "UbuntuManual:Ubuntu 系统微调"),
    ("10-网络设置.md", "UbuntuManual:网络设置"),
    ("11-编辑器.md", "UbuntuManual:编辑器"),
    ("12-版本控制系统.md", "UbuntuManual:版本控制系统"),
    ("13-编程.md", "UbuntuManual:编程"),
    ("14-GnuPG.md", "UbuntuManual:GnuPG"),
    ("15-Ubuntu 技术支持.md", "UbuntuManual:Ubuntu 技术支持"),
    ("16-附录.md", "UbuntuManual:附录"),
]

img_map = {}
cfg = None


def fetch(url, raw=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read() if raw else r.read().decode("utf-8", "replace")


def image_md(tag):
    src = tag.get("src", "")
    alt = tag.get("alt", "") or ""
    if not src or src.startswith("data:"):
        return ""
    if src.startswith("//"):
        src = "http:" + src
    elif src.startswith("/"):
        src = BASE.rstrip("/") + src
    if not src.startswith("http"):
        return ""
    key = src.split("?")[0]
    if key not in img_map:
        try:
            data = fetch(src, raw=True)
        except Exception as e:  # noqa: BLE001
            print("  图片下载失败 %s : %s" % (src, e))
            return "![%s](%s)" % (alt, src)
        tmp = "/tmp/_ub_img%d%s" % (int(time.time() * 1000), os.path.splitext(key)[1] or ".png")
        open(tmp, "wb").write(data)
        url = None
        for attempt in range(20):
            url = upload_image(cfg["cookie"], cfg["ctoken"], USER_ID, tmp)
            if url:
                break
            print("  上传重试 %d %s" % (attempt + 1, key))
            time.sleep(60)
        os.remove(tmp)
        if not url:
            return "![%s](%s)" % (alt, src)
        img_map[key] = url
        json.dump(img_map, open(IMG_MAP_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("  图片 -> %s" % url[:70])
        time.sleep(1)
    return "![%s](%s)" % (alt, img_map[key])


def inline(el):
    parts = []
    for c in el.children:
        if isinstance(c, NavigableString):
            parts.append(str(c))
        elif c.name == "br":
            parts.append("\n")
        elif c.name in ("b", "strong"):
            parts.append("**" + inline(c) + "**")
        elif c.name in ("i", "em"):
            parts.append("*" + inline(c) + "*")
        elif c.name in ("code", "tt", "kbd", "samp"):
            t = c.get_text().strip()
            parts.append("`%s`" % t if t else "")
        elif c.name == "img":
            parts.append(image_md(c))
        elif c.name == "a":
            href = c.get("href", "")
            txt = inline(c)
            if not href or href.startswith("#"):
                parts.append(txt)
            elif href.startswith("/") and not href.startswith("//"):
                if href.startswith("/%E7%89%B9%E6%AE%8A:") or "/Special:" in href:
                    continue                       # 特殊页链接丢弃
                parts.append(txt)                  # 站内链接 → 纯文本
            else:
                parts.append("[%s](%s)" % (txt, href))
        elif c.name == "sup":
            continue                               # 脚注引用（<sup class=reference>）
        elif c.name in ("ul", "ol", "table", "pre", "div", "blockquote"):
            continue                               # 块级交给 render
        else:
            parts.append(inline(c))
    t = "".join(parts)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\s*\n\s*", "\n", t)
    return t.strip()


def render_list(lst, out, depth=0):
    for li in lst.find_all("li", recursive=False):
        prefix = "  " * depth + ("- " if lst.name == "ul" else "1. ")
        txt = inline(li)
        if txt:
            out.append(prefix + txt)
        for child in li.find_all(["ul", "ol"], recursive=False):
            render_list(child, out, depth + 1)


def table_md(tb):
    rows = []
    for tr in tb.find_all("tr"):
        cells = [inline(td).replace("\n", " ") for td in tr.find_all(["td", "th"])]
        if any(cells):
            rows.append("| " + " | ".join(cells) + " |")
    if len(rows) >= 2:
        n = rows[0].count("|") - 1
        rows.insert(1, "|" + "|".join(["---"] * n) + "|")
    return "\n".join(rows)


def render(el, out, depth=0):
    for c in el.children:
        if isinstance(c, NavigableString):
            t = str(c).strip()
            if t:
                out.append(t)
            continue
        if c.name in ("script", "style"):
            continue
        if c.get("class") and ("mw-editsection" in c.get("class") or "noprint" in c.get("class")):
            continue
        if c.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            t = inline(c)
            if t and t != "目录":
                out.append("\n" + "#" * int(c.name[1]) + " " + t)
        elif c.name == "p":
            t = inline(c)
            if t:
                out.append(t)
        elif c.name in ("ul", "ol"):
            render_list(c, out, depth)
        elif c.name == "pre":
            code = c.get_text().strip("\n")
            if code.strip():
                out.append("\n```\n" + code + "\n```")
        elif c.name == "blockquote":
            t = inline(c)
            if t:
                out.append("\n> " + t.replace("\n", "\n> "))
        elif c.name == "table":
            t = table_md(c)
            if t:
                out.append("\n" + t)
        elif c.name == "hr":
            out.append("\n---")
        elif c.name == "img":
            t = image_md(c)
            if t:
                out.append(t)
        elif c.name in ("dl", "div", "section", "center", "dd", "dt"):
            render(c, out, depth)
        elif c.name == "a":
            t = inline(c)
            if t:
                out.append(t)
        else:
            t = inline(c)
            if t:
                out.append(t)


def main():
    global cfg
    cfg = load_upload_cfg(os.path.expanduser(COOKIE_CFG))
    if not cfg:
        print("cookie 不可用", file=sys.stderr)
        sys.exit(1)
    if os.path.exists(IMG_MAP_FILE):
        img_map.update(json.load(open(IMG_MAP_FILE, encoding="utf-8")))
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for name, page in PAGES:
        if only and only not in name:
            continue
        url = BASE + urllib.parse.quote(page.replace(" ", "_"))
        html = fetch(url)
        soup = BeautifulSoup(html, "html.parser")
        po = soup.select_one("div.mw-parser-output")
        if not po:
            print("!! 未找到正文: %s" % page)
            continue
        if page == "UbuntuManual":
            # 主页：只取导航块之前的 p（摘要 + 版权声明），再补一张章节表
            ps = []
            for c in po.find_all(recursive=False):
                if c.name == "ul" and "UbuntuManual导航" in c.get_text():
                    break
                if c.name == "p":
                    t = inline(c)
                    if t and t not in ("摘要", "版权声明"):
                        ps.append(t)
            toc = ["## 章节目录", ""]
            for nm, pg in PAGES[1:]:
                toc.append("- %s ｜ `%s`" % (nm.split("-", 1)[1].replace(".md", ""), nm))
            md = "## Ubuntu 参考手册\n\n" + "\n\n".join(ps) + "\n\n---\n\n" + "\n".join(toc) + "\n"
            open(os.path.join(OUT, name), "w", encoding="utf-8").write(md)
            print("OK %-34s %6d chars  %s" % (name, len(md), url))
            continue
        # 丢掉正文起点之前的一切（导航 ul + 导航 table + hr + 自动目录 div.toc）
        kids = list(po.find_all(recursive=False))
        start = None
        for i, c in enumerate(kids):
            if c.name in ("h1", "h2", "h3", "h4") and c.get("id") != "mw-toc-heading" \
                    and "toc" not in (c.get("class") or []):
                start = i
                break
        if start is None:                      # 无标题页（如主页）→ 跳过前导导航，从第一个 <p> 起
            for i, c in enumerate(kids):
                if c.name == "p":
                    start = i
                    break
            if start is not None:              # …并到导航块（hr/ul/table）为止
                for i, c in enumerate(kids[start:], start):
                    if i > start and c.name in ("hr", "ul", "table"):
                        for x in kids[i:]:
                            x.decompose()
                        break
        if start is None:
            start = 0
        for c in kids[:start]:
            c.decompose()
        out = []
        render(po, out, 0)
        md = "\n\n".join(x for x in out if x is not None)
        md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
        md = "\n".join(l for l in md.splitlines() if l.strip() != "目录")
        md = md.replace("<nowiki>", "").replace("</nowiki>", "")
        # MediaWiki 调试块（NewPP limit report / Transclusion …）在每页尾部，整个丢掉
        if "NewPP limit report" in md:
            md = md.split("NewPP limit report")[0].rstrip() + "\n"
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(md)
        print("OK %-34s %6d chars  %s" % (name, len(md), url))
    json.dump(img_map, open(IMG_MAP_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("图片总数:", len(img_map))


if __name__ == "__main__":
    main()