#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Jive/DECN 类社区页（EMC 中文支持论坛）HTML -> 语雀 md

输入：cc_warc.py 从 Common Crawl WARC 还原的原页 HTML（raw/DOC-*.html）
要点：
  - 正文 = <!-- [DocumentBodyStart:...] --> 到 <!-- [DocumentBodyEnd
  - 项目符 ü/Ø/•/– 是字面字符（Word 符号字体）→ 按首字符映射 1/2 级嵌套列表
  - <h1> = 小节标题（介绍/更多信息/参考/应用于）→ ##
用法：改 DOCS / SRC / OUT 后 python3 build_jive.py
"""
import re, html, os

SRC = "/home/admin/.openclaw/workspace/tmp/san-emc"
OUT = "/home/admin/.openclaw/workspace/tmp/san-build/book"
os.makedirs(OUT, exist_ok=True)
DOCS = [("DOC-16067", "01", "交换机管理工具"), ("DOC-16068", "02", "主机相关概念"),
        ("DOC-16069", "03", "Zone概念"), ("DOC-16080", "04", "VSAN和virtual fabric"),
        ("DOC-16081", "05", "ISL和互操作性"), ("DOC-16082", "06", "PortChannel和Trunking"),
        ("DOC-16083", "07", "AG和NPV"), ("DOC-16084", "08", "NPIV技术")]
IMG_MAP = {"DOC-16082": "assets/p6-compare.png", "DOC-16084": "assets/p8-npiv.png"}
CN = "一二三四五六七八"


def inline(el):
    el = re.sub(r'<a[^>]*href="[^"]*"[^>]*>(.*?)</a>', r'\1', el, flags=re.S)
    el = re.sub(r'<(strong|b)[^>]*>(.*?)</\1>', r'**\2**', el, flags=re.S)
    el = re.sub(r'<(em|i)[^>]*>(.*?)</\1>', r'\2', el, flags=re.S)
    el = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', el, flags=re.S)
    el = re.sub(r'<[^>]+>', '', el)
    return html.unescape(el).replace('\u00a0', ' ').strip()


def norm_bullet(t):
    m = re.match(r'^([üØ•–▪·§])\s*(.*)$', t, re.S)
    if m:
        ch, rest = m.group(1), m.group(2).strip()
        lvl = 1 if ch in 'ü•§·' else 2
        return ('- ' if lvl == 1 else '  - ') + rest
    return t


def conv_body(b):
    b = re.sub(r'<!--.*?-->', '', b, flags=re.S)
    b = re.sub(r'<h1[^>]*>(.*?)</h1>', lambda m: '\n\n## ' + inline(m.group(1)) + '\n\n', b, flags=re.S)
    b = re.sub(r'<ul[^>]*>(.*?)</ul>',
               lambda m: '\n\n' + '\n'.join('- ' + inline(x) for x in re.findall(r'<li[^>]*>(.*?)</li>', m.group(1), re.S)) + '\n\n',
               b, flags=re.S)
    b = re.sub(r'<img[^>]*>', '\n@@IMG@@\n', b)
    out = []
    for p in re.split(r'(?=<p\b)', b):
        mm = re.match(r'<p[^>]*>(.*)', p, re.S)
        txt = inline(mm.group(1)) if mm else inline(p)
        txt = txt.strip()
        if not txt:
            continue
        if '@@IMG@@' in txt:
            out.append('@@IMG@@')
            continue
        out.append(norm_bullet(txt))
    t = '\n\n'.join(out)
    t = re.sub(r'\*{4,}', '', t)
    t = re.sub(r'\*\*\s*\*\*', '', t)
    t = re.sub(r'<!--.*$', '', t, flags=re.S)
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t


for doc, num, title in DOCS:
    h = open(os.path.join(SRC, doc + '.html'), encoding='utf-8', errors='replace').read()
    s = h.find('DocumentBodyStart')
    e = h.find('DocumentBodyEnd')
    body = re.sub(r'^[^>]*-->', '', h[s:e])
    md = conv_body(body)
    if doc in IMG_MAP:
        md = md.replace('@@IMG@@', '![%s](%s)' % (title, IMG_MAP[doc]), 1)
    md = md.replace('@@IMG@@', '')
    head = '# SAN管理入门系列（%s）%s\n\n' % (CN[int(num) - 1], title)
    lines = md.split('\n')
    if lines and re.match(r'^#+\s*SAN管理入门系列', lines[0]):
        md = '\n'.join(lines[1:]).lstrip('\n')
    open(os.path.join(OUT, '%s-%s.md' % (num, title)), 'w').write(head + md.strip() + '\n')
print('built', len(DOCS))