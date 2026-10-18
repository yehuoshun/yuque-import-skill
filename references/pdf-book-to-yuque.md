# PDF 书 → 语雀 SOP（2026-10-18 固化，首例 OSTEP）

> 触发模板：「把这本 PDF 书/这个官方文档站（只有 PDF）导入语雀」。
> 首例：OSTEP《Operating Systems: Three Easy Pieces》68 章 → 库 `84683427`。
> 完整实战记录 + 排版识别表 + 8 条坑：**`examples/ostep-pdf/README.md`**（必读），脚本 `examples/ostep-pdf/{fetch_ostep,extract_ostep}.py`。

## 一、先确认是不是真没别的源（顺序不能反）

1. 站点有没有 HTML 版？`curl -I <chapter>.html` → 404 就是没有（OSTEP 实测）
2. 有没有官方/译者源仓库？GitHub `remzi-arpacidusseau/*` 只有 code/homework/projects/translations，**书稿源不公开**
3. 都没有 → 走 PDF 提取（**先跟老板确认两件事**：图要不要抠 / 要不要交子 agent）

## 二、流程

1. **清单**：站点目录表 → 手工整理 `plan.json`（`part` 分部 / `num` 章号 / `title` / `pdf` / `out` 输出名）
2. **下载**：并发 6 线程、幂等跳过（`fetch.py`，68 个 PDF ≈ 2 分钟）
3. **提取**：PyMuPDF `get_text("dict")` → 按字号/字体/缩进重建 `#/##/代码块/引用块/段落`（`extract.py`）
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