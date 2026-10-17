#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FreeBSD 使用手册（docs.freebsd.org/zh-cn/books/handbook/）→ markdown 导入树

步骤二：bs4 递归渲染器（Asciidoctor DOM: sect1-4 / paragraph / listingblock /
literalblock / admonitionblock / imageblock / ulist / olist / dlist / exampleblock /
tableblock），图片下载后传语雀 CDN 并重写为 CDN URL（img_map.json 缓存防重传）。

产物：
  clean/00-前言.md
  clean/部分 I. 起步/00-部分 I. 起步.md
  clean/部分 I. 起步/01-第 1 章 介绍.md ...
"""
import os, re, json, sys, time, urllib.request, html as H
from urllib.parse import urljoin

from bs4 import BeautifulSoup, NavigableString, Tag

sys.path.insert(0, "/home/admin/.openclaw/workspace/code/yuque-import-skill/scripts")
from yuque_tree_import import upload_image, load_upload_cfg  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = "https://docs.freebsd.org/zh-cn/books/handbook/"
CLEAN = os.path.join(ROOT, "clean")
IMG_MAP = os.path.join(ROOT, "img_map.json")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
ADM = {"note": "注意", "tip": "提示", "important": "重要", "warning": "警告", "caution": "当心"}
INLINE_CODE_SPAN = {"filename", "guimenuitem", "keyseq", "parameter", "literal"}
stats = {"img_ok": 0, "img_fail": 0, "img_skip": 0}


def fetch(url, tries=5):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(min(3 * (i + 1), 20))
    raise last


def load_map():
    try:
        return json.load(open(IMG_MAP, encoding="utf-8"))
    except Exception:
        return {}


def save_map(m):
    json.dump(m, open(IMG_MAP, "w", encoding="utf-8"), ensure_ascii=False, indent=0)


def img_md(src, alt, page_url, up):
    """绝对 URL → CDN 上传 → ![alt](url)；外链/失败回退原 URL。"""
    url = urljoin(page_url, src) if not src.startswith(("http://", "https://", "data:")) else src
    if url.startswith("data:"):
        stats["img_skip"] += 1
        return ""
    mp = load_map()
    if url in mp:
        return "![%s](%s)" % (alt, mp[url])
    tmp = "/tmp/fbsd-img-" + re.sub(r"[^\w.\-]", "_", os.path.basename(url))[-60:]
    for attempt in range(4):
        try:
            raw = fetch(url)
            open(tmp, "wb").write(raw)
            u = upload_image(up["cfg"]["cookie"], up["cfg"]["ctoken"], up["user_id"], tmp)
            os.remove(tmp)
            if u:
                mp = load_map()
                mp[url] = u
                save_map(mp)
                stats["img_ok"] += 1
                return "![%s](%s)" % (alt, u)
            break
        except Exception as e:
            if attempt == 3:
                print("    img FAIL %s: %s" % (url, e), flush=True)
    stats["img_fail"] += 1
    return "![%s](%s)" % (alt, url)


def is_internal(href):
    if href.startswith("#"):
        return True
    if href.startswith("http"):
        return "docs.freebsd.org/zh-cn/books/handbook/" in href
    return True          # 相对链接 = 本手册内部


def abs_href(href, page_url):
    if href.startswith("/"):
        return "https://docs.freebsd.org" + href
    return urljoin(page_url, href)


BR = "\x00"


def inline(el, page_url, up):
    """行内元素 → markdown 文本（块级子元素就地渲染并换行拼入）。"""
    out = []
    for n in el.children:
        if isinstance(n, NavigableString):
            out.append(str(n))
            continue
        if not isinstance(n, Tag):
            continue
        name = n.name
        cls = n.get("class") or []
        if name == "br":
            out.append(BR)
        elif name in ("strong", "b"):
            t = inline(n, page_url, up).strip()
            out.append("**%s**" % t if t else "")
        elif name in ("em", "i"):
            if any(c.startswith("fa") or c in ("icon", "heart") for c in cls):
                continue
            t = inline(n, page_url, up).strip()
            out.append("*%s*" % t if t else "")
        elif name in ("code", "tt", "kbd"):
            t = re.sub(r"\s+", " ", n.get_text()).strip()
            out.append("`%s`" % t if t else "")
        elif name in ("sup", "sub"):
            out.append(inline(n, page_url, up).strip())
        elif name == "span":
            if any(c in INLINE_CODE_SPAN for c in cls):
                t = re.sub(r"\s+", " ", n.get_text()).strip()   # 内层 <kbd> 已带反引号 → 取纯文本再包一层
                out.append("`%s`" % t if t else "")
            else:
                out.append(inline(n, page_url, up))
        elif name == "a":
            href = n.get("href") or ""
            t = inline(n, page_url, up).strip()
            if not t:
                continue                                   # <a class=anchor> 等空锚
            if is_internal(href):
                out.append(t)                              # 跨文档/站内链接 → 纯文字（语雀无相对链接）
            else:
                out.append("[%s](%s)" % (t, abs_href(href, page_url)))
        elif name == "img":
            out.append(img_md(n.get("src") or "", (n.get("alt") or "").strip(), page_url, up))
        elif name in ("p", "div", "pre", "ul", "ol", "dl", "table", "hr"):
            blk = "\n".join(render_block(n, page_url, up)).strip()
            out.append("\n" + blk + "\n" if blk else "")
        else:
            out.append(inline(n, page_url, up))
    t = "".join(out)
    t = re.sub(r"[ \t]*\n[ \t]*", " ", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = t.replace(BR, "\n")
    return t.strip()


def render_pre(pre, page_url, up):
    code_el = pre.find("code")
    lang = ""
    if code_el is not None:
        lang = code_el.get("data-lang") or ""
        if not lang:
            for c in (code_el.get("class") or []):
                if c.startswith("language-"):
                    lang = c[9:]
    if not lang:
        for c in (pre.get("class") or []):
            if c.startswith("language-"):
                lang = c[9:]
    text = pre.get_text()
    text = H.unescape(text).replace(BR, "\n").rstrip("\n")
    return ["```" + lang, text, "```"]


def render_table(tb, page_url, up):
    rows = []
    thead = tb.find("thead")
    body = tb.find("tbody") or tb
    def cells(tr):
        return [inline(td, page_url, up).replace("\n", " ").replace("|", "\\|").strip()
                for td in tr.find_all(["td", "th"], recursive=False)]
    head = []
    if thead is not None:
        trs = thead.find_all("tr")
        if trs:
            head = cells(trs[0])
    for tr in body.find_all("tr", recursive=False):
        rows.append(cells(tr))
    if not head and rows:
        head, rows = rows[0], rows[1:]      # 无 thead 的表：首行当表头（空表头行在语雀里是一条空栏）
    if not rows and not head:
        return []
    def line(cells_):
        n = max(len(head), len(cells_))
        cells_ = cells_ + [""] * (n - len(cells_))
        return "| " + " | ".join(cells_) + " |"
    n = max(len(head), max((len(r) for r in rows), default=0))
    hdr = head + [""] * (n - len(head))
    out = []
    cap = tb.find("caption")
    if cap is not None:
        t = re.sub(r"\s+", " ", cap.get_text()).strip()
        if t:
            out.append("**%s**" % t)
            out.append("")
    out.append(line(hdr))
    out.append("|" + "|".join("---" for _ in range(n)) + "|")
    out += [line(r) for r in rows]
    return out


def render_list(ul, page_url, up, ordered=False, depth=0):
    out = []
    n = 1
    for li in ul.find_all("li", recursive=False):
        marker = "%d. " % n if ordered else "- "
        n += 1
        inline_parts, blocks = [], []
        for ch in li.children:
            # <li><p>text</p></li> 是【正文】不是块 → 归到 head；div/pre/嵌套列表才是块
            if isinstance(ch, Tag) and ch.name in ("div", "pre", "ul", "ol", "dl", "table"):
                if ch.name == "div" and "title" in (ch.get("class") or []):
                    blocks.append("**%s**" % inline(ch, page_url, up))
                else:
                    blocks.append("\n".join(render_block(ch, page_url, up)))
            else:
                inline_parts.append(inline(ch, page_url, up) if isinstance(ch, Tag) else str(ch) if isinstance(ch, NavigableString) else "")
        head = re.sub(r"\s+", " ", "".join(inline_parts)).strip()
        if head:
            out.append(marker + head)
        else:
            out.append(marker.rstrip())
        for b in blocks:
            b = b.strip("\n")
            if not b:
                continue
            pad = "    " * (depth + 1)
            out += [(pad + l if l.strip() else "") for l in b.split("\n")]
    return out


def render_dl(dl, page_url, up):
    out = []
    for ch in dl.children:
        if not isinstance(ch, Tag):
            continue
        if ch.name == "dt":
            t = inline(ch, page_url, up)
            if t:
                out.append("**%s**" % t)
        elif ch.name == "dd":
            t = inline(ch, page_url, up)
            if t:
                out.append("  " + t.replace("\n", "\n  "))
    return out


def render_block(el, page_url, up):
    """块级元素 → md 行列表。"""
    name = el.name
    cls = el.get("class") or []
    if name == "hr":
        return ["---"]
    if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        t = inline(el, page_url, up)
        lvl = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}[name]
        if not t:
            return []
        pad = "\n" if lvl > 3 else ""       # h4+ 前面留空行（asciidoctor 同级标题紧排）
        return [pad, "#" * lvl + " " + t]
    if name == "p":
        t = inline(el, page_url, up)
        return [t] if t else []
    if name == "pre":
        return render_pre(el, page_url, up)
    if name == "table":
        return render_table(el, page_url, up)
    if name == "ul":
        return render_list(el, page_url, up)
    if name == "ol":
        return render_list(el, page_url, up, ordered=True)
    if name == "dl":
        return render_dl(el, page_url, up)
    if name == "img":
        m = img_md(el.get("src") or "", (el.get("alt") or "").strip(), page_url, up)
        return [m] if m else []
    if name != "div":
        t = inline(el, page_url, up)
        return [t] if t else []

    # ---- div 分支 ----
    if "toc-mobile" in cls or "book-menu-mobile" in cls or "last-modified" in cls or "buttons" in cls:
        return []
    if "admonitionblock" in cls:
        kind = next((c for c in cls if c in ADM), "note")
        inner = el.find("td", class_="content") or el
        body = []
        for ch in inner.children:
            if isinstance(ch, Tag):
                body += render_block(ch, page_url, up)
        label = ADM[kind]
        lines = ["> **%s**" % label, ">"]
        for l in body:
            lines.append(("> " + l) if l.strip() else ">")
        return lines
    if "imageblock" in cls:
        img = el.find("img")
        out = []
        ttl = el.find("div", class_="title")
        if ttl:
            out.append("**%s**" % inline(ttl, page_url, up))
        if img is not None:
            m = img_md(img.get("src") or "", (img.get("alt") or "").strip(), page_url, up)
            if m:
                out.append(m)
        return out
    if "listingblock" in cls or "literalblock" in cls:
        pre = el.find("pre")
        return render_pre(pre, page_url, up) if pre is not None else []
    if "ulist" in cls:
        ul = el.find("ul")
        return render_list(ul, page_url, up) if ul is not None else []
    if "olist" in cls:
        ol = el.find("ol")
        return render_list(ol, page_url, up, ordered=True) if ol is not None else []
    if "dlist" in cls:
        dl = el.find("dl")
        out = []
        ttl = el.find("div", class_="title")
        if ttl:
            out.append("**%s**" % inline(ttl, page_url, up))
        if dl is not None:
            out += render_dl(dl, page_url, up)
        return out
    if "title" in cls:
        t = inline(el, page_url, up)
        return ["**%s**" % t] if t else []
    # 通用容器（book-content / sect1-4 / sectionbody / content / paragraph / exampleblock …）
    out = []
    for ch in el.children:
        if isinstance(ch, Tag):
            out += render_block(ch, page_url, up)
    return out


def convert(slug, up):
    html = open(os.path.join(ROOT, "pages", slug + ".html"), encoding="utf-8", errors="replace").read()
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main", class_="main-wrapper-book")
    book = main.find("div", class_="book")
    content = book.find("div", class_="book-content") or book
    # 剥站点级噪声：h1 标题保留；translation 过期提示删；toc-mobile 删
    for d in content.find_all("div", class_=["toc-mobile"]):
        d.decompose()
    for d in content.find_all("div", class_="admonitionblock"):
        if "This translation may be out of date" in d.get_text():
            d.decompose()
    lines = []
    for ch in content.children:
        if isinstance(ch, Tag):
            lines += render_block(ch, "https://docs.freebsd.org/zh-cn/books/handbook/%s/" % slug, up)
    md = "\n".join(lines)
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = re.sub(r"[ \t]+\n", "\n", md)
    return md.strip() + "\n"


FNAME_RE = re.compile(r"[\\/:*?\"<>|\n]")


def safe(name):
    return FNAME_RE.sub("_", name).strip()


def build_plan():
    plan = json.load(open(os.path.join(ROOT, "plan.json"), encoding="utf-8"))
    # 组装目标路径
    out = []
    part = None
    chap_no = 0
    app_no = 0
    for p in plan:
        if p["kind"] == "part":
            part = p["title"]
            out.append((p, safe(part), "00-" + safe(part) + ".md"))
        elif p["slug"] == "preface":
            out.append((p, "", "00-" + safe(p["title"]) + ".md"))
        elif part and part.startswith("部分 V"):
            app_no += 1
            out.append((p, safe(part), "%s-%s.md" % (chr(64 + app_no), safe(p["title"]))))
        else:
            chap_no += 1
            out.append((p, safe(part or ""), "%02d-%s.md" % (chap_no, safe(p["title"]))))
    return out


def main():
    cfg = load_upload_cfg(os.path.expanduser("~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json"))
    up = {"cfg": cfg, "user_id": "25689388"} if cfg else None
    print("图片 CDN 上传:", "启用" if up else "关闭", flush=True)
    goal = {p["slug"]: (d, f) for p, d, f in build_plan()}
    for p, d, f in build_plan():
        fp = os.path.join(CLEAN, d, f) if d else os.path.join(CLEAN, f)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        try:
            md = convert(p["slug"], up)
        except Exception as e:
            print("ERR %s: %s" % (p["slug"], e), flush=True)
            raise
        open(fp, "w", encoding="utf-8").write(md)
        print("%-6s %-22s %6d chars  %s" % (p["kind"], p["slug"], len(md),
                                            os.path.relpath(fp, CLEAN)), flush=True)
    print("==== 完成 img_ok=%d img_fail=%d img_skip=%d" % (stats["img_ok"], stats["img_fail"], stats["img_skip"]), flush=True)


if __name__ == "__main__":
    main()
