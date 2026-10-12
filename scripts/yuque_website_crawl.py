#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语雀网站抓取导入 — 通用爬虫模板（2026-10-13 固化，实战源: gitref/nulab/gitmagic/liaoxuefeng）

用法:
  1. 复制本文件到 tmp/<站点>/crawl.py
  2. 改 SITE 配置区: base / pages / 正文窗口规则
  3. python3 crawl.py → 产物 site/*.md
  4. 产物级验证（必做, 别只看日志）:
     grep -l "导航关键词" site/*.md          # 导航污染
     grep -lE "<[a-z]+" site/*.md | grep -v 合法代码样例
     grep -o "index.html" site/*.md | wc -l  # 站内链接残留
     tail -3 site/*.md                       # 尾部抽查(模板/导航尾巴)
  5. 用 yuque-import-skill 导入 site/ 目录到语雀

正文窗口定位方法论（血泪教训, 逐条遵守）:
  - 先剥 <script>/<style>/<link>/注释, 再定位窗口 —— 评论区 JS 里的字符串
    ('comment-form'/'${...}') 会带偏窗口, 正文被拦腰截断(liaoxuefeng 实踩)
  - 窗口起点: 侧边栏/导航结束后的正文标题(如第一个 <h1)
  - 窗口终点: 评论区/页脚的【标签形式】标记(<div class="comment-form"), 
    禁止 find("comment-form") 裸字符串
  - 后处理: 作者卡片/社交行/评论模板尾巴(${...})/章节导航纯链接 全清

图片方案: 相对路径 <img> 下载 → 语雀 CDN 上传 → md 引用 CDN URL (自包含)。
img_map.json 缓存 src→url, 重跑不重复上传。
"""
import re, os, sys, time, urllib.request, urllib.error, html as h, json

sys.path.insert(0, "/home/admin/.openclaw/workspace/code/yuque-import-skill/scripts")
from yuque_tree_import import upload_image, load_upload_cfg  # noqa: E402

# ================= SITE 配置区（每站必改） =================
SITE = {
    "name": "example",
    "base": "https://example.com/books/x",
    "out": "/home/admin/.openclaw/workspace/tmp/x/site",
    # (输出文件名, 页面相对路径) — 顺序 = 站点目录顺序
    "pages": [
        ("01-首页.md", "index.html"),
    ],
    # 正文窗口规则（正则/查找串, 用 rfind/find 语义）
    "nav_end_marker": "gsc-index-item-title",      # 侧边栏/导航最后一个条目的特征串
    "content_start": "<h1",                        # 正文标题标签（第一个）
    "content_end_re": r'<div[^>]*class="comment-form',  # 评论区【标签形式】标记
    # 后处理: 删行关键词 / 截断标记 / 纯链接行清理
    "drop_lines_with": ["weibo.com/x", "业余马拉松选手"],
    "truncate_at": ["window.gitsite_comment", "gitsite_comment"],
    "strip_nav_links": True,                       # 删首尾纯链接行(面包屑/章节导航)
    # 站内链接重写: url路径尾 → 本库 md 文件名 (跨章互链)
    "link_rewrite": True,                          # 依据 pages 表自动重写
}
# =========================================================

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
IMG_MAP_FILE = None  # 运行时置为 out 同级 img_map.json

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def inline(t):
    """行内元素 → markdown。⚠️ 链接正则: group(1)=链接文字, group(2)=URL, 别搞反!"""
    t = re.sub(r"<br\s*/?>", "\n", t)
    t = re.sub(r'<a\s+[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
               lambda m: m.group(2) if m.group(1).startswith(("#", "javascript"))
               else "[%s](%s)" % (inline(m.group(2)), m.group(1)), t, flags=re.S)
    t = re.sub(r"<(strong|b)>(.*?)</\1>", r"**\2**", t, flags=re.S)
    t = re.sub(r"<(em|i)>(.*?)</\1>", r"*\2*", t, flags=re.S)
    t = re.sub(r"<(code|tt)>(.*?)</\1>",
               lambda m: "`" + h.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip() + "`", t, flags=re.S)
    t = re.sub(r"<[^>]+>", "", t)
    t = h.unescape(t)
    t = re.sub(r"[ \t]*\n[ \t]*", " ", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()

def _load_img_map():
    try:
        return json.load(open(IMG_MAP_FILE, encoding="utf-8"))
    except Exception:
        return {}

def _save_img_map(mp):
    json.dump(mp, open(IMG_MAP_FILE, "w", encoding="utf-8"), ensure_ascii=False)

def img_md(m, page_dir, up):
    """<img> 整标签 → 下载→CDN→![alt](cdn)。img 正则必须抓【整标签】再解析 src/alt。"""
    tag = m.group(0)
    src_m = re.search(r'src="([^"]*)"', tag)
    alt_m = re.search(r'alt="([^"]*)"', tag)
    src = src_m.group(1) if src_m else ""
    alt = (alt_m.group(1) if alt_m else "").strip()
    if src.startswith(("data:", "http://", "https://", "/static", "$")):
        return tag
    mp = _load_img_map()
    if src in mp:
        return f"![{alt}]({mp[src]})"
    try:
        raw = fetch(page_dir + "/" + src)
        tmp = os.path.join("/tmp", "crawl-img-" + os.path.basename(src))
        with open(tmp, "wb") as f:
            f.write(raw)
        url = upload_image(up["cfg"]["cookie"], up["cfg"]["ctoken"], up["user_id"], tmp)
        os.remove(tmp)
        if url:
            mp = _load_img_map()
            mp[src] = url
            _save_img_map(mp)
            print(f"    img→CDN: {src}", flush=True)
            return f"![{alt}]({url})"
    except Exception as e:
        print(f"    img FAIL {src}: {e}", flush=True)
    return f"![{alt}]({page_dir}/{src})"

def html_to_md(html, page_dir, up):
    """正文窗口: 先剥 script/style/link/注释 → nav_end 之后第一个 content_start → content_end_re"""
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S)
    html = re.sub(r"<link[^>]*>", "", html)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    side = html.rfind(SITE["nav_end_marker"])
    start = html.find(SITE["content_start"], side)
    if start < 0:
        start = side + 1
    cm = re.search(SITE["content_end_re"], html[start:])
    end = start + cm.start() if cm else html.rfind("</body>")
    body = html[start:end]
    body = re.sub(r'<a name="[^"]*"></a>', "", body)
    body = re.sub(r"<img\b[^>]*>", lambda m: img_md(m, page_dir, up), body)
    out = []
    pos = 0
    block_re = re.compile(r"<(h[1-4]|pre|p|li|dt|dd)([^>]*)>(.*?)</\1>", re.S)
    def emit_gap(gap):
        t = inline(gap)
        if t:
            out.append(t)
    for mm in block_re.finditer(body):
        if mm.start() > pos:
            emit_gap(body[pos:mm.start()])
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
        elif tag == "p":
            t = inline(inner)
            if t:
                out.append(t)
        elif tag in ("li",):
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
        emit_gap(body[pos:])
    md = re.sub(r"\n{3,}", "\n\n", "\n".join(out))
    return md.strip()

