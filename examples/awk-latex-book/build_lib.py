#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wuzhouhui/awk《AWK 程序设计语言》中文译本 → 语雀导入树。

用法：python3 build_lib.py <out_dir>
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import latex2md as L  # noqa: E402

SRC = '/home/admin/.openclaw/workspace/tmp/awk64/latex_src'
FIGS = '/home/admin/.openclaw/workspace/tmp/awk64/figs'

# (文件, 中文编号（第N章/附录）, 阿拉伯数字编号（节号）, 标题)
CHAPTERS = [
    ('preface', '', '', '前言'),
    ('an_awk_tutorial', '一', '1', '快速入门'),
    ('the_awk_language', '二', '2', 'Awk 语言'),
    ('data_processing', '三', '3', '数据处理'),
    ('reports_and_databases', '四', '4', '报表与数据库'),
    ('processing_words', '五', '5', '文本处理'),
    ('little_languages', '六', '6', '小语言'),
    ('experiments_with_algorithms', '七', '7', '算法实验'),
    ('epilog', '八', '8', '后记'),
    ('awk_summary', 'A', 'A', 'AWK 总结'),
    ('answers_to_selected_exercises', 'B', 'B', '部分习题答案'),
    ('index', '', '', '索引'),
]

FIG_ORDER = {
    'experiments_with_algorithms': ['exp-insertion', 'exp-partition1', 'exp-partition2',
                                    'exp-quicksort', 'exp-heap10', 'exp-heap-ordered',
                                    'exp-heap-prefix', 'exp-heap-sift', 'exp-heapsort',
                                    'exp-sortcmp'],
    'little_languages': ['lang-pipeline', 'lang-traffic', 'lang-infix'],
    'reports_and_databases': ['rep-format', 'rep-numjust', 'rep-letter', 'rep-qawk'],
    'processing_words': ['proc-grammar'],
}


def pass1():
    """收集 chap/sec/tbl/exer 编号，供 \\ref 解析。"""
    labels = {}
    for fn, cno, ar, _ in CHAPTERS:
        raw, vblocks = L.protect_verbatim(L.read(os.path.join(SRC, fn + '.tex')))
        text = L.restore_verbatim(L.strip_comments(raw), vblocks)
        for lb in re.findall(r'\\label\{(chap:[^}]*)\}', text):
            labels[lb] = cno if cno else ''
        if fn == 'index':
            continue
        sec = tbl = ex = 0
        i = 0
        rx = re.compile(r'\\(section\*?|begin\{figure\}|begin\{exercise\})')
        while True:
            m = rx.search(text, i)
            if not m:
                break
            kind = m.group(1)
            i = m.end()
            if kind == 'section':
                sec += 1
                lab = re.search(r'\\label\{(sec:[^}]*)\}', text[i:i + 300])
                if lab:
                    labels[lab.group(1)] = f'{ar}.{sec}'
            elif kind == 'begin{figure}':
                cap = re.compile(r'\\caption').search(text, i)
                endfig = text.find('\\end{figure}', i)
                if cap and (endfig < 0 or cap.start() < endfig):
                    tbl += 1
                    lab = re.search(r'\\label\{(tbl:[^}]*)\}', text[cap.start():cap.start() + 300])
                    if lab:
                        labels[lab.group(1)] = f'{ar}.{tbl}'
                    i = cap.start()
            elif kind == 'begin{exercise}':
                ex += 1
                lab = re.search(r'\\label\{(exer:[^}]*)\}', text[i:i + 300])
                if lab:
                    labels[lab.group(1)] = f'{ar}.{ex}'
    return labels


def mark_headings(text):
    """\subsection{..}/\subsubsection{..}/\section*{..} → @@H2/H3@@ 段落标记（支持嵌套花括号）。"""
    for cmd, marker in (('subsection', '@@H2@@'), ('subsubsection', '@@H3@@'),
                        ('section*', '@@H2@@')):
        pat = '\\' + cmd + '{'
        out = []
        i = 0
        while True:
            k = text.find(pat, i)
            if k < 0:
                out.append(text[i:])
                break
            if cmd == 'subsection' and text[max(0, k - 3):k] == 'sub':
                out.append(text[i:k + 3])
                i = k + 3
                continue
            out.append(text[i:k])
            j = k + len(pat) - 1
            e = L.match_brace(text, j)
            out.append('\n\n' + marker + text[j + 1:e] + '@@\n\n')
            i = e + 1
        text = ''.join(out)
    return text


def strip_chapter_head(body):
    body = re.sub(r'^\s*\\chapter\{[^}]*\}', '', body)
    body = re.sub(r'^\s*\\label\{[^}]*\}', '', body)
    return body


def build_sections(text):
    """切成 [(kind, title, body)]；kind in pre/sec/secstar。"""
    ms = list(re.finditer(r'\\section(\*?)\{', text))
    chunks = []
    if not ms:
        return [('only', '', text)]
    chunks.append(('pre', '', text[:ms[0].start()]))
    for k, m in enumerate(ms):
        arg, after = L.read_arg(text, m.end() - 1)
        end = ms[k + 1].start() if k + 1 < len(ms) else len(text)
        kind = 'secstar' if m.group(1) == '*' else 'sec'
        chunks.append((kind, arg or '', text[after:end]))
    return chunks


