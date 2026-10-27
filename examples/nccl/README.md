# NCCL《新概念C语言》→ 语雀导入树构建（limingth/NCCL @2fae5f0）

2026-10-27 fpb52 #62 实战，库 **85035630**（slug `nccl-2fae5f0`），62 节点（4 目录 / 58 文档），14 图。

## 仓库形态

不是译本，是作者李明自建的 C 语言课程书稿，**扁平 `Lesson-N.md` 结构**，没有 SUMMARY / book.json / conf.py 任何脚手架：

```
README.md              全书大纲（4 Unit × 24 = 96 课规划）
Unit-1/  24 × Lesson-N.md + README.md（= 单元导读：环境安装 + 逐课知识点大纲）
Unit-2/  24 × Lesson-N.md + README.md
Unit-3/  Lesson-49.md + Lesson-49/（代码目录）+ parser-tree.md + README.md
Unit-4/  README.md（空壳：73–96 全空）
images/  14 张（被 Unit-1/Unit-2 的 ../images/xxx 引用）
slides/  14 个 Lesson-1~14.pdf（pandoc/beamer 由 Unit-1 同名 md 生成）+ main.tex/Makefile/md2pdf.sh
enrollment.md          招生广告（含报价）
```

## 发布面口径

| 项 | 处理 |
|---|---|
| 00-前言 | 根 `README.md`（剥 setext 标题 `新概念C语言 / =====`） |
| Unit-1 / Unit-2 | 目录 + `00-Unit-N 导读.md`（原 `Unit-N/README.md`）+ 各 24 课 |
| Unit-3 | 目录 + 导读 + Lesson 49 + `49-代码/`（readfile.c / state.c / test.c / Makefile） |
| Unit-4 | **不建**（仓库只有空 README，作者自述未写完） |
| 附加 | `parser-tree.md` → `90-附加-语法分析树（原编号 Lesson 37）.md` 收在 Unit-3 尾 |
| 跳过 | `slides/`（派生品）、`enrollment.md`（招生）、`a.out`/`demo`/`readfile.o`（二进制） |

## 转换要点（踩过的）

1. **CRLF 必须转 LF**：13 篇原文件是 CRLF，直接导会让缩进代码块/表格断行。
2. **标题取文件 H1，不取根 README 的列表**：`Unit-1/Lesson-31` 的 H1 是「ll 和 date」、`Lesson-32` 是「Bash Clone」，根 README 写的是「ll (ls -l)」「MyBash 项目」——**不一致时以文件为真**，README 只是大纲。
3. **剥 `Lesson N` 前缀 + 补 `NN-` 序号**：原文件名 `Lesson-1.md` 字典序 = 1,10,11,…，必须零填充；标题里的英文+中文双名保留（`01-What is the simplest C program? 最简单的C程序.md`）。
4. **标题里的半角 `*` 洗成 `＊`**：Lesson 6「Print 9*9 multiplication table」——`*` 在标题里会被 markdown 当强调，且文件名容易踩坑。
5. **单元 README 里的站内相对链接要转纯文本**：`## Lesson 1 [What is ...](Lesson-1.md) 最简单的C程序` 在语雀里是死链（且 toc-md 的目录树按 `](...)` 切标题，留着会污染）。绝对外链（github.com/... 百度云/播客）保留。
6. **`README.md` 当导读不重复计数**：`Unit-N/README.md` 里既讲环境也在罗列 24 课知识点 → 保留全文（知识点大纲有价值），只做 delink。
7. **`../images/` 引用天然能解析**：把 `images/` 原样拷到导入根，`Unit-N/xxx.md` 里的 `../images/a.png` 正好指向根图片目录，rewrite_images 能直接上传，**不需要改引用路径**（对比 cppwasm-book 必须按章重映射）。
8. **同编号异内容要归位**：`Unit-3/parser-tree.md` 自标「Lesson 37 Parse Tree」但与 Unit-2 Lesson 37（词频统计器）撞号 → 放 Unit-3 尾部并改名 `90-附加-…（原编号 Lesson 37）`，别硬塞回 Unit-2。
9. **极薄正文 + 代码目录**：Lesson 49 正文 243B、内容全在同名目录 → 建 TITLE `49-代码` 收 `.c`（走纯文本代码块），二进制（`a.out`/`demo`/`.o`）不导。
10. **残缺度必须在三处写明**：库描述、`00-前言`/`00-Unit-3 导读` 末尾、账本 note —— 原书规划 96 课、实存 49 课，别让后来者以为是漏导。

## 跑法

```bash
# 1. 取源（HTTPS 直连常 502，用 codeload）
curl -sL -o /tmp/nccl.tar.gz https://codeload.github.com/limingth/NCCL/tar.gz/refs/heads/master
mkdir -p /tmp/nccl-src && tar xzf /tmp/nccl.tar.gz -C /tmp/nccl-src --strip-components=1

# 2. 改 build_lib.py 顶部 SRC/OUT，生成导入树
python3 build_lib.py

# 3. 传图 + 删图片目录 + 导入
python3 ../../scripts/yuque_rewrite_images.py <OUT> <imgmap.json> --throttle 3
rm -rf <OUT>/images
python3 ../../scripts/yuque_tree_import.py --root <OUT> --book <id> --progress <p.json> --toc-md
```

## 结果

六查全绿：TOC 62==本地 62 / 路径唯一 62/62 / 对账 0 错位 / 幽灵 0（docs 58 == TOC DOC 58）/ word_count 58 篇全 >0（最小 17，总 28,648 词）/ 逐篇回读 58 篇 0 异常（4 个 `.c` 仅语雀代码围栏差异）。根级顺序补 1 次 prependNode：`00-前言 → Unit-1 → Unit-2 → Unit-3`。