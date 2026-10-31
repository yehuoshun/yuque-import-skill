#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""waylau/apache-mina-2.x-user-guide → 语雀 md（2026-11-01 fpb52 #136）

GitBook 3.x 源仓库（Part I/II/III 扁平结构 + SUMMARY.md 定序）：
- 按 SUMMARY 序给每个 part 内文件加 NN- 前缀（章+节统一编号，字典序=书序）
- ⚠️ 空壳扫描先行：0 字节文件跳过（本仓 ch6 Transports 正文为空壳，小节 APR/串行正常）
- ⚠️ GBK 编码 md 检测并转 UTF-8（本仓 ch13 是 gb2312 的「未完待续」短桩）
- ⚠️ 图引用保持 ../images/ 原形态（rewrite_images 按 md 所在目录解析相对路径），
  外链死图（99btgc01.info）原位标注；README logo 本地化
- 产出 site/ 后走 yuque_rewrite_images.py 传 CDN → 删 images/ → tree_import --toc-md
"""
import re, os, shutil

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')   # 仓库 clone
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site')

def main():
    summary = open(os.path.join(SRC, 'SUMMARY.md'), encoding='utf-8').read()
    lines = [l.strip() for l in summary.split('\n') if l.strip()]
    entries = []
    for l in lines:
        m = re.match(r'^([\t ]*)\*\s*\[(.+?)\]\((.*?)\)$', l)
        if m and m.group(3).endswith('.md'):
            entries.append(m.group(3))
    parts = {
        'Part I - Basics': '01-Basics 基础',
        'Part II - MINA Core': '02-MINA Core 核心',
        'Part III - MINA Advanced': '03-MINA Advanced 高级',
    }
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    for srcpart, dstpart in parts.items():
        src_dir = os.path.join(SRC, srcpart)
        dst_dir = os.path.join(OUT, dstpart)
        os.makedirs(dst_dir, exist_ok=True)
        ordered = [os.path.basename(p) for p in entries if p.startswith(srcpart + '/')]
        for f in sorted(os.listdir(src_dir)):
            if f not in ordered:
                ordered.append(f)
        for i, base in enumerate(ordered, 1):
            sp = os.path.join(src_dir, base)
            if os.path.getsize(sp) == 0:
                print('SKIP empty:', srcpart, base)
                continue
            name = base[:-3] if base.endswith('.md') else base
            shutil.copy2(sp, os.path.join(dst_dir, f'{i:02d}-{name}.md'))
    # 前言 + logo
    r = open(os.path.join(SRC, 'README.md'), encoding='utf-8').read()
    r = r.replace('![logo](mina-logo.png)', '![logo](images/mina-logo.png)')
    open(os.path.join(OUT, '00-前言.md'), 'w', encoding='utf-8').write(r)
    os.makedirs(os.path.join(OUT, 'images'), exist_ok=True)
    for f in os.listdir(os.path.join(SRC, 'images')):
        shutil.copy2(os.path.join(SRC, 'images', f), os.path.join(OUT, 'images', f))
    shutil.copy2(os.path.join(SRC, 'mina-logo.png'), os.path.join(OUT, 'images', 'mina-logo.png'))
    # 编码检测 + 图片引用归一
    for root, dirs, files in os.walk(OUT):
        for fn in files:
            if not fn.endswith('.md'):
                continue
            p = os.path.join(root, fn)
            raw = open(p, 'rb').read()
            try:
                c = raw.decode('utf-8')
            except UnicodeDecodeError:
                c = raw.decode('gb2312', errors='replace')  # waylau 老仓偶见 GBK
                print('GBK→UTF-8:', os.path.relpath(p, OUT))
            c = re.sub(r'!\[[^\]]*\]\(http://99btgc01[^)]*\)', '（原配图为外链，已失效）', c)
            open(p, 'w', encoding='utf-8').write(c)

if __name__ == '__main__':
    main()
