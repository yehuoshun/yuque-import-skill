# 双轨导入：书 PDF + 课件 + 代码 型仓库 → 语雀

2026-10-21 首例（两本 LLM 中文书，同一套脚本跑两库）：
- **RUC《大语言模型》**（赵鑫等）← `LLMBook-zh/LLMBook-zh.github.io @ 7be1a80` → 库 `84818579`
  - 全书 PDF 391 页（书签 224 条）+ 24 份课件 PDF + `code/` 23 个 .py + README
- **复旦《大规模语言模型：从理论到实践》**（张奇等）← `intro-llm/intro-llm.github.io @ ba94fed` → 库 `84818580`
  - `chapter/` 两版全书 PDF（21MB / 56MB）+ `slides/` 8 个 pptx + `code/ch5/`（DeepSpeed-Chat）+ 站点脚手架

## 口径（老板 2026-10-21 拍板）

**双轨**：正文从 PDF 抽成**逐章可读文档**，**同时**把 PDF 原件走 `type=attachment` 附件。
- `01-正文/`：PyMuPDF 按 PDF **书签（outline）** 重建 —— 层级 1=部分（ruc）/ 章（fudan）→ 目录，章 → 一篇文档；节/小节 → `##` / `###` 标题（**用书签标题做锚，正文行文本归一化后与书签标题相等即判为标题**，比字号启发式稳）。
- `02-代码/`：原仓库 `code/`（文本文件原样进库）。
- `03-课件/`：课件 PDF → 附件文档；**PPTX 不上传**（硬规则 12 只给 PDF），只留「未上传」说明 + GitHub 直链。
- `04-原件（全书 PDF）/`：fudan 的两版全书 PDF；ruc 全书 PDF 在根级 `00-全书 PDF（原件）.md`。
- 站点脚手架（`css/ js/ fonts/ images/ index.html` 封面图 `assets/`）不入库；图跳过（矢量图文字会混入正文，属已知噪声）。

## 流程（build_lib.py 一条龙）

```bash
# 1) 配置：改 build_lib.py 里 LIBS 的 book/src/out/progress/keep/rename/drop/book_pdf/extract
# 2) 构建：硬链接整树 → 删脚手架 → 抽正文 → 上传 PDF 附件 + 预建附件文档 + 写账本
cd ~/.openclaw/workspace/tmp/llmbooks
python3 build_lib.py <lib>            # 用 exec background=true 跑（大 PDF 上传慢）
# 3) 导入（toc-md）
python3 ~/.openclaw/workspace/code/yuque-import-skill/scripts/yuque_tree_import.py \
  --root <out> --book <id> --progress <prog>.json --toc-md
# 4) 对账 + 六查（含全库占位扫描）
python3 scripts/yuque_toc_reconcile.py --root <out> --book <id> --progress <prog>.json
python3 scripts/yuque_check_ghosts.py --book <id>
```

## 关键设计点（踩过的都在这）

1. **附件文档 = 预建 + 账本注入**：toc-md 生成目录树时按本地文件+账本拼（`build_toc_md` 取 `node["segments"][*]["title"]`）。所以 PDF 文档可以**先用 API 建好（标题=原文件名，正文=附件链接），把 `{rel: {doc_id,slug,segments}}` 写进账本**，`tree_import` 就会 skip 它、只按磁盘形状拼目录 —— 标题能保持 `xxx.pdf`（不是 `xxx.pdf.md`）。
2. **★ 剥 C0 控制符（坑 50）**：PyMuPDF 抽的正文会带 `\x00`/`\x01` 公式残渣；不剥则整篇被导入器判成二进制 → 写占位、`word_count=0`（本次 RUC 3/15、fudan 2/12 篇中招）。`_clean()` 里 `re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)`（留 `\t\n\r`）。
3. **页眉页脚按书标定**：ruc 页眉 `y1<50`、页码 `y0>665`；fudan 页眉（书名+页码）`y0<74`、无页脚。写进 `extract` 配置。
4. **段落判定用缩进**：正文续行 `x0≈57`，段首/项目符 `x0≈78`（LaTeX 首行缩进）→ `x0 > base+6` 起新段；CJK 相接不加空格、否则加空格。
5. **图内孤立短标签**：连续 ≥3 行「无中文、≤14 字、无句末标点」→ 整块丢弃（矢量图文字泄漏，OSTEP 同款噪声）。
6. **章标题去重 + 排序**：正文里重复出现的章标题行丢掉；文件名 `NN-章标题.md` 保证语雀目录按 `sorted()` 得正序（否则「第一章/第三章/第二章」乱序）。
7. **PPTX 按硬规则 12 不上传**：建「未上传」说明文档，正文给 `repo/blob/main/<原路径>` 直链。

## 六查结果（本次两库全绿）

| 项 | ruc | fudan |
|---|---|---|
| TOC == 本地 | 81 == 81 | 133 == 133 |
| 全路径唯一 | ✅ | ✅ |
| 对账错位 | 0 | 0 |
| 幽灵 | 0（64==64） | 0（92==92） |
| 全库 word_count>0 | ✅（修 3 篇占位后） | ✅（修 2 篇占位后） |
| 附件 md5 抽查 | 2/2 对（含 10.8MB 全书） | 2/2 对（21MB + 56MB） |

toc-md PUT：ruc 秒级 / fudan 1.5s；两库均 0 失败、0 429、无分片。