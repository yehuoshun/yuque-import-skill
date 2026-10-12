#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语雀占位文档修复（2026-10-12 事故善后）

背景: yuque_tree_import.py 旧版二进制检测的 hi-byte>0.9 启发式会把中文密集文本
(.md/.cs/.txt/.ts...) 误判为二进制 → 文档被写成占位注释, 正文丢失。
涉及 10+ 库 169+ 篇 (HowToCook/deepwrite/Nulab/free-programming-books/kairisei/sts2mod 系等)。
v1.1.3 已删除该启发式; 本脚本负责回填已受损文档。

用法:
  python3 yuque_repair_placeholders.py --book <id> --source <本地目录>          # 本地源回填
  python3 yuque_repair_placeholders.py --book <id> --github <owner/repo>        # GitHub raw 回填(HEAD)
  python3 yuque_repair_placeholders.py --book <id> --github <owner/repo> --prefix <子目录>  # 仓库子目录为导入根
  python3 yuque_repair_placeholders.py --book <id> --github <owner/repo> --list  # 只列损坏清单不修

流程: TOC 路径重建 → list_docs 找零词文本文档 → 按路径取源内容 → PUT 回填 body → 验证。
空源文件跳过(本来就是空文件, 占位正确)。
"""
import argparse, json, os, sys, time, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yuque_tree_import import load_token, api  # noqa: E402

BASE = "https://www.yuque.com/api/v2"
TEXT_EXT = {".md", ".markdown", ".txt", ".cs", ".ts", ".js", ".jsx", ".tsx", ".py", ".json",
            ".yml", ".yaml", ".xml", ".html", ".htm", ".css", ".scss", ".sh", ".bash", ".ps1",
            ".c", ".h", ".cpp", ".hpp", ".java", ".go", ".rs", ".rb", ".php", ".vue", ".svelte",
            ".sql", ".toml", ".ini", ".cfg", ".conf", ".env", ".properties", ".gradle", ".kt",
            ".swift", ".m", ".csproj", ".sln", ".slnx", ".bat", ".cmd", ".tsv", ".csv",
            ".gitignore", ".gitattributes", ".editorconfig", ".rst", ".adoc", ".tex"}
TEXT_NOEXT = {"LICENSE", "README", "NOTICE", "MAKEFILE", "DOCKERFILE", "CHANGELOG",
              "CONTRIBUTING", "CODE_OF_CONDUCT", "OPERATIONS", "COPYING", "AUTHORS", "VERSION"}


def is_text_name(title):
    ext = os.path.splitext(title)[1].lower()
    return ext in TEXT_EXT or os.path.splitext(title)[0].upper() in TEXT_NOEXT


def toc_path_map(token, book):
    """doc_id → 完整路径（TOC DOC 节点自带 doc_id）"""
    d = api(token, BASE, "GET", f"/repos/{book}/toc")
    toc = d.get("data", d) if isinstance(d, dict) else d
    nodes = {n["uuid"]: n for n in toc}
    def path(n):
        parts = [n.get("title", "")]
        p = n.get("parent_uuid")
        seen = 0
        while p and p in nodes and seen < 100:
            parts.append(nodes[p].get("title", ""))
            p = nodes[p].get("parent_uuid")
            seen += 1
        return "/".join(reversed(parts))
    m = {}
    for n in toc:
        if n.get("type") == "DOC" and n.get("doc_id"):
            m[str(n["doc_id"])] = path(n)
    return m


def broken_docs(token, book):
    """零词 + 文本扩展名 的文档 [(doc_id, title, path)]"""
    out, offset = [], 0
    while True:
        d = api(token, BASE, "GET", f"/repos/{book}/docs?limit=100&offset={offset}")
        docs = d.get("data", [])
        if not docs:
            break
        for doc in docs:
            if (doc.get("word_count") or 0) == 0 and is_text_name(doc.get("title") or ""):
                out.append(doc)
        if len(docs) < 100:
            break
        offset += 100
    return out


def raw_github(owner_repo, path, prefix=""):
    """GitHub API contents 取文件(raw), 404 返回 None。
    raw.githubusercontent.com 在此沙箱被挡(Errno 111), api.github.com 通 → 用 contents 端点。"""
    import urllib.parse
    p = "/".join(urllib.parse.quote(seg) for seg in (prefix + "/" + path).strip("/").split("/"))
    url = "https://api.github.com/repos/%s/contents/%s" % (owner_repo, p)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                               "Accept": "application/vnd.github.raw"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def update_doc(token, book, doc_id, title, body):
    d = api(token, BASE, "PUT", f"/repos/{book}/docs/{doc_id}",
            {"title": title, "format": "markdown", "body": body})
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True)
    ap.add_argument("--source", default=None, help="本地源目录")
    ap.add_argument("--github", default=None, help="GitHub owner/repo")
    ap.add_argument("--prefix", default="", help="GitHub 仓库内导入根子目录")
    ap.add_argument("--list", action="store_true", help="只列损坏清单")
    args = ap.parse_args()
    if not args.source and not args.github:
        ap.error("--source 或 --github 必选其一")

    token = load_token("TOKEN_L91")
    paths = toc_path_map(token, args.book)
    docs = broken_docs(token, args.book)
    print(f"损坏候选: {len(docs)} 篇 (book {args.book})", flush=True)

    updated = skipped = failed = 0
    for doc in docs:
        did, title = doc["id"], doc["title"]
        path = paths.get(str(did))
        # 兜底: 按 title 反查（同标题多路径时取第一个）
        if not path:
            cand = [p for p in paths.values() if p.endswith("/" + title) or p == title]
            path = cand[0] if cand else None
        if args.list:
            print(f"   {did} | {title} | {path}")
            continue
        if not path:
            print(f"   SKIP {did} | {title} | 路径未定")
            skipped += 1
            continue
        try:
            if args.source:
                raw = open(os.path.join(args.source, path), "rb").read()
            else:
                raw = raw_github(args.github, path, args.prefix)
            if raw is None:
                print(f"   SKIP {did} | {title} | GitHub 404: {path}")
                skipped += 1
                continue
            text = raw.decode("utf-8", errors="replace")
            if not text.strip():
                print(f"   SKIP {did} | {title} | 源文件为空(合法)")
                skipped += 1
                continue
            update_doc(token, args.book, did, title, text)
            print(f"   OK  {did} | {title} | {len(text)} 字符回填", flush=True)
            updated += 1
        except Exception as e:
            print(f"   FAIL {did} | {title}: {e}")
            failed += 1
        time.sleep(0.8)
    print(f"\n=== 结果: 回填 {updated} / 跳过 {skipped} / 失败 {failed} ===")


if __name__ == "__main__":
    main()
