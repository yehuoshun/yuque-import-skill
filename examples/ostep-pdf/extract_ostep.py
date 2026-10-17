#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OSTEP 章节 PDF → Markdown（跳过矢量图，保留图注文字）。

排版特征（v1.10 PDF）：
  - 正文 9.0pt URWPalladioL-Roma；粗体 -Bold；斜体 -Ital；等宽 NimbusMonL-Regu
  - 小节标题 10.9pt（"4.1 ..."）；首页章标题 14.3pt + 章号 20.7pt
  - 段落首行缩进（x≈70），续行 x≈58 → 用缩进判断段落边界
  - 页眉（"2 THE ABSTRACTION: THE PROCESS"）/页码（纯数字）在 y<55 或 y>H-55
  - CRUX/TIP/ASIDE 标题行居中（x>120）且全大写
"""
import json
import os
import re
import sys

import pymupdf

WORK = "/home/admin/.openclaw/workspace/tmp/ostep"
WORDS = set()
try:
    with open(os.path.join(WORK, "words.txt"), encoding="utf-8", errors="replace") as f:
        WORDS = {l.strip().lower() for l in f if l.strip()}
except OSError:
    pass


def dehyphen(prev_md, next_md):
    """行尾连字符处理：双侧都是完整词 → 复合词保留 '-'；否则当排版断词删掉。"""
    m = re.search(r"([A-Za-z]{2,})-+$", prev_md)
    m2 = re.match(r"([A-Za-z]+)", next_md)
    if m and m2:
        left, right = m.group(1), m2.group(1)
        if len(left) >= 3 and left.lower() in WORDS and right.lower() in WORDS:
            return prev_md + next_md
    if m:
        return prev_md[:m.start(1)] + m.group(1) + next_md
    return prev_md.rstrip("-") + next_md
LIG = {"\ufb01": "fi", "\ufb02": "fl", "\ufb00": "ff", "\ufb03": "ffi", "\ufb04": "ffl",
       "\ufb05": "ft", "\ufb06": "st"}


def clean(t):
    for k, v in LIG.items():
        t = t.replace(k, v)
    t = (t.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"')
          .replace("\u201d", '"').replace("\u2010", "-").replace("\u2011", "-")
          .replace("\u2013", "-").replace("\u2014", "-")
          .replace("\u2026", "...").replace("\u00a0", " ").replace("\uf8ff", ""))
    return t


def is_mono(font):
    f = font.lower()
    return any(k in f for k in ("nimbusmon", "courier", "cmtt", "mono"))


def render_line(spans):
    out = []
    for s in spans:
        t = clean(s["text"])
        if not t.strip():
            if out:
                out.append(" ")
            continue
        f = s["font"]
        core = t.strip()
        if is_mono(f):
            out.append("`%s`" % core)
        elif "Bold" in f:
            out.append("**%s**" % core)
        elif "Ital" in f:
            out.append("*%s*" % core)
        else:
            out.append(core)
        out.append(" ")
    txt = "".join(out)
    txt = re.sub(r"\s+([,.;:!?)])", r"\1", txt)
    txt = re.sub(r"\(\s+", "(", txt)
    # 相邻同类强调 span 合并（"**time** **sharing**" → "**time sharing**"）
    for _ in range(4):
        new = re.sub(r"\*\*([^*]+)\*\*\s*\*\*([^*]+)\*\*", r"**\1 \2**", txt)
        new = re.sub(r"(?<![*\w])\*([^*]+)\*\s*\*([^*]+)\*(?![*\w])", r"*\1 \2*", new)
        new = re.sub(r"`([^`]+)`\s*`([^`]+)`", r"`\1 \2`", new)
        if new == txt:
            break
        txt = new
    return re.sub(r"[ ]{2,}", " ", txt).strip()


def load_lines(doc):
    lines = []
    for pno in range(doc.page_count):
        page = doc[pno]
        H = page.rect.height
        for b in page.get_text("dict")["blocks"]:
            if b["type"] != 0:
                continue
            for l in b["lines"]:
                spans = [s for s in l["spans"] if s["text"]]
                if not spans:
                    continue
                size = max(round(s["size"], 1) for s in spans)
                lines.append({
                    "page": pno, "y": l["bbox"][1], "x": l["bbox"][0], "H": H,
                    "size": size,
                    "mono": all(is_mono(s["font"]) for s in spans),
                    "text": clean("".join(s["text"] for s in spans)),
                    "md": render_line(spans),
                })
    return lines


def strip_headers(lines):
    out = []
    for L in lines:
        t = L["text"].strip()
        top, bot = L["y"] < 75, L["y"] > L["H"] - 78
        # 页码 / 章号装饰（短数字：顶部/底部/居中）
        if re.fullmatch(r"\d{1,3}", t) and (top or bot or L["x"] > 140):
            continue
        if L["size"] < 11.5 and (top or bot):
            if t.isupper() and re.search(r"[A-Z]{4,}", t):
                continue
            if re.fullmatch(r"\d+\s+\S.*", t) and t.upper() == t:
                continue
        out.append(L)
    return out


def to_blocks(lines):
    """行 → 块序列：h1/h2/代码/特殊框标题/普通段落"""
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        L = lines[i]
        t = L["text"].strip()
        if not t:
            i += 1
            continue
        # 标题
        if L["size"] >= 13 and not L["mono"]:
            blocks.append(("h1", L["md"]))
            i += 1
            continue
        if L["size"] >= 10.3 and not L["mono"]:
            blocks.append(("h2", L["md"]))
            i += 1
            continue
        # 代码块（连续等宽行）
        if L["mono"]:
            buf = []
            while i < n and lines[i]["mono"]:
                buf.append(lines[i]["text"].rstrip())
                i += 1
            blocks.append(("code", "\n".join(buf)))
            continue
        # 居中的全大写特殊框标题（CRUX / TIP / ASIDE）
        if L["x"] > 118 and t.isupper() and len(t) > 7:
            head = [t.rstrip(":")]
            i += 1
            while i < n and lines[i]["x"] > 85 and lines[i]["text"].strip().isupper():
                head.append(lines[i]["text"].strip().rstrip(":"))
                i += 1
            blocks.append(("asidelabel", " ".join(head)))
            continue
        # 普通段落（相对缩进 / 句末标点判断边界）
        cur = L
        cur_x = L["x"]
        i += 1
        while i < n:
            N = lines[i]
            nt = N["text"].strip()
            if not nt or N["mono"] or N["size"] >= 10.3 or (N["x"] > 118 and nt.isupper()):
                break
            prev = cur["md"].rstrip()
            prev_end = re.search(r'[.!?:]["\')\]]?$', cur["text"].rstrip())
            page_break = N["page"] != cur["page"]
            new_para = (N["x"] > cur_x + 6 or prev_end) and not (page_break and not prev_end)
            if new_para:
                break
            if prev.endswith("-") and not prev.endswith("--"):
                cur = dict(cur, md=dehyphen(prev, N["md"]),
                           text=cur["text"].rstrip()[:-1] + nt)
            else:
                cur = dict(cur, md=(prev + " " + N["md"]).strip(),
                           text=cur["text"].rstrip() + " " + nt)
            cur_x = N["x"]
            i += 1
        blocks.append(("p", cur["md"]))
    return blocks


def polish(md):
    """段落级收尾：跨行相邻强调合并 + 空格清理。"""
    for _ in range(4):
        new = re.sub(r"\*\*([^*]+)\*\*\s*\*\*([^*]+)\*\*", r"**\1 \2**", md)
        new = re.sub(r"`([^`]+)`\s*`([^`]+)`", r"`\1 \2`", new)
        if new == md:
            break
        md = new
    md = re.sub(r"\s+([,.;:!?)])", r"\1", md)
    md = re.sub(r"\(\(([^()]*)\)\)", r"(\1)", md)
    # 矢量图内的单字母标签混入图注行（"C Figure 7.1: ..."）→ 剥
    md = re.sub(r"^[A-Z] (?=Figure )", "", md)
    md = re.sub(r"\s{2,}", " ", md)
    return md.strip()


def blocks_to_md(blocks):
    out = []
    for kind, val in blocks:
        if kind == "h1":
            out.append("# " + val)
        elif kind == "h2":
            out.append("## " + val)
        elif kind == "code":
            out.append("```\n" + val + "\n```")
        elif kind == "asidelabel":
            out.append("> **%s**" % val)
        else:
            # 丢弃矢量图内的孤立短标签（"0"/"B"/"Time" 这类零散行，图本就没导）
            if re.fullmatch(r"[A-Za-z0-9\-]{1,3}", val.strip()):
                continue
            out.append(polish(val))
    return "\n\n".join(out).strip() + "\n"


def main():
    plan = json.load(open(os.path.join(WORK, "plan.json"), encoding="utf-8"))
    only = sys.argv[1] if len(sys.argv) > 1 else None
    total = 0
    for item in plan:
        if only and only not in item["pdf"]:
            continue
        pdf = os.path.join(WORK, "pdf", item["pdf"])
        doc = pymupdf.open(pdf)
        lines = strip_headers(load_lines(doc))
        md = blocks_to_md(to_blocks(lines))
        # 章标题（首页大标题）加回文件名标题行
        outdir = os.path.join(WORK, "clean", item["part"])
        os.makedirs(outdir, exist_ok=True)
        path = os.path.join(outdir, item["out"])
        open(path, "w", encoding="utf-8").write(md)
        total += 1
        print("%-52s %6d chars  (%d pages)" % (os.path.join(item["part"], item["out"]), len(md), doc.page_count))
    print("转换:", total)


if __name__ == "__main__":
    main()