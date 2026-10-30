#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#115 Haskell 趣学指南 (MnO2/learnyouahaskell-zh @ 8247441)
站点 learnyouahaskell.mno2.org = 繁中版 → 吃仓库 zh-tw/ 的 md（源）。
一章一篇（SUMMARY 定序/标题），NN- 前缀；图在 .gitbook/assets/（文件名含空格/括号，URL 编码）→ 解码后本地化。
"""
import os, re, shutil, urllib.parse

CLEAN = "learnyouahaskell-zh-8247441-clean"
SRC = os.path.join(CLEAN, "zh-tw")
OUT = "build"

ORDER = [
    ("ch01/introduction.md", "簡介"),
    ("ch02/ready-go.md", "從零開始"),
    ("ch03/type-and-typeclass.md", "Types and Typeclasses"),
    ("ch04/syntax-in-function.md", "函數的語法"),
    ("ch05/recursion.md", "遞迴"),
    ("ch06/high-order-function.md", "高階函數"),
    ("ch07/module.md", "模組 (Modules)"),
    ("ch08/build-our-own-type-and-typeclass.md", "構造我們自己的 Types 和 Typeclasses"),
    ("ch09/input-and-output.md", "輸入與輸出"),
    ("ch10/functionally-solving-problems.md", "函數式地思考來解決問題"),
    ("ch11/functors-applicative-functors-and-monoids.md", "Functors, Applicative Functors 與 Monoids"),
    ("ch12/a-fistful-of-monads.md", "來看看幾種 Monad"),
    ("ch13/for-a-few-monads-more.md", "再來看看更多 Monad"),
    ("ch14/zippers.md", "Zippers 資料結構"),
    ("faq/faq.md", "FAQ"),
]


def sanitize(name):
    name = re.sub(r"\s+", "_", name)
    name = name.replace("(", "").replace(")", "")
    return name


def fix_links(t):
    # 站内相对 .md/.html 链接 → 纯文字
    t = re.sub(r"\[([^\]]+)\]\((?!https?:)[^)]*\.(?:md|html)[^)]*\)", r"\1", t)
    return t


def fix_imgs(t):
    def rep(m):
        raw = m.group(1).strip()
        if not raw.startswith("../../.gitbook/assets/"):
            return m.group(0)
        name = urllib.parse.unquote(raw.rsplit("/", 1)[1])
        return "![](" + "assets/" + sanitize(name) + ")"
    t = re.sub(r"!\[[^\]]*\]\(((?:[^()]|\([^()]*\))*)\)", rep, t)
    return t


def strip_h1(t):
    lines = t.split("\n")
    for i, ln in enumerate(lines):
        if ln.strip() == "":
            continue
        if ln.startswith("# "):
            return "\n".join(lines[i + 1:]).lstrip("\n")
        break
    return t


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    readme = open(os.path.join(CLEAN, "README.md"), encoding="utf-8").read()
    open(os.path.join(OUT, "00-說明.md"), "w", encoding="utf-8").write(
        "> 来源：https://github.com/MnO2/learnyouahaskell-zh @ 8247441 ｜ 《HASKELL 趣學指南》"
        "（Learn You a Haskell for Great Good 繁體中文版，站 https://learnyouahaskell.mno2.org/ ）｜ "
        "正文取仓库 zh-tw/（站点即此繁中版），一章一篇。\n\n"
        + re.sub(r"^#\s+.*\n", "", readme).strip() + "\n")
    nn = 1
    for rel, title in ORDER:
        p = os.path.join(SRC, rel)
        t = open(p, encoding="utf-8").read()
        t = strip_h1(t)
        t = fix_imgs(fix_links(t))
        name = f"{nn:02d}-{title}.md"
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(t.strip() + "\n")
        print(f"  {nn:02d} {rel:48} -> {name} ({len(t)} chars)")
        nn += 1
    # 图
    shutil.copytree(os.path.join(CLEAN, ".gitbook", "assets"), os.path.join(OUT, "assets"))
    # 净化含 空格/括号 的文件名（rewrite 脚本的 split(None,1) 会截断带空格路径）
    for fn in list(os.listdir(os.path.join(OUT, "assets"))):
        new = sanitize(fn)
        if new != fn:
            os.rename(os.path.join(OUT, "assets", fn), os.path.join(OUT, "assets", new))
    print("done, assets:", len(os.listdir(os.path.join(OUT, "assets"))))


if __name__ == "__main__":
    main()
