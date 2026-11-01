#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""d3 wiki 中文翻译集合 -> 语雀导入树 (fpb52 #175 官方API文档)

源: mbostock/d3.wiki @ cecbbd1e (2021-07-04)
发布面: 43 个中文页 (CN-Home + API--中文手册 + 41 专篇)
  - 7 个导航壳 (核心函数/地理/几何/布局/比例尺/SVG函数/行为) -> TITLE 目录
  - 时间分区无中文页 (死链) 不建
  - 剔 6B 垃圾页 捆布局.md ("奈斯")
  - 英/日/俄/繁/印尼/其他语言页不收
"""
import os, re, shutil, sys

WIKI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(WIKI, "site")
if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

# ---------- 结构定义 ----------
# 组: (TITLE 名, [(页码在组内标题, 磁盘文件名), ...])
GROUPS = [
    ("03-核心函数", [
        ("01-选择器.md", "选择器.md"),
        ("02-过渡.md", "过渡.md"),
        ("03-数组.md", "数组.md"),
        ("04-请求.md", "请求.md"),
        ("05-CSV格式化.md", "CSV格式化.md"),
        ("06-格式化.md", "格式化.md"),
        ("07-本地化.md", "本地化.md"),
        ("08-颜色.md", "颜色.md"),
        ("09-命名空间.md", "命名空间.md"),
        ("10-数学.md", "数学.md"),
        ("11-内部.md", "内部.md"),
    ]),
    ("04-地理", [
        ("01-地理路径.md", "地理路径.md"),
        ("02-地理投影.md", "地理投影.md"),
    ]),
    ("05-几何", [
        ("01-泰森多边形.md", "泰森多边形.md"),
        ("02-四叉树.md", "四叉树.md"),
        ("03-赫尔.md", "赫尔.md"),
        ("04-多边形.md", "多边形.md"),
    ]),
    ("06-布局", [
        ("01-捆绑布局.md", "捆绑布局.md"),
        ("02-弦布局.md", "弦布局.md"),
        ("03-簇布局.md", "簇布局.md"),
        ("04-力布局.md", "力布局.md"),
        ("05-层次布局.md", "层次布局.md"),
        ("06-直方图布局.md", "直方图布局.md"),
        ("07-包布局.md", "包布局.md"),
        ("08-分区布局.md", "分区布局.md"),
        ("09-饼布局.md", "饼布局.md"),
        ("10-堆叠布局.md", "堆叠布局.md"),
        ("11-树布局.md", "树布局.md"),
        ("12-矩形树布局.md", "矩形树布局.md"),
    ]),
    ("07-比例尺", [
        ("01-数值比例尺.md", "数值比例尺.md"),
        ("02-序数比例尺.md", "序数比例尺.md"),
        ("03-时间比例尺.md", "时间比例尺.md"),
    ]),
    ("08-SVG函数", [
        ("01-SVG-形状.md", "SVG-形状.md"),
        ("02-SVG-轴.md", "SVG-轴.md"),
        ("03-SVG-控件.md", "SVG-控件.md"),
    ]),
    ("09-行为", [
        ("01-拖动.md", "拖动.md"),
        ("02-缩放.md", "缩放.md"),
    ]),
]

# ---------- 转换器 ----------
RE_CRUMB = re.compile(r'^> \[Wiki\].*\n', re.M)          # 面包屑首行
RE_BRACKET_URL = re.compile(r'\[\[([^]|]+)\|([^]]+)\]\]')  # [[文字|URL]] / [[文字|页面]]
RE_BRACKET_PAGE = re.compile(r'\[\[([^]|]+)\]\]')          # [[页面]]
RE_MD_LINK = re.compile(r'!\[[^\]]*\]\([^)]*\)|\[[^\]]*\]\([^)]*\)')  # 所有 md 链接/图（先处理图）

def is_img(m):
    t = m.group(0)
    return t.startswith('![')

def conv_text(text, fname):
    """处理 wiki 语法 -> markdown（文本传递函数，图已在前面处理过）"""
    # 1. 面包屑行
    text = RE_CRUMB.sub('', text, count=1)
    # 2. 译者样板块（「如发现翻译不当…邮箱…QQ群…」多行）
    text = re.sub(r'(?ms)^\* 如发现翻译不当[^\n]*\n(?:\* [^\n]*\n)*', '', text)
    # 3. 签名锚点行: <a name/href="#x">#</a> d3.<b>select</b>(<i>selector</i>) -> `d3.select(selector)`
    def sig_sub(m):
        rest = m.group(1)
        rest = re.sub(r'</?(?:b|i|em|strong|tt|code)[^>]*>', '', rest)
        # wiki 粗/斜体标记（**ease** / *value*）在反引号内会显示为字面量 -> 剥掉
        rest = rest.replace('**', '').replace('*', '')
        rest = rest.strip()
        # 签名行以字母/点/数字开头（函数名），包行内反引号
        if rest and rest[0] not in '（( \n\t]' and not re.match(r'[\u4e00-\u9fff]', rest[0]):
            return f'`{rest}`'
        return rest
    text = re.sub(r'<a (?:name="[^"]*"|href="[^"]*#?"*)[^>]*>\s*(?:#|[0-9]+)?\s*</a>\s*([^\n]*)', sig_sub, text)
    # 3b. 残留无 # 内容的 <a name> 纯锚（如 <a name="x" href="x"></a>）剥
    text = re.sub(r'<a name="[^"]*"[^>]*>\s*</a>', '', text)
    # 3c. HTML 图包裹链: <a href="URL"><img src="IMG" width=W></a> -> [![例图](IMG)](URL)
    def html_img_sub(m):
        href, src = m.group(1), m.group(2)
        return f'[![查看 bl.ocks 示例]({src})]({href})'
    text = re.sub(r'<a href="(https?://[^"]+)"><img src="(https?://[^"]+)"[^>]*></a>', html_img_sub, text)
    # 3d. 空外链锚点行（<a href="http://..."></a> 独立行）整行剥
    text = re.sub(r'^\s*<a href="https?://[^"]*"[^>]*>\s*</a>\s*$', '', text, flags=re.M)
    # 4. 剥遗留 b/i/a/em 标签（保文本）
    text = re.sub(r'</?(?:b|i|em|strong|tt|code|sub|sup|span|div)[^>]*>', '', text)
    # 5. wiki 内链 [[文字|URL]] -> [文字](URL)；[[文字|页面]] -> 纯文本；[[页面]] -> 纯文本；[[label](url)] 译者签名 -> [label](url)
    def bk_sub(m):
        label, target = m.group(1), m.group(2)
        if re.match(r'^https?://', target):
            return f'[{label}]({target})'
        return label
    text = RE_BRACKET_URL.sub(bk_sub, text)
    text = RE_BRACKET_PAGE.sub(lambda m: m.group(1), text)
    text = re.sub(r'\[\[([^]\]]+)\]\(([^)]+)\)\]', r'[\1](\2)', text)
    # 6. md 链接: 图已处理; 站内/锚点链接转纯文本, 外链保留
    def link_sub(m):
        t = m.group(0)
        if is_img(m):
            return t
        inner = t[1:-1]
        if '](' not in inner:
            return t
        label, url = inner.split('](', 1)
        url = url.rstrip(')')
        if re.match(r'^https?://', url):
            return f'[{label}]({url})'
        if url.startswith('github.com/mbostock/d3'):
            return label  # 本库未导入的英文页
        return label
    text = RE_MD_LINK.sub(link_sub, text)
    # 7. `<a name>` 残留(无 # 内容)剥
    text = re.sub(r'<a name="[^"]*"[^>]*>\s*</a>', '', text)
    # 7b. 剥遗留 <a href="...#..."> 纯链接残留
    text = re.sub(r'<a href="#[^"]*"[^>]*>\s*</a>', '', text)
    # 8. 真 `#` 函数标题与正文标题整体降一级 (子页)
    def shift(m):
        return '#' + m.group(0)
    text = re.sub(r'^#{1,4} ', shift, text, flags=re.M)
    # 9. 尾部译者署名行保留原样（已是列表）
    return text

def localize_wiki_png(text):
    """https://github.com/mbostock/d3/wiki/xxx.png -> xxx.png（本地文件）"""
    def sub(m):
        alt, fn = m.group(1), m.group(2)
        return f'![{alt}]({fn})'
    return re.sub(r'!\[([^\]]*)\]\(https://github\.com/mbostock/d3/wiki/([^)]+\.png)\)', sub, text)

