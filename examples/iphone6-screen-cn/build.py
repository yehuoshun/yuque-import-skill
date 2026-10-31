#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wileam.com/iphone-6-screen-cn/（iPhone 6 屏幕揭秘 中文译文）→ Markdown（2026-11-01）

单篇译文：PaintCode《iPhone 6 Screens Demystified》中文版，3 张内联 SVG 大图。
坑 41/52：SVG 必须原样保留（语雀支持内联 svg），且抽 svg 要深度计数（内层可能嵌套 svg）。
html5lib 会把 SVG 命名空间弄成 ns0/ns1 → 不能整页过解析器；先深度计数抽出原始 SVG 块，
剩余文本用 html5lib 转换，再回填。
"""
import re, os
import html5lib

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'site')
parser = html5lib.HTMLParser(strict=False, namespaceHTMLElements=False)

SVG_OPEN = re.compile(r'<svg\b')
SVG_TAG = re.compile(r'</?svg\b[^>]*>')

def extract_svgs(text):
    """深度计数抽 SVG 块（贪婪），返回 (去掉 svg 的文本, [svg 原文])"""
    svgs = []
    out, pos = [], 0
    for m in SVG_OPEN.finditer(text):
        depth, end = 0, None
        for mm in SVG_TAG.finditer(text, m.start()):
            depth += -1 if text[mm.start()+1] == '/' else 1
            if depth == 0:
                end = mm.end()
                break
        if end is None:
            continue
        out.append(text[pos:m.start()])
        svgs.append(text[m.start():end])
        out.append('<div class="svgph">@@SVG%d@@</div>' % (len(svgs) - 1))
        pos = end
    out.append(text[pos:])
    return ''.join(out), svgs

def render_fragment(frag):
    doc = parser.parse(frag)
    body = doc.find('body')
    lines = []
    def walk(el):
        tag = el.tag.split('}')[-1] if isinstance(el.tag, str) and '}' in el.tag else el.tag
        if tag in ('p', 'div'):
            t = ''.join(el.itertext()).strip()
            if t and '来源：' not in t and '译者：' not in t:
                lines.append(t)
            return
        if tag == 'hr':
            lines.append('---')
            return
        if tag == 'h2':
            return
        if tag == 'h3':
            lines.append('### ' + ''.join(el.itertext()).strip())
            return
        if tag == 'img':
            return
        if tag == 'br':
            return
        for ch in el:
            walk(ch)
    for ch in body:
        walk(ch)
    return lines

def main():
    raw = open(os.path.join(BASE, 'page.html'), 'rb').read()
    html = raw.decode('utf-8', errors='replace')
    a = html.find('<article')
    b = html.find('</article>', a)
    seg = html[a:b] if a >= 0 and b > a else html
    frag, svgs = extract_svgs(seg)
    print('svgs:', len(svgs))
    lines = render_fragment(frag)
    # 回填 svg
    out = []
    for l in lines:
        out.append(l)
    md_parts = []
    si = 0
    for l in lines:
        md_parts.append(l)
        # 在 --- 分隔处之后回填 svg 不好定位；改为按占位顺序：把 svg 插到每个 hr 之后
    md = '\n\n'.join(x for x in lines if x and x.strip()) + '\n'
    for i, svg in enumerate(svgs):
        md = md.replace('@@SVG%d@@' % i, svg)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, '01-iPhone 6 屏幕揭秘.md'), 'w', encoding='utf-8') as f:
        f.write(md)
    print('written', len(md))
    note = """# 00-说明

> 来源：http://wileam.com/iphone-6-screen-cn/ ｜ 网站口径（wileam.com 中文译文） ｜ 导入 2026-11-01

《iPhone 6 屏幕揭秘》中文译文（译者：小雪-Joanna），原文为 PaintCode 官方博客《iPhone 6 Screens Demystified》（http://www.paintcodeapp.com/news/iphone-6-screens-demystified），2014-09 发布。

- 单篇文档，正文含 3 张内联 SVG 矢量示意图（屏幕渲染区域划分 / 一根线的渲染 / 文字渲染），已原样保留（语雀支持内联 SVG）
- 译站另有无图版：http://code.wileam.com/iphone-6-screen/
- 内容基于 iPhone 6 / iOS 8 时代渲染机制（3x 渲染等），仅作历史参考
"""
    with open(os.path.join(OUT, '00-说明.md'), 'w', encoding='utf-8') as f:
        f.write(note)
    print('note written')

if __name__ == '__main__':
    main()
