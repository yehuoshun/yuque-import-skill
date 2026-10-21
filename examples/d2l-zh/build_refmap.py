#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从抓下来的 zh.d2l.ai 静态页里重建：
  1) 标签 → 交叉引用渲染文本（numref/eqref/ref 用）：直接取站上 <span class="std std-numref"> 的文本
  2) 标签 → 定义处编号（图/表/公式/小节），用于兜底
  3) 引文 bibkey → 站上渲染的引文文本（"(Goodfellow et al., 2016)" 里的名字部分）
输出 refmap.json
"""
import json, os, re, glob, collections, html

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.environ.get("SITE_OUT", os.path.join(HERE, "site"))
OUT = os.environ.get("REFMAP_OUT", os.path.join(HERE, "refmap.json"))
BIB = os.environ.get("BIB", os.path.join(HERE, "src", "d2l.bib"))


def txt(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def main():
    numref = {}      # frag -> rendered text ("图1.1.1" / "2.2节" / "第1章 引言")
    defs = {}        # label -> number text (定义处)
    cites = {}       # zref id -> label text
    cite_conflict = collections.defaultdict(set)
    stats = collections.Counter()

    for fp in sorted(glob.glob(os.path.join(SITE, "*.html"))):
        h = open(fp, encoding="utf-8", errors="replace").read()
        # 1) numref 渲染文本（站上直接给出的交叉引用文字）
        for m in re.finditer(r'href="[^"#]*#([^"]+)"[^>]*>\s*<span class="std std-numref">([^<]*)</span>', h):
            frag, t = m.group(1), txt(m.group(2))
            if frag in numref and numref[frag] != t:
                stats["numref_conflict"] += 1
            numref[frag] = t
        # 2) 定义处编号
        for m in re.finditer(r'<div class="figure[^"]*" id="[^"]*">\s*<span id="([^"]+)"></span>.*?'
                             r'<span class="caption-number">([^<]*)</span>', h, re.S):
            defs.setdefault(m.group(1), txt(m.group(2)))
        for m in re.finditer(r'<div class="math notranslate nohighlight" id="equation-([^"]+)">\s*'
                             r'<span class="eqno">([^<]*)', h, re.S):
            defs.setdefault(m.group(1), txt(m.group(2)))
        for m in re.finditer(r'<div class="section" id="([^"]+)">\s*(?:<span id="[^"]*"></span>)?'
                             r'<h(\d)>(?:<span class="section-number">([^<]*)</span>)?([^<]*)', h):
            label, lvl, num, title = m.group(1), m.group(2), (m.group(3) or "").strip(), m.group(4)
            defs.setdefault(label, f"{num} {txt(title)}".strip())
        # 表格
        for m in re.finditer(r'<span id="((?:tbl|tab)-[^"]+)"></span>\s*<table.*?'
                             r'<span class="caption-number">([^<]*)</span>', h, re.S):
            defs.setdefault(m.group(1), txt(m.group(2)))
        # 表格：<table ... id="idN"><caption><span class="caption-number">表X</span> —— 抓不到 label，靠下面 defs 兜底
        # 3) 引文渲染文本
        for m in re.finditer(r'href="[^"]*zreferences\.html#(id\d+)"[^>]*>(.*?)</a>', h, re.S):
            zid, t = m.group(1), txt(m.group(2))
            t = t.replace(" ", " ").strip()
            cite_conflict[zid].add(t)
        stats["pages"] += 1

    for zid, s in cite_conflict.items():
        if len(s) == 1:
            cites[zid] = s.pop()
        else:
            stats["cite_multi"] += 1
            cites[zid] = sorted(s)[0]

    # zref 页：id -> 完整参考文献文本
    zref_txt = {}
    zp = os.path.join(SITE, "chapter_references__zreferences.html")
    if os.path.exists(zp):
        h = open(zp, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r'<dt class="label" id="(id\d+)"><span class="brackets">([^<]*)</span></dt>\s*<dd><p>(.*?)</p>\s*</dd>', h, re.S):
            zref_txt[m.group(1)] = {"label": txt(m.group(2)), "ref": txt(m.group(3))}

    # bibkey -> zref id：用 bib 里的作者姓 + 年份去 zref 文本里对
    bib = open(BIB, encoding="utf-8", errors="replace").read()
    entries = re.findall(r'@\w+\{\s*([^,\s]+)\s*,(.*?)\n\}', bib, re.S)
    key2zid = {}
    key2ref = {}
    used = set(l.strip() for l in open('/tmp/keys.txt') if l.strip())

    def norm(s):
        return re.sub(r'[^0-9a-z\u4e00-\u9fff]', '', s.lower())

    for key, body in entries:
        kw = re.search(r'year\s*=\s*\{?(\d{4})', body)
        tm = re.search(r'\btitle\s*=\s*\{(.*?)\}\s*,?\s*\n', body, re.S)
        year = kw.group(1) if kw else "?"
        title = norm(re.sub(r'\s+', ' ', tm.group(1))) if tm else ""
        au = re.search(r'\bauthor\s*=\s*\{(.*?)\}\s*,?\s*\n', body, re.S)
        surnames = []
        if au:
            for a in re.split(r'\s+and\s+', re.sub(r'\s+', ' ', au.group(1))):
                a = a.strip().rstrip('}')
                if a:
                    if ',' in a:
                        surnames.append(a.split(',')[0].strip())
                    else:
                        surnames.append(a.split()[-1].strip())
        cands = []
        for zid, v in zref_txt.items():
            if year not in v["ref"]:
                continue
            nr = norm(v["ref"])
            score = 0
            if title and title[:28] and title[:28] in nr:
                score += 10
            if surnames and surnames[0] and surnames[0] in v["ref"]:
                score += 3
            score += sum(1 for s in surnames[1:] if s in v["ref"])
            if score >= 3:
                cands.append((score, zid))
        if cands:
            cands.sort(key=lambda x: (-x[0], x[1]))
            if len(cands) > 1 and cands[0][0] == cands[1][0]:
                stats["bib_multi"] += 1
            key2zid[key] = cands[0][1]
        elif key in used:
            stats["bib_unmatched"] += 1
    for k, z in key2zid.items():
        key2ref[k] = cites.get(z, zref_txt.get(z, {}).get("label", k))

    json.dump({"numref": numref, "defs": defs, "cites": cites, "zref": zref_txt,
               "key2zid": key2zid, "key2ref": key2ref, "stats": dict(stats)},
              open(OUT, "w"), ensure_ascii=False, indent=1)
    print("numref", len(numref), "defs", len(defs), "cites", len(cites),
          "zref", len(zref_txt), "bib_keys_mapped", len(key2zid), dict(stats))


if __name__ == "__main__":
    main()