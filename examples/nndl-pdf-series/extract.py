#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nndl 系列 PDF → 语雀导入树（逐章 md）。

用法:  python3 extract.py v2|ge
产出:  <here>/<book>/clean/  （可直接喂 yuque_tree_import.py --toc-md）
"""
import os
import re
import shutil
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = "/home/admin/.openclaw/workspace/tmp"

BOOKS = {
    "v2": dict(
        pdf=f"{TMP}/nndl-v2.pdf", out=f"{HERE}/v2/clean",
        chapter_level=2, part_level=1,
        hdr_y1=58.0, ftr_y0=640.0, margin_x=350.0,
        part_re=r"^第[一二三四五六七八九十]+部分",
        front=[("00-前言", 2, 3), ("00-如何阅读本书", 4, 5), ("00-常用符号表", 6, 7)],
    ),
    "ge": dict(
        pdf=f"{TMP}/nndl-ge.pdf", out=f"{HERE}/ge/clean",
        chapter_level=1, part_level=None,
        hdr_y1=58.0, ftr_y0=640.0, margin_x=10**9,
        part_re=None,
        front=[("00-前言", 2, 3)],
    ),
    "practice": dict(
        pdf=f"{TMP}/nndl-practice.pdf", out=f"{HERE}/practice/clean",
        chapter_level=1, part_level=None,
        hdr_y1=58.0, ftr_y0=640.0, margin_x=350.0,
        part_re=None,
        front=[("00-前言", 2, 3)],
    ),
    "llm-agent": dict(
        pdf=f"{TMP}/llm-agent.pdf", out=f"{HERE}/llm-agent/clean",
        chapter_level=2, part_level=1,
        hdr_y1=58.0, ftr_y0=640.0, margin_x=350.0,
        part_re=r"^(共用基础|大模型|智能体|边界与未来)$",
        front=[("00-前言", 2, 3)],
    ),
}

CJK = lambda ch: ("\u4e00" <= ch <= "\u9fff") or ("\u3000" <= ch <= "\u303f") or ("\uff00" <= ch <= "\uffef")
BULLET = "•·‣▪◆●○◦"


def _clean(s):
    """剥 C0 控制符（含 NUL）——PDF 公式残渣会带 \x00\x01，导入器判二进制→占位。"""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)


def _join(a, b):
    if not a:
        return b
    if not b:
        return a
    if CJK(a[-1]) and CJK(b[0]):
        return a + b
    return a + " " + b


def _major_join(parts):
    s = ""
    for p in parts:
        s = _join(s, p)
    return s


def page_lines(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        for l in b["lines"]:
            spans = [s for s in l["spans"] if s["text"]]
            if not spans:
                continue
            txt = "".join(s["text"] for s in l["spans"])
            if not txt.strip():
                continue
            out.append({"x0": l["bbox"][0], "x1": l["bbox"][2],
                        "y0": l["bbox"][1], "y1": l["bbox"][3],
                        "size": max(s["size"] for s in spans),
                        "font": spans[0]["font"], "text": txt})
    out.sort(key=lambda x: (round(x["y0"], 1), x["x0"]))
    # 合并「节号行 + 标题行」（同 y、编号在左）→ "1.1.1 人工智能的发展历史"
    NUM = re.compile(r"[A-Z]?\.?\d+(\.\d+)*")
    merged, i = [], 0
    while i < len(out):
        a = out[i]
        b = out[i + 1] if i + 1 < len(out) else None
        if b and abs(b["y0"] - a["y0"]) < 5:
            an, bn = NUM.fullmatch(a["text"].strip()), NUM.fullmatch(b["text"].strip())
            if an and not bn and b["size"] >= 10.5:
                t = a["text"].strip() + b["text"]
            elif bn and not an and a["size"] >= 10.5:
                t = b["text"].strip() + a["text"]
            else:
                t = None
            if t:
                merged.append({"x0": min(a["x0"], b["x0"]), "x1": max(a["x1"], b["x1"]),
                               "y0": min(a["y0"], b["y0"]), "y1": max(a["y1"], b["y1"]),
                               "size": max(a["size"], b["size"]),
                               "font": b["font"], "text": t})
                i += 2
                continue
        merged.append(a)
        i += 1
    return merged


def heading_bytext(doc, chapter_level):
    """归一化标题 -> 相对层级（heading_map 用文本匹配，比坐标稳）。"""
    m = {}
    for e in doc.get_toc():
        if e[0] <= chapter_level:
            continue
        key = re.sub(r"\s+", "", e[1])
        m[key] = e[0] - chapter_level
    return m


def part_titles(doc, part_level):
    if not part_level:
        return set()
    return {re.sub(r"\s+", "", e[1]) for e in doc.get_toc() if e[0] == part_level}


def chapters(doc, chapter_level, part_level):
    toc = doc.get_toc()
    ents = [(e[0], re.sub(r"\s+", " ", e[1]).strip(), e[2] - 1) for e in toc]
    chaps = [e for e in ents if e[0] == chapter_level]
    parts = {e[2]: e[1] for e in ents if part_level and e[0] == part_level}
    out = []
    for i, (lvl, title, pg) in enumerate(chaps):
        end = chaps[i + 1][2] - 1 if i + 1 < len(chaps) else doc.page_count - 1
        part = None
        if part_level:
            for p in sorted([k for k in parts if k <= pg], reverse=True):
                part = parts[p]
                break
        out.append(dict(part=part, title=title, sp=pg, ep=end))
    return out


def extract_pages(doc, sp, ep, cfg, hbytext, drop_titles, chapter_title):
    body_cnt = {}
    pages = []
    for pno in range(sp, ep + 1):
        page = doc[pno]
        lines = [l for l in page_lines(page) if l["y1"] > cfg["hdr_y1"] - 2 and l["y0"] < cfg["ftr_y0"]]
        for l in lines:
            if l["x0"] < cfg["margin_x"]:
                body_cnt[round(l["size"])] = body_cnt.get(round(l["size"]), 0) + 1
        pages.append((pno, lines))
    if not body_cnt:
        return ""
    body_size = max(body_cnt, key=body_cnt.get)

    chtitle = re.sub(r"[\s.]+", "", chapter_title)
    out = []
    cur = None

    def flush():
        nonlocal cur
        if cur and cur["text"].strip():
            out.append(cur)
        cur = None

    code_buf = []

    def flush_code():
        if code_buf:
            out.append({"kind": "code", "text": "\n".join(code_buf)})
            code_buf.clear()

    for pno, lines in pages:
        notes = []
        for l in lines:
            txt = re.sub(r"\s+", " ", _clean(l["text"])).strip()
            if not txt:
                continue
            # ---- 边注栏（右侧）----
            if l["x0"] >= cfg["margin_x"]:
                if not re.fullmatch(r"[（(]?\d+[.\-]\d+[）)]?", txt):   # 丢公式编号 (3.32)
                    notes.append((l["y0"], txt))
                continue
            # 大字号 = 章/部分标题（已由书签生成 #），丢
            if l["size"] >= 14.5:
                continue
            nt = re.sub(r"\s+", "", txt)
            if nt == chtitle or nt in drop_titles:
                continue
            if re.fullmatch(r"[\dIVXivx.·・\-–—]{1,6}", txt):   # 裸页码
                continue
            hlv = hbytext.get(nt)
            if hlv and len(nt) >= 3:
                flush_code()
                flush()
                out.append({"kind": "h", "level": hlv, "text": txt})
                continue
            # ---- 代码行（等宽字体）----
            if "Mono" in l["font"]:
                flush()
                base = cfg.get("code_base") or l["x0"]
                nch = max(0, round((l["x0"] - base) / (l["size"] * 0.5)))
                code_buf.append(" " * nch + txt)
                continue
            flush_code()
            is_li = txt[:1] in BULLET
            if is_li:
                txt = re.sub(r"^[%s]\s*" % re.escape(BULLET), "", txt)
            base_x = 72.0
            newp = (cur is None or is_li or l["size"] >= 12.5 or l["x0"] > base_x + 8
                    or re.match(r"^[A-Z][A-Za-z\-]{1,} [A-Z]", txt)
                    or (l["y0"] - cur.get("_y1", 0) > 1.8 * (l["size"] + 3)))
            if is_li:
                flush(); cur = {"kind": "li", "text": txt, "_y1": l["y1"]}
            elif newp:
                flush(); cur = {"kind": "p", "text": txt, "_y1": l["y1"]}
            else:
                cur["text"] = _join(cur["text"], txt); cur["_y1"] = l["y1"]
        flush()
        flush_code()
        if notes:
            out.append({"kind": "q", "text": _major_join([t for _, t in sorted(notes)])})

    # 丢“图内孤立短标签”连续块
    def _noise(t):
        return (not any(CJK(c) for c in t)) and len(t) <= 14 and t[-1] not in "。！？；,.!?;：:"
    clean, i = [], 0
    while i < len(out):
        if out[i]["kind"] == "p" and _noise(out[i]["text"]):
            j = i
            while j < len(out) and out[j]["kind"] == "p" and _noise(out[j]["text"]):
                j += 1
            if j - i >= 3:
                i = j
                continue
        clean.append(out[i]); i += 1
    out = clean

    md = []
    for it in out:
        if it["kind"] == "h":
            ht = re.sub(r"^([A-Z]?\.?\d+(?:\.\d+)*)(?=\S)", r"\1 ", it["text"])
            md.append("\n" + "#" * min(2 + it["level"] - 1, 6) + " " + ht + "\n")
        elif it["kind"] == "li":
            md.append("- " + it["text"])
        elif it["kind"] == "q":
            md.append("\n> 📝 " + it["text"] + "\n")
        elif it["kind"] == "code":
            cl = it["text"].split("\n")
            common = min((len(x) - len(x.lstrip()) for x in cl if x.strip()), default=0)
            cl = [x[common:] for x in cl]
            md.append("\n```\n" + "\n".join(cl) + "\n```\n")
        else:
            md.append(it["text"] + "\n")
    return re.sub(r"\n{3,}", "\n\n", "\n".join(md)).strip()


def build(book):
    cfg = BOOKS[book]
    doc = pymupdf.open(cfg["pdf"])
    # 等宽代码列左边界（用于还原缩进）
    cxs = []
    for pg in doc:
        for b in pg.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                if l["spans"] and "Mono" in l["spans"][0]["font"] and l["spans"][0]["text"].strip():
                    cxs.append(l["bbox"][0])
    cfg["code_base"] = min(cxs) if cxs else 0.0
    hbytext = heading_bytext(doc, cfg["chapter_level"])
    parts_nt = part_titles(doc, cfg["part_level"])
    drop = set(parts_nt)
    chs = chapters(doc, cfg["chapter_level"], cfg["part_level"])
    chs = [c for c in chs if re.sub(r"\s+", "", c["title"]) not in ("目录", "前言")]
    out = cfg["out"]
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out, exist_ok=True)
    made = []

    if cfg["front"]:
        for title, sp, ep in cfg["front"]:
            text = extract_pages(doc, sp, ep, cfg, {}, set(), title)
            with open(os.path.join(out, title + ".md"), "w", encoding="utf-8") as f:
                f.write("# %s\n\n%s\n" % (title[3:], text))
            made.append((title, len(text)))

    for i, ch in enumerate(chs, 1):
        title = re.sub(r"\s+", " ", ch["title"]).strip()
        title = re.sub(r"^(附录)\s+([A-E])\s+", r"\1\2 ", title)
        text = extract_pages(doc, ch["sp"], ch["ep"], cfg, hbytext, drop, ch["title"])
        if not text:
            print("  [warn] 空章:", title); continue
        rel = re.sub(r"[/\\:]", "-", title)
        if ch["part"]:
            pdir = re.sub(r"\s+", " ", ch["part"]).strip()
            pdir = os.path.join(out, pdir)
            os.makedirs(pdir, exist_ok=True)
            fn = os.path.join(pdir, "%02d-%s.md" % (i, rel))
        else:
            fn = os.path.join(out, "%02d-%s.md" % (i, rel))
        with open(fn, "w", encoding="utf-8") as f:
            f.write("# %s\n\n%s\n" % (title, text))
        made.append((title, len(text)))
    print("[%s] 章节数=%d" % (book, len(made)))
    for t, n in made:
        print("   %-30s %6d 字符" % (t, n))


if __name__ == "__main__":
    build(sys.argv[1])