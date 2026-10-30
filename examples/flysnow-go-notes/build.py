#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fpb52 #105 Go语言实战笔记：flysnow.org 正文 → 语雀导入树

源：仓库 README 索引（rujews/go-in-action-notes @3da951a）+ 作者博客 flysnow.org 正文
- Gin 系列 README 给的是微信公众号链（140 条反爬"环境异常"）→ 换官网同系列同序 6 页
"""
import os, re, sys, json, shutil, urllib.request, time
from bs4 import BeautifulSoup

BASE = "/home/admin/.openclaw/workspace/tmp/fpb105"
RAW = os.path.join(BASE, "raw")
OUT = os.path.join(BASE, "build")

SERIES_TITLES = {
    "Golang Gin 实战系列": "01-Golang Gin 实战系列",
    "Go语言实战笔记": "02-Go语言实战笔记",
    "Go语言经典库使用分析": "03-Go语言经典库使用分析",
}

# README 里 6 条微信链 → 官网同系列页（标题已逐条核对一致）
GIN_MAP = {
    1: "gin-01.html", 2: "gin-02.html", 3: "gin-03.html",
    4: "gin-04.html", 5: "gin-05.html", 6: "gin-06.html",
}

PROMO_BQ = re.compile(r"(欢迎扫码关注公众号|本文为原创文章|转载注明出处|未完待续)")
PROMO_INLINE = re.compile(r"\*{0,2}(欢迎)?(大家)?(继续)?关注公众号[^*。！]*[。！]?\*{0,2}")


def clean_title(t):
    t = t.strip()
    if "|" in t:
        t = t.split("|")[-1].strip()
    t = t.replace("《", "").replace("》", "")
    t = t.replace("/", "／").replace("*", "＊").replace("|", "｜")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def is_promo(block):
    s = block.strip()
    if re.search(r"(为了答谢新老朋友|交流微信群|qrcode_for_weixin|关注公众号|扫码关注)", s):
        return True
    # 末尾只剩一条纯链接（推荐位残渣）
    if re.fullmatch(r"\[[^\]]*\]\([^)]*\)", s):
        return True
    return False


def inline(node):
    """行内 → markdown 文本"""
    out = []
    for c in node.children:
        if isinstance(c, str):
            out.append(str(c))
            continue
        name = c.name
        if name == "code":
            txt = c.get_text()
            out.append("`%s`" % txt if "`" not in txt else txt)
        elif name in ("strong", "b"):
            out.append("**%s**" % inline(c).strip())
        elif name in ("em", "i"):
            out.append("*%s*" % inline(c).strip())
        elif name == "a":
            href = c.get("href", "")
            inner_img = c.find("img")
            if inner_img is not None and not c.get_text().strip():
                src = inner_img.get("src", "")
                if src.startswith("/"):
                    src = "https://www.flysnow.org" + src
                out.append("![%s](%s)" % (inner_img.get("alt", "").strip() or "图", src))
                continue
            txt = inline(c).strip() or href
            if href.startswith("/"):
                href = "https://www.flysnow.org" + href
            out.append("[%s](%s)" % (txt, href) if href else txt)
        elif name == "br":
            out.append("\n")
        elif name == "img":
            src = c.get("src", "")
            if src.startswith("/"):
                src = "https://www.flysnow.org" + src
            out.append("![%s](%s)" % (c.get("alt", "").strip() or "图", src))
        elif name in ("span", "sub", "sup", "small", "kbd", "mark", "del", "u"):
            out.append(inline(c))
        else:
            out.append(inline(c))
    return "".join(out)


def code_block(pre):
    lang = pre.get("data-language") or ""
    txt = pre.get_text()
    txt = txt.replace("\u00a0", " ")
    txt = txt.rstrip("\n")
    lang = {"c++": "cpp", "cs": "csharp", "js": "javascript", "sh": "bash"}.get(lang, lang)
    return "```%s\n%s\n```" % (lang, txt)


def table_md(tbl):
    rows = []
    for tr in tbl.find_all("tr"):
        cells = [inline(td).replace("\n", " ").strip() for td in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    n = max(len(r) for r in rows)
    rows = [r + [""] * (n - len(r)) for r in rows]
    head = "| " + " | ".join(rows[0]) + " |"
    sep = "| " + " | ".join(["---"] * n) + " |"
    body = ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join([head, sep] + body)


def walk(container, bullets=0):
    """块级转换"""
    out = []
    for el in container.children:
        if isinstance(el, str):
            t = str(el).strip()
            if t:
                out.append(t)
            continue
        name = el.name
        cls = el.get("class") or []
        if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            lv = int(name[1])
            txt = inline(el).strip()
            if txt:
                out.append("#" * min(lv + 1, 6) + " " + txt)
        elif name == "p":
            txt = inline(el).strip()
            if txt:
                out.append(txt)
        elif name == "blockquote":
            txt = "\n".join(x for x in walk(el) if x.strip())
            if PROMO_BQ.search(txt.replace("\n", "")):
                continue
            out.append("\n".join("> " + ln if ln else ">" for ln in txt.split("\n")))
        elif name == "pre":
            out.append(code_block(el))
        elif name == "div" and "highlight" in cls:
            pre = el.find("pre")
            out.append(code_block(pre) if pre else "")
        elif name in ("ul", "ol"):
            pad = "  " * bullets
            for i, li in enumerate(el.find_all("li", recursive=False), 1):
                marker = ("%d. " % i) if name == "ol" else "- "
                # li 里可能有子列表 / 段落
                sub = walk(li, bullets + 1)
                if sub:
                    first = sub[0]
                    rest = sub[1:]
                    out.append(pad + marker + first.strip())
                    for r in rest:
                        r = r.rstrip()
                        if r.lstrip().startswith(("- ", "1. ")) or r.lstrip().startswith("  "):
                            out.append(pad + "  " + r.lstrip("\n"))
                        else:
                            out.append(pad + "  " + r)
        elif name == "table":
            t = table_md(el)
            if t:
                out.append(t)
        elif name == "img":
            src = el.get("src", "")
            if src:
                out.append("![%s](%s)" % (el.get("alt", "").strip() or "图", src))
        elif name == "figure":
            sub = walk(el)
            if sub:
                out.append("\n".join(sub))
        elif name == "hr":
            out.append("---")
        elif name == "aside":
            sub = walk(el)
            if sub:
                out.append("\n".join("> " + ln if ln else ">" for x in sub for ln in x.split("\n")))
        else:
            sub = walk(el, bullets)
            if sub:
                out.append("\n".join(sub))
    return out


def convert(path):
    h = open(path, encoding="utf-8", errors="replace").read()
    soup = BeautifulSoup(h, "html5lib")
    h1 = soup.find("h1")
    title = h1.get_text().strip() if h1 else ""
    pc = soup.find("div", class_="post-content")
    if pc is None:
        raise RuntimeError("no post-content: " + path)

    # 剔推广/二维码
    for img in pc.find_all("img"):
        if "qrcode_for_weixin" in (img.get("src") or ""):
            p = img.find_parent(["p", "a"])
            if p is not None and p.name == "p":
                p.decompose()
            elif p is not None and p.name == "a" and p.find_parent("p") is not None:
                p.find_parent("p").decompose()
            else:
                img.decompose()

    blocks = [b for b in walk(pc) if b and b.strip()]

    # 尾部导航/推广清理（本站所有文章都是「正文 → 精彩文章推荐 → 红包/扫码」结构）
    for i, b in enumerate(blocks):
        if re.match(r"^#{2,4}\s*精彩文章推荐\s*$", b.strip()):
            blocks = blocks[:i]
            break
    while blocks and is_promo(blocks[-1]):
        blocks.pop()

    md = "\n\n".join(blocks)
    # 行内推广句
    md = PROMO_INLINE.sub("", md)
    # 图片绝对化（稍后本地化）
    md = re.sub(r"\]\(/uploads/", "](https://www.flysnow.org/uploads/", md)
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
    return title, md


def fetch_img(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        open(dest, "wb").write(r.read())
    time.sleep(0.5)


def main():
    man = json.load(open(os.path.join(BASE, "manifest.json"), encoding="utf-8"))
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    counters = {}
    report = []
    for item in man:
        seq = item["seq"]
        src = GIN_MAP.get(seq, item["file"])
        path = os.path.join(RAW, src)
        if not os.path.exists(path):
            raise RuntimeError("missing raw: " + path)
        title_raw, md = convert(path)
        series = item["series"]
        dirname = SERIES_TITLES[series]
        counters[series] = counters.get(series, 0) + 1
        idx = counters[series]
        title = clean_title(title_raw)

        d = os.path.join(OUT, dirname)
        os.makedirs(d, exist_ok=True)

        # 本地化图片：/uploads/... → 同目录文件
        def loc(m):
            url = m.group(2)
            name = url.split("/")[-1]
            try:
                fetch_img(url, os.path.join(d, name))
                return "%s%s%s" % (m.group(1), name, m.group(3))
            except Exception as e:
                print("  img fail %s %s" % (url, e))
                return m.group(0)
        md = re.sub(r"(!\[[^\]]*\]\()(https://www\.flysnow\.org/uploads/[^)]+)(\))", loc, md)

        fn = "%02d-%s.md" % (idx, title)
        open(os.path.join(d, fn), "w", encoding="utf-8").write(md)
        report.append({"seq": seq, "series": series, "idx": idx, "title": title,
                       "file": os.path.join(dirname, fn), "bytes": len(md.encode())})

    # 00-说明
    intro = """# 00-说明

