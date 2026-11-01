# PDF 书 → 语雀（2026-11-01 #152《Spring 2.0核心技术与最佳实践》实战）

**触发**：站点只托管一个 PDF 原件（`michaelliao.github.io/download/pdf/...`），无 HTML 版、无源仓库。廖雪峰 2007 年书（电子工业出版社），543 页。

## 库信息
- 库 85209087 / slug `spring2-core-practice-20261101` / 网站口径（分组文章收集）
- 双轨：解析正文 16 篇（前言 + 11 章 + 附录 A/B/C）+ `00-PDF 原件.md`（PDF 附件）
- 六查全绿（TOC 16==本地、word_count 16/16>0、附件 URL 在 body）

## 流程要点
1. **书签锚定章节**：`首页NN` 书签 = 章封面页（跳过），`NN` 书签 = 章正文起点；章名 = 紧跟 `首页NN` 的下一个 2 级书签（如「初识Spring」）
2. **章节页范围** = 章正文起点 → 下一章封面页前
3. **页眉剔除**：章标题页眉行（`Spring 快速入门` 等，出现 ≥3 次的高频短行即候选）在代码块内外都要剔
4. **代码围栏化**：PDF 提取的代码行缩进不规则（有的顶格）→ 用 Java 语法特征攒块（`public/private/class/import/void` 等 CODE_START + `[;{}]$` CODE_END，`}` 单行也算），**空行并入**（下一行仍是代码）
5. **段落软换行合并**：上一行无句末标点（`。！？；：）}"`）即续接（中文 PDF 物理行合并）
6. **PDF 原件附件**：`type=attachment`（非 image）上传 → 取响应 `url` 字段（`yuque.com/attachments/...`）→ 根级 `00-PDF 原件.md` 挂 `📎 [name.pdf（NNNNKB）](url)`

## 复用
```bash
python3 build.py          # 生成 site/（16 篇 md）
# 之后：手动传 PDF 附件 → 建 00-PDF 原件.md → tree_import --toc-md → 六查
```

⚠️ 老书 PDF 提取是「可读级」：代码围栏有碎片、正文带断行噪声，属预期（正文可读 + 原件可下即达标）。
