#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图灵社区《开源软件架构》(The Architecture of Open Source Applications, 中文版) → markdown 树。

来源：https://www.ituring.com.cn/book/1143（图书 id 1143，miniBookId 19）
    —— 图灵社区是 Vue SPA，页面本身没有正文；正文藏在 JSON API：
       GET https://api.ituring.com.cn/api/Book/mini/<章节id>  → {subject, htmlOfBody}
       （章节列表来自 GET https://api.ituring.com.cn/api/book/1143 的 ebook.chapters）
       ⚠️ 「/api/book/1143」这种猜测的路径会返回 SPA 外壳，真正 API 在 api.ituring.com.cn

产出树（site/）：
    前言（卷一）.md
    卷1/<第N章 ....md>     ← subject 去掉「卷1：」前缀
    卷2/<第N章 ....md>     ← subject 去掉「卷2：」前缀

图片：全部下载到 site/_img/ 后交给 scripts/yuque_rewrite_images.py 传语雀 CDN。
  - http://www.aosabook.org/images/X  → https://aosabook.org/static/X（站点改版，旧路径 404）
  - http://raw.github.com/...         → https://raw.githubusercontent.com/...
  - /download/xxxx（无 host）          → https://download.ituring.com.cn/download/xxxx

用法: python3 build.py            # 全量（带 raw 缓存）
      python3 build.py --refresh  # 重新拉 API
