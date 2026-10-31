#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w3school.com.cn HTML5 教程 → Markdown（2026-11-01 导入）

源：https://www.w3school.com.cn/html5/index.asp（网站口径）
模板：新模板 <article class="main-content">，utf-8
坑：html5lib 解析（坑 73，stdlib html.parser 不实现隐式关闭）；代码块 HTML 实体反转义；
    p.tiy（在线试验链接）丢弃；video/script 交互演示丢弃；站内链接转纯文本。
"""
import re, os, sys, html as H
import html5lib

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raw')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site')

PAGES = [
    # (raw file, 章节目录, 文件名, 页面 h1 是否剥)
    ('html5-intro',  '01-HTML5 教程', '01-HTML5 简介.md'),
    ('semantic',     '01-HTML5 教程', '02-HTML 语义元素.md'),
    ('syntax',       '01-HTML5 教程', '03-HTML 风格指南和代码约定.md'),
    ('canvas-tut',   '01-HTML5 教程', '04-HTML Canvas 图形.md'),
    ('svg',          '01-HTML5 教程', '05-HTML SVG 图形.md'),
    ('video',        '01-HTML5 教程', '06-HTML 视频.md'),
    ('audio',        '01-HTML5 教程', '07-HTML 音频.md'),
    ('object',       '01-HTML5 教程', '08-HTML 插件.md'),
    ('youtube',      '01-HTML5 教程', '09-HTML YouTube 视频.md'),
    ('webapi',       '01-HTML5 教程', '10-HTML Web API.md'),
    ('geo',          '01-HTML5 教程', '11-HTML 地理定位 API.md'),
    ('dragdrop',     '01-HTML5 教程', '12-HTML 拖放 API.md'),
    ('webstorage',   '01-HTML5 教程', '13-HTML Web Storage API.md'),
    ('workers',      '01-HTML5 教程', '14-HTML Web Workers API.md'),
    ('sse',          '01-HTML5 教程', '15-HTML 服务器发送事件 API.md'),
    ('ref-canvas',   '02-HTML5 参考手册', '01-HTML Canvas 参考手册.md'),
    ('ref-avdom',    '02-HTML5 参考手册', '02-HTML Audio／Video DOM 参考手册.md'),
]

parser = html5lib.HTMLParser(strict=False, namespaceHTMLElements=False)

def text_of(el):
    return ''.join(el.itertext())

def render_inline(el):
    """渲染行内内容：text/code/a/b/strong/em/i/span/sub/sup（顺序：text 在前、子节点在后）"""
    out = []
    tag = el.tag.split('}')[-1] if isinstance(el.tag, str) and '}' in el.tag else el.tag
    if tag == 'code':
        return '`' + H.unescape(''.join(el.itertext())) + '`'
    if tag == 'a':
        href = el.get('href', '')
        t = ''.join(el.itertext()).strip()
        if not t:
            return ''
        # 站内链接 → 纯文本；外部链接保留
        if href.startswith('/') or href.startswith('#'):
            return t
        return f'[{t}]({href})'
    if tag in ('b', 'strong'):
        return '**' + ''.join(el.itertext()) + '**'
    if tag in ('i', 'em'):
        return '*' + ''.join(el.itertext()) + '*'
    if tag == 'br':
        return '  \n'
    if el.text:
        out.append(el.text)
    for child in el:
        out.append(render_inline(child))
        if child.tail:
            out.append(child.tail)
    return ''.join(out)

def render_block(el, images_dir):
    """渲染块级元素，返回 (md 行列表, 是否交互演示丢弃)"""
    tag = el.tag.split('}')[-1] if isinstance(el.tag, str) and '}' in el.tag else el.tag
    cls = el.get('class', '') or ''
    lines = []
    if tag == 'h1':
        return [], False
    if tag == 'h2':
        return ['## ' + text_of(el).strip()], False
    if tag == 'h3':
        return ['### ' + text_of(el).strip()], False
    if tag == 'h4':
        return ['#### ' + text_of(el).strip()], False
    if tag == 'p':
        if 'tiy' in cls:
            return [], False  # 亲自试一试 在线试验链接，丢弃
        t = render_inline(el).strip()
        if not t:
            return [], False
        if 'note' in cls:
            return ['> ' + t], False
        return [t], False
    if tag == 'pre':
        # 代码块：HTML 实体反转义
        code = H.unescape(''.join(el.itertext()))
        lang = ''
        m = re.search(r'language-([\w]+)', cls)
        if m:
            lang = m.group(1)
        code = code.rstrip('\n')
        fence = '```' + lang
        return [fence, code, '```'], False
    if tag == 'table':
        rows = []
        for tr in el.findall('.//tr'):
            cells = []
            for td in tr.findall('./td') + tr.findall('./th'):
                t = render_inline(td).strip()
                t = re.sub(r'\s*\|\s*', ' ', t)
                cells.append(t)
            if cells and any(cells):
                rows.append(cells)
        if not rows:
            return [], False
        # markdown 表：首行做表头
        out = []
        ncols = max(len(r) for r in rows)
        rows = [r + [''] * (ncols - len(r)) for r in rows]
        out.append('| ' + ' | '.join(rows[0]) + ' |')
        out.append('|' + '|'.join(['---'] * ncols) + '|')
        for r in rows[1:]:
            out.append('| ' + ' | '.join(r) + ' |')
        return out, False
    if tag in ('ul', 'ol'):
        out = []
        for i, li in enumerate(el.findall('.//li')):
            prefix = '- ' if tag == 'ul' else f'{i+1}. '
            # li 内可能是块级（p/pre）或行内
            sub_lines = []
            for child in li:
                s, _ = render_block(child, None)
                sub_lines.extend(s)
            t = render_inline(li).strip()
            if sub_lines and not t:
                out.append(prefix + (sub_lines[0] if len(sub_lines) == 1 else '\n'.join(sub_lines)))
            elif t:
                out.append(prefix + t)
        return out, False
    if tag == 'img':
        src = el.get('src', '')
        if src:
            fn = os.path.basename(src)
            return [f'![{fn}](../images/{fn})'], False
        return [], False
    if tag in ('video', 'audio', 'script', 'button', 'embed', 'iframe', 'object', 'form'):
        return [], True  # 交互演示，丢弃
    if tag == 'div':
        # 处理子块（含交互演示容器）
        for child in el:
            sub, _ = render_block(child, images_dir)
            lines.extend(sub)
        return lines, False
    if tag == 'section':
        for child in el:
            sub, _ = render_block(child, images_dir)
            lines.extend(sub)
        return lines, False
    if tag == 'article':
        for child in el:
            sub, _ = render_block(child, images_dir)
            lines.extend(sub)
        return lines, False
    if tag == 'nav':
        return [], False
    if tag == 'hr':
        return ['---'], False
    if tag == 'blockquote':
        t = render_inline(el).strip()
        return [f'> {t}'] if t else [], False
    if tag == 'span':
        t = render_inline(el).strip()
        return [t] if t else [], False
    # 未知标签：递归子元素
    for child in el:
        sub, _ = render_block(child, images_dir)
        lines.extend(sub)
    return lines, False

def convert(raw_name):
    raw = open(os.path.join(RAW, raw_name + '.html'), 'rb').read()
    html = raw.decode('utf-8', errors='replace')
    a = html.find('<article class="main-content">')
    b = html.find('</article>', a)
    if a < 0 or b < 0:
        print(f'!! {raw_name}: article not found')
        return None
    seg = html[a:b + len('</article>')]
    doc = parser.parse(seg)
    art = None
    for el in doc.iter():
        tag = el.tag.split('}')[-1] if isinstance(el.tag, str) and '}' in el.tag else el.tag
        if tag == 'article' and 'main-content' in (el.get('class') or ''):
            art = el
            break
    if art is None:
        print(f'!! {raw_name}: article el not found')
        return None
    lines = []
    dropped_demo = False
    for child in art:
        sub, is_demo = render_block(child, None)
        if is_demo:
            dropped_demo = True
        lines.extend(sub)
    md = '\n\n'.join(l for l in lines if l.strip()) + '\n'
    return md, dropped_demo

def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, 'images'), exist_ok=True)
    # 图片下载
    imgs = {
        'eg_dragdrop_w3school.gif': 'https://www.w3school.com.cn/i/eg_dragdrop_w3school.gif',
        'ct_sem_elements.png': 'https://www.w3school.com.cn/i/ct_sem_elements.png',
        'viewport1.jpg': 'https://www.w3school.com.cn/i/css/viewport1.jpg',
        'viewport2.jpg': 'https://www.w3school.com.cn/i/css/viewport2.jpg',
    }
    import subprocess
    for fn, url in imgs.items():
        dest = os.path.join(OUT, 'images', fn)
        if not os.path.exists(dest):
            r = subprocess.run(['curl', '-sS', '-L', '--max-time', '20', url], capture_output=True)
            if r.returncode == 0 and len(r.stdout) > 100:
                open(dest, 'wb').write(r.stdout)
                print('img OK', fn, len(r.stdout))
            else:
                print('img FAIL', fn)
    for raw_name, sub, fname in PAGES:
        res = convert(raw_name)
        if res is None:
            continue
        md, dropped = res
        d = os.path.join(OUT, sub)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, fname), 'w', encoding='utf-8') as f:
            f.write(md)
        print(f'{raw_name:14s} -> {sub}/{fname}  {len(md)}B  dropped_demo={dropped}')

    # 00-说明
    note = """# 00-说明

