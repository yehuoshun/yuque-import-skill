# 案例：reStructuredText 书稿源（.rst → md 自写转换器）（《Backbone.js入门教程第二版》，2026-11-01）

触发链接是 GitHub 仓库 `the5fire/backbonejs-learning-note`，仓库里**没有 md**，全是 `.rst`（Sphinx 风格）。
走开源项目口径（库名带 commit、分组「开源项目」stack 57018723）。

## 结论先行

| 项 | 值 |
|---|---|
| 库 | `Backbone.js入门教程第二版（6d91478）` id=85211950 slug=backbonejs-learning-note-6d91478 |
| 节点 | **54**（9 目录 + 44 文档 + 1 PDF 附件文档） |
| 图 | 5 张全传语雀 CDN |
| 附件 | 原书 PDF 1.3MB 上传为独立文档（doc 290342342） |
| 六查 | 全绿（幽灵 0 / word_count=0 篇 0 / 回读 3 篇逐字符相等） |

## rst 转换要点（build.py）

1. **标题层级靠下划线字符区分**：`===`/`---`/`~~~` 各自映射到 md 的 `#`/`##`/`###`（按出现顺序维护层级表，不要按字符种类硬编码）。
2. `.. code:: lang` + 缩进块 → 围栏代码块；缩进统一去 4 空格基准。
3. `.. image:: path` → `![alt](path)`，带 `:alt:` 选项时取该值；图片路径相对 rst 文件目录。
4. 行内 ` ``code`` ` → `` `code` ``；`**bold**`/`*em*` 原样保留。
5. 链接：`\`title <url>\`` → `[title](url)`；**站内死链**（链到 repo 里不存在的文件）→ 剥成纯文本，避免语雀 404。
6. 全局收尾：剥掉围栏外残留的行尾 `::`（rst 的「以下为代码块」标记）。
7. 列表：`*` / `#.` 混排时注意 md 嵌套缩进（2 空格），`*N.` 会被误判斜体，需按 `^*\d+\.` 特判。
8. `images/` 目录在导入**之前**删掉（图已传 CDN），否则 tree_import 会把图片目录当文档建出来（占位文档污染，见 way-to-go 案例）。

## PDF 附件入库（预建文档 + 账本注入 + 磁盘空占位）

`yuque_tree_import.py` 的 `build_toc_md` **只遍历磁盘树**，账本里有 doc 但磁盘没文件的节点会被挤出 TOC（表现为「幽灵 0 但附件文档不在目录里」）。
正确姿势（与 llmbooks 双轨一致）：

1. 先 `POST /repos/{book}/docs` 创建 PDF 文档并上传附件 → 拿到 doc_id。
2. 往 progress 账本写节点：`nodes["<文件名>"] = {"type":"doc","doc_id":...,"slug":...,"segments":[{"title":...,"slug":...,"doc_id":...}]}`。
3. **磁盘放一个同名空占位文件**（`touch site/xxx.pdf`，内容无所谓）。
4. 重跑 tree_import（toc-md）：占位文件命中账本 → skip 创建，但 `build_toc_md` 能拼进目录树 → PUT 后归位。

## 删库重导注意

`progress` 账本记录的是 **doc_id**；如果删库重建，**必须删掉 progress 文件**，否则全部节点走 skip（新库 0 文档、TOC 挂死 id）。
删库改正文同理：toc-md 模式**不更新已存在文档的正文**，正文要改只能删库重导或逐篇 PUT。