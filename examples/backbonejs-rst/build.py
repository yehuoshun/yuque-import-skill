#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""#172 Backbone.js入门教程第二版（the5fire/backbonejs-learning-note @ 6d91478）
双轨：chapters/*.rst → md 正文 + code/ 源码树 + images/ 5 张 CDN + PDF 原件附件（预建文档+账本注入）。
"""
import json, os, re, shutil, subprocess, sys, time, urllib.request, uuid, mimetypes

SRC = "/home/admin/.openclaw/workspace/tmp/fpb172-src"
OUT = "/home/admin/.openclaw/workspace/tmp/fpb172-site"
SK = "/home/admin/.openclaw/workspace/code/yuque-import-skill/scripts"
PROG = "/home/admin/.openclaw/workspace/tmp/fpb172-progress.json"
BOOK = "85211950"
TOKEN = os.environ["TOKEN_L91"]
BASE = "https://www.yuque.com/api/v2"
COOKIE_CFG = "/home/admin/.openclaw/workspace/tmp/fpb-waylau/cookie.json"
USER_ID = "25689388"

def api(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, headers={"X-Auth-Token": TOKEN, "User-Agent": "fpb172-build"})
    if body is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(body).encode()
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and i < 3:
                time.sleep(min(10 * (2 ** i), 60)); continue
            raise RuntimeError("API %s %s -> %s %s" % (method, path, e.code, e.read()[:300]))

def make_doc(book, title, body):
    d = api("POST", "/repos/%s/docs" % book, {"title": title, "format": "markdown", "body": body})["data"]
    if not d.get("slug"):
        raise RuntimeError("POST /docs 未返回 slug: %s" % title)
    return d

def upload_attach(cookie, ctoken, path):
    ext = os.path.splitext(path)[1].lower()
    mime = mimetypes.types_map.get(ext, "application/pdf")
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

# ---------------------------------------------------------------- rst → md
UNDER = {"=": 1, "-": 2, "~": 3, "^": 4, '"': 5, "'": 5, "*": 3, "+": 3, "#": 4}

def convert_rst(text):
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        # 标题：下一行全同字符下划线
        if i + 1 < len(lines) and line.strip() and len(lines[i + 1]) >= 3 and set(lines[i + 1]) == {lines[i + 1][0]} and lines[i + 1][0] in UNDER:
            ch = lines[i + 1][0]
            lvl = UNDER[ch]
            out.append("#" * (lvl + 1) + " " + line.strip())
            i += 2
            continue
        # 指令
        m = re.match(r"^\.\. (code|image):: ?(.*)$", line)
        if m:
            kind, arg = m.group(1), m.group(2).strip()
            j = i + 1
            opts = {}
            while j < len(lines) and re.match(r"^   :", lines[j]):
                mo = re.match(r"^   :([^:]+): *(.*)$", lines[j])
                if mo:
                    opts[mo.group(1)] = mo.group(2)
                j += 1
            if kind == "code":
                code = []
                while j < len(lines) and (lines[j].startswith("    ") or lines[j].strip() == ""):
                    code.append(lines[j][4:] if lines[j].startswith("    ") else "")
                    j += 1
                while code and code[-1].strip() == "":
                    code.pop()
                out.append("```" + (arg or ""))
                out.extend(code)
                out.append("```")
                i = j
                continue
            else:  # image
                alt = opts.get("alt", "")
                out.append("![%s](%s)" % (alt, arg))
                i = j
                continue
        # 分隔线
        if re.match(r"^[-=~_*+#]{4,}$", line):
            out.append("---")
            i += 1
            continue
        # 行内转换
        out.append(inline(line))
        i += 1
    # 压缩多余空行
    txt = "\n".join(out)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip() + "\n"

def inline(s):
    # 1) 保护 ``字面量``
    lits = []
    def keep_lit(m):
        lits.append(m.group(1))
        return "\x00L%d\x00" % (len(lits) - 1)
    s = re.sub(r"``([^`]+)``", keep_lit, s)
    # 2) 链接 `text <url>`_
    def repl_link(m):
        text, url = m.group(1), m.group(2)
        if re.search(r"\.(rst|md)(#|$)", url) or url.startswith(("../", "./", "http://localhost")):
            return text  # 站内死链 → 纯文本
        return "[%s](%s)" % (text, url)
    s = re.sub(r"`([^`]+) <([^<>]+)>`_", repl_link, s)
    # 3) 恢复字面量（还原成单反引号？rst ``x`` = 等宽，md 用 `x`）
    def restore(m):
        return "`" + lits[int(m.group(1))] + "`"
    s = re.sub(r"\x00L(\d+)\x00", restore, s)
    return s

# ---------------------------------------------------------------- 组装
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT, exist_ok=True)

# 章映射：chapters 文件名 → NN-标题（标题取 README 目录 + 章内 H1 优先）
chap_map = {
    "00-preface.rst": "00-前言",
    "01-hello-backbonejs.rst": "01-Hello Backbonejs",
    "02-backbonejs-model.rst": "02-Backbonejs中的Model实践",
    "03-backbonejs-collection.rst": "03-Backbonejs中的Collections实践",
    "04-backbonejs-router.rst": "04-Backbonejs中的Router实践",
    "05-backbonejs-view.rst": "05-Backbonejs中的View实践",
    "06-backbonejs-todos-1.rst": "06-实战演练：todos分析（一）",
    "07-backbonejs-todos-2.rst": "07-实战演练：todos分析（二）View的应用",
    "08-backbonejs-todos-3.rst": "08-实战演练：todos分析（三）总结",
    "09-intro-webpy.rst": "09-后端环境搭建：web.py的使用",
    "10-expand-todos-with-server.rst": "10-实战演练：扩展todos到Server端（backbonejs+webpy）",
    "11-web-chatroom-base-on-backbonejs-1.rst": "11-前后端实战演练：Web聊天室-功能分析",
    "12-web-chatroom-base-on-backbonejs-2.rst": "12-前后端实战演练：Web聊天室-详细设计",
    "13-web-chatroom-base-on-backbonejs-3.rst": "13-前后端实战演练：Web聊天室-服务端开发",
    "14-web-chatroom-base-on-backbonejs-4.rst": "14-前后端实战演练：Web聊天室-前端开发",
    "15-import-requirejs.rst": "15-引入requirejs",
    "16-exception-in-backbone.rst": "16-补充异常处理",
    "17-customize-backbonejs-sync.rst": "17-定制Backbonejs",
    "18-backbone-summary.rst": "18-再次总结",
    "19-backbone-js-resource.rst": "19-Backbonejs相关资源",
}
# 剥章级 H1（= 下划线标题）——转换器里 lvl1 标题现为 H2（# # 前缀）
for src, name in chap_map.items():
    txt = open(f"{SRC}/chapters/{src}", encoding="utf-8").read()
    md = convert_rst(txt)
    # 剥首个 H2（章标题）
    md = re.sub(r"^## .*\n", "", md, count=1)
    # 章内站内链接（NN-xxx.rst）→ 已在 inline 转纯文本
    with open(f"{OUT}/{name}.md", "w", encoding="utf-8") as f:
        f.write(md)

# README → 00-说明（剥「目录」段）
readme = open(f"{SRC}/README.rst", encoding="utf-8").read()
readme = re.sub(r"目录\n-{10,}\n.*$", "", readme, flags=re.S)
readme_md = convert_rst(readme)
readme_md = re.sub(r"^## Backbone.js入门教程第二版\n", "", readme_md, count=1)
with open(f"{OUT}/00-说明.md", "w", encoding="utf-8") as f:
    f.write("> 来源：the5fire/backbonejs-learning-note @ 6d91478（GitHub） ｜ 作者：the5fire ｜ 正文 chapters/*.rst 转 md，另有 PDF 原件附件 ｜ 导入 2026-11-01\n\n" + readme_md)

# 反馈 + 国内网站附录
for src, name in [("反馈.rst", "90-反馈"), ("sites-baseon-backbonejs.rst", "90-国内哪些网站在用backbonejs")]:
    txt = open(f"{SRC}/{src}", encoding="utf-8").read()
    md = convert_rst(txt)
    md = re.sub(r"^## .*\n", "", md, count=1)
    with open(f"{OUT}/{name}.md", "w", encoding="utf-8") as f:
        f.write(md)

# code/ 整树硬链（剔空壳 webpy-todos）
shutil.copytree(f"{SRC}/code", f"{OUT}/code", ignore=shutil.ignore_patterns("webpy-todos", ".git"))
# images/：只拷被引用的 5 张
os.makedirs(f"{OUT}/images", exist_ok=True)
for img in ["login.png", "topics.png", "message.png", "wechat-arch.png", "donate-alipay.png"]:
    shutil.copy(f"{SRC}/images/{img}", f"{OUT}/images/{img}")

# 章内 ../images/ → images/（md 平铺到根后）
for f in os.listdir(OUT):
    if f.endswith(".md"):
        p = os.path.join(OUT, f)
        txt = open(p, encoding="utf-8").read()
        txt = txt.replace("../images/", "images/")
        open(p, "w", encoding="utf-8").write(txt)

# 统计
n_md = sum(1 for f in os.listdir(OUT) if f.endswith(".md"))
n_code = sum(len(fs) for _, _, fs in os.walk(f"{OUT}/code"))
print(f"[#172] 正文文档 {n_md} + code 源码 {n_code} 文件 + images 5 张")

# ---------------------------------------------------------------- PDF 附件双轨
cfg = json.load(open(COOKIE_CFG, encoding="utf-8"))
cookie, ctoken = cfg["cookie"], cfg["ctoken"]
pdf = f"{SRC}/backbonejs_第二版.pdf"
if os.path.exists(pdf):
    prog = {"nodes": {}}
    if os.path.exists(PROG):
        prog = json.load(open(PROG, encoding="utf-8"))
    rel = "backbonejs_第二版.pdf"
    if rel in prog["nodes"] and prog["nodes"][rel].get("doc_id"):
        print("[#172] 附件文档已存在，skip")
    else:
        url = upload_attach(cookie, ctoken, pdf)
        size = os.path.getsize(pdf)
        human = "%d KB" % round(size / 1024) if size < 1048576 else "%.1f MB" % (size / 1048576)
        body = ("PDF 原件（语雀附件，点下方链接下载）\n\n"
                "📎 [backbonejs_第二版.pdf（%s）](%s)\n\n"
                "<!-- 来源：the5fire/backbonejs-learning-note @ 6d91478 ｜ 原路径：/backbonejs_第二版.pdf -->\n" % (human, url))
        d = make_doc(BOOK, "backbonejs_第二版.pdf", body)
        prog["nodes"][rel] = {"type": "doc", "uuid": "", "doc_id": d["id"], "slug": d["slug"],
                              "segments": [{"title": "backbonejs_第二版.pdf", "slug": d["slug"], "doc_id": d["id"]}]}
        json.dump(prog, open(PROG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"[#172] PDF 附件上传 + 预建文档 {d['id']}（{human}）")
else:
    print("[#172] ⚠️ PDF 不存在：", pdf)
    sys.exit(1)
print("[#172] 完成。导入根:", OUT)