> 来源：https://www.w3school.com.cn/html5/index.asp ｜ 网站口径（w3school 中文站「HTML5 教程」） ｜ 导入 2026-11-01

本库收录 w3school.com.cn 中文站的 HTML5 教程内容（当前站点将 HTML5 教程并入「HTML 教程」栏目，原 /html5/ 目录下多数页面 404，正文以现行页面为准）：

- **01-HTML5 教程**：HTML5 简介、语义元素、风格指南、Canvas、SVG、视频、音频、插件、YouTube、Web API、地理定位、拖放、Web 存储、Web Workers、SSE
- **02-HTML5 参考手册**：Canvas 参考手册、Audio/Video DOM 参考手册

未收录：

- 各页「亲自试一试」（tiy）在线交互演示页（独立 ASP 页面，无法静态化）
- 页面内嵌 `<video>`/`<script>` 交互演示（按钮、播放器等，无静态正文）
- 旧 /html5/ 目录下的独立教程页（html5_intro.asp 等已 404，内容已并入 /html/ 栏目）
- 测验、实例汇总页及 /tags/ 下的通用 HTML 参考（非 HTML5 专属）

全库 17 篇正文，零填充前缀即阅读顺序。
"""
    with open(os.path.join(OUT, '00-说明.md'), 'w', encoding='utf-8') as f:
        f.write(note)
    print('00-说明.md written')

if __name__ == '__main__':
    main()
