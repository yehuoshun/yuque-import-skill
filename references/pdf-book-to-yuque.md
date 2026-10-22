# PDF 书 → 语雀 SOP（2026-10-18 固化，首例 OSTEP）

> 触发模板：「把这本 PDF 书/这个官方文档站（只有 PDF）导入语雀」。
> 首例：OSTEP《Operating Systems: Three Easy Pieces》68 章 → 库 `84683427`。
> 完整实战记录 + 排版识别表 + 8 条坑：**`examples/ostep-pdf/README.md`**（必读），脚本 `examples/ostep-pdf/{fetch_ostep,extract_ostep}.py`。
>
> ⭐ **默认口径（2026-10-18 老板拍板）：PDF 导入 =「原版 + 解析」双轨** —— 解析正文照旧导库，**同时把 PDF 原件上传语雀附件**，以根级 `00-PDF 原件.md` 挂同一库（正文可读 + 原件可下）。做法见 §五，默认执行、不必再问。
> 二次导入可参考完整双轨样例 `examples/scalability-pdf/`（《走向分布式》，含提取脚本 + README）。

## 一、先确认是不是真没别的源（顺序不能反）

1. 站点有没有 HTML 版？`curl -I <chapter>.html` → 404 就是没有（OSTEP 实测）
2. 有没有官方/译者源仓库？GitHub `remzi-arpacidusseau/*` 只有 code/homework/projects/translations，**书稿源不公开**
3. 都没有 → 走 PDF 提取（**先跟老板确认两件事**：图要不要抠 / 要不要交子 agent）；**PDF 原件附件按默认口径必传**（§五），不用问

## 二、流程

1. **清单**：站点目录表 → 手工整理 `plan.json`（`part` 分部 / `num` 章号 / `title` / `pdf` / `out` 输出名）
2. **下载**：并发 6 线程、幂等跳过（`fetch.py`，68 个 PDF ≈ 2 分钟）
3. **提取**：PyMuPDF `get_text("dict")` → 按字号/字体/缩进重建 `#/##/代码块/引用块/段落`（`extract.py`）
3.5 **PDF 原件附件（默认，§五）**：`type=attachment` 上传 → 取响应 `url` 字段 → 建根级 `00-PDF 原件.md` 挂进导入树，与解析正文同库同行
4. **建库**：只有 PDF 的官方站 → **网站口径**（库名+slug 带日期，分组「文章收集」36149506）；有 repo 的走开源项目口径
5. **导入**：`yuque_tree_import.py --toc-md`（分部目录 = 7 个 TITLE）
6. **四查**：TOC == 本地 == docs、全路径唯一、**每篇逐字符回读比对**、reconcile 0 错位

## 三、共同的硬骨头

- **断词**：TeX 断词（"infor-mally"）vs 真复合词（"space-shared"）——用 `words_alpha.txt` 词表判「双侧都是完整词才保留连字符」
- **矢量图文字混入正文**：`get_images()` 为 0 说明图是矢量绘制，图内标签（`Running`/`0`/`20`/`A`）在文本层 → 丢弃 1–3 字符孤立短段落做轻量清理；图本身跳过（老板拍板口径）
- **页眉页脚阈值按实测调**：OSTEP 页眉 y≈64、页码 y≈574（H=648）→ `top<75` / `bot>H-78`
- **空 span 不能过滤**（`if s["text"]` 而非 `.strip()`），否则词间空格全丢
- **相邻同类强调跨行合并**（`**time** **sharing**` → `**time sharing**`）
- **跨页续段**：上一行无句末标点即续接，别按 x 变化断

## 五、PDF 原件附件直传（2026-10-18 双轨实战《走向分布式》84706243 补）

老板口径：**提取照旧，PDF 本体也额外传上去**（正文可读 + 原件可下，双轨并行）。

1. 上传走 `type=attachment`（样例见 `yuque_rewrite_images.py` 的 attachment 上传路径）：返回 JSON 里**取 `url` 字段**（`https://www.yuque.com/attachments/yuque/0/2026/pdf/<uid>/<ts>-<uuid>.pdf`，会话门控：带 cookie 才 200，无会话 302 到登录）
2. **坑：用 filekey 拼 `cdn.nlark.com/yuque/0/2026/pdf/...` 是 403 死路**（PDF 类型 attachment 走代理路径，不公开直链）——一切以 `url` 字段为准
3. 建一棵根级文档 `00-PDF 原件.md`：`# 标题（PDF 原件）` + 元信息（书名/译者/版本/页数/整理人）+ `📎 [xxx.pdf（410KB）](<url 字段>)` + 源站链接；`--toc-md` 下根级 DOC 排最前，无需归位（有 TITLE 目录时才要 prependNode，坑 35）
4. 验收：GET 该文档 body 含 `yuque.com/attachments/` URL；带 cookie `curl -L` 实拉 200 + `application/pdf` + 与源文件 md5 一致
5. 备注：提取与附件可并行——正文 30 篇拆篇照常导，附件只挂在 00 号文档上，互不干扰

## 四、产物验证（别只看日志）

```bash
grep -c '^```' 输出/*.md            # 代码围栏成对
python3 -c "...逐篇回读比对..."      # 逐字符等长（verify.py 模板见 tmp/ostep/verify.py）
grep -nE '^[0-9]{1,3}$' 输出/*.md    # 页码/图标签残留抽查
```

## 六、LaTeX 中文教材 · 多本一套（2026-10-22 蒲公英书系列）

**触发**：站点只有落地页、正文是 LaTeX 排版的出版前电子稿 PDF（`nndl.ai` 系列 4 本）。复用脚本 + README：`examples/nndl-pdf-series/`（`extract.py` + `build.py` + `fix_order.py`）。

要点（相对 OSTEP 的新增）：
1. **标题用书签文本锚定**（`heading_bytext`）：节号与标题常**同 y 拆成两行**（`1.1.1` 用 `LMRoman12-Bold`、标题用 `FZHTJW`）→ `page_lines()` 里做同 y 行合并；**附录节号带字母**（`A.1`/`A.1.1`）→ 正则要 `[A-Z]?\.?\d+(\.\d+)*`。
2. **右侧边注栏**（`FZKTJW`，x0≈411）与公式编号 `(3.32)` 用 `margin_x` 分流：边注 → `> 📝` 引用块（**逐行 CJK 相接不加空格**）；**单栏书（通识版）把 `margin_x` 设成极大值关掉**。
3. **代码行 → 围栏代码块**：LabTaX `listings` 的代码是等宽行、行号另起一行（纯数字）→ 数字行已被「裸页码」过滤丢掉，等宽行攒成 ``` 代码块（缩进 = `round((x0-code_base)/(size*0.5))` 再整块 dedent）。**不做会把代码注释 `# xxx` 当 H1，大纲炸掉**。
4. **页眉 y1<58 / 页脚 y0>640**（四本一致）；大字号 ≥14.5pt = 章/部分标题（丢，书签已生成 `#`）。
5. **同一套源多本书 → 分开建库**（老板 2026-10-22 拍板；网站口径 / 分组「文章收集」）。
6. ⚠️ **根级 TITLE 按 Unicode 字典序排**：`第一部分/第三部分/第二部分/附录` → 一<三<二<附，出来的顺序就是「一、三、二、附」→ 目录名要带 `NN-` 数字前缀；已在库里的用 `fix_order.py` 逐发 `prependNode/sibling` 换回（一次挪一个，回读校验循环收敛）。根级 DOC 仍会落到 TITLE 之后（老坑 29），同脚本一并归位。