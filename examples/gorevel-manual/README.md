# examples/gorevel-manual — Revel 框架手册（gorevel.cn）

fpb52 #112 · 库 85155165 · 网站口径（原站已死） · 2026-10-31

`gorevel.cn` DNS 已死 **且域名被抢注成停放页**（2025 快照是 AV 广告页）→ 走 **Wayback 2019-06-10 快照**。
- 页面清单：CDX `url=gorevel.cn/docs/manual*`（24 页）；用 `web/<ts>id_/...` 取原始页。
- ⚠️ **runner fetch 15 分钟 job 上限**：24 页一次抓会超时被 cancel（archive.org 偶发 90s 超时）→ **拆成 2~3 个小批**（每批 ~12 页）。
- 正文容器 `div.span10`（剥离 `div.page-header` 的 h1）；`pre>code`（`class=lang-*` 取语言）；`ul`；`div.alert` → 引用块。
- 分组取自页面 `leftnav`：概要 / 控制器 / 模块 / 操作 / 参考（5 TITLE，`NN-` 前缀）；`00-說明` = index（介绍）。
- 收尾 `prependNode/sibling` 把 `00-說明.md` 挪到首个 TITLE 前。

结果：29 节点（5 目录/24 文档），无图；六查全绿（word_count 24/24>0 min 89 / 回读 0 异常 / 根序归位）。
