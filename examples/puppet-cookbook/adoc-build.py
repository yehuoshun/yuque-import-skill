#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Puppet 2.7 Cookbook 中文版（sinosmond/puppet-27-cookbook-CN @ 5415c55）→ 语雀干净树。

源形状：**AsciiDoc 书稿**（不是 GitBook markdown）——book.txt 主控 + include 拼装：
  book.txt            封面/作者/版本 + [IMPORTANT] 版权声明 +「中文翻译版」节
  00-translator_preamble / 01-colophon / 02-author / 03-preface   前置 4 篇
  ch01..ch09-*.txt    章首页（引言 + include 清单）
  recipes/chNNsecMM-*.txt   95 个处方（正文主体）
站点副本：https://wizardforcel.gitbooks.io/puppet-27-cookbook/content/（老 gitbooks.io 静态站仍在线，
本文用它做**逐页文本校对**的 oracle —— 见 verify.py）。

AsciiDoc → Markdown 转换规则（本脚本实现，踩坑见 README.md）：
  节标题  == / === / ====      → # / ## / ###（降一级；落地页的章标题 = #）
  属性    {Recipe101} {Gettingready} … → entries.txt 里的中文（**只替换已知属性**，
          代码块里 {name}/{md5} 这类未定义属性必须原样保留）
  清单块  [source,puppet] + ---- / [source,ruby] + ----      → ```puppet / ```ruby
  字面块  ...... / ..................（4 个以上点号）          → ```（无语言）
  警告块  [NOTE]/[TIP]/[IMPORTANT] + ====…====               → > **注**/… 引用块
  引用块  [quote, Author, ] + 一段                          → > 引文 / > —— Author
  侧栏    ****…****                                          → > 引用块
  开放块  --…--                                              → 容器（只剥壳）
  块标题  .译者注                                            → 并入警告块标签
  锚点    [[ch01sec01]] / <<ch01sec01,{Recipe101}>>          → 删除 / 取文字
  行内    +x+ ++x++ → `x`；*x* → **x**；http://u[文字] → [文字](u)；http://u[] → <u>
  列表    - / * / ** 嵌套；1. / a. 子项 → 缩进 3 空格的嵌套有序列表
  续项    +（单独一行）→ 后一个块缩进到列表项内容列（代码块也能进列表项）

命名：NN / NN.MM 点分编号，落地页 NN-标题.md 排子节点前（与站点点号一致）。
"""
import os
import re
import shutil
import sys

SRC = "/home/admin/.openclaw/workspace/tmp/puppet27-src"
OUT = "/home/admin/.openclaw/workspace/tmp/puppet27-cookbook-cn-clean"
IMG_DIR = "_imgs"

BAD = re.compile(r'[/\\:*?"<>|\r\n]')

# ---------------------------------------------------------------- 工具

def log(*a):
    print(*a, flush=True)


def sanitize(t):
    t = re.sub(r"\s+", " ", t.replace("\u00a0", " ")).strip()
    return t


def fname(t):
    """标题 → 安全文件名（去掉 / : 等，压缩空格）。"""
    return re.sub(r"\s+", " ", BAD.sub("_", t)).strip()


def load_attrs(path):
    d = {}
    for line in open(path, encoding="utf-8-sig"):
        m = re.match(r"^:([^:]+):\s*(.*)$", line.rstrip("\n"))
        if m:
            d[m.group(1).strip()] = m.group(2).strip()
    return d


ATTRS = {}
QUOTE_RE = re.compile(r"^\[quote(?:,\s*([^,\]]*))?(?:,\s*([^\]]*))?\]$")
SOURCE_RE = re.compile(r"^\[source,\s*([A-Za-z0-9_+-]+)\s*\]$")
ADMON_RE = re.compile(r"^\[(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]$")
ADMON_LABEL = {"NOTE": "注", "TIP": "提示", "IMPORTANT": "重要",
               "WARNING": "警告", "CAUTION": "小心"}
DELIM = {
    "listing": re.compile(r"^-{4,}$"),
    "literal": re.compile(r"^\.{4,}$"),
    "admon": re.compile(r"^={4,}$"),
    "sidebar": re.compile(r"^\*{4,}$"),
    "open": re.compile(r"^--$"),
}
HEAD_RE = re.compile(r"^(=+)\s+(.*)$")
ANCHOR_RE = re.compile(r"^\[\[.*\]\]$")
BUL_RE = re.compile(r"^(\s*)(\*{1,5}|-)\s+(.*)$")
ORD_RE = re.compile(r"^(\s*)(\d+)\.\s+(.*)$")
LET_RE = re.compile(r"^(\s*)([a-z])\.\s+(.*)$")
INC_RE = re.compile(r"^include::([^\[]+)\[.*\]$", re.M)


def inline(text):
    """行内替换（只在正文用，代码块禁用）。"""
    # 未定义属性保留：只替换 ATTRS 里有的
    def attr(m):
        return ATTRS.get(m.group(1), m.group(0))
    text = re.sub(r"\{([A-Za-z][A-Za-z0-9_]*)\}", attr, text)
    # 交叉引用 <<anchor,文字>> → 文字
    text = re.sub(r"<<[^>,]+,\s*([^>]*?)>>", r"\1", text)
    text = re.sub(r"<<[^>]*>>", "", text)
    # 链接：http://url[文字] / http://url[] / https://url[文字]
    def link(m):
        url, label = m.group(1), m.group(2)
        return "<%s>" % url if label.strip() == "" else "[%s](%s)" % (label, url)
    text = re.sub(r"(https?://[^\s\[\]]+)\[([^\]]*)\]", link, text)
    # 行内等宽：++x++ 先于 +x+
    text = re.sub(r"\+\+(.+?)\+\+", r"`\1`", text)
    text = re.sub(r"\+(?!\+|\s)([^+\n]+?)\+", r"`\1`", text)
    # 粗体/斜体
    text = re.sub(r"(?<![*\w])\*\*(?!\s)(.+?)(?<!\s)\*\*(?![*\w])", r"**\1**", text)
    text = re.sub(r"(?<![*\w])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![*\w])", r"**\1**", text)
    text = re.sub(r"(?<![\w_])_(?!\s)([^_\n]+?)(?<!\s)_(?![\w_])", r"*\1*", text)
    return text.rstrip()


# ---------------------------------------------------------------- 转换核心

class Conv:
    def __init__(self):
        self.out = []
        self.state = None          # None / 'fence' / 'admon' / 'sidebar'
        self.attr = None           # 当前块属性行内容
        self.title = None          # 块标题（.xxx）
        self.fence_kind = None
        self.admon_fence = None   # 注释块里嵌的代码块
        self.admon_lang = ""
        self.open_depth = 0      # 处于 -- 开放块内部
        self.cont = ""             # 列表续项缩进

    def push(self, line, indent=True):
        if self.cont and indent and line.strip():
            self.out.append(self.cont + line)
        else:
            self.out.append(line)

    def run(self, text):
        lines = text.split("\n")
        i, n = 0, len(lines)
        while i < n:
            raw = lines[i]
            line = raw.rstrip()

            # ---- 代码块内部：原样输出，只等同类型闭合行 ----
            if self.state == "fence":
                close = DELIM["listing"] if self.fence_kind == "listing" else DELIM["literal"]
                if close.match(line):
                    self.push("```")
                    self.state = None
                    self.fence_kind = None
                    i += 1
                    continue
                self.push(line)
                i += 1
                continue
            if self.state in ("admon", "sidebar"):
                # 注释块内部还能嵌清单/字面块（[source,x] + ----）→ 用 > ``` 包一层
                if self.admon_fence:
                    close = DELIM["listing"] if self.admon_fence == "listing" else DELIM["literal"]
                    if close.match(line):
                        self.push("> ```")
                        self.admon_fence = None
                    elif line.strip():
                        self.push("> " + line)
                    else:
                        self.push(">")
                    i += 1
                    continue
                if SOURCE_RE.match(line.strip()) or ADMON_RE.match(line.strip()):
                    self.admon_lang = (SOURCE_RE.match(line.strip()).group(1)
                                       if SOURCE_RE.match(line.strip()) else "")
                    i += 1
                    continue
                if DELIM["listing"].match(line) or DELIM["literal"].match(line):
                    self.admon_fence = "listing" if DELIM["listing"].match(line) else "literal"
                    self.push("> ```" + (self.admon_lang if self.admon_fence == "listing" else ""))
                    i += 1
                    continue
                if re.match(r"^={4,}$", line) or re.match(r"^\*{4,}$", line):
                    self.state = None
                    self.admon_lang = ""
                    i += 1
                    continue
                if line.strip():
                    self.push("> " + inline(line))
                else:
                    self.push(">")
                i += 1
                continue

            # ---- 空行 ----
            if not line.strip():
                if self.out and self.out[-1] != "":
                    self.out.append("")
                if not self.open_depth:      # 开放块内部的空行不断续项
                    self.cont = ""
                i += 1
                continue

            # ---- 锚点 / include ----
            if ANCHOR_RE.match(line.strip()) or INC_RE.match(line.strip()):
                i += 1
                continue

            # ---- 块属性 ----
            m = SOURCE_RE.match(line.strip()) or ADMON_RE.match(line.strip()) \
                or QUOTE_RE.match(line.strip())
            if m:
                self.attr = line.strip()
                i += 1
                continue

            # ---- 块标题 .xxx（下一行是分隔符/属性才算）----
            if re.match(r"^\.(?!\.)\S", line):
                nxt = lines[i + 1].strip() if i + 1 < n else ""
                if re.match(r"^[-.=*]{4,}$", nxt) or nxt == "--" or SOURCE_RE.match(nxt) \
                        or ADMON_RE.match(nxt) or INC_RE.match(nxt):
                    self.title = line[1:].strip()
                    i += 1
                    continue

            # ---- 块标题（非警告块）落到正文里，不能丢 ----
            def flush_title():
                if self.title:
                    self.push("**" + inline(self.title) + "**")
                    self.title = None

            # ---- 分隔符 ----
            if DELIM["listing"].match(line):
                flush_title()
                lang = ""
                if self.attr:
                    sm = SOURCE_RE.match(self.attr)
                    if sm:
                        lang = sm.group(1)
                self.fence_kind = "listing"
                self.push("```" + lang)
                self.state = "fence"
                self.attr = None
                i += 1
                continue
            if DELIM["literal"].match(line):
                flush_title()
                self.fence_kind = "literal"
                self.push("```")
                self.state = "fence"
                self.attr = None
                i += 1
                continue
            if DELIM["admon"].match(line):
                if self.attr and ADMON_RE.match(self.attr):
                    lab = ADMON_LABEL[ADMON_RE.match(self.attr).group(1)]
                    if self.title:
                        lab += "（%s）" % self.title
                    self.push("> **%s**" % lab)
                    self.state = "admon"
                elif self.attr and QUOTE_RE.match(self.attr):
                    qm = QUOTE_RE.match(self.attr)
                    self.state = "admon"
                    self.quote_meta = (qm.group(1) or "").strip()
                else:
                    self.state = "admon"
                self.attr = None
                self.title = None
                i += 1
                continue
            if DELIM["sidebar"].match(line):
                self.state = "sidebar"
                self.attr = None
                self.title = None
                i += 1
                continue
            if DELIM["open"].match(line):
                flush_title()
                self.open_depth = 1 - self.open_depth
                self.attr = None
                self.title = None
                i += 1
                continue

            # ---- 引用块（[quote, Author, ] + 一段文字）----
            if self.attr and QUOTE_RE.match(self.attr):
                flush_title()
                qm = QUOTE_RE.match(self.attr)
                author = (qm.group(1) or "").strip()
                citation = re.sub(r"^[\"'‘“]|[\"'’”],?$", "", (qm.group(2) or "").strip())
                citation = citation.strip().rstrip(",").strip().strip("\"'")
                quote = []
                while i < n and lines[i].strip() and not INC_RE.match(lines[i].strip()):
                    quote.append(lines[i].strip())
                    i += 1
                self.attr = None
                self.title = None
                q = inline(" ".join(quote))
                if citation:                      # 站点渲染：[quote, 说话人, 出处] → 正文 "出处" — 说话人
                    q += ' "%s"' % citation
                self.push("> " + q)
                if author:
                    self.push(">")
                    self.push("> —— " + author)
                continue

            # ---- 列表续项 + ----
            if line.strip() == "+":
                i += 1
                continue
            flush_title()

            # ---- 标题 ----
            hm = HEAD_RE.match(line)
            if hm:
                lvl = max(1, len(hm.group(1)) - 1)
                self.cont = ""
                self.push("#" * lvl + " " + inline(hm.group(2)))
                self.attr = None
                self.title = None
                i += 1
                continue

            # ---- 列表 ----
            bm = BUL_RE.match(line)
            om = ORD_RE.match(line) if not bm else None
            lm = LET_RE.match(line) if not (bm or om) else None
            if bm or om or lm:
                self.cont = ""            # 列表项自身不再吃续项缩进
                if bm:
                    lead, mark, body = bm.groups()
                    depth = len(mark) if mark.startswith("*") else 1 + len(lead) // 2
                    indent = "  " * (depth - 1)
                    self.push(indent + "- " + inline(body))
                    self.cont = indent + "  "
                elif om:
                    lead, num, body = om.groups()
                    indent = "   " * (len(lead) // 3)
                    self.push(indent + num + ". " + inline(body))
                    self.cont = indent + "   "
                else:
                    lead, letter, body = lm.groups()
                    indent = "   " * (len(lead) // 3)
                    self.push(indent + "1. " + inline(body))
                    self.cont = indent + "   "
                i += 1
                continue

            # ---- 正文段落 ----
            self.push(inline(line))
            i += 1

        return "\n".join(self.out)


def convert(text):
    c = Conv()
    body = c.run(text)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body + "\n"


def write_md(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)
    log("  +", os.path.relpath(path, OUT))


# ---------------------------------------------------------------- 建树

def replace_images(text, src_dir, out_md_dir):
    """image::image/x.png[] → ![x](相对路径)，顺带把图收进 _imgs/。"""
    def sub(m):
        src = m.group(1)
        key = os.path.basename(src)
        dst = os.path.join(OUT, IMG_DIR, key)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        p = os.path.join(src_dir, src)
        if os.path.exists(p) and not os.path.exists(dst):
            shutil.copyfile(p, dst)
        return "![%s](%s)" % (key, os.path.relpath(dst, out_md_dir))
    return re.sub(r"image::([^\[]+)\[[^\]]*\]", sub, text)


def split_sections(text, level):
    """按指定级别的标题切分：返回 (intro, [(title, body), ...])。"""
    pat = re.compile(r"^%s\s+(.*)$" % ("=" * level), re.M)
    marks = list(pat.finditer(text))
    if not marks:
        return text, []
    intro = text[:marks[0].start()]
    out = []
    for k, m in enumerate(marks):
        end = marks[k + 1].start() if k + 1 < len(marks) else len(text)
        out.append((m.group(1).strip(), text[m.start():end]))
    return intro, out


def build():
    global ATTRS
    ATTRS = load_attrs(os.path.join(SRC, "entries.txt"))
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    book = open(os.path.join(SRC, "book.txt"), encoding="utf-8-sig").read()

    # ---- 00 书名页（书头 + [IMPORTANT] 版权声明）----
    head = book.split("== 中文翻译版")[0]
    imp = re.search(r"\[IMPORTANT\]\n=+\n(.*?)\n=+\n", head, re.S)
    lines = [l.rstrip() for l in head.split("\n")]
    author = next((l.split(":", 2)[2].strip() for l in lines
                   if l.startswith(":Author:")), "")
    email = next((l.split(":", 2)[2].strip() for l in lines
                  if l.startswith(":Email:")), "")
    body = "# Puppet 2.7 Cookbook 中文版\n\n**%s** <%s>\n\nversion 1.0, October, 2011\n" % (author, email)
    if imp:
        body += "\n> **重要**\n>\n"
        for l in imp.group(1).strip().split("\n"):
            l = re.sub(r"^\s*[*\-\s]+", "", l.strip()).strip()
            l = re.sub(r"[*\s]+$", "", l)
            if not l:
                continue
            body += "> " + inline(l) + "\n"
    write_md(os.path.join(OUT, "00-书名页.md"), body)

    # ---- 01 中文翻译版（book.txt 里那一节）----
    sec = book.split("== 中文翻译版", 1)[1]
    write_md(os.path.join(OUT, "01-中文翻译版.md"),
             convert("# 中文翻译版" + sec.replace("include::00-translator_preamble.txt[]", "")))

    # ---- 02 译者序 / 05 前言：章首页 + 子节 ----
    front = [
        ("00-translator_preamble.txt", "02", True),
        ("01-colophon.txt", "03", False),
        ("02-author.txt", "04", False),
        ("03-preface.txt", "05", True),
    ]
    for src, num, has_subs in front:
        text = open(os.path.join(SRC, src), encoding="utf-8-sig").read()
        if not has_subs:
            title = re.search(r"^==\s+(.*)$", text, re.M).group(1).strip()
            body = convert(re.sub(r"^==\s+.*$", "# " + title, text, count=1, flags=re.M))
            write_md(os.path.join(OUT, "%s-%s.md" % (num, fname(title))), body)
            continue
        title = re.search(r"^==\s+(.*)$", text, re.M).group(1).strip()
        intro, subs = split_sections(text, 3)
        # 章首页
        intro_md = re.sub(r"^==\s+.*$", "# " + title, intro, count=1, flags=re.M)
        d = os.path.join(OUT, "%s-%s" % (num, fname(title)))
        write_md(os.path.join(d, "%s-%s.md" % (num, fname(title))), convert(intro_md))
        for k, (st, sb) in enumerate(subs, 1):
            sb = re.sub(r"^===\s+.*$", "## %s" % st, sb, count=1, flags=re.M)
            write_md(os.path.join(d, "%s.%02d-%s.md" % (num, k, fname(st))), convert(sb))

    # ---- 06..14 章节 ----
    chapters = sorted(f for f in os.listdir(SRC)
                      if re.match(r"^ch0\d-.*\.txt$", f))
    assert len(chapters) == 9, chapters
    for idx, chf in enumerate(chapters, start=6):
        text = open(os.path.join(SRC, chf), encoding="utf-8-sig").read()
        title = re.search(r"^==\s+(.*)$", text, re.M).group(1).strip()
        if not title.startswith(("监控",)) and idx == 7:
            pass
        intro = text.split("include::")[0]
        intro_md = re.sub(r"^==\s+.*$", "# " + title, intro, count=1, flags=re.M)
        d = os.path.join(OUT, "%02d-%s" % (idx, fname(title)))
        write_md(os.path.join(d, "%02d-%s.md" % (idx, fname(title))), convert(intro_md))
        recipes = INC_RE.findall(text)
        for k, rel in enumerate(recipes, 1):
            rtext = open(os.path.join(SRC, rel), encoding="utf-8-sig").read()
            rt = re.search(r"^===\s+(.*)$", rtext, re.M).group(1).strip()
            rt = inline(rt)
            rtext = re.sub(r"^===\s+.*$", "## " + rt, rtext, count=1, flags=re.M)
            body = replace_images(convert(rtext), SRC, d)
            write_md(os.path.join(d, "%02d.%02d-%s.md" % (idx, k, fname(rt))), body)
        assert len(recipes) == len([p for p in os.listdir(os.path.join(SRC, "recipes"))
                                    if p.startswith("ch%02dsec" % (idx - 5))]), (idx, len(recipes))

    # 统计
    docs = sum(1 for r, _, fs in os.walk(OUT) for f in fs if f.endswith(".md"))
    dirs = sum(1 for r, ds, _ in os.walk(OUT) for d in ds) + 0
    imgs = len(os.listdir(os.path.join(OUT, IMG_DIR))) if os.path.exists(os.path.join(OUT, IMG_DIR)) else 0
    log("\n[build] 文档 %d / 目录 %d / 节点 %d / 图 %d → %s" % (docs, dirs, docs + dirs, imgs, OUT))


if __name__ == "__main__":
    build()