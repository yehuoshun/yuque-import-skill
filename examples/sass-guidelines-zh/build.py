#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sass-guidelin.es/zh/（Sass Guidelines 中文版）→ Markdown（2026-11-01 导入）

网站口径单页书：div#main 内 <section class="chapter chapter--*"> 按章切分。
- 剔 chapter--author / chapter--contributing（站点元信息）
- 目录 nav、设置面板在 main 外/非 chapter section，天然丢弃
- <pre class="highlight"> = Rouge 高亮：剥 span、反转义；语言启发式（< 开头 → html，其余 scss）
- 图片 css-order-chart.png 下载到 site/images/（随后走 yuque_rewrite_images.py 传 CDN）
"""
import re, os, subprocess, html as H
import html5lib

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'site')
SRC = os.path.join(BASE, 'index.html')

parser = html5lib.HTMLParser(strict=False, namespaceHTMLElements=False)

KEEP = [  # (章节 class 后缀, 文件名)
    ('chapter--sass',          '01-关于Sass.md'),
    ('chapter--introduction',  '02-简介.md'),
    ('chapter--syntax',        '03-语法格式.md'),
    ('chapter--naming',        '04-命名约定.md'),
    ('chapter--comments',      '05-注释.md'),
    ('chapter--architecture',  '06-结构.md'),
    ('chapter--rwd',           '07-响应式设计和断点.md'),
    ('chapter--variables',     '08-变量.md'),
    ('chapter--extend',        '09-扩展.md'),
    ('chapter--mixins',        '10-混合宏.md'),
    ('chapter--conditions',    '11-条件语句.md'),
    ('chapter--loops',         '12-循环.md'),
    ('chapter--errors',        '13-警告和错误.md'),
    ('chapter--tools',         '14-工具.md'),
    ('chapter--tldr',          '15-总结概要.md'),
]

def inline(el):
    out = []
    tag = el.tag.split('}')[-1] if isinstance(el.tag, str) and '}' in el.tag else el.tag
    if tag == 'code':
        return '`' + H.unescape(''.join(el.itertext())) + '`'
    if tag == 'a':
        href = el.get('href', '') or ''
        t = ''.join(el.itertext()).strip()
        if not t:
            return ''
        if href.startswith('#') or href.startswith('/'):
            return t
        return f'[{t}]({href})'
    if tag in ('b', 'strong'):
        return '**' + ''.join(el.itertext()) + '**'
    if tag in ('i', 'em'):
        return '*' + ''.join(el.itertext()) + '*'
    if tag == 'br':
        return '  \n'
    if tag == 'img':
        src = el.get('src', '')
        if src:
            return f'![{os.path.basename(src)}](images/{os.path.basename(src)})'
        return ''
    if el.text:
        out.append(el.text)
    for ch in el:
        out.append(inline(ch))
        if ch.tail:
            out.append(ch.tail)
    return ''.join(out)

def block(el):
    tag = el.tag.split('}')[-1] if isinstance(el.tag, str) and '}' in el.tag else el.tag
    cls = el.get('class', '') or ''
    lines = []
    if tag == 'h2':
        return [], False
    if tag in ('h3', 'h4', 'h5', 'h6'):
        return ['#' * int(tag[1]) + ' ' + ''.join(el.itertext()).strip()], False
    if tag == 'p':
        t = inline(el).strip()
        if not t:
            return [], False
        if 'note' in cls or 'warning' in cls or 'tip' in cls:
            return ['> ' + t], False
        return [t], False
    if tag == 'blockquote':
        out = []
        for ch in el:
            sub, _ = block(ch)
            out.extend(sub)
        return ['> ' + l for l in out if l.strip()], False
    if tag == 'pre':
        code = H.unescape(''.join(el.itertext())).rstrip('\n')
        first = code.lstrip()[:1]
        lang = 'html' if first == '<' else 'scss'
        return ['```' + lang, code, '```'], False
    if tag == 'table':
        rows = []
        for tr in el.findall('.//tr'):
            cells = [inline(td).strip().replace('|', ' ') for td in tr.findall('./td') + tr.findall('./th')]
            if cells and any(cells):
                rows.append(cells)
        if not rows:
            return [], False
        ncols = max(len(r) for r in rows)
        rows = [r + [''] * (ncols - len(r)) for r in rows]
        out = ['| ' + ' | '.join(rows[0]) + ' |', '|' + '|'.join(['---'] * ncols) + '|']
        for r in rows[1:]:
            out.append('| ' + ' | '.join(r) + ' |')
        return out, False
    if tag in ('ul', 'ol'):
        out = []
        n = 0
        for li in el.findall('./li'):
            t = inline(li).strip()
            if t:
                n += 1
                out.append(('- ' if tag == 'ul' else f'{n}. ') + t)
        return out, False
    if tag in ('div', 'section', 'article', 'figure', 'aside'):
        for ch in el:
            sub, _ = block(ch)
            lines.extend(sub)
        return lines, False
    if tag in ('script', 'style', 'nav', 'button', 'form'):
        return [], False
    # 其它：行内处理
    t = inline(el).strip()
    return [t] if t else [], False

def main():
    raw = open(SRC, 'rb').read()
    html = raw.decode('utf-8', errors='replace')
    doc = parser.parse(html)
    # 收集所有 section.chapter 元素
    chapters = []
    for el in doc.iter():
        tag = el.tag.split('}')[-1] if isinstance(el.tag, str) and '}' in el.tag else el.tag
        if tag == 'section' and 'chapter' in (el.get('class') or ''):
            chapters.append(el)
    print('found chapter sections:', len(chapters))
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, 'images'), exist_ok=True)
    # 图片下载
    img_url = 'https://sass-guidelin.es/assets/images/css-order-chart.png'
    dest = os.path.join(OUT, 'images', 'css-order-chart.png')
    if not os.path.exists(dest):
        r = subprocess.run(['curl', '-sS', '-L', '--max-time', '25', img_url], capture_output=True)
        if r.returncode == 0 and len(r.stdout) > 100:
            open(dest, 'wb').write(r.stdout)
            print('img OK', len(r.stdout))
        else:
            print('img FAIL', r.returncode, len(r.stdout))
    # 按 KEEP 映射
    for cls_suffix, fname in KEEP:
        sec = None
        for el in chapters:
            if cls_suffix in (el.get('class') or ''):
                sec = el
                break
        if sec is None:
            print('!! missing chapter', cls_suffix)
            continue
        lines = []
        for ch in sec:
            sub, _ = block(ch)
            lines.extend(sub)
        md = '\n\n'.join(l for l in lines if l.strip()) + '\n'
        with open(os.path.join(OUT, fname), 'w', encoding='utf-8') as f:
            f.write(md)
        print(f'{cls_suffix:20s} -> {fname}  {len(md)}B')
    note = """# 00-说明

> 来源：https://sass-guidelin.es/zh/ ｜ 网站口径（Sass Guidelines 中文版，Hugo Giraudel 著） ｜ 导入 2026-11-01

Sass Guidelines 中文翻译（sass-guidelin.es/zh/），单页书按章拆为 15 篇：

关于Sass / 简介 / 语法格式 / 命名约定 / 注释 / 结构 / 响应式设计和断点 / 变量 / 扩展 / 混合宏 / 条件语句 / 循环 / 警告和错误 / 工具 / 总结概要

未收录：

- 站点元信息页（关于作者、贡献、目录）
- 页面右侧「设置」交互面板（主题切换等站点功能，非书稿内容）
- 站点「左侧可选面板」等交互切换 UI（正文中以文字说明保留）

全库正文零填充前缀即阅读顺序；示例代码 149 段（SCSS/CSS/HTML 混合，按内容启发式标注语言）；1 张配图（声明顺序图）已传语雀 CDN。
"""
    with open(os.path.join(OUT, '00-说明.md'), 'w', encoding='utf-8') as f:
        f.write(note)
    print('00-说明.md written')

if __name__ == '__main__':
    main()
