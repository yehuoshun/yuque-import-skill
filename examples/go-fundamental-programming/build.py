#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fpb52 #96《Go 编程基础》(Unknwon/go-fundamental-programming @3336687) → 语雀 clean 树

仓库极小：README.md + lectures/lecture1..15.md（课堂笔记，无图）+ lectures/*.go（6 个示例）
- 15 篇笔记 → 根级 `第NN课 <标题>.md`（零填充前缀，字典序即课时序）
- 6 个 .go  → `示例代码/<原名>.go`（导入器按扩展名包 ```go 围栏）
- README   → `00-说明.md`（剥掉指向 lectures/*.md 的相对链，保留站外视频/资料链）
"""
import os, re, shutil, sys

SRC = "/tmp/g96"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/g96-clean"

REL_LINK = re.compile(r"\[([^\]]+)\]\((lectures/[^)]+|\.?/?lecture\d+\.md)\)")
ANY_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def strip_rel_links(text):
    """仓库内相对链 → 纯文本（语雀里是死链）；站外链保留。"""
    def rep(m):
        title, url = m.group(1), m.group(2)
        if url.startswith(("http://", "https://")):
            return m.group(0)
        return title
    return ANY_LINK.sub(rep, text)


def build_lecture(n):
    raw = open(os.path.join(SRC, "lectures", "lecture%d.md" % n), encoding="utf-8").read()
    lines = raw.split("\n")
    # 1) 取 Setext 一级标题 = "第 N 课：标题"，并去掉标题块
    title = None
    out = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if title is None and ln.strip() and i + 1 < len(lines) and re.match(r"^=+\s*$", lines[i + 1]):
            title = ln.strip()
            i += 2
            continue
        out.append(ln)
        i += 1
    if title is None:
        title = "第 %d 课" % n
    text = "\n".join(out)
    # 2) 课程大纲里 tab 缩进的时间点 → 无序列表
    text = re.sub(r"(?m)^\t+\[(\d+:\d+)\] (.+)$", r"- `[\1]` \2", text)
    # 3) 相对链（上/下一课等）→ 纯文本
    text = strip_rel_links(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    title = re.sub(r"^第\s*(\d+)\s*课[：:]\s*", "", title).strip()
    return n, title, text


def build_readme():
    raw = open(os.path.join(SRC, "README.md"), encoding="utf-8").read()
    lines = raw.split("\n")
    # 剥 Setext 标题块
    out = []
    i = 0
    while i < len(lines):
        if lines[i].strip() and i + 1 < len(lines) and re.match(r"^=+\s*$", lines[i + 1]):
            i += 2
            continue
        out.append(lines[i])
        i += 1
    text = "\n".join(out)
    text = strip_rel_links(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    made = []
    for n in range(1, 16):
        num, title, body = build_lecture(n)
        # 标题里的 / 换全角，避免当目录分隔
        fname = "第%02d课 %s.md" % (num, title.replace("/", "／"))
        with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
            f.write("# 第 %d 课：%s\n\n%s\n" % (num, title, body))
        made.append(fname)
    os.makedirs(os.path.join(OUT, "示例代码"), exist_ok=True)
    for fn in sorted(os.listdir(os.path.join(SRC, "lectures"))):
        if fn.endswith(".go"):
            shutil.copy2(os.path.join(SRC, "lectures", fn), os.path.join(OUT, "示例代码", fn))
    with open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8") as f:
        f.write("# 说明\n\n" + build_readme() + "\n")
    print("docs:", len(made), "+ 说明 + go示例")
    for m in made:
        print("  ", m)


main()