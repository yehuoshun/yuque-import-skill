#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nndl 系列 → 语雀导入根目录组装（含 PDF 原件附件，双轨）。

用法:  python3 build.py v2|ge|practice|llm-agent
产出:  <here>/<book>/import/  （喂 yuque_tree_import.py --toc-md）
"""
import json
import mimetypes
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
import uuid

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = "/home/admin/.openclaw/workspace/tmp"
COOKIE_CFG = os.path.expanduser("~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json")
USER_ID = "25689388"

BOOKS = {
    "v2": dict(clean=f"{HERE}/v2/clean", pdf=f"{TMP}/nndl-v2.pdf",
               pdf_name="神经网络与深度学习（第二版）.pdf",
               site="https://nndl.ai/nndl-v2/",
               title="神经网络与深度学习（第二版）",
               meta="邱锡鹏 著 · 机械工业出版社 · 2026 · 562 页 · 出版前电子稿"),
    "ge": dict(clean=f"{HERE}/ge/clean", pdf=f"{TMP}/nndl-ge.pdf",
               pdf_name="神经网络与深度学习（通识版）.pdf",
               site="https://nndl.ai/nndl-ge/",
               title="神经网络与深度学习（通识版）",
               meta="邱锡鹏 著 · 2026 · 360 页 · 出版前电子稿 · 16 章"),
    "practice": dict(clean=f"{HERE}/practice/clean", pdf=f"{TMP}/nndl-practice.pdf",
                     pdf_name="神经网络与深度学习：案例与实践（第二版）.pdf",
                     site="https://nndl.ai/nndl-practice/",
                     title="神经网络与深度学习：案例与实践（第二版）",
                     meta="邱锡鹏 著 · 机械工业出版社 · 2026 · 400 页 · 出版前电子稿"),
    "llm-agent": dict(clean=f"{HERE}/llm-agent/clean", pdf=f"{TMP}/llm-agent.pdf",
                      pdf_name="大模型与智能体.pdf",
                      site="https://nndl.ai/llm-agent/",
                      title="大模型与智能体：从基础原理到系统构建与未来展望",
                      meta="邱锡鹏 著 · 人民邮电出版社 · 2026 · 419 页 · 出版前电子稿"),
}


def upload_attach(cookie, ctoken, path, name):
    ext = os.path.splitext(path)[1].lower()
    mime = mimetypes.types_map.get(ext, "application/octet-stream")
    with open(path, "rb") as f:
        data = f.read()
    boundary = "----YuqueImport" + uuid.uuid4().hex
    body = b"\r\n".join([
        ("--" + boundary).encode(),
        ('Content-Disposition: form-data; name="file"; filename="%s"' % name).encode("utf-8"),
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
            with urllib.request.urlopen(req, timeout=900) as r:
                return json.loads(r.read().decode())["data"]["url"]
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


def main():
    b = BOOKS[sys.argv[1]]
    out = os.path.join(HERE, sys.argv[1], "import")
    if os.path.isdir(out):
        shutil.rmtree(out)
    shutil.copytree(b["clean"], out)
    cfg = json.load(open(COOKIE_CFG))
    size = os.path.getsize(b["pdf"])
    pages = pymupdf.open(b["pdf"]).page_count
    print("[build] %s 上传 PDF 原件 (%s) ..." % (sys.argv[1], human(size)), flush=True)
    url = upload_attach(cfg["cookie"], cfg["ctoken"], b["pdf"], b["pdf_name"])
    print("[build] 附件 url =", url, flush=True)
    body = (
        "# %s（PDF 原件）\n\n"
        "- **书名**：%s\n"
        "- **作者**：邱锡鹏\n"
        "- **版本**：%s\n"
        "- **页数**：%d 页（PDF %.1f MB）\n"
        "- **来源站**：%s\n"
        "- **整理**：由出版前电子稿 PDF 抽取逐章正文（图/公式为 PDF 文本层近似），原件见此附件\n\n"
        "📎 [%s（%s）](%s)\n"
    ) % (b["title"], b["title"], b["meta"], pages, size / 1048576.0, b["site"], b["pdf_name"], human(size), url)
    with open(os.path.join(out, "00-PDF 原件.md"), "w", encoding="utf-8") as f:
        f.write(body)
    print("[build] 导入根 =", out)


if __name__ == "__main__":
    main()