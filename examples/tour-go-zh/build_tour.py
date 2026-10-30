#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fpb52 #106 Go 指南（A Tour of Go 中文版）：Go-zh/tour 仓库 .article → 语雀导入树

源站 tour.go-zh.org 本机 502、web.archive.org 直连 000（被墙）
→ 吃源仓库 content/*.article（.play 内联展平成 go 代码块）
"""
import os, re, sys, json, shutil

SRC = "/home/admin/.openclaw/workspace/tmp/tour-src/content"
OUT = "/home/admin/.openclaw/workspace/tmp/fpb106/build"

MODULES = ["welcome", "basics", "flowcontrol", "moretypes", "methods", "concurrency"]


def clean_title(t):
    t = t.strip()
    t = t.replace("`", "")
    for a, b in [("/", "／"), ("*", "＊"), ("|", "｜"), (":", "："), ("?", "？"),
                 ('"', "”"), ("<", "‹"), (">", "›")]:
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


def org_links(s):
    """[[url][text]] → [text](url)；javascript:/相对地址 → 纯文本"""
    def rep(m):
        url, text = m.group(1), m.group(2)
        if url.startswith(("http://", "https://")):
            return "[%s](%s)" % (text, url)
        return text
    return re.sub(r"\[\[([^\]]*)\]\[([^\]]*)\]\]", rep, s)


def code_of(spec):
    path = os.path.join(SRC, spec)
    if not os.path.exists(path):
        return "```go\n// 源码缺失: %s\n```" % spec
    body = open(path, encoding="utf-8").read().rstrip("\n")
    # 剔构建约束标记（tour 工具用它把示例排除在编译之外，展示层不保留）
    lines = [ln for ln in body.split("\n") if not re.match(r"^// \+build .*\bOMIT\b", ln)]
    while lines and not lines[0].strip():
        lines.pop(0)
    body = "\n".join(lines)
    return "```go\n%s\n```" % body


def convert_section(body_lines):
    out, buf = [], []

    def flush():
        if buf:
            out.append("\n".join(buf).strip("\n"))
            buf.clear()

    for line in body_lines:
        if line.startswith("#appengine:"):
            continue
        m = re.match(r"^\.(play|code)\s+(\S+)\s*$", line)
        if m:
            flush()
            out.append(code_of(m.group(2)))
            continue
        m = re.match(r"^\.image\s+(\S+)", line)
        if m:
            flush()
            name = os.path.basename(m.group(1))
            out.append("![%s](%s)" % (name, name))
            continue
        buf.append(org_links(line))
    flush()
    txt = "\n\n".join(x for x in out if x.strip())
    txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
    return txt


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    report = []
    total = 0
    for mi, mod in enumerate(MODULES, 1):
        path = os.path.join(SRC, mod + ".article")
        lines = open(path, encoding="utf-8").read().split("\n")
        # 模块头：首行标题 + 到第一个 "* " 前的描述
        title = lines[0].strip()
        # 切 section
        secs = []
        cur = None
        for line in lines[1:]:
            m = re.match(r"^\*\s+(.*)$", line)
            if m:
                if cur:
                    secs.append(cur)
                cur = {"title": m.group(1).strip(), "body": []}
            elif cur is not None:
                cur["body"].append(line)
        if cur:
            secs.append(cur)

        dirname = "%02d-%s" % (mi, clean_title(title))
        d = os.path.join(OUT, dirname)
        os.makedirs(d)
        seen = {}
        for si, sec in enumerate(secs, 1):
            body = convert_section(sec["body"])
            if not body.strip():
                print("  empty section skipped: %s / %s" % (title, sec["title"]))
                continue
            # 图片：本模块用到才拷
            for img in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body):
                src = os.path.join(SRC, "img", img)
                if os.path.exists(src):
                    shutil.copy(src, os.path.join(d, img))
            st = clean_title(sec["title"])
            seen[st] = seen.get(st, 0) + 1
            if seen[st] > 1:            # 同父重名（巡回课重复出现同名节）
                st = "%s（续）" % st
            fn = "%02d-%s.md" % (si, st)
            open(os.path.join(d, fn), "w", encoding="utf-8").write(body + "\n")
            report.append({"module": title, "dir": dirname, "idx": si, "title": st,
                           "file": os.path.join(dirname, fn), "bytes": len(body.encode())})
            total += 1
        print("%s → %d 节" % (dirname, len(secs)))

    intro = """# 00-说明

**《Go 指南》中文版（A Tour of Go）**

- 源仓库：`Go-zh/tour` @ `4a8e183`（Go 作者组编写，Go-zh 小组翻译）
- 书单原链：`https://tour.go-zh.org/list`（Wayback 2025-12-10 快照）
- 导入日期：2026-10-31

## 为什么吃仓库而不是抓站

源站 `tour.go-zh.org` 本机直连返回 **502**，`web.archive.org` 直连 **000（被墙）**；
仓库 `content/*.article` 就是站点渲染的唯一真源（站点由 `gotour` 把 `.article` 渲染成页面），
故直接取仓库内容，逐节（`* 标题`）拆成文档，`.play xxx.go` 指令内联展平为 ```go 代码块。

## 收录范围

6 个模块共 **98 节**（welcome 3 / basics 17 / flowcontrol 14 / moretypes 26+1 / methods 26 / concurrency 11）。

⚠️ 仓库 README 自述「已弃用，新版移至 website 代码仓库」（最后提交 2023-03-06）；
源站又不可达，无法逐节与线上比对。内容为 Go 官方指南中文全译本，若干 `.play` 示例的
运行按钮在语雀不可用（代码本身完整可读）。

## 口径

- `#appengine:` 前缀行是「Google App Engine 运行环境」专用注释，线上非 AppEngine 视图不显示 → 已剔
- `[[url][文字]]`（Org 链接）→ Markdown 链接；`javascript:…` 伪协议（页面高亮/翻页提示）→ 纯文本
- `.image` 指令 → 图片引用，图从仓库 `content/img/` 拷出后传语雀 CDN
- 每节一个文档，模块用 TITLE 目录，零填充序号保证字典序即书序
"""
    open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8").write(intro)
    json.dump(report, open("/home/admin/.openclaw/workspace/tmp/fpb106/report.json", "w"),
              ensure_ascii=False, indent=1)
    print("docs:", total)


if __name__ == "__main__":
    main()