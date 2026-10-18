#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mastering Elasticsearch 中文版（xtmhm2000/mastering-elasticsearch @ d2b8d61）→ 语雀干净树。

源形状：GitBook 源，SUMMARY 3 层（前言 + 9 章，章内 2~3 层）；章标题自带「第N章」→ 目录名剥掉（NN 已编码序号）。
  chapter-3/6/7 的 16 个子节文件全是 0 字节空壳（翻译烂尾，SUMMARY 也未收录）→ 不建垃圾节点。
  notes/ 里 lm.png/rm.png/pixel.gif 是排版垫片（宽 1px/13px 绝对定位装饰）→ 剥掉；note.png 图标保留。
  根目录带原版英文 PDF（Mastering ElasticSearch [eBook].pdf）→ 先传语雀附件，链接写进 00-前言.md（双轨）。
命名：点分编号 NN / NN.MM / NN.MM.KK，落地页 NN-标题.md 排子节点前。
"""
import os
import re
import shutil
import sys

SRC = "/home/admin/.openclaw/workspace/tmp/mes-src"
OUT = "/home/admin/.openclaw/workspace/tmp/mes-d2b8d61-clean"
IMG_DIR = "_imgs"
BAD = re.compile(r'[/\\:*?"<>|\r\n]')
SUM_RE = re.compile(r'^(\s*)\*\s+\[([^\]]*)\]\(([^)]*)\)\s*$')
SPACER_RE = re.compile(r'<img\s+src="(?:\.\./)?notes/(?:pixel\.gif|lm\.png|rm\.png)"[^>]*/>\s*', re.I)
CH_RE = re.compile(r'^第(\d+)章\s*')

PDF_URL = sys.argv[1] if len(sys.argv) > 1 else ""   # 原版 PDF 附件 URL（可选）

missing, plan, used = [], [], set()


def sanitize(t):
    return re.sub(r"\s+", " ", t.replace("\u00a0", " ")).strip()


def rewrite(text, src_md_dir, out_md_dir):
    text = SPACER_RE.sub("", text)

    def collect(source, key):
        # 源仓库个别引用少写 imgs/ 层（chapter-4/45_README.md 里 ../44_cluster.png 实际在 imgs/）→ 兴趣回退补一层
        if not source.startswith("http") and not os.path.exists(source):
            alt = re.sub(r"(/)([^/]+)$", r"\1imgs/\2", source)
            if os.path.exists(alt):
                source = alt
        name = re.sub(r'[/\\:*?"<>|]', "__", key)
        dst = os.path.join(OUT, IMG_DIR, name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(dst):
            if source.startswith("http"):
                import subprocess
                r = subprocess.run(["curl", "-sSfL", "-m", "120", "-o", dst, source], capture_output=True)
                if r.returncode != 0 or os.path.getsize(dst) == 0:
                    missing.append(key)
                    return None
            else:
                if not os.path.exists(source):
                    missing.append(key)
                    return None
                shutil.copyfile(source, dst)
        return os.path.relpath(dst, out_md_dir)

    def sub_md(m):
        bits = m.group(2).split(None, 1)
        if bits[0].startswith(("http://", "https://", "data:")):
            return m.group(0)
        new = collect(os.path.normpath(os.path.join(src_md_dir, bits[0])), bits[0])
        return m.group(0) if not new else "%s%s%s" % (m.group(1), new, m.group(3))

    def sub_html(m):
        if m.group(3).startswith(("http://", "https://", "data:")):
            return m.group(0)
        new = collect(os.path.normpath(os.path.join(src_md_dir, m.group(3))), m.group(3))
        return m.group(0) if not new else "%s%s%s%s" % (m.group(1), m.group(2), new, m.group(4))

    text = re.sub(r'(<img\b[^>]*?\bsrc=)(["\'])([^"\']+)(["\'])', sub_html, text)
    return re.sub(r'(!\[[^\]]*\]\()([^)]+)(\))', sub_md, text)


def emit(src_rel, out_dir, fname):
    a = os.path.join(SRC, src_rel)
    body = rewrite(open(a, encoding="utf-8").read(), os.path.dirname(a), out_dir)
    if fname == "00-前言.md" and PDF_URL:
        body += ("\n\n---\n\n**原版英文 PDF 附件**（Mastering ElasticSearch [eBook].pdf，Packt, 1st ed.）："
                 "[点击下载](%s)\n" % PDF_URL)
    open(os.path.join(out_dir, fname), "w", encoding="utf-8").write(body)
    used.add(src_rel)
    plan.append(("DOC", os.path.relpath(os.path.join(out_dir, fname), OUT)))


def build(nodes, out_dir, prefix=""):
    for i, n in enumerate(nodes, 1):
        num = "%s%02d" % (prefix, i)
        title = sanitize(n["title"])
        base = "%s-%s" % (num, title)
        link = resolve(n["link"])
        if n["subs"]:
            d = os.path.join(out_dir, base)
            os.makedirs(d, exist_ok=True)
            plan.append(("TITLE", os.path.relpath(d, OUT)))
            if link:
                emit(link, d, base + ".md")
            build(n["subs"], d, num + ".")
        elif link:
            emit(link, out_dir, base + ".md")


def resolve(link):
    return link if link and os.path.isfile(os.path.join(SRC, link)) else None


def parse_summary():
    stack, roots = [], []
    for line in open(os.path.join(SRC, "SUMMARY.md"), encoding="utf-8"):
        m = SUM_RE.match(line.rstrip("\n"))
        if not m:
            continue
        depth = len(m.group(1)) // 3
        node = {"title": m.group(2).strip(), "link": m.group(3).strip(), "subs": []}
        while stack and stack[-1][0] >= depth:
            stack.pop()
        (stack[-1][1]["subs"] if stack else roots).append(node)
        stack.append((depth, node))
    return roots


if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

roots = parse_summary()
assert roots[0]["link"] == "README.md" and not roots[0]["subs"]
emit("README.md", OUT, "00-前言.md")
roots = roots[1:]

# 章目录名剥「第N章」前缀（NN 已编码序号）
for n in roots:
    m = CH_RE.match(n["title"])
    if m:
        n["title"] = n["title"][m.end():].strip()

build(roots, OUT)

srcmd = set()
for dp, _, fns in os.walk(SRC):
    if "/.git" in dp:
        continue
    for f in fns:
        if f.endswith(".md"):
            srcmd.add(os.path.relpath(os.path.join(dp, f), SRC))
srcmd.discard("SUMMARY.md")
print("TITLE %d / DOC %d / 合计 %d" % (sum(1 for p in plan if p[0] == "TITLE"),
                                       sum(1 for p in plan if p[0] == "DOC"), len(plan)))
print("源 md %d / 已用 %d" % (len(srcmd), len(used)))
print("未用:", sorted(srcmd - used))
print("图缺失:", missing)
print("收集图片:", sum(len(f) for _, _, f in os.walk(os.path.join(OUT, IMG_DIR))))
for x in sorted(os.listdir(OUT)):
    if x != IMG_DIR:
        print("  ", x)