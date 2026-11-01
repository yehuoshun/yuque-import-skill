# Electron 中文文档（wizardforcel GitBook 2.x 嵌套树版）

2026-11-01 fpb52 #177 实战。库 85212898 / slug `electron-doc-20261101`。

## 源

`https://wizardforcel.gitbooks.io/electron-doc/content/`（GitBook 2.x 静态站，io.js 时代中译）。

## 与 examples/wizardforcel-gitbook（平铺版）的区别

wizardforcel 老站**多数是扁平侧栏**（`ibm-j-cq` 等），本例 `electron-doc` 是**嵌套树**：
5 大组（常见问题/向导/教程/API文档/开发）+ API 文档下 4 个子组（自定义 DOM 元素/主进程模块/渲染进程模块/双进程模块），
组节点自带页面（通常是只有标题的空壳）。

- 组节点（有子 `ul`）→ **TITLE 目录**；组页正文为空壳 → **不建「00-本章导读」占位**（只有标题的组页没有可导内容）
- 叶子页 → `NN-标题.md`，**每层 ul 内独立编号**（顶层 01..、子组内重新 01..）
- 无图（全站 0 img）→ 不涉及 CDN

## 关键实现点

1. 编号：每个 `ul` 内 li 从 1 独立编号（与 summary 序一致），非页面项（外链/占位 li）不占编号
2. 剥编号前缀：`'2.1. 支持平台' → '支持平台'`（`^\s*\d+(\.\d+)*\s*\.?\s*`），标题里的 `` ` ``/`<`/`>` 洗掉
3. 文件名标题不重复：剥首个 H1（标题由文件名承担）
4. 组页 `page_to_md` 返回空 → 不建导读（`md.strip()` 判断）

## 坑（2026-11-01 实捶）

- **test 6 后不要删 progress.json 再全量重导**：test 建的 4-6 个 doc 会以旧 id 残留成幽灵（全量重建新 id）。
  test 之后直接全量（保留 progress）让 test 节点 skip 即可；若已删则必须清幽灵（DELETE + 回查 404）。
- GitBook 2.x 组页（`faq/faq.html` 等）`section.normal` 里只有 H1 标题，正文在侧栏目录里 → 不建占位节点是正确口径。

## 产物

- `build.py`：嵌套树解析 + 转换（本目录）
- 站点原始结构参考：`/tmp/fpb177-index.html`（2026-11-01 快照）
