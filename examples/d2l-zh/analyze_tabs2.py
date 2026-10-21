#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证：源码里「无 #@tab 标记」的 cell 到底属于哪个框架面板（对照站上各面板代码块）。"""
import re, os, sys, json, html, collections

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get("SRC_DIR", os.path.join(HERE, "src"))
SITE = os.environ.get("SITE_OUT", os.path.join(HERE, "site"))


def txt(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def norm(s):
    return re.sub(r"\s+", "", s)


def site_panels(page_html):
    """返回 {framework: set(norm code)} 以及 {framework: [ordered blocks]}"""
    h = open(page_html, encoding="utf-8", errors="replace").read()
    groups = re.split(r'<div class="mdl-tabs mdl-js-tabs', h)[1:]
    sets = collections.defaultdict(set)
    seq = collections.defaultdict(list)
    for g in groups:
        labels = [txt(x).strip() for x in re.findall(r'class="mdl-tabs__tab[^"]*"[^>]*>(.*?)</a>', g, re.S)]
        parts = re.split(r'<div class="mdl-tabs__panel[^"]*"', g)[1:]
        for i, lab in enumerate(labels):
            if lab not in ('mxnet', 'pytorch', 'tensorflow', 'paddle'):
                continue
            if i >= len(parts):
                continue
            for m in re.finditer(r'<pre>(.*?)</pre>', parts[i], re.S):
                t = norm(txt(m.group(1)))
                sets[lab].add(t)
                seq[lab].append(t)
    return sets, seq


def src_cells(fp):
    s = open(fp, encoding="utf-8", errors="replace").read()
    cells = []
    for m in re.finditer(r'```\{\.python \.input[^}]*\}\n(.*?)```', s, re.S):
        body = m.group(1)
        mk = re.match(r'\s*#@tab (\w+)', body)
        text = "\n".join(l for l in body.strip().split("\n") if not l.strip().startswith('#@tab'))
        cells.append((mk.group(1) if mk else None, norm(text.strip())))
    return cells


def main():
    nav = json.load(open("/home/admin/.openclaw/workspace/tmp/d2l/d2l_nav.json"))
    stat = collections.Counter()
    ex = collections.defaultdict(list)
    for path, title in nav:
        md = os.path.join(SRC, path.replace(".html", ".md"))
        hp = os.path.join(SITE, path.replace("/", "__"))
        if not os.path.exists(md) or not os.path.exists(hp):
            continue
        sets, _ = site_panels(hp)
        for mk, t in src_cells(md):
            if mk is not None:
                continue
            where = [f for f in ('mxnet', 'pytorch', 'tensorflow', 'paddle') if t in sets[f]]
            key = tuple(where)
            stat[str(key)] += 1
            if len(ex[key]) < 3:
                ex[key].append((path, t[:60]))
    for k, v in stat.most_common():
        print(k, v)
        for p in ex[k][:2]:
            print('     ', p[0], '|', p[1])


if __name__ == "__main__":
    main()