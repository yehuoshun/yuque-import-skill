#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Elixir School 中文（elixirschool.com/zh-hans）→ 语雀导入树。

口径：开源项目（源仓库 elixirschool/elixirschool 的 lessons/zh-hans/*.md 为准；站点由它渲染）。
发布面/顺序 = 站点侧栏实际列出的 8 个分区 47 篇（仓库里的 misc/distillery.md 站点未发布且页面 500，不收）。
- frontmatter `%{ version, title, excerpt }` → 取 title 作文档名，excerpt 作提示块
- 4 空格缩进代码块 → 围栏（仅当首行不是缩进列表项，否则是嵌套列表）
- `/images/x.png` → `../images/x.png`（拷进 build/images，随后传 CDN 再删）
- `/zh-hans/lessons/...` 内链 + `#锚点` → 纯文字；`//host` → `https://host`
"""
import os, re, shutil

SRC = "/home/admin/.openclaw/workspace/tmp/fpb088-src"
OUT = "/home/admin/.openclaw/workspace/tmp/fpb088/build"

SECTIONS = [
    ("01-Basics（基础）", "basics", [
        "basics", "collections", "enum", "pattern_matching", "control_structures",
        "functions", "pipe_operator", "modules", "mix", "sigils", "documentation",
        "comprehensions", "strings", "date_time", "iex_helpers"]),
    ("02-Intermediate（中级）", "intermediate", [
        "mix_tasks", "erlang", "error_handling", "escripts", "concurrency"]),
    ("03-Advanced（高级）", "advanced", [
        "otp_concurrency", "otp_supervisors", "otp_distribution", "metaprogramming",
        "umbrella_projects", "typespec", "behaviours", "protocols"]),
    ("04-Testing（测试）", "testing", ["basics", "bypass", "mox", "stream_data"]),
    ("05-Data Processing（数据处理）", "data_processing", ["genstage"]),
    ("06-Ecto", "ecto", ["basics", "changesets", "associations", "querying_basics"]),
    ("07-Storage（存储）", "storage", ["ets", "mnesia"]),
    ("08-Miscellaneous（杂项）", "misc", [
        "benchee", "plug", "eex", "debugging", "nerves", "guardian", "poolboy",
        "nimble_publisher"]),
]

FM = re.compile(r"^%\{\s*(.*?)\n\}\s*\n---\s*\n", re.S)

def parse(path):
    raw = open(path, encoding="utf-8").read()
    m = FM.match(raw)
    fm, body = (m.group(1), raw[m.end():]) if m else ("", raw)
    tm = re.search(r'title:\s*"([^"]*)"', fm)
    em = re.search(r'excerpt:\s*"""\s*(.*?)\s*"""', fm, re.S)
    return (tm.group(1).strip() if tm else ""), (em.group(1).strip() if em else ""), body

def convert_indented(body):
    lines = body.split("\n")
    out, fence, i = [], False, 0
    while i < len(lines):
        ln = lines[i]
        if ln.lstrip().startswith("```"):
            fence = not fence
            out.append(ln); i += 1; continue
        if not fence and re.match(r"^(    |\t)\S", ln) and not re.match(r"^(    |\t)([-*+]|\d+\.)\s", ln):
            buf = []
            while i < len(lines) and (re.match(r"^(    |\t)", lines[i]) or
                                      (lines[i].strip() == "" and i + 1 < len(lines) and re.match(r"^(    |\t)", lines[i + 1]))):
                buf.append(lines[i][4:] if lines[i].startswith("    ") else lines[i].lstrip("\t"))
                i += 1
            out.append("```")
            out.extend(buf)
            out.append("```")
            continue
        out.append(ln); i += 1
    return "\n".join(out)

LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")

def fix_links(text):
    def rep(m):
        t, h = m.group(1), m.group(2)
        if h.startswith("/zh-hans/lessons") or h.startswith("#"):
            return t                                  # 站内死链/页内锚点 → 纯文字
        if h.startswith("//"):
            return "[%s](https:%s)" % (t, h)
        if h.startswith("/images/"):
            return "[%s](../images/%s)" % (t, os.path.basename(h))
        return m.group(0)
    return LINK.sub(rep, text)

def safe(name):
    return name.replace("/", "／").replace('"', "").strip()

if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)
used_imgs = set()

note = (
    "# Elixir School（中文）\n\n"
    "**来源**：https://github.com/elixirschool/elixirschool @ 4e5bea2 ｜ `lessons/zh-hans/`（站点 https://elixirschool.com/zh-hans 由本仓库渲染）\n"
    "**原著**：Elixir School（Elixir 社区课程，MIT/Apache 授权）\n"
    "**范围**：站点侧栏实际发布的 8 个分区 47 篇（Basics 15 / Intermediate 5 / Advanced 8 / Testing 4 / Data Processing 1 / Ecto 4 / Storage 2 / Miscellaneous 8）；"
    "仓库内 `misc/distillery.md` 站点未发布（页面 500），未收。\n"
    "**导入日期**：2026-10-30\n"
)
open(os.path.join(OUT, "00-说明.md"), "w", encoding="utf-8").write(note)

for dname, secdir, slugs in SECTIONS:
    d = os.path.join(OUT, dname)
    os.makedirs(d)
    for j, slug in enumerate(slugs, 1):
        p = os.path.join(SRC, "lessons", "zh-hans", secdir, slug + ".md")
        title, excerpt, body = parse(p)
        assert title, p
        body = convert_indented(body)
        body = fix_links(body)
        body = re.sub(r"(?m)^ {1,3}(```)", r"\1", body)   # 围栏缩进归零（1~3 空格合法但统一更稳）
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        head = "# %s\n\n" % title + ("> %s\n\n" % excerpt.replace("\n", " ") if excerpt else "")
        fn = safe("%02d-%s.md" % (j, title))
        open(os.path.join(d, fn), "w", encoding="utf-8").write(head + body + "\n")
        for im in re.findall(r"\.\./images/([^)\s]+)", body):
            used_imgs.add(im)
        print("[%s] %s" % (dname, fn))

# 拷图
if used_imgs:
    os.makedirs(os.path.join(OUT, "images"), exist_ok=True)
    miss = []
    for im in sorted(used_imgs):
        src = os.path.join(SRC, "images", im)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(OUT, "images", im))
        else:
            miss.append(im)
    print("图片:", len(used_imgs) - len(miss), "张拷贝，缺失:", miss)

nd = sum(1 for r, _, fs in os.walk(OUT) for f in fs if f.endswith(".md"))
print("文档数:", nd, "｜ 图片:", len(used_imgs))