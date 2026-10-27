# LaTeX2HTML 多页静态站 → 语雀（2026-10-28）

**首例**：`https://c-faq-chn.sourceforge.net/ccfaq/ccfaq.html`（《C 语言常见问题集》中译本 0.9.4，2005-06-23，Steve Summit 原著 / 朱群英·孙云 译）
→ 库 **85036448**（`C 语言常见问题集（2026-10-28）`，slug `c-faq-chn-20261028`，分组「文章收集」待补），387 节点（20 目录 / 367 文档），六查全绿。

## 适用形态

老 texinfo/LaTeX 书用 **LaTeX2HTML 2002-2-1** 出的静态站：`node1.html … nodeN.html` 平铺，每页 =
导航面板 + `<H1>` 标题 + 正文，目录页 `index/ccfaq.html` ≈ 全站 TOC。特征：`<SPAN CLASS="arabic">` 拼数字、`&nbsp;` 密布、`CLASS="ChildLinks"` 子链接块、GBK 编码。

## 流程

```bash
python3 fetch.py     # 按 toc.json 并发 curl 拉全部 node*.html（改 BASE/TOK 常量）
python3 build.py     # converter.py 转 md + 按 TOC 建树
python3 scripts/yuque_rewrite_images.py <clean> img_map.json --cookie-config <cfg>
rm -rf <clean>/imgs
python3 scripts/yuque_repo_import.py create-book --name "书名（<日期>）" --slug <slug> --desc "来源：<URL> ｜ 网站口径 …"
python3 scripts/yuque_tree_import.py --root <clean> --book <id> --progress <p> --toc-md
```

## 坑（照抄别漏）

1. **WAF 认 UA**：`User-Agent: Mozilla/5.0` 一律 **403**，`curl/x.y`（curl 默认）放行 → 抓取统一用 `curl`（脚本里就是 subprocess curl），别用 urllib 裸请求。
2. **编码硬编码 GBK**（`<META charset=GBK>`）：`utf-8` 解码会静默乱码 → `decode('gb18030','ignore')`。
3. **正文切片**：从 `End of Navigation Panel` 之后的 `-->` 起、到**最后一个** `<DIV CLASS="navigation">` 止；`rfind` 不能写成 `find`（页尾还有 prev/next 面板）。
4. **首个标题要丢**：标题已由文件名提供，`<H1>`/`<H2>`（文献页是 H2）重复 → 只丢**第一个**标题块。
5. **`CLASS="ChildLinks"` 的 `<UL>` 必须整块跳过**：那是「本章问题清单」，留着就是一堆重复目录。
6. **章节页只有子链接**（无正文）→ **不建 00-导读文档**，只建 TITLE 目录；反之「前言/感谢/文献」这类无子节的章 → 落成根级文档。
7. **`<DT>`/`<DD>` 常无闭合标签**（`<DT><A>x</A> <DD>正文`）→ 用「遇到 `<DD>` 就收尾 `<DT>`」的隐式闭合逻辑，靠 endtag 会全丢。
8. **`<PRE>` 要独立缓冲**，别进行缓冲（行缓冲会把换行压成空格，代码全糊）；收尾按公共缩进去缩进。
9. **`<BR>` 在标题里要忽略**（`<H2>…<BR> 文献 </H2>` 否则标题被拆两行）。
10. **中文换行拼接**：段落内源码按 ~70 列换行，拼行时中文字符之间的空格要吃掉（`(?<=[CJK])\s+(?=[CJK]) → ''`），否则「不能放 入」。
11. **表格 `DIV ALIGN="CENTER"` 包 `<TABLE>`** → 转 md 表格即可（本例 4 页有表）；空单元格保留。
12. **短页是上游真短**（如「参见第 17 章。」），不是转换丢内容 → 回读一致即可，别去补。
13. **根级 DOC 落后**（坑 29）：本次 1 发 `prependNode`（`01-前言` → `02-…` 目录）。
