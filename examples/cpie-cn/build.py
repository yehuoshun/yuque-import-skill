#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""liancheng/cpie-cn《Erlang并发编程》→ 语雀 clean 树（Sphinx/reST 书稿）。

复用 scripts/yuque_rst_convert.py，并打 examples/sphinx-rst-site 的 3 个 monkey-patch
（BLOCK_RE 的 `<p` 匹 `<pre` 前缀 / 提示框换行与嵌套 / 行内字面量 span）。

本仓特有：
  * rst 大量用 conf.py `rst_prolog` 的替换（|eps| |->| |-->| |=>| |>=| |double-accute-*|
    |latex| |date|）——docutils 不读 conf.py → 先把 prolog 注入每份 rst（整树复制到 work/，
    保 literalinclude 相对路径）。
  * 图在 `_static/images/`，引用写的是 `_static/...`（无前导斜杠）→ 按目录深度补 `../`。
  * 附录B 上游为空壳（146B 只有标题）→ 不建节点。

用法：python3 build.py --src <repo> --out <clean树>
"""
import argparse
import html as h
import importlib.util
import os
import re
import shutil
import sys

SKILL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(SKILL, "scripts"))
_spec = importlib.util.spec_from_file_location("yrc", os.path.join(SKILL, "scripts", "yuque_rst_convert.py"))
Y = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(Y)

# ================== monkey-patch（同 examples/sphinx-rst-site） ==================
_lang_of = lambda attrs: next((c for c in re.search(r'class="([^"]*)"', attrs or "").group(1).split()
                               if c not in ("code", "literal-block", "highlight", "doctest-block", "raw")), "") \
    if re.search(r'class="([^"]*)"', attrs or "") else ""

_orig_inline = Y.inline
_SPAN_OPEN = re.compile(r'<span class="docutils literal[^"]*">')
_SPAN_TAG = re.compile(r'</?span\b[^>]*>')


def _wrap_literals(t):
    out, pos = [], 0
    while True:
        m = _SPAN_OPEN.search(t, pos)
        if not m:
            out.append(t[pos:])
            break
        out.append(t[pos:m.start()])
        depth, i = 1, m.end()
        while i < len(t) and depth > 0:
            nm = _SPAN_TAG.search(t, i)
            if not nm:
                break
            depth += -1 if t[nm.start():nm.start() + 2] == "</" else 1
            i = nm.end()
        inner = re.sub(r'</?span\b[^>]*>', "", t[m.end():i]).strip()
        out.append("`" + inner + "`")
        pos = i
    return "".join(out)


Y.inline = lambda t: _orig_inline(_wrap_literals(t))


def _apply_pfx(blocks, first, cont):
    return [(k, "\n".join(first + l if l else l for l in t.split("\n")))
            if i == 0 else (k, "\n".join(cont + l if l else l for l in t.split("\n")))
            for i, (k, t) in enumerate(blocks)]


def html_to_md_fixed(body):
    bq = {}

    def restore(text):
        return re.sub(r"\x00BQ\d+\x00", lambda m: _wrap_literals(bq.get(m.group(0), m.group(0))), text)

    def add_line(lines, text):
        for ln in text.split("\n"):
            lines.append(ln if ln.startswith(">") else "> " + ln)

    def make_bq(inner):
        inner = convert_admonitions(inner)
        title = ""
        tm = re.search(r'<p[^>]*class="[^"]*admonition-title[^"]*"[^>]*>(.*?)</p>', inner, re.S)
        if tm:
            title = Y.inline(tm.group(1))
            inner = inner[:tm.start()] + inner[tm.end():]
        lines = [("> **%s**：" % title) if title else ">"]
        pos2 = 0
        for mm2 in re.finditer(r"<(p|ul|ol|pre|blockquote)\b([^>]*)>(.*?)</\1>", inner, re.S):
            if mm2.start() > pos2:
                t = restore(Y.inline(inner[pos2:mm2.start()]))
                if t.strip():
                    add_line(lines, t)
            pos2 = mm2.end()
            tag, bi = mm2.group(1), mm2.group(3)
            if tag == "pre":
                code = h.unescape(re.sub(r"<[^>]+>", "", bi)).strip("\n")
                lines.append("> ```")
                lines.extend("> " + c for c in code.split("\n"))
                lines.append("> ```")
            elif tag in ("ul", "ol"):
                for li in re.findall(r"<li[^>]*>(.*?)</li>", bi, re.S):
                    t = restore(Y.inline(li))
                    if t:
                        add_line(lines, "- " + t)
            else:
                t = restore(Y.inline(bi))
                if t:
                    add_line(lines, t)
        if pos2 < len(inner):
            t = restore(Y.inline(inner[pos2:]))
            if t.strip():
                add_line(lines, t)
        if len(lines) == 1:
            t = restore(Y.inline(re.sub(r"<[^>]+>", " ", inner)))
            if t:
                add_line(lines, t)
        key = "\x00BQ%d\x00" % len(bq)
        bq[key] = "\n".join(lines)
        return "\n\n" + key + "\n\n"

    def convert_admonitions(src):
        out, pos = [], 0
        pat = re.compile(r'<(div|aside) class="admonition[^"]*">')
        while True:
            m = pat.search(src, pos)
            if not m:
                out.append(src[pos:])
                break
            out.append(src[pos:m.start()])
            tag = m.group(1)
            depth, end = 0, None
            for mm in re.finditer(r'</?' + tag + r'\b[^>]*>', src[m.start():]):
                depth += -1 if src[m.start() + mm.start() + 1] == "/" else 1
                if depth == 0:
                    end = m.start() + mm.end()
                    break
            if end is None:
                out.append(src[m.start():])
                break
            out.append(make_bq(src[m.end():end - len(tag) - 3]))
            pos = end
        return "".join(out)

    body = re.sub(r'<(aside|dl)[^>]*class="(?:footnote|citation)[^"]*"[^>]*>.*?</\1>', "", body, flags=re.S)
    body = convert_admonitions(body)

    def restore2(text):
        return re.sub(r"\x00BQ\d+\x00", lambda m: _wrap_literals(bq.get(m.group(0), m.group(0))), text)

    def render(frag):
        res = []

        def lp(kind, text):
            if text and text.strip():
                res.append((kind, text))

        pos = 0
        for mm in Y.BLOCK_RE.finditer(frag):
            if mm.start() > pos:
                lp("p", restore2(Y.inline(frag[pos:mm.start()])))
            pos = mm.end()
            tag, attrs, inner = mm.group(1), mm.group(2), mm.group(3)
            if tag.startswith("h"):
                lp("h", "#" * int(tag[1]) + " " + restore2(Y.inline(inner)))
            elif tag == "pre":
                code = h.unescape(re.sub(r"<[^>]+>", "", inner)).strip("\n")
                lp("pre", "```" + _lang_of(attrs) + "\n" + code + "\n```")
            elif tag == "table":
                lp("table", Y.table_md(inner))
            elif tag == "blockquote":
                for k, t in _apply_pfx(render(inner), "> ", "> "):
                    lp(k, t)
            elif tag == "p":
                lp("p", restore2(Y.inline(inner)))
            elif tag == "li":
                res.extend(_apply_pfx(render(inner), "- ", "  "))
            elif tag == "dt":
                lp("dt", "**" + restore2(Y.inline(inner)) + "**")
            elif tag == "dd":
                res.extend(_apply_pfx(render(inner), "  ", "  "))
        if pos < len(frag):
            lp("p", restore2(Y.inline(frag[pos:])))
        return res

    out = render(body)
    KEEP = {("li", "li"), ("table", "table"), ("bq", "bq"), ("dt", "dt"), ("dt", "dd"), ("dd", "dd"), ("dd", "dt")}
    chunks = []
    for i, (kind, text) in enumerate(out):
        if i:
            chunks.append("\n" if (out[i - 1][0], kind) in KEEP else "\n\n")
        chunks.append(text)
    return re.sub(r"\n{3,}", "\n\n", "".join(chunks)).strip() + "\n"


Y.html_to_md = html_to_md_fixed
Y.BLOCK_RE = re.compile(r"<(h[1-6]|pre|p|li|dt|dd|table|blockquote)\b([^>]*)>(.*?)</\1>", re.S)
# =================================================================================

PROLOG = """\
.. |date| date:: %Y-%m-%d
.. |double-accute-o| unicode:: U+0151
    :trim:
