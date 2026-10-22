#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CSDN lovelion（刘伟/Sunny）《史上最全设计模式导学目录》全系列 → markdown。

源：http://blog.csdn.net/lovelion/article/details/17517213（索引页）
    + 索引里 129 篇系列文章（= 7 设计原则 + 24 模式 + 2 复习 + 2 综合实例）
树：01-基础知识 / 02-面向对象设计原则 / 03-创建型 / 04-结构型 / 05-行为型 / 06-足球 / 07-综合实例
"""
import os, re, sys, json, time, html, hashlib, mimetypes, urllib.request, urllib.error
from bs4 import BeautifulSoup, Tag, NavigableString

IDX = 'https://blog.csdn.net/lovelion/article/details/17517213'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'site')
IMG = os.path.join(OUT, '_img')
CACHE = os.path.join(HERE, 'pages')
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')


def fetch(url, tries=8, min_size=5000):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.md5(url.encode()).hexdigest()[:16] + '.html'
    fp = os.path.join(CACHE, key)
    if os.path.exists(fp) and os.path.getsize(fp) > min_size:
        return open(fp, encoding='utf-8', errors='replace').read()
    last = ''
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'zh-CN,zh;q=0.9', 'Referer': IDX})
            with urllib.request.urlopen(req, timeout=45) as r:
                data = r.read().decode('utf-8', 'replace')
            # CSDN 反爬：521 或 无 content_views → 重试
            if len(data) > min_size and 'content_views' in data:
                open(fp, 'w', encoding='utf-8').write(data)
                time.sleep(1.5)
                return data
            last = 'short_or_blocked:%d' % len(data)
        except urllib.error.HTTPError as e:
            last = 'HTTP %s' % e.code
        except Exception as e:
            last = repr(e)
        time.sleep(3 + 3 * i)
    raise RuntimeError('fetch fail %s: %s' % (url, last))


# ---------- 目录结构（由索引页解析出，硬编码兜底见 build_plan） ----------
GROUPS = [
    ('01-基础知识', [('从招式与内功谈起——设计模式概述（一）', '7417668'),
                     ('从招式与内功谈起——设计模式概述（二）', '7420863'),
                     ('从招式与内功谈起——设计模式概述（三）', '7420866')]),
    ('02-面向对象设计原则', [('面向对象设计原则概述', '7536532'),
                             ('面向对象设计原则之单一职责原则', '7536542'),
                             ('面向对象设计原则之开闭原则', '7537584'),
                             ('面向对象设计原则之里氏代换原则', '7540445'),
                             ('面向对象设计原则之依赖倒转原则', '7562783'),
                             ('面向对象设计原则之接口隔离原则', '7562842'),
                             ('面向对象设计原则之合成复用原则', '7563441'),
                             ('面向对象设计原则之迪米特法则', '7563445')]),
    ('03-创建型模式', [
        ('简单工厂模式', [('工厂三兄弟之简单工厂模式（一）', '9300337'), ('工厂三兄弟之简单工厂模式（二）', '9300549'),
                     ('工厂三兄弟之简单工厂模式（三）', '9300657'), ('工厂三兄弟之简单工厂模式（四）', '9300731')]),
        ('工厂方法模式', [('工厂三兄弟之工厂方法模式（一）', '9306457'), ('工厂三兄弟之工厂方法模式（二）', '9306745'),
                     ('工厂三兄弟之工厂方法模式（三）', '9307137'), ('工厂三兄弟之工厂方法模式（四）', '9307561')]),
        ('抽象工厂模式', [('工厂三兄弟之抽象工厂模式（一）', '9319181'), ('工厂三兄弟之抽象工厂模式（二）', '9319323'),
                     ('工厂三兄弟之抽象工厂模式（三）', '9319423'), ('工厂三兄弟之抽象工厂模式（四）', '9319481'),
                     ('工厂三兄弟之抽象工厂模式（五）', '9319571')]),
        ('单例模式', [('确保对象的唯一性——单例模式（一）', '7420883'), ('确保对象的唯一性——单例模式（二）', '7420885'),
                   ('确保对象的唯一性——单例模式（三）', '7420886'), ('确保对象的唯一性——单例模式（四）', '7420888'),
                   ('确保对象的唯一性——单例模式（五）', '7420889')]),
        ('原型模式', [('对象的克隆——原型模式（一）', '7424559'), ('对象的克隆——原型模式（二）', '7424594'),
                   ('对象的克隆——原型模式（三）', '7424620'), ('对象的克隆——原型模式（四）', '7424623')]),
        ('建造者模式', [('复杂对象的组装与创建——建造者模式（一）', '7426015'), ('复杂对象的组装与创建——建造者模式（二）', '7426323'),
                    ('复杂对象的组装与创建——建造者模式（三）', '7426855')]),
    ]),
    ('04-结构型模式', [
        ('适配器模式', [('不兼容结构的协调——适配器模式（一）', '8624325'), ('不兼容结构的协调——适配器模式（二）', '8624412'),
                    ('不兼容结构的协调——适配器模式（三）', '8624428'), ('不兼容结构的协调——适配器模式（四）', '8624633')]),
        ('桥接模式', [('处理多维度变化——桥接模式（一）', '7464183'), ('处理多维度变化——桥接模式（二）', '7464195'),
                   ('处理多维度变化——桥接模式（三）', '7464204'), ('处理多维度变化——桥接模式（四）', '7464208')]),
        ('组合模式', [('树形结构的处理——组合模式（一）', '7956898'), ('树形结构的处理——组合模式（二）', '7956908'),
                   ('树形结构的处理——组合模式（三）', '7956931'), ('树形结构的处理——组合模式（四）', '7956937'),
                   ('树形结构的处理——组合模式（五）', '7956962')]),
        ('装饰模式', [('扩展系统功能——装饰模式（一）', '7424685'), ('扩展系统功能——装饰模式（二）', '7425849'),
                   ('扩展系统功能——装饰模式（三）', '7425861'), ('扩展系统功能——装饰模式（四）', '7425873')]),
        ('外观模式', [('深入浅出外观模式（一）', '8258121'), ('深入浅出外观模式（二）', '8259705'),
                   ('深入浅出外观模式（三）', '8259789')]),
        ('享元模式', [('实现对象的复用——享元模式（一）', '7667781'), ('实现对象的复用——享元模式（二）', '7667810'),
                   ('实现对象的复用——享元模式（三）', '7667839'), ('实现对象的复用——享元模式（四）', '7667860'),
                   ('实现对象的复用——享元模式（五）', '7667901')]),
        ('代理模式', [('代理模式（一）', '8227953'), ('代理模式（二）', '8228042'),
                   ('代理模式（三）', '8228132'), ('代理模式（四）', '8228156')]),
    ]),
    ('05-行为型模式', [
        ('职责链模式', [('请求的链式处理——职责链模式（一）', '7420891'), ('请求的链式处理——职责链模式（二）', '7420893'),
                    ('请求的链式处理——职责链模式（三）', '7420898'), ('请求的链式处理——职责链模式（四）', '7420902')]),
        ('命令模式', [('请求发送者与接收者解耦——命令模式（一）', '8796736'), ('请求发送者与接收者解耦——命令模式（二）', '8806049'),
                   ('请求发送者与接收者解耦——命令模式（三）', '8806239'), ('请求发送者与接收者解耦——命令模式（四）', '8806509'),
                   ('请求发送者与接收者解耦——命令模式（五）', '8806643'), ('请求发送者与接收者解耦——命令模式（六）', '8806677')]),
        ('解释器模式', [('自定义语言的实现——解释器模式（一）', '7713567'), ('自定义语言的实现——解释器模式（二）', '7713578'),
                    ('自定义语言的实现——解释器模式（三）', '7713589'), ('自定义语言的实现——解释器模式（四）', '7713593'),
                    ('自定义语言的实现——解释器模式（五）', '7713602'), ('自定义语言的实现——解释器模式（六）', '7713615')]),
        ('迭代器模式', [('遍历聚合对象中的元素——迭代器模式（一）', '9992005'), ('遍历聚合对象中的元素——迭代器模式（二）', '9992243'),
                    ('遍历聚合对象中的元素——迭代器模式（三）', '9992679'), ('遍历聚合对象中的元素——迭代器模式（四）', '9992731'),
                    ('遍历聚合对象中的元素——迭代器模式（五）', '9992799'), ('遍历聚合对象中的元素——迭代器模式（六）', '9992931')]),
        ('中介者模式', [('协调多个对象之间的交互——中介者模式（一）', '8482952'), ('协调多个对象之间的交互——中介者模式（二）', '8483005'),
                    ('协调多个对象之间的交互——中介者模式（三）', '8483031'), ('协调多个对象之间的交互——中介者模式（四）', '8483081'),
                    ('协调多个对象之间的交互——中介者模式（五）', '8483151')]),
        ('备忘录模式', [('撤销功能的实现——备忘录模式（一）', '7526740'), ('撤销功能的实现——备忘录模式（二）', '7526747'),
                    ('撤销功能的实现——备忘录模式（三）', '7526755'), ('撤销功能的实现——备忘录模式（四）', '7526756'),
                    ('撤销功能的实现——备忘录模式（五）', '7526759')]),
        ('观察者模式', [('对象间的联动——观察者模式（一）', '7720232'), ('对象间的联动——观察者模式（二）', '7720382'),
                    ('对象间的联动——观察者模式（三）', '7720490'), ('对象间的联动——观察者模式（四）', '7720507'),
                    ('对象间的联动——观察者模式（五）', '7720522'), ('对象间的联动——观察者模式（六）', '7720537')]),
        ('状态模式', [('处理对象的多种状态及其相互转换——状态模式（一）', '8522982'), ('处理对象的多种状态及其相互转换——状态模式（二）', '8523062'),
                   ('处理对象的多种状态及其相互转换——状态模式（三）', '8523083'), ('处理对象的多种状态及其相互转换——状态模式（四）', '8523105'),
                   ('处理对象的多种状态及其相互转换——状态模式（五）', '8523130'), ('处理对象的多种状态及其相互转换——状态模式（六）', '8523162')]),
        ('策略模式', [('算法的封装与切换——策略模式（一）', '7818983'), ('算法的封装与切换——策略模式（二）', '7819136'),
                   ('算法的封装与切换——策略模式（三）', '7819216'), ('算法的封装与切换——策略模式（四）', '7819266')]),
        ('模板方法模式', [('模板方法模式深度解析（一）', '8299794'), ('模板方法模式深度解析（二）', '8299863'),
                     ('模板方法模式深度解析（三）', '8299927')]),
        ('访问者模式', [('操作复杂对象结构——访问者模式（一）', '7433523'), ('操作复杂对象结构——访问者模式（二）', '7433567'),
                    ('操作复杂对象结构——访问者模式（三）', '7433576'), ('操作复杂对象结构——访问者模式（四）', '7433591')]),
    ]),
    ('06-设计模式与足球（趣味复习）', [('设计模式与足球（一）', '7707380'), ('设计模式与足球（二）', '7707497'),
                             ('设计模式与足球（三）', '7707605'), ('设计模式与足球（四）', '7708208')]),
    ('07-综合应用实例', [
        ('多人联机射击游戏', [('多人联机射击游戏中的设计模式应用（一）', '8262987'), ('多人联机射击游戏中的设计模式应用（二）', '8263025')]),
        ('数据库同步系统', [('设计模式综合实例分析之数据库同步系统（一）', '8671196'), ('设计模式综合实例分析之数据库同步系统（二）', '8671578'),
                      ('设计模式综合实例分析之数据库同步系统（三）', '8671653')]),
    ]),
]


def build_plan():
    plan = [(IDX, '00-史上最全设计模式导学目录.md')]
    for name, items in GROUPS:
        if isinstance(items[0], tuple) and isinstance(items[0][1], str):
            for i, (t, aid) in enumerate(items, 1):
                plan.append(('https://blog.csdn.net/lovelion/article/details/%s' % aid,
                             '%s/%02d-%s.md' % (name, i, t)))
        else:
            for j, (sub, arts) in enumerate(items, 1):
                for i, (t, aid) in enumerate(arts, 1):
                    plan.append(('https://blog.csdn.net/lovelion/article/details/%s' % aid,
                                 '%s/%02d-%s/%02d-%s.md' % (name, j, sub, i, t)))
    return plan


# ---------------- 转换 ----------------
def clean(s):
    s = s.replace('\xad', '').replace('\u200b', '').replace('\ufeff', '')
    s = re.sub(r'[\s\u00a0]+', ' ', s)
    s = re.sub(r'\s+([，。、：；！？）】》」』…％])', r'\1', s)
    s = re.sub(r'([（【《「『])\s+', r'\1', s)
    return s.strip()


_img_cache = {}


def dl_img(src):
    src = src.split('?')[0]
    if src in _img_cache:
        return _img_cache[src]
    base = os.path.basename(src)
    if not os.path.splitext(base)[1]:
        base += '.png'
    local = os.path.join(IMG, base)
    if os.path.exists(local) and os.path.getsize(local) > 0:
        _img_cache[src] = local
        return local
    for i in range(3):
        try:
            req = urllib.request.Request(src, headers={'User-Agent': UA, 'Referer': 'https://blog.csdn.net/'})
            with urllib.request.urlopen(req, timeout=30) as r:
                ct = r.headers.get('Content-Type', '')
                data = r.read()
            if 'image' not in ct or len(data) < 60:
                break
            ext = mimetypes.guess_extension(ct.split(';')[0].strip()) or os.path.splitext(base)[1] or '.png'
            if ext == '.jpe':
                ext = '.jpg'
            if os.path.splitext(base)[1] != ext:
                base = os.path.splitext(base)[0] + ext
                local = os.path.join(IMG, base)
            os.makedirs(IMG, exist_ok=True)
            open(local, 'wb').write(data)
            time.sleep(0.2)
            _img_cache[src] = local
            return local
        except Exception:
            time.sleep(1 + i)
    _img_cache[src] = None
    return None


def inline(el, prefix=''):
    out = []
    for ch in el.children:
        if isinstance(ch, NavigableString):
            out.append(str(ch))
            continue
        if not isinstance(ch, Tag):
            continue
        n = ch.name
        if n in ('script', 'style', 'svg'):
            continue
        if n == 'br':
            out.append(' ')
            continue
        if n == 'img':
            local = dl_img(ch.get('src') or '')
            if local:
                rel = prefix + '_img/' + os.path.basename(local)
                out.append('![%s](%s)' % (clean(ch.get('alt') or ''), rel))
            continue
        if n == 'code':
            out.append('`%s`' % ch.get_text('', strip=False).strip())
            continue
        out.append(inline(ch, prefix))
    return clean(''.join(out))


def render_table(t, lines, prefix):
    rows = t.find_all('tr')
    cells_per_row = [len(r.find_all(['td', 'th'])) for r in rows]
    layout = bool(t.find('table')) or (max(cells_per_row or [0]) <= 1)
    if layout:
        txt = inline(t, prefix)
        if txt:
            lines.append('> ' + txt)
            lines.append('')
        return
    data = [[inline(c, prefix) for c in r.find_all(['td', 'th'])] for r in rows]
    data = [r for r in data if any(x for x in r)]
    if not data:
        return
    w = max(len(r) for r in data)
    lines.append('| ' + ' | '.join(data[0] + [''] * (w - len(data[0]))) + ' |')
    lines.append('|' + '---|' * w)
    for r in data[1:]:
        lines.append('| ' + ' | '.join(r + [''] * (w - len(r))) + ' |')
    lines.append('')


def render_list(el, lines, prefix, depth):
    ordered = el.name == 'ol'
    for i, li in enumerate(el.find_all('li', recursive=False), 1):
        parts = []
        for ch in li.children:
            if isinstance(ch, Tag) and ch.name in ('ul', 'ol'):
                continue
            if isinstance(ch, NavigableString):
                parts.append(str(ch))
            elif isinstance(ch, Tag):
                parts.append(inline(ch, prefix) if ch.name not in ('img',) else inline(ch, prefix))
        txt = clean(''.join(parts))
        if txt:
            lines.append(' ' * (depth * 2) + ('%d. ' % i if ordered else '- ') + txt)
        for sub in li.find_all(recursive=False):
            if sub.name in ('ul', 'ol'):
                render_list(sub, lines, prefix, depth + 1)


def render(el, lines, prefix):
    for ch in el.children:
        if isinstance(ch, NavigableString):
            t = str(ch).strip()
            if t:
                lines.append(clean(t))
                lines.append('')
            continue
        if not isinstance(ch, Tag):
            continue
        n = ch.name
        if n in ('script', 'style', 'svg', 'button', 'iframe'):
            continue
        if n in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            t = inline(ch, prefix)
            if t:
                lines.append('#' * int(n[1]) + ' ' + t)
                lines.append('')
        elif n == 'p':
            t = inline(ch, prefix)
            if t:
                lines.append(t)
                lines.append('')
        elif n == 'pre':
            code_el = ch.find('code')
            lang = ''
            if code_el is not None:
                m = re.search(r'language-([\w+#-]+)', ' '.join(code_el.get('class') or []))
                if m:
                    lang = m.group(1)
            code = (code_el or ch).get_text('', strip=False)
            lines.append('```' + lang)
            lines.append(code.strip('\n'))
            lines.append('```')
            lines.append('')
        elif n == 'table':
            render_table(ch, lines, prefix)
        elif n in ('ul', 'ol'):
            render_list(ch, lines, prefix, 0)
            lines.append('')
        elif n == 'img':
            local = dl_img(ch.get('src') or '')
            if local:
                lines.append('![%s](%s)' % (clean(ch.get('alt') or ''), prefix + '_img/' + os.path.basename(local)))
                lines.append('')
        elif n == 'blockquote':
            t = inline(ch, prefix)
            if t:
                lines.append('> ' + t)
                lines.append('')
        elif n in ('div', 'article', 'section', 'span', 'strong', 'em', 'a', 'code', 'center', 'font', 'tbody', 'tr', 'td'):
            if n in ('span', 'strong', 'em', 'a', 'code', 'font'):
                t = inline(ch, prefix)
                if t:
                    lines.append(t)
                    lines.append('')
            else:
                render(ch, lines, prefix)
        else:
            render(ch, lines, prefix)


def convert(html_text, prefix=''):
    soup = BeautifulSoup(html_text, 'html.parser')
    m = soup.select_one('#content_views')
    lines = []
    if m is None:
        return ''
    # 标题（文章自身 H1，在 content_views 之外）
    h1 = soup.select_one('h1.title-article') or soup.select_one('h1')
    if h1 is not None:
        t = clean(h1.get_text(' ', strip=True))
        t = re.sub(r'(_|-)?CSDN博客$', '', t)
        if t:
            lines.append('# ' + t)
            lines.append('')
    render(m, lines, prefix)
    txt = '\n'.join(lines)
    txt = re.sub(r'\n{3,}', '\n\n', txt)
    return txt.strip() + '\n'


def main():
    plan = build_plan()
    print('pages: %d' % len(plan))
    fails = []
    for i, (url, rel) in enumerate(plan):
        out = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        try:
            h = fetch(url)
        except Exception as e:
            fails.append((url, rel, repr(e)[:80]))
            print('  FAIL %s %s' % (rel, e), flush=True)
            continue
        md = convert(h, '../' * rel.count('/'))
        open(out, 'w', encoding='utf-8').write(md)
        if (i + 1) % 20 == 0 or i == 0:
            print('  [%d/%d] %s (%dB)' % (i + 1, len(plan), rel, len(md)), flush=True)
    print('done. fails=%d' % len(fails))
    for f in fails:
        print('  ', f)
    print('images: %d' % (len([f for f in os.listdir(IMG)]) if os.path.isdir(IMG) else 0))


if __name__ == '__main__':
    main()