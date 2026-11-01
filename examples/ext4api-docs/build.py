#!/usr/bin/env python3
"""ExtJS 4.1 API 中文文档 (extjs-doc-cn/ext4api @ gh-pages) → Markdown

Sencha Docs 数据格式：output/<ClassName>.js = JSONP 包装的 JSON
  {"tagname":"class","name":"Ext.button.Button","html":"<div>...整页 HTML...</div>",...}
正文全在 html 字段。类名 → 命名空间目录（Ext.data/、Ext.grid/...）。
"""
import json, re, os, sys
from bs4 import BeautifulSoup

SRC = os.path.join(os.path.dirname(__file__), '..', 'fpb179-ext4api-src', 'output')
OUT = os.path.join(os.path.dirname(__file__), 'site')

JSONP_RE = re.compile(r"^Ext\.data\.JsonP\.\w+\((.*)\)\s*;?\s*$", re.S)

def load_class(fn):
    raw = open(fn, encoding='utf-8').read()
    m = JSONP_RE.match(raw)
    if not m:
        return None
    return json.loads(m.group(1))

def ns_dir(name):
    """Ext.button.Button → Ext.button (命名空间目录)"""
    parts = name.split('.')
    if len(parts) <= 2:
        return '_root'  # Ext 根级或全局类
    return '.'.join(parts[:-1])

def txt(el):
    return el.get_text(' ', strip=True) if el else ''

def clean_inline(s):
    """清洗行内文本：站内链 → 纯文本、code → 反引号"""
    s = re.sub(r'#!/api/[A-Za-z0-9_.\-]+', '', s)  # 锚点残渣（name href 也是 #!/api/...）
    return s.strip()

def render_children(el, out):
    """递归渲染 el 的子元素（不含 el 自身）。"""
    for ch in el.children:
        if getattr(ch, 'name', None) is None:
            t = str(ch).strip()
            if t:
                out.append(t)
            continue
        render_node(ch, out)

def render_node(el, out):
    name = el.name
    cls = el.get('class') or []
    if 'member' in cls:
        render_member(el, out)
    elif name in ('h1','h2','h3','h4','h5','h6'):
        t = txt(el).strip()
        if t:
            out.append('\n\n' + '#' * int(name[1]) + ' ' + t + '\n')
    elif name == 'p':
        t = txt(el).strip()
        if el.find('img'):
            out.append('\n\n')
            render_children(el, out)
            out.append('\n')
        elif el.find(['div','ul','ol','pre','table','h1','h2','h3','h4','h5','h6']):
            # 含块级/嵌套 member（源数据畸形嵌套），逐子渲染
            out.append('\n\n')
            render_children(el, out)
            out.append('\n')
        elif t:
            out.append('\n\n' + t + '\n')
    elif name == 'pre':
        t = txt(el).strip()
        if t:
            out.append('\n\n```\n' + t + '\n```\n')
    elif name == 'code':
        out.append('`' + txt(el).strip() + '`')
    elif name == 'a':
        # 站内链（#!/api/...）→ 纯文本；外链保留
        href = el.get('href') or ''
        t = txt(el).strip()
        if href.startswith('#!/') or href.startswith('source/') or not t:
            out.append(t)
        else:
            out.append(f'[{t}]({href})')
    elif name == 'ul':
        for li in el.find_all('li', recursive=False):
            render_li(li, out)
    elif name == 'ol':
        for i, li in enumerate(el.find_all('li', recursive=False), 1):
            out.append(f'\n{i}. ')
            render_children(li, out)
            out.append('\n')
    elif name in ('strong','b','em','i','span','br','div','li'):
        render_children(el, out)
    elif name == 'table':
        out.append('\n\n| ')
        # 表头
        ths = el.find_all('th')
        if ths:
            out.append(' | '.join(txt(t) for t in ths))
            out.append(' |\n| ' + ' | '.join('---' for _ in ths) + ' |\n')
        for tr in el.find_all('tr'):
            tds = tr.find_all(['td','th'])
            if tds and not (ths and tr.find_all('th')):
                out.append('| ' + ' | '.join(txt(t) for t in tds) + ' |\n')
        out.append('\n')
    elif name in ('script','style','hr','input','button','form','iframe'):
        pass  # 丢弃
    elif name == 'img':
        # 真实配图：复制到 site 同相对位置，输出 markdown 引用
        src = el.get('src') or ''
        alt = el.get('alt') or ''
        if src.startswith('images/') and not src.startswith('data:'):
            rel = src
            srcpath = os.path.join(SRC, '..', rel)
            dst = os.path.join(OUT, rel)
            if os.path.exists(srcpath):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                import shutil
                shutil.copy(srcpath, dst)
                out.append(f'\n\n![{alt}]({rel})\n')
    else:
        render_children(el, out)

