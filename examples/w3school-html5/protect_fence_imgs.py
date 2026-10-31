#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""保护代码围栏内的字面 <img> 标签（示例代码），避免 rewrite_images 误重写。

用法：
  python3 protect_fence_imgs.py <site_dir> <protect.json>
  产出 protect.json = {md相对路径: [(placeholder, 原文), ...]}
重写完成后用 restore_fence_imgs.py 还原。
"""
import sys, os, re, json

def main():
    site = sys.argv[1]
    out = {}
    for root, dirs, files in os.walk(site):
        for fn in files:
            if not fn.endswith('.md'):
                continue
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, site)
            text = open(p, encoding='utf-8').read()
            lines = text.split('\n')
            in_fence = False
            new_lines = []
            n = 0
            for line in lines:
                if line.startswith('```'):
                    in_fence = not in_fence
                    new_lines.append(line)
                    continue
                if in_fence:
                    m = re.search(r'<img\b[^>]*?\bsrc=(["\'])([^"\']+)(["\'])', line)
                    if m:
                        ph = f'<!--IMG_FENCE_{n}-->'
                        out.setdefault(rel, []).append((ph, m.group(0)))
                        line = line.replace(m.group(0), ph)
                        n += 1
                new_lines.append(line)
            open(p, 'w', encoding='utf-8').write('\n'.join(new_lines))
    json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    total = sum(len(v) for v in out.values())
    print(f'protected {total} img tags in fences across {len(out)} files')

if __name__ == '__main__':
    main()
