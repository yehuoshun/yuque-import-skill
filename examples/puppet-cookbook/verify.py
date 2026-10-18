#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Puppet 2.7 Cookbook 中文版 导入验收（四查 + 逐页正文比对 vs 老 gitbooks.io 静态站）。

为什么有 oracle 比对：本库源是 **AsciiDoc**（要自写转换器），比 md 源风险高——
路径对不代表正文没丢（SKILL 老坑）。老 gitbooks.io 静态站（= 同一份源码的官方渲染）
正好当**逐页文本 oracle**：站点页 ↔ 本地 md 按标题配对，归一化（去标记/标点/空白）后
逐页算相似度，低分页逐个打印差异上下文，人工过一眼。

用法：
  python3 verify.py <book_id> [--cache ./site-cache] [--thresh 0.99] [--fetch]

四查：① TOC 节点数 == 本地（除 _imgs） ② 全路径唯一 ③ 幽灵文档 0（TOC DOC 数 == /docs 数）
      ④ 根级顺序断言（toc-md 收尾后根级 DOC 会排到 TITLE 之后，须 prependNode 归位过）
"""
import argparse
import difflib
import html
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
from yuque_tree_import import load_token, api, walk  # noqa: E402

BASE = "https://www.yuque.com/api/v2"

ROOT = "/home/admin/.openclaw/workspace/tmp/puppet27-cookbook-cn-clean"
SITE = "https://wizardforcel.gitbooks.io/puppet-27-cookbook/content/"
EXPECT_ROOT = ["00-书名页.md", "01-中文翻译版.md", "02-译者序", "03-原书版权页.md",
               "04-关于作者.md", "05-前言", "06-Puppet 基础设施", "07-监控、报告和排错",
               "08-Puppet 语言及其写作风格", "09-书写更优质的配置清单", "10-使用文件和软件包",
               "11-用户和虚拟资源", "12-应用程序", "13-服务器和云基础设施",
               "14-外部工具和 Puppet 生态环境"]

LABELS = ("注", "提示", "重要", "警告", "小心")


def fetch(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return open(path, encoding="utf-8").read()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    txt = urllib.request.urlopen(req, timeout=45).read().decode("utf-8", "replace")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(txt)
    time.sleep(0.3)
    return txt


def site_sidebar(index_html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(index_html, "html.parser")
    ul = soup.find("nav").find("ul", class_="summary")
    out = []
    for li in ul.find_all("li", class_="chapter"):
        a = li.find("a")
        out.append((li.get("data-path"), a.get_text(" ", strip=True) if a else ""))
    return out


def site_text(path):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(open(path, encoding="utf-8").read(), "html.parser")
    sec = soup.find("section", class_="normal")
    return sec.get_text("\n", strip=True) if sec else ""


def norm(text):
    """归一化：只留字（字母/数字/汉字），去掉一切标记与标点空白。"""
    t = text
    t = re.sub(r"^\s*[`>]*\s*```.*$", "", t, flags=re.M)      # 围栏行
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", t)                # 图片
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)            # 链接→文字
    t = re.sub(r"^\s*(#+|[-*+]|\d+\.)\s+", "", t, flags=re.M)
    t = re.sub(r"^\s*>\s?", "", t, flags=re.M)
    t = re.sub(r"^\s*\*{0,2}(%s)\*{0,2}\s*（([^）]*)）\*{0,2}\s*$" % "|".join(LABELS), r"\2", t, flags=re.M)   # 标签带块标题 → 留标题
    t = re.sub(r"^\s*\*{0,2}(%s)\*{0,2}\s*$" % "|".join(LABELS), "", t, flags=re.M)
    t = re.sub(r"[`*_]", "", t)
    t = html.unescape(t)
    t = re.sub(r"^\d+", "", t)
    return "".join(ch for ch in t if ch.isalnum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("book_id")
    ap.add_argument("--cache", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "site-cache"))
    ap.add_argument("--thresh", type=float, default=0.99)
    ap.add_argument("--fetch", action="store_true", help="强制重抓站点页")
    ap.add_argument("--readback", action="store_true", help="逐篇回读语雀正文比对（慢，123 次 API）")
    args = ap.parse_args()
    if args.fetch:
        import shutil
        shutil.rmtree(args.cache, ignore_errors=True)

    idx = fetch(SITE + "index.html", os.path.join(args.cache, "index.html"))
    pages = site_sidebar(idx)

    # 站点标题 → 本地文件（标题去点号编号）
    def key(t):
        t = re.sub(r"^\s*[\d.]+\s*", "", t)
        return re.sub(r"\s+", "", t)

    local = {"Puppet2.7Cookbook中文版": [os.path.join(ROOT, "00-书名页.md")]}
    for p, isdir in walk(ROOT):
        if isdir or not p.endswith(".md"):
            continue
        b = os.path.basename(p)[:-3]
        b = re.sub(r"^[\d.]+-", "", b)
        local.setdefault(re.sub(r"\s+", "", b), []).append(p)

    print("站点页 %d / 本地 md %d" % (len(pages), sum(len(v) for v in local.values())))
    worst, miss, lag = [], [], []
    for path, title in pages:
        k = key(title) or "Puppet2.7Cookbook中文版"
        cand = local.get(k)
        if not cand:
            miss.append((path, title))
            continue
        f = cand[0]
        st = os.path.join(args.cache, os.path.basename(path))
        if not os.path.exists(st) and not (args.fetch):
            fetch(SITE + path, st)
        s_norm = norm(site_text(st))
        l_norm = norm(open(f, encoding="utf-8").read())
        r = difflib.SequenceMatcher(None, s_norm, l_norm).ratio()
        if r < args.thresh or len(s_norm) < 20:
            ops = [t for t, *_ in difflib.SequenceMatcher(None, s_norm, l_norm).get_opcodes()
                   if t != "equal"]
            # 站点渲染的旧版书稿可能比源仓库少内容（源仓库有后续修订）→ 只增不减 = 站点滞后，可接受
            (lag if set(ops) <= {"insert"} else worst).append(
                (r, path, title, f, s_norm, l_norm))
    print("按标题未配对的站点页: %d %s" % (len(miss), miss[:5]))
    print("站点滞后页（本地只多不少，可接受）: %d" % len(lag))
    for r, path, title, f, s, l in sorted(lag)[:4]:
        print("    %.4f  %s  %s（站点旧版少 %d 字）" % (r, path, title, len(l) - len(s)))
    print("低于阈值 %.3f 的真实差异页: %d" % (args.thresh, len(worst)))
    for r, path, title, f, s, l in sorted(worst)[:12]:
        print("\n--- %.4f  %s  %s\n    md: %s" % (r, path, title, f))
        sm = difflib.SequenceMatcher(None, s, l)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != "equal":
                print("    [%s] 站点=%r / 本地=%r" % (tag, s[max(0, i1 - 15):i2 + 15], l[max(0, j1 - 15):j2 + 15]))
    ok_content = (not miss) and (not worst)
    print("\n逐页正文比对: %d 页 ≥%.3f，%d 页站点滞后，%d 页真实差异 → %s"
          % (len(pages) - len(worst) - len(lag) - len(miss), args.thresh, len(lag), len(worst),
             "PASS ✅" if ok_content else "FAIL ❌"))

    # ---------------- 四查 ----------------
    tok = load_token("TOKEN_L91")
    toc = api(tok, BASE, "GET", "/repos/%s/toc" % args.book_id)["data"]
    docs, offset = [], 0
    while True:
        r = api(tok, BASE, "GET", "/repos/%s/docs?limit=100&offset=%d" % (args.book_id, offset))
        docs += r["data"]
        if len(docs) >= (r.get("meta", {}).get("total") or 0) or not r["data"]:
            break
        offset += 100
    kids = {}
    by_uuid = {}
    for n in toc:
        by_uuid[n["uuid"]] = n
    for n in toc:
        kids.setdefault(n.get("parent_uuid") or "", []).append(n)

    def pth(n):
        parts = []
        while True:
            parts.append(n["title"])
            pu = n.get("parent_uuid") or ""
            if not pu:
                break
            n = by_uuid[pu]
        return "/".join(reversed(parts))

    paths = [pth(n) for n in toc]
    local_paths = []
    for p, isdir in walk(ROOT):
        if isdir or not p.endswith(".md"):
            continue
        rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
        local_paths.append(rel)
    local_nodes = [p for p, _ in walk(ROOT) if os.path.basename(p) != "_imgs"
                   and "/_imgs/" not in p]
    toc_doc = [n for n in toc if n.get("type") == "DOC"]
    root_kids = [k["title"] for k in kids.get("", [])]

    print("\n==== 四查 ====")
    c1 = len(toc) == len(local_nodes)
    print("① 节点数: TOC %d / 本地 %d → %s" % (len(toc), len(local_nodes), "PASS ✅" if c1 else "FAIL ❌"))
    c2 = len(paths) == len(set(paths))
    print("② 全路径唯一: %d 条 / 去重 %d → %s" % (len(paths), len(set(paths)), "PASS ✅" if c2 else "FAIL ❌"))
    c3 = len(toc_doc) == len(docs)
    print("③ 幽灵文档: TOC DOC %d / /docs %d → %s" % (len(toc_doc), len(docs), "PASS ✅" if c3 else "FAIL ❌"))
    c4 = root_kids == EXPECT_ROOT
    print("④ 根级顺序 %s" % ("PASS ✅" if c4 else "FAIL ❌\n   实际: %s" % root_kids))

    # ⑤ 逐篇回读（语雀正文 vs 本地 md；路径对不代表正文没丢）
    c5 = True
    if args.readback:
        pathes = {pth(n): n for n in toc}
        bad = []
        for p, isdir in walk(ROOT):
            if isdir or not p.endswith(".md"):
                continue
            rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
            n = pathes.get(rel)
            if not n or not n.get("doc_id"):
                continue
            d = api(tok, BASE, "GET", "/repos/%s/docs/%s" % (args.book_id, n["doc_id"]))["data"]
            a, b = norm(d.get("body") or ""), norm(open(p, encoding="utf-8").read())
            r = difflib.SequenceMatcher(None, a, b).ratio()
            if r < 0.999:
                bad.append((round(r, 4), rel, len(a), len(b)))
            time.sleep(0.2)
        c5 = not bad
        print("⑤ 逐篇回读: 差异页 %d %s → %s"
              % (len(bad), bad[:5], "PASS ✅" if c5 else "FAIL ❌"))

    print("\nRESULT=%s" % ("PASS" if (ok_content and c1 and c2 and c3 and c4 and c5) else "FAIL"))


if __name__ == "__main__":
    main()