def build_index(text, ctx):
    text = re.sub(r'\\begin\{multicols\}\{[^}]*\}', '', text)
    text = re.sub(r'\\end\{multicols\}', '', text)
    text = re.sub(r'\\setlength\s*\\parindent\{[^}]*\}', '', text)
    groups = list(re.finditer(r'\\pdfbookmark\[2\]\{([^}]*)\}\{[^}]*\}', text))
    out = []
    head = text[:groups[0].start()] if groups else text
    intro = L.text_to_md(strip_chapter_head(head), ctx)
    if intro.strip():
        out.append(intro)
    for k, g in enumerate(groups):
        name = g.group(1)
        end = groups[k + 1].start() if k + 1 < len(groups) else len(text)
        seg = text[g.end():end]
        # 组标题行形如 \medskip\textbf{\large{符号}}
        seg = re.sub(r'\\medskip\s*\\textbf\{\\large\{[^}]*\}\}', '', seg)
        items = [l for l in seg.split('\n') if l.strip()]
        lines = [f'## {name}', '']
        for it in items:
            it = it.replace('\\hangindent=2pc', '').replace('\\hangafter=1', '')
            it = it.replace('\\setlength\\parindent{0pt}', '')
            md = L.inline(it, ctx).strip()
            md = re.sub(r'[ \t]{2,}', ' ', md)
            if md:
                lines.append(f'- {md}')
        out.append('\n'.join(lines))
    return L.finish('\n\n'.join(out), ctx)


def main():
    outdir = sys.argv[1]
    if os.path.isdir(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)
    os.makedirs(os.path.join(outdir, 'images'))
    labels = pass1()

    docs = []      # (dir, filename, title, md)
    for fn, cno, ar, ctitle in CHAPTERS:
        raw, vblocks = L.protect_verbatim(L.read(os.path.join(SRC, fn + '.tex')))
        text = L.restore_verbatim(L.strip_comments(raw), vblocks)
        ctx = L.Ctx(fn, labels, FIG_ORDER.get(fn, []))
        ctx.chap_no = ar
        chunks = build_sections(text)

        if fn == 'index':
            docs.append(('', '索引.md', '索引', build_index(text, ctx)))
            continue

        numbered = [c for c in chunks if c[0] == 'sec']
        if not numbered:
            # 单篇：整章一篇文档（前言 / 附录A / 附录B）
            body = text
            if fn == 'preface':
                body = re.sub(r'\\section\*\{([^{}]*)\}', r'\n\n@@H2@@\1@@\n\n', body)
            else:
                body = re.sub(r'\\subsubsection\{([^{}]*)\}', r'\n\n@@H2@@\1@@\n\n', body)
                body = re.sub(r'\\section\*\{([^{}]*)\}', r'\n\n@@H2@@\1@@\n\n', body)
            if fn == 'preface':
                docs.append(('', '00-前言.md', '前言', L.finish(L.render_blocks(body, ctx), ctx)))
            else:
                name = f'附录{cno} {ctitle}' if cno in 'AB' else ctitle
                docs.append(('附录', name + '.md', name, L.finish(L.render_blocks(body, ctx), ctx)))
            continue

        tdir = f'第{cno}章 {ctitle}'
        # 章导读
        pre = strip_chapter_head(chunks[0][2] if chunks[0][0] == 'pre' else '')
        if pre.strip():
            md = L.finish(L.render_blocks(pre, ctx), ctx)
            if md.strip():
                docs.append((tdir, '00-本章导读.md', f'第{cno}章 {ctitle} · 导读', md))
        k = 0
        for kind, title, body in chunks:
            body = mark_headings(body)
            if kind != 'sec':
                continue
            k += 1
            t = L.clean_title(title)
            name = f'{ar}.{k} {t}'
            md = L.finish(L.render_blocks(body, ctx), ctx)
            docs.append((tdir, name + '.md', name, md))

    for d, fname, title, md in docs:
        if d:
            md = md.replace('](images/', '](../images/')
        p = os.path.join(outdir, d) if d else outdir
        os.makedirs(p, exist_ok=True)
        with open(os.path.join(p, fname), 'w', encoding='utf-8') as fh:
            fh.write(md)

    used = set()
    for fn, _, _, _ in CHAPTERS:
        used.update(FIG_ORDER.get(fn, []))
    for name in sorted(used):
        src = os.path.join(FIGS, name + '.png')
        if not os.path.exists(src):
            print('MISSING FIG', name)
            continue
        shutil.copy(src, os.path.join(outdir, 'images', name + '.png'))

    n = 0
    for root, dirs, files in os.walk(outdir):
        for f in files:
            if f.endswith('.md'):
                n += 1
    print(f'OK docs={n} images={len(os.listdir(os.path.join(outdir, "images")))} -> {outdir}')


main()