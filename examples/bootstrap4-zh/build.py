#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#120 Bootstrap 4 繁體中文手冊 (hexschool/bootstrap_zh @ zh-tw-dev 71e66c0)
站点 bootstrap.hexschool.com 的 md 源在 zh-tw-dev:site/docs/4.2/*.md（Jekyll+Liquid）。
用极简 Liquid 引擎（liquid.py）展开 include/capture/highlight/for/if → md。
结构：按 nav.yml 分组（中文组名）建 TITLE 目录，篇名取 front matter title。
"""
import os, re, sys, yaml, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import liquid  # noqa

SRC = "src/site"
DOCS = os.path.join(SRC, "docs", "4.2")
INC = os.path.join(SRC, "_includes")
DATA = os.path.join(SRC, "_data")
OUT = "build"

GROUPS = [
    ("getting-started", "快速開始"),
    ("layout", "排版"),
    ("content", "內容"),
    ("components", "元件"),
    ("utilities", "通用類別"),
    ("extend", "擴增"),
    ("about", "關於"),
]


def load_ctx():
    data = {}
    for fn in os.listdir(DATA):
        if fn.endswith((".yml", ".yaml")):
            with open(os.path.join(DATA, fn), encoding="utf-8") as f:
                data[fn.rsplit(".", 1)[0]] = yaml.safe_load(f)
    return {
        "site": {"baseurl": "", "docs_version": "4.2", "repo": "", "data": data},
    }


def front_matter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except Exception:
        fm = {}
    return fm, text[m.end():]


def render(text, ctx):
    nodes, _, _ = liquid.parse(liquid.lex(text))
    return eval_nodes(nodes, ctx)


def eval_nodes(nodes, ctx, inc=INC):
    out = []
    for n in nodes:
        k = n["kind"]
        if k == "text":
            out.append(n["text"])
        elif k == "var":
            v = liquid.resolve(n["raw"], ctx)
            out.append("" if v is None else str(v))
        elif k == "tag":
            out.append(do_tag(n["raw"], ctx, inc))
        elif k == "capture":
            name = n["raw"].split(None, 1)[1].strip()
            ctx[name] = eval_nodes(n["body"], ctx, inc)
        elif k == "highlight":
            lang = n["raw"].split()[1] if len(n["raw"].split()) > 1 else ""
            body = eval_nodes(n["body"], ctx, inc)
            out.append("\n```" + lang + "\n" + body.strip("\n") + "\n```\n")
        elif k == "for":
            m = re.match(r"for\s+(\w+)\s+in\s+(.+)", n["raw"])
            var = m.group(1); expr = m.group(2).strip()
            rm = re.match(r"\(\s*(\d+)\s*\.\.\s*(\d+)\s*\)", expr)
            it = list(range(int(rm.group(1)), int(rm.group(2)) + 1)) if rm else liquid.resolve(expr, ctx)
            if not isinstance(it, list):
                it = []
            for i, item in enumerate(it):
                sub = dict(ctx); sub[var] = item
                sub["forloop"] = {"index": i + 1, "index0": i, "first": i == 0, "last": i == len(it) - 1}
                out.append(eval_nodes(n["body"], sub, inc))
        elif k in ("if", "unless"):
            first = n["raw"].split(None, 1)[1]
            for idx, (raw, branch) in enumerate(n["branches"]):
                if idx == 0:
                    ok = (not liquid.eval_cond(first, ctx)) if k == "unless" else liquid.eval_cond(first, ctx)
                else:
                    kw = raw.split()[0]
                    ok = True if kw == "else" else liquid.eval_cond(raw.split(None, 1)[1], ctx)
                if ok:
                    out.append(eval_nodes(branch, ctx, inc)); break
    return "".join(out)


def do_tag(raw, ctx, inc):
    kw = raw.split()[0]
    if kw == "assign":
        m = re.match(r"assign\s+(\w+)\s*=\s*(.*)", raw)
        ctx[m.group(1)] = liquid.resolve(m.group(2), ctx)
        return ""
    if kw == "include":
        return do_include(raw, ctx, inc)
    return ""


def do_include(raw, ctx, inc):
    rest = raw[len("include"):].strip()
    file = rest.split()[0]
    params = {}
    for m in re.finditer(r"(\w+)=(\"[^\"]*\"|'[^']*'|\S+)", rest):
        params[m.group(1)] = m.group(2).strip("\"'")
    path = os.path.join(inc, file)
    if file.endswith(".md"):
        if os.path.exists(path):
            txt = open(path, encoding="utf-8").read()
            sub = dict(ctx); sub["include"] = params
            return render(txt, sub)
        return ""
    if file == "example.html":
        if "hide_markup" in rest:
            return ""
        c = ctx.get(params.get("content", ""), "")
        return "\n```html\n" + str(c).strip() + "\n```\n"
    if file == "callout.html":
        c = ctx.get(params.get("content", ""), "") or ""
        t = params.get("type", "info")
        label = {"info": "Note", "warning": "警告", "danger": "危險"}.get(t, "Note")
        body = "\n".join(("> " + ln) if ln.strip() else ">" for ln in str(c).strip().split("\n"))
        return f"\n> **{label}**\n>\n{body}\n"
    if file.startswith("icons/"):
        return '<img src="..." alt="...">'
    if file == "bugify.html":
        return str(ctx.get(params.get("content", ""), ""))
    return ""


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    nav = yaml.safe_load(open(os.path.join(DATA, "nav.yml"), encoding="utf-8"))
    # url→(group_title, order)
    group_order = {}
    for g in nav:
        gt = g["title"]
        pages = g.get("pages") or []
        for i, p in enumerate(pages):
            group_order[slugify(p.get("url", p["title"]))] = (gt, i)

    # 00-说明
    open(os.path.join(OUT, "00-說明.md"), "w", encoding="utf-8").write(
        "> 来源：https://github.com/hexschool/bootstrap_zh @ 71e66c0（zh-tw-dev 分支；站点 bootstrap.hexschool.com）"
        " ｜ Bootstrap 4.2 官方文件繁體中文手冊（六角學院譯）；正文取 md 源 site/docs/4.2，按官方分組結構。\n")

    root_docs = {"browser-bugs": ("90-瀏覽器 Bug.md", "瀏覽器 Bug"), "migration": ("91-更版紀錄.md", "更版紀錄")}
    # 收集每个 group dir 的文件
    for d, gtitle in GROUPS:
        dirpath = os.path.join(DOCS, d)
        if not os.path.isdir(dirpath):
            continue
        files = [f for f in sorted(os.listdir(dirpath)) if f.endswith(".md")]
        items = []
        for f in files:
            base = f[:-3]
            fm, _ = front_matter(open(os.path.join(dirpath, f), encoding="utf-8").read())
            order = group_order.get(base, (None, 999))[1]
            title = fm.get("title", base)
            items.append((order, title, os.path.join(dirpath, f)))
        items.sort(key=lambda x: (x[0], x[1]))
        outdir = os.path.join(OUT, gtitle)
        os.makedirs(outdir)
        for i, (order, title, path) in enumerate(items, 1):
            ctx = load_ctx()
            fm, body = front_matter(open(path, encoding="utf-8").read())
            md = render(body, ctx)
            md = post_md(md, prefix="../")
            name = f"{i:02d}-{str(title).replace('/', '／')}.md"
            open(os.path.join(outdir, name), "w", encoding="utf-8").write(md)
            print(f"  {d}/{os.path.basename(path):28} -> {gtitle}/{name} ({len(md)})")
    # 根级 docs
    for base, (outname, title) in root_docs.items():
        p = os.path.join(DOCS, base + ".md")
        if os.path.exists(p):
            ctx = load_ctx()
            fm, body = front_matter(open(p, encoding="utf-8").read())
            md = post_md(render(body, ctx))
            open(os.path.join(OUT, outname), "w", encoding="utf-8").write(md)
            print("  root ->", outname)
    copy_assets()
    print("done")


def post_md(md, prefix=""):
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"\{#[^}]*\}", "", md)          # Kramdown 锚点
    md = re.sub(r"\{:[^}]*\}", "", md)           # Kramdown 属性
    md = re.sub(r"\n{3,}", "\n\n", md)
    # 图片：/docs/4.2/assets/... → <prefix>assets/...
    md = md.replace('src="/docs/4.2/assets/', 'src="' + prefix + 'assets/')
    md = md.replace("](/docs/4.2/assets/", "](" + prefix + "assets/")
    md = re.sub(r"\]\(\((https?://[^)]+)\)\)", r"](\1)", md)   # 双括号链接
    md = strip_bd_wrappers(md)
    return md.strip() + "\n"


def strip_bd_wrappers(md):
    out, pend = [], False
    for ln in md.split("\n"):
        if re.match(r'^<div class="bd-example[^"]*"\s*>\s*$', ln):
            pend = True
            continue
        if pend and re.match(r"^</div>\s*$", ln):
            pend = False
            continue
        out.append(ln)
    return "\n".join(out)


def copy_assets():
    refs = set()
    for root, _, files in os.walk(OUT):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            t = open(os.path.join(root, fn), encoding="utf-8").read()
            refs |= set(re.findall(r'src="(?:\.\./)?(assets/[^"]+)"', t))
            refs |= set(re.findall(r"\]\((?:\.\./)?(assets/[^)]+)\)", t))
    for r in refs:
        s = os.path.join(DOCS, r)
        d = os.path.join(OUT, r)
        if os.path.exists(s):
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
    print("assets:", len(refs))


if __name__ == "__main__":
    main()
