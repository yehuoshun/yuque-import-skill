# UNIX TOOLBOX 中文版 转换器（单页 XHTML → 23 篇，2026-10-18）

源：`http://cb.vu/unixtoolbox_zh_CN.xhtml`（Colin Barschel & Greco Shi，CC BY-SA；站点已标 archived 但**原站仍在线**）
> 老板给的是 archive.org 快照（`web.archive.org/web/20210812021003/...`）——沙箱访问 archive.org 超时 → 改用原站。

成品：库 id `84705524`「UNIX TOOLBOX 中文版（2026-10-18）」slug `unix-toolbox-zh-20261018`，
**24 节点**（`00-前言` + 23 章），分组「文章收集」，四查全绿。

## 站点特征

- 单页 XHTML（21 万字节），正文在 `div.main`；`div.title` / `div.abstract` 单独取，`div.menu`（目录）/`div.changestyle`/`div.footerfirst`/`div.footerlast`/`div.pb` 全丢
- ⚠️ 页面把**完整 XHTML 内嵌**在 `<div id="toolboxContent">` 里 → **bs4 二次解析失效**（`h1`/`pre` 全查不到，但 `decode_contents()` 里标签明明在；疑与嵌套 `<html>`/`<?xml?>`/DOCTYPE 有关）
  → 本转换器**纯正则顺序扫描块**：`<(h1|h2|h3|h4|pre|p|ul|table)…>(.*?)</\1>`
- 行内：`span.cmt`（注释）→ 保留文本；`span.fn/pp/keyword` → 反引号；`a.xrefp/xref`（内部锚点）→ 纯文本；外链 → markdown 链接
- `<pre>`（316 个命令块）原样进 ` ```bash ` 围栏
- 尾巴常有 XHTML 注释碎片（`end main -->`、孤立 `-->`、未闭合 `<div`）→ 截断 + 逐行清

## 拆分与命名

- 按 `h1` 切章（23 章）；文件名 `NN-<h1文本>.md`（洗 `/\\:*?"<>|`）
- `00-前言.md` = 书名 + 摘要 + 章节目录表 + 源地址

## 用法

`python3 crawl_unixtoolbox.py`（结果写到 `tmp/unixtoolbox-clean/`）；换站点需改 `URL`/`OUT` 与容器选择器。