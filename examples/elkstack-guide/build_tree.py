#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ELKstack 中文指南（chenryn/ELKstack-guide-cn @ a30092e）→ 语雀导入干净目录树。

源形状：GitBook 源仓库。SUMMARY.md 存 4~5 层嵌套（中文标题 + 英文扁平磁盘路径）；
        4 个空链接纯分组节点（`[插件配置]()`）；4 个 SUMMARY 断链的目录首页 README
        （文件不存在）→ 落成 TITLE 目录、无文档。

命名规则（同级排序靠分隔符）：
  节点号 = 点分路径 "01" / "01.01" / "01.01.01"
  有子节点 → 目录 "<num>-<title>/"；节点链接存在 → 目录内落地页 "<num>-<title>.md"
  无子节点 → 文件 "<num>-<title>.md"
  ('-'(0x2D) < '.'(0x2E) < 数字/字母 → 落地页天然排在同级目录与子节点之前)
  根级 README.md → "00-前言.md"
  排除：SUMMARY.md / .gitignore / .DS_Store / cover.jpg

孤儿（未被 SUMMARY 引用但属书内容）：
  kibana/v5/README.md                → Kibana 5 组内 04.00
  kibana/difference.md               → 根级（Kibana 各版本的对比）
  elasticsearch/auth/searchguard.md  → 权限管理组内（追加）
  elasticsearch/monitor/marvel.md    → 监控方案组内（追加）
  kibana/v3/**                       → 顶级组「Kibana 3（旧版）」（镜像源目录，标题取 H1）

图片：本地图统一收进 OUT/_imgs/<源相对路径洗成 __>，md 引用改成到该处的相对路径；
      6 个 GitHub raw 外链预下载（gh-proxy）同路处理；其余外链原样保留。
      _imgs 由 yuque_rewrite_images.py 传 CDN 后删除。
"""
import os
import re
import shutil
import subprocess

SRC = "/home/admin/.openclaw/workspace/tmp/elkstack-src"
OUT = "/home/admin/.openclaw/workspace/tmp/elkstack-a30092e-clean"
IMG_DIR = "_imgs"
BAD = re.compile(r'[/\\:*?"<>|\r\n]')
SUM_RE = re.compile(r'^(\s*)\*\s+\[([^\]]*)\]\(([^)]*)\)\s*$')

GH_RAW = {
    "https://github.com/elastic/packetbeat-dashboards/raw/master/screenshots/Packetbeat-statistics.png":
        "https://gh-proxy.com/https://raw.githubusercontent.com/elastic/packetbeat-dashboards/master/screenshots/Packetbeat-statistics.png",
    "https://github.com/elastic/packetbeat-dashboards/raw/master/screenshots/MySql-performance.png":
        "https://gh-proxy.com/https://raw.githubusercontent.com/elastic/packetbeat-dashboards/master/screenshots/MySql-performance.png",
    "https://github.com/chenryn/kibana/raw/master/docs/chenryn_img/range-panel.jpg":
        "https://gh-proxy.com/https://raw.githubusercontent.com/chenryn/kibana/master/docs/chenryn_img/range-panel.jpg",
    "https://github.com/chenryn/kibana/raw/master/docs/chenryn_img/range-setting.jpg":
        "https://gh-proxy.com/https://raw.githubusercontent.com/chenryn/kibana/master/docs/chenryn_img/range-setting.jpg",
    "https://raw.githubusercontent.com/parvez/snapshot_for_kibana/master/screenshots/4.%20schedule.png":
        "https://gh-proxy.com/https://raw.githubusercontent.com/parvez/snapshot_for_kibana/master/screenshots/4.%20schedule.png",
    "https://raw.githubusercontent.com/magenx/Logstash/master/Kibana%203%20%20%20OSSEC%20MONITORING%20DASHBOARD.png":
        "https://gh-proxy.com/https://raw.githubusercontent.com/magenx/Logstash/master/Kibana%203%20%20%20OSSEC%20MONITORING%20DASHBOARD.png",
}

plan, used, missing_imgs = [], set(), []


def sanitize(t):
    t = BAD.sub("-", t).replace("\u00a0", " ")
    return re.sub(r"\s+", " ", t).strip()


def rewrite_images(text, src_md_dir, out_md_dir):
    def collect(source, src_key):
        name = re.sub(r'[/\\:*?"<>|]', "__", src_key)
        dst = os.path.join(OUT, IMG_DIR, name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(dst):
            if source.startswith("http"):
                r = subprocess.run(["curl", "-sSfL", "-m", "120", "-o", dst, source],
                                   capture_output=True)
                if r.returncode != 0 or os.path.getsize(dst) == 0:
                    missing_imgs.append((src_key, "download-fail"))
                    return None
            else:
                if not os.path.exists(source):
                    missing_imgs.append((src_key, "not-found"))
                    return None
                shutil.copyfile(source, dst)
        return os.path.relpath(dst, out_md_dir)

    def sub_md(m):
        bits = m.group(2).split(None, 1)
        src = bits[0]
        if src.startswith(("http://", "https://", "data:")):
            if src in GH_RAW:
                new = collect(GH_RAW[src], "ghraw__" + os.path.basename(src).replace("%20", "_"))
                if new:
                    return "%s%s%s" % (m.group(1), new, m.group(3))
            return m.group(0)
        new = collect(os.path.normpath(os.path.join(src_md_dir, src)), src)
        return m.group(0) if not new else "%s%s%s" % (m.group(1), new, m.group(3))

    def sub_html(m):
        src = m.group(3)
        if src.startswith(("http://", "https://", "data:")):
            if src in GH_RAW:
                new = collect(GH_RAW[src], "ghraw__" + os.path.basename(src).replace("%20", "_"))
                if new:
                    return "%s%s%s%s" % (m.group(1), m.group(2), new, m.group(4))
            return m.group(0)
        new = collect(os.path.normpath(os.path.join(src_md_dir, src)), src)
        return m.group(0) if not new else "%s%s%s%s" % (m.group(1), m.group(2), new, m.group(4))

    text = re.sub(r'(<img\b[^>]*?\bsrc=)(["\'])([^"\']+)(["\'])', sub_html, text)
    text = re.sub(r'(!\[[^\]]*\]\()([^)]+)(\))', sub_md, text)
    return text


def emit_doc(src_rel, out_dir, fname):
    src_abs = os.path.join(SRC, src_rel)
    body = rewrite_images(open(src_abs, encoding="utf-8").read(),
                          os.path.dirname(src_abs), out_dir)
    open(os.path.join(out_dir, fname), "w", encoding="utf-8").write(body)
    used.add(src_rel)
    plan.append(("DOC", os.path.relpath(os.path.join(out_dir, fname), OUT), src_rel))


def resolve(link):
    return link if link and os.path.isfile(os.path.join(SRC, link)) else None


def build(nodes, out_dir, prefix=""):
    for i, n in enumerate(nodes, 1):
        num = "%s%02d" % (prefix, i)
        title = sanitize(n["title"])
        base = "%s-%s" % (num, title)
        link = resolve(n["link"])
        if n.get("_k3"):
            d = os.path.join(out_dir, base)
            os.makedirs(d, exist_ok=True)
            plan.append(("TITLE", os.path.relpath(d, OUT), None))
            walk_k3(os.path.join(SRC, "kibana", "v3"), d, "")
            continue
        if n["subs"]:
            d = os.path.join(out_dir, base)
            os.makedirs(d, exist_ok=True)
            plan.append(("TITLE", os.path.relpath(d, OUT), None))
            if n.get("_extra_intro"):
                emit_doc(n["_extra_intro"], d, "%s.00-Kibana4（章节首页）.md" % num)
            if link:
                emit_doc(link, d, base + ".md")
            build(n["subs"], d, num + ".")
        elif link:
            emit_doc(link, out_dir, base + ".md")


K3_DIR_TITLE = {
    "advanced": "进阶",
    "auth": "认证与权限",
    "dashboard": "仪表板",
    "panels": "面板详解",
    "source-code-analysis": "源码解析",
}


def walk_k3(d, cur_out, prefix):
    rels = sorted(os.listdir(d))
    dirs = [x for x in rels if os.path.isdir(os.path.join(d, x)) and x != "img"]
    idx = 0
    for fn in [x for x in rels if x.endswith(".md")]:
        full = os.path.join(d, fn)
        if fn == "README.md":
            emit_doc(os.path.relpath(full, SRC), cur_out,
                     "%s-%s.md" % (prefix or "00", sanitize(first_h1(full) or "简介")))
        else:
            idx += 1
            emit_doc(os.path.relpath(full, SRC), cur_out,
                     "%s%02d-%s.md" % (prefix, idx, sanitize(first_h1(full) or fn[:-3])))
    for dn in dirs:
        idx += 1
        sub = os.path.join(cur_out, "%s%02d-%s" % (prefix, idx,
                                                   sanitize(K3_DIR_TITLE.get(dn, dn))))
        os.makedirs(sub, exist_ok=True)
        plan.append(("TITLE", os.path.relpath(sub, OUT), None))
        walk_k3(os.path.join(d, dn), sub, "%s%02d." % (prefix, idx))


def first_h1(path):
    for ln in open(path, encoding="utf-8", errors="replace"):
        if ln.startswith("# "):
            return ln[2:].strip()
    return None


def auto_extra(group_suffix, title, src_rel):
    """往某个分组目录里追加文档，编号 = 现有同级条目数+1"""
    gdir = None
    for p in plan:
        if p[0] == "TITLE" and p[1].endswith(group_suffix):
            gdir = p[1]
    assert gdir, group_suffix
    num = os.path.basename(gdir).split("-")[0]
    mx = 0
    for x in os.listdir(os.path.join(OUT, gdir)):
        m = re.match(r"^%s\.(\d+)" % re.escape(num), x)
        if m:
            mx = max(mx, int(m.group(1)))
    emit_doc(src_rel, os.path.join(OUT, gdir), "%s.%02d-%s.md" % (num, mx + 1, title))


def parse_summary():
    stack, roots = [], []
    for line in open(os.path.join(SRC, "SUMMARY.md"), encoding="utf-8"):
        m = SUM_RE.match(line.rstrip("\n"))
        if not m:
            continue
        depth = len(m.group(1)) // 3
        node = {"title": m.group(2).strip(), "link": m.group(3).strip(), "subs": []}
        while stack and stack[-1][0] >= depth:
            stack.pop()
        (stack[-1][1]["subs"] if stack else roots).append(node)
        stack.append((depth, node))
    return roots


# ---------------- main ----------------
if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

roots = parse_summary()
assert roots[0]["link"] == "README.md"
emit_doc("README.md", OUT, "00-前言.md")
roots = roots[1:]

for n in roots:
    if n["title"] == "Kibana 5":
        n["_extra_intro"] = "kibana/v5/README.md"

ki = next(i for i, n in enumerate(roots) if n["title"] == "Kibana 5")
roots.insert(ki + 1, {"title": "Kibana 3（旧版）", "link": "", "subs": [], "_k3": True})
roots.insert(ki + 2, {"title": "Kibana 各版本的对比", "link": "kibana/difference.md", "subs": []})

build(roots, OUT)

auto_extra("-权限管理", "Searchguard 的部署与权限策略配置（旧版）",
           "elasticsearch/auth/searchguard.md")
auto_extra("-监控方案", "marvel（旧版商业监控方案）", "elasticsearch/monitor/marvel.md")

# ---- 覆盖核对 ----
src_md = set()
for dp, _, fns in os.walk(SRC):
    if "/.git" in dp or dp.endswith("/.git"):
        continue
    for f in fns:
        if f.endswith(".md"):
            src_md.add(os.path.relpath(os.path.join(dp, f), SRC).replace("\\", "/"))
src_md.discard("SUMMARY.md")
print("TITLE %d / DOC %d / 合计 %d" % (sum(1 for p in plan if p[0] == "TITLE"),
                                       sum(1 for p in plan if p[0] == "DOC"), len(plan)))
print("源 md %d / 已用 %d" % (len(src_md), len(used)))
print("未用:", sorted(src_md - used))
print("凭空:", sorted(used - src_md))
print("图片问题:", missing_imgs)
print("收集图片 %d" % sum(len(f) for _, _, f in os.walk(os.path.join(OUT, IMG_DIR))))
print("--- 根级 ---")
for x in sorted(os.listdir(OUT)):
    if x != IMG_DIR:
        print("   ", x)