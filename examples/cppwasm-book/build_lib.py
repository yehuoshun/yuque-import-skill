#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《C/C++面向WebAssembly编程》源仓库 zh/ → 语雀导入树。

口径：老 GitBook 3.x 源仓库（book.json structure.readme=preface.md，SUMMARY.md=目录）
  - 发布面 = SUMMARY.md 中**未被注释**的条目（7 章 × 章导读 + 33 节 = 40 篇）
  - 前言 = zh/preface.md（book.json 的 readme）
  - 标题-only 空壳全剔（ch0-intro/readme.md 28B、ch5-03-fetch/5-04-net-frame/6-03-threads-frame/
    7-04-touch/8-* 全部 6B）= TODO 残留，SUMMARY 里也都注释掉了
  - zh/README.md 是仓库门面（前言 + 进度清单 + 版权，与 preface 重复）→ 不入库
  - 章节 readme.md 是章导读（100~430B）→ 落到章目录下 `00-本章导读.md`
  - 图：52 张 png 相对引用 `images/xxx.png` + 根 cover.png / weixin-wasm-hackers.jpg
    → 拷进导入树后由 yuque_rewrite_images.py 传 CDN，再删图片目录（硬规则 10）

用法：
  python3 build_lib.py --repo ~/.openclaw/workspace/tmp/cppwasm-book \
      --out ~/.openclaw/workspace/tmp/cppwasm-book-946acba-clean
"""
import argparse
import os
import re
import shutil

SUMMARY_LINE = re.compile(r'^(\s*)\* \[(.+?)\]\((.+?)\)\s*$')


def sanitize_name(t: str) -> str:
    """文件名/title 安全化：半角 / → 全角 ／；剥行内反引号。"""
    return t.replace('/', '／').replace('`', '').strip()


def strip_h1(body: str) -> str:
    """剥掉正文首个 H1（与 file title / 上级目录名重复）。"""
    lines = body.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].startswith('# '):
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        return '\n'.join(lines[i:])
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True, help='克隆下来的仓库根目录')
    ap.add_argument('--out', required=True, help='导入树输出目录（会被清空重建）')
    ap.add_argument('--sub', default='zh', help='书稿子目录（默认 zh）')
    args = ap.parse_args()

    src = os.path.join(os.path.abspath(args.repo), args.sub)
    out = os.path.abspath(args.out)
    if not os.path.isdir(src):
        raise SystemExit('书稿目录不存在: %s' % src)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)

    summary = open(os.path.join(src, 'SUMMARY.md'), encoding='utf-8').read().splitlines()

    stats = {'title': 0, 'doc': 0, 'skipped_shell': [], 'missing': []}
    cur_chapter_dir = None
    todo = []  # (indent, title, rel_src)
    chapter_map = {}  # 源章节目录名 -> 输出章目录名

    for line in summary:
        m = SUMMARY_LINE.match(line)
        if not m:
            continue
        indent, title, rel = len(m.group(1)), m.group(2), m.group(3)
        todo.append((indent, title, rel))

    for indent, title, rel in todo:
        path = os.path.join(src, rel)
        if not os.path.isfile(path):
            stats['missing'].append(rel)
            continue
        body = open(path, encoding='utf-8').read()
        if len(body.strip()) < 10:  # 标题-only 空壳
            stats['skipped_shell'].append('%s (%dB)' % (rel, len(body.encode())))
            continue

        if indent == 0:  # 章
            cur_chapter_dir = sanitize_name(title)
            chapter_map[os.path.dirname(rel)] = cur_chapter_dir
            os.makedirs(os.path.join(out, cur_chapter_dir), exist_ok=True)
            stats['title'] += 1
            target = os.path.join(out, cur_chapter_dir, '00-本章导读.md')
        else:  # 节
            if cur_chapter_dir is None:
                raise SystemExit('节 %s 出现在任何章之前' % rel)
            target = os.path.join(out, cur_chapter_dir, sanitize_name(title) + '.md')
        stats['doc'] += 1
        open(target, 'w', encoding='utf-8').write(strip_h1(body))

    # 前言
    preface = os.path.join(src, 'preface.md')
    if os.path.isfile(preface):
        body = open(preface, encoding='utf-8').read()
        open(os.path.join(out, '00-前言.md'), 'w', encoding='utf-8').write(strip_h1(body))
        stats['doc'] += 1

    # 图片目录 + 封面图（供 rewrite 脚本按相对路径解析，跑完删）
    for name in os.listdir(src):
        if name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
            shutil.copy2(os.path.join(src, name), os.path.join(out, name))
    for src_dir, chap_dir in chapter_map.items():
        img_src = os.path.join(src, src_dir, 'images')
        if os.path.isdir(img_src):
            shutil.copytree(img_src, os.path.join(out, chap_dir, 'images'))

    # 报告
    print('输出: %s' % out)
    print('TITLE 目录: %d ｜ 文档: %d ｜ 合计节点: %d'
          % (stats['title'], stats['doc'], stats['title'] + stats['doc']))
    if stats['skipped_shell']:
        print('剔空壳 %d: %s' % (len(stats['skipped_shell']), ', '.join(stats['skipped_shell'])))
    if stats['missing']:
        print('!! 缺失文件 %d: %s' % (len(stats['missing']), ', '.join(stats['missing'])))

    # 图片引用清点
    md_refs = 0
    for root, _, files in os.walk(out):
        for f in files:
            if f.endswith('.md'):
                md_refs += len(re.findall(r'!\[[^\]]*\]\(([^)]+)\)',
                                          open(os.path.join(root, f), encoding='utf-8').read()))
    print('md 图片引用处数: %d' % md_refs)


if __name__ == '__main__':
    main()