**《Go语言实战》读书笔记系列**（作者：飞雪无情 / flysnow.org）

- 索引来源：GitHub 仓库 `rujews/go-in-action-notes` @ `3da951a`（README 即全书目录）
- 正文来源：作者博客 <https://www.flysnow.org>（正文抓取，非公众号）
- 导入日期：2026-10-31

## 收录范围（三个系列，共 41 篇）

| 系列 | 篇数 | 内容 |
|---|---|---|
| Golang Gin 实战系列 | 6 | Gin 框架入门、Restful API、路由/查询/表单参数 |
| Go语言实战笔记 | 29 | 环境搭建 + Go 包/数组/切片/Map/类型/方法/接口/并发/通道/反射/unsafe 等 |
| Go语言经典库使用分析 | 6 | Gorilla Context、Gorilla Handlers、Negroni 中间件源码分析 |

## 口径说明

- 仓库 README 里 **Gin 系列 6 篇给的是微信公众号链接**（`mp.weixin.qq.com`，直接抓取返回「环境异常」反爬页），
  已换成作者官网**同系列、同序号**的 6 篇文章（标题逐条比对一致），正文完整。
- 每篇保留作者正文；已剔除页尾「本文为原创文章 / 欢迎扫码关注公众号」推广块与公众号二维码图。
- 原文内的站内相对链接补全为 `https://www.flysnow.org/...` 绝对地址。
- 两个系列的三篇文章在原文里没有小标题（纯段落 + 代码），已原样保留结构。
"""
    open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8").write(intro)

    json.dump(report, open(os.path.join(BASE, "report.json"), "w"), ensure_ascii=False, indent=1)
    print("docs:", len(report))
    for r in report:
        print("%s %s %s %dB" % (r["series"][:8], r["idx"], r["title"], r["bytes"]))


if __name__ == "__main__":
    main()