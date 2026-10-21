#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""legado（aoaostar/legado @ fd0ec7f9）→ 语雀「原版 + 解析」双轨构建。

⚠️ 2026-10-21 口径变更（硬规则 12：**附件只给 PDF**）：
   `upload` / `all` 模式**已停用**（默认拒绝执行；确需复现历史双轨才设 `LEGADO_ALLOW_ATTACH=1`）。
   新口径 = 解析单轨：只跑 `prep`，不传原件附件，索引里的「原件」列改给上游直链。
   本脚本保留作历史 3 版（fd0ec7f9 / 0dde287 / 8b13d08）的复现记录。

产出目录结构（clean_dir = tmp/legado-fd0ec7f9-book/）：
  00-前言.md
  01-原版附件.md              ← 原版轨（已停用）：21 条资源原件（20 独立文件）附件
  02-书源.md ... 07-在线朗读引擎.md   ← 解析轨索引（每分类一篇）
  08-解析/                    ← 解析轨正文（README / index.html / sources/*.md）

用法:
  python3 legado-fd0ec7f9-build.py prep      # 只生成解析正文 + 索引（无附件链接）
  python3 legado-fd0ec7f9-build.py upload    # 上传原件附件（断点续传 attach_map.json）
  python3 legado-fd0ec7f9-build.py all       # upload + 生成全部文档
"""
import json
import os
import re
import sys
import time
import zipfile
import mimetypes
import urllib.request
import urllib.error
import uuid

ROOT = "/home/admin/.openclaw/workspace/tmp"
SRC = os.path.join(ROOT, "legado")                       # 镜像（release @ fd0ec7f9）
OUT = os.path.join(ROOT, "legado-fd0ec7f9-book")         # clean_dir
ATTACH_MAP = os.path.join(ROOT, "legado-fd0ec7f9-attach.json")
USER_ID = "25689388"
COOKIE_CFG = "~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json"
COMMIT = "fd0ec7f9"
STACK = 57018723

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
from yuque_tree_import import load_upload_cfg  # noqa


# ---------------- README 解析 ----------------
def parse_readme():
    txt = open(os.path.join(SRC, "README.md"), encoding="utf-8").read()
    cats, cur = [], None
    for line in txt.splitlines():
        m = re.match(r'<h2 id="id_\d+">(.*?)</h2>', line.strip())
        if m:
            cur = {"name": m.group(1), "entries": []}
            cats.append(cur)
            continue
        s = line.strip()
        if cur is None:
            continue
        if s.startswith("* "):
            cur["entries"].append({"name": s[2:].strip()})
        elif s.startswith("+ ") and cur["entries"]:
            e = cur["entries"][-1]
            if "[访问直链](" in s:
                e["url"] = re.search(r'\]\(([^)]+)\)', s).group(1)
            elif "[一键导入](" in s:
                e["import"] = re.search(r'\]\(([^)]+)\)', s).group(1)
            elif "[访问网站](" in s:
                v = re.search(r'\]\(([^)]+)\)', s)
                e["site"] = v.group(1) if v else ""
            elif s.startswith("+ 上一次同步状态:"):
                e["status"] = s.split(":", 1)[1].strip()
                mm = re.search(r'共\s*(\d+)\s*条', e["status"])
                e["count"] = int(mm.group(1)) if mm else 0
            elif s.startswith("+ 更新时间:"):
                e["updated"] = s.split(":", 1)[1].strip()
            elif s.startswith("+ 同步时间:"):
                e["synced"] = s.split(":", 1)[1].strip()
    return cats


def fname_of(e):
    return os.path.basename(e["url"].split("?")[0])


def esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


# ---------------- 解析正文 ----------------
def parse_json_doc(path, name, meta_lines):
    """JSON 原件 → 可读 markdown 正文"""
    head = "# %s\n\n" % name + "".join("> %s\n" % l for l in meta_lines) + "\n"
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            inner = z.namelist()
            body = [head, "## 压缩包内容\n", "| 文件 | 大小 |", "|---|---|"]
            for n in inner:
                body.append("| %s | %d B |" % (n, z.getinfo(n).file_size))
            body.append("")
            for n in inner:
                if n.endswith(".json"):
                    d = json.loads(z.read(n).decode("utf-8"))
                    body.append("## %s\n" % n)
                    body.append("| 字段 | 值 |")
                    body.append("|---|---|")
                    for k, v in d.items():
                        body.append("| %s | %s |" % (esc(k), esc(v)))
                    body.append("")
        return "\n".join(body) + "\n"

    d = json.load(open(path, encoding="utf-8"))
    if isinstance(d, dict):
        body = [head, "| 字段 | 值 |", "|---|---|"]
        for k, v in d.items():
            body.append("| %s | %s |" % (esc(k), esc(v)))
        return "\n".join(body) + "\n"

    if not d:
        return head + "（空文件）\n"
    k0 = set(d[0].keys()) if isinstance(d[0], dict) else set()
    body = [head]
    if {"bookSourceName", "bookSourceUrl"} & k0:
        body += ["共 %d 条书源。\n" % len(d),
                 "| # | 名称 | 网址 | 分组 | 启用 |", "|---:|---|---|---|---|"]
        for i, it in enumerate(d, 1):
            body.append("| %d | %s | %s | %s | %s |" % (
                i, esc(it.get("bookSourceName", "")), esc(it.get("bookSourceUrl", "")),
                esc(it.get("bookSourceGroup", "") or "—"),
                "✅" if it.get("enabled") else "—"))
    elif {"sourceName", "sourceUrl"} & k0:
        body += ["共 %d 条订阅源。\n" % len(d),
                 "| # | 名称 | 网址 | 分组 | 启用 |", "|---:|---|---|---|---|"]
        for i, it in enumerate(d, 1):
            body.append("| %d | %s | %s | %s | %s |" % (
                i, esc(it.get("sourceName", "")), esc(it.get("sourceUrl", "")),
                esc(it.get("sourceGroup", "") or "—"),
                "✅" if it.get("enabled") else "—"))
    elif {"pattern", "replacement"} & k0:
        body += ["共 %d 条净化规则。\n" % len(d),
                 "| # | 名称 | 分组 | 启用 | 正则 |", "|---:|---|---|---|---|"]
        for i, it in enumerate(d, 1):
            pat = esc(it.get("pattern", ""))
            if len(pat) > 90:
                pat = pat[:90] + "…"
            body.append("| %d | %s | %s | %s | `%s` |" % (
                i, esc(it.get("name", "")), esc(it.get("group", "") or "—"),
                "✅" if it.get("isEnabled") else "—", pat))
    else:  # httpTTS / 其它 name+url 列表
        body += ["共 %d 条。\n" % len(d),
                 "| # | 名称 | 接口 URL |", "|---:|---|---|"]
        for i, it in enumerate(d, 1):
            body.append("| %d | %s | %s |" % (
                i, esc(it.get("name", "")), esc(it.get("url", ""))))
    return "\n".join(body) + "\n"


# ---------------- 资源原件上传 ----------------
def upload_attach(cookie, ctoken, path):
    ext = os.path.splitext(path)[1].lower()
    mime = mimetypes.types_map.get(ext, "application/octet-stream")
    boundary = "----YuqueImport" + uuid.uuid4().hex
    with open(path, "rb") as f:
        data = f.read()
    body = b"\r\n".join([
        ('--' + boundary).encode(),
        ('Content-Disposition: form-data; name="file"; filename="%s"' % os.path.basename(path)).encode(),
        ("Content-Type: %s" % mime).encode(), b"", data,
        ('--' + boundary + '--').encode()])
    url = ("https://www.yuque.com/api/upload/attach?attachable_type=User"
           "&attachable_id=%s&type=attachment&ctoken=%s" % (USER_ID, ctoken))
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)
    req.add_header("Cookie", cookie)
    req.add_header("Referer", "https://www.yuque.com/")
    req.add_header("Origin", "https://www.yuque.com")
    for i in range(6):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode()).get("data", {}).get("url") or None
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and i < 5:
                print("  [429/5xx] %s 等 %ds 重试" % (os.path.basename(path), 10 * (2 ** i)),
                      flush=True)
                time.sleep(min(10 * (2 ** i), 120))
                continue
            print("  [ERR] %s HTTP %s %s" % (os.path.basename(path), e.code,
                                             e.read().decode()[:160]), flush=True)
            return None
        except Exception as ex:
            print("  [ERR] %s %s" % (os.path.basename(path), ex), flush=True)
            if i < 2:
                time.sleep(5)
                continue
            return None
    return None


def do_upload(cats):
    cfg = load_upload_cfg(COOKIE_CFG)
    if not cfg:
        print("cookie 不可用", file=sys.stderr)
        sys.exit(1)
    mp = json.load(open(ATTACH_MAP, encoding="utf-8")) if os.path.exists(ATTACH_MAP) else {}
    print("已有缓存: %d" % len(mp), flush=True)
    for e in [x for c in cats for x in c["entries"]]:
        fn = fname_of(e)
        if fn in mp:
            continue
        p = os.path.join(SRC, "sources", fn)
        if not os.path.exists(p):
            print("  [缺文件] %s" % fn, flush=True)
            continue
        sz = os.path.getsize(p)
        print("上传 %s (%.1f MB)..." % (fn, sz / 1048576), flush=True)
        u = upload_attach(cfg["cookie"], cfg["ctoken"], p)
        if u:
            mp[fn] = u
            json.dump(mp, open(ATTACH_MAP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("  ✔ %s -> %s" % (fn, u[:80]), flush=True)
            time.sleep(5)
    print("附件完成: %d 个" % len(mp), flush=True)


# ---------------- 文档生成 ----------------
def gen_docs(cats):
    mp = json.load(open(ATTACH_MAP, encoding="utf-8")) if os.path.exists(ATTACH_MAP) else {}
    synced = next((e.get("synced", "") for c in cats for e in c["entries"] if e.get("synced")), "")
    os.makedirs(os.path.join(OUT, "08-解析", "sources"), exist_ok=True)

    # ---- 08-解析 正文 ----
    for fn in ("README.md", "index.html"):
        src = os.path.join(SRC, fn)
        if os.path.exists(src):
            open(os.path.join(OUT, "08-解析", fn), "w", encoding="utf-8").write(
                open(src, encoding="utf-8").read())
    for c in cats:
        for e in c["entries"]:
            fn = fname_of(e)
            p = os.path.join(SRC, "sources", fn)
            if not os.path.exists(p):
                continue
            dst = os.path.join(OUT, "08-解析", "sources", fn + ".md")
            if os.path.exists(dst):
                continue
            meta = ["分类：%s（%s 条）" % (c["name"], e.get("count", 0)),
                    "直链：%s" % e["url"],
                    "一键导入：`%s`" % e.get("import", ""),
                    "全局同步时间：%s" % synced]
            open(dst, "w", encoding="utf-8").write(parse_json_doc(p, fn, meta))

    # ---- 00-前言 ----
    total_files = len({fname_of(e) for c in cats for e in c["entries"]})
    lines = [
        "# 前言", "",
        "本库是「阅读」APP（legado）资源的**原版 + 解析双轨**存档：**解析正文**可读，**原件 JSON** 可下载后导入 App。", "",
        "## 来源", "",
        "| 项 | 值 |", "|---|---|",
        "| 站点 | https://legado.aoaostar.com |",
        "| 仓库 | https://github.com/aoaostar/legado （默认分支 `release`） |",
        "| Commit | `%s` （“Add sync changes”） |" % COMMIT,
        "| 上游同步时间 | %s |" % synced,
        "| 整理人 | AOAOSTAR（Pluto） |",
        "| 资源规模 | %d 条资源 / %d 个原件文件 |" % (
            sum(len(c["entries"]) for c in cats), total_files), "",
        "## 库结构", "",
        "```",
        "00-前言.md            本文件",
        "01-原版附件.md         原版轨：21 条资源的原件 JSON 附件（可直接下载）",
        "02-书源.md            解析轨索引：7 条书源合集",
        "03-订阅源.md          解析轨索引：2 条订阅源",
        "04-净化规则.md        解析轨索引：1 条净化规则",
        "05-阅读排版.md        解析轨索引：1 套阅读排版",
        "06-主题.md            解析轨索引：4 套主题",
        "07-在线朗读引擎.md     解析轨索引：6 套在线朗读（TTS）",
        "08-解析/              解析轨正文（README / index.html / sources/*.json 逐条解析）",
        "```", "",
        "## 怎么用", "",
        "1. **原件下载**：`01-原版附件.md` 里点 📎 下载原始 JSON；",
        "2. **App 导入**：把 JSON 放进手机后用「阅读」APP 的「导入书源 → 本地导入」；或直接点条目里的 `legado://` 一键导入链接（需手机已装「阅读」APP）；",
        "3. **看内容**：不想装 App 就先看 `08-解析/` 下的解析文档（逐条列出名称与网址）。", "",
        "「阅读」APP 下载：[官方 Release](https://github.com/gedoor/legado/releases)、[酷安](https://www.coolapk.com/apk/256030)。", "",
        "## 口径", "",
        "- 原件为上游仓库 `sources/` 原样文件，附件 URL 由语雀托管（会话门控：带登录态才可下载）；",
        "- 解析正文由原件 JSON 逐条转表（书源/TTS 列名称与网址，净化规则列正则）；",
        "- `CNAME` / `sources/cache.lock` / `.github/workflows/build.yml` 为站点与 CI 产物，未入库；",
        "- 上游每次同步都会重写 `README.md` / `index.html`，本库为 **%s 快照**。" % COMMIT, "",
    ]
    open(os.path.join(OUT, "00-前言.md"), "w", encoding="utf-8").write("\n".join(lines))

    # ---- 01-原版附件 ----
    L = ["# 原版附件（原件 JSON）", "",
         "> 上游 `sources/` 目录原样文件（%d 个独立文件 / %d 条资源引用），上传语雀托管，可直接下载后导入「阅读」APP。" % (
             len(mp), sum(len(c["entries"]) for c in cats)), "",
         "| 分类 | 名称 | 条数 | 原件 | 直链 | 一键导入 |",
         "|---|---|---:|---|---|---|"]
    for c in cats:
        for e in c["entries"]:
            fn = fname_of(e)
            u = mp.get(fn)
            p = os.path.join(SRC, "sources", fn)
            sz = os.path.getsize(p) if os.path.exists(p) else 0
            att = "[📎 %s](%s)" % (fn, u) if u else "（未上传）"
            if sz >= 1024 * 1024:
                att += " %.1fMB" % (sz / 1048576)
            imp = e.get("import", "")
            imp = "[legado://](%s)" % imp if imp else "—"
            L.append("| %s | %s | %s | %s | [直链](%s) | %s |" % (
                esc(c["name"]), esc(e["name"]), e.get("count", 0), att, e["url"], imp))
    L += ["", "> 注：上游 README 把「月下自酌」与「纵横不败」两条都指向同一个文件 `856adf0e.json`，故 %d 条引用 / %d 个文件。" % (
        sum(len(c["entries"]) for c in cats), len(mp)), ""]
    open(os.path.join(OUT, "01-原版附件.md"), "w", encoding="utf-8").write("\n".join(L))

    # ---- 02..07 分类索引 ----
    for i, c in enumerate(cats, 2):
        L = ["# %s" % c["name"], "",
             "> 共 %d 条。原件下载见 `01-原版附件.md`；逐条解析见 `08-解析/sources/`。" % len(c["entries"]), "",
             "| # | 名称 | 条数 | 来源网站 | 上游更新时间 | 直链 | 一键导入 | 原件 |",
             "|---:|---|---:|---|---|---|---|---|"]
        for j, e in enumerate(c["entries"], 1):
            fn = fname_of(e)
            u = mp.get(fn)
            att = "[📎](%s)" % u if u else "—"
            site = e.get("site", "")
            site = "[%s](%s)" % (re.sub(r'^https?://(www\.)?', '', site).split("/")[0], site) if site else "—"
            L.append("| %d | %s | %s | %s | %s | [直链](%s) | [导入](%s) | %s |" % (
                j, esc(e["name"]), e.get("count", 0), site, esc((e.get("updated") or "")[:10]),
                e["url"], e.get("import", ""), att))
        L.append("")
        open(os.path.join(OUT, "0%d-%s.md" % (i, c["name"])), "w", encoding="utf-8").write("\n".join(L))

    print("生成完成: %s" % OUT, flush=True)
    for dp, dns, fns in os.walk(OUT):
        for f in sorted(fns):
            p = os.path.join(dp, f)
            print("  %8d  %s" % (os.path.getsize(p), os.path.relpath(p, OUT)), flush=True)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("upload", "all") and os.environ.get("LEGADO_ALLOW_ATTACH") != "1":
        print("[停用] 2026-10-21 口径：附件只给 PDF（硬规则 12）——legado 原件不再上传附件；"
              "\n       新口径只跑 `prep`（解析单轨 + 索引给上游直链）。"
              "\n       复现历史双轨才设 LEGADO_ALLOW_ATTACH=1。", file=sys.stderr)
        sys.exit(2)
    cats = parse_readme()
    print("分类 %d / 条目 %d" % (len(cats), sum(len(c["entries"]) for c in cats)), flush=True)
    if mode in ("upload", "all"):
        do_upload(cats)
    if mode in ("prep", "all"):
        gen_docs(cats)