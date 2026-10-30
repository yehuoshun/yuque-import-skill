# examples/codeguide — AlloyTeam 前端代码规范（CodeGuide）

fpb52 #117 · 库 85155128 · AlloyTeam/CodeGuide @ 2c2864b (gh-pages) · 2026-10-31

源 = **Jekyll 站点**：`index.html` 拼装 `_includes/*.html` 分片，代码样例再 `{% include css/x.css %}`。
口径：**展开 include → HTML→md**，一篇一大区：
`00-说明`(README) + `01-最佳原则` + `02-命名规则` + `03-HTML 规范` + `04-CSS、SCSS 规范` + `05-JavaScript 规范` + `06-检查工具`。

要点：
- 写一个 Jekyll include 展开器（递归 `{% include X %}`），`{% highlight lang %}…{% endhighlight %}` → `<pre data-lang>` 转围栏代码。
- 各大区首行 `## 区域名` 与文档标题重复 → 剥；其余规则标题降一级（`### 规则` → `## 规则`）。
- 无正文图（`images/demo_*.png` 只被 CSS 引用）；`fonts/`、`_includes/*.js` 脚手架不入库（本口径只产 md）。

结果：7 节点（0 目录 / 7 文档），无图；六查全绿（word_count 7/7>0 min 59 / 回读 0 异常 / 根序正确）。
