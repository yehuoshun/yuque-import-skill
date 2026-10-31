#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""还原 protect_fence_imgs.py 的占位符（rewrite_images 跑完后执行）。"""
import sys, os, json

def main():
    site = sys.argv[1]
    data = json.load(open(sys.argv[2], encoding='utf-8'))
    total = 0
    for rel, pairs in data.items():
        p = os.path.join(site, rel)
        text = open(p, encoding='utf-8').read()
        for ph, orig in pairs:
            assert ph in text, f'{rel}: placeholder {ph} missing'
            text = text.replace(ph, orig)
            total += 1
        open(p, 'w', encoding='utf-8').write(text)
    print(f'restored {total} img tags')

if __name__ == '__main__':
    main()
