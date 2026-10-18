#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《走向分布式》PDF → Markdown（30 章拆篇 + 位图提取内嵌 + 页内图片就近插入）。

排版特征（Release 1.0.1, ccshih 译 2015-03-22, 41 页 612x792）：
  - 章标题页：顶部 "CHAPTER"(y~102) + 罗马数字(y~132) + "DAY N: 标题"(17.22pt, y~180-245, 可换行)
  - 正文 11.95pt（中文 WenQuanYiMicroHei / 西文 ArialMT / 粗体 Arial-BoldMT）
  - 脚注/整理者注：9.96pt 段（行首带编号 "1"/"2"，尾部 "（by 邓草原）"）→ blockquote
  - 上标引用标记 7.97pt（正文行尾 "1"/"2"）→ 原样保留
  - 项目符号行 "• "（x≈91）→ markdown "- "；编号行 "N. "（x≈72）→ 段边界
  - 无等宽字体 → 无代码块
  - 页眉（"走向分布式, Release 1.0.1"）y≈35.6；页码 y≈742（H=792）→ top<60 / bot>730
  - 位图 3 张：p16 CAP 示意图 / p21 Kafka 架构图 / p22 partition 示意；矢量仅页眉页脚横线，不渲染
  - 跨页续段：页首无图且上行无句末标点 → 合并；页首有图 → 断段，图插在段后
