#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""鸟哥的 Linux 私房菜 - 服务器架设篇 → 语雀
站点专用爬虫（基于 yuque_website_crawl.py 模板，按 vbird 老式排版重写转换器）

站点结构（实探 2026-10-16）：
  - 22 章；每章有「整章全文页」NNNNname.php + 分页 NNNNname_1.php…（全文页 == 分页拼接，勿重复导）
  - 正文档位：<!-- 本文的正式部分 -->（繁体页为 <!-- 本文的正式部分 -->）→ 页脚 <div style="padding-top: 0px; text-align: center;">
  - 标题用 <span class="text_h1|text_h2">（不是 h 标签）；终端块 <table class="term"><pre>
  - 装饰图：大标题的图示 / 小标题的图示 / 鸟哥的图示（剔除，不传 CDN）

产物：site/NN-<章名>.md（顺序 = 章号 1..22）
"""
import re, os, sys, json, time, html as h, urllib.request
import urllib.parse as uparse
from html.parser import HTMLParser

sys.path.insert(0, "/home/admin/.openclaw/workspace/code/yuque-import-skill/scripts")
from yuque_tree_import import upload_image, load_upload_cfg  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(HERE, "pages")
OUT = os.path.join(HERE, "site")
IMGDIR = os.path.join(HERE, "imgs")
IMG_MAP = os.path.join(HERE, "img_map.json")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE = "http://cn.linux.vbird.org/linux_server/"

DECOR_ALT = {"大标题的图示", "小标题的图示", "小標題的圖示", "鸟哥的图示", "鳥哥的圖示", "图示", "圖示"}
VOID = {"br", "hr", "img", "meta", "link", "input", "col", "area", "base", "embed", "source", "track", "wbr"}

_cfg = load_upload_cfg(os.path.expanduser("~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json"))
UP = {"cfg": _cfg, "user_id": "25689388"} if _cfg else None


# ---------------- 图片：下载 + 传 CDN（缓存） ----------------
def img_url(src, page_dir):
    if not src.startswith(("http://", "https://")):
        src = uparse.urljoin(page_dir, src)
    return src


def cdn_url(src):
    if os.environ.get("DRY"):        # 干跑：只下载不上传（验证转换器）
        return src
    mp = {}
    if os.path.exists(IMG_MAP):
        mp = json.load(open(IMG_MAP, encoding="utf-8"))
    if src in mp:
        return mp[src]
    os.makedirs(IMGDIR, exist_ok=True)
    local = os.path.join(IMGDIR, re.sub(r'[^\w.\-]', '_', src)[-120:])
    if not os.path.exists(local):
        req = urllib.request.Request(src, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            open(local, "wb").write(r.read())
    url = None
    for attempt in range(3):
        url = upload_image(UP["cfg"]["cookie"], UP["cfg"]["ctoken"], UP["user_id"], local)
        if url:
            break
        time.sleep(2)
    if url:
        mp[src] = url
        json.dump(mp, open(IMG_MAP, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"    img→CDN {src}", flush=True)
        return url
    print(f"    img FAIL {src}", flush=True)
    return src


# ---------------- 迷你 DOM ----------------
class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs, children, parent):
        self.tag, self.attrs, self.children, self.parent = tag, attrs, children, parent


class DomParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root", {}, [], None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, dict(attrs), [], self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, dict(attrs), [], self.cur))

    def handle_endtag(self, tag):
        c = self.cur
        while c is not None and c.tag != tag:
            c = c.parent
        if c is not None and c.parent is not None:
            self.cur = c.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def find_all(n, tags):
    out = []
    for c in n.children:
        if isinstance(c, Node):
            if c.tag in tags:
                out.append(c)
            else:
                out.extend(find_all(c, tags))
    return out


def txt(n):
    """节点纯文本（用于兜底）"""
    if isinstance(n, str):
        return n
    return "".join(txt(c) for c in n.children)


def inline(n):
    """行内 → markdown（返回字符串，可能含 soft newline）"""
    if isinstance(n, str):
        return n
    t = n.tag
    if t == "br":
        return "\n"
    if t == "img":
        return ""                     # 图片已在预处理替换
    if t == "hr":
        return "\n"
    inner = "".join(inline(c) for c in n.children)
    if t in ("b", "strong"):
        s = inner.strip()
        return f"**{s}**" if s else ""
    if t in ("i", "em"):
        s = inner.strip()
        return f"*{s}*" if s else ""
    if t == "a":
        return link_md(n, inner)
    if t == "span":
        cl = n.attrs.get("class", "")
        if "text_import" in cl or "text_vbird" in cl:
            s = inner.strip()
            return f"**{s}**" if s else ""
        return inner
    if t == "font":
        return inner
    if t in ("p", "div", "li", "td", "th", "ul", "ol", "table", "tbody", "tr", "center", "blockquote"):
        return inner
    return inner


def link_md(n, inner):
    href = (n.attrs.get("href") or "").strip()
    label = re.sub(r"\s+", " ", inner).strip()
    if not href or href.startswith(("#", "javascript:", "mailto:")) or "linux_server" in href:
        return label or ""
    return f"[{label}]({href})"


def clean_inline(s):
    s = re.sub(r"[ \t\u3000]*\n[ \t\u3000]*", " ", s)
    s = re.sub(r"[ \t\u3000]{2,}", " ", s)
    return s.strip()


# ---------------- 块渲染 ----------------
CODE_SLOTS = []


def blocks(n, depth=0):
    """节点 → block 列表（每项是 markdown 片段）；顺序保留"""
    out = []
    buf = []          # 行内缓冲

    def flush():
        if buf:
            s = clean_inline("".join(buf))
            if s:
                out.append(s)
            buf.clear()

    def walk(node, depth):
        for c in node.children:
            if not isinstance(c, Node):
                buf.append(c)
                continue
            t = c.tag
            cl = c.attrs.get("class", "")
            if t == "span" and ("text_h1" in cl or "text_h2" in cl):
                flush()
                lvl = "##" if "text_h1" in cl else "###"
                s = clean_inline(inline(c))
                if s:
                    out.append(f"\n{lvl} {s}")
            elif t == "pre":
                flush()
                code = h.unescape(re.sub(r"<[^>]+>", "", "".join(txt(c)))).strip("\n")
                code = code.replace("\u00a0", " ")
                CODE_SLOTS.append(code)
                out.append(f"\n@@CODE{len(CODE_SLOTS) - 1}@@")
            elif t == "table":
                flush()
                out.extend(render_table(c, depth))
            elif t in ("ul", "ol"):
                flush()
                ls = render_list(c, c.tag == "ol", depth)
                if ls:
                    out.append("\n" + ls)
            elif t == "li":
                walk(c, depth)          # 兜底：孤立 li 当普通块
            elif t == "p":
                if any(isinstance(x, Node) and x.tag in ("div", "ul", "ol", "table", "pre", "center", "blockquote") for x in c.children):
                    flush()
                    walk(c, depth)
                else:
                    flush()
                    s = clean_inline(inline(c))
                    if s:
                        out.append(s)
            elif t in ("div", "center", "blockquote", "font"):
                if any(isinstance(x, Node) and x.tag in ("p", "div", "ul", "ol", "table", "pre", "center", "blockquote") for x in c.children):
                    flush()
                    walk(c, depth)
                else:
                    buf.append(inline(c))
            elif t in ("br", "hr"):
                if t == "br":
                    buf.append("\n")
            elif t == "h1":
                flush()
                out.append("\n# " + clean_inline(inline(c)))
            elif t in ("h2", "h3", "h4"):
                flush()
                out.append("\n" + "#" * int(t[1]) + " " + clean_inline(inline(c)))
            else:
                walk(c, depth)

    walk(n, depth)
    flush()
    return out


def render_list(n, ordered, depth):
    lines = []
    i = 0
    for c in n.children:
        if not (isinstance(c, Node) and c.tag == "li"):
            continue
        i += 1
        inline_buf, subs = [], []
        for cc in c.children:
            if isinstance(cc, Node) and cc.tag in ("ul", "ol"):
                subs.append(cc)
            elif isinstance(cc, Node) and cc.tag in ("p", "div", "center"):
                inline_buf.append(inline(cc))
            else:
                inline_buf.append(inline(cc))
        s = clean_inline("".join(inline_buf))
        pref = f"{i}. " if ordered else "- "
        lines.append("    " * depth + pref + s)
        for s2 in subs:
            lines.append(render_list(s2, s2.tag == "ol", depth + 1))
    return "\n".join(x for x in lines if x.strip())


def render_table(n, depth):
    rows = find_all(n, ("tr",))
    grid = []
    for tr in rows:
        cells = [c for c in tr.children if isinstance(c, Node) and c.tag in ("td", "th")]
        grid.append(cells)
    grid = [r for r in grid if r]
    if not grid:
        return []
    # 单格 → 容器（Tips / 例题框）：按块递归
    if len(grid) == 1 and len(grid[0]) == 1:
        cell = grid[0][0]
        inner = blocks(cell, depth)
        if not inner:
            return []
        txtl = [x for x in inner if x.strip()]
        if len(txtl) == 1 and "@@CODE" not in txtl[0] and sum(len(x) for x in txtl) < 4000:
            body = txtl[0].strip()
            return ["\n> " + body.replace("\n", "\n> ")]     # Tips → 引用块
        return ["\n"] + inner
    # 多行/多列 → markdown 管道表
    out_rows = []
    for r in grid:
        cells = []
        for td in r:
            s = clean_inline(inline(td)).replace("|", "\\|")
            cells.append(s or " ")
        out_rows.append(cells)
    ncol = max(len(r) for r in out_rows)
    out_rows = [r + [" "] * (ncol - len(r)) for r in out_rows]
    lines = ["| " + " | ".join(out_rows[0]) + " |",
             "|" + "|".join(["---"] * ncol) + "|"]
    for r in out_rows[1:]:
        lines.append("| " + " | ".join(r) + " |")
    return ["\n" + "\n".join(lines)]


# ---------------- 页面处理 ----------------
CN = {c: i + 1 for i, c in enumerate("一二三四五六七八九十")}


def cn_num(s):
    """中文数字 → int（只用于章号，最大二十二）"""
    if s == "十":
        return 10
    if s.startswith("十"):
        return 10 + CN.get(s[1:], 0)
    if "十" in s:
        a, b = s.split("十")
        return CN[a] * 10 + (CN.get(b, 0) if b else 0)
    return CN.get(s, 0)


def process(fname):
    raw = open(os.path.join(PAGES, fname), encoding="utf-8", errors="replace").read()
    page_dir = BASE
    trad = "檔頭部分" in raw          # 繁体章（鸟哥这几章没出简体版）
    # 章名 + 章号
    m = re.search(r'<span class="text_head0">(.*?)</span>\s*(?:</a>|<br)', raw, re.S)
    title = h.unescape(re.sub(r"<[^>]+>", "", m.group(1))) if m else fname[:-4]
    title = re.sub(r"\s+", " ", title).strip()
    title = re.sub(r"\s*、\s*", "、", title)
    title = re.sub(r"\s*：\s*", "：", title)
    mnum = re.match(r"第([一二三四五六七八九十]+)章", title)
    chap = cn_num(mnum.group(1)) if mnum else 99
    name = re.sub(r"^第[一二三四五六七八九十]+章、?", "", title)
    # 正文窗口
    i = raw.find("本文的正式部分")
    if i < 0:
        raise RuntimeError("找不到 本文的正式部分")
    j = raw.find("padding-top: 0px; text-align: center;", i)
    body = raw[i + len("本文的正式部分"): j if j > 0 else len(raw)]
    body = re.sub(r"^[^>]*-->", "", body)                     # 去掉注释尾巴
    body = re.sub(r"(?is)<(script|style|link)[^>]*>.*?</\1>|<link[^>]*>|<!--.*?-->", "", body)
    body = re.sub(r'<a\s+name="[^"]*"\s*></a>', "", body)
    # 装饰图剔除
    body = re.sub(r'(?is)<img\b[^>]*>', lambda m: drop_or_keep(m, page_dir), body)
    # 终端块 → 占位
    body = re.sub(r'(?is)<table[^>]*class="term"[^>]*>.*?</table>', term_block, body)
    p = DomParser()
    p.feed(body)
    blk = blocks(p.root)
    md = "\n\n".join(x.strip() for x in blk if x.strip())
    mdate = re.search(r'text_history">(.*?)</span>', raw, re.S)
    date = re.sub(r"<[^>]+>", "", mdate.group(1)).strip() if mdate else ""
    head = f"# {title}"
    if date:
        head += f"\n\n*{date}*"
    md = head + "\n\n" + md
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = re.sub(r"[ \t\u3000]*@@CODE(\d+)@@[ \t\u3000]*", r"\n\n@@CODE\1@@\n\n", md)
    for k, code in enumerate(CODE_SLOTS):
        md = md.replace(f"@@CODE{k}@@", "```\n" + code + "\n```")
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
    return chap, name, md, trad


def drop_or_keep(m, page_dir):
    tag = m.group(0)
    am = re.search(r'alt="([^"]*)"', tag)
    alt = (am.group(1) if am else "").strip()
    sm = re.search(r'src="([^"]*)"', tag)
    src = sm.group(1) if sm else ""
    if alt in DECOR_ALT or "logo.png" in src or "vbird_face.gif" in src:
        return ""
    if not src:
        return ""
    url = cdn_url(img_url(src, page_dir))
    return f'![{alt}]({url})'


def term_block(m):
    inner = m.group(0)
    pre = re.search(r"(?is)<pre[^>]*>(.*?)</pre>", inner)
    seg = pre.group(1) if pre else inner
    code = h.unescape(re.sub(r"<[^>]+>", "", seg)).replace("\u00a0", " ").rstrip()
    CODE_SLOTS.append(code)
    return f"\n@@CODE{len(CODE_SLOTS) - 1}@@\n"


def t2s_convert(md):
    """繁体章 → 简体版（opencc tw2sp；仅用于额外产出的（简体版）文档，原繁体文不动）"""
    try:
        from opencc import OpenCC
        return OpenCC("tw2sp").convert(md)
    except Exception as e:
        print(f"    ⚠️ opencc 不可用，跳过简体版: {e}", flush=True)
        return None


def main():
    os.makedirs(OUT, exist_ok=True)
    fulls = sorted(f for f in os.listdir(PAGES)
                   if re.match(r"^\d{4}[A-Za-z0-9_.-]*\.php$", f) and not re.search(r"_\d+\.php$", f))
    if os.environ.get("ONLY"):
        fulls = [f for f in fulls if os.environ["ONLY"] in f]
    docs = []
    for fn in fulls:
        CODE_SLOTS.clear()
        try:
            chap, name, md, trad = process(fn)
        except Exception as e:
            print(f"ERR {fn}: {e}", flush=True)
            continue
        fname = f"{chap:02d}-{name}.md"
        fname = re.sub(r'[/\\:*?"<>|]', "／", fname)
        open(os.path.join(OUT, fname), "w", encoding="utf-8").write(md)
        docs.append((chap, fname, len(md)))
        print(f"{fname}  {len(md)} chars" + ("  [繁体]" if trad else ""), flush=True)
        if trad:                       # 繁体章额外产出简体版（原文保留）
            s = t2s_convert(md)
            if s:
                sf = fname[:-3] + "（简体版）.md"
                open(os.path.join(OUT, sf), "w", encoding="utf-8").write(s)
                docs.append((chap, sf, len(s)))
                print(f"{sf}  {len(s)} chars  [tw2sp]", flush=True)
    docs.sort()
    print(f"\n共 {len(docs)} 篇；顺序：", flush=True)
    for c, f, n in docs:
        print(f"  {c:02d}  {f}  ({n})", flush=True)
    json.dump([{"chap": c, "file": f} for c, f, n in docs],
              open(os.path.join(HERE, "docs.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