def render_li(li, out):
    """列表项：纯文本 → `- text`；含子列表/块级 → 递归。"""
    blocks = [c for c in li.find_all(['p','pre','ul','ol','table','div'], recursive=False)]
    if not blocks:
        t = txt(li).strip()
        if t:
            out.append('- ' + t + '\n')
    else:
        out.append('\n- ')
        render_children(li, out)
        out.append('\n')

def render_member(el, out):
    """成员（cfg/property/method/event）：标题 + 描述。"""
    title_el = el.find('div', class_='title')
    if not title_el:
        render_children(el, out)
        return
    # 剥 view-source 链接
    for vs in title_el.find_all('a', class_='view-source'):
        vs.decompose()
    # 继承来源
    src = ''
    defined_in = title_el.find('span', class_='defined-in')
    if defined_in:
        src = txt(defined_in).strip()
    name_el = title_el.find('a', class_='name')
    mname = txt(name_el).strip() if name_el else ''
    # type 部分 = title 里 name 之后的全部文本（签名/返回类型）
    title_text = title_el.get_text(' ', strip=True)
    rest_txt = title_text
    if mname and mname in title_text:
        rest_txt = title_text.split(mname, 1)[1]
    rest_txt = re.sub(r'\s+', ' ', rest_txt).strip()
    rest_txt = re.sub(r'^[:：\s]+', '', rest_txt)
    new_kw = 'new ' if title_el.find('strong', class_='new-keyword') else ''
    line = f"{new_kw}{mname}{' : ' + rest_txt if rest_txt else ''}"
    if not mname:
        # 无 name 的成员（如 Parameters 块内）直接渲染内容
        render_children(el, out)
        return
    out.append(f'\n\n#### {line}\n')
    if src:
        out.append(f'\n> 定义于 {src}\n')
    # 描述：short 是截断预览（…结尾），long 是完整
    desc = el.find('div', class_='description')
    if desc:
        long_el = desc.find('div', class_='long')
        if long_el and txt(long_el):
            out.append('\n')
            render_children(long_el, out)
        else:
            short_el = desc.find('div', class_='short')
            if short_el:
                t = txt(short_el).strip()
                t = re.sub(r'[.…]+$', '', t)
                if t:
                    out.append('\n\n' + t + '\n')

def render_html(html):
    soup = BeautifulSoup(html, 'html5lib')
    root = soup.find('div')
    out = []
    if root:
        render_children(root, out)
    text = '\n'.join(out)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+\n', '\n', text)
    # 围栏外字面 HTML 标签转义（防语雀当 HTML 吞；代码块内不动）
    text = escape_html_outside_fences(text)
    # 残余 view-source 链接文本（畸形嵌套表格内）
    text = re.sub(r'\s*view source\s*', ' ', text)
    return text.strip()

def escape_html_outside_fences(text):
    """按 ``` 围栏 split，围栏外的 <tag> 形态文本转义为 &lt;tag&gt;。"""
    parts = re.split(r'(```[^\n]*\n.*?```)', text, flags=re.S)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            out.append(part)  # 围栏内不动
        else:
            part = re.sub(r'<(/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*)>', r'&lt;\1\2\3&gt;', part)
            out.append(part)
    return ''.join(out)

def convert(fn):
    d = load_class(fn)
    if not d or 'html' not in d:
        return None, None
    name = d['name']
    html = d['html']
    # 去掉 hierarchy pre（继承树噪音，站内死链多）
    html = re.sub(r"<pre class=['\"]hierarchy['\"]>.*?</pre>", '', html, flags=re.S)
    # 转义字面 <script> 标签（文档示例，不闭合会吞后续内容）
    html = re.sub(r'<script\b[^>]*>', '&lt;script&gt;', html)
    html = re.sub(r'</script\s*>', '&lt;/script&gt;', html)
    md = render_html(html)
    # 标题 = 类名 + 简介
    head = f"# {name}\n\n"
    return name, head + md

def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, '_root'), exist_ok=True)
    stats = []
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith('.js'):
            continue
        name, md = convert(os.path.join(SRC, fn))
        if not name:
            continue
        nd = ns_dir(name)
        dpath = os.path.join(OUT, nd)
        os.makedirs(dpath, exist_ok=True)
        fpath = os.path.join(dpath, name + '.md')
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(md)
        stats.append((len(md), fpath))
    stats.sort()
    print(f"converted {len(stats)} classes")
    for sz, fp in stats[:3] + stats[len(stats)//2:len(stats)//2+3] + stats[-3:]:
        print(f"{sz:8d} {os.path.relpath(fp, OUT)}")

if __name__ == '__main__':
    main()
