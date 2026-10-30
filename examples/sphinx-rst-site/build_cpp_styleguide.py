#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fpb #82 《Google C++ 风格指南》(zh-google-styleguide) Sphinx 站 → 语雀 md
源：readthedocs 的 `_sources/google-cpp-styleguide/*.rst.txt`（Sphinx 源，直取 rst，最干净）
口径：网站口径（无独立 md 仓库；readthedocs 的 _sources 即站源）
处理：
  - 复用 yuque-import-skill 的 yuque_rst_convert.rst_to_md（docutils html5 中间层）
  - ⚠️ 修 bug：原 html_to_md 的 admonition（Tip/Note 提示框）输出多行引用块后，
    被块间隙的 inline() 把换行压成空格（`> **Tip**： > 内容`）→ 用占位符把提示框
    先摘出来、扫描完再回填
  - 剥首个 H1（= 章标题，文件名已承载，避免语雀双标题）
  - 文件名 NN-章名.md（剥原章号，序号前缀保序）
"""
import os, re, sys, glob

SKILL = "/home/admin/.openclaw/workspace/code/yuque-import-skill/scripts"
sys.path.insert(0, SKILL)
import yuque_rst_convert as Y
from docutils.core import publish_parts
import html as h

HERE = os.path.dirname(os.path.abspath(__file__))
RST = os.path.join(HERE, "rst")
OUT = os.path.join(HERE, "site")

# 章源文件 -> 输出文件名（顺序即书序；index 是扉页/前言）
PAGES = [
    ("index",      "00-扉页"),
    ("headers",    "01-头文件"),
    ("scoping",    "02-作用域"),
    ("classes",    "03-类"),
    ("functions",  "04-函数"),
    ("magic",      "05-来自 Google 的奇技"),
    ("others",     "06-其他 C++ 特性"),
    ("naming",     "07-命名约定"),
    ("comments",   "08-注释"),
    ("formatting", "09-格式"),
    ("exceptions", "10-规则特例"),
    ("end",        "11-结束语"),
]

# ---------- monkey-patch：带占位符的 html_to_md（修提示框换行） ----------
def _lang_of(attrs):
    m = re.search(r'class="([^"]*)"', attrs or "")
    if not m:
        return ""
    for cls in m.group(1).split():
        if cls not in ("code", "literal-block", "highlight", "doctest-block", "raw"):
            return cls
    return ""

# ---------- 行内字面量：docutils html5 输出 <span class="docutils literal"> 而非 <tt> ----------
_orig_inline = Y.inline
_SPAN_OPEN = re.compile(r'<span class="docutils literal[^"]*">')
_SPAN_TAG = re.compile(r'</?span\b[^>]*>')
def _wrap_literals(t):
    """把 docutils literal span（可能含内层 <span class="pre">）整体转为行内 code
    深度计数找外层 </span>；不 unescape（交给 _orig_inline 统一，否则 < > 被当 HTML 剥掉）"""
    out, pos = [], 0
    while True:
        m = _SPAN_OPEN.search(t, pos)
        if not m:
            out.append(t[pos:]); break
        out.append(t[pos:m.start()])
        depth, i = 1, m.end()
        while i < len(t) and depth > 0:
            nm = _SPAN_TAG.search(t, i)
            if not nm: break
            depth += -1 if t[nm.start():nm.start()+2] == "</" else 1
            i = nm.end()
        inner = re.sub(r'</?span\b[^>]*>', "", t[m.end():i]).strip()
        out.append("`" + inner + "`")
        pos = i
    return "".join(out)

def inline_fixed(t):
    return _orig_inline(_wrap_literals(t))
Y.inline = inline_fixed


def _apply_pfx(blocks, first, cont):
    out = []
    for i, (k, t) in enumerate(blocks):
        p = first if i == 0 else cont
        out.append((k, "\n".join(p + l if l else l for l in t.split("\n"))))
    return out


def html_to_md_fixed(body):
    # 提示框先用占位符摘出（否则多行引用块被块间隙的 inline 压成一行）
    bq = {}

    def restore(text):
        return re.sub(r"\x00BQ\d+\x00",
                      lambda m: _wrap_literals(bq.get(m.group(0), m.group(0))), text)

    def add_line(lines, text):
        """把文本逐行插入引用块；已带 > 前缀的行（来自嵌套提框占位符）原样保留"""
        for ln in text.split("\n"):
            lines.append(ln if ln.startswith(">") else "> " + ln)

    def make_bq(inner):
        inner = convert_admonitions(inner)   # 先递归处理内层提框 → 占位符
        title = ""
        tm = re.search(r'<p[^>]*class="[^"]*admonition-title[^"]*"[^>]*>(.*?)</p>', inner, re.S)
        if tm:
            title = Y.inline(tm.group(1))
            inner = inner[:tm.start()] + inner[tm.end():]
        lines = [("> **%s**：" % title) if title else ">"]
        # 保序抽块：alternation 不含 div，且带 \b（否则 (p) 会匹 <pre 前缀）
        pos2 = 0
        for mm2 in re.finditer(r"<(p|ul|ol|pre|blockquote)\b([^>]*)>(.*?)</\1>", inner, re.S):
            if mm2.start() > pos2:   # 块间隙（含嵌套提框占位符）不能丢
                t = restore(Y.inline(inner[pos2:mm2.start()]))
                if t.strip(): add_line(lines, t)
            pos2 = mm2.end()
            tag, attrs, bi = mm2.group(1), mm2.group(2), mm2.group(3)
            if tag == "pre":
                code = h.unescape(re.sub(r"<[^>]+>", "", bi)).strip("\n")
                lines.append("> ```")
                lines.extend("> " + c for c in code.split("\n"))
                lines.append("> ```")
            elif tag in ("ul", "ol"):
                for li in re.findall(r"<li[^>]*>(.*?)</li>", bi, re.S):
                    t = restore(Y.inline(li))
                    if t: add_line(lines, "- " + t)
            else:
                t = restore(Y.inline(bi))
                if t: add_line(lines, t)
        if pos2 < len(inner):
            t = restore(Y.inline(inner[pos2:]))
            if t.strip(): add_line(lines, t)
        if len(lines) == 1:
            t = restore(Y.inline(re.sub(r"<[^>]+>", " ", inner)))
            if t: add_line(lines, t)
        key = "\x00BQ%d\x00" % len(bq)
        bq[key] = "\n".join(lines)
        return "\n\n" + key + "\n\n"

    def convert_admonitions(src):
        out, pos = [], 0
        pat = re.compile(r'<(div|aside) class="admonition[^"]*">')
        while True:
            m = pat.search(src, pos)
            if not m:
                out.append(src[pos:]); break
            out.append(src[pos:m.start()])
            tag = m.group(1)
            depth, end = 0, None
            for mm in re.finditer(r'</?' + tag + r'\b[^>]*>', src[m.start():]):
                depth += -1 if src[m.start()+mm.start()+1] == "/" else 1
                if depth == 0:
                    end = m.start() + mm.end(); break
            if end is None:
                out.append(src[m.start():]); break
            out.append(make_bq(src[m.end():end - len(tag) - 3]))
            pos = end
        return "".join(out)

    body = re.sub(r'<(aside|dl)[^>]*class="(?:footnote|citation)[^"]*"[^>]*>.*?</\1>', "", body, flags=re.S)
    body = convert_admonitions(body)

    def restore(text):
        def _r(m):
            return _wrap_literals(bq.get(m.group(0), m.group(0)))
        return re.sub(r"\x00BQ\d+\x00", _r, text)

    # ---------- 递归渲染：dd/li/blockquote 内的块级（尤其代码块）不再被 inline 吞 ----------
    def render(frag):
        res = []
        def lp(kind, text):
            if text and text.strip():
                res.append((kind, text))
        pos = 0
        for mm in Y.BLOCK_RE.finditer(frag):
            if mm.start() > pos:
                lp("p", restore(Y.inline(frag[pos:mm.start()])))
            pos = mm.end()
            tag, attrs, inner = mm.group(1), mm.group(2), mm.group(3)
            if tag.startswith("h"):
                lp("h", "#" * int(tag[1]) + " " + restore(Y.inline(inner)))
            elif tag == "pre":
                code = h.unescape(re.sub(r"<[^>]+>", "", inner)).strip("\n")
                lp("pre", "```" + _lang_of(attrs) + "\n" + code + "\n```")
            elif tag == "table":
                lp("table", Y.table_md(inner))
            elif tag == "blockquote":
                sub = _apply_pfx(render(inner), "> ", "> ")
                for k, t in sub:
                    lp(k, t)
            elif tag == "p":
                lp("p", restore(Y.inline(inner)))
            elif tag == "li":
                res.extend(_apply_pfx(render(inner), "- ", "  "))
            elif tag == "dt":
                lp("dt", "**" + restore(Y.inline(inner)) + "**")
            elif tag == "dd":
                res.extend(_apply_pfx(render(inner), "  ", "  "))
        if pos < len(frag):
            lp("p", restore(Y.inline(frag[pos:])))
        return res

    out = render(body)
    KEEP = {("li", "li"), ("table", "table"), ("bq", "bq"),
            ("dt", "dt"), ("dt", "dd"), ("dd", "dd"), ("dd", "dt")}
    chunks = []
    for i, (kind, text) in enumerate(out):
        if i:
            sep = "\n" if (out[i-1][0], kind) in KEEP else "\n\n"
            chunks.append(sep)
        chunks.append(text)
    md = re.sub(r"\n{3,}", "\n\n", "".join(chunks))
    return md.strip() + "\n"

Y.html_to_md = html_to_md_fixed   # rst_to_md 内部引用模块全局名 → 生效
# ⚠️ 修 BLOCK_RE：原正则 <(h1-6|pre|p|...) 里 p 分支会匹配 <pre 前缀（坑 9 变体），
#    <pre> 被当 <p>，非贪婪 (.*?)</p> 跨界吞掉中间内容 → 加 \b 词边界断掉 <p|<pre
Y.BLOCK_RE = re.compile(r"<(h[1-6]|pre|p|li|dt|dd|table|blockquote)\b([^>]*)>(.*?)</\1>", re.S)


def strip_first_h1(md):
    lines = md.split("\n")
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        if ln.startswith("# "):
            rest = lines[i+1:]
            while rest and not rest[0].strip():
                rest.pop(0)
            return "\n".join(rest)
        break
    return md


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(OUT + "/*.md"):
        os.remove(f)
    rep = []
    for src, name in PAGES:
        md = Y.rst_to_md(os.path.join(RST, src + ".rst.txt"), RST)
        md = strip_first_h1(md)
        open(os.path.join(OUT, name + ".md"), "w", encoding="utf-8").write(md)
        rep.append("%-28s %6dB  code=%d" % (name + ".md", len(md.encode()), md.count("```")//2))
    print("\n".join(rep))


if __name__ == "__main__":
    main()