"""
import os, re, sys, json, html, time, hashlib, mimetypes, urllib.request, urllib.error
from bs4 import BeautifulSoup, Tag, NavigableString

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
OUT = os.path.join(HERE, 'site')
IMGDIR = os.path.join(OUT, '_img')
BOOK = 'https://api.ituring.com.cn/api/book/1143'
MINI = 'https://api.ituring.com.cn/api/Book/mini/%s'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')


def fetch(url, tries=6, timeout=30):
    last = ''
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': UA, 'Accept': 'application/json,text/html,*/*'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last = repr(e)
            time.sleep(2 + 2 * i)
    raise RuntimeError('fetch fail %s: %s' % (url, last))


def fetch_json(url, tries=6):
    return json.loads(fetch(url, tries).decode('utf-8', 'replace'))


# ---------------- 转换（复用 csdn-lovelion 的 render 家族，已适配脏 HTML） ----------------
def clean(s):
    s = s.replace('\xad', '').replace('\u200b', '').replace('\ufeff', '')
    s = re.sub(r'[\s\u00a0]+', ' ', s)
    s = re.sub(r'\s+([，。、：；！？）】》」』…％])', r'\1', s)
    s = re.sub(r'([（【《「『])\s+', r'\1', s)
    return s.strip()


_img_names = {}   # url -> basename


def norm_src(src):
    """把历史外链归一化到当前可访问地址"""
    if not src:
        return src
    if src.startswith('/download/'):
        return 'https://download.ituring.com.cn' + src
    if src.startswith('http://www.aosabook.org/images/'):
        return src.replace('http://www.aosabook.org/images/', 'https://aosabook.org/static/')
    if src.startswith('http://aosabook.org/images/'):
        return src.replace('http://aosabook.org/images/', 'https://aosabook.org/static/')
    if src.startswith('http://raw.github.com/'):
        return src.replace('http://raw.github.com/', 'https://raw.githubusercontent.com/')
    if src.startswith('https://raw.github.com/'):
        src = src.replace('https://raw.github.com/', 'https://raw.githubusercontent.com/')
    # 已下线的图床：仓库 stfairy/aosa-violet 已不存在 → 同名图在官方站静态目录里有
    # （https://raw.github.com/stfairy/aosa-violet/master/X.png → aosabook.org/static/violet/X.png）
    if 'aosa-violet' in src:
        return 'https://aosabook.org/static/violet/' + os.path.basename(src)
    return src


def dl_img(src):
    if not src:
        return None
    src = norm_src(src)
    if src in _img_names:
        return _img_names[src]
    base = os.path.basename(src.split('?')[0])
    if not base or '.' not in base:
        base = hashlib.md5(src.encode()).hexdigest()[:10] + '.png'
    local = os.path.join(IMGDIR, base)
    if os.path.exists(local) and os.path.getsize(local) > 0:
        _img_names[src] = base
        return base
    for i in range(4):
        try:
            data = fetch(src, tries=2, timeout=60)
            ct = ''
            ext = mimetypes.guess_extension((ct or '').split(';')[0].strip()) or os.path.splitext(base)[1] or '.png'
            if ext == '.jpe':
                ext = '.jpg'
            if os.path.splitext(base)[1].lower() != ext.lower():
                base = os.path.splitext(base)[0] + ext
                local = os.path.join(IMGDIR, base)
            os.makedirs(IMGDIR, exist_ok=True)
            with open(local, 'wb') as f:
                f.write(data)
            _img_names[src] = base
            return base
        except Exception as e:
            sys.stderr.write('img retry %s: %r\n' % (src, e))
            time.sleep(1 + i)
    sys.stderr.write('img FAIL %s\n' % src)
    _img_names[src] = None
    return None


def inline(el, prefix=''):
    out = []
    for ch in el.children:
        if isinstance(ch, NavigableString):
            out.append(str(ch)); continue
        if not isinstance(ch, Tag):
            continue
        n = ch.name
        if n in ('script', 'style', 'svg'):
            continue
        if n == 'br':
            out.append(' '); continue
        if n == 'img':
            base = dl_img(ch.get('src') or '')
            if base:
                out.append('![%s](%s_img/%s)' % (clean(ch.get('alt') or ''), prefix, base))
            continue
        if n == 'code':
            out.append('`%s`' % ch.get_text('', strip=False).strip()); continue
        if n == 'hr':
            out.append(' '); continue
        out.append(inline(ch, prefix))
    return clean(''.join(out))


def render_table(t, lines, prefix):
    rows = t.find_all('tr')
    data = []
    for r in rows:
        cells = [inline(c, prefix) for c in r.find_all(['td', 'th'])]
        if any(cells):
            data.append(cells)
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
                parts.append(inline(ch, prefix))
        txt = clean(''.join(parts))
        if txt:
            lines.append(' ' * (depth * 2) + ('%d. ' % i if ordered else '- ') + txt)
        for sub in li.find_all('ul', recursive=False) + li.find_all('ol', recursive=False):
            render_list(sub, lines, prefix, depth + 1)
    lines.append('')


BLOCK = ('p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'pre', 'table', 'blockquote', 'div')


def render(el, lines, prefix):
    for ch in el.children:
        if isinstance(ch, NavigableString):
            t = str(ch).strip()
            if t:
                lines.append(clean(t)); lines.append('')
            continue
        if not isinstance(ch, Tag):
            continue
        n = ch.name
        if n in ('script', 'style', 'svg', 'button', 'iframe'):
            continue
        if n in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            t = inline(ch, prefix)
            if t:
                lines.append('#' * int(n[1]) + ' ' + t); lines.append('')
        elif n == 'p':
            # 脏 HTML 里 <p> 会互相嵌套（缺 </p>）→ 含块级子元素时下钻，别 inline 成大段
            if ch.find(BLOCK) is not None:
                render(ch, lines, prefix)
            else:
                t = inline(ch, prefix)
                if t:
                    lines.append(t); lines.append('')
        elif n == 'pre':
            code_el = ch.find('code')
            lang = ''
            if code_el is not None:
                m = re.search(r'language-([\w+#-]+)', ' '.join(code_el.get('class') or []))
                if m:
                    lang = m.group(1)
            code = (code_el or ch).get_text('', strip=False)
            lines.append('```' + lang); lines.append(code.strip('\n')); lines.append('```'); lines.append('')
        elif n == 'table':
            render_table(ch, lines, prefix)
        elif n in ('ul', 'ol'):
            render_list(ch, lines, prefix, 0)
        elif n == 'img':
            base = dl_img(ch.get('src') or '')
            if base:
                lines.append('![%s](%s_img/%s)' % (clean(ch.get('alt') or ''), prefix, base)); lines.append('')
        elif n == 'blockquote':
            t = inline(ch, prefix)
            if t:
                lines.append('> ' + t); lines.append('')
        elif n == 'hr':
            lines.append('---'); lines.append('')
        elif n == 'br':
            lines.append('')
        else:
            render(ch, lines, prefix)


def convert_body(html_text, prefix=''):
    soup = BeautifulSoup(html_text, 'html.parser')
    lines = []
    render(soup, lines, prefix)
    # 折叠连续空行
    out = []
    for ln in lines:
        if ln == '' and out and out[-1] == '':
            continue
        out.append(ln)
    return '\n'.join(out).strip() + '\n'


# ---------------- 树 ----------------
def safe(name):
    name = re.sub(r'\s+', ' ', name).strip()
    return name.replace('/', '／')


def main():
    refresh = '--refresh' in sys.argv
    os.makedirs(RAW, exist_ok=True)
    bk_fp = os.path.join(RAW, '_book.json')
    if refresh or not os.path.exists(bk_fp):
        bk = fetch_json(BOOK)
        json.dump(bk, open(bk_fp, 'w'), ensure_ascii=False)
    bk = json.load(open(bk_fp))
    chs = bk['ebook']['chapters']
    print('章节数:', len(chs))

    chapters = []
    for c in chs:
        cid = str(c['id'])
        fp = os.path.join(RAW, cid + '.json')
        if refresh or not os.path.exists(fp):
            d = fetch_json(MINI % cid)
            json.dump(d, open(fp, 'w'), ensure_ascii=False)
            time.sleep(0.4)
        d = json.load(open(fp))
        chapters.append({'id': cid, 'subject': d.get('subject') or c['subject'],
                         'body': d.get('htmlOfBody') or ''})

    # 组装树：前言 + 卷1/ + 卷2/
    # 注意：_img 缓存不能删（否则每次重跑都全量重下图）；只清 md 和卷目录
    os.makedirs(OUT, exist_ok=True)
    for vol in ('卷1', '卷2'):
        d = os.path.join(OUT, vol)
        if os.path.isdir(d):
            import shutil; shutil.rmtree(d)
    for fn in os.listdir(OUT):
        if fn.endswith('.md'):
            os.remove(os.path.join(OUT, fn))
    plan = []            # (relpath, chapter)
    seen_titles = {}
    for ch in chapters:
        subj = re.sub(r'\s+', ' ', ch['subject']).strip()
        m = re.match(r'^卷([12])：\s*(.+)$', subj)
        if not m:
            rel = safe(subj) + '.md'          # 前言（卷一）
        else:
            vol, title = m.group(1), m.group(2)
            title = safe(title)
            # 同卷同名（如两个「第6章 Git」＝两份独立译文）→ 加「（译文一/二）」
            key = (vol, title)
            n = seen_titles.get(key, 0) + 1
            seen_titles[key] = n
            rel = '卷%s/%s.md' % (vol, title)
            if n > 1:
                # 回填前一份为「译文一」，本份为「译文N」
                ch_list = [p for p in plan if p[0].startswith('卷%s/%s' % (vol, title))]
                if ch_list and '（译文' not in ch_list[0][0]:
                    old = ch_list[0][0]
                    ch_list[0][0] = old[:-3] + '（译文一）.md'
                rel = '卷%s/%s（译文%s）.md' % (vol, title, '一二三四五六七八九'[n - 1])
        plan.append([rel, ch])

    for rel, ch in plan:
        depth = rel.count('/')
        prefix = '../' * depth
        md = convert_body(ch['body'], prefix)
        fp = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(md)
        print('  %-52s %6d B  imgs=%d' % (rel, len(md), md.count('![')))

    print('文档数:', len(plan), '| 图片:', len([1 for k, v in _img_names.items() if v]))


if __name__ == '__main__':
    main()