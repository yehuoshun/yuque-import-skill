# go-ast-book（《Go 语法树入门》/《Go语言定制指南》）→ 语雀

- **源**：https://github.com/chai2010/go-ast-book @ `6bb3a6f`（2024-09-26）
- **作者**：柴树杉 / 史斌 / 丁尔男；书名《Go 语言定制指南》（原名《Go 语法树入门》）
- **库**：85149817 ／ slug `go-ast-book-6bb3a6f`（开源项目口径，stack 57018723）
- **产物**：20 文档扁平（零目录）、13 图 CDN；rebuild：`python3 build.py`

## 结构

GitBook 3.x 源仓（`chN/readme.md` + `SUMMARY.md`），**SUMMARY 只列到「章」、没有子节层级** → 一章一篇：

| 源 | 目标 |
|---|---|
| `index.md` | `00-Go语言定制指南.md` |
| `preface.md` | `01-前言.md`（三篇序言合一，内层 H1 → ##） |
| `chN/readme.md` | `NN-第N章 xxx.md`（N=1..16，两位零填充） |
| `appendix/a-goyacc/readme.md` | `18-附录A goyacc.md` |
| `appendix/b-antlr4/readme.md` | `19-附录B ANTLR4.md` |

章号/序号零填充 → `sorted(listdir)` 字典序即书序，**免收尾 prependNode 归位**（扁平零目录，本来也没有顺序坑）。

## 三个要点

1. **第 12–16 章正文未开源**：出版社版权限制，仓库里只留一段「本章简介」+ 实体书购买链接（ch12 还多一句「出版社已约稿…增加了语义信息/SSA/LLVM/凹语言」）。**保留为简介文档**（让读者知道章节存在、残缺在哪），剥掉每章重复的同一张实体书封面图；残缺度写进库描述。preface.md 里三篇序言同样只有一句「版权限制请参考实体书」。
2. **图片是 `../images/x.png`**：导入树是扁平的，先生成 `images/` 与 `cover.jpg` 到 clean 根 → `yuque_rewrite_images.py` 传 CDN（13 处）→ **`rm -rf images cover.jpg` 再导入**（否则每张图变独立占位文档，SKILL 硬规则 10）。
3. **不收**：`ch7/x.md`（孤儿片段「1.2 复合面值」，与 ch8 重复）、`ch*/examples/**` 与 `appendix/**/examples/**` 源码树（书里是片段讲解，不是书稿正文）、`book.ini`/`Makefile`/`style.css`/`README.md`/微信二维码图。

## 六查结果（2026-10-30）

TOC 20 == 本地 20 ／ 对账错位 0 ／ 幽灵 0（docs 20 == TOC DOC 20）／ word_count 20/20 > 0 ／ 逐篇回读 20/20 零异常（CDN 引用 13 == 重写数）／ 无分片。toc-md PUT 0.6s，结构核对 PASS。

⚠️ `move-stack` 开源项目 57018723 三轮均返 `{}`（语雀侧 2026-10-27/28 起的静默 no-op 回归，见 `references`）→ 挂账。
