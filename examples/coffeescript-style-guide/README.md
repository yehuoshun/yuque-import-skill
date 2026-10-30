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

---

## 附：同书第二译本（geekplux 版，2026-10-30 导入，库 85147386）

- 源：https://github.com/geekplux/coffeescript-style-guide @ `b87e527`（`README.md` 即**中文正本**——该仓把中文放主 README，另一仓 elrrrrrrr 放 `README-ZH.md`）
- 库：85147386 / slug `coffeescript-style-guide-b87e527` / https://www.yuque.com/yehuoshun/coffeescript-style-guide-b87e527
- 结果：15 文档（全根级 DOC），六查全绿。
- 与 elrrrrrrr 版的差异（除译文用词不同外）：
  1. **首屏有 codesponsor.io 赞助横幅**（`<a target='_blank'>…<img/></a>` 一行）→ 需额外剔掉。
  2. **H2 全部唯一**（只有一个 `## 注释（Comments）`；annotations 直接叫 `## 注解（Annotations）`）→ **不需要重名改名**。
  3. 章节标题带英文括注（`代码布局（Code Layout）`）→ 文件名含全角括号 `（）`，无 `/`，安全。
  - 其余坑（跟围栏拆篇、剔 `## 目录`、剔 `<a name=…>` 锚点、引用式链接内联）与 elrrrrrrr 版一致（见上「复用要点」与 references 坑 82）。
- 脚本：`examples/coffeescript-style-guide/build_geekplux.py`。
