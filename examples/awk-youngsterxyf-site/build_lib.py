#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awk.readthedocs.io（Sphinx，残缺译本 youngsterxyf/pylemon）→ 语雀导入树

为什么要自写转换器（不复用 yuque_rst_convert.py）：
  1. docutils 中间层把行内字面量 `` `emp.data` `` 吃掉（<tt> 无属性 → 正则不匹配 →
     反引号错位，正文丢字），本文档 133 处行内字面量，不能忍
  2. ``| `` 行块（终端会话、模式摘要）被压成一行，行结构全丢
  3. 段落尾 ``：::`` 残留一个冒号

构造全集（实测）：标题（over/underline）、段落、行内字面量、**粗体**、:math: 角色、
`::` 字面块（4 空格 / TAB 缩进）、`| ` 行块、简单表（`==== ====` 列分隔）、toctree 指令。

用法：
  python3 build_lib.py --src <rst 目录> --out <导入树目录>
"""
import argparse
import os
import re
import shutil

UNDERLINE = "=-~^\"'`#*+"

DOC = "␟"  # 段内占位（行块硬换行）


def strip_inline_roles(t):
    return re.sub(r":(?:math|ref|doc|term|code|literal|file|command):`([^`]*)`", r"\1", t)


def inline(t):
    t = strip_inline_roles(t)
    # RST 外链：`文字 <url>`_ / `文字 <url>`__ → [文字](url)
    t = re.sub(r"`([^`<]+?)\s*<([^`>]+)>`__?", lambda m: "[%s](%s)" % (m.group(1).strip(), m.group(2).strip()), t)
    # `` ``x`` `` 双反引号先归一成单反引号，再当行内代码
    t = re.sub(r"``([^`]+)``", lambda m: "`" + m.group(1).strip() + "`", t)
    t = re.sub(r"`([^`]+)`", lambda m: "`" + m.group(1).strip() + "`", t)
    # RST 转义：\* \` \| 等 → 去掉反斜杠
    t = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|])", r"\1", t)
    return t.strip()


def col_spans(sep):
    return [(m.start(), m.end()) for m in re.finditer(r"=+", sep)]


def parse(path):
    """返回 [('h', level, text) | ('p', text) | ('pre', code) | ('lb', lines) | ('table', rows)]"""
    raw = open(path, encoding="utf-8").read().replace("\ufeff", "").replace("\r\n", "\n")
    lines = raw.split("\n")
    blocks, i, n = [], 0, len(lines)

    def is_underline(s):
        s = s.rstrip()
        return len(s) >= 3 and set(s) <= set(UNDERLINE) and len(set(s)) == 1

    while i < n:
        ln = lines[i]
        s = ln.strip()

        # 空行
        if not s:
            i += 1
            continue

        # 指令（toctree 等）：整条 + 其缩进选项/子块丢弃
        if s.startswith(".."):
            i += 1
            while i < n and (not lines[i].strip() or lines[i][:1] in (" ", "\t")):
                i += 1
            continue

        # 孤立的下划线行（如 ch2 结尾残留的 `======`）→ 丢
        if is_underline(ln):
            i += 1
            continue

        # 标题：文本 + underline（本站无 overline 标题）
        if i + 1 < n and is_underline(lines[i + 1]):
            blocks.append(("h", 2, s))
            i += 2
            continue

        # 简单表：`====  ====` 列分隔行
        if re.fullmatch(r"=+( +=+)+", s):
            spans = col_spans(ln)
            j, rows = i + 1, []
            while j < n and not re.fullmatch(r"=+( +=+)*", lines[j].strip()):
                if lines[j].strip():
                    row = []
                    for (a, b) in spans:
                        row.append(lines[j][a:b].strip() if a < len(lines[j]) else "")
                    row += [""] * (len(spans) - len(row))
                    rows.append(row)
                j += 1
            blocks.append(("table", rows))
            i = j + 1
            continue

        # 行块：`| 文本`
        if re.match(r"^\|\s?|^\|$", ln):
            buf = []
            while i < n and re.match(r"^\|\s?|^\|$", lines[i]) and lines[i].strip():
                buf.append(lines[i][1:].strip())
                i += 1
            blocks.append(("lb", buf))
            continue

        # 段落（可能以 :: 引出字面块）
        buf = []
        while i < n:
            cur = lines[i]
            if not cur.strip():
                break
            if re.fullmatch(r"=+( +=+)+", cur.strip()) or re.match(r"^\|\s?|^\|$", cur) or cur.strip().startswith(".."):
                break
            if i + 1 < n and is_underline(lines[i + 1]) and cur.strip():
                break
            buf.append(cur.strip())
            i += 1
        text = " ".join(buf).strip()
        if not text:
            continue
        literal = False
        if text.endswith("::"):
            literal = True
            text = text[:-2].rstrip()
            # RST 规则：`text::` → `text:`；`text ::` → `text`；已带全角/半角冒号则不再补
            if text and not text.endswith(("：", ":")):
                text += ":"
        if text:
            blocks.append(("p", text))
        # 字面块：空行后首个缩进行开始，直到去缩进
        if literal:
            j = i
            while j < n and not lines[j].strip():
                j += 1
            if j < n and lines[j][:1] in (" ", "\t"):
                code, indent = [], None
                while j < n:
                    cl = lines[j]
                    if not cl.strip():
                        code.append("")
                        j += 1
                        continue
                    cur_ind = len(cl) - len(cl.lstrip())
                    if indent is None:
                        indent = cur_ind
                    if cur_ind < indent:
                        break
                    code.append(cl[indent:].rstrip())
                    j += 1
                while code and not code[-1]:
                    code.pop()
                blocks.append(("pre", "\n".join(code)))
                i = j
    return blocks


def render(blocks):
    out = []
    for kind, val in blocks:
        if kind == "h":
            continue
        elif kind == "p":
            out.append(inline(val))
        elif kind == "pre":
            out.append("```\n" + val + "\n```")
        elif kind == "lb":
            out.append("  \n".join(inline(x) for x in val))
        elif kind == "table":
            if not val:
                continue
            w = len(val[0])
            sep = "|" + "|".join("---" for _ in range(w)) + "|"
            head = "| " + " | ".join("" for _ in range(w)) + " |"  # 无表头的简单表 → 空表头（同 awk LaTeX 口径）
            rows = ["| " + " | ".join(inline(c) for c in r) + " |" for r in val]
            out.append("\n".join([head, sep] + rows))
    return "\n\n".join(out).strip() + "\n"


def split_sections(path):
    """返回 (chapter_title, intro_blocks, [(sec_title, blocks)])"""
    blocks = parse(path)
    title, intro, secs = None, [], []
    cur = None
    for b in blocks:
        if b[0] == "h":
            if title is None and (cur is None):
                title = b[2]
                continue
            cur = (b[2], [])
            secs.append(cur)
            continue
        (cur[1] if cur else intro).append(b)
    return title, intro, secs


def safe(name):
    return name.replace("/", "／")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    if os.path.isdir(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out)

    # 00-前言（index.rst：书名 + 作者 + 译者）
    t_idx, intro_idx, _ = split_sections(os.path.join(a.src, "index.rst"))
    front = render(intro_idx)
    y = len(t_idx) * "="
    open(os.path.join(a.out, "00-前言.md"), "w", encoding="utf-8").write(
        "# %s\n\n%s\n\n---\n\n"
        "> **译本状态**：本站仅覆盖 **第 1 章** 与 **第 2 章 2.1 节**，此后章节未译"
        "（readthedocs 站最后更新 2017-10-26）。\n"
        "> 完整译本另见语雀库 **awk-787d83c（AWK 程序设计语言，LaTeX 源全 8 章 + 2 附录）**。\n"
        % (t_idx, front))

    plan = [("chapter-one", "一. AWK入门指南"), ("chapter-two", "二. AWK语言详解")]
    for fn, dirname in plan:
        title, intro, secs = split_sections(os.path.join(a.src, fn + ".rst"))
        d = os.path.join(a.out, safe(dirname))
        os.makedirs(d)
        if intro:
            open(os.path.join(d, "00-本章导读.md"), "w", encoding="utf-8").write(
                "# %s\n\n%s" % (title, render(intro)))
        with open(os.path.join(d, "00-本章导读.md"), "a", encoding="utf-8") as f:
            if not intro:
                f.write("# %s\n" % title)
            if fn == "chapter-two":
                f.write("\n> ⚠️ 本站译本在本章 **2.1 模式** 之后中断，2.2 及后续章节无内容。\n")
        for st, blocks in secs:
            open(os.path.join(d, safe(st) + ".md"), "w", encoding="utf-8").write(
                "# %s\n\n%s" % (st, render(blocks)))
        print("%-12s -> %s/  %d 篇" % (fn, dirname, len(secs) + 1))


if __name__ == "__main__":
    main()