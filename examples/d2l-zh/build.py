#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组装导入树：clean/  （中文目录/文件名，与站上目录顺序一致）"""
import re, os, json, sys, html, collections, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from convert import convert, site_headings, REFMAP   # noqa

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
SITE = os.path.join(HERE, "site")
CLEAN = os.path.join(HERE, "clean")
NAV = json.load(open(os.path.join(HERE, "d2l_nav.json")))

BAD = re.compile(r'[/\\:*?"<>|]')


def clean_name(s):
    return BAD.sub("", s).strip()


def sec_title(title):
    """'2.1. 数据操作' → '2.1 数据操作'；'1. 引言' → '1. 引言'"""
    m = re.match(r'^(\d+(?:\.\d+)*)\.\s+(.*)$', title)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return title


def dest_name(title, src_md):
    """站上标题可能为空（如 16.6.）→ 用源文件首个 H1 兜底"""
    t = sec_title(title)
    if re.match(r'^\d+(?:\.\d+)*\.?$', t.strip()):
        try:
            s = open(src_md, encoding="utf-8").read()
            m = re.match(r'^#\s+(.+)$', s, re.M)
            if m:
                name = re.sub(r'[`*]', '', m.group(1)).strip()
                pre = re.match(r'^(\d+(?:\.\d+)*)\s', t) or re.match(r'^(\d+(?:\.\d+)*)', t)
                t = f"{t.rstrip('.')} {name}"
        except OSError:
            pass
    return t


def build_plan():
    """返回 [(dest_rel, src_md|None, site_html|None)]"""
    plan = []
    root_idx = 0
    chapters = []          # [(num, name, dirname, [items])]
    cur = None
    for path, title in NAV:
        if path.endswith("zreferences.html"):
            continue
        site_html = path.replace("/", "__")
        md_rel = path.replace(".html", ".md")
        src_md = os.path.join(SRC, md_rel)
        if path.endswith("index.html") and path.count("/") == 1:
            m = re.match(r'^(\d+)\.\s*(.+)$', title)
            if m:
                num = int(m.group(1))
                cnt = len([c for c in chapters if c[0] < num]) + 1
                d = f"{num + 2:02d}-第{num}章 {clean_name(m.group(2))}"
                cur = (num, m.group(2), d, [(f"{num}. {m.group(2)}.md", src_md, site_html)])
                chapters.append(cur)
                continue
            # 前言/安装/符号
            root_idx += 1
            plan.append((None, f"{root_idx - 1:02d}-{clean_name(title)}.md", src_md, site_html))
            continue
        # 章节内小节
        if cur is not None:
            cur[3].append((f"{dest_name(title, src_md)}.md", src_md, site_html))
        else:
            print("!! 未归属页面", path, title)
    out = []
    for _, rel, src, site in plan:
        out.append((rel, src, site))
    for num, name, d, items in chapters:
        for fn, src, site in items:
            out.append((os.path.join(d, clean_name(fn)), src, site))
    out.append(("19-参考文献.md", None, "chapter_references__zreferences.html"))
    return out


def zref_md():
    h = open(os.path.join(SITE, "chapter_references__zreferences.html"), encoding="utf-8", errors="replace").read()
    lines = ["# 参考文献", ""]
    n = 0
    for m in re.finditer(r'<dt class="label" id="id\d+"><span class="brackets">([^<]*)</span></dt>\s*'
                         r'<dd><p>(.*?)</p>\s*</dd>', h, re.S):
        n += 1
        label = html.unescape(m.group(1)).replace("[", "").replace("]", "").strip()
        ref = m.group(2)
        ref = re.sub(r'<a class="reference external" href="([^"]+)"[^>]*>(.*?)</a>', r'[\2](\1)', ref, flags=re.S)
        ref = re.sub(r'<a class="reference external" href="([^"]+)"[^>]*/>', r'\1', ref)
        ref = re.sub(r'<em>(.*?)</em>', r'*\1*', ref, flags=re.S)
        ref = html.unescape(re.sub(r'<[^>]+>', '', ref))
        ref = ref.replace("\xa0", " ").replace("\u2013", "–").replace("\\url ", "").strip()
        ref = re.sub(r'\s+', ' ', ref)
        lines.append(f"{n}. **{label}** {ref}")
        lines.append("")
    return "\n".join(lines) + "\n", n


def main():
    if os.path.exists(CLEAN):
        shutil.rmtree(CLEAN)
    os.makedirs(CLEAN)
    # 图片目录
    shutil.copytree(os.path.join(SRC, "img"), os.path.join(CLEAN, "_img"))
    plan = build_plan()
    total = collections.Counter()
    print(f"计划 {len(plan)} 个文档")
    for rel, src_md, site_html in plan:
        dest = os.path.join(CLEAN, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        depth = rel.count("/")
        prefix = "../" * depth
        if src_md is None:
            md, n = zref_md()
            open(dest, "w", encoding="utf-8").write(md)
            total["zref"] += 1
            print(f"  {rel}  参考文献 {n} 条")
            continue
        heads = site_headings(os.path.join(SITE, site_html)) if site_html else []
        stats = collections.Counter()
        md = convert(open(src_md, encoding="utf-8").read(), heads, prefix, stats)
        open(dest, "w", encoding="utf-8").write(md)
        total.update(stats)
        total["docs"] += 1
        flag = "⚠" if stats["ref_unresolved"] or stats["cite_unresolved"] else " "
        print(f" {flag}{rel:52s} {len(md):7d}B keep={stats['code_keep']:3d} "
              f"drop={sum(v for k, v in stats.items() if k.startswith('code_drop')):3d} "
              f"h1={stats['h1_dropped']} refunres={stats['ref_unresolved']} citeunres={stats['cite_unresolved']}")
    print("== 汇总 ==")
    for k, v in total.most_common():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()