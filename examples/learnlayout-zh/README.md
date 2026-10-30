# examples/learnlayout-zh —《学习CSS布局》(zh.learnlayout.com)

fpb52 #119 · 库 85155135 · 网站口径 · 2026-10-31

静态多页站（learnlayout.com 中文版）：
- 页面清单与顺序 = `/toc`（20 讲）；加首页 = 21 篇，`NN-标题` 前缀免归位。
- 正文容器 `#container`；**剥** `style`/`script`、`.nav-wrapper`（上一页/下一页）、`footer`（页码）、`#translations`（语言切换）。
- ⚠️ 有的页（float 等）把 `.nav-wrapper`/`footer` **嵌在 `<p class="content">` 里** → 光在块级过滤不够，`inline()` 里也要跳过 `nav-wrapper`/`footer`。
- 代码块 = `figure.highlight > pre > code.language-x`；live demo 盒子的 `<span class="label">` 转行内代码。
- 图：仅 `frameworks` 页 10 张框架 logo + `float/percent` 的样例图 → 下载到 `images/` 后传 CDN 删目录。

结果：21 节点（0 目录/21 文档），12 图 CDN；六查全绿（word_count 21/21>0 min 27 / 回读 0 异常 / 根序正确）。
