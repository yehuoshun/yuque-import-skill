# PDF 书 → 语雀（首例：OSTEP《Operating Systems: Three Easy Pieces》，2026-10-18）

源：`https://pages.cs.wisc.edu/~remzi/OSTEP/`（官网只有 **68 个章节 PDF**，无 HTML、无公开书稿源；Version 1.10 / 2023-11）
成品：库 id `84683427`「Operating Systems - Three Easy Pieces（2026-10-18）」slug `ostep-20261018`，
7 个分部目录 + 68 篇 = 75 节点，分组「文章收集」，四查全绿（68 篇逐字符等长）。

## 流程（六步）

1. **探源**：确认有没有 HTML/md 源。OSTEP 没有 → 只能吃 PDF（`curl -I xxx.html` 一律 404，`.pdf` 200）
2. **章节清单**：主页的目录表是 `<table>`（6 列 = 6 个分部），手工/解析成 `plan.json`（part / num / title / pdf / out）
3. **下载**：`fetch_ostep.py`（`ThreadPoolExecutor(6)`，幂等跳过已下载）
4. **PDF → md**：`extract_ostep.py`（PyMuPDF `get_text("dict")`，按字号/字体/缩进重建结构）
5. **建库导入**：网站口径（库名+slug 带日期 / 分组「文章收集」36149506）+ `yuque_tree_import.py --toc-md`
6. **四查** + `yuque_toc_reconcile.py`（这次 68 篇全部逐字符回读比对）

## 排版识别规则（OSTEP v1.10 实测）

| 元素 | 特征 | 处理 |
|---|---|---|
| 正文 | `URWPalladioL-Roma` 9.0pt | 段落（首行缩进 x≈70 / 续行 x≈58 → **用相邻行 x 比较判断段界**） |
| 粗体/斜体/行内 code | `-Bold` / `-Ital` / `NimbusMonL-Regu` | `**x**` / `*x*` / `` `x` `` |
| 小节标题 | 10.9pt | `## 4.1 …` |
| 章标题页 | 章号 20.7pt + 标题 14.3pt | 章号丢弃（纯数字+居中），标题 → `# ` |
| 代码块 | 连续等宽行 | ``` 围栏 |
| CRUX / TIP 框 | 居中（x>118）+ 全大写 | `> **THE CRUX OF THE PROBLEM …**` |
| 页眉/页码 | y<75 或 y>H-78；短数字常见于 x>140 | 丢弃 |
| 图注 | 斜体 `Figure x.y: …` | 保留为文字 |

## 踩过的坑（都实锤）

1. **断词 vs 复合词**（最花时间）：OSTEP 用 "infor-mally" 这类 TeX 断词，也有 "space-shared"/"time-sharing"/"page-table" 这类真复合词 ——
   一刀切删连字符会得到 `spaceshared`（错词），一刀切保留会得到 `infor-mally`（脏）。
   解法：**双侧片段都是完整英文词才保留连字符**（查 `words_alpha.txt` 词表，`len(left)>=3` 防 "as-signed" 误判），否则删连字符拼接。
   词表：`https://gh-proxy.com/https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt`（4MB / 37 万词）
2. **pyproject 装不上别硬刚**：沙箱里 `pip install pyspellchecker` 失败（site-packages 有残留损坏 dist）→ 直接下词表文件最省事
3. **矢量图的文字会混进正文**：OSTEP 的图是矢量绘制（`get_images()` 返回 0），图内标签（`Running`/`0`/`20`/`A`）全在文本层 →
   老板拍板**跳过图**，代价是零散标签混入。轻量清理：丢弃 1–3 字符的孤立短段落 + 剥图注行前缀（`^[A-Z] (?=Figure )`）
4. **浮动框打断跨页段落**：TIP/CRUX 框插在正文中时，PDF 文本顺序会把它排在正文之前（"a context" → 框 → "switch"），
   段落被切成两半。无版面分析能力时接受（少量段落首词丢失）
5. **页眉 y≈64**（不是 40）：阈值取 y<75 才拦得住；页码在 y≈574 / H=648 → 阈值 H-78
6. **`get_text("dict")` 的 span 过滤**：不要丢空 span（`if s["text"].strip()` 会吃掉词间空格 → "THE CRUXOFTHE"），
   改成 `if s["text"]`，渲染时再处理
7. **相邻同类强调要合并**：PDF 把 "time sharing" 拆成两个 Bold span → `**time** **sharing**`，
   段落级跑几轮 `re.sub(r"\*\*([^*]+)\*\*\s*\*\*([^*]+)\*\*", ...)` 合并（跨行也要）
8. **跨页续段**：`N.page != cur.page` 且上一行**没有句末标点**时视为续接（否则 x 变化会把段落切断）

## 复用

改 `plan.json` 的章节清单即可用于别的 PDF 书；排版差异大的书要调字号阈值（`size >= 13` / `>= 10.3`）与页眉页脚阈值。