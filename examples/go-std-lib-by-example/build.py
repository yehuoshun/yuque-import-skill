#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fpb52 #102 《Go语言标准库》(polaris1119/The-Golang-Standard-Library-by-Example @ c466fcc) → 语雀 clean 目录。

GitBook 3.x 源仓：层级取自 SUMMARY.md（书未写完，SUMMARY 里大量「无链接」的章/节）
- README.md → 00-简介.md（剥作者二维码图）
- 每章一个 TITLE `第NN章 …`；`NN.0.md` → `00-本章导读.md`；`NN.M.md` → `NN.M 标题.md`
- 只导 SUMMARY 里**带链接**的节点；无链接（第11/12/14/17章、3.2/5.2-5.4/7.2-7.4/8.2-8.4/13.2/13.4/15.1 等）不建空壳
- 补：SUMMARY 未收录但仓库有正文的节（7.5 encoding/csv、8.5 archive/tar）也导
- 剥每篇尾部 `# 导航` 段；剥首 H1；文件名里 `/` → `／`
- 章内图片 `chapterNN/imgs/` 按章拷进对应章目录，交 rewrite 传 CDN 后再删
"""
import os, re, shutil

SRC = "/home/admin/.openclaw/workspace/tmp/fpb102-src"
DST = "/home/admin/.openclaw/workspace/tmp/fpb102"

CH_RE = re.compile(r"^\*\s+(?:\[(?P<t>.+?)\]\((?P<p>.+?)\)|(?P<t2>.+?))\s*$")
SEC_RE = re.compile(r"^\s+-\s+(?:(?P<num>\d+\.\d+)\s+)?(?:\[(?P<t>.+?)\]\((?P<p>.+?)\)|(?P<t2>.*?))\s*$")
NAV_RE = re.compile(r"^\s*#\s*导航\s*#?\s*$", re.M)


def clean_title(t):
    return t.rstrip("# ").strip()


def sane(name):
    return name.replace("/", "／")


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")


def body(path):
    t = open(path, encoding="utf-8").read()
    lines = t.split("\n")
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        if ln.startswith("# "):
            lines = lines[i + 1:]
        break
    t = "\n".join(lines)
    m = NAV_RE.search(t)
    if m:
        t = t[:m.start()]
    return t.strip() + "\n"


def main():
    if os.path.isdir(DST):
        shutil.rmtree(DST)
    os.makedirs(DST)

    readme = open(os.path.join(SRC, "README.md"), encoding="utf-8").read()
    readme = re.sub(r"!\[\]\(polarisxu-qrcode-small\.jpg\)\n?", "", readme)
    readme = re.sub(r"^\s*#\s*.*?#\s*$", "", readme, count=1, flags=re.M).lstrip("\n")
    write(os.path.join(DST, "00-简介.md"), readme)

    lines = open(os.path.join(SRC, "SUMMARY.md"), encoding="utf-8").read().split("\n")
    chapter_dir = None
    pend_title = None
    n_doc = 0
    missing = []
    for ln in lines:
        if not ln.strip():
            continue
        if ln.startswith("* "):
            m = CH_RE.match(ln)
            title = clean_title(m.group("t") or m.group("t2"))
            path = m.group("p")
            pend_title = title
            if path and re.match(r"chapter\d+", path):
                num = int(re.match(r"chapter(\d+)", path).group(1))
                ctitle = re.sub(r"^第.+?章\s*", "", title)
                chapter_dir = os.path.join(DST, sane("第%02d章 %s" % (num, ctitle)))
                os.makedirs(chapter_dir, exist_ok=True)
                write(os.path.join(chapter_dir, "00-本章导读.md"), body(os.path.join(SRC, path)))
                n_doc += 1
            else:
                chapter_dir = None
        elif ln.startswith(" ") or ln.startswith("\t"):
            m = SEC_RE.match(ln)
            if not m or not m.group("p") or not re.match(r"chapter\d+", m.group("p")):
                continue
            sp = m.group("p")
            if chapter_dir is None and pend_title:
                num = int(re.match(r"chapter(\d+)", sp).group(1))
                ctitle = re.sub(r"^第.+?章\s*", "", pend_title)
                chapter_dir = os.path.join(DST, sane("第%02d章 %s" % (num, ctitle)))
                os.makedirs(chapter_dir, exist_ok=True)
            if not os.path.exists(os.path.join(SRC, sp)):
                missing.append(sp)
                continue
            write(os.path.join(chapter_dir, sane("%s %s.md" % (m.group("num"), clean_title(m.group("t"))))),
                  body(os.path.join(SRC, sp)))
            n_doc += 1

    # 补：SUMMARY 未收录但仓库存在的节文件（7.5 / 8.5）
    for d in sorted(os.listdir(SRC)):
        m = re.match(r"chapter(\d+)$", d)
        if not m or not os.path.isdir(os.path.join(SRC, d)):
            continue
        num = int(m.group(1))
        hdir = next((os.path.join(DST, c) for c in os.listdir(DST)
                     if c.startswith("第%02d章" % num)), None)
        if not hdir:
            continue
        for fn in sorted(os.listdir(os.path.join(SRC, d))):
            mm = re.match(r"0*(\d+)\.0*(\d+)\.md$", fn)
            if not mm or mm.group(2) == "0":
                continue
            sec = "%s.%s" % (mm.group(1), mm.group(2))
            if any(x.startswith(sec + " ") for x in os.listdir(hdir)):
                continue
            src = os.path.join(SRC, d, fn)
            h1 = open(src, encoding="utf-8").readline().strip()
            stitle = re.sub(r"^#\s*\d+\.\d+\s*", "", h1).rstrip("# ").strip()
            write(os.path.join(hdir, sane("%s %s.md" % (sec, stitle))), body(src))
            n_doc += 1

    for d in os.listdir(SRC):
        if re.match(r"chapter\d+$", d) and os.path.isdir(os.path.join(SRC, d, "imgs")):
            num = int(d[7:])
            for cand in os.listdir(DST):
                if cand.startswith("第%02d章" % num):
                    shutil.copytree(os.path.join(SRC, d, "imgs"), os.path.join(DST, cand, "imgs"))

    print("[done] 文档 %d" % n_doc)
    if missing:
        print("[missing] SUMMARY 有链接但仓库无文件: %s" % ", ".join(missing))


if __name__ == "__main__":
    main()
