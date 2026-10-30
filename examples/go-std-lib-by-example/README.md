# The-Golang-Standard-Library-by-Example（《Go语言标准库》）→ 语雀

- **源**：https://github.com/polaris1119/The-Golang-Standard-Library-by-Example @ `c466fcc`（2022-03-06，CC BY-SA 3.0）
- **书名**：polarisxu《Go语言标准库》The Golang Standard Library by Example 开源版 md 源
- **库**：85149891 ／ slug `go-std-lib-by-example-c466fcc`（开源项目口径，stack 57018723）
- **产物**：13 章 TITLE + 51 文档 = 64 节点；1 图 CDN；rebuild：`python3 build.py`

## 结构（层级取自 SUMMARY.md）

| 源 | 目标 |
|---|---|
| `README.md` | `00-简介.md`（剥作者二维码图） |
| `chapterNN/NN.0.md` | `第NN章 …/00-本章导读.md` |
| `chapterNN/NN.M.md` | `第NN章 …/NN.M 标题.md` |

章号两位零填充（`第01..第16`），节名用 **SUMMARY 文本**（比文件 H1 规范，很多 H1 没有编号）；剥每篇尾部 `# 导航` 段 + 首 H1；标题/文件名里 `/` → `／`（`path/filepath`、`io/fs`、`database/sql`、`sync/atomic`、`os/signal`）。

## 四个要点

1. **书未写完**：SUMMARY 列 17 章，仓库实存 chapter01–10/13/15/16。第 11/12/14/17 章只有章名；3.2、5.2–5.4、7.2–7.4、8.2–8.4、13.2/13.4、15.1 等节无链接文件。→ **无正文的章/节一律不建空壳**，残缺度写进库描述。⚠️ 13.2/13.4 SUMMARY 挂了链接但**文件不存在（断链）**——按「文件存在」判，跳过并记 missing。
2. **别漏「SUMMARY 未收录但有正文」的孤儿**：7.5 `encoding/csv`、8.5 `archive/tar` 两个文件在仓库里、SUMMARY 里是纯文本无链接 → 按文件名编号补落到本应所属的章目录（7.5 内容完整；8.5 只有两句话、H1 还错标成 8.1）。
3. **章首页不一定有**：ch5/15/16 的章标题在 SUMMARY 里无链接（=没有 `NN.0.md`）→ 目录靠 `第NN章` TITLE 建，**章目录名要从「待用章标题 + 节路径里的 chapterNN」推**，不能只看章标题行有没有链接。
4. **收尾必做**：根级 `00-简介.md` 在 toc-md 后会排到所有 TITLE 之后 → 补 1 发 `prependNode/action_mode=sibling, target_uuid=<第一个 TITLE>` 归位（坑 29）。章内图片 `chapter06/imgs/` 拷进章目录、传 CDN 后**连目录删净**。

## 六查结果（2026-10-30）

TOC 64 == 本地 64 ／ 对账错位 0 ／ 幽灵 0（docs 51 == TOC DOC 51）／ word_count 51/51 > 0 ／ 逐篇回读 51/51 零异常（CDN 引用 1 == 重写数；另有 1 张新浪外链原样保留）／ 无分片。toc-md PUT 0.9s，结构核对 PASS。

⚠️ `move-stack` 开源项目 57018723 三轮均返 `{}`（语雀侧 2026-10-27/28 起的静默 no-op 回归）→ 挂账。
