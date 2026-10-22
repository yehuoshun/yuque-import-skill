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
  5. Sphinx 交叉引用角色（`:ref:`x`` / `:doc:`x`` / `:term:`x`` …）docutils 不认，会**原样留在正文**
     （2026-10-17 linuxtools_rst 实踩）→ 转换前剥成纯文本（`:ref:`ldd <ldd>`` → `ldd`）
  6. **`.. literalinclude::` 原样被 docutils 丢弃（代码整段消失）**（2026-10-22 me115/design_patterns 实踩）→
     必须转换前展开：把目标源码读进来、顶格缩进 4 空格，重写成 `.. code:: <lang>` 指令（docutils 核心自带 code 指令）
  7. **`.. contents:: 目录` 会渲成一段扁平锚点列表**（纯重复大纲，语雀自带侧边大纲）→ 整条剥掉
  8. **块之间必须空行分隔**：旧版把块级元素用单 `\n` 拼接 → 相邻两段 `<p>` 在 markdown 里**并成一段**；
     现在按块类型 join（同类 `li`/表格行/引用行/`dt`-`dd` 用单 `\n`，其余用 `\n\n`）
"""
import re, os, sys, html as h, shutil, argparse
from docutils.core import publish_parts

# literalinclude → 内联代码块（坑 6）
LI_RE = re.compile(r'^\.\.\s+literalinclude::\s*(\S+)\s*$')
LI_OPT_RE = re.compile(r'^\s+:([\w-]+):\s*(.*)$')
EXT_LANG = {'.c': 'c', '.h': 'cpp', '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp', '.hpp': 'cpp',
            '.py': 'python', '.java': 'java', '.js': 'javascript', '.ts': 'typescript', '.cs': 'csharp',
            '.go': 'go', '.rb': 'ruby', '.sh': 'bash', '.json': 'json', '.xml': 'xml', '.html': 'html',
            '.css': 'css', '.sql': 'sql', '.php': 'php', '.rs': 'rust', '.lua': 'lua', '.pl': 'perl',
            '.toml': 'toml', '.yaml': 'yaml', '.yml': 'yaml', '.ini': 'ini', '.conf': 'ini', '.make': 'makefile'}


def expand_literalinclude(src, srcroot, fdir):
    """把 `.. literalinclude::` 指令展开成 `.. code:: <lang>` + 缩进源码。"""
    lines = src.split("\n")
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        m = LI_RE.match(ln)
        if not m:
            out.append(ln)
            i += 1
            continue
        path, opts = m.group(1), {}
        i += 1
        while i < len(lines):
            om = LI_OPT_RE.match(lines[i])
            if not om:
                if lines[i].strip() == "":
                    i += 1
                    continue
                break
            opts[om.group(1)] = om.group(2).strip()
            i += 1
        # 路径：以 / 开头 = Sphinx srcdir（conf.py 所在）；否则相对当前 rst 文件目录
        real = os.path.join(srcroot, path.lstrip("/")) if path.startswith("/") else os.path.join(fdir, path)
        lang = opts.get("language") or EXT_LANG.get(os.path.splitext(path)[1].lower(), "")
        try:
            code = open(real, encoding="utf-8", errors="replace").read().replace("\ufeff", "")
        except Exception:
            out.append("")
            out.append(".. note:: 源码文件缺失：%s" % path)
            continue
        body = "\n".join(("    " + c if c.strip() else "") for c in code.rstrip("\n").split("\n"))
        out.append("")
        out.append(".. code:: %s" % lang)
        out.append("")
        out.append(body)
        out.append("")
    return "\n".join(out)

BLOCK_RE = re.compile(r"<(h[1-6]|pre|p|li|dt|dd|table|blockquote)([^>]*)>(.*?)</\1>", re.S)

# Sphinx 交叉引用角色 → 纯文本（坑 5）
ROLE_RE = re.compile(
    r':(ref|doc|term|numref|meth|func|class|attr|mod|exc|data|const|obj|file|command|option|'
    r'envvar|kbd|guilabel|menuselection|abbr|download|pep|rfc|sup|sub|literal|math):`([^`]*)`')


def _strip_role(m):
    """`:ref:`显示文本 <目标>`` → '显示文本'；`:ref:`目标`` → '目标'"""
    body = m.group(2)
    mm = re.match(r'^(.*?)\s*<[^>]*>$', body)
    return mm.group(1).strip() if mm else body


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

    # 块级元素收成 (kind, text)；join 时按类型决定间隔（坑 8）
    out = []

    def push(kind, text):
        if text and text.strip():
            out.append((kind, text))

    def lang_of(attrs):
        m = re.search(r'class="([^"]*)"', attrs or "")
        if not m:
            return ""
        for cls in m.group(1).split():
            if cls not in ("code", "literal-block", "highlight", "doctest-block", "raw"):
                return cls
        return ""

    pos = 0
    for mm in BLOCK_RE.finditer(body):
        if mm.start() > pos:
            push("p", inline(body[pos:mm.start()]))
        pos = mm.end()
        tag, attrs, inner = mm.group(1), mm.group(2), mm.group(3)
        if tag.startswith("h"):
            title = inline(inner)
            push("h", "#" * int(tag[1]) + " " + title)
        elif tag == "pre":
            code = h.unescape(re.sub(r"<[^>]+>", "", inner)).strip("\n")
            lang = lang_of(attrs)
            push("pre", "```" + lang + "\n" + code + "\n```")
        elif tag == "table":
            push("table", table_md(inner))
        elif tag == "blockquote":
            t = inline(inner)
            push("bq", "> " + t.replace("\n", "\n> "))
        elif tag == "p":
            push("p", inline(inner))
        elif tag == "li":
            push("li", "- " + inline(inner))
        elif tag == "dt":
            push("dt", "**" + inline(inner) + "**")
        elif tag == "dd":
            push("dd", "  " + inline(inner))
    if pos < len(body):
        push("p", inline(body[pos:]))

    KEEP = {("li", "li"), ("table", "table"), ("bq", "bq"),
            ("dt", "dt"), ("dt", "dd"), ("dd", "dd"), ("dd", "dt")}
    chunks = []
    for i, (kind, text) in enumerate(out):
        if i:
            sep = "\n" if (out[i - 1][0], kind) in KEEP else "\n\n"
            chunks.append(sep)
        chunks.append(text)
    md = re.sub(r"\n{3,}", "\n\n", "".join(chunks))
    return md.strip() + "\n"


def rst_to_md(path, srcdir=None):
    srcdir = srcdir or os.path.dirname(os.path.abspath(path))
    src = open(path, encoding="utf-8", errors="replace").read()
    src = src.replace("\ufeff", "")  # 去 BOM（2026-10-15: 否则首行指令/正则被 \ufeff 卡住, epigraph 原文泄漏）
    # 段落尾 `::` + 空行 + 列0指令（无缩进 literal 内容）→ docutils 会把指令吞进 literal 块, 收成单冒号（2026-10-15 补）
    src = re.sub(r"::\s*\n\s*\n(?=\.\. )", ":\n\n", src)
    # Sphinx 交叉引用角色 → 纯文本（沟 5，2026-10-17 linuxtools_rst 实踩）
    src = ROLE_RE.sub(_strip_role, src)
    # literalinclude → 内联 code 块（坑 6，2026-10-22 design_patterns 实踩）
    src = expand_literalinclude(src, srcdir, os.path.dirname(path))
    # `.. contents:: 目录` 整条剥掉（坑 7）：本地大纲与语雀侧边大纲重复
    src = re.sub(r'^\.\.\s+contents::.*\n(?:\s+:.*\n)*', '', src, flags=re.M)
    parts = publish_parts(source=src, writer_name="html5",
                          settings_overrides={"initial_header_level": 1,
                                              "doctitle_xform": False,  # 不做“首节提升为标题”：保留节层级（否则子节全被压成 h1，大纲扁平；2026-10-22 design_patterns 实踩）
                                              "report_level": 5, "halt_level": 5,
                                              "syntax_highlight": "short"})
    return html_to_md(parts["html_body"])


def main():
    ap = argparse.ArgumentParser(description="Sphinx/reST 工程 → Markdown（docutils 中间层）")
    ap.add_argument("--src", required=True, help="rst 源目录")
    ap.add_argument("--out", required=True, help="md 输出目录")
    ap.add_argument("--skip-dirs", default="_build,_static,_templates,_theme,contrib,graphics,images",
                    help="整棵跳过的目录（逗号分隔）")
    ap.add_argument("--srcdir", default=None,
                    help="Sphinx srcdir（解析 literalinclude 的 / 开头绝对路径），默认同 --src")
    args = ap.parse_args()

    src, out = os.path.abspath(args.src), os.path.abspath(args.out)
    srcdir = os.path.abspath(args.srcdir) if args.srcdir else src
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
                md = rst_to_md(os.path.join(root, f), srcdir)
                fn = f[:-4] + ".md"
                open(os.path.join(dst_dir, fn), "w", encoding="utf-8").write(md)
                n_rst += 1
            else:
                shutil.copy(os.path.join(root, f), os.path.join(dst_dir, f))
                n_md += 1
    print(f"转换完成: {n_rst} 个 rst→md, {n_md} 个 md 原样复制 → {out}")


if __name__ == "__main__":
    main()
