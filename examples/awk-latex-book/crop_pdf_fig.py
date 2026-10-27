#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按文本锚点 + 矢量图形簇裁剪 PDF 图区（v3：收紧吞并条件 + 跨页回退）。"""
import pymupdf, argparse, os, sys

PDF = os.environ.get('PDF', '/home/admin/.openclaw/workspace/tmp/awk64/The_AWK_Programming_Language_zh_CN.pdf')
XMIN, XMAX = 45.0, 558.0


def lines_of(page):
    out = []
    for b in page.get_text('dict')['blocks']:
        if b['type']:
            continue
        for l in b['lines']:
            t = ''.join(s['text'] for s in l['spans']).strip()
            if t:
                out.append((pymupdf.Rect(l['bbox']), t))
    return out


def cluster(boxes, gap=20):
    n = len(boxes)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in range(n):
        for j in range(i + 1, n):
            a, b = boxes[i], boxes[j]
            if (a[0] - gap < b[2] and b[0] - gap < a[2] and
                    a[1] - gap < b[3] and b[1] - gap < a[3]):
                ra, rb = find(i), find(j)
                if ra != rb:
                    parent[rb] = ra
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(boxes[i])
    return [pymupdf.Rect(min(b[0] for b in g), min(b[1] for b in g),
                         max(b[2] for b in g), max(b[3] for b in g)) for g in groups.values()]


def dgroups(page):
    dboxes = []
    for d in page.get_drawings():
        r = d['rect']
        if r.x1 > 560 or r.x0 < 40:
            continue
        if r.width < 1.5 and r.height < 1.5:
            continue
        dboxes.append((r.x0, r.y0, r.x1, r.y1))
    if not dboxes:
        return []
    return [g for g in cluster(dboxes) if g.width > 8 and g.height > 8]


def grow(box, lines):
    box = pymupdf.Rect(box)
    for _ in range(8):
        grown = pymupdf.Rect(box)
        for r, t in lines:
            if r.x0 < box.x0 - 45 or r.x1 > box.x1 + 55:
                continue
            cy = (r.y0 + r.y1) / 2
            if box.y0 - 16 <= cy <= box.y1 + 16:
                grown |= r
        if grown == box:
            break
        box = grown
    return box


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--needle', default=None)
    ap.add_argument('--out', required=True)
    ap.add_argument('--mode', default='before', choices=['before', 'after'])
    ap.add_argument('--pad', type=float, default=4.0)
    ap.add_argument('--dpi', type=int, default=300)
    ap.add_argument('--page', type=int, default=None, help='直接指定页码')
    ap.add_argument('--clip', default=None, help='手动指定裁剪框 x0,y0,x1,y1（需配合 --page）')
    a = ap.parse_args()

    doc = pymupdf.open(PDF)
    if a.page is not None:
        pno, page, arect = a.page, doc[a.page], pymupdf.Rect(0, 0, XMAX, 0)
        arect.y0 = arect.y1 = 0 if a.mode == 'after' else page.rect.height
    else:
        pno = page = arect = None
        for i, p in enumerate(doc):
            rr = p.search_for(a.needle)
            if rr:
                pno, page, arect = i, p, rr[0]
                break
        if page is None:
            print('NOT FOUND', a.needle); sys.exit(2)

    if a.clip:
        x0, y0, x1, y1 = [float(v) for v in a.clip.split(',')]
        clip = pymupdf.Rect(x0, y0, x1, y1)
        pix = page.get_pixmap(clip=clip, dpi=a.dpi)
        pix.save(a.out)
        print(f'OK(manual) page={pno} clip={clip} {pix.width}x{pix.height} -> {a.out}')
        return

    groups = dgroups(page)
    if a.page is None and not groups and a.mode == 'after' and pno + 1 < doc.page_count:
        pno, page = pno + 1, doc[pno + 1]
        groups = dgroups(page)
        arect = pymupdf.Rect(0, 0, XMAX, 0)

    def pick(gs, ar):
        c = None
        for g in gs:
            if a.mode == 'before':
                if g.y1 <= ar.y0 + 1 and (c is None or g.y1 > c.y1):
                    c = g
            else:
                if g.y0 >= ar.y1 - 1 and (c is None or g.y0 < c.y0):
                    c = g
        return c

    cand = pick(groups, arect)
    if cand is None and a.page is None and a.mode == 'before' and pno > 0:
        pno, page = pno - 1, doc[pno - 1]
        groups = dgroups(page)
        arect = pymupdf.Rect(0, page.rect.height, XMAX, page.rect.height)
        cand = pick(groups, arect)
    if cand is None and a.page is None and a.mode == 'after' and pno + 1 < doc.page_count:
        pno, page = pno + 1, doc[pno + 1]
        groups = dgroups(page)
        arect = pymupdf.Rect(0, 0, XMAX, 0)
        cand = pick(groups, arect)
    if cand is None:
        print('no cluster', a.mode, 'anchor', arect, 'page', pno); sys.exit(4)
    box = pymupdf.Rect(cand)
    for g in groups:
        if g is cand:
            continue
        ov = min(box.y1, g.y1) - max(box.y0, g.y0)
        if ov > 0.5 * min(box.height, g.height):
            box |= g
    box = grow(box, lines_of(page))
    clip = pymupdf.Rect(max(XMIN, box.x0 - a.pad), max(20, box.y0 - a.pad),
                        min(XMAX, box.x1 + a.pad), min(page.rect.height - 20, box.y1 + a.pad))
    pix = page.get_pixmap(clip=clip, dpi=a.dpi)
    pix.save(a.out)
    print(f'OK page={pno} clip=({clip.x0:.0f},{clip.y0:.0f},{clip.x1:.0f},{clip.y1:.0f}) '
          f'{pix.width}x{pix.height} -> {a.out}')


main()