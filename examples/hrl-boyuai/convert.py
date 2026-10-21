#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hrl.boyuai.com (dumi SSR) 页面 → markdown。
- 正文区: div.__dumi-default-layout-content > div.markdown
- 公式: MathJax SVG（无 TeX 源）→ 抽 <svg> 存 _math/<hash>.svg，正文内嵌 <img>
- 图片: /static/*.png|jpg|gif → 存 _img/<name>，正文内嵌
- 代码: <pre class="prism-code language-XXX"> 的 token-line → fenced code
"""
import re, os, sys, json, hashlib, html as htmllib
from html.parser import HTMLParser

# 资源相对引用前缀：md 落在 depth-1 子目录时须补 "../"（相对自身才解析得到）
ASSET_PREFIX = ""

VOID = {"br","img","hr","input","meta","link","path","use","polygon","rect","circle","line",
        "polyline","ellipse","stop","image","area","col","source","track","wbr","text"}  # text 单独处理

class Node:
    __slots__ = ("tag","attrs","children","parent")
    def __init__(self, tag, attrs, parent=None):
        self.tag=tag; self.attrs=attrs or {}; self.children=[]; self.parent=parent

class DOM(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root=Node("#root",{})
        self.stack=[self.root]
    def handle_starttag(self, tag, attrs):
        n=Node(tag, dict(attrs), self.stack[-1]); self.stack[-1].children.append(n)
        if tag not in VOID:
            self.stack.append(n)
    def handle_startendtag(self, tag, attrs):
        n=Node(tag, dict(attrs), self.stack[-1]); self.stack[-1].children.append(n)
    def handle_endtag(self, tag):
        if tag in VOID: return
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:
                del self.stack[i:]; break
    def handle_data(self, data):
        if data.strip()=="" and data.strip("\n")=="" and not data.strip():
            # keep meaningful whitespace only between words
            pass
        self.stack[-1].children.append(("text", data))

def text_of(node):
    out=[]
    for c in node.children:
        if isinstance(c, tuple): out.append(c[1])
        else: out.append(text_of(c))
    return "".join(out)

# ---------- 资源预处理 ----------
def preprocess_assets(html_str, img_dir):
    """把 data:base64 图存盘 + /static/ → _img/ 相对路径。"""
    import base64
    def rep_data(m):
        ext=m.group(1).lower(); ext='jpg' if ext=='jpeg' else ext
        raw=base64.b64decode(m.group(2))
        h=hashlib.md5(raw).hexdigest()[:16]
        p=os.path.join(img_dir, f"data_{h}.{ext}")
        if not os.path.exists(p):
            open(p,"wb").write(raw)
        return f'src="_img/data_{h}.{ext}"'
    html_str=re.sub(r'src="data:image/(\w+);base64,([^"]+)"', rep_data, html_str)
    html_str=re.sub(r'src="/static/([^"]+)"', lambda m: f'src="_img/{m.group(1).split("/")[-1]}"', html_str)
    return html_str

# ---------- 公式预处理 ----------
def preprocess_math(html_str, math_dir, math_map):
    """把 math 包裹层替换为占位标签, 抽出 svg 存盘。返回处理后的 html。"""
    stats={"n":0,"new":0}
    def save_svg(svg):
        # 归一化去 id 用于跨页去重
        norm=re.sub(r'MJX-\d+','MJX',svg)
        norm=re.sub(r'\bid="[^"]*"','',norm)
        norm=re.sub(r'xlink:href="#[^"]*"','',norm)
        h=hashlib.md5(norm.encode()).hexdigest()[:16]
        if h not in math_map:
            # ex → px (1ex≈8px) 让外部 <img> 尺寸稳定
            s=re.sub(r'\b(width|height)="([0-9.]+)ex"',
                     lambda m: f'{m.group(1)}="{round(float(m.group(2))*8,2)}px"', svg)
            with open(os.path.join(math_dir,h+".svg"),"w",encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n'+s)
            math_map[h]=h+".svg"; stats["new"]+=1
        stats["n"]+=1
        return "_math/"+h+".svg"
    def rep_display(m):
        svg=re.search(r'(<svg\b.*</svg>)', m.group(0), re.S)
        url=save_svg(svg.group(1)) if svg else None
        return f'<mathd data-u="{url}"></mathd>' if url else ''
    def rep_inline(m):
        svg=re.search(r'(<svg\b.*</svg>)', m.group(0), re.S)
        url=save_svg(svg.group(1)) if svg else None
        return f'<mathi data-u="{url}"></mathi>' if url else ''
    html_str=re.sub(r'<div class="math math-display">.*?</div>', rep_display, html_str, flags=re.S)
    html_str=re.sub(r'<span class="math math-inline">.*?</span>', rep_inline, html_str, flags=re.S)
    return html_str, stats

# ---------- 渲染 ----------
def inline(node):
    parts=[]
    for c in node.children:
        if isinstance(c, tuple):
            parts.append(c[1]); continue
        t=c.tag
        if t=="mathi":
            parts.append(f'![]({ASSET_PREFIX}{c.attrs.get("data-u","")})')
        elif t=="a":
            if c.attrs.get("aria-hidden")=="true": continue
            href=c.attrs.get("href",""); txt=inline(c)
            if href.startswith("http"):
                parts.append(f'[{txt}]({href})')
            else:
                parts.append(txt)  # 站内链/锚点 → 纯文本
        elif t=="strong" or t=="b": parts.append("**"+inline(c)+"**")
        elif t=="em" or t=="i": parts.append("*"+inline(c)+"*")
        elif t=="code": parts.append("`"+text_of(c).strip()+"`")
        elif t=="br": parts.append("\n")
        elif t=="img":
            src=c.attrs.get("src","")
            parts.append(f'![]({ASSET_PREFIX}{src})' if src.startswith("_img/") else "")
        elif t=="mathd":
            parts.append(f'\n\n![]({ASSET_PREFIX}{c.attrs.get("data-u","")})\n\n')
        elif t=="span":
            if "icon" in c.attrs.get("class",""): continue
            parts.append(inline(c))
        else:
            # 未识别(含 svg 图标): 只取文本
            parts.append(inline(c))
    return "".join(parts)

def img_local(src):
    name=src.split("/")[-1]
    return "_img/"+name

def collect_imgs(content_html, img_dir):
    names=[]
    for m in re.finditer(r'<img\b[^>]*?\bsrc="(/static/[^"]+)"', content_html):
        nm=m.group(1).split("/")[-1]
        if nm not in names: names.append(nm)
    return names

def render_block(node, out, depth=0):
    for c in node.children:
        if isinstance(c, tuple):
            txt=c[1].strip()
            if txt: out.append(txt)
            continue
        t=c.tag
        if t in ("h1","h2","h3","h4","h5","h6"):
            lvl=int(t[1]); txt=inline(c).strip()
            out.append("#"*lvl+" "+txt)
        elif t=="p":
            txt=inline(c).strip()
            if txt: out.append(txt)
        elif t in ("ul","ol"):
            render_list(c, out, ordered=(t=="ol"))
        elif t=="pre":
            out.append(render_code(c))
        elif t=="table":
            out.append(render_table(c))
        elif t=="center":
            txt=inline(c).strip()
            if txt: out.append(txt)
        elif t=="div":
            cls=c.attrs.get("class","")
            if "math math-display" in cls:  # 理论上已被替换
                continue
            if "__dumi-default-table" in cls:
                # 里面包着真表格
                render_block(c, out, depth)
            elif c.attrs.get("align")=="center":
                inner=[x for x in c.children if not isinstance(x,tuple)]
                if inner and any(x.tag=="img" for x in inner):
                    for x in inner:
                        if x.tag=="img":
                            src=x.attrs.get("src","")
                            if src.startswith("_img/"):
                                out.append(f'![]({ASSET_PREFIX}{src})')
                else:
                    txt=inline(c).strip()
                    if txt: out.append(txt)
            else:
                render_block(c, out, depth)
        elif t=="mathd":
            u=c.attrs.get("data-u","")
            if u: out.append(f'![]({ASSET_PREFIX}{u})')
        elif t in ("mjx-container","svg","script","style","button"):
            continue
        elif t=="hr":
            out.append("---")
        elif t=="blockquote":
            txt=inline(c).strip(); out.append("> "+txt)
        else:
            # 兜底: 递归/文本
            txt=inline(c).strip()
            if txt: out.append(txt)

def render_list(node, out, ordered, indent=""):
    for i,c in enumerate([x for x in node.children if not isinstance(x,tuple)],1):
        if c.tag!="li": continue
        mark=f"{i}. " if ordered else "- "
        # 简单处理: 列表项内联文本 + 嵌套列表
        txt=inline(c).strip()
        if txt: out.append(indent+mark+txt)
        for sub in c.children:
            if not isinstance(sub,tuple) and sub.tag in ("ul","ol"):
                render_list(sub, out, ordered=(sub.tag=="ol"), indent=indent+"  ")

def render_code(pre):
    cls=pre.attrs.get("class","")
    m=re.search(r'language-([\w+-]+)', cls)
    lang=m.group(1) if m else ""
    lines=[d for d in pre.children if not isinstance(d,tuple) and d.tag=="div" and "token-line" in d.attrs.get("class","")]
    if lines:
        code="\n".join(text_of(ln) for ln in lines)
    else:
        code=text_of(pre)
    code=code.rstrip("\n")
    fence="```"
    return fence+lang+"\n"+code+"\n"+fence

def render_table(tbl):
    rows=[]
    thead=None
    for sec in tbl.children:
        if isinstance(sec,tuple): continue
        if sec.tag=="thead":
            thead=[ [inline(td).strip().replace("\n"," ") for td in tr.children if not isinstance(td,tuple) and td.tag in("th","td")]
                    for tr in sec.children if not isinstance(tr,tuple) and tr.tag=="tr"]
        elif sec.tag=="tbody":
            for tr in sec.children:
                if isinstance(tr,tuple) or tr.tag!="tr": continue
                rows.append([inline(td).strip().replace("\n"," ") for td in tr.children if not isinstance(td,tuple) and td.tag in("td","th")])
        elif sec.tag=="tr":
            rows.append([inline(td).strip().replace("\n"," ") for td in sec.children if not isinstance(td,tuple) and td.tag in("td","th")])
    if not thead:
        if not rows: return ""
        thead=[rows[0]]; rows=rows[1:]
    ncol=len(thead[0]) if thead else 0
    out=["| "+" | ".join(thead[0])+" |", "| "+" | ".join(["---"]*ncol)+" |"]
    for r in rows:
        r=(r+[""]*ncol)[:ncol]
        out.append("| "+" | ".join(r)+" |")
    return "\n".join(out)

def convert_page(html_str, math_dir, math_map, img_dir, prefix=""):
    global ASSET_PREFIX
    ASSET_PREFIX = prefix
    i=html_str.find("__dumi-default-layout-content")
    if i<0: return "", {"n":0,"new":0}
    i=html_str.find(">", i)+1
    j=html_str.find("<script", i)
    content=html_str[i:j]
    # 去掉 copy 按钮
    content=re.sub(r'<button[^>]*></button>','',content)
    content=preprocess_assets(content, img_dir)
    content, mstat = preprocess_math(content, math_dir, math_map)
    dom=DOM(); dom.feed(content)
    out=[]
    root=dom.root
    render_block(root, out)
    # 清理
    txt="\n\n".join(x for x in out if x.strip())
    txt=re.sub(r'\n{3,}','\n\n',txt).strip()+"\n"
    return txt, mstat

if __name__=="__main__":
    print("module; use build.py")