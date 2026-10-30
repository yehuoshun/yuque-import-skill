#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#116 Real World Haskell 中文版 (huangzworks/real-world-haskell-cn @ f67b07d)
Sphinx/reST 书稿仓 → yuque_rst_convert.py 转 md。
- 先剥 rst 注释（`.. xxx` 无 ``::`` 的行 + 其缩进续行），否则会留 --> 垃圾（chp/12）。
- 章 chp/N.rst → 根级 NN-<H1>.md（零填充）；index → 00-说明；convention → 90-翻译约定。
- 图 image/（引用 /image/x 与 ../image/x）→ 拷到导入根 image/ 后本地化传 CDN。
- code/（Haskell 源码，已由 literalinclude 内联）不入库。
"""
import os, re, sys, glob, shutil, subprocess

CLEAN = "real-world-haskell-cn-f67b07d-clean"
PREP = "rst_prep"
OUT = "build"
CONV = "/home/admin/.openclaw/workspace/code/yuque-import-skill/scripts/yuque_rst_convert.py"


def strip_rst_comments(lines):
    out, i, n = [], 0, len(lines)
    while i < n:
        ln = lines[i]
        if re.match(r"^\.\.[ \t]", ln) and "::" not in ln:
            i += 1
            while i < n:
                s = lines[i]
                if s.strip() == "":
                    j = i + 1
                    if j < n and lines[j].startswith((" ", "\t")):
                        i += 1
                        continue
                    break
                if s.startswith((" ", "\t")):
                    i += 1
                    continue
                break
            continue
        out.append(ln)
        i += 1
    return out


def drop_arrow_comments(text):
    """去掉 rst 注释残留行（行尾 ' -->' 且无 CJK，且在代码围栏之外）。"""
    out, infence = [], False
    for ln in text.split("\n"):
        if ln.startswith("```"):
            infence = not infence
            out.append(ln)
            continue
        if (not infence) and ln.rstrip().endswith("-->") and not re.search(r"[\u4e00-\u9fff]", ln):
            continue
        out.append(ln)
    return "\n".join(out)


def main():
    for d in (PREP, OUT):
        if os.path.exists(d):
            shutil.rmtree(d)
    # 1) 预处理：只保留 chp/*.rst + index.rst + convention.rst，剥注释
    os.makedirs(os.path.join(PREP, "chp"))
    targets = [("index.rst", "index.rst"), ("convention.rst", "convention.rst")]
    for src, dst in targets:
        t = open(os.path.join(CLEAN, src), encoding="utf-8").read().split("\n")
        open(os.path.join(PREP, dst), "w", encoding="utf-8").write("\n".join(strip_rst_comments(t)))
    for p in glob.glob(os.path.join(CLEAN, "chp", "*.rst")):
        t = open(p, encoding="utf-8").read().split("\n")
        open(os.path.join(PREP, "chp", os.path.basename(p)), "w", encoding="utf-8").write("\n".join(strip_rst_comments(t)))
    # 2) 转换
    subprocess.run([sys.executable, CONV, "--src", PREP, "--out", OUT], check=True)
    # 3) 重组：章 → 根级 NN-<title>.md
    def chapter_no(fn):
        return int(re.search(r"(\d+)", os.path.basename(fn)).group(1))
    for md in sorted(glob.glob(os.path.join(OUT, "chp", "*.md")), key=chapter_no):
        no = chapter_no(md)
        lines = open(md, encoding="utf-8").read().split("\n")
        title = None
        for ln in lines:
            if ln.startswith("# "):
                title = ln[2:].strip()
                break
        if not title:
            title = f"第{no}章"
        title = title.replace("/", "／")
        body = "\n".join(lines)
        body = drop_arrow_comments(body)
        name = f"{no:02d}-{title}.md"
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(body.strip() + "\n")
        print(f"  {no:02d} <- {md}")
    shutil.rmtree(os.path.join(OUT, "chp"))
    # index → 00-说明
    idx = open(os.path.join(OUT, "index.md"), encoding="utf-8").read().split("\n")
    idx = [ln for ln in idx if ln.strip() not in ("## 翻译约定",)]
    open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8").write(
        "> 来源：https://github.com/huangzworks/real-world-haskell-cn @ f67b07d ｜ "
        "《Real World Haskell》简体中文翻译版（原著 http://book.realworldhaskell.org/ ）｜ "
        "Sphinx/reST 书稿转换；正文一章一篇（第 1–16、18–28 章，第 17 章未译）。\n\n"
        + "\n".join(idx).strip() + "\n")
    os.remove(os.path.join(OUT, "index.md"))
    if os.path.exists(os.path.join(OUT, "README.md")):
        os.remove(os.path.join(OUT, "README.md"))
    cv = open(os.path.join(OUT, "convention.md"), encoding="utf-8").read()
    # 剥首行 H1（= 翻译约定）
    cv = re.sub(r"^#\s+.*\n", "", cv, count=1)
    open(os.path.join(OUT, "90-翻译约定.md"), "w", encoding="utf-8").write(cv.strip() + "\n")
    os.remove(os.path.join(OUT, "convention.md"))
    # 4) 图
    shutil.copytree(os.path.join(CLEAN, "image"), os.path.join(OUT, "image"))
    for md in glob.glob(os.path.join(OUT, "*.md")):
        t = open(md, encoding="utf-8").read()
        t = t.replace("](/image/", "](image/").replace("](../image/", "](image/")
        open(md, "w", encoding="utf-8").write(t)
    print("done")


if __name__ == "__main__":
    main()
