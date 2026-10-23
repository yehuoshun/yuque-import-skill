#!/usr/bin/env python3
"""现代 GitBook v2 站 (einverne.gitbook.io/selenium-doc) → 语雀 md。

源：站自带 llms.txt 全量索引 + 每页 `路径.md`（GitBook 官方 Markdown 导出，正文 SSR 直出），
不用抓 HTML、不用写 DOM 渲染器。逐页 md 落盘后做三件事：
  1. 剥 GitBook 注入的第一行样板 callout（`> For the complete documentation index, see llms.txt ...`）
  2. 剥正文首个 H1（标题已由 文件名/目录 提供）
  3. 外链图（seleniumhq.org 老站已 404）→ 改本地 `../imgs/`（图由 vdt/selenium 镜像仓补回，
     再交 yuque_rewrite_images.py 传 CDN；跑完删掉 imgs/）
"""
import os, re

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
OUT = os.path.join(HERE, "site")

BOILER = re.compile(r'^> For the complete documentation index.*?\n\n', re.S)
IMG = re.compile(r'http://seleniumhq\.org/docs/_images/([^)\s]+)')

# (raw file, 目标相对路径)
PAGES = [
    ("master.md", "00-介绍.md"),
    ("guan-fang-wen-dang__introduction.md", "官方文档/01-Selenium 介绍.md"),
    ("guan-fang-wen-dang__selenium-1.md", "官方文档/02-Selenium RC.md"),
    ("guan-fang-wen-dang__selenium-web-driver.md", "官方文档/03-Selenium Web Driver.md"),
    ("guan-fang-wen-dang__selenium-grid.md", "官方文档/04-Selenium Grid.md"),
    ("wiki__advanced-user-interactions.md", "wiki/01-高级用户交互.md"),
    ("wiki__web-driver-js.md", "wiki/02-Web driver js.md"),
    ("wiki__frequently-asked-questions.md", "wiki/03-常见问题.md"),
]


def clean(text, depth):
    text = BOILER.sub("", text, count=1)
    text = text.strip("\n")
    # 剥首个 H1
    text = re.sub(r'^# [^\n]*\n+', '', text, count=1)
    prefix = "../" * depth
    text = IMG.sub(lambda m: f"{prefix}imgs/{m.group(1)}", text)
    return text.strip() + "\n"


def main():
    for f in os.listdir(OUT) if os.path.isdir(OUT) else []:
        p = os.path.join(OUT, f)
        if os.path.isfile(p):
            os.remove(p)
    for src, rel in PAGES:
        depth = rel.count("/")
        text = clean(open(os.path.join(RAW, src), encoding="utf-8").read(), depth)
        dst = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "w", encoding="utf-8").write(text)
        print(f"{rel}  chars={len(text)}")
    print("pages:", len(PAGES))


if __name__ == "__main__":
    main()