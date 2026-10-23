#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docs.huihoo.com GNU make 指南（GB2312 单页长文）→ 按章拆篇 markdown 树。

站点：http://docs.huihoo.com/gnu/linux/gmake.html
- 编码 GB2312，单页全文章节用纯文本编号（0) 介绍 / 1.2 何时分解你的项目 / 3 总结）
- 代码块用文本标记「=== makefile 开始 === / === makefile 结束 ===」
- 无图、无分页、无 HTML 标题（h1-h6 全无）
"""
import re
import os
import sys
import urllib.request

URL = "http://docs.huihoo.com/gnu/linux/gmake.html"
LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gmake.html")  # 已下载的本地副本（站点 522 间歇）
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()


def main():
    if os.path.exists(LOCAL):
        raw = open(LOCAL, "rb").read()
    else:
        raw = fetch(URL)
        with open(LOCAL, "wb") as f:
            f.write(raw)
    html = raw.decode("gb2312", "replace")
    os.makedirs(OUT, exist_ok=True)

    # 剥 <script> 广告块
    html = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    # 保护正文伪标签（makefile 语法文本里的 <target>/<dependency>/<command>，非真实 HTML 标签）
    html = re.sub(r"<(/?)??(target|dependency|command|tab)([^a-zA-Z])?>", r"&lt;\1\2\3&gt;", html)
    # 行级清理：剥标签、解实体、去空白
    lines = []
    for l in html.split("\n"):
        t = re.sub(r"<[^>]+>", "", l)
        t = t.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            lines.append(t)
    # 找代码块区间
    code_ranges = []
    start = None
    for i, t in enumerate(lines):
        if re.match(r"^===\s*\S+\s*开始\s*===$", t):
            start = i
        elif start is not None and re.match(r"^===\s*\S+\s*结束\s*===$", t):
            code_ranges.append((start, i))
            start = None
    print("代码块:", len(code_ranges))

    # 按章拆篇：0) 介绍 / 1) 多文件项目 / 2) GNU Make 工具 / 3 总结
    # 标题行匹配：N. 节标题 或 N) 章标题 或 N 总结（行尾无句号）
    heads = []  # (lineno, title, level)
    for i, t in enumerate(lines):
        m = re.match(r"^(\d+)\.(\d+)\s*(.+)$", t)   # 节 1.2（原站 1.1 无空格：1.1为什么使用它们?）
        if m and not m.group(3).strip().endswith("节）。"):  # 排除正文引用「参考下面的 2.4 节）」
            heads.append((i, "%s.%s %s" % (m.group(1), m.group(2), m.group(3).strip()), 2))
            continue
        m = re.match(r"^(\d+)\)\s+(.+)$", t)          # 章 0) 介绍
        if m:
            heads.append((i, "%s. %s" % (m.group(1), m.group(2).strip()), 1))
            continue
        m = re.match(r"^(\d+)\s+(.+)$", t)            # 章 3 总结（无括号）
        if m and not m.group(2).endswith("。") and not m.group(2).endswith(".") and len(m.group(2)) < 30:
            heads.append((i, "%s. %s" % (m.group(1), m.group(2).strip()), 1))
    # 去重：同编号的标题只留第一个（正文引用「2.4 节）」会误中）
    seen = set()
    heads2 = []
    for h in heads:
        key = h[1]
        if key in seen:
            continue
        seen.add(key)
        heads2.append(h)
    heads = heads2
    print("标题:", len(heads))
    for h in heads:
        print("  L%-4d %s" % (h[0], h[1]))

    # 提取页眉（第一个标题前的所有行）→ 根级 00-译者说明.md（作者/版权/来源信息）
    first_head = min(h[0] for h in heads) if heads else len(lines)
    header_lines = [t for t in lines[:first_head] if t and not re.match(r"^~+$", t)]
    if header_lines:
        hmd = "本文译自 George Foot（gfoot）的 《GNU Make 指南》（C-Scene 项目 #2）。\n\n"
        hmd += "\n\n".join(header_lines) + "\n"
        fp = os.path.join(OUT, "00-译者说明.md")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(hmd)
        print("  ✍ 00-译者说明.md  %dB" % len(hmd))

    # 边界 = 标题行（含），尾巴 = 行尾
    bounds = heads + [(len(lines), "END", 0)]
    docs = []
    for idx, (ln, title, lv) in enumerate(bounds[:-1]):
        end = bounds[idx + 1][0]
        body = []
        code_flags = [False] * len(lines)
        for a, b in code_ranges:
            for j in range(a, b + 1):
                code_flags[j] = True
        in_code = False
        for j in range(ln + 1, end):
            t = lines[j]
            if re.match(r"^===\s*\S+\s*开始\s*===$", t):
                in_code = True
                continue
            if re.match(r"^===\s*\S+\s*结束\s*===$", t):
                in_code = False
                continue
            if not t:
                continue
            # 剥装饰线 ~~~~~~~~~
            if re.match(r"^~+$", t):
                continue
            if in_code:
                body.append(("code", t))
            else:
                body.append(("text", t))
        docs.append((title, lv, body))
        print("  [%s] %d 行" % (title, len(body)))

    # 写文件：章 = 目录节点（目录名 NN-标题），节 = 文档；章正文（若有）并入首节前
    # 简化：每章一个目录，章下每节一个文档；章内非节正文放「00-章概述」文档
    def write_doc(fname, title, body):
        md = []
        buf = []  # 连续 code 行攒成一个围栏块
        for kind, t in body:
            if kind == "code":
                buf.append(t)
                continue
            if buf:
                md.append("```makefile\n%s\n```" % "\n".join(buf))
                buf = []
            md.append(t)
        if buf:
            md.append("```makefile\n%s\n```" % "\n".join(buf))
        text = "\n\n".join(md) + "\n"
        text = re.sub(r"\n{3,}", "\n\n", text)
        fp = os.path.join(OUT, fname)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(text)
        print("  ✍ %-40s %6dB" % (fname, len(text)))

    # 建树：章目录 + 节文档
    chapters = []  # (ch_title, ch_lv, [sections])
    cur = None
    for title, lv, body in docs:
        if lv == 1:
            cur = (title, body, [])
            chapters.append(cur)
        else:
            if cur:
                cur[2].append((title, body))
    # 章名编号规范化：0. 介绍 / 1. 多文件项目 / 2. GNU Make 工具 / 3. 总结
    for ci, (ch_title, ch_body, sections) in enumerate(chapters):
        dirname = "%02d-%s" % (ci, re.sub(r"^\d+\.\s*", "", ch_title).replace("/", "／"))
        dpath = os.path.join(OUT, dirname)
        os.makedirs(dpath, exist_ok=True)
        # 章概述 = 章标题下、首节前的正文；若为空则该文档不建
        if ch_body:
            write_doc(os.path.join(dpath, "00-%s.md" % re.sub(r"^\d+\.\s*", "", ch_title).replace("/", "／")),
                      ch_title, ch_body)
        for si, (sec_title, sec_body) in enumerate(sections):
            secname = re.sub(r"^\d+\.\d+\s*", "", sec_title).replace("/", "／")
            fname = "%02d-%s.md" % (si + 1, secname)
            write_doc(os.path.join(dpath, fname), sec_title, sec_body)
        print("  章 %s: %d 节" % (dirname, len(sections)))


if __name__ == "__main__":
    main()
