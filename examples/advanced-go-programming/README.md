# advanced-go-programming-book（《Go语言高级编程》）→ 语雀

- **源**：https://github.com/chai2010/advanced-go-programming-book @ `4447d09`（2025-10-07）
- **作者**：柴树杉 / 曹春晖；书名《Go语言高级编程》Advanced Go Programming
- **库**：85150011 ／ slug `advanced-go-programming-4447d09`（开源项目口径，stack 57018723）
- **产物**：7 TITLE + 69 文档 = 76 节点；74 图 CDN；rebuild：`python3 build.py`

## 结构（层级取自 SUMMARY.md）

| 源 | 目标 |
|---|---|
| `index.md` / `preface.md` / `errata/README.md` | 根级 `00-Go语言高级编程.md` / `01-前言.md` / `02-勘误（第一版第一次印刷）.md` |
| `chN-*/readme.md` | `第N章 <章名>/00-本章导读.md` |
| `chN-*/chN-MM-*.md` | `第N章 <章名>/NN-<SUMMARY 标题>.md`（**章内序号每章从 01 重置**） |
| `appendix/readme.md` + `appendix/appendix-*.md` | `附录/00-本章导读.md` + `附录/NN-附录X：….md` |

剥每篇首个 H1；标题/文件名里 `/` → `／`、`:` → `：`。

## 三个要点

1. **图片按章归集**：正文写的是 `../images/x.png`（相对章目录一跳）。导入树是分层的，所以**按章把被引用的图拷进 `<章目录>/images/`、引用改 `images/x.png`**，再统一传 CDN。⚠️ 注意**章节与图名前缀不一致**：`ch5-web` 的正文引用了一大批 `ch6-*` 命名的图（ch5 22 张图里多数是 ch6 前缀）——按「谁引用」归谁，别按图名前缀猜章。
2. **章内序号每章重置**：toc-md 的树序来自 `sorted(listdir)`，节名必须带两位前缀（`01-…`、`11-…`），且**每进入新章要重置计数**，否则第二章会接着第一章的号继续编、顺序全乱。
3. **根级多文档要按升序 prependNode**：根级 `00/01/02` 三篇在 toc-md 后都排在所有 TITLE 之后。归位时**按目标顺序从前往后逐发 prepend（升序）**——`prependNode` 是「插到 target 之前」，倒序发出会把顺序写反。

## 六查结果（2026-10-30）

TOC 76 == 本地 76 ／ 对账错位 0 ／ 幽灵 0（docs 69 == TOC DOC 69）／ word_count 69/69 > 0 ／ 逐篇回读 69/69 零异常（CDN 引用 74 == 重写数）／ 无分片。toc-md PUT 1.4s，结构核对 PASS。

⚠️ `move-stack` 开源项目 57018723 三轮均返 `{}`（语雀侧 2026-10-27/28 起的静默 no-op 回归）→ 挂账。
