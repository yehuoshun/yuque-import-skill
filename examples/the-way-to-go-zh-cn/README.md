# the-way-to-go_ZH_CN（《Go 入门指南》）→ 语雀

- **源**：https://github.com/Unknwon/the-way-to-go_ZH_CN @ `7a54d34`（《The Way To Go》中文译本）
- **库**：85149501 ／ slug `the-way-to-go-zh-cn-7a54d34`（开源项目口径，57018723）
- **产物**：4 个部分 TITLE + 21 个章 TITLE + 211 文档 = 236 节点；35 图 CDN

## 结构

- 层级**取自 `eBook/directory.md`**（4 部分 / 21 章 / 190 节），不是文件名——章 1/2/4 没有 `NN.0.md` 章导读，章标题只有目录里有
- `NN.M.md`（M≥1）→ `第NN章 .../NN.MM 标题.md`；`NN.0.md` → `第NN章 .../00-本章导读.md`
- 节号与章号都**零填充两位**（`04.05`），否则 `4.10` 会排到 `4.2` 前
- 部分目录名里把全角冒号换成空格（`第一部分 学习 Go 语言`）
- `preface.md` → 根级 `00-前言.md`；`Discussion_about_16.10.md` → 第16章「16.10 附：…」

## 三个坑

1. **部分名按 unicode 排序会乱**：`三(4E09) < 二(4E8C)` → toc-md 生成的顺序变成 一、三、二、四。导入后必须用 `prependNode` 把「第二部分」挪到「第三部分」前（或一开始就给目录名加 `第1部分/第2部分` 数字前缀）。
2. **图有 HTML 写法**：`<img src="images/x.jpg?raw=true" style="zoom:80%">`（10.6 节）——只认 markdown `![]()` 的转换器会漏图；`?raw=true` 后缀要剥掉再找文件。上游确有两处图缺失（`20.8_fig20.1.png`、`studygolang-qrcode.jpg`）→ 正文原位标注「原书插图缺失」。
3. **收尾必做**：`rm -rf <clean>/images` **要在导入之前**。本次因工具层超时导致 rm 未执行，244 张图被当成 35 个占位文档塞进库（TOC 多出 `images` TITLE）→ 事后只能逐个 `DELETE /repos/{id}/docs/{doc_id}`（35 个）再 `removeNode` 删空的 `images` TITLE，并清掉 progress.json 里的 `images/*` 条目，否则回读脚本会报「TOC 无此 uuid」。
