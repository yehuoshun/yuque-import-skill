# examples/coffeescript-style-guide —— 《CoffeeScript 风格指南》中文译本

- 源：https://github.com/elrrrrrrr/coffeescript-style-guide @ 7b7fd79（`README-ZH.md`；英文 `README.md` 与 `coffeelint.json` 不入库）
- 库：85147316 / slug `coffeescript-style-guide-7b7fd79` / https://www.yuque.com/yehuoshun/coffeescript-style-guide-7b7fd79
- 结果：15 节点（全根级 DOC），六查全绿。

## 复用要点（详见 references/github-repo-to-yuque.md 坑 82）

1. **按 `## ` 拆文档并跟代码围栏**——`# 正确` / `# 错误` 是围栏内注释，`grep '^#'` 会误当 H1 标题。
2. **剔 `## 目录`**：语雀自带侧边 TOC；原目录全是 `#anchor` 内链，导入后必死。
3. **剔 `<a name="x"/>` 锚点行**（每个小节前一行）。
4. **内联引用式链接**：文末 `[ref]: url` 定义块在拆篇后落在别的文档 → 先全量收集再 `[t][r]` → `[t](url)`，最后删定义块。
5. **重名 `## 注释`**（comments / annotations 各自一个）→ 同父同名会歧义，后者改「注解」。
6. **全根级 DOC 时不用归位**：walk 按名称排序，`00-`…`14-` 零填充 = 阅读序。
