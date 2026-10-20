#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sketch 中文用户手册（sketchcn.com）→ 分章 markdown。

源：Common Crawl 2019-04-25 快照（站点已下线）
结构：正文窗口 = 侧栏手风琴导航 </ul> 之后 → <div class="verticalspacer"> 之前
     按 <h1> 拆章（坑 34：单页长文档 → 按 h1 拆）
     h3/h4 级小标题在 Muse 里是 <p>，用 index.md（翻译源，i5ting/sketchcn）的标题做 oracle 还原
"""
import os, re, sys, html as H, shutil

SRC_HTML = "manual-2019-18.html"                      # CC 2019-04-25 快照（权威发布版）
ORACLE_MD = "i5ting-sketchcn/index.md"                # 翻译源（标题 oracle）
IMG_SRC_DIRS = ["i5ting-sketchcn/sketchcn.com/images", "i5ting-sketchcn/images"]
OUT = "clean"

# ---------- 1. oracle：index.md 的标题（中文部分，去掉（English）后缀） ----------
def load_oracle():
    md = open(ORACLE_MD, encoding="utf-8").read()
    om = {}
    for m in re.finditer(r'^(#{1,4})\s*(.+)$', md, re.M):
        lvl, t = len(m.group(1)), m.group(2).strip()
        t = re.sub(r'\s*[（(][^（）()]*[)）]\s*$', '', t).strip()
        if t and re.search(r'[\u4e00-\u9fff]', t):
            om.setdefault((lvl, t), 0)
            om[(lvl, t)] += 1
    return om

# ---------- 2. 正文窗口 ----------
def content_window(raw):
    s = raw.find("欢迎使用 Sketch 3")
    assert s > 0, "找不到内容起点"
    start = raw.rfind("<div", 0, s)
    e = raw.find('<div class="verticalspacer">', start)
    assert e > 0, "找不到内容终点"
    w = raw[start:e]
    w = re.sub(r'<(script|style)\b.*?</\1>', '', w, flags=re.S | re.I)
    w = re.sub(r'<!--.*?-->', '', w, flags=re.S)
    return w

# ---------- 3. 行内转换 ----------
def inline(s):
    s = re.sub(r'<a\b[^>]*?href="([^"]*)"[^>]*>(.*?)</a>', lambda m: (
        "[%s](%s)" % (re.sub(r'<[^>]+>', '', m.group(2)).strip(), m.group(1))
        if m.group(1).startswith("http") else re.sub(r'<[^>]+>', '', m.group(2)).strip()), s, flags=re.S)
    s = re.sub(r'<img\b[^>]*>', '', s)
    s = re.sub(r'<br\s*/?>', ' ', s, flags=re.I)
    s = re.sub(r'</?span\b[^>]*>', '', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = H.unescape(s)
    s = s.replace('\u00a0', ' ').replace('\u200b', '')
    s = re.sub(r'[ \t]+', ' ', s).strip()
    return s

BLOCK = re.compile(
    r'<(h[1-4])\b[^>]*>(.*?)</\1>'
    r'|<p\b([^>]*)>(.*?)</p>'
    r'|(<img\b[^>]*?/?>)',
    re.S | re.I)
IMG_RE = re.compile(r'src="([^"]+)"')
BULLET = ('・', '•', '·', 'Ø', 'ü', '–')

def convert(window, oracle, img_keep):
    lines, chapters = [], []
    cur = None
    real_h2 = set(inline(m.group(1)) for m in re.finditer(r'<h2\b[^>]*>(.*?)</h2>', window, re.S | re.I))
    for m in BLOCK.finditer(window):
        if m.group(1):  # heading tag
            lvl = int(m.group(1)[1])
            t = inline(m.group(2))
            if not t:
                continue
            if lvl == 1:
                cur = {"title": t, "lines": []}
                chapters.append(cur)
                lines = cur["lines"]
                continue
            if cur is None:      # h1 之前（前言区）
                continue
            lines.append(("#" * lvl) + " " + t)
            lines.append("")
        elif m.group(5):  # img
            src = IMG_RE.search(m.group(5))
            if not src:
                continue
            url = src.group(1).replace('%40', '@')
            if not url.startswith("images/"):
                continue
            if cur is None:
                continue          # 前言里不要装饰图
            if url not in img_keep:
                continue
            lines.append("![%s](%s)" % (os.path.basename(url), url))
            lines.append("")
        else:  # p
            attrs, body = m.group(3) or "", m.group(4)
            t = inline(body)
            if not t:
                continue
            cls = re.search(r'class="([^"]*)"', attrs)
            cls = cls.group(1) if cls else ''
            kind = None
            for lvl in (2, 3, 4):
                if oracle.get((lvl, t)):
                    kind = lvl
                    break
            # 该标题在本页另有真 h2 标签（如「添加图层」在「图层」章）= 这里是更小一级的子标题
            if kind == 2 and t in real_h2:
                kind = 3
            if 'code' in cls:
                lines.append("```")
                lines.append(H.unescape(re.sub(r'<[^>]+>', '', body)).strip())
                lines.append("```")
                lines.append("")
            elif kind and len(t) <= 30 and not t.endswith('。'):
                lines.append(("#" * kind) + " " + t)
                lines.append("")
            elif t[0] in BULLET:
                lines.append("- " + t[1:].strip())
                lines.append("")
            else:
                lines.append(t)
                lines.append("")
    # 修相邻重复标题 + 压缩空行 + 紧凑列表
    out = []
    for c in chapters:
        body = "\n".join(c["lines"])
        body = re.sub(r'\n{3,}', '\n\n', body)
        body = re.sub(r'(?m)^(- .*)\n\n(?=- )', r'\1\n', body)   # 连续列表项之间不留空行
        out.append((c["title"], body.strip()))
    return out

def main():
    oracle = load_oracle()
    raw = open(SRC_HTML, encoding="utf-8").read()
    w = content_window(raw)
    # 收集正文里引用到的图片
    refs = []
    for m in IMG_RE.finditer(w):
        u = m.group(1).replace('%40', '@')
        if u.startswith("images/") and u not in refs:
            refs.append(u)
    print("[img] 正文引用图 %d 张" % len(refs))
    os.makedirs(OUT, exist_ok=True)
    imgdir = os.path.join(OUT, "images")
    os.makedirs(imgdir, exist_ok=True)
    img_keep, missing = set(), []
    for u in refs:
        name = os.path.basename(u)
        for d in IMG_SRC_DIRS:
            p = os.path.join(d, name)
            if os.path.exists(p):
                shutil.copy2(p, os.path.join(imgdir, name))
                img_keep.add(u)
                break
        else:
            missing.append(u)
    print("[img] 落地 %d 张；缺失 %d 张 %s" % (len(img_keep), len(missing), missing))

    chapters = convert(w, oracle, img_keep)
    print("[ch] %d 章" % len(chapters))
    written = []
    # 前言
    pre = ["# Sketch 中文用户手册（Sketch 3）", "",
           "欢迎使用 Sketch 3 的用户手册，这个手册的内容同时适用于新手和熟练用户。", "",
           "如果你对于这个手册的内容有任何想法和疑问，请通过邮箱 mail@bohemiancoding.com 随时联系我们。我们会不断的完善本手册。", "",
           "本手册翻译自 Sketch 官方用户手册，已更新至 Sketch 3 版本。", "",
           "> 来源：http://sketchcn.com/sketch-chinese-user-manual.html",
           "> 站点已下线（域名在售），正文经 Common Crawl 2019-04-25 快照恢复；配图取自同源镜像仓库 github.com/i5ting/sketchcn",
           "> 原站作者：Aegean K（Sketch 中文网 / ©2014 SketchCN）", "", "## 目录", ""]
    for i, (t, _) in enumerate(chapters, 1):
        pre.append("%d. %s" % (i, t))
    p0 = os.path.join(OUT, "00-前言.md")
    open(p0, "w", encoding="utf-8").write("\n".join(pre) + "\n")
    written.append(p0)
    for i, (t, body) in enumerate(chapters, 1):
        fn = "%02d-%s.md" % (i, t.replace('/', '／'))
        p = os.path.join(OUT, fn)
        open(p, "w", encoding="utf-8").write("# %s\n\n%s\n" % (t, body))
        written.append(p)
    print("[out] 写好 %d 个文件到 %s" % (len(written), OUT))
    for f in written:
        print("   ", os.path.basename(f), os.path.getsize(f))

if __name__ == "__main__":
    main()