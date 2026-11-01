#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fpb52 #150 Nutz 官方手册 — wendal/nutz doc/manual（.man zDoc 格式）→ md

zDoc 语法（doc/manual/zdoc/syntax.man 官方规范）:
  - 头部元数据 #title: / #index: / #author: / #verifier:
  - ---- 分隔线（≥5 个 -）
  - 缩进（Tab）= 父子层级；拥有子的行 = 标题行
  - * 无序列表 / # 有序列表
  - [url] [url text] 超链接；`code` 反引号=行内代码
  - {*b} {/i} {_u} {~s} {#F00;x} 样式；{^sup} {,sub} 上下标
  - <img> / <WxH:img> 图片；{{{<lang> ... }}} 代码块
"""
import os, re, sys, json, html

SRC = "../nutz-src/doc/manual"
OUT = "site"
os.makedirs(OUT, exist_ok=True)

# index.xml 顺序 = 发布顺序（分组名 + 组内 .man 顺序）
INDEX = [
    ("committer", "关于源码"),
    ("dao", "Dao 手册"),
    ("ioc", "Ioc 手册"),
    ("mvc", "Mvc 手册"),
    ("json", "Json 手册"),
    ("el", "表达式引擎"),
    ("lang", "甜 Java"),
    ("zmole", "zMole - 快速代码生成工具"),
    ("zdoc", "zDoc 手册"),
    ("history", "版本历史"),
    ("faq", "FAQ"),
    ("appendix", "附录"),
]

# 从 index.xml 提每组顺序
import xml.etree.ElementTree as ET
tree = ET.parse(os.path.join(SRC, "index.xml"))
root = tree.getroot()
GROUP_ORDER = {}  # group -> [man paths]
for g in root.findall("doc"):
    path = g.get("path")
    if path in [x[0] for x in INDEX]:
        files = []
        for d in g.findall("doc"):
            files.append(d.get("path"))
        GROUP_ORDER[path] = files

def read_man(path):
    raw = open(path, "rb").read()
    return raw.decode("utf-8", "replace")

def clean_meta(text):
    """剥头部元数据"""
    lines = text.split("\n")
    out = []
    for ln in lines:
        if ln.startswith("#title:") or ln.startswith("#index:") or \
           ln.startswith("#author:") or ln.startswith("#verifier:"):
            continue
        out.append(ln)
    return "\n".join(out)

def is_hr(ln):
    return len(ln.strip()) >= 5 and set(ln.strip()) == {"-"}

def is_code_start(ln):
    return ln.strip().startswith("{{{")

def is_code_end(ln):
    return ln.strip().startswith("}}}")

# ---- 行内样式转换 ----
def inline(text):
    """处理样式/链接/行内代码/图片。返回 md 行内文本。"""
    t = text
    # 图片 <WxH:path> 或 <path>（仅限 .png/.jpg/.gif，排除 URL 里其他尖括号形态）
    def img_repl(m):
        inner = m.group(2)
        if inner is None:
            return m.group(0)
        if re.match(r'^https?://', inner):
            # 远程图: 按 basename 反查本地，找不到保留 URL
            return f"![{inner.split('/')[-1]}]({inner})"
        inner2 = re.sub(r'^\d+x\d+:?', '', inner)  # 去 WxH:
        name = inner2.split('/')[-1].split('.')[0]
        # 语法示例（路径本地不存在）→ 行内代码保留原文
        if not os.path.exists(os.path.join(SRC, inner2.lstrip('./'))):
            return f"`<{m.group(1) or ''}{inner}>`"
        return f"![{name}]({inner2})"
    t = re.sub(r'<([0-9]+x[0-9]+:)?([^<>]*\.(?:png|jpg|gif|jpeg|PNG|JPG|GIF))>', img_repl, t)
    # 链接 [url text] / [url]
    def link_repl(m):
        inner = m.group(1)
        if ' ' in inner:
            url, txt = inner.split(' ', 1)
        else:
            url, txt = inner, inner
        # 站内 .man 链接（含 #锚点）→ 死链，转纯文本
        if '.man' in url or url.startswith('#'):
            return txt
        return f"[{txt}]({url})"
    t = re.sub(r'(?<!!)\[([^\[\]]+)\]', link_repl, t)
    # 样式组合 {*x} {/x} {_x} {~x} {#color;x} {^sup} {,sub}
    # 样式标记 = 可选颜色 #xxxx; + 至少一个样式字母 */_~；贪婪匹配标记，内容直到第一个 }
    # 样式组合 {*x} {/x} {_x} {~x} {#color;x} {#color*x} {^sup} {,sub}
    # 形态: 颜色(可选 #xxx 或 #xxx;) + 样式字母(可选 */_~) + 内容
    def style_repl(m):
        color = m.group(1) or ""
        marks = m.group(2) or ""
        body = m.group(3)
        if not marks and not color:
            return m.group(0)  # {cid} 这类 JSON/占位符，原样保留
        md = body
        if '*' in marks: md = f"**{md}**"
        if '/' in marks: md = f"*{md}*"
        if '~' in marks: md = f"~~{md}~~"
        if '_' in marks: md = f"<u>{md}</u>"
        return md
    t = re.sub(r'\{(#?[0-9A-Fa-f]{1,6};?)?([*/_~]*)([^{}]*)\}', style_repl, t)
    # 反引号行内代码（含 `` 转义 `` -> `）
    t = t.replace('``', '\x00').replace('`', '`').replace('\x00', '`')
    # HTML 实体
    t = html.unescape(t)
    return t

# ---- 树解析: 缩进 = 层级 ----
def parse_blocks(text):
    """按行解析成块树。返回 list of (depth, kind, content)
    kind: title/para/list_ul/list_ol/code/img/hr
    """
    # 续行合并：行尾 `\` 与下一行拼接（zDoc 续行符）
    lines = text.split("\n")
    merged = []
    j = 0
    while j < len(lines):
        ln = lines[j]
        while ln.rstrip().endswith("\\") and j + 1 < len(lines):
            ln = ln.rstrip()[:-1] + lines[j + 1]
            j += 1
        merged.append(ln)
        j += 1
    lines = merged
    blocks = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        if is_hr(ln):
            blocks.append((0, "hr", ""))
            i += 1
            continue
        # 代码块
        if is_code_start(ln):
            code_depth = len(ln) - len(ln.lstrip("\t "))
            lang = ln.strip()[3:-1].strip() if '>' in ln else ""
            lang = re.sub(r'^<|>$', '', lang)
            lang = lang.strip()
            # 语言规范化
            lang_map = {"JAVA": "java", "Java": "java", "java": "java",
                        "Javascript": "javascript", "JSON": "json", "Json": "json",
                        "xml": "xml", "SQL": "sql", "SQLs": "sql", "sql": "sql",
                        "bash": "bash", "HTML": "html", "Jsp": "jsp",
                        "index.xml": "xml", "web.xml": "xml",
                        "zDoc": "", "IOC-XML 配置": "xml", "IOC-JSON 配置": "json"}
            lang = lang_map.get(lang, lang.lower() if lang else "")
            code = []
            i += 1
            while i < len(lines) and not is_code_end(lines[i]):
                code.append(lines[i])
                i += 1
            i += 1  # skip }}}
            blocks.append((code_depth, "code", (lang, "\n".join(code))))
            continue
        # 缩进层级：前导 tab = 1 层；连续空格按 4 个 = 1 层（tab+空格混排归一化）
        lead = ln[:len(ln) - len(ln.lstrip("\t "))]
        depth = lead.count("\t") + len(lead.replace("\t", "")) // 4
        stripped = ln.strip()
        if re.match(r'^[*]\s+', stripped):
            kind = "list_ul"
            content = re.sub(r'^[*]\s+', '', stripped, count=1)
        elif re.match(r'^#\s+', stripped):
            kind = "list_ol"
            content = re.sub(r'^#\s+', '', stripped, count=1)
        elif re.match(r'^<([0-9]+x[0-9]+:)?[^<>]*\.(png|jpg|gif|jpeg|PNG|JPG|GIF)>$', stripped):
            kind = "img"
            content = stripped
        else:
            kind = "para"
            content = stripped
        blocks.append((depth, kind, content))
        i += 1
    return blocks

def blocks_to_md(blocks):
    """块 → 树 → DFS 渲染。深度 0 有子 = ## 标题；叶子 = 内容。"""
    # 栈式建树
    stack = []  # (depth, node)
    root_children = []
    for d, kind, content in blocks:
        node = {"d": d, "kind": kind, "content": content, "children": []}
        while stack and stack[-1][0] >= d:
            stack.pop()
        if stack:
            stack[-1][1]["children"].append(node)
        else:
            root_children.append(node)
        stack.append((d, node))

    def render_node(node, depth):
        """渲染一个节点（含子树），返回行列表"""
        kind = node["kind"]
        content = node["content"]
        children = node["children"]
        if kind == "hr":
            return ["---"]
        if kind == "code":
            lang, code = content
            return ["```" + lang, code.rstrip("\n"), "```"]
        if kind == "img":
            m = re.search(r'<([0-9]+x[0-9]+:)?([^<>]*\.(?:png|jpg|gif|jpeg|PNG|JPG|GIF))>', content)
            if m:
                inner = re.sub(r'^\d+x\d+:?', '', m.group(2))
                name = inner.split('/')[-1].split('.')[0]
                return [f"![{name}]({inner})"]
            return []
        if kind in ("list_ul", "list_ol"):
            prefix = "- " if kind == "list_ul" else "1. "
            lines = [prefix + inline(content)]
            for ch in children:
                if ch["kind"] in ("list_ul", "list_ol") and ch["d"] == node["d"] + 1:
                    for sl in render_node(ch, depth+1):
                        lines.append("  " + sl)
            return lines
        # title / para
        if kind == "para" and content.startswith("||"):
            # 表格行（单元格跑 inline 样式）
            cells = [inline(c.strip()) for c in content.strip("|").split("||")]
            return ["| " + " | ".join(cells) + " |"]
        if children and kind == "para":
            # 有子的段落行 = 标题
            lvl = min(depth + 2, 6)
            out = [f"{'#'*lvl} {inline(content)}"]
        elif kind == "para":
            out = [inline(content)] if inline(content).strip() else []
        else:
            lvl = min(depth + 2, 6)
            out = [f"{'#'*lvl} {inline(content)}"]
        for ch in children:
            out.extend(render_node(ch, depth+1))
        return out

    result = []
    for node in root_children:
        result.extend(render_node(node, 0))
    # 表格：连续 `| ... |` 行攒成 md 表格（首行表头 + 分隔行）
    merged_lines = []
    i = 0
    rows = []
    while i < len(result):
        ln = result[i]
        if ln.startswith("| ") and ln.endswith(" |"):
            rows.append(ln)
        else:
            if rows:
                merged_lines.append(rows[0])
                merged_lines.append("|" + "|".join(["---"]*(rows[0].count(" | "))) + "|")
                merged_lines.extend(rows[1:])
                rows = []
            merged_lines.append(ln)
        i += 1
    if rows:
        merged_lines.append(rows[0])
        merged_lines.append("|" + "|".join(["---"]*(rows[0].count(" | "))) + "|")
        merged_lines.extend(rows[1:])
    result = merged_lines
    txt = "\n".join(result)
    txt = re.sub(r'\n{3,}', '\n\n', txt)
    return txt.strip()

def man_to_md(man_path, title):
    text = read_man(man_path)
    text = clean_meta(text)
    blocks = parse_blocks(text)
    md = blocks_to_md(blocks)
    md = f"# {title}\n\n{md}\n" if md else f"# {title}\n\n<!-- 占位 -->\n"
    # zDoc 语法文档：图片全是语法示例，还原成行内代码（`<../logo.png>`）
    if "syntax.man" in man_path:
        md = re.sub(r'!\[([^\]]*)\]\(([^)]*\.(?:png|jpg))\s*\)', lambda m: f"`<{m.group(2)}>`", md)
    return md

def safe_fn(s):
    s = re.sub(r'[\\/:*?"<>|]', "／", s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

# ---- 构建发布面 ----
# 分组: NN-分组名/NN-标题.md（组内按 index.xml 顺序）
# 根级: nutz_preface.man → 00-写在前面的话.md；nutz_release_notes.man → 01-发行注记.md
manifest = {"groups": {}, "files": [], "imgs": []}

def read_title(man_path):
    for ln in open(man_path, encoding="utf-8", errors="replace"):
        if ln.startswith("#title:"):
            return ln.split(":", 1)[1].strip()
    return ""

# 根级 2 篇
root_files = [
    ("nutz_preface.man", "00-写在前面的话.md"),
    ("nutz_release_notes.man", "01-发行注记.md"),
]
for man, outname in root_files:
    src = os.path.join(SRC, man)
    if os.path.exists(src):
        title = read_title(src)
        md = man_to_md(src, title)
        with open(os.path.join(OUT, outname), "w", encoding="utf-8") as f:
            f.write(md)
        manifest["files"].append(outname)

def glob_all_md():
    import glob
    return glob.glob(os.path.join(OUT, "**", "*.md"), recursive=True)

n_fix = 0

for gi, (gdir, gtitle) in enumerate(INDEX):
    gnum = f"{gi+2:02d}"
    gname = f"{gnum}-{safe_fn(gtitle)}"
    gpath = os.path.join(OUT, gname)
    os.makedirs(gpath, exist_ok=True)
    files = GROUP_ORDER.get(gdir, [])
    manifest["groups"][gdir] = gname
    for fi, man in enumerate(files):
        src = os.path.join(SRC, gdir, man)
        if not os.path.exists(src):
            continue
        title = read_title(src)
        md = man_to_md(src, title)
        fnum = f"{fi+1:02d}"
        outname = f"{fnum}-{safe_fn(title)}.md"
        with open(os.path.join(gpath, outname), "w", encoding="utf-8") as f:
            f.write(md)
        manifest["files"].append(f"{gname}/{outname}")

# ---- 图片: 按 md 相对路径复制（保持 .man 目录形态）----
import shutil
img_refs = set()
for root, dirs, files in os.walk(SRC):
    for fn in files:
        if fn.endswith(".man"):
            p = os.path.join(root, fn)
            text = open(p, encoding="utf-8", errors="replace").read()
            for m in re.finditer(r'<([0-9]+x[0-9]+:)?([^<>]*\.(?:png|jpg|gif|jpeg|PNG|JPG|GIF))>', text):
                inner = m.group(2)
                if inner.startswith("http"):
                    continue
                # 相对 .man 所在目录
                base = os.path.dirname(p)
                abs_p = os.path.normpath(os.path.join(base, inner))
                if os.path.exists(abs_p):
                    rel = os.path.relpath(abs_p, SRC)
                    img_refs.add(rel)

# 复制引用的图到 site 对应位置（site/<rel>）
for rel in img_refs:
    src = os.path.join(SRC, rel)
    dst = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    manifest["imgs"].append(rel)

# ---- 图片引用重写：md 内 `![x](<相对 .man 目录>)` → 相对当前 md 的正确路径 ----
# 每个 .man 的相对基准目录 = SRC 下其所在目录；site 镜像位置 = OUT/<rel>
def img_abs_in_site(man_dir, inner):
    abs_p = os.path.normpath(os.path.join(man_dir, inner))
    rel = os.path.relpath(abs_p, SRC)
    return os.path.normpath(os.path.join(OUT, rel))

for md_path in glob_all_md():
    txt = open(md_path, encoding="utf-8").read()
    md_dir = os.path.dirname(md_path)
    def _fix(m):
        name, path = m.group(1), m.group(2)
        if path.startswith("http"):
            return m.group(0)
        # 找对应 .man（site/<NN-组>/<NN-名>.md → 源 <组>/<源文件名>.man）
        # 用 basename 反查：哪个 .man 的 #title 对应？这里直接按「md 内路径解析到 site」
        ap = os.path.normpath(os.path.join(md_dir, path))
        if os.path.exists(ap):
            return m.group(0)
        # 尝试从 SRC 的任意 .man 目录解析（同名图可能多处）
        cands = []
        for root, dirs, files in os.walk(SRC):
            for fn in files:
                if fn == path.split('/')[-1]:
                    abs_p = os.path.normpath(os.path.join(root, fn))
                    cands.append(abs_p)
        if not cands:
            return m.group(0)  # 保留原样（缺失）
        # 用与 md 所在组一致的候选（同组优先）
        group = os.path.basename(md_dir).split('-', 1)[-1]
        best = None
        for c in cands:
            if group in c:
                best = c
                break
        if best is None:
            best = cands[0]
        rel_site = os.path.relpath(best, SRC)
        site_abs = os.path.normpath(os.path.join(OUT, rel_site))
        rel_md = os.path.relpath(site_abs, md_dir)
        return f"![{name}]({rel_md})"
    new = re.sub(r'!\[([^]]*)\]\(([^)]*\.(?:png|jpg|gif|jpeg))\s*\)', _fix, txt)
    if new != txt:
        open(md_path, "w", encoding="utf-8").write(new)
        n_fix += 1

print("img refs rewritten:", n_fix)

with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=1)

print("files:", len(manifest["files"]), "groups:", len(manifest["groups"]), "imgs:", len(manifest["imgs"]))
for g, gn in manifest["groups"].items():
    print(" ", g, "->", gn)
