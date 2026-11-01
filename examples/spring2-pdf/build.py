#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fpb52 #152 Spring 2.0核心技术与最佳实践 — 廖雪峰 PDF（michaelliao.github.io）→ md

网站口径（PDF 原件托管在个人站点）+ 默认双轨（解析正文 + PDF 原件附件）。
结构：书签锚定章节（章封面「首页NN」跳过，正文从「NN」页开始到下一章前）。
"""
import pymupdf, os, re, json

PDF = "spring2.0.pdf"
OUT = "site"
os.makedirs(OUT, exist_ok=True)

doc = pymupdf.open(PDF)
toc = doc.get_toc()

# 1 级书签：标题 + 起始页
lvl1 = [(t, p-1) for l, t, p in toc if l == 1]  # 0-indexed

# 章正文起点（书签名为 NN 数字的 1 级条目）
chapters = []  # (章名, start, end)
for i, (t, p) in enumerate(lvl1):
    if re.match(r'^\d+$', t):
        end = lvl1[i+1][1] - 1 if i+1 < len(lvl1) else doc.page_count - 1
        chapters.append((t, p, end))

# 前言
preface = None
for t, p in lvl1:
    if t == 'd前言':
        # 到 e作者简介 之前
        idx = [i for i,(tt,_) in enumerate(lvl1) if tt=='e作者简介']
        end = lvl1[idx[0]][1] - 1 if idx else p + 3
        preface = (p, end)
        break

print("chapters:", chapters)
print("preface:", preface)

# 抽取函数：页范围 → md
def extract(p_start, p_end):
    out = []
    for pno in range(p_start, p_end + 1):
        page = doc[pno]
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if b.get("type") != 0:
                continue
            lines = []
            for ln in b["lines"]:
                txt = "".join(sp["text"] for sp in ln["spans"])
                lines.append(txt)
            text = "\n".join(lines)
            if text.strip():
                out.append(text)
    return "\n\n".join(out)

def clean(text):
    """去页眉页脚、连续空行"""
    lines = text.split("\n")
    keep = []
    for ln in lines:
        s = ln.strip()
        if s in ("Java 技术大系", "Spring 2.0 核心技术与最佳实践"):
            continue
        if re.match(r'^\d+$', s):  # 页码
            continue
        if s.startswith("第") and re.match(r'^第\d+ 章', s):
            continue
        keep.append(ln)
    t = "\n".join(keep)
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()

def chapter_md(title, text):
    return f"# {title}\n\n{text}\n"

# 前言
if preface:
    p_start, p_end = preface
    text = clean(extract(p_start, p_end))
    # 剥前言里的目录（内容简介/目录页在 f目录，前言本身含特色/内容/读者对象）
    with open(os.path.join(OUT, "00-前言.md"), "w", encoding="utf-8") as f:
        f.write(chapter_md("前言", text))
    print("preface:", len(text))

# 章
for title, p_start, p_end in chapters:
    text = clean(extract(p_start, p_end))
    fname = f"{title}-第{title}章.md" if False else None
    # 文件名: NN-<章名>.md；章名从章首页标题提（书签只有编号）
    # 取正文首个 1.x 节标题前的内容作为章名？简化：用编号 + 首行
    m = re.search(r'([\u4e00-\u9fa5A-Za-z0-9 /．.]+?)\s*\n', text)
    fname = f"{int(title):02d}.md"
    with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
        f.write(chapter_md(f"第{int(title)}章", text))
    print(title, f"p{p_start+1}-{p_end+1}", "len:", len(text))

appendix = [(t, p-1) for l, t, p in toc if l == 1 and t.startswith("附录")]
for t, p in appendix:
    idx = [i for i,(tt,_) in enumerate(lvl1) if tt==t]
    end = lvl1[idx[0]+1][1]-1 if idx[0]+1 < len(lvl1) else doc.page_count-2
    text = clean(extract(p, end))
    with open(os.path.join(OUT, f"{t}.md"), "w", encoding="utf-8") as f:
        f.write(chapter_md(t, text))
    print(t, f"p{p+1}-{end+1}", "len:", len(text))

print("DONE")
