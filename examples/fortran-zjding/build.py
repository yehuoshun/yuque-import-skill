#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fortran-zjding：丁泽军《Fortran77和90/95编程入门》USTC micro 站 → 语雀 clean 树

- 源: http://micro.ustc.edu.cn/Fortran/ZJDing/  (Word 导出的 HTML, 2001-2002)
- 20 个章节页 Sec<ch>-<n>.htm，标题/层级取自 index.html
- 示例代码在 example/*.f|f90（GBK/UTF-8 混合）→ 就地内联为代码块
- 公式/插图 gif|jpg → 下载进 images/，交给 yuque_rewrite_images.py 传 CDN
"""
import os, re, sys, glob, html, shutil, urllib.request
import bs4

BASE = "http://micro.ustc.edu.cn/Fortran/ZJDing/"
RAW = "/tmp/f95/raw"
EXDIR = "/tmp/f95/ex"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/f95/clean"

# ---- 目录结构（来自 index.html）----
CHAPTERS = [
    ("1", "Fortran语言程序设计初步"),
    ("2", "改变程序流程"),
    ("3", "循环结构"),
    ("4", "数据结构"),
    ("5", "数组"),
    ("6", "过程和模块"),
    ("7", "输入输出和文件"),
]
SECTIONS = [  # (页文件, 编号, 标题, 章)
    ("Sec1-1", "1.1", "Fortran语言发展概况", "1"),
    ("Sec1-2", "1.2", "Fortran程序简例", "1"),
    ("Sec1-3", "1.3", "Fortran程序的基本组成", "1"),
    ("Sec1-4", "1.4", "数学运算", "1"),
    ("Sec1-5", "1.5", "Compaq Visual Fortran软件的使用", "1"),
    ("Sec2-1", "2.1", "算法和流程图", "2"),
    ("Sec2-2", "2.2", "逻辑运算", "2"),
    ("Sec2-3", "2.3", "选择结构", "2"),
    ("Sec3-1", "3.1", "单纯循环", "3"),
    ("Sec3-2", "3.2", "条件循环", "3"),
    ("Sec4-1", "4.1", "数据类型和属性", "4"),
    ("Sec4-2", "4.2", "非数值型数据", "4"),
    ("Sec4-3", "4.3", "派生数据类型", "4"),
    ("Sec5-1", "5.1", "数组定义与类型", "5"),
    ("Sec5-2", "5.2", "数组赋值与运算", "5"),
    ("Sec6-1", "6.1", "程序单元结构", "6"),
    ("Sec6-2", "6.2", "过程", "6"),
    ("Sec6-3", "6.3", "模块", "6"),
    ("Sec7-1", "7.1", "输入输出编辑", "7"),
    ("Sec7-2", "7.2", "文件的存取", "7"),
]

CODE_RE = re.compile(r"color:\s*#(?:FF9900|FF6600)", re.I)
MARGIN_RE = re.compile(r"margin-left:\s*([\d.]+)pt")
def is_code(p, txt):
    htmls = str(p)
    if "mso-list" in htmls:
        return False   # 列表项，交给列表渲染
    if p.find("img") is not None:
        return False   # 含图的段落（插图+题注），不当代码
    if CODE_RE.search(htmls):
        # 橙色既用于语法模板(代码)，也用于成段中文提示(注意事项)：长且以句号收尾的当中文
        if len(txt) > 60 and txt.rstrip().endswith("。"):
            return False
        return True
    if "。" in txt:
        return False
    if "text-autospace:none" in htmls:
        return True
    m = MARGIN_RE.search(htmls)
    if m and float(m.group(1)) >= 40:
        return True
    ti = re.search(r"text-indent:\s*([\d.]+)pt", htmls)
    if ti and float(ti.group(1)) >= 40 and "line-height:15" in htmls:
        return True
    return False

def sanitize(name):
    return re.sub(r'[^\w.]+', '_', name)

IMG_CACHE = {}   # src -> local rel name

def img_ref(src):
    """src like Sec1-4.files/image004.gif -> images/<page>_<file>"""
    if src in IMG_CACHE:
        return IMG_CACHE[src]
    base = os.path.basename(src)
    page = src.split(".files")[0] if ".files" in src else "img"
    local = "../images/%s_%s" % (sanitize(page), sanitize(base))
    IMG_CACHE[src] = local
    return local

def render_inline(node, ctx):
    """递归渲染行内内容 -> markdown 片段。ctx collects examples/movies."""
    out = []
    for c in node.children:
        if isinstance(c, bs4.Comment):
            continue
        if isinstance(c, bs4.NavigableString):
            out.append(str(c))
        elif c.name == "img":
            src = c.get("src", "")
            w = int(c.get("width") or 0)
            h = int(c.get("height") or 0)
            if src and ("files/" in src):
                if w <= 16 and h <= 16:
                    continue  # 装饰性项目符号
                out.append("![公式](%s)" % img_ref(src))
        elif c.name in ("o:p", "v:shapetype", "v:shape", "v:imagedata", "xml"):
            continue
        elif c.name in ("b", "strong"):
            t = render_inline(c, ctx).strip()
            out.append("**%s**" % t if t else "")
        elif c.name in ("i", "em"):
            t = render_inline(c, ctx).strip()
            out.append("*%s*" % t if t else "")
        elif c.name == "sup":
            t = render_inline(c, ctx).strip()
            out.append("^{%s}" % t)
        elif c.name == "sub":
            t = render_inline(c, ctx).strip()
            out.append("_{%s}" % t)
        elif c.name == "a":
            href = c.get("href", "")
            t = render_inline(c, ctx).strip()
            if href.startswith("example/") or href.startswith("EXAMPLE/"):
                fname = href.split("/", 1)[1]
                ctx["examples"].append(fname)
                # 链接本体丢弃（代码会内联到段后）
            elif href.startswith("movie/"):
                ctx["movies"].append(href)
                out.append("（动画 [%s](%s%s)）" % (os.path.basename(href), BASE, href))
            elif href.startswith("http"):
                out.append("[%s](%s)" % (t, href) if t else href)
            elif href.startswith("#") or href == "":
                out.append(t)
            else:
                out.append(t)
        elif c.name == "br":
            out.append("  \n")
        else:
            out.append(render_inline(c, ctx))
    s = "".join(out)
    s = s.replace("\xa0", " ").replace("\u3000", " ")
    s = re.sub(r"[ \t]+", " ", s).strip()
    s = s.replace("[]", "")   # 示例链接被内联后残留的空方括号
    s = re.sub(r"\[if[^\]]*\]|\[endif\]", "", s)
    s = re.sub(r"\[if[^\]]*&[^\]]*\]", "", s)
    return s

def render_table(tbl, ctx):
    rows = []
    for tr in tbl.find_all("tr"):
        cells = []
        for cell in tr.find_all(["td", "th"]):
            t = render_inline(cell, ctx)
            cells.append(t.replace("|", "\\|").replace("\n", " "))
        if any(c.strip() for c in cells):
            rows.append(cells)
    if not rows:
        return ""
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    lines = ["| " + " | ".join(rows[0]) + " |",
             "| " + " | ".join(["---"] * ncol) + " |"]
    for r in rows[1:]:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)

def load_code(fname):
    for cand in (fname, fname.lower()):
        p = os.path.join(EXDIR, os.path.basename(cand).lower())
        if os.path.exists(p):
            raw = open(p, "rb").read()
            for enc in ("utf-8", "gb18030"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", "replace")
    return None

def code_lang(fname):
    if fname.endswith(".f90"):
        return "fortran"
    if fname.endswith(".for") or fname.endswith(".f"):
        return "fortran"
    return "text"

def build_section(page, num, title, chap):
    soup = bs4.BeautifulSoup(open(os.path.join(RAW, page + ".htm"),
                                  encoding="utf-8", errors="replace").read(), "html5lib")
    body = soup.body
    root = body.find("div", class_="Section1") or body
    out = []
    code_buf = []
    ex_done = set()

    def flush_code():
        if code_buf:
            out.append("```fortran\n" + "\n".join(code_buf).rstrip() + "\n```")
            code_buf.clear()

    def flush_examples(ctx):
        for f in ctx["examples"]:
            if f in ex_done:
                continue
            ex_done.add(f)
            code = load_code(f)
            if code is None:
                out.append("> 示例文件 `%s`（未取到）" % f)
                continue
            out.append("**示例文件 `%s`：**" % os.path.basename(f))
            out.append("```%s\n%s\n```" % (code_lang(f), code.rstrip("\n")))
        ctx["examples"] = []

    for el in root.children:
        if isinstance(el, bs4.NavigableString):
            continue
        ctx = {"examples": [], "movies": []}
        if el.name == "table":
            flush_code()
            out.append(render_table(el, ctx))
            flush_examples(ctx)
        elif el.name == "p" or el.name in ("div", "h1", "h2", "h3", "h4", "pre"):
            txt = el.get_text("", strip=True)
            if not txt and el.find("img") is None:
                continue
            htmls = str(el)
            szs = [int(x) for x in re.findall(r"font-size:\s*(\d+)", htmls)]
            sz = max(szs) if szs else 0
            if sz >= 22:
                # 章标题/节标题：均由 TOC 目录与文档名承载，正文内不再重复
                continue
            if sz == 16:
                flush_code()
                out.append("## " + re.sub(r"^(\d+\.\d+\.\d+)\s*", r"\1 ", txt))
                flush_examples(ctx)
                continue
            if "color:red" in htmls and re.match(r"^[a-z]\)", txt):
                flush_code()
                out.append("### " + txt)
                flush_examples(ctx)
                continue
            if is_code(el, txt):
                line = render_inline(el, ctx)
                code_buf.append(line)
                flush_examples(ctx)
                continue
            flush_code()
            md = render_inline(el, ctx)
            if md:
                if "mso-list" in htmls:
                    md = "- " + md
                out.append(md)
            flush_examples(ctx)
        else:
            continue
    flush_code()

    # 收尾：清理空行
    text = "\n\n".join(x for x in out if x.strip())
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def main():
    # 准备输出树
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "images"), exist_ok=True)
    chmap = {c: "第%s章 %s" % (c, t) for c, t in CHAPTERS}
    for c, _ in CHAPTERS:
        os.makedirs(os.path.join(OUT, chmap[c]), exist_ok=True)

    for page, num, title, chap in SECTIONS:
        md = build_section(page, num, title, chap)
        fname = "%s %s.md" % (num, title.replace("/", "／"))
        with open(os.path.join(OUT, chmap[chap], fname), "w", encoding="utf-8") as f:
            f.write("# %s %s\n\n%s\n" % (num, title, md))

    # 下载所有引用到的图片
    n = 0
    for src, local in IMG_CACHE.items():
        dst = os.path.join(OUT, local.replace("../", ""))
        url = BASE + src
        try:
            d = urllib.request.urlopen(url, timeout=30).read()
            open(dst, "wb").write(d)
            n += 1
        except Exception as e:
            print("IMGFAIL", src, e)
    print("images downloaded:", n)

main()
