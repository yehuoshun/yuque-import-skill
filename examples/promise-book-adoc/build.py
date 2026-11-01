#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fpb52 #166 JavaScript Promise迷你书（中文版）→ 语雀导入树（2026-11-01）

源：liubin/promises-book @ 930f798（AsciiDoc 书稿：index.adoc 主控 + include:: 拼装）
口径：开源项目；复用 examples/puppet-cookbook/adoc-build.py 的 AsciiDoc→md 转换器
结构：00-说明 + 00-前言（Ch0）+ 4 章目录（Chapter.1~4，章内逐节一篇）
      + 05-Promises API Reference + 06-用語集 + 07-参考网站 + 08-关于作者与译者
      （Appendix-Note 未进 index.adoc 发布面 → 不收；图 14 张 → CDN）
"""
import os, re, sys, shutil, importlib.util

SRC = "/home/admin/.openclaw/workspace/tmp/fpb166-src"
OUT = "/home/admin/.openclaw/workspace/tmp/fpb166-promise-book/site"
EX = "/home/admin/.openclaw/workspace/code/yuque-import-skill/examples/puppet-cookbook/adoc-build.py"

spec = importlib.util.spec_from_file_location("adocbuild", EX)
ab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ab)

CHAPTERS = [
    ("Ch1_WhatsPromises", "01-Chapter.1 什么是Promise",
     ["what-is-promise.adoc", "promise-overview.adoc", "writing-promises.adoc"]),
    ("Ch2_HowToWrite", "02-Chapter.2 实战Promise",
     ["promise-resolve.adoc", "promise-reject.adoc", "column-promise-resolve.adoc",
      "promise-then.adoc", "promise-catch.adoc", "then-return-new-promise.adoc",
      "promise-and-array.adoc", "promise-all.adoc", "promise-race.adoc",
      "onrejected-or-catch.adoc"]),
    ("Ch3_Testing", "03-Chapter.3 Promise测试",
     ["basic-tests.adoc", "mocha-promise.adoc", "controllable-tests.adoc"]),
    ("Ch4_AdvancedPromises", "04-Chapter.4 Advanced",
     ["promise-library.adoc", "resolve-thenable.adoc", "not-throw-use-reject.adoc",
      "deferred-promise.adoc", "race-delay-timeout.adoc", "promise-done.adoc",
      "promise-chain.adoc", "promise-sequence.adoc"]),
]
SINGLES = [
    ("Ch0_Introduction/readme.adoc", "00-前言.md"),
    ("Appendix-Reference/readme.adoc", "05-Promises API Reference.md"),
    ("Appendix-Glossary/glossary.adoc", "06-用語集.md"),
    ("Appendix-Glossary/resource-link.adoc", "07-参考网站.md"),
    ("Appendix-Glossary/about-author.adoc", "08-关于作者与译者.md"),
]

NOISE = re.compile(r"^:([a-z][a-z0-9_-]*):\s*(.*)$")


def shift(t):
    """标题整体降一级（Conv：'='→#, '=='→#, '==='→## 所以先加一层）"""
    return re.sub(r"^(=+)(\s+)(.*)$", lambda m: "=" * (len(m.group(1)) + 1) + " " + m.group(3), t, flags=re.M)


def img_fix(ln):
    def sub(m):
        src = m.group(1)
        parts = [p.strip().strip('"') for p in m.group(2).split(',')]
        alt = parts[0] if parts else ''
        link = ''
        for p in parts:
            if p.startswith('link='):
                link = p[5:].strip().strip('"')
        if src.startswith(('http://', 'https://')):
            img = f'![{alt}]({src})'
            return f'[{img}]({link})' if link else img
        return f'image::{src}[{alt}]'
    return re.sub(r'(?<!:)image:(?!:)(\S+?)\[([^\]]*)\]', sub, ln)