def mark_dead_imgs(text):
    """f.cloud.github.com 死链图 -> 原图缺失标注"""
    def sub(m):
        alt = m.group(1)
        return f'> ⚠️ 原图缺失：{alt}（f.cloud.github.com 图床已下线）'
    return re.sub(r'!\[([^\]]*)\]\(https://f\.cloud\.github\.com/[^)]+\)', sub, text)

def clean_md(text):
    """最终清理：空列表行合并、连续空行压缩"""
    text = re.sub(r'^\s*[-*+]\s*$', '', text, flags=re.M)   # 空列表项
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+$', '', text, flags=re.M)
    return text.strip() + '\n'

# ---------- 处理 ----------
def build_doc(src_file, out_name):
    with open(os.path.join(WIKI, src_file), encoding='utf-8') as f:
        raw = f.read()
    # 所有文档统一降级：文档标题由文件名承担（含根级三篇）
    text = localize_wiki_png(raw)
    text = mark_dead_imgs(text)
    text = conv_text(text, src_file)
    final = clean_md(text)
    with open(os.path.join(OUT, out_name), 'w', encoding='utf-8') as f:
        f.write(final)
    return final

# 根级三篇
build_doc("CN-Home.md", "01-D3.js 简介.md")
build_doc("API--中文手册.md", "02-API 中文手册.md")

