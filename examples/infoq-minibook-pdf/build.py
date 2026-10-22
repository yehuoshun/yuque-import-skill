#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《硝烟中的Scrum和XP》(InfoQ 迷你书, 中文版) PDF → 语雀导入树（正文抽取阶段）。

用法:  python3 build.py extract      # 只抽正文到 clean/，打印摘要
      python3 build.py attach        # 上传 PDF 附件 + 预建 00-PDF 原件.md + 写账本
"""
import os, re, sys, json, mimetypes, uuid, time, urllib.request, urllib.error
import pymupdf

WS = "/home/admin/.openclaw/workspace"
SK = os.path.join(WS, "code/yuque-import-skill/scripts")
sys.path.insert(0, SK)
from yuque_tree_import import api, load_token  # noqa: E402

PDF = "/tmp/scrum-and-xp.pdf"
OUT = os.path.join(WS, "tmp/scrumxp/clean")
PROG = os.path.join(WS, "tmp/scrumxp/progress.json")
COOKIE_CFG = os.path.join(WS, "skills/yuque-ai-mcp/config/config.json")
USER_ID = "25689388"
BASE = "https://www.yuque.com/api/v2"
BOOK = 84860629            # 建库后填
PDF_MD = "00-PDF 原件.md"

# (文档名(不含扩展名), 起始页idx, 结束页idx)  1-indexed 页码 = idx+1
PAGES = [
    ("00-扉页与版权信息", 0, 3),
    ("01-译者序", 8, 8),
    ("02-致谢", 9, 9),
    ("03-序——Jeff Sutherland", 10, 11),
    ("04-序——Mike Cohn", 12, 13),
    ("05-前言——嘿，Scrum 成了！", 14, 14),
    ("06-简介", 15, 18),
    ("07-我们怎样编写产品backlog", 19, 22),
    ("08-我们怎样准备sprint计划", 23, 24),
    ("09-我们怎样制定sprint计划", 25, 56),
    ("10-我们怎样让别人了解我们的sprint", 57, 59),
    ("11-我们怎样编写sprint backlog", 60, 75),
    ("12-我们怎样进行每日例会", 76, 79),
    ("13-我们怎样进行sprint演示", 80, 82),
    ("14-我们怎样做sprint回顾", 83, 88),
    ("15-Sprint之间的休整时刻", 89, 91),
    ("16-怎样制定发布计划，处理固定价格的合同", 92, 97),
    ("17-我们怎样组合使用Scrum和XP", 98, 104),
    ("18-我们怎样做测试", 105, 115),
    ("19-我们怎样管理多个Scrum团队", 116, 139),
    ("20-我们怎样管理地理位置上分布的团队", 140, 143),
    ("21-Scrum master检查列表", 144, 145),
    ("22-额外的话", 146, 147),
    ("23-有关作者", 148, 149),
]

BULLET_FONTS = {"Wingdings-Regular", "SymbolMT", "CourierNewPSMT", "Marlett", "Webdings"}
BULLET_CHARS = set("•·‣▪◆●○◦\x83\xa8\x6f")
CJK = lambda ch: ("\u4e00" <= ch <= "\u9fff") or ("\u3000" <= ch <= "\u303f") or ("\uff00" <= ch <= "\uffef")


def _clean(s):
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)


def _join(a, b):
    if not a:
        return b
    if not b:
        return a
    if CJK(a[-1]) and CJK(b[0]):
        return a + b
    return a + " " + b


def page_lines(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        for l in b["lines"]:
            spans = [s for s in l["spans"] if s["text"].strip()]
            if not spans:
                continue
            txt = "".join(s["text"] for s in l["spans"])
            if not txt.strip():
                continue
            out.append({"x0": l["bbox"][0], "y0": l["bbox"][1], "y1": l["bbox"][3],
                        "size": max(s["size"] for s in spans),
                        "font": spans[0]["font"], "text": txt})
    out.sort(key=lambda x: (round(x["y0"], 1), x["x0"]))
    return out


def is_bullet(l):
    if l["font"] in BULLET_FONTS:
        t = l["text"].strip()
        if t in ("", "o") or (len(t) <= 2 and all(c in BULLET_CHARS for c in t)):
            return True
    return False


def extract(doc, s, e, title):
    title_norm = re.sub(r"[\s.]+", "", re.sub(r"^\d+-", "", title))
    rows = []
    for pno in range(s, e + 1):
        lines = [l for l in page_lines(doc[pno]) if l["y0"] > 70 and l["size"] <= 30]
        # 广告块：含 infoq.com 的行 + 其上最多 2 行 >=13.5pt 的文字
        ad_idx = set()
        for i, l in enumerate(lines):
            if re.search(r"infoq\.com|^https?://", l["text"], re.I):
                ad_idx.add(i)
                for j in range(i - 1, max(-1, i - 3), -1):
                    if lines[j]["size"] >= 13.5:
                        ad_idx.add(j)
                    else:
                        break
        lines = [l for i, l in enumerate(lines) if i not in ad_idx]
        # 按 y 聚类成 row
        i = 0
        while i < len(lines):
            cl = [lines[i]]
            j = i + 1
            while j < len(lines) and abs(lines[j]["y0"] - lines[i]["y0"]) <= 1.3:
                cl.append(lines[j]); j += 1
            cl.sort(key=lambda x: x["x0"])
            i = j
            size = max(x["size"] for x in cl)
            if is_bullet(cl[0]) and len(cl) > 1:
                lvl = 1 if cl[0]["x0"] < 95 else 2
                txt = ""
                for x in cl[1:]:
                    txt = _join(txt, re.sub(r"\s+", " ", _clean(x["text"])).strip())
                if txt:
                    rows.append({"kind": "li", "lvl": lvl, "text": txt, "size": size,
                                 "x0": cl[0]["x0"], "y0": cl[0]["y0"]})
                continue
            parts = [re.sub(r"\s+", " ", _clean(x["text"])).strip() for x in cl]
            parts = [p for p in parts if p]
            if not parts:
                continue
            gaps = [cl[k + 1]["x0"] - cl[k]["x0"] for k in range(len(cl) - 1)]
            if len(parts) >= 3 and gaps and max(gaps) > 28:
                txt = " | ".join(parts)
            else:
                txt = ""
                for p in parts:
                    txt = _join(txt, p)
            rows.append({"kind": "t", "text": txt, "size": size, "x0": cl[0]["x0"], "y0": cl[0]["y0"]})

    # 分类 + 去重标题
    AD_ROW = re.compile(r"中文站.*社区|infoq\.com|^https?://|trenches", re.I)
    out = []
    for r in rows:
        t = r["text"].strip()
        if not t:
            continue
        if AD_ROW.search(t):
            continue
        if r["size"] >= 15.0:
            if re.sub(r"[\s.]+", "", t) == title_norm:
                continue
            out.append({"kind": "h2", "text": t})
        elif r["size"] >= 13.0:
            out.append({"kind": "h3", "text": t})
        elif r["kind"] == "li":
            out.append({"kind": "li", "lvl": r["lvl"], "text": t,
                        "x0": r["x0"], "y0": r["y0"], "size": r["size"]})
        else:
            if re.fullmatch(r"[\dIVXivx.·・\-–—]{1,6}", t):
                continue
            out.append({"kind": "p", "text": t, "x0": r["x0"], "y0": r["y0"], "size": r["size"]})

    # 噪声块：连续 >=3 行「无中文、<=14 字、无句末标点」→ 图内标签，丢
    def noise(t):
        return (not any(CJK(c) for c in t)) and len(t) <= 14 and t[-1] not in "。！？；,.!?;：:”"
    cl2, k = [], 0
    while k < len(out):
        if out[k]["kind"] == "p" and noise(out[k]["text"]):
            m = k
            while m < len(out) and out[m]["kind"] == "p" and noise(out[m]["text"]):
                m += 1
            if m - k >= 3:
                k = m; continue
        cl2.append(out[k]); k += 1
    out = cl2

    # 段落合并
    merged = []
    for it in out:
        prev = merged[-1] if merged else None
        if (prev and it["kind"] == "p" and prev["kind"] in ("p", "li")
                and prev["text"][-1] not in "。！？；：）)”!?"
                and (prev["kind"] == "li" or abs(it["x0"] - prev.get("x0", 0)) < 12)
                and it["y0"] - prev.get("y1", 0) < 1.7 * (it["size"] + 3)):
            prev["text"] = _join(prev["text"], it["text"])
            prev["y1"] = it["y0"]
            continue
        it2 = dict(it); it2["y1"] = it.get("y0", 0)
        merged.append(it2)

    # 首行标题去重：与文档名“近似”则丢（去标点/空白后互含）
    norm = lambda x: re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", x)
    tn = norm(re.sub(r"^\d+-", "", title))
    for k, it in enumerate(merged):
        if it["kind"] in ("h2", "h3"):
            hn = norm(it["text"])
            if hn and (hn in tn or tn in hn or hn[:6] == tn[:6]) and len(hn) >= 3:
                merged.pop(k)
            break

    md = []
    for it in merged:
        if it["kind"] == "h2":
            md.append("\n## " + it["text"] + "\n")
        elif it["kind"] == "h3":
            md.append("\n### " + it["text"] + "\n")
        elif it["kind"] == "li":
            md.append(("  " if it["lvl"] == 2 else "") + "- " + it["text"])
        else:
            md.append(it["text"] + "\n")
    return _clean(re.sub(r"\n{3,}", "\n\n", "\n".join(md)).strip())


def do_extract():
    doc = pymupdf.open(PDF)
    os.makedirs(OUT, exist_ok=True)
    report = []
    for title, s, e in PAGES:
        txt = extract(doc, s, e, title)
        path = os.path.join(OUT, title + ".md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(txt)
        report.append((title, len(txt), txt.count("\n## "), txt.count("\n### "), txt.count("\n- ")))
    print(f"{'file':46} chars  ##  ###  bullets")
    for r in report:
        print(f"{r[0]:46} {r[1]:6} {r[2]:3} {r[3]:4} {r[4]:4}")
    print("nodes:", len(PAGES) + 1)


def load_cookie_cfg(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def upload_attach(cookie, ctoken, path):
    mime = mimetypes.types_map.get(os.path.splitext(path)[1].lower(), "application/octet-stream")
    with open(path, "rb") as f:
        data = f.read()
    boundary = "----YuqueImport" + uuid.uuid4().hex
    body = b"\r\n".join([
        ("--" + boundary).encode(),
        ('Content-Disposition: form-data; name="file"; filename="%s"' % os.path.basename(path)).encode(),
        ("Content-Type: %s" % mime).encode(), b"", data,
        ("--" + boundary + "--").encode()])
    url = ("https://www.yuque.com/api/upload/attach?attachable_type=User"
           "&attachable_id=%s&type=attachment&ctoken=%s" % (USER_ID, ctoken))
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)
    req.add_header("Cookie", cookie)
    req.add_header("Referer", "https://www.yuque.com/")
    req.add_header("Origin", "https://www.yuque.com")
    req.add_header("User-Agent", "Mozilla/5.0")
    for i in range(5):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.loads(r.read().decode())["data"]["url"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and i < 4:
                time.sleep(min(10 * 2 ** i, 120)); continue
            raise
    raise RuntimeError("upload failed")


def do_attach():
    book = BOOK
    assert book, "先在 build.py 里填 BOOK"
    pdfp = os.path.join(WS, "tmp/scrumxp/scrum-and-xp-chinese-version.pdf")
    if not os.path.exists(pdfp):
        import shutil
        shutil.copy(PDF, pdfp)
    cfg = load_cookie_cfg(COOKIE_CFG)
    url = upload_attach(cfg["cookie"], cfg["ctoken"], pdfp)
    print("[attach]", url)
    token = load_token("TOKEN_L91")
    body = "\n".join([
        "# 硝烟中的Scrum和XP（PDF 原件）", "",
        "- **书名**：硝烟中的Scrum和XP ——我们如何实施 Scrum",
        "- **作者**：Henrik Kniberg ｜ **译者**：李剑 ｜ **审校**：郑柯",
        "- **出品**：InfoQ 中文站（企业软件开发丛书），© 2008 C4Media Inc.",
        "- **页数**：150 ｜ **文件**：scrum-and-xp-chinese-version.pdf（2.97 MB）",
        "- **源站**：https://www.infoq.cn/minibook/scrum-xp-from-the-trenches",
        "- **PDF 来源**：InfoQ 官方公开合集 https://static001.geekbang.org/resource/ebook/100books/book100.zip 内 book100/scrum-and-xp-chinese-version.pdf",
        "- **md5**：e1e54cc71db570ada3dc8ce44c89e290", "",
        "📎 [scrum-and-xp-chinese-version.pdf（2.97 MB）](%s)" % url, "",
        "（正文见本库各章文档。）"])
    d = api(token, BASE, "POST", "/repos/%s/docs" % book,
            {"title": PDF_MD, "format": "markdown", "body": body})["data"]
    print("[attach] doc", d["id"], d["slug"])
    prog = {"nodes": {}}
    if os.path.exists(PROG):
        prog = json.load(open(PROG, encoding="utf-8"))
    prog.setdefault("nodes", {})[PDF_MD] = {
        "type": "doc", "uuid": "", "doc_id": d["id"], "slug": d["slug"],
        "segments": [{"title": PDF_MD, "slug": d["slug"], "doc_id": d["id"]}]}
    json.dump(prog, open(PROG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[attach] 账本已写", PROG)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "attach":
        do_attach()
    else:
        do_extract()