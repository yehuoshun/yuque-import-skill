#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ZMQ 指南（anjuke/zguide-cn @ 91d94b7）→ 语雀导入树构建。

口径：开源项目（GitHub repo）。
- 5 章各建 TITLE 目录；章内按 ### 小节拆文档；章首导语落 00 导读。
- 章标题取 README 目录列表（源 chapter4.md 的 H2 漏了「第四章」）。
- chapter1.md 全文重复书首（标题/致谢/授权）→ 剥离，改由 00-说明.md 承载。
- 配图原是 GitHub raw 绝对外链 → 改写为 ../images/x.png，交 rewrite 脚本传 CDN。
"""
import os
import re
import shutil

SRC = "/home/admin/.openclaw/workspace/tmp/zguide-cn-91d94b7-clean"
OUT = "/home/admin/.openclaw/workspace/tmp/fpb083/build"
IMG_PREFIX = "https://github.com/anjuke/zguide-cn/raw/master/images/"

CH_TITLES = {
    1: "第一章 ZeroMQ基础",
    2: "第二章 ZeroMQ进阶",
    3: "第三章 高级请求-应答模式",
    4: "第四章 可靠的请求-应答模式",
    5: "第五章 高级发布-订阅模式",
}


def sanitize(t):
    return t.replace("/", "／").strip()


def split_sections(body_lines):
    intro, sections, cur_title, cur = [], [], None, []
    fence = False
    for ln in body_lines:
        s = ln.lstrip()
        if s.startswith("```") or s.startswith("~~~"):
            fence = not fence
            cur.append(ln)
            continue
        m = None if fence else re.match(r"^###\s+(.*\S)\s*$", ln)
        if m:
            if cur_title is None:
                intro = cur
            else:
                sections.append((cur_title, cur))
            cur_title = m.group(1).strip()
            cur = []
        else:
            cur.append(ln)
    if cur_title is None:
        intro = cur
    else:
        sections.append((cur_title, cur))
    return intro, sections


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(os.path.join(SRC, "images"), os.path.join(OUT, "images"))

    ch_list = "\n".join("- %s" % CH_TITLES[c] for c in range(1, 6))
    note = (
        "# ZMQ 指南（中文版）\n\n"
        "**作者**：Pieter Hintjens <ph@imatix.com>（iMatix CEO）\n"
        "**译者**：张吉 <jizhang@anjuke.com>（安居客 · 好租网工程师）\n"
        "**原文**：https://github.com/imatix/zguide/tree/v2.2\n"
        "**源仓库**：https://github.com/anjuke/zguide-cn @ 91d94b7\n\n"
        "> **NOTE**：本译本涵盖 2011 年 10 月的 ZeroMQ 稳定版（2.1.0 stable release）；"
        "读者仍可借此了解 ZMQ 的基本概念与哲学。\n\n---\n\n## 目录\n\n"
        + ch_list
        + "\n\n---\n\n本书译自 Pieter Hintjens 的 *ZeroMQ Guide*；"
        "此译本采用 [Creative Commons Attribution-ShareAlike 3.0 License]"
        "(http://creativecommons.org/licenses/by-sa/3.0/) 授权。\n"
    )
    open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8").write(note)

    total = 1
    for ch in range(1, 6):
        raw = open(os.path.join(SRC, "chapter%d.md" % ch), encoding="utf-8").read()
        raw = raw.replace(IMG_PREFIX, "../images/")
        lines = raw.split("\n")
        h2 = next(i for i, ln in enumerate(lines) if re.match(r"^##\s", ln))
        intro, sections = split_sections(lines[h2 + 1:])

        chdir = os.path.join(OUT, "%02d-%s" % (ch, sanitize(CH_TITLES[ch])))
        os.makedirs(chdir)

        intro_text = "\n".join(intro).strip()
        if intro_text:
            open(os.path.join(chdir, "%02d.00 本章导读.md" % ch),
                 "w", encoding="utf-8").write(intro_text + "\n")
            total += 1
        for i, (title, body) in enumerate(sections, 1):
            text = "\n".join(body).strip()
            assert text, "空小节 ch%d %s" % (ch, title)
            fn = "%02d.%02d %s.md" % (ch, i, sanitize(title))
            open(os.path.join(chdir, fn), "w", encoding="utf-8").write(text + "\n")
            total += 1
        print("ch%d: %d sections intro=%s" % (ch, len(sections), bool(intro_text)))
    print("构建完成 文档数:", total)


if __name__ == "__main__":
    main()
