#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双轨构建器：仓库(书 PDF + 代码 + 课件) → 语雀导入树。

用法:  python3 build_lib.py ruc | fudan

产物:
  <out>/                 导入根（可直接喂 yuque_tree_import.py --toc-md）
  <progress>.json        账本（PDF / PPTX 已预建文档并记账，tree_import 会 skip）

之后:
  python3 ~/.openclaw/workspace/code/yuque-import-skill/scripts/yuque_tree_import.py \
     --root <out> --book <id> --progress <progress>.json --toc-md
"""
import os, sys, json, shutil, subprocess, time, mimetypes, uuid, urllib.request, urllib.error, re
import pymupdf

WS = "/home/admin/.openclaw/workspace"
SK = os.path.join(WS, "code/yuque-import-skill/scripts")
sys.path.insert(0, SK)
from yuque_tree_import import api, load_token  # noqa: E402

COOKIE_CFG = os.path.expanduser("~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json")
USER_ID = "25689388"
BASE = "https://www.yuque.com/api/v2"

# ---------------------------------------------------------------- 库配置
LIBS = {
    "ruc": dict(
        name="ruc",
        book=84818579,
        repo="https://github.com/LLMBook-zh/LLMBook-zh.github.io",
        commit="7be1a80",
        src=os.path.join(WS, "tmp/LLMBook-zh.github.io-7be1a80-clean"),
        out=os.path.join(WS, "tmp/llmbooks/ruc"),
        progress=os.path.join(WS, "tmp/llmbooks/ruc-progress.json"),
        # 文本白名单（相对路径；目录递归全收）
        keep=["README.md", "code"],
        # 目录改名（原目录 -> 导入树目录名），保证根级顺序
        rename={"code": "02-代码", "slides": "03-课件"},
        # 顺手删掉的（原树里不需要进库的）
        drop=["assets", "cover.jpg", "cover-re.jpg", "cover-re.png",
              "List.png", "LLMbook-re.png"],
        # 全书 PDF：src 相对路径 -> 根级 md 文件名（doc 标题）
        book_pdf=("LLMBook.pdf", "00-全书 PDF（原件）.md"),
        # 正文抽取
        extract=dict(pdf="LLMBook.pdf", chapter_level=2, part_level=1,
                     hdr_y1=50.0, ftr_y0=665.0, max_chapters=None),
    ),
    "fudan": dict(
        name="fudan",
        book=84818580,
        repo="https://github.com/intro-llm/intro-llm.github.io",
        commit="ba94fed",
        src=os.path.join(WS, "tmp/intro-llm.github.io-ba94fed-clean"),
        out=os.path.join(WS, "tmp/llmbooks/fudan"),
        progress=os.path.join(WS, "tmp/llmbooks/fudan-progress.json"),
        keep=["README.md", "code"],
        rename={"code": "02-代码", "slides": "03-课件", "chapter": "04-原件（全书 PDF）"},
        drop=["css", "js", "fonts", "images", "index.html", ".DS_Store", "favicon.ico"],
        book_pdf=None,
        extract=dict(pdf="chapter/LLM-TAP-v2.pdf", chapter_level=1, part_level=None,
                     hdr_y1=74.0, ftr_y0=10**9, max_chapters=None),
    ),
}


# ---------------------------------------------------------------- 语雀上传
def upload_attach(cookie, ctoken, path):
    """type=attachment，返回 url（PDF 走这个；2026-10-21 硬规则 12）。"""
    ext = os.path.splitext(path)[1].lower()
    mime = mimetypes.types_map.get(ext, "application/octet-stream")
    with open(path, "rb") as f:
        data = f.read()
    boundary = "----YuqueImport" + uuid.uuid4().hex
    body = b"\r\n".join([
        ("--" + boundary).encode(),
        ('Content-Disposition: form-data; name="file"; filename="%s"' % os.path.basename(path)).encode("utf-8"),
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
    last = None
    for i in range(5):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                d = json.loads(r.read().decode())
            return d.get("data", {}).get("url")
        except urllib.error.HTTPError as e:
            last = "HTTP %s %s" % (e.code, e.read()[:200])
            if e.code in (429, 500, 502, 503, 504) and i < 4:
                time.sleep(min(10 * (2 ** i), 120)); continue
            raise RuntimeError(last)
        except Exception as e:  # noqa
            last = repr(e)
            if i < 2:
                time.sleep(3); continue
            raise RuntimeError(last)
    raise RuntimeError(last)


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "%d %s" % (round(n), u)
        n /= 1024.0
    return "%.1f TB" % n


def make_doc(token, book, title, body):
    d = api(token, BASE, "POST", "/repos/%s/docs" % book,
            {"title": title, "format": "markdown", "body": body})["data"]
    if not d.get("slug"):
        raise RuntimeError("POST /docs 未返回 slug: %s" % title)
    return d


# ---------------------------------------------------------------- 正文抽取
CJK = lambda ch: ("\u4e00" <= ch <= "\u9fff") or ("\u3000" <= ch <= "\u303f") or ("\uff00" <= ch <= "\uffef")
BULLET = "•·‣▪◆●○◦"


def _clean(s):
    """★ 必做：剥 C0 控制符（含 NUL）—— PDF 公式/字体残渣会带 \x00\x01，
    导入器把 NUL 判成二进制→正文写占位（2026-10-21 fudan 第5/6章实捶）。
    保留 \t\n\r。"""
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
            spans = [s for s in l["spans"] if s["text"]]
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


def heading_map(doc, chapter_level):
    """outline -> {(page_idx, y0): (rel_level, title)}；只取比 chapter 更深的层级。"""
    hm = {}
    for e in doc.get_toc(simple=False):
        lvl, title, pg, dest = e[0], e[1], e[2], (e[3] if len(e) > 3 else None)
        if lvl <= chapter_level:
            continue
        y = dest.get("to").y if isinstance(dest, dict) and dest.get("to") else None
        if y is None:
            continue
        hm.setdefault(pg - 1, []).append((y, lvl - chapter_level, title))
    return hm


def chapters(doc, chapter_level, part_level):
    """outline -> [(part_title|None, chap_title, start_page_idx, start_y, end_page_idx, end_y)]"""
    toc = doc.get_toc(simple=False)
    ents = []
    for e in toc:
        lvl, title, pg, dest = e[0], e[1], e[2], (e[3] if len(e) > 3 else None)
        y = (dest.get("to").y if isinstance(dest, dict) and dest.get("to") else 0.0) or 0.0
        ents.append((lvl, re.sub(r"\s+", " ", title).strip(), pg - 1, y))
    chaps = [e for e in ents if e[0] == chapter_level]
    parts = {e[2]: e[1] for e in ents if part_level and e[0] == part_level}
    out = []
    for i, (lvl, title, pg, y) in enumerate(chaps):
        end_pg = chaps[i + 1][2] if i + 1 < len(chaps) else doc.page_count - 1
        # 部分标题：取该章之前最近的一个部分标题页
        part = None
        if part_level:
            for p in sorted([k for k in parts if k <= pg], reverse=True):
                part = parts[p]
                break
        out.append(dict(part=part, title=title, sp=pg, sy=y, ep=end_pg))
    return out


def extract_chapter(doc, ch, hbytext, cfg):
    body_size_c = {}
    pages = []
    for pno in range(ch["sp"], ch["ep"] + 1):
        page = doc[pno]
        lines = page_lines(page)
        lines = [l for l in lines if l["y1"] > cfg["hdr_y1"] - 2 and l["y0"] < cfg["ftr_y0"]]
        for l in lines:
            body_size_c[round(l["size"])] = body_size_c.get(round(l["size"]), 0) + 1
        pages.append((pno, lines))
    if not body_size_c:
        return []
    body_size = max(body_size_c, key=body_size_c.get)

    chtitle = re.sub(r"[\s.]+", "", ch["title"])
    out = []
    cur = None

    def flush():
        nonlocal cur
        if cur and cur["text"].strip():
            out.append(cur)
        cur = None

    for pno, lines in pages:
        for l in lines:
            # 页脚脚注/小字
            if l["size"] < body_size - 1.0 and l["y0"] > 0.75 * doc[pno].rect.height:
                continue
            txt = re.sub(r"\s+", " ", _clean(l["text"])).strip()
            if not txt:
                continue
            nt = re.sub(r"\s+", "", txt)
            # 章节标题在正文里重复出现一次 → 丢掉
            if re.sub(r"[\s.]+", "", txt) == chtitle:
                continue
            # 标题识别：正文行文本 == outline 标题（归一化后）
            hlv = hbytext.get(nt)
            if hlv and len(nt) >= 3:
                flush()
                out.append({"kind": "h", "level": hlv, "text": txt})
                continue
            if re.fullmatch(r"[\dIVXivx.·・\-–—]{1,6}", txt):   # 裸页码
                continue
            is_li = txt[:1] in BULLET or l["font"].lower().startswith("txsys")
            if is_li:
                txt = re.sub(r"^[%s]\s*" % re.escape(BULLET), "", txt)
            x0_base = 57.0
            newp = (cur is None or is_li or l["x0"] > x0_base + 6
                    or (l["y0"] - cur.get("_y1", 0) > 1.7 * (l["size"] + 3)))
            if is_li:
                flush(); cur = {"kind": "li", "text": txt, "_y1": l["y1"]}
            elif newp:
                flush(); cur = {"kind": "p", "text": txt, "_y1": l["y1"]}
            else:
                cur["text"] = _join(cur["text"], txt); cur["_y1"] = l["y1"]
    flush()

    # 后处理：干掉“图内孤立短标签”块（连续 >=3 行、无中文、<=14 字、无句末标点）
    def _noise(t):
        return (not any(CJK(c) for c in t)) and len(t) <= 14 and t[-1] not in "。！？；,.!?;：:"
    clean, i = [], 0
    while i < len(out):
        if out[i]["kind"] == "p" and _noise(out[i]["text"]):
            j = i
            while j < len(out) and out[j]["kind"] == "p" and _noise(out[j]["text"]):
                j += 1
            if j - i >= 3:
                i = j
                continue
        clean.append(out[i]); i += 1
    out = clean

    md = []
    for it in out:
        if it["kind"] == "h":
            md.append("\n" + "#" * min(2 + it["level"] - 1, 6) + " " + it["text"] + "\n")
        elif it["kind"] == "li":
            md.append("- " + it["text"])
        else:
            md.append(it["text"] + "\n")
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(md)).strip()
    return _clean(text)


def build_zhengwen(doc_path, out_dir, cfg):
    doc = pymupdf.open(doc_path)
    hm = heading_map(doc, cfg["chapter_level"])
    hbytext = {}
    for e in doc.get_toc(simple=False):
        if e[0] <= cfg["chapter_level"]:
            continue
        hbytext[re.sub(r"\s+", "", e[1])] = e[0] - cfg["chapter_level"]
    chs = chapters(doc, cfg["chapter_level"], cfg["part_level"])
    if cfg.get("max_chapters"):
        chs = chs[: cfg["max_chapters"]]
    made = []
    for i, ch in enumerate(chs, 1):
        title = ch["title"]
        if cfg["chapter_level"] == 1:
            m = re.match(r"^(\d+)\s+(.*)$", title)
            if m:
                title = "第%s章 %s" % (m.group(1), m.group(2))
        text = extract_chapter(doc, ch, hbytext, cfg)
        if not text:
            print("  [warn] 空章:", ch["title"]); continue
        sub = os.path.join(out_dir, "01-正文")
        if ch["part"]:
            sub = os.path.join(sub, ch["part"])
        os.makedirs(sub, exist_ok=True)
        fn = os.path.join(sub, "%02d-%s.md" % (i, re.sub(r'[/\\:]', "-", title)))
        with open(fn, "w", encoding="utf-8") as f:
            f.write("# %s\n\n%s\n" % (title, text))
        made.append((title, len(text)))
    return made


# ---------------------------------------------------------------- 主流程
def main():
    lib = LIBS[sys.argv[1]]
    src, out = lib["src"], lib["out"]
    cfg = json.load(open(COOKIE_CFG))
    cookie, ctoken = cfg["cookie"], cfg["ctoken"]
    token = load_token("TOKEN_L91")
    book = lib["book"]

    print("[build] 库=%s book=%s" % (lib["name"], book))
    # 1) 干净导入根：硬链接整树 → 删不需要的
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(["cp", "-al", src, out], check=True)
    for d in lib["drop"]:
        p = os.path.join(out, d)
        if os.path.isdir(p):
            shutil.rmtree(p)
        elif os.path.exists(p):
            os.remove(p)
    # 白名单外的一切删掉（保留 rename 里出现的目录 + book_pdf 所在目录）
    keepset = set(lib["keep"])
    for rn in lib["rename"]:
        keepset.add(rn)
    for name in list(os.listdir(out)):
        if name in keepset:
            continue
        p = os.path.join(out, name)
        if os.path.isdir(p):
            shutil.rmtree(p)
        else:
            os.remove(p)
    for old, new in lib["rename"].items():
        op = os.path.join(out, old)
        if os.path.isdir(op):
            os.rename(op, os.path.join(out, new))
    # 2) 正文抽取
    print("[build] 抽正文 …")
    made = build_zhengwen(os.path.join(src, lib["extract"]["pdf"]), out, lib["extract"])
    print("[build] 正文 %d 章, 共 %.0f KB" % (len(made), sum(n for _, n in made) / 1024))

    # 3) 附件 + 附件文档（PDF→附件；PPTX→未上传说明）
    prog = {"nodes": {}}
    if os.path.exists(lib["progress"]):
        prog = json.load(open(lib["progress"], encoding="utf-8"))
    attach_list = []
    # 3a. 根级全书 PDF（本体不进树，只留一个空占位 md，doc 标题=md 名）
    if lib["book_pdf"]:
        rel_src, md_name = lib["book_pdf"]
        with open(os.path.join(out, md_name), "w", encoding="utf-8") as f:
            f.write("")
        attach_list.append((os.path.join(src, rel_src), md_name))
    # 3b. 导入树里现存的 PDF / PPTX（rel 已是改名后的树内相对路径）
    for root, dirs, files in os.walk(out):
        dirs[:] = [d for d in dirs if d != ".git"]
        for fn in sorted(files):
            if os.path.splitext(fn)[1].lower() not in (".pdf", ".pptx"):
                continue
            p = os.path.join(root, fn)
            attach_list.append((p, os.path.relpath(p, out)))

    print("[build] 附件/课件文档 %d 个 …" % len(attach_list))
    rev = {v: k for k, v in lib["rename"].items()}

    def orig_rel(rel):
        parts = rel.split(os.sep)
        if parts[0] in rev:
            parts[0] = rev[parts[0]]
        return "/".join(parts)
    for path, rel in attach_list:
        if rel in prog["nodes"] and prog["nodes"][rel].get("doc_id"):
            print("   skip", rel); continue
        ext = os.path.splitext(path)[1].lower()
        title = os.path.basename(rel)
        if ext == ".pdf":
            url = upload_attach(cookie, ctoken, path)
            body = ("PDF 原件（语雀附件，点下方链接下载）\n\n"
                    "📎 [%s（%s）](%s)\n\n"
                    "<!-- 来源：%s @ %s ｜ 原路径：%s -->\n"
                    % (title, human(os.path.getsize(path)), url, lib["repo"],
                       lib["commit"], orig_rel(rel)))
        else:
            body = ("课件原件（PPTX）—— 按现行口径（附件只上传 PDF）**未上传语雀**，原件见 GitHub 仓库：\n\n"
                    "`%s/blob/main/%s`\n\n"
                    "<!-- 来源：%s ｜ 原路径：%s -->\n"
                    % (lib["repo"], orig_rel(rel), lib["repo"], orig_rel(rel)))
        d = make_doc(token, book, title, body)
        prog["nodes"][rel] = {"type": "doc", "uuid": "", "doc_id": d["id"],
                              "slug": d["slug"],
                              "segments": [{"title": title, "slug": d["slug"], "doc_id": d["id"]}]}
        json.dump(prog, open(lib["progress"], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("   +", rel, "->", d["id"])
    print("[build] 完成。导入树:", out)
    print("[build] 账本:", lib["progress"])
    print("[build] 下一步: python3 %s/yuque_tree_import.py --root %s --book %s --progress %s --toc-md"
          % (SK, out, book, lib["progress"]))


if __name__ == "__main__":
    main()