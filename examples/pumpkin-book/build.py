#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""南瓜书（datawhalechina/pumpkin-book）→ 语雀导入根目录 clean/ 组装。

源：仓库 docs/（vitepress 迁移后的 md 源；站点 datawhalechina.github.io/pumpkin-book
   还在跑旧 docsify，但正文 md 与 master 上 docs/chapterN/chapterN.md **逐字节相同**，
   所以直接吃仓库 md、不用爬 HTML 当 oracle）。

产出 clean/：
  00-前言.md                      ← 仓库根 README.md（HTML 清洗）
  01-纸质版勘误表.md               ← docs/errata.md
  02-第1章 绪论.md … 17-第16章 强化学习.md   ← docs/chapterN/chapterN.md（去掉首行 H1，标题=文件名）
  18-第1章 绪论（法文版）.md        ← docs/chapter1/chapter1_FR.md
  19-第2章 模型评估与选择（法文版）.md ← docs/chapter2/chapter2_FR.md
  _img/                            ← 待传 CDN 的 7 张图（导入前必须移出根目录！硬规则 10）

处理规则：
  - `> [!IMPORTANT]` GitHub callout → `> **📌 本章学习须知**`（语雀/ docsify 都不认 callout 语法）
  - 章节首行 H1 丢弃（语雀文档标题=文件名，避免重复）
  - README 的 <div align=center>/<h1>/<h2>/<img>/<a> 清洗成 md
  - raw.githubusercontent 图 → 复制成本地 _img/<name>，md 引用改相对路径（随后 yq 脚本传 CDN）
  - 图 7 张 = README 6 张（pumpkin/nangua_v2/yanggao1/yanggao2/xigua/qrcode）+ chapter2_FR 的 roc.png
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get("SRC", os.path.join(HERE, "src"))
CLEAN = os.environ.get("CLEAN", os.path.join(HERE, "clean"))

RAW = "https://raw.githubusercontent.com/datawhalechina/pumpkin-book/master/"

# 章节顺序（取自 vitepress sidebar / 各章 H1）
CHAPTERS = [
    ("chapter1", "第1章 绪论"),
    ("chapter2", "第2章 模型评估与选择"),
    ("chapter3", "第3章 线性模型"),
    ("chapter4", "第4章 决策树"),
    ("chapter5", "第5章 神经网络"),
    ("chapter6", "第6章 支持向量机"),
    ("chapter7", "第7章 贝叶斯分类器"),
    ("chapter8", "第8章 集成学习"),
    ("chapter9", "第9章 聚类"),
    ("chapter10", "第10章 降维与度量学习"),
    ("chapter11", "第11章 特征选择与稀疏学习"),
    ("chapter12", "第12章 计算学习理论"),
    ("chapter13", "第13章 半监督学习"),
    ("chapter14", "第14章 概率图模型"),
    ("chapter15", "第15章 规则学习"),
    ("chapter16", "第16章 强化学习"),
]


def clean_callout(text):
    return text.replace("> [!IMPORTANT]", "> **📌 本章学习须知**")


def strip_h1(text):
    """去掉首个 H1 标题行（语雀文档标题=文件名，避免正文再重复一遍）。

    注意：章节 1-11 的正文以 `> [!IMPORTANT]` callout 开头，H1 在其后，
    所以不能只看首行，要扫全文第一个 `# xxx` 行。"""
    text = re.sub(r'^# .*\n?', '', text, count=1, flags=re.M)
    return text.strip("\n") + "\n"


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


IMG_NAMES = ["pumpkin.png", "nangua_v2.jpg", "yanggao1.jpg", "yanggao2.jpg",
             "xigua.jpg", "qrcode.jpeg"]


def clean_readme(text):
    text = clean_callout(text)
    # <img src="URL" ...> → ![name](本地)
    def img_sub(m):
        url = m.group(1)
        name = url.rsplit("/", 1)[-1]
        return "![](_img/%s)" % name
    text = re.sub(r'<img\s+src="([^"]+)"[^>]*>', img_sub, text)
    # <a href="URL" ...>T</a> → [T](URL)
    text = re.sub(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.S)
    text = re.sub(r'</?div[^>]*>', '', text)
    text = re.sub(r'</?center[^>]*>', '', text)
    text = re.sub(r'^\s*<h1>(.*?)</h1>\s*$', r'# \1', text, flags=re.M)
    text = re.sub(r'^\s*<h2>(.*?)</h2>\s*$', r'## \1', text, flags=re.M)
    # 压缩多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip() + "\n"


def main():
    if not os.path.isdir(SRC):
        sys.exit("源目录不存在: %s（先 clone datawhalechina/pumpkin-book）" % SRC)
    if os.path.isdir(CLEAN):
        shutil.rmtree(CLEAN)
    os.makedirs(CLEAN)

    # 00 前言
    write(os.path.join(CLEAN, "00-前言.md"), clean_readme(read(os.path.join(SRC, "README.md"))))

    # 01 勘误表
    write(os.path.join(CLEAN, "01-纸质版勘误表.md"),
          strip_h1(read(os.path.join(SRC, "docs/errata.md"))))

    # 02..17 章节
    n = 2
    for d, title in CHAPTERS:
        body = clean_callout(strip_h1(read(os.path.join(SRC, "docs", d, d + ".md"))))
        write(os.path.join(CLEAN, "%02d-%s.md" % (n, title)), body)
        n += 1

    # 18/19 法文版
    fr = [("chapter1/chapter1_FR.md", "第1章 绪论（法文版）"),
          ("chapter2/chapter2_FR.md", "第2章 模型评估与选择（法文版）")]
    for rel, title in fr:
        body = clean_readme(read(os.path.join(SRC, "docs", rel))).strip() + "\n"
        write(os.path.join(CLEAN, "%02d-%s.md" % (n, title)), body)
        n += 1

    # _img：raw.githubusercontent 指向的本地文件复制进来
    imgs = os.path.join(CLEAN, "_img")
    os.makedirs(imgs, exist_ok=True)
    copied = []
    for name in IMG_NAMES:
        s = os.path.join(SRC, "res", name)
        shutil.copy(s, os.path.join(imgs, name))
        copied.append(name)
    shutil.copy(os.path.join(SRC, "docs/chapter2/resources/images/roc.png"),
                os.path.join(imgs, "roc.png"))
    copied.append("roc.png")

    # 把 FR/正文里残留的 raw.githubusercontent URL 改写为 _img/<name>
    for fn in os.listdir(CLEAN):
        if not fn.endswith(".md"):
            continue
        p = os.path.join(CLEAN, fn)
        t = read(p)
        t2 = re.sub(re.escape(RAW) + r'(\S+?)/([^/"\s)]+\.(?:png|jpg|jpeg|gif|svg|webp))',
                    lambda m: "_img/" + m.group(2), t)
        if t2 != t:
            write(p, t2)

    print("clean 生成完毕: %s" % CLEAN)
    print("文档 %d 篇 + 图 %d 张" % (n, len(copied)))
    for fn in sorted(os.listdir(CLEAN)):
        print("  ", fn)


if __name__ == "__main__":
    main()
