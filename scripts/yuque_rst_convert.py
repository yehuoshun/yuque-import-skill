#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sphinx/reST 工程 → Markdown 转换（2026-10-13 固化，Got GitHub 实战）

用法:
  python3 yuque_rst_convert.py --src <rst源目录> --out <md输出目录> \
      [--skip-dirs "_build,_static,_templates,_theme,contrib,graphics,images"]

行为:
  - 递归把 .rst 转 .md（docutils html5 中间层 + 块级转 md），保持相对路径
  - .md 原样复制（如 README.md）；--skip-dirs 里的目录整棵跳过
  - 处理: 标题/段落/列表/字面块/链接/表格/note 提示框; 脚注定义块与行内引用整体剥离

依赖: pip install docutils（pandoc 装不上时的替代方案, 见坑 1）

已踩坑（2026-10-13 实捶）:
  1. pandoc 在沙箱装不上（tuna 镜像 403、PyPI 下载超时）→ docutils 纯 Python 秒装
  2. 正则 `</\\1>` 不能配非捕获组 `(?:aside|dl)` → "invalid group reference"，用捕获组
  3. docutils html5 脚注引用是 role="doc-noteref"/"doc-backlink"（新版, 不是 class=footnote-reference），
     且必须【先于链接正则】剥离，否则被 <a href=#...> 降级逻辑吃掉, [1][2] 残留正文
  4. 脚注定义块（aside/dl.footnote、dl.citation）整体丢弃, 避免文档尾挂脚注清单
