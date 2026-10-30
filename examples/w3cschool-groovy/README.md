# examples/w3cschool-groovy —《Groovy 教程》(w3cschool.cn)

fpb52 #114 · 库 85155150 · 网站口径 · 2026-10-31

w3cschool「Groovy 教程」（Groovy 官方教程中文版，tutorialspoint 风格）36 篇。
- 页面清单/顺序取自首页侧栏 `/groovy/*.html` 链接；`NN-<h1>` 前缀免归位。
- 正文容器 `div.content-intro`；页面标题取容器外的 `<h1>`。
- 代码 `pre.prettyprint.tryit` → ```；输出 `pre.result` → ```text；表 `table.reference`。
- ⚠️ **表格行必须 join 成一块**（每行 push 成独立块会被空行拆散 → markdown 表失效）。
- ⚠️ **容器的直接子 `<img>` 要单独分支渲染**（只靠 `inline()` 会漏掉不在 `<p>` 里的图）。
- 图在 `atts.w3cschool.cn`（外链）→ 下载本地化传 CDN（21 图）。

结果：37 节点（0 目录/37 文档 = 36 篇 + 说明），21 图 CDN；六查全绿（word_count 37/37>0 min 40 / 回读 0 异常 / 根序正确）。
