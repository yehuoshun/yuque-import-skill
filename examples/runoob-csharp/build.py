#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""#68 菜鸟教程 C# 教程 → markdown（网站口径，复用 #29 runoob 转换器）
窗口: div.article-intro#content；代码块 div.example_code/pre；quiz 不收录；
站内 /csharp/ 链接 → 纯文字；图片 → 语雀 CDN（img_map.json 断点）。
"""
import os, re, sys, json, html as h, urllib.request
from bs4 import BeautifulSoup, Tag, NavigableString, Comment

sys.path.insert(0, "/home/admin/.openclaw/workspace/code/yuque-import-skill/scripts")
from yuque_tree_import import upload_image, load_upload_cfg  # noqa: E402

HERE = "/home/admin/.openclaw/workspace/tmp/fpb-068-csharp"
CACHE = os.path.join(HERE, "pages")
OUT = os.path.join(HERE, "site")
IMGMAP = os.path.join(HERE, "img_map.json")
os.makedirs(OUT, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE = "https://www.runoob.com"

SLUG2MD = {
    "csharp-tutorial.html": "01-C# 教程.md", "csharp-intro.html": "02-C# 简介.md",
    "csharp-environment-setup.html": "03-开发环境.md", "csharp-program-structure.html": "04-程序结构.md",
    "csharp-basic-syntax.html": "05-基本语法.md", "csharp-data-types.html": "06-数据类型.md",
    "csharp-type-conversion.html": "07-类型转换.md", "csharp-variables.html": "08-变量.md",
    "csharp-variable-scope.html": "09-变量作用域.md", "csharp-constants.html": "10-常量.md",
    "csharp-operators.html": "11-运算符.md", "csharp-decision.html": "12-判断.md",
    "csharp-loops.html": "13-循环.md", "csharp-encapsulation.html": "14-封装.md",
    "csharp-methods.html": "15-方法.md", "csharp-nullable.html": "16-可空类型.md",
    "csharp-array.html": "17-数组.md", "csharp-string.html": "18-字符串.md",
    "csharp-struct.html": "19-结构体.md", "csharp-enum.html": "20-枚举.md",
    "csharp-class.html": "21-类.md", "csharp-inheritance.html": "22-继承.md",
    "csharp-polymorphism.html": "23-多态性.md", "csharp-operator-overloading.html": "24-运算符重载.md",
    "csharp-interface.html": "25-接口.md", "csharp-namespace.html": "26-命名空间.md",
    "csharp-preprocessor-directives.html": "27-预处理器指令.md",
    "csharp-regular-expressions.html": "28-正则表达式.md", "csharp-exception-handling.html": "29-异常处理.md",
    "csharp-file-io.html": "30-文件的输入与输出.md", "csharp-attribute.html": "31-特性.md",
    "csharp-reflection.html": "32-反射.md", "csharp-property.html": "33-属性.md",
    "csharp-indexer.html": "34-索引器.md", "csharp-delegate.html": "35-委托.md",
    "csharp-event.html": "36-事件.md", "csharp-collection.html": "37-集合.md",
    "csharp-generic.html": "38-泛型.md", "csharp-anonymous-methods.html": "39-匿名方法.md",
    "csharp-unsafe-codes.html": "40-不安全代码.md", "csharp-multithreading.html": "41-多线程.md",
}
# 站内链接 → 本库 md（纯文字化）
CS2MD = {k: v for k, v in SLUG2MD.items()}

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()

def load_imgs():
    try:
        return json.load(open(IMGMAP, encoding="utf-8"))
    except Exception:
        return {}

def save_imgs(mp):
    json.dump(mp, open(IMGMAP, "w", encoding="utf-8"), ensure_ascii=False)

_up_cfg = None
def get_up():
    global _up_cfg
    if _up_cfg is None:
        cfg = load_upload_cfg("/home/admin/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json")
        _up_cfg = {"cfg": cfg, "user_id": "25689388"} if cfg else None
    return _up_cfg

def img_to_cdn(src, mp):
    if src in mp:
        return mp[src]
    try:
        raw = fetch(src)
        ext = os.path.splitext(src)[1][:8] or ".png"
        tmp = "/tmp/rb68-img" + ext
        with open(tmp, "wb") as f:
            f.write(raw)
        up = get_up()
        url = upload_image(up["cfg"]["cookie"], up["cfg"]["ctoken"], up["user_id"], tmp)
        os.remove(tmp)
        if url:
            mp[src] = url
            save_imgs(mp)
            print("  img->CDN", src)
            return url
    except Exception as e:
        print("  img FAIL", src, e)
    return src

def _abs_img(src):
    if src.startswith("//"):
        src = "https:" + src
    elif src.startswith("/"):
        src = BASE + src
    elif not src.startswith(("http://", "https://")):
        src = BASE + "/" + src
    return src

def inline_text(node, mp):
    parts = []
    for t in node.contents:
        if isinstance(t, NavigableString):
            if not isinstance(t, Comment):
                parts.append(str(t))
        elif isinstance(t, Tag):
            if t.name == "br":
                parts.append("\n")
            elif t.name == "img":
                src = t.get("src", "")
                alt = (t.get("alt") or "").strip()
                if src.startswith(("data:", "$")):
                    continue
                url = img_to_cdn(_abs_img(src), mp)
                parts.append("![%s](%s)" % (alt, url))
            elif t.name == "a":
                href = t.get("href", "")
                txt = inline_text(t, mp).strip()
                if not txt:
                    continue
                if "/try/" in href or href.startswith("javascript:"):
                    continue
                if "/csharp/" in href:
                    parts.append(txt)
                else:
                    parts.append("[%s](%s)" % (txt, href))
            elif t.name in ("strong", "b"):
                parts.append("**" + inline_text(t, mp) + "**")
            elif t.name in ("em", "i"):
                parts.append("*" + inline_text(t, mp) + "*")
            elif t.name in ("code", "tt", "span", "font", "sub", "sup"):
                parts.append(inline_text(t, mp))
            else:
                parts.append(inline_text(t, mp))
    return h.unescape("".join(parts))

def code_text(node):
    txt = h.unescape(node.get_text())
    lines = [ln.rstrip() for ln in txt.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)

def table_md(node, mp):
    rows = []
    for tr in node.find_all("tr"):
        cells = []
        for td in tr.find_all(["td", "th"]):
            cells.append(re.sub(r"\s+", " ", inline_text(td, mp)).replace("|", "\\|").strip())
        rows.append("| " + " | ".join(cells) + " |")
    if len(rows) >= 2:
        n = rows[0].count("|") - 1
        sep = "|" + "|".join("---" for _ in range(n)) + "|"
        return "\n".join([rows[0], sep] + rows[1:])
    return "\n".join(rows)

SKIP_DIVS = {"tryit", "example", "marked", "quiz", "tutintro", "notranslate", "result"}

def render_block(node, mp, out):
    if isinstance(node, Comment):
        return
    if isinstance(node, NavigableString):
        t = str(node).strip()
        if t:
            out.append(t)
        return
    name = node.name
    cls = " ".join(node.get("class") or [])
    if name in ("script", "style", "noscript", "iframe", "form", "ins", "nav"):
        return
    if name == "br":
        return
    if name == "a":
        href = node.get("href", "")
        txt = inline_text(node, mp).strip()
        if not txt:
            return
        if "/try/" in href or href.startswith("javascript:"):
            return
        if "/csharp/" in href:
            out.append(txt)
        else:
            out.append("[%s](%s)" % (txt, href))
        return
    if name == "div":
        if ("tryit" in cls or "quiz" in cls or "interactive" in cls
                or node.get("id") in ("flags", "exp", "txt", "content_views")):
            return
        if "hl-main" in cls or "example_code" in cls or "marked" in cls:
            c = code_text(node)
            if c.strip():
                out.append("```\n" + c + "\n```")
            return
        if "table-responsive" in cls or "data-container" in cls:
            for ch in node.children:
                render_block(ch, mp, out)
            return
        for ch in node.children:
            render_block(ch, mp, out)
        return
    if name in ("h1", "h2", "h3", "h4", "h5"):
        t = inline_text(node, mp).strip()
        if t == "测试工具":
            return
        if t:
            out.append("\n" + "#" * int(name[1]) + " " + t)
        return
    if name == "p":
        t = inline_text(node, mp).strip()
        if t:
            out.append(t)
        return
    if name in ("ul", "ol"):
        for li in node.find_all("li", recursive=False):
            t = inline_text(li, mp).strip()
            if t:
                out.append("- " + t)
        return
    if name == "table":
        t = table_md(node, mp)
        if t:
            out.append("\n" + t)
        return
    if name == "pre":
        c = code_text(node)
        if c.strip():
            out.append("```\n" + c + "\n```")
        return
    if name == "img":
        src = node.get("src", "")
        alt = (node.get("alt") or "").strip()
        if src.startswith(("data:", "$")):
            return
        url = img_to_cdn(_abs_img(src), mp)
        out.append("![%s](%s)" % (alt, url))
        return
    if name == "hr":
        return
    for ch in node.children:
        render_block(ch, mp, out)

def convert(slug):
    html = open(os.path.join(CACHE, slug), encoding="utf-8", errors="replace").read()
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one("div.article-intro#content") or soup.select_one("div.article-body")
    if content is None:
        print("NO CONTENT", slug)
        return None
    mp = load_imgs()
    out = []
    for ch in content.children:
        render_block(ch, mp, out)
    md = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
    md = re.sub(r"^# .*\n+", "", md)
    md = re.sub(r"^!\[[^\]]*\]\([^)]*\)\n+", "", md)
    save_imgs(mp)
    return md.strip() + "\n"

def main():
    ok = 0
    for slug in sorted(SLUG2MD):
        md = convert(slug)
        if md is None:
            continue
        fname = SLUG2MD[slug]
        open(os.path.join(OUT, fname), "w", encoding="utf-8").write(md)
        print("ok", fname, len(md))
        ok += 1
    print("total", ok)

if __name__ == "__main__":
    main()