.. |double-accute-A| unicode:: U+00c4
    :trim:
.. |double-accute-a| unicode:: U+00e4
    :trim:
.. |eps| unicode:: U+03b5
.. |->| unicode:: U+2192
.. |-->| unicode:: U+2192
.. |=>| unicode:: U+21d2
.. |>=| unicode:: U+2265
.. |latex| replace:: LaTeX

"""

TREE = [
    ("index.rst",               "00-前言.md"),
    ("cpie-cn-project.rst",     "01-翻译计划.md"),
    ("preface.rst",             "02-序言.md"),
    ("acknowledgements.rst",    "03-致谢.md"),
    ("introduction.rst",        "04-简介.md"),
]
CHAPTERS = [
    "part-i_chapter-1.rst", "part-i_chapter-2.rst", "part-i_chapter-3.rst",
    "part-i_chapter-4.rst", "part-i_chapter-5.rst", "part-i_chapter-6.rst",
    "part-i_chapter-7.rst", "part-i_chapter-8.rst", "part-i_chapter-9.rst",
    "part-i_appendix-a.rst",
    # part-i_appendix-b.rst 空壳，跳过
    "part-i_appendix-c.rst", "part-i_appendix-d.rst", "part-i_appendix-e.rst",
]


def first_h1(md):
    m = re.search(r"^# (.+)$", md, re.M)
    return m.group(1).strip() if m else ""


def norm_title(t):
    return re.sub(r"\s+", " ", t).strip().replace("/", "／")


def fix_images(md, depth):
    pref = "../" * depth

    def r(m):
        rel = m.group(1)          # _static/ 之后的部分
        return "![%s](%s_static/%s)" % (os.path.basename(rel), pref, rel)

    return re.sub(r'!\[[^\]]*\]\((?:\.\./)*_static/([^)]+)\)', r, md)


def prepare_work(src, work):
    if os.path.exists(work):
        shutil.rmtree(work)
    shutil.copytree(src, work, ignore=shutil.ignore_patterns(".git"))
    for f in os.listdir(work):
        if f.endswith(".rst"):
            p = os.path.join(work, f)
            body = open(p, encoding="utf-8").read()   # 先读后写（w 会先截断）
            open(p, "w", encoding="utf-8").write(PROLOG + body)


def convert(work, out, src_rel, dst_rel, strip_h1=True):
    md = Y.rst_to_md(os.path.join(work, src_rel), work)
    if strip_h1:
        md = re.sub(r"^# .+\n+", "", md, count=1, flags=re.M)
    md = fix_images(md, dst_rel.count("/"))
    dst = os.path.join(out, dst_rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "w", encoding="utf-8").write(md)
    return len(md)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", default=None)
    args = ap.parse_args()
    src, out = os.path.abspath(args.src), os.path.abspath(args.out)
    work = os.path.abspath(args.work or (out + "-work"))
    prepare_work(src, work)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)

    for src_rel, dst_rel in TREE:
        n = convert(work, out, src_rel, dst_rel, strip_h1=(dst_rel != "00-前言.md"))
        if dst_rel == "00-前言.md":
            # 首 H1 = 书名，已由 00-说明 承载 → 只剥标题行
            pass
        print("  %-50s %6d B" % (dst_rel, n))
    for i, src_rel in enumerate(CHAPTERS, 1):
        md0 = Y.rst_to_md(os.path.join(work, src_rel), work)
        title = norm_title(first_h1(md0)) or os.path.splitext(src_rel)[0]
        dst_rel = "05-第I部分 编程/%02d-%s.md" % (i, title)
        n = convert(work, out, src_rel, dst_rel)
        print("  %-50s %6d B" % (dst_rel, n))

    refs = set()
    for root, _, files in os.walk(out):
        for f in files:
            if f.endswith(".md"):
                for m in re.finditer(r"\]\((?:\.\./)*_static/([^)]+)\)", open(os.path.join(root, f), encoding="utf-8").read()):
                    refs.add(m.group(1))
    for rel in sorted(refs):
        s = os.path.join(work, "_static", rel)
        if not os.path.exists(s):
            print("  !! 缺图", rel)
            continue
        d = os.path.join(out, "_static", rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)
    print("图引用 %d 张" % len(refs))


if __name__ == "__main__":
    main()
