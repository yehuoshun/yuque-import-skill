# PDF 书 → 语雀（LaTeX 中文教材，多本一套）：蒲公英书系列（2026-10-22）

源：`https://nndl.ai/`（邱锡鹏「蒲公英书系列」主站，Jekyll；站上**只有落地页 + 可视化资源，没有章节正文**）。
4 本书的全文都以 **LaTeX 排版的出版前电子稿 PDF**（GitHub release）形式提供：

| 书 | 站点 | PDF（release） | 页数 | 库 id |
|---|---|---|---|---|
| 神经网络与深度学习（第二版，蒲公英书） | /nndl-v2/ | `nndl/nndl` → `book-pdf` → nndl-v2.pdf | 562 | 84859381 |
| 神经网络与深度学习（通识版） | /nndl-ge/ | `nndl/nndl` → `book-pdf` → nndl-ge.pdf | 360 | 84859382 |
| 神经网络与深度学习：案例与实践（第二版） | /nndl-practice/ | `nndl/nndl-practice` → `book-pdf` → nndl-practice.pdf | 400 | 84859388 |
| 大模型与智能体 | /llm-agent/ | `nndl/llm-beginner` → `book-pdf` → llm-agent.pdf | 419 | 84859389 |

口径：**老板给了站点 → 网站口径**（库名+slug 带日期、分组「文章收集」36149506）；**多本分开建库**（老板 2026-10-22 拍板）。
默认双轨：正文逐章提取 + **PDF 原件走 `type=attachment` 附件**（挂根级 `00-PDF 原件.md`）。

## 流程

```bash
# 1) 下 PDF（release 资产，走 gh-proxy）
curl -sL -o nndl-v2.pdf "https://gh-proxy.com/https://github.com/nndl/nndl/releases/download/book-pdf/nndl-v2.pdf"
# 2) 逐章提取 → <book>/clean/
python3 extract.py v2|ge|practice|llm-agent        # BOOKS 表里改 pdf/out/chapter_level/front
# 3) 组装导入根（拷 clean → import，上传 PDF 附件，写 00-PDF 原件.md）
python3 build.py v2|ge|practice|llm-agent
# 4) 建库 + 移分组（yuque_repo_import.py create-book / move-stack --stack-id 36149506）
# 5) 导入（toc-md）
python3 ../../scripts/yuque_tree_import.py --root <book>/import --book <id> \
        --progress <book>-progress.json --toc-md
# 6) 根级顺序归位（坑 29：toc-md 把根级 DOC 排到 TITLE 之后；本系列还踩到根级 TITLE 字典序错序）
python3 fix_order.py <id> "00-PDF 原件.md" "00-前言.md" ... "第一部分 机器学习基础" "第二部分 基础模型" ...
```

## 提取设计（复用 `build_lib.py` 的思路，针对 LaTeX 中文书改了 4 处）

- **标题用书签文本锚定**：`heading_bytext()` 归一化书签标题（去空格）→ 正文行归一化后相等即判标题；比坐标启发式稳。
  ⚠️ **节号与标题常在同 y 但拆成两行**（`1.1.1` 用 `LMRoman12-Bold`、标题用 `FZHTJW`）→ `page_lines()` 里加**同 y 行合并**（一行是纯节号 `\d+(\.\d+)*` 或 `[A-Z]\.\d+…` 且另一行 size≥10.5 → 拼成 `1.1.1 人工智能的发展历史`）。**附录节号是 `A.1`/`A.1.1`（带字母）**，纯数字正则匹配不到 → 正则要带 `[A-Z]?`。
- **页眉/页脚按书标定**：四本都是页眉 y1≈49（含书名/节名/日期/页码）→ 丢 `y1 < 58`；页脚 y≈648 `https://nndl.ai/` → 丢 `y0 > 640`。
- **边注栏（右栏）**：v2 有大量右侧旁注（x0≈411，`FZKTJW`）；正文 x0=70.9/首行缩进 89-91。`margin_x=350` 把边注与公式编号 `(3.32)` 分流：边注拼成 `> 📝 …` 引用块（**逐行 CJK 相接不加空格**，否则中文旁注插满空格），公式编号丢弃。**通识版是单栏没有边注** → `margin_x` 设成极大值关掉。
- **代码行 → 围栏代码块**：practice / llm-agent 用 `listings`，代码行是等宽字体（`LMMono*`，x0≈93.6），**行号是另起一行（纯数字、非等宽）** → 纯数字行已被「裸页码」过滤丢掉；等宽行攒成 ``` 代码块，缩进 = `round((x0 - code_base)/(size*0.5))` 再对整块做 dedent（`code_base` = 全文档等宽行最小 x0）。**不这么做的话**，代码注释 `# xxx` 会被当 Markdown H1，整篇文档大纲炸掉。
- 大字号（≥14.5pt）行 = 章/部分/前言标题（已由书签生成 `#`）→ 丢；size≥12.5 的行（如「参考文献」小节标题）强制另起段；参考文献行按 `^[A-Z][A-Za-z-]+ [A-Z]` 作者模式起段（否则整段参考文献粘成一坨）。

## 结构

- v2：3 篇前置（前言/如何阅读本书/常用符号表）+ 4 个分部目录（第一/二/三部分 + 附录）+ 16 章 + 附录 A–E = **25 文档 / 4 目录**
- 通识版：前言 + 16 章 = 17 文档（无目录；章节平铺）
- 案例与实践：前言 + 10 章 + 索引 = 12 文档
- 大模型与智能体：前言 + 17 章 + 索引 = 18 文档 / 4 个目录（共用基础/大模型/智能体/边界与未来）

## 验收（六查全绿）

TOC==本地、全路径唯一、对账错位 0、幽灵 0、**全库 word_count>0**、附件 md5 对（v2 实拉 200 application/pdf 且 md5 一致）。
根级顺序：v2 六轮收敛（4 根级 DOC 归位 + 第二/第三部分换序）、llm-agent 三轮；通识版/案例与实践天然正确。

## 坑小结

1. **根级 TITLE 会按 Unicode 字典序排**：`第一部分/第三部分/第二部分/附录` 的码点为 一<三<二<附 → toc-md 出来的顺序是「一、三、二、附」。**文件/目录名要带 `NN-` 数字前缀**才能定序；已经在库里的用 `fix_order.py` 逐发 `prependNode/sibling` 换回来（一次只挪一个节点，回读校验、循环收敛）。
2. **站上无正文**：nndl.ai 是落地页站（`nndl/nndl.github.io`，Jekyll），书稿 LaTeX 源**不公开**，正文只能吃 release PDF。别去爬 HTML。
3. 边注/公式/矢量图文字会混进正文（PDF 文本层客观限制）；公式以 **PDF 原件附件**兜底。