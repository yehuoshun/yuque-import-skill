#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""legado（aoaostar/legado）→ 语雀「解析单轨」构建（2026-10-21 口径，硬规则 12：**附件只给 PDF**）。

新口径 = 解析单轨：
  - **不建** `01-原版附件.md`、**不上传** `sources/*.json`（原「原版轨」已停用，代码已删；
    历史双轨产物留档在 git 历史与旧库 fd0ec7f9 / 0dde287 / 8b13d08 / 06b8162）
  - 结构 = `00-前言.md` + `02..07` 六篇分类索引 + `08-解析/`（README / index.html / sources/*.json.md）
  - 索引里的「原件」列改为**上游直链** https://legado.aoaostar.com/sources/<file>

产出（clean_dir）：
  00-前言.md
  02-书源.md ... 07-在线朗读引擎.md   ← 每分类一篇索引（含上游直链 / 一键导入）
  08-解析/                            ← README / index.html / sources/*.json 逐条解析

用法:
  python3 build.py            # 生成 clean_dir（只此一个模式）

路径可由环境变量覆盖（默认指向脚本所在示例的镜像）：
  LEGADO_ROOT   （默认 /home/admin/.openclaw/workspace/tmp）
  LEGADO_SRC    （默认 $LEGADO_ROOT/legado，即仓库镜像/干净副本，需含 README.md 与 sources/）
  LEGADO_OUT    （默认 $LEGADO_ROOT/legado-book）
  LEGADO_COMMIT （默认 5c0ee9e，写进前言/来源表）

不入库：`CNAME` / `sources/cache.lock` / `.github/`（站点与 CI 产物）。
"""
import json
import os
import re
import zipfile

ROOT = os.environ.get("LEGADO_ROOT", "/home/admin/.openclaw/workspace/tmp")
SRC = os.environ.get("LEGADO_SRC", os.path.join(ROOT, "legado"))          # 镜像干净副本
OUT = os.environ.get("LEGADO_OUT", os.path.join(ROOT, "legado-book"))     # clean_dir
COMMIT = os.environ.get("LEGADO_COMMIT", "5c0ee9e")
UPSTREAM = "https://legado.aoaostar.com/sources/"


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


# ---------------- 文档生成 ----------------
def gen_docs(cats):
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
                    "上游直链：%s" % UPSTREAM + fn,
                    "一键导入：`%s`" % e.get("import", ""),
                    "全局同步时间：%s" % synced]
            open(dst, "w", encoding="utf-8").write(parse_json_doc(p, fn, meta))

    # ---- 00-前言 ----
    total_files = len({fname_of(e) for c in cats for e in c["entries"]})
    lines = [
        "# 前言", "",
        "本库是「阅读」APP（legado）资源站（<https://legado.aoaostar.com>）的**解析存档**："
        "每个原始资源 JSON/ZIP 逐条转表，方便直接阅读检索；**原件不上传附件**（2026-10-21 口径：附件只给 PDF），"
        "需要原件请点条目里的**上游直链**下载。", "",
        "## 来源", "",
        "| 项 | 值 |", "|---|---|",
        "| 站点 | https://legado.aoaostar.com |",
        "| 仓库 | https://github.com/aoaostar/legado （默认分支 `release`） |",
        "| Commit | `%s` |" % COMMIT,
        "| 上游同步时间 | %s |" % synced,
        "| 整理人 | AOAOSTAR（Pluto） |",
        "| 资源规模 | %d 条资源 / %d 个原件文件 |" % (
            sum(len(c["entries"]) for c in cats), total_files), "",
        "## 库结构", "",
        "```",
        "00-前言.md            本文件",
        "02-书源.md            分类索引：7 条书源合集（含上游直链 / 一键导入）",
        "03-订阅源.md          分类索引：2 条订阅源",
        "04-净化规则.md        分类索引：1 条净化规则",
        "05-阅读排版.md        分类索引：1 套阅读排版",
        "06-主题.md            分类索引：4 套主题",
        "07-在线朗读引擎.md     分类索引：6 套在线朗读（TTS）",
        "08-解析/              解析正文（README / index.html / sources/*.json 逐条解析）",
        "```", "",
        "## 怎么用", "",
        "1. **看内容**：先看 `02..07` 的分类索引，再去 `08-解析/sources/` 下看逐条解析；",
        "2. **原件下载**：索引里的「原件」列给的是**上游直链** `legado.aoaostar.com/sources/<file>`，浏览器直接下载；",
        "3. **App 导入**：把 JSON 放进手机后用「阅读」APP 的「导入书源 → 本地导入」；或直接点条目里的 `legado://` 一键导入链接（需手机已装「阅读」APP）。", "",
        "「阅读」APP 下载：[官方 Release](https://github.com/gedoor/legado/releases)、[酷安](https://www.coolapk.com/apk/256030)。", "",
        "## 口径", "",
        "- 原件为上游仓库 `sources/` 原样文件，**不入库、不上传附件**（硬规则 12：附件只给 PDF）；索引「原件」列给**上游直链**；",
        "- 解析正文由原件 JSON 逐条转表（书源/TTS 列名称与网址，净化规则列正则；主题/排版列字段值）；",
        "- `CNAME` / `sources/cache.lock` / `.github/workflows/build.yml` 为站点与 CI 产物，未入库；",
        "- 上游每次同步都会重写 `README.md` / `index.html`，本库为 **%s 快照**。" % COMMIT, "",
    ]
    open(os.path.join(OUT, "00-前言.md"), "w", encoding="utf-8").write("\n".join(lines))

    # ---- 02..07 分类索引 ----
    for i, c in enumerate(cats, 2):
        L = ["# %s" % c["name"], "",
             "> 共 %d 条。原件下载见「原件」列（上游直链）；逐条解析见 `08-解析/sources/`。" % len(c["entries"]), "",
             "| # | 名称 | 条数 | 来源网站 | 上游更新时间 | 直链 | 一键导入 | 原件 |",
             "|---:|---|---:|---|---|---|---|---|"]
        for j, e in enumerate(c["entries"], 1):
            fn = fname_of(e)
            site = e.get("site", "")
            site = "[%s](%s)" % (re.sub(r'^https?://(www\.)?', '', site).split("/")[0], site) if site else "—"
            L.append("| %d | %s | %s | %s | %s | [直链](%s) | [导入](%s) | [下载](%s%s) |" % (
                j, esc(e["name"]), e.get("count", 0), site, esc((e.get("updated") or "")[:10]),
                e["url"], e.get("import", ""), UPSTREAM, fn))
        L.append("")
        open(os.path.join(OUT, "0%d-%s.md" % (i, c["name"])), "w", encoding="utf-8").write("\n".join(L))

    print("生成完成: %s" % OUT, flush=True)
    for dp, dns, fns in os.walk(OUT):
        for f in sorted(fns):
            p = os.path.join(dp, f)
            print("  %8d  %s" % (os.path.getsize(p), os.path.relpath(p, OUT)), flush=True)


if __name__ == "__main__":
    cats = parse_readme()
    print("分类 %d / 条目 %d" % (len(cats), sum(len(c["entries"]) for c in cats)), flush=True)
    gen_docs(cats)