def clean(t):
    lines = []
    in_block = False
    i = 0
    src = t.split("\n")
    while i < len(src):
        ln = src[i]
        s = ln.strip()
        if re.match(r"^-{4,}$", s) or re.match(r"^\.{4,}$", s):
            in_block = not in_block
            lines.append(ln)
            i += 1
            continue
        if in_block:
            lines.append(ln)
            i += 1
            continue
        if NOISE.match(s):
            i += 1
            continue
        if s in ("++++", "'''") or re.match(r"^(ifeval|endif)::.*$", s):
            i += 1
            continue
        if re.match(r'^\[role[^\]]*\]$', s):
            i += 1
            continue
        # 定义列表 Term:: + 缩进定义
        m = re.match(r"^(\S.*?)::\s*$", ln.rstrip())
        if m and not ln.startswith((" ", "\t")):
            term = m.group(1).strip()
            body = []
            i += 1
            while i < len(src) and (not src[i].strip() or re.match(r"^\s+\S", src[i])):
                if src[i].strip():
                    body.append(src[i].strip())
                i += 1
            lines.append("- **%s**" % term)
            for b in body:
                lines.append("  " + b)
            continue
        lines.append(img_fix(ln))
        i += 1
    return "\n".join(lines)


def conv_file(rel, out_md):
    path = os.path.join(SRC, rel)
    raw = open(path, encoding="utf-8-sig").read()
    body = ab.convert(shift(clean(raw)))
    # 剥首个标题（= 文档名）
    lines = body.split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    body = "\n".join(lines).strip() + "\n"
    # 图片：按源文件目录解析相对路径，收进 site/_imgs
    sd = os.path.dirname(path)
    md_dir = os.path.dirname(os.path.join(OUT, out_md))
    body = ab.replace_images(body, sd, md_dir)
    return body


def title_of(rel):
    raw = open(os.path.join(SRC, rel), encoding="utf-8-sig").read()
    for ln in raw.split("\n"):
        m = re.match(r"^=+\s+(.*)$", ln.strip())
        if m:
            return m.group(1).strip()
    return os.path.basename(rel)


def main():
    ab.OUT = OUT
    ab.ATTRS = {"bookversion": ""}
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    # 00-说明
    open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8").write(
        "# JavaScript Promise迷你书（中文版）\n\n"
        "- 原著：azu《JavaScript Promiseの本》（日文）\n"
        "- 翻译：liubin、kaku、honnkyou\n"
        "- 许可：Creative Commons Attribution-NonCommercial\n"
        "- 源仓库：https://github.com/liubin/promises-book\n"
        "- 在线版：http://liubin.org/promises-book/\n\n"
        "本库为源仓库 AsciiDoc 书稿的 Markdown 化导入：前言 + 4 章正文 + API 参考 + 术语集/参考网站/作者译者。\n"
        "（源仓库 Appendix-Note/ 未在 index.adoc 发布面内，未收录。）\n")

    for rel, dst in SINGLES:
        body = conv_file(rel, dst)
        open(os.path.join(OUT, dst), "w", encoding="utf-8").write(body)
        print(dst, len(body))

    for dirname, chdir, files in CHAPTERS:
        os.makedirs(os.path.join(OUT, chdir), exist_ok=True)
        for i, f in enumerate(files, 1):
            name = title_of(os.path.join(dirname, f))
            for a, b in (("/", "／"), (":", "："), ("?", "？"), ("*", "＊"),
                         ("\\", "＼"), ("<", "＜"), (">", "＞"), ("|", "｜")):
                name = name.replace(a, b)
            dst = f"{chdir}/{i:02d}-{name}.md"
            body = conv_file(os.path.join(dirname, f), dst)
            open(os.path.join(OUT, dst), "w", encoding="utf-8").write(body)
            print(dst, len(body))

    docs = sum(1 for r, _, fs in os.walk(OUT) for f in fs if f.endswith(".md"))
    dirs = sum(len(ds) for _, ds, _ in os.walk(OUT))
    print(f"[build] 文档 {docs} / 目录 {dirs} / 节点 {docs+dirs}")


if __name__ == "__main__":
    main()