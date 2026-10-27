# LaTeX 书稿仓库 → 语雀（《AWK 程序设计语言》中文译本，2026-10-27）

源仓库：`https://github.com/wuzhouhui/awk` @ `787d83c`（Aho / Kernighan / Weinberger 著，社区中文译本，2015–2022 停更，全部章节译完）
产出库：**85035154**（slug `awk-787d83c`）｜ 65 节点 = 9 目录 + 56 文档 ｜ 18 张矢量图

## 为什么走 LaTeX 源而不是 PDF 抽章

仓库里同时有 `The_AWK_Programming_Language_zh_CN.pdf`（中文成书）和 `latex_src/`（正文 LaTeX 源）。
- PDF 抽章（`references/pdf-book-to-yuque.md`）省转换器，但代码块缩进/`verbatim` 与表格靠排版猜，易丢；
- LaTeX 源结构最全（`awkcode` 环境 483 个、`pattern` 语法框 44 个、`tabular` 20 个、`tabbing` 15 个、`exercise` 84 个、`summary` 框 7 个），**正文只吃源**；
- **图反过来从 PDF 裁**：本书插图是 6 个 `.eps` + 14 个 `tikzpicture`（无 caption、无编号），既不能直接传 CDN（eps），手写 TikZ 渲染器也不划算 → 用 `crop_pdf_fig.py` 在**成书 PDF 里按文本锚点定位图区**裁 PNG（300dpi）。

## 脚本

| 脚本 | 作用 |
|------|------|
| `latex2md.py` | 通用 LaTeX 子集 → Markdown 渲染器（章节/表格/代码/列表/习题/总结框/数学/引用/字号宏指令） |
| `build_lib.py` | 本书装配：章节切分、编号两遍扫描（`\ref` 解析）、目录树落盘、图拷 `images/` |
| `crop_pdf_fig.py` | 按「图后正文首句」锚点 + PDF 矢量图形簇裁图（`--needle/--mode/--page/--clip`） |

```bash
# 1) 裁图（每个图给一个锚点=图后面那段正文的开头几字，避免命中多页）
PDF=...zh_CN.pdf python3 crop_pdf_fig.py --needle "指向最后一个比" --out figs/exp-partition1.png
PDF=...zh_CN.pdf python3 crop_pdf_fig.py --page 128 --clip 45,80,545,244 --out figs/proc-grammar.png
# 2) 装配（要 latex_src/ 与 figs/）
python3 build_lib.py /path/to/out
# 3) 传图 + 重写 + 删 images/ + toc-md 导入 + 六查
python3 ../../scripts/yuque_rewrite_images.py /path/to/out img_map.json --throttle 3
```

## 结构口径

- `00-前言.md`（根级 DOC，`prependNode` 提到首位）+ 8 个 `第N章 标题` TITLE + 附录 TITLE（`附录A`/`附录B`）+ 根级 `索引.md`
- **一节一篇**：`N.M 标题.md`；章首导读落 `00-本章导读.md`（有正文才建）
- 小节标题按原书**不编号**（preamble 里 `\CTEXsetup[number={}]{subsection}`）→ `## 标题`；`\subsubsection` 在附录里升 `##`、在章内降 `###`
- 表按章编号还原成 `**表 2.1** 比较运算符`；习题还原成 `**习题 3.1** 题干…`；`\ref` 全部解析成「第X章 / N.M / 表 N.M / 习题 N.M」

## 踩过的坑（详见 references 坑 69）

1. **`%` 注释必须在 verbatim 之后剥**：awk 代码里满地 `printf("%s\n")`，先跑 `strip_comments` 会把 `"` 之后整行吃掉 → 代码块全废。做法：`protect_verbatim()` 先把 `awkcode/verbatim/lstlisting/\verb` 换成 `\x02N\x02` 占位，剥完注释再还原。
2. **`\verb` 的结束符要按分隔符配平**：`\\verb\W[^\n]*?\W` 会在 `\verb'"%.6g"'` 的第二个 `"` 处提前收尾，剩下的 `%.6g` 触发注释截断 → 表格整行被吞。正确写法 `\\verb\\*?(.)(?:(?!\\1).)*?\\1`。
3. **`tabular` 切分不能把转义 `\&` 当列分隔**：分隔符判断要放在「反斜杠转义」分支**之前**且带花括号深度，否则 `\makecell{a \\ b}` 里的换行会把一行拆成两行。
4. **`figure` 环境在本书里是「表」不是「图」**（`\captionsetup{type=table}` + `\caption`）；`\begin{figure}[ht]` 的 `[ht]` 属于 body 开头，必须剥掉（否则漏成正文 `[ht] 比较运算符`）。
5. **无 `\hline` 的 `tabular` 没有表头**：Markdown 必须有表头 → 造空表头 `| | |` + 分隔行，别拿首行数据当表头。
6. **`tabbing` → 两列表**（`\>`/`\=` 切左右），单元格里 2+ 空格要收（源里是排版缩进）；`\hspace{8em}` 残留在左列会变成多余空格。
7. **`\marginpar{N}` 是原书页码**（每页一个数字），全删；**`quote` 里含表格/代码块时不要套 `> ` 引用块**（围栏和表格被 `>` 打散），直接透出。
8. **段落级标记法**：`\subsection{..}` 等标题命令先换成 `@@H2@@…@@` 独立段落，再交给行内渲染器 —— 直接让 inline 输出 `## ` 会跟整段正文黏在一行。
9. **CJK 之间不补空格**：源码硬换行拼接按「两侧都是 CJK 就不加空格」处理（`模式–动作` 这类宏自带首尾空格也要靠这条压掉）；代码块内一律不动。
10. **图必须在 PDF 里找**：`\includegraphics` 的 eps 与 `tikzpicture` 在 PDF 里都是矢量路径 → `page.get_drawings()` 聚簇（gap≈20pt）+ 以簇为骨架「吞并」邻近文本行（只吞 x 范围与簇重叠的），才能把 `\node[left]` 这类画在框外的标签一起框进来。
11. **裁图锚点用「图后正文首句」**（纯中文 8–12 字最好）：`page.search_for()` 不认跨行，长锚点会找不到；图落在页首时 `mode=before` 要回退上一页页尾（`mode=after` 反之）。
12. **根级 TITLE 顺序会被 Unicode 字典序打乱**（`一 三 二 五 八 六 四`）：toc-md 后按目标顺序**逆序 prependNode 到首位**逐步归位；根级 DOC（前言/索引）同理。

## 实测

- 65 节点（9 目录 / 56 文档）；toc-md 目录树 65 行 / 2744B，PUT **0.6s**，结构核对 PASS，0 失败
- 18 图全部 CDN（rewrite 18/18，0 缺失；`images/` 已删净）
- 六查全绿：TOC 65==本地 65 ｜ 56 条 DOC 路径唯一 ｜ 对账 0 错位 ｜ 幽灵 0（docs 56 == TOC DOC 56）｜ 56 篇 word_count 全 >0（最小 111）｜ 逐篇回读 56 篇 0 差
- 根级顺序修正：`00-前言.md` → 首，`索引.md` → 尾
- ⚠️ move-stack 未过（cookie Web API 写侧风控，连续 ≥1 天，见 `references/api-notes.md`）→ 分组待补 stack 57018723