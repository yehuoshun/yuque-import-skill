# 案例：Datawhale 南瓜书（pumpkin-book）→ 语雀（2026-10-22）

触发链接 `https://datawhalechina.github.io/pumpkin-book/` —— Datawhale 的《南瓜书》（周志华《机器学习》
「西瓜书」的公式详解）。站点是 **docsify**，源仓库 `datawhalechina/pumpkin-book`。

## 结论先行

| 项 | 值 |
|---|---|
| 库 | `南瓜书 PumpkinBook（20261022）` id=**84856649** slug=`pumpkin-book-20261022` |
| 分组 | 「文章收集」stack 36149506（网站口径） |
| 源 | `datawhalechina/pumpkin-book` master @ `58add39`（2026-01-21「从docsify迁移至vitepress」） |
| 节点 | **20** DOC（0 目录，全平铺） |
| 图 | 章内公式图全在 Datawhale 自家阿里云 OSS（SVG，**不动**）；仅 7 张 `raw.githubusercontent` 图传语雀 CDN |
| 验收 | TOC 20==本地 20、全路径唯一、对账 0 错位、幽灵 0、20 篇 word_count 全>0、CDN 图 7/7 200 |
| 耗时 | 建库~1min（含 move-stack 时序等待）+ 导入 ~40s + 验收 ~1min |

## 复现

```bash
git clone --depth 1 https://gh-proxy.com/https://github.com/datawhalechina/pumpkin-book.git src
SRC=$PWD/src CLEAN=/tmp/pumpkin-book-clean python3 build.py
python3 ../../scripts/yuque_rewrite_images.py /tmp/pumpkin-book-clean /tmp/pumpkin-book-imgmap.json --throttle 2
mv /tmp/pumpkin-book-clean/_img /tmp/pumpkin-book-img-hold   # ← 必须！硬规则 10
python3 ../../scripts/yuque_tree_import.py --root /tmp/pumpkin-book-clean --book <book_id> --progress <p> --toc-md
python3 ../../scripts/yuque_check_ghosts.py --book <book_id>
```

## 关键实现

### 1. 「站点 vs 仓库」——直接吃仓库 md，不用爬 HTML

站点还挂在**旧 docsify**（`loadSidebar` + `_sidebar.md`），而 master 已迁到 vitepress（`docs/` + `.vitepress/`）。
实测线上 `chapter1/chapter1.md` 与仓库 `docs/chapter1/chapter1.md` **逐字节相同（18349B）** → 站点没有独立内容，
爬 HTML 纯属浪费；直接吃仓库 `docs/`。这是 d2l 的「源仓库 md」取法，且**这次连 oracle 都不需要**（docsify 渲染
的就是同一份 md，不存在 Sphinx 那种「站上有编号、源里没有」的落差）。

### 2. 目录/命名口径（`build.py`）

```
00-前言.md                 ← 仓库根 README（HTML 清洗：div/h1/h2/img/a → md）
01-纸质版勘误表.md          ← docs/errata.md
02-第1章 绪论.md … 17-第16章 强化学习.md   ← docs/chapterN/chapterN.md
18-第1章 绪论（法文版）.md / 19-第2章 模型评估与选择（法文版）.md
```

- 章标题取自各章自己的 H1（第2章 H1 是「模型评估与选择」，vitepress 侧栏简写成「模型评估」→ **以正文为准**）
- 章节 1–11 正文以 `> [!IMPORTANT]` callout 开头、H1 在其后，所以剥 H1 要**扫全文第一个 `# xxx` 行**，
  不能只看首行（只看首行会漏掉这 11 篇的 H1）

### 3. 只动三处，正文一字不改

| 处理 | 原因 |
|---|---|
| `> [!IMPORTANT]` → `> **📌 本章学习须知**` | GitHub callout 语法语雀不认，会原样显示 `[!IMPORTANT]` |
| 去首个 H1 | 语雀文档标题=文件名，正文再顶一个 H1 是重复 |
| HTML 清洗（仅前言/法文版） | `<div align=center>`/`<center>`/`<h1>`/`<h2>`/`<img>`/`<a>` 语雀不渲染 |

### 4. 图片：只救 `raw.githubusercontent` 的 7 张

正文公式图（16 处引用，全是 SVG）挂在 **`datawhale-business.oss-cn-hangzhou.aliyuncs.com`**——Datawhale 自己的
阿里云 OSS，国内直连，**保持原样**（比转 CDN 更高保真，SVG 也不会被位图化）。
只有 7 张指到 `raw.githubusercontent.com`（前言 6 张 `res/*` + 法文版 `roc.png`），这些在境内常被墙 →
本地有原图（`res/`、`docs/chapter2/resources/images/`）→ 复制成 `_img/`、引用相对化、
`yuque_rewrite_images.py` 传 CDN、**导入前把 `_img/` 移出根目录**（硬规则 10）。

### 5. 仓库里没用的东西（没进库）

- `docs/chapter2/resources/`（roc.pdf/pptx）、`docs/chapter4/resources/`（4 个 pdf + pptx）：正文 md **一个都没引用**
  （chapter4 的「图4-1」直接引 OSS 上的 svg）→ 不入库（硬规则 12：附件只给 PDF，且这些非正文一部分）
- `docs/index.md`（vitepress home 版式 + `<script setup>` 团队卡片）、`docs/public/*.png`（站点 logo）、
  `.vitepress/`、`res/`（除上面 6 张被 README 引用的）、`package*.json`、`.github/` —— 全部不入库