"""
import re, os, sys, html as h, shutil, argparse
from docutils.core import publish_parts

BLOCK_RE = re.compile(r"<(h[1-6]|pre|p|li|dt|dd|table|blockquote)([^>]*)>(.*?)</\1>", re.S)


def inline(t):
    """行内元素 → markdown。链接: 外链保留, 内部锚点/脚注降级为纯文字"""
    # <img> → markdown 图片（2026-10-15 补: 此前 .. image:: 整张丢失）
    def _img(m):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(0)))
        return "![%s](%s)" % (attrs.get("alt", ""), attrs.get("src", ""))
    t = re.sub(r"<img[^>]*/?>", _img, t, flags=re.S)
    # 脚注/引文引用标记（docutils html5: role=doc-noteref/doc-backlink）→ 必须先于链接正则整体去掉
    t = re.sub(r'<a[^>]*role="doc-(?:noteref|backlink)"[^>]*>.*?</a>', "", t, flags=re.S)
    t = re.sub(r"<br\s*/?>", "\n", t)
    t = re.sub(r'<a\s+[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
               lambda m: m.group(2) if m.group(1).startswith(("#", "javascript", "mailto"))
               else "[%s](%s)" % (inline(m.group(2)), m.group(1)), t, flags=re.S)
    t = re.sub(r"<(strong|b)>(.*?)</\1>", r"**\2**", t, flags=re.S)
    t = re.sub(r"<(em|i)>(.*?)</\1>", r"*\2*", t, flags=re.S)
    t = re.sub(r"<(code|tt|cite|kbd)>[^>]*>(.*?)</\1>",
               lambda m: "`" + h.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip() + "`", t, flags=re.S)
    t = re.sub(r"<[^>]+>", "", t)
    t = h.unescape(t)
    t = re.sub(r"[ \t]*\n[ \t]*", " ", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()


def table_md(inner):
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", inner, re.S)
    out = []
    for r in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)
        out.append("| " + " | ".join(inline(c) for c in cells) + " |")
    if len(out) >= 2:
        n = out[0].count("|") - 1
        sep = "|" + "|".join("---" for _ in range(n)) + "|"
        return "\n".join([out[0], sep] + out[1:])
    return "\n".join(out)


def html_to_md(body):
    # 脚注/引文定义块（docutils html5: aside.footnote / dl.footnote / dl.citation）→ 整体丢弃
    body = re.sub(r'<(aside|dl)[^>]*class="(?:footnote|citation)[^"]*"[^>]*>.*?</\1>', "", body, flags=re.S)
    # note/tip 提示框 → blockquote
    def admon(m):
        inner = m.group(2)  # 2026-10-15: 正则加 (div|aside) 捕获组后组号移位, group(2) 才是内容
        title = ""
        tm = re.search(r'<p[^>]*class="[^"]*admonition-title[^"]*"[^>]*>(.*?)</p>', inner, re.S)
        if tm:
            title = inline(tm.group(1))
            inner = inner[:tm.start()] + inner[tm.end():]
        paras = re.findall(r"<p[^>]*>(.*?)</p>", inner, re.S)
        lines = [f"> **{title}**：" if title else ">"]
        for p in paras:
            t = inline(p)
            if t:
                lines.append("> " + t)
        return "\n".join(lines)
    body = re.sub(r'<(div|aside) class="admonition[^"]*">(.*?)</\1>', admon, body, flags=re.S)

    out = []
    pos = 0
    for mm in BLOCK_RE.finditer(body):
        if mm.start() > pos:
            t = inline(body[pos:mm.start()])
            if t:
                out.append(t)
        pos = mm.end()
        tag, attrs, inner = mm.group(1), mm.group(2), mm.group(3)
        if tag.startswith("h"):
            title = inline(inner)
            if title:
                out.append("\n" + "#" * int(tag[1]) + " " + title)
        elif tag == "pre":
            code = h.unescape(re.sub(r"<[^>]+>", "", inner)).strip("\n")
            if code:
                out.append("\n```\n" + code + "\n```")
        elif tag == "table":
            t = table_md(inner)
            if t:
                out.append("\n" + t)
        elif tag == "blockquote":
            t = inline(inner)
            if t:
                out.append("\n> " + t.replace("\n", "\n> "))
        elif tag == "p":
            t = inline(inner)
            if t:
                out.append(t)
        elif tag == "li":
            t = inline(inner)
            if t:
                out.append("- " + t)
        elif tag == "dt":
            t = inline(inner)
            if t:
                out.append("**" + t + "**")
        elif tag == "dd":
            t = inline(inner)
            if t:
                out.append("  " + t)
    if pos < len(body):
        t = inline(body[pos:])
        if t:
            out.append(t)
    md = re.sub(r"\n{3,}", "\n\n", "\n".join(out))
    return md.strip() + "\n"


def rst_to_md(path):
    src = open(path, encoding="utf-8", errors="replace").read()
    src = src.replace("\ufeff", "")  # 去 BOM（2026-10-15: 否则首行指令/正则被 \ufeff 卡住, epigraph 原文泄漏）
    # 段落尾 `::` + 空行 + 列0指令（无缩进 literal 内容）→ docutils 会把指令吞进 literal 块, 收成单冒号（2026-10-15 补）
    src = re.sub(r"::\s*\n\s*\n(?=\.\. )", ":\n\n", src)
    parts = publish_parts(source=src, writer_name="html5",
                          settings_overrides={"initial_header_level": 1,
                                              "report_level": 5, "halt_level": 5,
                                              "syntax_highlight": "short"})
    return html_to_md(parts["html_body"])


def main():
    ap = argparse.ArgumentParser(description="Sphinx/reST 工程 → Markdown（docutils 中间层）")
    ap.add_argument("--src", required=True, help="rst 源目录")
    ap.add_argument("--out", required=True, help="md 输出目录")
    ap.add_argument("--skip-dirs", default="_build,_static,_templates,_theme,contrib,graphics,images",
                    help="整棵跳过的目录（逗号分隔）")
    args = ap.parse_args()

    src, out = os.path.abspath(args.src), os.path.abspath(args.out)
    skip = set(args.skip_dirs.split(","))
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)

    n_rst = n_md = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in skip]
        rel = os.path.relpath(root, src)
        for f in sorted(files):
            if not (f.endswith(".rst") or f.endswith(".md")):
                continue
            dst_dir = os.path.join(out, rel) if rel != "." else out
            os.makedirs(dst_dir, exist_ok=True)
            if f.endswith(".rst"):
                md = rst_to_md(os.path.join(root, f))
                fn = f[:-4] + ".md"
                open(os.path.join(dst_dir, fn), "w", encoding="utf-8").write(md)
                n_rst += 1
            else:
                shutil.copy(os.path.join(root, f), os.path.join(dst_dir, f))
                n_md += 1
    print(f"转换完成: {n_rst} 个 rst→md, {n_md} 个 md 原样复制 → {out}")


if __name__ == "__main__":
    main()