def postprocess(text, url2md):
    """后处理: 截断标记 / 删行关键词 / 评论模板尾巴(${}) / 站内链接重写 / 导航纯链接"""
    for marker in SITE.get("truncate_at", []):
        i = text.find(marker)
        if i >= 0:
            cut = text.rfind("\n", 0, i)
            text = text[: cut if cut > 0 else i]
            break
    lines = []
    for ln in text.split("\n"):
        if any(k in ln for k in SITE.get("drop_lines_with", [])):
            continue
        i = ln.find("${")
        if i >= 0:
            ln = ln[:i].rstrip()
        lines.append(ln)
    def rewrite(m):
        text2, href = m.group(1), m.group(2)   # ①文字 ②URL!
        clean = href.lstrip("./")
        for u, fname in url2md.items():
            if clean == u.strip("/") or clean.endswith(u.strip("/")) or u.strip("/").endswith(clean):
                return "[%s](%s)" % (text2, fname)
        return m.group(0)
    if SITE.get("link_rewrite"):
        pat = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
        lines = [pat.sub(rewrite, ln) for ln in lines]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"
    if SITE.get("strip_nav_links"):
        pure = re.compile(r"^\[[^\]]*\]\([^)]*\)$")
        ls = [l for l in text.split("\n")]
        while ls and pure.match(ls[-1].strip()):
            ls.pop()
        while ls and pure.match(ls[0].strip()):
            ls.pop(0)
        text = "\n".join(ls).strip() + "\n"
    return text

def main():
    global IMG_MAP_FILE
    s = SITE
    IMG_MAP_FILE = os.path.join(os.path.dirname(s["out"]) + "/", "img_map.json")
    IMG_MAP_FILE = os.path.join(os.path.dirname(s["out"]), "img_map.json")
    cfg = load_upload_cfg(os.path.expanduser("~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json"))
    up = {"cfg": cfg, "user_id": "25689388"} if cfg else None
    print("图片 CDN 上传:", "启用" if up else "未启用", flush=True)
    os.makedirs(s["out"], exist_ok=True)
    url2md = {}
    for fname, rel in s["pages"]:
        url2md[rel] = fname
        url2md[s["base"] + "/" + rel] = fname
    for fname, path in s["pages"]:
        page_dir = s["base"] + "/" + path.rsplit("/", 1)[0]
        try:
            html = fetch(s["base"] + "/" + path).decode("utf-8", "ignore")
            md = html_to_md(html, page_dir, up)
            md = postprocess(md, url2md)
            with open(os.path.join(s["out"], fname), "w", encoding="utf-8") as f:
                f.write(md + "\n")
            print(f"{fname}: {len(md)} chars", flush=True)
        except Exception as e:
            print(f"ERR {path}: {e}", flush=True)
        time.sleep(0.5)

if __name__ == "__main__":
    main()
