#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LaTeX 书稿 → 语雀导入树（Markdown）。首例：wuzhouhui/awk《AWK 程序设计语言》中文译本。

输入：latex_src/*.tex（8 章 + 前言 + 2 附录 + 索引），图片用 crop_fig3.py 从编译好的中文 PDF 里裁。
输出：<out>/ 导入树（一章一个 TITLE 目录，一节一篇文档；图存 images/）。

设计要点见 README.md。
"""
import os
import re
import shutil
import sys

SRC = '/home/admin/.openclaw/workspace/tmp/awk64/latex_src'
FIGS = '/home/admin/.openclaw/workspace/tmp/awk64/figs'

# 章节顺序：file, 编号（中文数字或 'A'/'B'/''）, 标题（用于 TITLE 目录）
CHAPTERS = [
    ('preface', '0', '前言'),
    ('an_awk_tutorial', '一', '快速入门'),
    ('the_awk_language', '二', 'Awk 语言'),
    ('data_processing', '三', '数据处理'),
    ('reports_and_databases', '四', '报表与数据库'),
    ('processing_words', '五', '文本处理'),
    ('little_languages', '六', '小语言'),
    ('experiments_with_algorithms', '七', '算法实验'),
    ('epilog', '八', '后记'),
    ('awk_summary', 'A', 'AWK 总结'),
    ('answers_to_selected_exercises', 'B', '部分习题答案'),
    ('index', '', '索引'),
]

# 每章图的出现顺序（tex 里第 k 个图 → 第 k 个文件）
FIG_ORDER = {
    'experiments_with_algorithms': ['exp-insertion', 'exp-partition1', 'exp-partition2',
                                    'exp-quicksort', 'exp-heap10', 'exp-heap-ordered',
                                    'exp-heap-prefix', 'exp-heap-sift', 'exp-heapsort',
                                    'exp-sortcmp'],
    'little_languages': ['lang-pipeline', 'lang-traffic', 'lang-infix'],
    'reports_and_databases': ['rep-format', 'rep-numjust', 'rep-letter', 'rep-qawk'],
    'processing_words': ['proc-grammar'],
}

CN_NUM = {'1': '一', '2': '二', '3': '三', '4': '四', '5': '五', '6': '六', '7': '七', '8': '八',
          '一': '一', '二': '二', '三': '三', '四': '四', '五': '五', '六': '六', '七': '七', '八': '八'}


# ---------------------------------------------------------------- 工具

def read(p):
    return open(p, encoding='utf-8').read()


def protect_verbatim(text):
    """把 verbatim 类环境与 \\verb 先换成占位符，防止 strip_comments 误吃 %。"""
    blocks = []

    def rep(m):
        blocks.append(m.group(0))
        return '\x02%d\x02' % (len(blocks) - 1)

    text = re.sub(r'\\begin\{(awkcode|verbatim|lstlisting)\}.*?\\end\{\1\}', rep, text, flags=re.S)
    text = re.sub(r"\\verb\*?(.)(?:(?!\1).)*?\1", rep, text)
    return text, blocks


def restore_verbatim(text, blocks):
    for i, b in enumerate(blocks):
        text = text.replace('\x02%d\x02' % i, b)
    return text


def strip_comments(s):
    """去掉 % 注释（百分号转义除外）；行尾百分号造成的续行直接拼接。"""
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == '\\' and i + 1 < n:
            out.append(s[i:i + 2])
            i += 2
            continue
        if c == '%':
            j = s.find('\n', i)
            if j < 0:
                break
            i = j  # 保留换行
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def match_brace(s, i, op='{', cl='}'):
    """s[i] == op，返回匹配的 cl 下标（考虑嵌套）。"""
    depth = 0
    j = i
    n = len(s)
    while j < n:
        c = s[j]
        if c == '\\' and j + 1 < n:
            j += 2
            continue
        if c == op:
            depth += 1
        elif c == cl:
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return n - 1  # 跨段落的组：当作到结尾，尽量不炸


def read_arg(s, i):
    """读 {…} 参数，返回 (内容, 新位置)；没有参数返回 (None, i)。"""
    while i < len(s) and s[i] in ' \t\n':
        i += 1
    if i >= len(s) or s[i] != '{':
        return None, i
    j = match_brace(s, i)
    return s[i + 1:j], j + 1


def dedent(text):
    lines = text.split('\n')
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ''
    ind = min((len(l) - len(l.lstrip(' ')) for l in lines if l.strip()), default=0)
    return '\n'.join(l[ind:] if len(l) >= ind else l.lstrip() for l in lines)


def untex_plain(s):
    """把一小段 LaTeX 变成纯文本（语法框用），支持嵌套参数。"""
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == '\\':
            if s[i + 1:i + 2] == '\\':
                out.append('\n')
                i += 2
                continue
            m = re.match(r'\\([a-zA-Z]+)\*?', s[i:])
            if m:
                name = m.group(1)
                j = i + m.end()
                if j < n and s[j] == '[':
                    j = match_brace(s, j, '[', ']') + 1
                if j < n and s[j] == '{':
                    e = match_brace(s, j)
                    out.append(untex_plain(s[j + 1:e]))
                    i = e + 1
                    continue
                if name in ('par', 'newline'):
                    out.append('\n')
                elif name in ('ldots', 'dots', 'cdots'):
                    out.append('…')
                elif name in ('quad', 'qquad'):
                    out.append(' ')
                i = j
                continue
            d = s[i + 1]
            out.append({'\\': '\n', '\\{': '{', '\\}': '}', '%': '%', '&': '&',
                        '$': '$', '_': '_', '#': '#', ' ': ' '}.get(d, d))
            i += 2
            continue
        if c == '$':
            k = s.find('$', i + 1)
            if k > 0:
                out.append(math_inline(s[i + 1:k]))
                i = k + 1
                continue
        out.append(c)
        i += 1
    return ''.join(out)


def clean_title(s):
    """标题去掉行内标记，供文件名/目录名使用。"""
    t = untex_plain(s)
    t = t.replace('``', '“').replace("''", '”')
    t = t.replace(':', '：').replace('/', '／').replace('`', '')
    t = t.replace('： ', '：').replace(' ：', '：')
    t = re.sub(r'\s+', ' ', t).strip()
    return t


# ---------------------------------------------------------------- 编号收集（第 1 遍）

def collect_numbers():
    labels = {}
    seq = []          # [(file, chapter_no, chapter_title)]
    chap_idx = {'A': 'A', 'B': 'B'}
    for fn, cno, ctitle in CHAPTERS:
        seq.append((fn, cno, ctitle))
    for fn, cno, ctitle in seq:
        text = strip_comments(read(os.path.join(SRC, fn + '.tex')))
        # 章标签
        for m in re.finditer(r'\\chapter\{', text):
            arg, _ = read_arg(text, m.end() - 1)
            pass
        labels_hit = re.findall(r'\\label\{(chap:[^}]*)\}', text)
        for lb in labels_hit:
            labels[lb] = cno
        sec_n = 0
        tbl_n = 0
        ex_n = 0
        in_fig = 0
        if fn == 'index':
            continue
        # 顺序扫描：section / figure 里的 caption / exercise
        i = 0
        n = len(text)
        while i < n:
            m = re.compile(r'\\(section\*?|subsection\*?|begin\{figure\}|begin\{exercise\}|caption)\{?').search(text, i)
            if not m:
                break
            cmd = m.group(1)
            i = m.end()
            if cmd.startswith('section'):
                sec_n += 1
                if not cmd.endswith('*'):
                    lb, _ = read_arg(text, m.end() - 1)
                    if lb and '\\label{' in text[m.end():m.end() + 60]:
                        pass
                # 找紧随其后的 label
                seg = text[m.end():m.end() + 200]
                mm = re.search(r'\\label\{(sec:[^}]*)\}', seg)
                if mm and not cmd.endswith('*'):
                    labels[mm.group(1)] = f'{cno}.{sec_n}' if cno not in ('A', 'B') else f'{cno}.{sec_n}'
            elif cmd == 'begin{figure}':
                # figure 里 caption 才算表；tikz 图无 caption
                seg = text[m.end():m.end() + 400]
                mm = re.search(r'\\caption\{', seg)
                if mm:
                    tbl_n += 1
                    lab = re.search(r'\\label\{(tbl:[^}]*)\}', text[m.end() + mm.start():m.end() + mm.start() + 200])
                    if lab:
                        labels[lab.group(1)] = f'{cno}.{tbl_n}'
            elif cmd == 'begin{exercise}':
                ex_n += 1
                seg = text[m.end():m.end() + 200]
                mm = re.search(r'\\label\{(exer:[^}]*)\}', seg)
                if mm:
                    labels[mm.group(1)] = f'{cno}.{ex_n}'
    return labels


# ---------------------------------------------------------------- 渲染

class Ctx:
    def __init__(self, fn, labels, images):
        self.fn = fn
        self.labels = labels
        self.images = list(images)
        self.blocks = []
        self.sec_no = 0
        self.tbl_no = 0
        self.ex_no = 0
        self.chap_no = ''

    def block(self, md):
        """登记一个块，返回哨兵。"""
        self.blocks.append(md)
        return f'\x01{len(self.blocks) - 1}\x01'


def inline(s, ctx):
    """行内 LaTeX → Markdown。"""
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == '\\':
            if i + 1 >= n:
                i += 1
                continue
            d = s[i + 1]
            if d.isalpha():
                j = i + 1
                while j < n and s[j].isalpha():
                    j += 1
                name = s[i + 1:j]
                i = j
                star = ''
                if i < n and s[i] == '*':
                    star = '*'
                    i += 1
                if name == 'verb':
                    if i >= n:
                        break
                    delim = s[i]
                    k = s.find(delim, i + 1)
                    if k < 0:
                        k = n
                    body = s[i + 1:k]
                    i = k + 1
                    out.append(code_span(body))
                    continue
                if i < n and s[i] == '[':
                    e = match_brace(s, i, '[', ']')
                    opt = s[i + 1:e]
                    i = e + 1
                else:
                    opt = None
                if name == 'begin' or name == 'end':
                    # 未知环境残余：吃掉 {name}
                    if i < n and s[i] == '{':
                        e = match_brace(s, i)
                        i = e + 1
                    continue
                if name in ARG1:
                    arg, i2 = read_arg(s, i)
                    if arg is None:
                        continue
                    i = i2
                    out.append(ARG1[name](arg, ctx, star))
                    continue
                if name in ARG2:
                    a1, i2 = read_arg(s, i)
                    i = i2
                    a2, i3 = read_arg(s, i)
                    i = i3
                    out.append(ARG2[name](a1 or '', a2 or '', ctx))
                    continue
                if name == 'multicolumn':
                    a1, i2 = read_arg(s, i)
                    a2, i3 = read_arg(s, i2)
                    a3, i4 = read_arg(s, i3)
                    i = i4
                    out.append(inline(a3 or '', ctx))
                    continue
                if name == 'pdfbookmark':
                    a1, i2 = read_arg(s, i)
                    a2, i3 = read_arg(s, i2)
                    a3, i4 = read_arg(s, i3)
                    i = i4
                    continue
                if name in NOARG:
                    out.append(NOARG[name])
                    continue
                # 未知命令：若有参数，吞掉渲染内容
                arg, i2 = read_arg(s, i)
                if arg is not None:
                    out.append(inline(arg, ctx))
                    i = i2
                continue
            else:
                i += 2
                out.append({'\\': '\n', ' ': ' ', '%': '%', '&': '&', '$': '$', '_': '_',
                            '#': '#', '{': '{', '}': '}', ',': ' ', ';': ' ', '!': '',
                            '-': '', '~': ' '}.get(d, d))
                continue
        if c == '{' or c == '}':
            i += 1
            continue
        if c == '$':
            k = s.find('$', i + 1)
            if k > 0:
                out.append(math_inline(s[i + 1:k]))
                i = k + 1
                continue
            i += 1
            continue
        if c == '~':
            out.append(' ')
            i += 1
            continue
        if c == '`' and s[i:i + 2] == '``':
            out.append('“')
            i += 2
            continue
        if c == "'" and s[i:i + 2] == "''":
            out.append('”')
            i += 2
            continue
        if c == '-' and s[i:i + 3] == '---':
            out.append('—')
            i += 3
            continue
        if c == '-' and s[i:i + 2] == '--':
            out.append('–')
            i += 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


MATH_MAP = {'\\_': '_', '\\^': '^', '\\geqslant': '≥', '\\geq': '≥', '\\ge': '≥',
            '\\leqslant': '≤', '\\leq': '≤', '\\le': '≤', '\\ne': '≠', '\\neq': '≠',
            '\\times': '×', '\\pi': 'π', '\\in': '∈', '\\cdots': '…',
            '\\ldots': '…', '\\dots': '…', '\\{': '{', '\\}': '}', '\\%': '%'}


def math_inline(m):
    m = re.sub(r'\\texttt\{([^{}]*)\}', r'`\1`', m)
    for k, v in MATH_MAP.items():
        m = m.replace(k, v)
    m = re.sub(r'\\[a-zA-Z]+', '', m)
    m = m.replace('{', '').replace('}', '').strip()
    return m


def code_span(body):
    body = body.strip()
    if not body:
        return ''
    if '`' in body:
        return '``' + body + '``'
    return '`' + body + '`'


def code_block(body, lang=''):
    body = body.rstrip('\n')
    body = dedent(body)
    fence = '```'
    while fence in body:
        fence += '`'
    return f'{fence}{lang}\n{body}\n{fence}'


def _wrap(fmt):
    def f(arg, ctx, star):
        inner = inline(arg, ctx).strip()
        if not inner:
            return ''
        return fmt(inner)
    return f


def _code(arg, ctx, star):
    return code_span(untex_plain(arg))


def _plain_cmd(txt):
    def f(arg, ctx, star):
        return txt
    return f


def _ref(arg, ctx, star):
    v = ctx.labels.get(arg.strip())
    return v if v is not None else '??'


def _footnote(arg, ctx, star):
    return '（注：' + inline(arg, ctx).strip() + '）'


def _href(u, t, ctx):
    return inline(t, ctx)


ARG1 = {
    'textit': _wrap(lambda x: '*' + x + '*'),
    'textbf': _wrap(lambda x: '**' + x + '**'),
    'emph': _wrap(lambda x: '*' + x + '*'),
    'term': _wrap(lambda x: '*' + x + '*'),
    'cterm': _wrap(lambda x: '**' + x + '**'),
    'texttt': _code,
    'filename': _code,
    'textsf': _wrap(lambda x: x),
    'textrm': _wrap(lambda x: x),
    'text': _wrap(lambda x: x),
    'mbox': _wrap(lambda x: x),
    'textwidth': _wrap(lambda x: x),
    'large': _wrap(lambda x: x),
    'Large': _wrap(lambda x: x),
    'small': _wrap(lambda x: x),
    'normalsize': _wrap(lambda x: x),
    'url': _wrap(lambda x: x),
    'ref': _ref,
    'label': _plain_cmd(''),
    'marginpar': _plain_cmd(''),
    'footnote': _footnote,
    'hspace': _plain_cmd(' '),
    'vspace': _plain_cmd(''),
    'caption': _plain_cmd(''),
    'captionsetup': _plain_cmd(''),
    'index': _plain_cmd(''),
    'makecell': _wrap(lambda x: x.replace('\n', ' ')),
    'myexer': _plain_cmd('习题 '),
    'patact': _plain_cmd('模式–动作'),
    'stmt': _plain_cmd('*statements*'),
    'expr': _plain_cmd('*expression*'),
    'regexpr': _plain_cmd('*regular expression*'),
    'pat': _plain_cmd('*pattern*'),
    'fmt': _plain_cmd('*format*'),
    'awk': _plain_cmd('`awk`'),
    'print': _plain_cmd('`print`'),
    'printf': _plain_cmd('`printf`'),
    'nf': _plain_cmd('`NF`'),
    'nr': _plain_cmd('`NR`'),
    'AND': lambda a, c, s: '`&&`',
    'OR': lambda a, c, s: '`||`',
    'NOT': lambda a, c, s: '`!`',
    'BEGIN': lambda a, c, s: '`BEGIN`',
    'END': lambda a, c, s: '`END`',
    'length': lambda a, c, s: '`length`',
    'while': lambda a, c, s: '`while`',
    'for': lambda a, c, s: '`for`',
    'fs': lambda a, c, s: '`FS`',
    'OFS': lambda a, c, s: '`OFS`',
    'ctn': lambda a, c, s: '`continue`',
    'include': _plain_cmd(''),
    'input': _plain_cmd(''),
    'centering': lambda a, c, s: '',
}

ARG2 = {'href': _href}

NOARG = {
    'par': '\n\n',
    'newline': '\n',
    'hline': '',
    'medskip': '\n\n',
    'bigskip': '\n\n',
    'smallskip': '\n',
    'noindent': '',
    'indent': '',
    'ldots': '…',
    'dots': '…',
    'cdots': '…',
    'quad': ' ',
    'qquad': ' ',
    'textbackslash': '\\',
    'LaTeX': 'LaTeX',
    'TeX': 'TeX',
    'clearpage': '',
    'newpage': '',
    'tableofcontents': '',
    'maketitle': '',
    'frontmatter': '',
    'mainmatter': '',
    'backmatter': '',
    'appendix': '',
    'leftmark': '',
    'rightmark': '',
    'thepage': '',
    'thefootnote': '',
    'value': '',
    'endinput': '',
    'setlength': '',
    'settowidth': '',
    'renewcommand': '',
    'newcommand': '',
    'theoremstyle': '',
    'theoremheaderfont': '',
    'theorembodyfont': '',
    'newtheorem': '',
    'maxheight': '',
    'height': '',
    'width': '',
    'footnotesize': '',
    'scriptsize': '',
    'tiny': '',
    'small': '',
    'normalsize': '',
    'large': '',
    'Large': '',
    'huge': '',
    'Huge': '',
    'bfseries': '',
    'itshape': '',
    'ttfamily': '',
    'sffamily': '',
    'rmfamily': '',
    'normalfont': '',
    'pagebreak': '',
    'vfill': '',
    'hfill': '',
    'protect': '',
    'relax': '',
    'leavevmode': '',
    'raggedright': '',
    'zihao': '',
    'setcounter': '',
    'addtocounter': '',
    'thispagestyle': '',
    'phantomsection': '',
}

# ---------------------------------------------------------------- 块级渲染

def is_cjk(ch):
    return ord(ch) > 0x2E7F


def join_lines(seg):
    """把源码硬换行接上：CJK-CJK 直接接，其余补空格。"""
    lines = [l.strip() for l in seg.split('\n')]
    lines = [l for l in lines if l]
    if not lines:
        return ''
    buf = lines[0]
    for l in lines[1:]:
        if buf and l and is_cjk(buf[-1]) and is_cjk(l[0]):
            buf += l
        else:
            buf += ' ' + l
    return buf


def text_to_md(seg, ctx):
    seg = seg.replace('\r\n', '\n')
    paras = re.split(r'\n[ \t]*\n', seg)
    outs = []
    for p in paras:
        lines = [l.strip() for l in p.split('\n')]
        lines = [l for l in lines if l]
        if not lines:
            continue
        if lines[0].startswith('@@H2@@'):
            outs.append('## ' + inline(lines[0][6:].replace('@@', ''), ctx).strip())
            lines = lines[1:]
            if not lines:
                continue
        if lines[0].startswith('@@H3@@'):
            outs.append('### ' + inline(lines[0][6:].replace('@@', ''), ctx).strip())
            lines = lines[1:]
            if not lines:
                continue
        buf = lines[0]
        for l in lines[1:]:
            if buf and l and is_cjk(buf[-1]) and is_cjk(l[0]):
                buf += l
            else:
                buf += ' ' + l
        try:
            t = inline(buf, ctx)
        except ValueError:
            print('!! INLINE FAIL para:', repr(buf[:400]))
            raise
        t = re.sub(r'[ \t]{2,}', ' ', t)
        t = re.sub(r'(?<=[\u3000-\u303f\u4e00-\u9fff]) (?=[\u3000-\u303f\u4e00-\u9fff])', '', t)
        t = t.strip()
        if t:
            outs.append(t)
    return '\n\n'.join(outs)


def split_top(body, sep):
    """按顶层分隔符切分（考虑 {} 嵌套、反斜杠转义）。"""
    out = []
    depth = 0
    i = 0
    n = len(body)
    cur = []
    L = len(sep)
    while i < n:
        if depth == 0 and body[i:i + L] == sep:
            out.append(''.join(cur))
            cur = []
            i += L
            continue
        c = body[i]
        if c == '\\' and i + 1 < n:
            cur.append(body[i:i + 2])
            i += 2
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        cur.append(c)
        i += 1
    out.append(''.join(cur))
    return out


def take_image(ctx):
    if not ctx.images:
        return '（图：缺失）'
    name = ctx.images.pop(0)
    return f'![{name}](images/{name}.png)'


def parse_tabular(body, ctx):
    if 'tikzpicture' in body:
        return ctx.block(take_image(ctx))
    body = body.strip()
    if body.startswith('{'):
        j = match_brace(body, 0)
        body = body[j + 1:]
    rows = []
    for raw in split_top(body, '\\\\'):
        raw = raw.replace('\\hline', '')
        raw = re.sub(r'^\s*\[[^\]]*\]', '', raw)
        raw = re.sub(r'\\cline\{[^}]*\}', '', raw)
        if not raw.strip():
            continue
        cells = [re.sub(r'[ \t]{2,}', ' ',
                        inline(join_lines(c.replace('\\\\', ' ')), ctx)).strip()
                 for c in split_top(raw, '&')]
        rows.append(cells)
    if not rows:
        return ''
    ncol = max(len(r) for r in rows)
    rows = [r + [''] * (ncol - len(r)) for r in rows]
    has_head = '\\hline' in body
    if not has_head:
        rows = [[''] * ncol] + rows
    def esc(c):
        return c.replace('|', '\\|').replace('\n', ' ')
    lines = ['| ' + ' | '.join(esc(c) for c in rows[0]) + ' |',
             '|' + '|'.join([' --- '] * ncol) + '|']
    for r in rows[1:]:
        lines.append('| ' + ' | '.join(esc(c) for c in r) + ' |')
    return '\n'.join(lines)


def parse_tabbing(body, ctx):
    rows = []
    for raw in split_top(body, '\\\\'):
        if not raw.strip():
            continue
        m = re.search(r'\\[>=]', raw)
        if m:
            left, right = raw[:m.start()], raw[m.end():]
        else:
            left, right = raw, ''
        left = re.sub(r'\\hspace\{[^}]*\}', '', left)
        rows.append((re.sub(r'[ \t]{2,}', ' ', inline(join_lines(left), ctx)).strip(),
                     re.sub(r'[ \t]{2,}', ' ', inline(join_lines(right), ctx)).strip()))
    if not rows:
        return ''
    out = ['| 形式 | 说明 |', '| --- | --- |']
    for l, r in rows:
        out.append(f'| {l.replace("|", "\\|")} | {r.replace("|", "\\|")} |')
    return '\n'.join(out)


def render_env(name, body, ctx):
    if name in ('awkcode', 'verbatim', 'lstlisting'):
        return ctx.block(code_block(body))
    if name == 'pattern':
        txt = untex_plain(body)
        txt = re.sub(r'\n[ \t]*\n', '\n', txt)
        return ctx.block(code_block(txt, 'text'))
    if name == 'tikzpicture':
        return ctx.block(take_image(ctx))
    if name == 'tabular':
        return ctx.block(parse_tabular(body, ctx))
    if name == 'tabbing':
        return ctx.block(parse_tabbing(body, ctx))
    if name == 'figure':
        cap = re.search(r'\\caption\{', body)
        head = ''
        rest = body
        if cap:
            arg, pos = read_arg(body, cap.end() - 1)
            ctx.tbl_no += 1
            head = f'**表 {ctx.chap_no}.{ctx.tbl_no}** {inline(arg or "", ctx).strip()}'
            rest = body[:cap.start()] + body[pos:]
        inner = render_blocks(rest, ctx)
        return (head + '\n\n' + inner) if head else inner
    if name in ('center', 'flushright', 'multicols', 'mdframed', 'varwidth', 'titlepage'):
        if 'tikzpicture' in body or 'includegraphics' in body:
            return ctx.block(take_image(ctx))
        return render_blocks(body, ctx)
    if name == 'includegraphics':
        return ctx.block(take_image(ctx))
    if name in ('quote', 'quotation'):
        inner = render_blocks(body, ctx).strip()
        if not inner:
            return ''
        if re.search(r'\x01\d+\x01', inner):
            return inner          # 内含表格/代码块：直接透出，不套引用块
        quoted = '\n'.join(('> ' + l.lstrip()) if l.strip() else '>' for l in inner.split('\n'))
        return ctx.block(quoted)
    if name == 'summary':
        arg, pos = read_arg(body, 0)
        title = inline(arg or '', ctx).strip()
        inner = render_blocks(body[pos:] if arg is not None else body, ctx).strip()
        return f'### {title}\n\n{inner}'
    if name == 'exercise':
        ctx.ex_no += 1
        body = re.sub(r'^\s*\\label\{[^}]*\}', '', body)
        inner = render_blocks(body, ctx).strip()
        no = ctx.chap_no
        return f'**习题 {no}.{ctx.ex_no}** {inner}'
    if name in ('enumerate', 'itemize'):
        items = re.split(r'\\item(?![a-zA-Z])', body)
        items = [it for it in items[1:]]
        out = []
        for k, it in enumerate(items, 1):
            inner = render_blocks(it, ctx).strip()
            if not inner:
                continue
            ls = inner.split('\n')
            if name == 'enumerate':
                head = f'{k}. '
            else:
                head = '- '
            buf = [head + ls[0]]
            for l in ls[1:]:
                buf.append(('   ' + l) if l.strip() else '')
            out.append('\n'.join(buf))
        return '\n'.join(out)
    # 透明容器
    return render_blocks(body, ctx)


BEGIN_RE = re.compile(r'\\begin\{([A-Za-z]+\*?)\}')


def render_blocks(s, ctx):
    out = []
    i = 0
    n = len(s)
    while True:
        m = BEGIN_RE.search(s, i)
        if not m:
            out.append(text_to_md(s[i:], ctx))
            break
        name = m.group(1)
        out.append(text_to_md(s[i:m.start()], ctx))
        pat = re.compile(r'\\(begin|end)\{' + re.escape(name) + r'\}')
        depth = 1
        j = m.end()
        endpos = None
        while depth:
            m2 = pat.search(s, j)
            if not m2:
                endpos = None
                break
            if m2.group(1) == 'begin':
                depth += 1
            else:
                depth -= 1
                if depth == 0:
                    endpos = m2.start()
                    j = m2.end()
        if endpos is None:
            out.append(text_to_md(s[m.start():], ctx))
            break
        body = s[m.end():endpos]
        if body.startswith('['):
            try:
                e = match_brace(body, 0, '[', ']')
                body = body[e + 1:]
            except ValueError:
                pass
        out.append(render_env(name, body, ctx))
        i = j
    return '\n\n'.join(x for x in out if x is not None and x.strip() != '')


def subst(md, ctx):
    for _ in range(6):
        if '\x01' not in md:
            break
        md = re.sub(r'\x01(\d+)\x01', lambda m: '\n\n' + ctx.blocks[int(m.group(1))] + '\n\n', md)
    md = re.sub(r'[ \t]+\n', '\n', md)
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md.strip() + '\n'


def finish(md, ctx):
    md = re.sub(r'[ \t]*\x01(\d+)\x01[ \t]*',
                lambda m: '\n\n\x01' + m.group(1) + '\x01\n\n', md)
    md = re.sub(r'[ \t]+\n', '\n', md)
    md = re.sub(r'\n{3,}', '\n\n', md)
    md = subst(md, ctx)
    return md

NOARG.update({
    'patact': '模式–动作',
    'stmt': '*statements*',
    'expr': '*expression*',
    'regexpr': '*regular expression*',
    'pat': '*pattern*',
    'fmt': '*format*',
    'myexer': '习题 ',
    'awk': '`awk`',
    'print': '`print`',
    'printf': '`printf`',
    'nf': '`NF`',
    'nr': '`NR`',
    'AND': '`&&`',
    'OR': '`||`',
    'NOT': '`!`',
    'BEGIN': '`BEGIN`',
    'END': '`END`',
    'length': '`length`',
    'while': '`while`',
    'for': '`for`',
    'fs': '`FS`',
    'OFS': '`OFS`',
    'ctn': '`continue`',
})
for _k in ['patact', 'stmt', 'expr', 'regexpr', 'pat', 'fmt', 'myexer', 'awk', 'print',
           'printf', 'nf', 'nr', 'AND', 'OR', 'NOT', 'BEGIN', 'END', 'length', 'while',
           'for', 'fs', 'OFS', 'ctn']:
    ARG1.pop(_k, None)
