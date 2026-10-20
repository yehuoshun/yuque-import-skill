#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sketch 中文站「其余文档」→ 分章 markdown（Sketch 2 用户手册 + 15 篇技巧分享）。

源：Common Crawl 快照（站点已下线）
  sketch2 : CC-MAIN-2019-18 / 20190425144526
  技巧分享 : tips1 CC-MAIN-2019-18 / tips2·3 CC-MAIN-2019-13 / tips4 CC-MAIN-2019-22
            （每页含多篇，各篇带 月/日 徽标 → 按发布时间正序重排）
结构：正文窗口 = 导航之后 → <div class="verticalspacer"> 之前（Muse 站通用）
"""
import os, re, shutil, html as H

SKETCH2 = "cc2/sketch2-2019-18.html"
TIPS = ["cc2/tips1-2019-18.html", "cc2/tips2-2019-13.html",
        "cc2/tips3-2019-13.html", "cc2/tips4-2019-22.html"]
IMG_SRC_DIRS = ["i5ting-sketchcn/sketchcn.com/images", "i5ting-sketchcn/images"]
OUT = "clean2"

BLOCK = re.compile(
    r'<(h[1-4])\b[^>]*>(.*?)</\1>'
    r'|<p\b([^>]*)>(.*?)</p>'
    r'|(<img\b[^>]*?/?>)', re.S | re.I)
IMG_RE = re.compile(r'src="([^"]+)"')
DATE_RE = re.compile(r'id="u\d+-6">\s*<p>([A-Za-z]{3})</p>\s*<p>(\d+)</p>')
DATE_DIV_RE = re.compile(r'<div class="clearfix grpelem" id="u\d+-6">\s*<p>[A-Za-z]{3}</p>\s*<p>\d+</p>\s*</div>')
MON = {m: i for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
BULLET = ('・', '•', '·', 'Ø', 'ü', '–')
HEAD_MAX = 32


def content_window(raw, kind):
    if kind == "manual":
        hud = raw.rfind("<div", 0, raw.find("欢迎使用 Sketch 2"))
    else:
        hud = raw.rfind("<div", 0, raw.find("<h1"))
    e = raw.find('<div class="verticalspacer">', hud)
    assert e > 0, "no verticalspacer"
    w = raw[hud:e]
    w = re.sub(r'<(script|style)\b.*?</\1>', '', w, flags=re.S | re.I)
    w = re.sub(r'<!--.*?-->', '', w, flags=re.S)
    # 站内导航/翻页按钮（《技巧分享》底部 1/2/3/4 页码等）→ 整块剔掉
    w = re.sub(r'<a\b[^>]*href="(?:sketch-tips-tricks-\d+|sketch-chinese-user-manual|chinese-user-manual-for-sketch2|index)\.html"[^>]*>.*?</a>', '', w, flags=re.S)
    # <a><p>文本</p></a> 的按钮/链接 → 把 <a> 挪进 <p> 里，保住 URL
    w = re.sub(r'<a\b([^>]*)>\s*<p([^>]*)>(.*?)</p>\s*</a>', r'<p\2><a\1>\3</a></p>', w, flags=re.S)
    return w


def inline(s):
    s = re.sub(r'<a\b[^>]*?href="([^"]*)"[^>]*>(.*?)</a>', lambda m: (
        "[%s](%s)" % (re.sub(r'<[^>]+>', '', m.group(2)).strip(), m.group(1))
        if m.group(1).startswith("http") else re.sub(r'<[^>]+>', '', m.group(2)).strip()), s, flags=re.S)
    s = re.sub(r'<img\b[^>]*>', '', s)
    s = re.sub(r'<br\s*/?>', ' ', s, flags=re.I)
    s = re.sub(r'</?span\b[^>]*>', '', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = H.unescape(s).replace('\u00a0', ' ').replace('\u200b', '')
    return re.sub(r'[ \t]+', ' ', s).strip()


def is_subhead(t):
    """Muse 站的 h3 级小标题是普通 <p>：短、无句读 → 判为小标题"""
    if not t or len(t) > HEAD_MAX:
        return False
    if any(c in t for c in '。，！？：；、'):
        return False
    if '](' in t:                      # 链接/按钮，不是标题
        return False
    if re.match(r'^[0-9１-９][)）.、]', t):
        return False
    if t.startswith('http') or t[0] in BULLET:
        return False
    if t.endswith(('的', '了', '着', '是')):
        return False
    return True


def render_blocks(html_frag, out):
    n_before = len(out)
    for m in BLOCK.finditer(html_frag):
        if m.group(1):
            lvl, t = int(m.group(1)[1]), inline(m.group(2))
            if t:
                out += [("#" * lvl) + " " + t, ""]
        elif m.group(5):
            u = IMG_RE.search(m.group(5))
            if not u:
                continue
            u = u.group(1).replace('%40', '@')
            if u.startswith("images/"):
                out += ["![%s](%s)" % (os.path.basename(u), u), ""]
        else:
            attrs, body = m.group(3) or "", m.group(4)
            t = inline(body)
            if not t:
                continue
            if 'code' in attrs:
                out += ["```", H.unescape(re.sub(r'<[^>]+>', '', body)).strip(), "```", ""]
            elif t[0] in BULLET:                      # 项目符先判，否则短句会被误当标题
                out += ["- " + t[1:].strip(), ""]
            elif is_subhead(t):
                out += ["### " + t, ""]
            else:
                out += [t, ""]
    return out


def demote_head_runs(lines, n=3):
    """≥n 个连续标题（中间只有空行）= 图的说明标签，不是标题 → 降成普通行"""
    out, i = [], 0
    while i < len(lines):
        if lines[i].startswith('### '):
            j = i
            grp = []
            while j < len(lines) and (lines[j].startswith('### ') or lines[j] == ''):
                if lines[j]:
                    grp.append(j)
                j += 1
            if len(grp) >= n:
                for k in range(i, j):
                    out.append(lines[k][4:] if lines[k].startswith('### ') else lines[k])
            else:
                out.extend(lines[i:j])
            i = j
        else:
            out.append(lines[i])
            i += 1
    return out


def tidy(lines):
    b = "\n".join(demote_head_runs(list(lines)))
    b = re.sub(r'\n{3,}', '\n\n', b)
    b = re.sub(r'(?m)^(- .*)\n\n(?=- )', r'\1\n', b)
    return b.strip()


def split_sections(frag):
    """按 <h1> 切段 → [(h1文本, 片段html)]"""
    idx = [m.start() for m in re.finditer(r'<h1\b', frag)]
    secs = []
    for i, s in enumerate(idx):
        e = idx[i + 1] if i + 1 < len(idx) else len(frag)
        seg = frag[s:e]
        mm = re.match(r'<h1\b[^>]*>(.*?)</h1>', seg, re.S)
        t = re.sub(r'<[^>]+>', '', mm.group(1))
        secs.append((H.unescape(t).replace('\u00a0', ' ').strip(), seg[mm.end():]))
    return secs


def main():
    os.makedirs(OUT, exist_ok=True)
    imgdir = os.path.join(OUT, "images")
    os.makedirs(imgdir, exist_ok=True)

    # ---------- Sketch 2 手册 ----------
    raw2 = open(SKETCH2, encoding="utf-8").read()
    w2 = content_window(raw2, "manual")
    mch = [(t, tidy(render_blocks(seg, []))) for t, seg in split_sections(w2)]

    # ---------- 技巧分享 ----------
    tips = []
    for f in TIPS:
        raw = open(f, encoding="utf-8").read()
        w = content_window(raw, "tip")
        rawc = re.sub(r'<!--.*?-->', '', raw, flags=re.S)
        dates = [(MON[m.group(1)], int(m.group(2))) for m in DATE_RE.finditer(rawc)]
        w2b = DATE_DIV_RE.sub('', w)                       # 去掉日期徽标块
        secs = split_sections(w2b)
        assert len(dates) == len(secs), "%s 日期 %d != 篇数 %d" % (f, len(dates), len(secs))
        for (d, (t, seg)) in zip(dates, secs):
            tips.append({"date": d, "title": t, "src": f, "lines": render_blocks(seg, [])})
    tips.sort(key=lambda x: x["date"])
    print("[tip] %d 篇：%s" % (len(tips), " / ".join(
        "%02d-%02d %s" % (t["date"][0], t["date"][1], t["title"]) for t in tips)))

    # ---------- 图片 ----------
    refs = []
    for _, seg in split_sections(w2):
        for u in IMG_RE.findall(seg):
            u = u.replace('%40', '@')
            if u.startswith("images/") and u not in refs:
                refs.append(u)
    for t in tips:                                   # tips 已是 markdown，用 md 图引用正则
        for u in re.findall(r'!\[[^\]]*\]\((images/[^)\s]+)', "\n".join(t["lines"])):
            u = u.replace('%40', '@')
            if u not in refs:
                refs.append(u)
    keep, miss = set(), []
    for u in refs:
        name = os.path.basename(u)
        for d in IMG_SRC_DIRS:
            if os.path.exists(os.path.join(d, name)):
                shutil.copy2(os.path.join(d, name), os.path.join(imgdir, name))
                keep.add(u)
                break
        else:
            miss.append(u)
    print("[img] 引用 %d 张 → 落地 %d；缺 %d %s" % (len(refs), len(keep), len(miss), miss))

    # ---------- 写盘 ----------
    root = ["# Sketch 中文站 · Sketch 2 用户手册与技巧分享", "",
            "原站 Sketch 2 手册开篇：「欢迎使用 Sketch 2 的用户手册，这个手册的内容同时适用于新手和熟练用户。",
            "如果你对于这个手册的内容有任何想法和疑问，请通过邮箱 mail@bohemiancoding.com 随时联系我们。我们会不断的完善本手册。」", "",
            "> 来源：http://sketchcn.com/ （`chinese-user-manual-for-sketch2.html` + `sketch-tips-tricks-1~4.html`）",
            "> 站点已下线（域名在售）：正文经 Common Crawl 快照恢复 —— Sketch 2 手册 CC-MAIN-2019-18；",
            "> 技巧分享 tips1 CC-MAIN-2019-18 / tips2·3 CC-MAIN-2019-13 / tips4 CC-MAIN-2019-22；配图取自同源镜像仓库 github.com/i5ting/sketchcn",
            "> 原站：Sketch 中文网 ©2014 SketchCN / Aegean K", "",
            "## 目录", "", "**1. Sketch 2 用户手册**（%d 章）" % len(mch), ""]
    for i, (t, _) in enumerate(mch, 1):
        root.append("%d. %s" % (i, t))
    root += ["", "**2. 技巧分享**（%d 篇，按发布时间正序，2014-03-09 ~ 2014-06-02）" % len(tips), ""]
    for i, t in enumerate(tips, 1):
        root.append("%d. %s（2014-%02d-%02d）" % (i, t["title"], t["date"][0], t["date"][1]))
    open(os.path.join(OUT, "00-前言.md"), "w", encoding="utf-8").write("\n".join(root) + "\n")

    d1 = os.path.join(OUT, "01-Sketch 2 用户手册")
    os.makedirs(d1, exist_ok=True)
    for i, (t, b) in enumerate(mch, 1):
        open(os.path.join(d1, "%02d-%s.md" % (i, t.replace('/', '／'))), "w",
             encoding="utf-8").write("# %s\n\n%s\n"
                                    % (t, b.replace("](images/", "](../images/")))
    d2 = os.path.join(OUT, "02-技巧分享")
    os.makedirs(d2, exist_ok=True)
    for i, t in enumerate(tips, 1):
        open(os.path.join(d2, "%02d-%s.md" % (i, t["title"].replace('/', '／'))), "w",
             encoding="utf-8").write("# %s\n\n> 发布于 2014-%02d-%02d\n\n%s\n"
                                    % (t["title"], t["date"][0], t["date"][1],
                                       tidy(t["lines"]).replace("](images/", "](../images/")))
    n = 0
    for dp, dn, fn in os.walk(OUT):
        for f in sorted(fn):
            if f.endswith(".md"):
                n += 1
    print("[out] md 文件 %d 个（+ images/ %d 张）" % (n, len(os.listdir(imgdir))))


if __name__ == "__main__":
    main()