#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yuque_rewrite_images 的正则回归单测（不联网）。

覆盖：
  1. HTML `<img src="...">`（双引号）
  2. HTML `<img src='...'>`（单引号）—— 2026-10-17 linux-doc 实踩漏传的那类
  3. 属性顺序/换行、alt 里带引号等其他属性
  4. markdown `![alt](path)`
  5. markdown path 里含成对括号 `![](./石凉粉(冰粉)成品1.jpg)` —— 2026-10-20 HowToCook 实踩漏传的那类
  6. 反例：纯文本里的 src= 不应误伤

跑法：cd scripts && python3 test_rewrite_images_re.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yuque_rewrite_images import HTML_RE, MD_RE  # noqa: E402

fails = []


def eq(name, got, want):
    if got != want:
        fails.append("%s: got %r want %r" % (name, got, want))
    print(("PASS " if got == want else "FAIL ") + name)


# ---- HTML：单/双引号 + 各种属性排布 ----
html_cases = [
    ("html double", '<img src="pic/b.jpg" width="150"/>', "pic/b.jpg"),
    ("html single", "<img src='../pic/a.jpg' width='110px'/>", "../pic/a.jpg"),
    ("html single abs", "<img alt=x src='/abs/c.png'>", "/abs/c.png"),
    ("html multiline", "<img\ndata-x=1\nsrc='d.svg'>", "d.svg"),
    ("html https", '<img src="https://cdn.example.com/x.png">', "https://cdn.example.com/x.png"),
]
for name, text, want in html_cases:
    m = HTML_RE.search(text)
    eq(name, m.group(3) if m else None, want)

# 反例：没有 img 标签的 src= 不该被匹配
m = HTML_RE.search('<a href="x.html">src="not-an-image.png"</a>')
eq("html negative (no <img>)", m, None)

# ---- markdown ----
md_cases = [
    ("md basic", "![alt](images/x.png)", "images/x.png"),
    ("md nested parens-safe", "![](../img/y.jpg)", "../img/y.jpg"),
    # 2026-10-20 HowToCook：中文文件名带括号 → 旧正则截断成「本地缺失」
    ("md paren path", "![石凉粉(冰粉)成品1](./石凉粉(冰粉)成品1.jpg)",
     "./石凉粉(冰粉)成品1.jpg"),
    ("md paren path + title", '![x](./a(b).jpg "标题")', './a(b).jpg "标题"'),
    ("md paren path, trailing note", "![x](./a.jpg) 说明(b)", "./a.jpg"),
]
for name, text, want in md_cases:
    m = MD_RE.search(text)
    eq(name, m.group(2) if m else None, want)
eq("md negative (plain link)", MD_RE.search("[text](page.md)"), None)

n = len(html_cases) + 1 + len(md_cases) + 1
print("\n%s" % (("ALL PASS (%d)" % n) if not fails else "FAILED %d" % len(fails)))
sys.exit(1 if fails else 0)