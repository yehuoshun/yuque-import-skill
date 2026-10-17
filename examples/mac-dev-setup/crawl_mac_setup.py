#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《Mac 开发配置手册》(aaaaaashu.gitbooks.io/mac-dev-setup) → markdown

站点是 GitBook 2.6.7 静态站（老 gitbooks.io 仍在线，无源仓库）。
正文容器 = section.normal（页外 nav-prev/nav-next 天然在外）。
bs4 递归渲染；站内链接（./X/index.html 等）剥成纯文本；图片下载转语雀 CDN。
"""
import json
import os
import re
import sys
import time
import urllib.request
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.element import NavigableString

sys.path.insert(0, "/home/admin/.openclaw/workspace/code/yuque-import-skill/scripts")
from yuque_tree_import import load_upload_cfg, upload_image  # noqa: E402

BASE = "https://aaaaaashu.gitbooks.io/mac-dev-setup/content/"
OUT = "/home/admin/.openclaw/workspace/tmp/mac-dev-setup/site"
IMG_MAP_FILE = "/home/admin/.openclaw/workspace/tmp/mac-dev-setup/img_map.json"
COOKIE_CFG = "~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json"
USER_ID = "25689388"

PAGES = [
    ("00-Introduction.md", "index.html"),
    ("01-System Preferences.md", "SystemPreferences/index.html"),
    ("02-XCode.md", "XCode/index.html"),
    ("03-Homebrew.md", "Homebrew/index.html"),
    ("03.1-Usage.md", "Homebrew/Usage.html"),
    ("03.2-Cask.md", "Homebrew/Cask.html"),
    ("04-iTerm2.md", "iTerm/index.html"),
    ("04.1-ZSH.md", "iTerm/zsh.html"),
    ("05-Git.md", "Git/index.html"),
    ("05.1-Git ignore.md", "Git/gitignore.html"),
    ("06-MySql.md", "MySql/index.html"),
    ("07-Node.js.md", "Node.js/index.html"),
    ("08-Apps.md", "Apps/index.html"),
]

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
img_map = {}
cfg = None


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def image_md(tag, page_url):
    src = tag.get("src", "")
    alt = tag.get("alt", "") or ""
    if not src or src.startswith("data:"):
        return ""
    if src.startswith(("http://", "https://")):
        return "![%s](%s)" % (alt, src)
    absu = urljoin(page_url, src)
    key = absu
    if key not in img_map:
        try:
            data = fetch(absu)
        except Exception as e:  # noqa: BLE001
            print("  图片下载失败 %s : %s" % (absu, e))
            return "![%s](%s)" % (alt, absu)
        tmp = "/tmp/_md_img_%d%s" % (int(time.time() * 1000), os.path.splitext(absu)[1] or ".png")
        open(tmp, "wb").write(data)
        url = None
        for attempt in range(20):
            url = upload_image(cfg["cookie"], cfg["ctoken"], USER_ID, tmp)
            if url:
                break
            print("  上传重试 %d: %s" % (attempt + 1, absu))
            time.sleep(60)
        os.remove(tmp)
        if not url:
            print("  上传失败 %s" % absu)
            return "![%s](%s)" % (alt, absu)
        img_map[key] = url
        json.dump(img_map, open(IMG_MAP_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("  图片 -> %s" % url[:70])
        time.sleep(1)
    return "![%s](%s)" % (alt, img_map[key])


def inline(el, page_url):
    parts = []
    for c in el.children:
        if isinstance(c, NavigableString):
            parts.append(str(c))
        elif c.name in ("ul", "ol", "table", "pre", "blockquote"):
            continue          # 块级子节点交给 render()，否则列表文本重复
        elif c.name == "br":
            parts.append("\n")
        elif c.name in ("strong", "b"):
            parts.append("**" + inline(c, page_url) + "**")
        elif c.name in ("em", "i"):
            parts.append("*" + inline(c, page_url) + "*")
        elif c.name in ("code", "tt", "kbd"):
            parts.append("`" + c.get_text().strip() + "`")
        elif c.name == "img":
            parts.append(image_md(c, page_url))
        elif c.name == "a":
            href = c.get("href", "")
            if c.get("class") and "anchor" in c.get("class"):
                continue
            txt = inline(c, page_url)
            if not href or href.startswith("#") or re.search(r"\.html?($|#)", href) \
                    or href.startswith("./") or href.startswith("../"):
                parts.append(txt)                     # 站内/锚点 → 纯文本
            else:
                parts.append("[%s](%s)" % (txt, href))
        elif c.name == "span":
            parts.append(inline(c, page_url))
        else:
            parts.append(inline(c, page_url))
    t = "".join(parts)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\s*\n\s*", "\n", t)
    return t.strip()


def render_list(lst, out, page_url, depth):
    """列表渲染（递归不经过 render 主循环，否则嵌套 li 会走 else 分支丢前缀）"""
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
                (ch.name in ("p", "ul", "ol", "pre", "table", "blockquote", "div", "h1", "h2", "h3", "h4",
                             "h5", "h6", "hr", "img")) for ch in c.find_all(recursive=False))
            if has_block:
                render(c, out, page_url, depth)
            else:
                t = inline(c, page_url)
                if t:
                    out.append(t)
        elif c.name == "a":
            t = inline(c, page_url)
            if t:
                out.append(t)
        else:
            render(c, out, page_url, depth)


def main():
    global cfg
    cfg = load_upload_cfg(os.path.expanduser(COOKIE_CFG))
    if not cfg:
        print("cookie 不可用", file=sys.stderr)
        sys.exit(1)
    if os.path.exists(IMG_MAP_FILE):
        img_map.update(json.load(open(IMG_MAP_FILE, encoding="utf-8")))
    os.makedirs(OUT, exist_ok=True)
    for name, rel in PAGES:
        url = urljoin(BASE, rel)
        html = fetch(url).decode("utf-8", "replace")
        soup = BeautifulSoup(html, "html.parser")
        sec = soup.select_one("section.normal")
        if not sec:
            print("!! 未找到 section.normal: %s" % rel)
            continue
        out = []
        render(sec, out, url)
        md = "\n\n".join(out)
        md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
        # 连续列表行之间的空行 → 删（否则语雀渲染成松散列表）
        lines = md.splitlines()
        compact = []
        for i, l in enumerate(lines):
            if (not l.strip() and i + 1 < len(lines)
                    and re.match(r"^\s*(?:- |\d+\. )", lines[i + 1])
                    and compact and re.match(r"^\s*(?:- |\d+\. )", compact[-1])):
                continue
            compact.append(l)
        md = "\n".join(compact) + "\n"
        # GitBook 插件产物：读者数徽章（bitdeli）
        md = "\n".join(l for l in md.splitlines() if "bitdeli" not in l.lower())
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(md)
        print("OK %-28s %6d chars  %s" % (name, len(md), url))
    json.dump(img_map, open(IMG_MAP_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("图片总数:", len(img_map))


if __name__ == "__main__":
    main()