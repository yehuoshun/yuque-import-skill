#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fpb52 #109 《Go语言博客实践》(Go Blog In Action)：achun/Go-Blog-In-Action → 语雀导入树

仓库 = 8 个 ChapterNN.md 扁平文件（一个文件 = 一章 = 原书一页），无目录无图
"""
import os, re, json, shutil

SRC = "/home/admin/.openclaw/workspace/tmp/gbia-src"
OUT = "/home/admin/.openclaw/workspace/tmp/fpb109/build"

CH = {
    1: "选择 Martini 框架",
    2: "永远的MVC",
    3: "面向对象和并发",
    4: "服务器裸奔",
    5: "静态博客",
    6: "解析器与舞台剧",
    7: "解析器与ABNF",
    8: "Rivet",
}


def clean(s):
    s = s.strip().replace("\u3000", "")
    for a, b in [("/", "／"), ("*", "＊"), ("|", "｜"), (":", "："), ("?", "？"), ("`", "")]:
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def inline_refs(text):
    """引用式链接 → 行内链接（拆章/换渲染器后定义块会失效）"""
    defs = {}
    out = []
    for ln in text.split("\n"):
        m = re.match(r"^\s*\[([^\]]+)\]:\s*(\S+)(?:\s+[\"'(].*)?\s*$", ln)
        if m:
            defs[m.group(1).strip().lower()] = m.group(2).strip()
            continue
        out.append(ln)
    text = "\n".join(out)

    def rep(m):
        label, ref = m.group(1), (m.group(2) or m.group(1)).strip().lower()
        url = defs.get(ref)
        return "[%s](%s)" % (label, url) if url else m.group(0)
    return re.sub(r"\[([^\]]+)\]\[([^\]]*)\]", rep, text)


def demote_headings(text):
    """setext/ATX 一级标题 → ##，其余依次降一级（章节标题由文件名给）；跟围栏走"""
    lines = text.split("\n")
    out, fence = [], False
    for i, ln in enumerate(lines):
        s = ln.rstrip()
        if re.match(r"^\s*```", s):
            fence = not fence
            out.append(ln)
            continue
        if fence:
            out.append(ln)
            continue
        # setext：下一行是 === 或 ---（且当前行非空、不是列表/表格）
        nxt = lines[i + 1].rstrip() if i + 1 < len(lines) else ""
        if s.strip() and re.match(r"^={3,}$", nxt.strip()) and not re.match(r"^\s*([-*+|>#]|\d+\.)", s):
            out.append("## " + s.strip())
            continue
        if s.strip() and re.match(r"^-{3,}$", nxt.strip()) and not re.match(r"^\s*([-*+|>#]|\d+\.)", s):
            out.append("### " + s.strip())
            continue
        if re.match(r"^={3,}$", s.strip()) or re.match(r"^#{1,2}\s*$", s.strip()):
            continue                      # 已被上一条消费掉的下划线行 / 空标题
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            level = len(m.group(1)) + 1   # 1→2, 2→3 ...
            out.append("#" * min(level, 6) + " " + m.group(2).strip())
            continue
        out.append(ln)
    return "\n".join(out)


def convert(fn):
    body = open(os.path.join(SRC, fn), encoding="utf-8").read().replace("\r\n", "\n")
    body = inline_refs(body)
    body = demote_headings(body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"
    return body


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    rd = open(os.path.join(SRC, "README.md"), encoding="utf-8").read()
    rd = inline_refs(rd)
    # README 里的目录清单（与语雀 TOC 重复 + 全是锚点死链）→ 剔
    rd = re.sub(r"^\s*-\s*第\d+章.*$", "", rd, flags=re.M)
    rd = re.sub(r"^\s*-\s*第\d+节.*$", "", rd, flags=re.M)
    rd = re.sub(r"^\s*目录\s*$", "", rd, flags=re.M)
    rd = re.sub(r"^-{3,}\s*$", "", rd, flags=re.M)      # 分隔横线（也是 setext 下划线，先按目录位置清）
    rd = demote_headings(rd)
    rd = re.sub(r"\n{3,}", "\n\n", rd).strip()

    intro = """# 00-说明

**《Go语言博客实践》**（Go Blog In Action，作者：喻恒春 / achun）

- 源仓库：`achun/Go-Blog-In-Action` @ `d8e2120`（drinker 分支版本，最后提交 2017-06-15；Martini 版，老版本另见 master）
- 书单原链：`https://github.com/achun/Go-Blog-In-Action`
- 导入日期：2026-10-31

## 收录范围

仓库就是 **8 个 `ChapterNN.md`**（一章一篇，无子目录、无配图），按章落库为 8 篇根级文档
（`01-选择 Martini 框架` … `08-Rivet`，零填充前缀 = 阅读序）。

⚠️ 原书未完成：第 5 章《静态博客》作者自注「未完待续，穿插解析器部分」；
第 6/7 章是解析器专题的两次不同尝试（PEG 舞台剧 → ABNF → ABNFA）。

## 口径

- 一个文件 = 一章 = 一个文档（GitHub 上本书也是按章分页 + 章内锚点，不硬拆节）
- 标题由文件名给出（取自仓库 README 目录），正文里的 setext/ATX 一级标题统一降为 `##`，其余标题依次降一级
- 引用式链接（`[文字][1]` / `[文字][]` + 文末 `[1]: url` 定义块）**全部内联成行内链接**，定义块删除
- 仓库 README 的目录清单（`第N章/第N节` + 章内锚点）与语雀 TOC 重复且全是死锚点 → 不收

## 仓库 README 原文

%s
""" % rd
    open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8").write(intro)

    report = []
    for n, title in CH.items():
        fn = "Chapter%02d.md" % n
        body = convert(fn)
        f = os.path.join(OUT, "%02d-%s.md" % (n, clean(title)))
        open(f, "w", encoding="utf-8").write(body)
        report.append({"file": os.path.basename(f), "bytes": len(body.encode()),
                       "cjk": len(re.findall(r"[\u4e00-\u9fff]", body))})
    json.dump(report, open("/home/admin/.openclaw/workspace/tmp/fpb109/report.json", "w"),
              ensure_ascii=False, indent=1)
    for r in report:
        print("%-40s %6dB cjk=%d" % (r["file"], r["bytes"], r["cjk"]))


if __name__ == "__main__":
    main()