# **docsify 源仓库**（`docs/_sidebar.md` 全导航）→ 语雀（2026-10-28）

**首例**：`mingits/linux-c`（《Linux C 编程一站式学习》宋劲杉/北京亚嵌教育研究中心 @ c6e8593，GPL-3.0，65★）
→ 库 **85068530**（slug `linux-c-c6e8593`，分组「开源项目」待补），48 节点（3 目录 / 45 文档 = 3 篇导读 + 37 章 + 历史/前言/附录A·B/参考书目），144 图 CDN，六查全绿，根级 2 发 prependNode 归位。

## 什么时候用它

仓库 = **docsify 静态站源仓库**：`docs/` 下有 `_sidebar.md`（`- [标题](路由)`，路由**无扩展名**，子项缩进 2 空格）+ `index.html`（`window.$docsify = { loadSidebar: true, ... }`）+ `.nojekyll`。
有别于：
- `beej-zhcn`（老 GitBook 2.x：`SUMMARY.md` 带 `* ` 前缀 + 缩进 4 空格）
- `clang-tutorial`（Loppo：`loppo.yml` + `chapters.yml`）
- `wizardforcel-gitbook` / `gitbook-v2-md`（渲染站抓 HTML）

## 用法

```bash
python3 examples/linux-c-one-stop-learning/build.py   # 改脚本顶部 SRC/OUT
python3 scripts/yuque_rewrite_images.py <OUT> img_map.json --throttle 2
rm -rf <OUT>/imgs                                    # 硬规则 10（img_map.json 放 OUT 外）
python3 scripts/yuque_repo_import.py create-book --name "书名（<commit>）" --slug 书名-<commit> --desc "..."
python3 scripts/yuque_tree_import.py --root <OUT> --book <id> --progress <p> --toc-md
```

## 关键点

1. **认 `_sidebar.md`，不认目录名**：`[I. C 语言入门](1-C-语言入门/TOC)` 这种 `/TOC` 结尾 = **篇目录入口页**（TOC.md 是章节目录正文）→ 该路由建成 TITLE 目录 + 目录内 `00-<篇名>.md`（坑 72「目录自身有正文」同口径）；普通路由 `resolve()` 时补 `.md` 扩展名。
2. **根级 DOC 必落后于 TITLE（坑 29 常态）**：本次 5 个根级 DOC（历史/前言/附录A·B/参考书目）全被排到 3 个篇目录后 → **2 发 prependNode 收敛**（`01-历史`、`02-前言` 插到 `03-I.` 前；`06/07/08` 本来就在 03/04/05 后，自然落位）。每发后 GET /toc 回读校验（坑 98 铁律）。
3. **图在 `docs/images/`**：章节引用 `../images/x.png`、根文档引用 `images/x.png` → 统一正则 `!\[...\]\([^)]*?images/([^)]+)\)` 按文档深度重写到 `<OUT>/imgs/`（章节 `../imgs/`、根 `imgs/`）。
4. **教学示例假引用会被 rewrite 报「本地缺失」**：ch37 讲 HTTP 时正文里 ` <img src='mypic.jpg'>` 是**示例代码**不是真图 —— rewrite 会报 3 处缺失但**不会改写正文**，忽略即可（别去补图）。
5. **正文大量 docsify 路由交叉引用**（`](1-C-语言入门/ch01-程序的基本概念#_1-程序和编程语言)`，355 处）→ 保真不动（语雀里不可点，但正文语义完整）；`#  第 37 章` 双空格、`<p id="t1-1">表 1.1…` gitbook 遗留标签同样保真不洗。
6. **上游缺图**：gitbook 导出时漏了 `stdlib.buffer.png`（正文引用还在）→ 从同书其他镜像仓库捞（`light4/Linux-C` 有 `images/stdlib.buffer.png`，gh api contents base64 拉回），补进 `imgs/` 后重跑 rewrite 只补传 1 张。
7. 章节文件名自带 `chNN-` 前缀（`ch19-汇编与-C-之间的关系.md`），跨篇重名章（ch13/ch27 本阶段总结）靠路径隔离，无需改名。
