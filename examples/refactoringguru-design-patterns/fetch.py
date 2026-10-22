#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""refactoringguru.cn /design-patterns 全节抓取 → markdown（网站口径）。

261 页 = 简介/目录/3 分类页 + 22 模式页 + 工厂比较 + 双分派 + 电子书页
        + 代码示例（10 语言 landing + 220 篇示例）
结构照站点：模式页按分类进 02/03/04；示例按语言进 05-代码示例/<lang>/
"""
import os, re, sys, time, json, urllib.request, urllib.error
from bs4 import BeautifulSoup, Tag, NavigableString

BASE = 'https://refactoringguru.cn'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'site')
IMGDIR = os.path.join(OUT, '_img')
CACHE = os.path.join(HERE, 'pages')
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'

PATTERNS = [
    ('factory-method', '工厂方法模式', 'creational'),
    ('abstract-factory', '抽象工厂模式', 'creational'),
    ('builder', '生成器模式', 'creational'),
    ('prototype', '原型模式', 'creational'),
    ('singleton', '单例模式', 'creational'),
    ('adapter', '适配器模式', 'structural'),
    ('bridge', '桥接模式', 'structural'),
    ('composite', '组合模式', 'structural'),
    ('decorator', '装饰模式', 'structural'),
    ('facade', '外观模式', 'structural'),
    ('flyweight', '享元模式', 'structural'),
    ('proxy', '代理模式', 'structural'),
    ('chain-of-responsibility', '责任链模式', 'behavioral'),
    ('command', '命令模式', 'behavioral'),
    ('iterator', '迭代器模式', 'behavioral'),
    ('mediator', '中介者模式', 'behavioral'),
    ('memento', '备忘录模式', 'behavioral'),
    ('observer', '观察者模式', 'behavioral'),
    ('state', '状态模式', 'behavioral'),
    ('strategy', '策略模式', 'behavioral'),
    ('template-method', '模板方法模式', 'behavioral'),
    ('visitor', '访问者模式', 'behavioral'),
]
LANGS = [('csharp', 'C#'), ('cpp', 'C++'), ('go', 'Go'), ('java', 'Java'), ('php', 'PHP'),
         ('python', 'Python'), ('ruby', 'Ruby'), ('rust', 'Rust'), ('swift', 'Swift'),
         ('typescript', 'TypeScript')]
CATDIR = {'creational': '02-创建型模式', 'structural': '03-结构型模式', 'behavioral': '04-行为模式'}
CATNAME = {'creational': '创建型模式', 'structural': '结构型模式', 'behavioral': '行为模式'}


def build_plan():
    """[(url_path, out_rel, extra_skip_classes)]"""
    plan = []
    plan.append(('/design-patterns', '00-设计模式简介.md', ()))
    plan.append(('/design-patterns/catalog', '01-设计模式目录.md', ()))
    for cat in ('creational', 'structural', 'behavioral'):
        d = CATDIR[cat]
        plan.append(('/design-patterns/%s-patterns' % cat, '%s/00-%s概览.md' % (d, CATNAME[cat]), ()))
    for i, (slug, name, cat) in enumerate(PATTERNS, 1):
        plan.append(('/design-patterns/%s' % slug, '%s/%02d-%s.md' % (CATDIR[cat], i, name), ()))
    plan.append(('/design-patterns/factory-comparison', '02-创建型模式/06-工厂模式比较.md', ()))
    plan.append(('/design-patterns/visitor-double-dispatch', '04-行为模式/23-双分派与访问者模式.md', ()))
    # 代码示例
    plan.append(('/design-patterns/examples', '05-代码示例/00-代码示例概览.md', ()))
    for li, (lslug, lname) in enumerate(LANGS, 1):
        d = '05-代码示例/%02d.%02d-%s' % (5, li, lname)
        plan.append(('/design-patterns/%s' % lslug, '%s/00-%s 模式代码示例.md' % (d, lname), ()))
        for i, (slug, name, cat) in enumerate(PATTERNS, 1):
            plan.append(('/design-patterns/%s/%s/example' % (slug, lslug),
                         '%s/%02d-%s.md' % (d, i, name), ()))
    plan.append(('/design-patterns/book', '06-深入设计模式（电子书）.md', ()))
    return plan


_fetched = 0


def fetch(url, tries=6):
    global _fetched
    os.makedirs(CACHE, exist_ok=True)
    key = re.sub(r'[^A-Za-z0-9]+', '_', url)[-120:] + '.html'
    fp = os.path.join(CACHE, key)
    if os.path.exists(fp) and os.path.getsize(fp) > 2000:
        return open(fp, encoding='utf-8', errors='replace').read()
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'zh-CN,zh;q=0.9'})
            with urllib.request.urlopen(req, timeout=45) as r:
                data = r.read().decode('utf-8', 'replace')
            if len(data) > 2000:
                open(fp, 'w', encoding='utf-8').write(data)
                _fetched += 1
                time.sleep(0.25)
                return data
            last = 'short:%d' % len(data)
        except Exception as e:
            last = repr(e)
        time.sleep(2 * (i + 1))
    raise RuntimeError('fetch failed %s: %s' % (url, last))


def dl_image(src):
    path = urllib.parse.urlparse(src).path  # /images/patterns/...
    local = os.path.join(IMGDIR, path.lstrip('/'))
    if os.path.exists(local) and os.path.getsize(local) > 0:
        return local
    os.makedirs(os.path.dirname(local), exist_ok=True)
    for i in range(5):
        try:
            req = urllib.request.Request(BASE + src, headers={'User-Agent': UA, 'Referer': BASE + '/'})
            with urllib.request.urlopen(req, timeout=45) as r:
                open(local, 'wb').write(r.read())
            time.sleep(0.15)
            return local
        except Exception:
            time.sleep(1 + i)
    return None


import urllib.parse  # noqa: E402  (used by dl_image)

LANG_RE = re.compile(r'^(C#|C\+\+|Go|Java|PHP|Python|Ruby|Rust|Swift|TypeScript)')

JUNK_EXACT = {'breadcrumb', 'sidebar-navigation', 'prev-next', 'pattern-image', 'dp-pattern-card',
              'dp-pattern-links', 'product-block', 'btn', 'comments', 'no-feature', 'add-comment'}
JUNK_TAGS = {'script', 'style', 'nav', 'button', 'form', 'iframe', 'noscript', 'svg', 'link', 'meta',
             'i', 'aside', 'head'}


def is_junk(tag, extra):
    if tag.name in JUNK_TAGS:
        return True
    for c in (tag.get('class') or []):
        cl = c.lower()
        if cl in extra or cl in JUNK_EXACT:
            return True
        for p in ('banner', 'prom', 'footer', 'main-menu', 'buy-widget'):
            if cl.startswith(p):
                return True
    return False


def clean(s):
    s = s.replace('\xad', '')
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\s+([，。、：；！？）】》」』…％])', r'\1', s)
    s = re.sub(r'([（【《「『])\s+', r'\1', s)
    return s.strip()


def lang_of(a):
    m = LANG_RE.match(a.get('title') or '')
    img = a.find('img')
    if not m and img is not None:
        m = LANG_RE.match(img.get('alt') or '')
    return m.group(1) if m else (a.get('title') or '').strip()


def inline(el, extra=()):
    out = []
    for ch in el.children:
        if isinstance(ch, NavigableString):
            out.append(str(ch))
            continue
        if not isinstance(ch, Tag):
            continue
        n = ch.name
        cls = ch.get('class') or []
        if n in ('i', 'svg', 'script', 'style', 'img'):
            continue
        if n == 'br':
            out.append(' ')
            continue
        if n == 'code':
            out.append('`%s`' % ch.get_text('', strip=False).replace('\xad', '').strip())
            continue
        if 'code-pair' in cls:
            c = ch.find('code')
            p = ch.select_one('.code-parentheses')
            t = c.get_text('', strip=False).replace('\xad', '').strip() if c else ''
            pt = p.get_text('', strip=False).strip() if p else ''
            if 'with-parentheses' in (c.get('class') or [] if c else []):
                t = t + '()'
            out.append(('`%s`（%s）' % (t, pt)) if pt else ('`%s`' % t))
            continue
        if 'fa-stars' in cls or 'dp-popularity' in cls:
            stars = ''.join('★' if 'fa-star' in (ic.get('class') or []) else '☆'
                            for ic in ch.find_all('i'))
            out.append(stars)
            continue
        if 'prog-lang-link' in cls:
            out.append(lang_of(ch))
            continue
        if n in ('strong', 'b'):
            out.append('**' + inline(ch).strip() + '**')
            continue
        if n == 'a' and 'btn' in [c.lower() for c in cls]:
            continue
        out.append(inline(ch))
    return clean(''.join(out))


def add_figure(fig, lines, extra, prefix):
    cls = fig.get('class') or []
    if 'code' in cls:
        pre = fig.find('pre')
        if pre is not None:
            emit_pre(pre, lines)
            return
    if 'image' in cls or fig.find('img'):
        got = False
        for img in fig.find_all('img'):
            if 'structure-img-indexed' in (img.get('class') or []):
                continue
            if emit_img(img, lines, prefix):
                got = True
        if got:
            return
    render_children(fig, lines, extra, prefix)


def emit_img(img, lines, prefix):
    src = img.get('src') or ''
    if not (src.startswith('/images/patterns/content/') or src.startswith('/images/patterns/diagrams/')):
        return False
    local = dl_image(src)
    if not local:
        return False
    rel = prefix + '_img/' + urllib.parse.urlparse(src).path.lstrip('/')
    alt = clean(img.get('alt') or '')
    lines.append('![%s](%s)' % (alt, rel))
    lines.append('')
    return True


def emit_pre(pre, lines):
    lang = (pre.get('lang') or '').strip()
    if lang == 'output':
        lang = ''
    code = pre.get_text('', strip=False).replace('\xad', '')
    lines.append('```' + lang)
    lines.append(code.rstrip('\n'))
    lines.append('```')
    lines.append('')


def render_table(t, lines, extra):
    rows = []
    for tr in t.find_all('tr'):
        cells = [inline(td) for td in tr.find_all(['th', 'td'])]
        if cells:
            rows.append(cells)
    if not rows:
        return
    w = max(len(r) for r in rows)
    lines.append('| ' + ' | '.join(rows[0] + [''] * (w - len(rows[0]))) + ' |')
    lines.append('|' + '---|' * w)
    for r in rows[1:]:
        lines.append('| ' + ' | '.join(r + [''] * (w - len(r))) + ' |')
    lines.append('')


def render_list(el, lines, extra, prefix, depth):
    first = el.find('li')
    icls = ''
    if first is not None:
        ic = first.find('i')
        icls = ' '.join(ic.get('class') or []) if ic is not None else ''
    if 'fa-check' in icls:
        lines.append('**优点：**')
        lines.append('')
    elif 'fa-times' in icls:
        lines.append('**缺点：**')
        lines.append('')
    ordered = el.name == 'ol'
    idx = 0
    for li in el.find_all('li', recursive=False):
        idx += 1
        mark = '%d. ' % idx if ordered else '- '
        subs = [c for c in li.find_all(recursive=False) if c.name in ('ul', 'ol')]
        parts = []
        for ch in li.children:
            if isinstance(ch, Tag) and ch.name in ('ul', 'ol'):
                break
            if isinstance(ch, NavigableString):
                parts.append(str(ch))
            elif isinstance(ch, Tag):
                parts.append(inline(ch))
        txt = clean(''.join(parts))
        if txt:
            lines.append(' ' * (depth * 2) + mark + txt)
        for s in subs:
            render_list(s, lines, extra, prefix, depth + 1)


def render_children(el, lines, extra, prefix):
    for ch in el.children:
        if isinstance(ch, NavigableString):
            t = str(ch).strip()
            if t:
                lines.append(t)
            continue
        if not isinstance(ch, Tag):
            continue
        render_block(ch, lines, extra, prefix)


def render_block(ch, lines, extra, prefix):
    if is_junk(ch, extra):
        return
    n = ch.name
    cls = ch.get('class') or []
    if n in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        t = inline(ch)
        if t:
            lines.append('#' * int(n[1]) + ' ' + t)
            lines.append('')
        return
    if n == 'p':
        links = ch.select('a.prog-lang-link')
        if len(links) >= 5:
            lines.append('**代码示例：** ' + ' · '.join(lang_of(a) for a in links))
            lines.append('')
            return
        t = inline(ch)
        if t:
            lines.append(t)
            lines.append('')
        return
    if n in ('ul', 'ol'):
        render_list(ch, lines, extra, prefix, 0)
        lines.append('')
        return
    if n == 'pre':
        emit_pre(ch, lines)
        return
    if n == 'blockquote':
        t = inline(ch)
        if t:
            lines.append('> ' + t)
            lines.append('')
        return
    if n == 'figure':
        add_figure(ch, lines, extra, prefix)
        return
    if n == 'img':
        emit_img(ch, lines, prefix)
        return
    if n == 'table':
        render_table(ch, lines, extra)
        return
    if 'dp-lang-list' in cls:
        langs = [lang_of(a) for a in ch.select('a.prog-lang-link')]
        lines.append('**支持的语言：** ' + ' · '.join(langs))
        lines.append('')
        return
    if n == 'a' and 'pattern-card' in ' '.join(cls):
        nm = ch.select_one('.pattern-name')
        ak = ch.select_one('.pattern-aka')
        it = ch.select_one('.pattern-card-bottom p') or ch.select_one('.pattern-intent')
        line = '- **%s**' % (inline(nm) if nm else '')
        if ak:
            line += '（%s）' % inline(ak)
        if it:
            line += ' — %s' % inline(it)
        lines.append(line)
        lines.append('')
        return
    if 'applicability-problem' in cls or 'applicability-solution' in cls:
        pre = '> 🐞 ' if 'problem' in ' '.join(cls) else '⚡ '
        ps = ch.find_all('p', recursive=False)
        if not ps:
            t = inline(ch)
            if t:
                lines.append(pre + t)
                lines.append('')
            return
        for k, p in enumerate(ps):
            t = inline(p)
            if t:
                lines.append((pre if k == 0 else '') + t)
                lines.append('')
        return
    if n == 'a' and 'btn' in [c.lower() for c in cls]:
        return
    if n in ('a', 'code', 'span', 'strong', 'em', 'b'):
        t = inline(ch)
        if t:
            lines.append(t)
            lines.append('')
        return
    render_children(ch, lines, extra, prefix)


def convert(html_text, url_path, extra, prefix=''):
    soup = BeautifulSoup(html_text, 'html.parser')
    main = soup.select_one('main')
    conts = [c for c in (main.select('div.page.text, article.page.text') if main else [])
             if not any('no-feature' in (p.get('class') or [])
                        for p in c.parents if isinstance(p, Tag) and p is not main and p.name != 'body')]
    lines = []
    for c in conts:
        render_children(c, lines, extra, prefix)
    txt = '\n'.join(lines)
    txt = re.sub(r'\n{3,}', '\n\n', txt)
    return txt.strip() + '\n'


def main():
    plan = build_plan()
    only_examples = '--examples-only' in sys.argv
    print('pages: %d' % len(plan))
    os.makedirs(OUT, exist_ok=True)
    n = 0
    for i, (up, rel, extra) in enumerate(plan):
        if only_examples and '/example' not in up:
            continue
        out = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        html_text = fetch(BASE + up)
        md = convert(html_text, up, tuple(extra), '../' * rel.count('/'))
        open(out, 'w', encoding='utf-8').write(md)
        n += 1
        if n % 20 == 0 or n == 1:
            print('  [%d/%d] %s -> %s (%dB)' % (n, len(plan), up, rel, len(md)), flush=True)
    print('done: %d pages, fetch=%d' % (n, _fetched))
    # 图片统计
    imgs = sum(len(f) for _, _, f in os.walk(IMGDIR)) if os.path.isdir(IMGDIR) else 0
    print('images downloaded: %d' % imgs)


if __name__ == '__main__':
    main()