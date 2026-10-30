#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""老 gitbooks.io 站（中文页 404）→ 吃源仓库 md → markdown 树（可复用）。

首例：mydearxym/phoenix-doc-in-chinese @ 52f09cb《Phoenix 框架中文文档》
      → 语雀库 85147782（slug phoenix-doc-in-chinese-52f09cb），39 节点六查全绿。
坑清单：references/github-repo-to-yuque.md 坑 87。

用法：
  git clone https://github.com/mydearxym/phoenix-doc-in-chinese.git /tmp/phx
  python3 build.py --src /tmp/phx --out ./build
  # 补一个 build/00-说明.md（来源/commit/残缺度）后：
  python3 ../../scripts/yuque_tree_import.py --root ./build --book <id> \
      --progress ./progress.json --toc-md
"""
import argparse
import os
import re
import shutil

SELF_RE = re.compile(r"https?://[a-z0-9-]+\.gitbooks\.io/[^)\s]*", re.I)


def parse_summary(path):
    """SUMMARY.md → (root_docs, [(section_title, [(doc_title, relpath)])])

    一级且紧跟缩进子项 = 分组（父页常与首个子项同文件 → 跳过父页）；
    一级且无子项 = 根级文档。
    """
    items = []
    for ln in open(path, encoding="utf-8"):
        m = re.match(r"^(\s*)\*\s+\[([^\]]*)\]\(([^)]*)\)\s*$", ln.rstrip("\n"))
        if m:
            items.append((len(m.group(1)), m.group(2).strip(), m.group(3).strip()))
    root_docs, groups = [], []
    for i, (indent, title, href) in enumerate(items):
        if indent >= 2:
            groups[-1][1].append((title, href))
            continue
        nxt = items[i + 1] if i + 1 < len(items) else None
        if nxt and nxt[0] >= 2:
            groups.append((title, []))
        elif href:
            root_docs.append((title, href))
    return root_docs, groups


def norm(t):
    return re.sub(r"[\s_]+", "", t).lower()


def deprefix(t):
    return re.sub(r"^[A-Za-z]+_", "", t)


def headings(lines):
    """[(行号, (层级, 标题) | None)] —— None 表示这是围栏行（用于 fence-aware 判定）"""
    inf, res = False, []
    for i, ln in enumerate(lines):
        if re.match(r"^\s*(```|~~~)", ln):
            inf = not inf
            res.append((i, None))
            continue
        if inf:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", ln.rstrip("\n"))
        if m:
            res.append((i, (len(m.group(1)), m.group(2).strip())))
    return res


def rewrite_links(text):
    def repl(m):
        label, url = m.group(1), m.group(2).strip()
        if SELF_RE.match(url):            # 站内自指 → 纯文字
            return label
        if url.startswith(("http://", "https://", "mailto:")):
            return m.group(0)             # 外链原样（含 .md 结尾的 GitHub 链接）
        if re.match(r"^[^)\s]+\.(md|html)(#.*)?$", url) or url in ("", "./", "."):
            return label                  # 相对 .md/.html → 纯文字
        if url.startswith("#"):
            return label
        return m.group(0)

    return re.sub(r"\[([^\]]*)\]\(([^)]*)\)", repl, text)


def clean(body, doc_title):
    body = body.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = body.split("\n")
    # 1) 只剥「首个标题行」且它等于 SUMMARY 标题 / 去前缀版
    cands = {norm(doc_title), norm(deprefix(doc_title))}
    for idx, h in headings(lines):
        if h is None:
            continue
        if norm(h[1]) in cands:
            lines[idx] = None
        break
    lines = [ln for ln in lines if ln is not None]
    # 2) 相对层级归一：去重层级集合 → H2,H3,H4…（保嵌套，任何起点都能收口）
    hs = headings(lines)
    levels = sorted({h[0] for _, h in hs if h is not None})
    remap = {l: i + 2 for i, l in enumerate(levels)}
    for idx, h in hs:
        if h is None:
            continue
        nl = remap[h[0]]
        if nl != h[0]:
            lines[idx] = "#" * nl + " " + h[1]
    text = rewrite_links("\n".join(lines))
    return re.sub(r"\n{4,}", "\n\n\n", text).strip() + "\n"


def safe(name):
    return re.sub(r"\s+", " ", name).strip().replace("/", "／")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="源仓库根目录（含 SUMMARY.md）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--summary", default="SUMMARY.md")
    args = ap.parse_args()
    if os.path.exists(args.out):
        shutil.rmtree(args.out)
    os.makedirs(args.out)
    root_docs, groups = parse_summary(os.path.join(args.src, args.summary))
    n = 0
    for ri, (title, href) in enumerate(root_docs, 0):
        sp = os.path.join(args.src, href)
        if not os.path.exists(sp):
            print("!! 缺失(根级) %s (%s)" % (href, title))
            continue
        md = clean(open(sp, encoding="utf-8").read(), title)
        fn = "%02d-%s.md" % (ri, safe(title))
        open(os.path.join(args.out, fn), "w", encoding="utf-8").write(md)
        n += 1
        print("  %-40s %6d B" % (fn, len(md)))
    for gi, (sec, docs) in enumerate(groups, 1):
        d = os.path.join(args.out, "%02d-%s" % (gi, safe(sec)))
        os.makedirs(d, exist_ok=True)
        for di, (title, href) in enumerate(docs, 1):
            sp = os.path.join(args.src, href)
            if not os.path.exists(sp):
                alt = re.sub(r"\.md$", "s.md", sp)   # SUMMARY 单复数笔误兜底
                if os.path.exists(alt):
                    sp = alt
                else:
                    print("!! 缺失 %s (%s)" % (href, title))
                    continue
            md = clean(open(sp, encoding="utf-8").read(), title)
            fn = "%02d-%s.md" % (di, safe(title))
            open(os.path.join(d, fn), "w", encoding="utf-8").write(md)
            n += 1
            print("  %-40s %6d B" % (os.path.join("%02d-%s" % (gi, safe(sec)), fn), len(md)))
    print("文档 %d 篇（另需补 00-说明.md）" % n)


if __name__ == "__main__":
    main()