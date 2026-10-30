# examples/bootstrap4-zh — Bootstrap 4 繁體中文手冊（六角學院）

fpb52 #120 · 库 85155154 · hexschool/bootstrap_zh @ 71e66c0 (分支 **zh-tw-dev**) · 2026-10-31

站点 `bootstrap.hexschool.com`（**Jekyll v3.8.5**）。默认分支 `gh-pages` 只有渲染后的 HTML；
**md 源在 `zh-tw-dev` 分支的 `site/docs/4.2/`**（→ clone zh-tw-dev 而非默认分支）。
- 用自带极简 Liquid 引擎（`liquid.py`）展开 `include / capture / highlight / for / if` 子集：
  - `{% capture e %}…{% endcapture %}{% include example.html content=e %}` → ```html 代码块（丢弃预览）
  - `{% include callout.html content=… type=… %}` → `> **Note/警告/危險**` 引用块；`{% include callout-*.md %}` 递归展开
  - `{% for x in site.data.Y %}` 读 `site/_data/*.yml`；`{% include icons/placeholder.svg %}` → `<img src="..." alt="...">`
- 结构按 `site/_data/nav.yml` 分组成 TITLE（中文组名），篇名取 front matter `title`，组内序号按 nav 顺序。
- 后处理：剥 Kramdown `{#anchor}`/`{:[…]}`、`]((url))` 双括号、`<div class="bd-example…">` 预览包裹；图 `/docs/4.2/assets/*` → `../assets/*`（子目录文档）+ 本地化传 CDN。
- ⚠️ **子目录文档的图必须写 `../assets/`**（rewrite 按 md 所在目录解析）。
- ⚠️ 根级 TITLE 按 Unicode 排（元件/內容/快速開始…）→ 收尾用 `prependNode/sibling` 5 发归位成「00-說明 → 快速開始 → 排版 → 內容 → 元件 → 通用類別 → 擴增 → 關於 → 90/91」。
- `--dry` 报的 84 处「本地缺失」全是代码样例里的 `<img src="..." alt="...">` 占位符，非真缺图。

结果：79 节点（7 目录/72 文档），3 图 CDN（7 处引用）；六查全绿（word_count 72/72>0 / 回读 0 异常 / 根序归位）。
