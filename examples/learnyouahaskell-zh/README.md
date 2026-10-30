# examples/learnyouahaskell-zh —《HASKELL 趣學指南》

fpb52 #115 · 库 85155144 · MnO2/learnyouahaskell-zh @ 8247441 · 2026-10-31

站点 `learnyouahaskell.mno2.org` = **繁中版** → 吃源仓库 `zh-tw/` 的 md（站点即此繁中版）。
一章一篇（14 章 + FAQ），`NN-` 前缀；每章首个 H1 == 标题 → 剥。
图：全部在 `.gitbook/assets/`（引用为 `../../.gitbook/assets/x%20%281%29.png`，URL 编码）→ `unquote` 解码后**净化文件名**（空格→`_`、去括号），再本地化传 CDN。
- ⚠️ **带空格/括号的文件名必须净化**：`yuque_rewrite_images.py` 用 `split(None,1)` 处理 `"title"`，会把 `assets/bird (1).png` 截成 `assets/bird` → 判本地缺失。
- `resource-1/resource.md` 只有 `# resource`（12B 空壳）→ 不收。
- FAQ 里 `https://github.com/.../$img/turtle.png` 是坏外链，原样留。

结果：16 节点（0 目录/16 文档），115 图 CDN；六查全绿（word_count 16/16>0 min 231 / 回读 0 异常 / 根序正确）。