# 组
for title, items in GROUPS:
    d = os.path.join(OUT, title)
    os.makedirs(d, exist_ok=True)
    for out_name, src in items:
        build_doc(src, os.path.join(title, out_name))

# 00-说明
note = """# 00-说明

> 本库为 D3.js 官方 wiki 中文翻译集合的镜像整理，源仓库 `mbostock/d3.wiki` @ `cecbbd1e`（2021-07-04 最后更新）。

## 来源与发布面

- 源：https://github.com/mbostock/d3/wiki（官方 wiki，D3 v3 时代资料）
- commit：`cecbbd1e538e519605a2e4a163f46315918e9a0b`（2021-07-04）
- 发布面：43 个中文页面 —— `01-D3.js 简介`（CN-Home）+ `02-API 中文手册`（API--中文手册）+ 41 个中文专篇
- 剔：`捆布局.md`（6 字节垃圾页「奈斯」）；英文（Home/Gallery/Tutorials/Plugins 等）、日文（JP-*）、俄文、繁体（TW-Home）、印尼文（ID-Home）页面均不收
- `时间` 分区（d3.time）无中文翻译页（原文链接为死链），不建空节点

## 结构与导航壳

- 原 wiki 面包屑层级：`API--中文手册 ▸ 分组 ▸ 专篇`。7 个分组（导航壳页：核心函数/地理/几何/布局/比例尺/SVG函数/行为）正文仅为子页链接列表 → 建成目录（TITLE）；专篇文档挂其下
- 顺序按 `02-API 中文手册` 原书 8 大分区顺序（核心→地理→几何→布局→比例尺→SVG→行为；时间未翻译跳过）

## 翻译背景（节自原页）

- 本文档由 [VisualCrew 小组](https://github.com/VisualCrew) 耗时两年翻译，保持与 D3 V3 最后一版（3.5.17）一致。D3 V4 最新版 API 请参考 [d3.v4-API-Translation](https://github.com/tianxuzhang/d3.v4-API-Translation)
- 联系译者：zhang_tianxu@sina.com；QQ 群 D3.js 437278817、大数据可视化 436442115
- API 使用方法可参考：https://github.com/tianxuzhang/d3-api-demo

## 转换口径

- 原 wiki 语法（`[[页面]]` 内链、`[文字](#锚点)`、面包屑导航）已转换为 Markdown；站内/锚点链接转纯文本（语雀死链），外链保留
- `<a name>` 锚点签名行（如 `d3.select(selector)`）转为行内反引号代码
- 图：本地图（色板/示意图）与 `github.com/mbostock/d3/wiki/*.png` 本地化共 45 张转语雀 CDN；`bl.ocks.org` 缩略图外链原样保留；`f.cloud.github.com`（2012 旧图床，已下线）2 张标注「原图缺失」；wikimedia 1 张外链保留
- 正文标题整体降一级（文档标题由文件名承担）
"""
with open(os.path.join(OUT, "00-说明.md"), 'w', encoding='utf-8') as f:
    f.write(note)

# ---------- 图收集 ----------
# 收集 site 内所有本地图引用 -> 拷贝 wiki 根 png
refs = set()
for root, _dirs, files in os.walk(OUT):
    for fn in files:
        if not fn.endswith('.md'):
            continue
        p = os.path.join(root, fn)
        with open(p, encoding='utf-8') as f:
            t = f.read()
        for m in re.finditer(r'!\[[^\]]*\]\(([^)]+\.png)\)', t):
            ref = m.group(1)
            if not re.match(r'^https?://', ref):
                refs.add(ref)

copied = []
for ref in sorted(refs):
    src_p = os.path.join(WIKI, ref)
    if os.path.exists(src_p):
        dst_p = os.path.join(OUT, ref)
        os.makedirs(os.path.dirname(dst_p), exist_ok=True)
        shutil.copy2(src_p, dst_p)
        copied.append(ref)
    else:
        print(f"[warn] 本地图缺失: {ref}")

print(f"文档: {sum(1 for _ in os.walk(OUT) for _ in [0]) if False else ''}", end="")
total_docs = 0
all_md = []
for root, _d, files in os.walk(OUT):
    for fn in files:
        if fn.endswith('.md'):
            all_md.append(os.path.join(root, fn))
print(f"md 文件总数: {len(all_md)}")
print(f"图引用本地文件数: {len(refs)}, 已拷贝: {len(copied)}")
for c in copied:
    print("  img:", c)