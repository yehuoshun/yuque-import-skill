# examples/csdn-java-golang —《Java程序员的Golang入门指南》(CSDN)

fpb52 #110 · 库 85155140 · CSDN dc_726 · 2026-10-31（**残缺：(下) 未获取**）

⚠️ CSDN 该文现在带 **JS WAF 安全验证**（HTTP 521 + 26KB 挑战页）：
- 本机直连、`m.blog.csdn.net`、cookie jar、`/phoenix/web/v1/article/detail`、`r.jina.ai` 全失败；
- re-harness runner 出口同样 521；`fetch-files` 也拿不到。
- (上) 篇正文取 **Wayback**（`/web/2id_/...`，逐次 `gzip` 解压；runner 出口能连 archive.org）。
- **(下) 篇 `46745947` 无任何 Wayback 快照**（CDX 返回 `[]`）→ 本库只收 (上)。
- 从作者专栏页 `category_5598457.html` 的 Wayback 快照里找到 (下) 的 id 与标题（标题 oracle）。

口径：网站（文章收集）。正文 `div#content_views`，按 `h2` 拆篇（首个 h2=文章标题）：`00-说明` + `1.序言` + `2.你好，世界` + `3.语法基础` = 4 节点；无图。

结果：4 节点六查全绿（错位 0 / 幽灵 0 / word_count 4/4>0 min 98 / 回读 0 异常 / 根序正确）。
