#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""llmknowledge 中文书：单 md → 10 篇（按 H2 切，与站点 10 页一一对应）"""
import os, re, shutil

SRC = "/tmp/llmknow/repo/content/理解现代LLM系统_从RAG到全景.md"
CLEAN = "/tmp/llmknow/clean"
IMG_SRC = "/tmp/llmknow/repo/content/images"

txt = open(SRC, encoding="utf-8").read()

# 清理头部：H1 书名 + 空引用块（`>` / `> `）+ `---`
txt = txt.replace("# 理解现代大语言模型系统-从RAG到全景\n", "", 1)
txt = re.sub(r"^\s*>\s*$", "", txt, flags=re.M)  # 空引用块行
txt = re.sub(r"\n---\n(?=## )", "\n", txt, count=1)

# HTML img → markdown 图（语雀渲染稳）
def to_md_img(m):
    src = m.group(1)
    alt = m.group(2) or ""
    return f"![{alt}]({src})"
txt = re.sub(r'<img src="([^"]+)" alt="([^"]*)">', to_md_img, txt)

# 按 H2 切
h2s = list(re.finditer(r"^## (.+)$", txt, flags=re.M))
assert len(h2s) == 10, f"H2 数量 {len(h2s)} != 10"
sections = []
for i, m in enumerate(h2s):
    end = h2s[i+1].start() if i+1 < len(h2s) else len(txt)
    title = m.group(1).strip()
    body = txt[m.end():end].strip("\n")
    sections.append((title, body))

os.makedirs(CLEAN, exist_ok=True)
names = []
for i, (title, body) in enumerate(sections):
    fn = f"{i:02d}-{title}.md"
    # 清洗文件名字符
    fn = re.sub(r'[\\/:*?"<>|]', "_", fn)
    open(os.path.join(CLEAN, fn), "w", encoding="utf-8").write(f"# {title}\n\n{body}\n")
    names.append((fn, len(body)))
    print(f"{fn:60s} {len(body):6d}B")

# 图片目录复制
shutil.copytree(IMG_SRC, os.path.join(CLEAN, "images"), dirs_exist_ok=True)
print("\nimages:", sorted(os.listdir(os.path.join(CLEAN, "images"))))
print("总节点(不含 images):", len(names))