"""
import json
import os
import re
import sys

import pymupdf

PDF = "/home/admin/.openclaw/workspace/tmp/scalability.pdf"
OUT = "/home/admin/.openclaw/workspace/tmp/scalability-20261018-clean"

WORDS = set()
try:
    with open("/home/admin/.openclaw/workspace/tmp/ostep/words.txt", encoding="utf-8", errors="replace") as f:
        WORDS = {l.strip().lower() for l in f if l.strip()}
except OSError:
    pass

LIG = {"\ufb01": "fi", "\ufb02": "fl", "\ufb00": "ff", "\ufb03": "ffi", "\ufb04": "ffl"}


def clean(t):
    for k, v in LIG.items():
        t = t.replace(k, v)
    t = (t.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"')
         .replace("\u201d", '"').replace("\u2010", "-").replace("\u2011", "-")
         .replace("\u2013", "-").replace("\u2014", "-")
         .replace("\u2026", "...").replace("\u00a0", " ").replace("\uf8ff", ""))
    return t


CJK = r"\u4e00-\u9fff\u3000-\u303f\uff00-\uffef"


def fix_spacing(t):
    t = re.sub(r"(?<=[%s]) (?=[%s])" % (CJK, CJK), "", t)
    t = re.sub(r"(?<=[%s]) (?=[，。：；！？、）】》…])" % CJK, "", t)
    t = re.sub(r"(?<=[（【《]) (?=[%s])" % CJK, "", t)
    return t


def is_bold(font):
    return "Bold" in font


def render_line(spans):
    out = []
    for s in spans:
        t = clean(s["text"])
        if not t:
            continue
        if is_bold(s["font"]):
            t = "**%s**" % t
        out.append(t)
    txt = "".join(out)
    for _ in range(4):
        new = re.sub(r"\*\*([^*]+)\*\*\s*\*\*([^*]+)\*\*", r"**\1 \2**", txt)
        new = re.sub(r"(?<![*\w])\*([^*]+)\*\s*\*([^*]+)\*(?![*\w])", r"*\1 \2*", new)
        if new == txt:
            break
        txt = new
    txt = re.sub(r"\s+([,.;:!?)])", r"\1", txt)
    txt = re.sub(r"\(\s+", "(", txt)
    txt = fix_spacing(txt)
    return re.sub(r"[ ]{2,}", " ", txt).strip()


def dehyphen(prev_md, next_md):
    m = re.search(r"([A-Za-z]{2,})-+$", prev_md)
    m2 = re.match(r"([A-Za-z]+)", next_md)
    if m and m2:
        left, right = m.group(1), m2.group(1)
        if len(left) >= 3 and left.lower() in WORDS and right.lower() in WORDS:
            return prev_md + next_md
    if m:
        return prev_md[: m.start(1)] + m.group(1) + next_md
    return prev_md.rstrip("-") + next_md


# 章起页（0-based）；TITLES 取书内目录原文（标题页为全大写，目录为原文大小写）
CHAPTER_PAGES = [4, 5, 7, 9, 10, 11, 12, 14, 15, 17, 18, 19, 20, 21, 23, 25,
                 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39]
LAST_PAGE = 40
TITLES = {
    1: "Scalability", 2: "分散式系统的面向", 3: "Partition",
    4: "为什麽有有些时候不要把 QUERY 洒到所有机器上平行处理？",
    5: "资料切割的 METADATA 管理", 6: "Replication",
    7: "无强一致性及无法决定执行顺序带来的问题", 8: "最终一致性", 9: "CAP Theorem",
    10: "In-Memory data", 11: "Zookeeper", 12: "Zookeeper (续)",
    13: "Apache Kafka", 14: "Apache Kafka (2)", 15: "Apache Kafka (3)",
    16: "Apache Kafka (4)", 17: "Apache Kafka (5)",
    18: "Apache Kafka 与 Stream Computing", 19: "分散式资料系统 vs. 科层组织",
    20: "In-Memory 的技术议题?", 21: "分散式运算系统", 22: "分散式运算系统的沟通方式",
    23: "Stream Computing 的应用范围", 24: "Stream Computing 特性",
    25: "选择 Stream Computing 框架", 26: "Stream Computing 框架的组成角色",
    27: "如何追踪每一个 Record 的处理进度", 28: "错误处理机制",
    29: "从 Stream 到 Micro batch", 30: "Stream States & Finale",
}
ALT = {(16, 98): "CAP Theorem 示意图（Source: w3resource.com）",
       (21, 116): "Kafka 基本架构图（取自 Kafka documentation）",
       (22, 121): "Kafka partition 与 consumer 示意"}


def chapter_pages(i):
    start = CHAPTER_PAGES[i]
    end = (CHAPTER_PAGES[i + 1] - 1) if i + 1 < len(CHAPTER_PAGES) else LAST_PAGE
    return list(range(start, end + 1))


def load_lines(doc, pages):
    lines, images = [], []
    for pno in pages:
        page = doc[pno]
        H = page.rect.height
        for img in page.get_images(full=True):
            xref = img[0]
            info = doc.extract_image(xref)
            for r in page.get_image_rects(xref):
                images.append({"page": pno, "y0": r.y0, "xref": xref, "ext": info["ext"]})
        for b in page.get_text("dict")["blocks"]:
            if b["type"] != 0:
                continue
            for l in b["lines"]:
                spans = [s for s in l["spans"] if s["text"]]
                if not spans:
                    continue
                y = l["bbox"][1]
                if y < 60 or y > 730:      # 页眉 / 页码
                    continue
                text = clean("".join(s["text"] for s in spans))
                if not text.strip():
                    continue
                size = max(round(s["size"], 2) for s in spans)
                # 章标题页装饰与标题行（CHAPTER/罗马数字 y<180；DAY N: 标题 y 180-245 有独立 H1）
                if pno in CHAPTER_PAGES and y < 245:
                    if text.strip().upper() == "CHAPTER" or re.fullmatch(r"[A-Z]+", text.strip()):
                        continue
                    if y >= 180 and size >= 16:
                        continue
                lines.append({"page": pno, "y": y, "x": l["bbox"][0],
                              "size": size, "text": text, "md": render_line(spans)})
    return lines, images


def to_md(pages, title, doc):
    lines, images = load_lines(doc, pages)
    first_y = {}
    for L in lines:
        first_y.setdefault(L["page"], L["y"])
    early_img_pages = {im["page"] for im in images if im["y0"] < first_y.get(im["page"], 10 ** 9)}

    pending_img = sorted(images, key=lambda im: (im["page"], im["y0"]))
    blocks = []

    def flush_imgs(before_page, before_y):
        nonlocal pending_img
        keep = []
        for im in pending_img:
            if im["page"] < before_page or (im["page"] == before_page and im["y0"] < before_y):
                rel = "img/scalability-p%02d-%d.%s" % (im["page"], im["xref"], im["ext"])
                alt = ALT.get((im["page"], im["xref"]), "图")
                blocks.append(("img", (rel, alt)))
            else:
                keep.append(im)
        pending_img = keep

    i, n = 0, len(lines)
    while i < n:
        L = lines[i]
        flush_imgs(L["page"], L["y"])
        t = L["text"].strip()
        if not t:
            i += 1
            continue
        if L["size"] <= 10.2:       # 9.96pt 脚注/整理者注
            buf = [t]
            i += 1
            while i < n and lines[i]["size"] <= 10.2:
                buf.append(lines[i]["text"].strip())
                i += 1
            blocks.append(("quote", " ".join(buf)))
            continue
        bullet = t.startswith("\u2022")
        numitem = re.match(r"^\d+[.、)]", t) is not None
        cur = L
        cur_x = L["x"]
        i += 1
        while i < n:
            N = lines[i]
            nt = N["text"].strip()
            if not nt or N["size"] <= 10.2:
                break
            if nt.startswith("\u2022") or re.match(r"^\d+[.、)]", nt):
                break                       # 新列表项 = 硬边界
            page_break = N["page"] != cur["page"]
            if page_break and N["page"] in early_img_pages:
                break                       # 页首有图 → 断段，图插在这之间
            prev_end = re.search(r"[.!?;。！？'\")\]]+\d*$", cur["text"].rstrip())
            # list wrap x jumps up (91.2 -> 101.3); no x_jump split inside lists
            x_jump = (not bullet and not numitem) and (N["x"] > cur_x + 6)
            new_para = (x_jump or prev_end) and not (page_break and not prev_end)
            if (bullet or numitem) and N["x"] <= cur_x - 8:
                new_para = True             # list ended: indent back to left edge
            if not prev_end and cur["text"].startswith("Source:"):
                new_para = True             # force break after figure caption
            if new_para:
                break
            prev = cur["md"].rstrip()
            nxt = re.sub(r"^\u2022\s*", "", N["md"])
            if prev.endswith("-") and not prev.endswith("--"):
                cur = dict(cur, md=dehyphen(prev, nxt),
                           text=cur["text"].rstrip()[:-1] + " " + nt)
            else:
                cur = dict(cur, md=(prev + " " + nxt).strip(),
                           text=cur["text"].rstrip() + " " + nt)
            cur_x = N["x"]
            i += 1
        body = cur["md"]
        if bullet:
            body = re.sub(r"^\u2022\s*", "- ", body)
        if numitem and not re.match(r"^\d+[.、)]", body):
            body = re.sub(r"^\u2022\s*", "", body)
        blocks.append(("p", body))
    flush_imgs(10 ** 9, 10 ** 9)

    out = ["# %s" % title, ""]
    for kind, val in blocks:
        if kind == "p":
            out.append(polish(val))
            out.append("")
        elif kind == "quote":
            for ln in val.split("\n"):
                out.append("> %s" % ln)
            out.append("")
        elif kind == "img":
            rel, alt = val
            out.append("![%s](%s)" % (alt, rel))
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def polish(md):
    for _ in range(4):
        new = re.sub(r"\*\*([^*]+)\*\*\s*\*\*([^*]+)\*\*", r"**\1 \2**", md)
        new = re.sub(r"`([^`]+)`\s*`([^`]+)`", r"`\1 \2`", new)
        if new == md:
            break
        md = new
    md = re.sub(r"\s+([,.;:!?)])", r"\1", md)
    md = re.sub(r"\(\(([^()]*)\)\)", r"(\1)", md)
    md = fix_spacing(md)
    md = re.sub(r"\s{2,}", " ", md)
    return md.strip()


def main():
    only = int(sys.argv[1]) if len(sys.argv) > 1 else None
    doc = pymupdf.open(PDF)
    os.makedirs(os.path.join(OUT, "img"), exist_ok=True)
    total = 0
    for idx, pno in enumerate(CHAPTER_PAGES):
        n = idx + 1
        if only and only != n:
            continue
        title = "Day %d: %s" % (n, TITLES[n])
        fname = "%02d-Day %d-%s.md" % (n, n, TITLES[n].replace("/", "-"))
        md = to_md(chapter_pages(idx), title, doc)
        with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
            f.write(md)
        # 导出位图（幂等：已存在跳过）
        for im in load_lines(doc, chapter_pages(idx))[1]:
            info = doc.extract_image(im["xref"])
            rel = "scalability-p%02d-%d.%s" % (im["page"], im["xref"], info["ext"])
            path = os.path.join(OUT, "img", rel)
            if not os.path.exists(path):
                with open(path, "wb") as f:
                    f.write(info["image"])
        total += 1
        print("%02d <- p%d  %-58s %6d chars" % (n, pno, fname, len(md)))
    print("chapters:", total)


if __name__ == "__main__":
    main()