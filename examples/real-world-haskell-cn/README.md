# examples/real-world-haskell-cn —《Real World Haskell》中文版

fpb52 #116 · 库 85155146 · huangzworks/real-world-haskell-cn @ f67b07d · 2026-10-31

Sphinx/reST 书稿仓（`conf.py`/`Makefile`/`index.rst`/`chp/N.rst`）。
- `yuque_rst_convert.py` 转 md；**转换前先剥 rst 注释**（`.. xxx` 无 `::` 的行 + 其缩进续行），否则留 `-->` 垃圾（chp/12 整块）。
- 章 `chp/N.rst` → 根级 `NN-<H1>.md`（零填充；标题取自 md 首个 `# `）；`index` → `00-说明`；`convention` → `90-翻译约定`。
- 转换后**再兜一道**：删除代码围栏外、行尾 ` -->` 且无 CJK 的注释残留行。
- 图 `image/`（引用混合 `/image/x` 绝对 与 `../image/x` 相对）→ 统一改 `image/x` 拷到导入根 → 传 CDN 删目录（18 图）。
- `code/`（Haskell 源码，已由 literalinclude 内联）不入库。
- 残缺度：第 17 章未译（toctree/磁盘都没有）。

结果：29 节点（0 目录/29 文档 = 27 章 + 说明 + 翻译约定），18 图 CDN；六查全绿（word_count 29/29>0 min 303 / 回读 0 异常 / 根序正确）。
