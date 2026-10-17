# 《Mac 开发配置手册》抓取器（GitBook 2.x 静态站，2026-10-17）

源：`https://aaaaaashu.gitbooks.io/mac-dev-setup/content/`（老 gitbooks.io **仍在线**，GitBook 2.6.7 生成的静态 HTML）
作者：阿树（意译自 Sourabh Bajaj 的 Mac OS X Setup Guide）｜ 无源仓库（GitHub 上 `aaaaaashu/mac-dev-setup` 不存在）

## 站点特征

- 每页一个 HTML（`index.html`、`SystemPreferences/index.html`、`Homebrew/Usage.html` …），侧栏 `ul.summary` 给出**站点目录顺序**
- **正文容器 = `section.normal`**（GitBook 2.x 标准）——上一页/下一页导航是 `div.book-body > div.navigation*`，在正文容器**之外**，天然不会被抓进来
- 无 `.md` / `SUMMARY.md`（401），只能抓 HTML
- 图片：本手册无站内图片；正文只有两张**外链图**（`orangehat.u.qiniudn.com` 七牛测试域名，已 404）+ 若干外链文章

## 复用步骤

1. 改 `crawl.py` 顶部 `BASE` / `PAGES` / `OUT` / `IMG_MAP_FILE`
2. `PAGES` 顺序 = 侧栏目录顺序（用 `NN-标题.md` 命名；本站 13 页平铺）
3. `python3 crawl.py` → `site/*.md`
4. 产物级验证（grep 导航词/残留标签/`index.html`/尾部抽查）
5. `yuque_repo_import.py create-book`（网站口径：库名带日期、slug 带日期、分组「文章收集」36149506）+ `move-stack` + `yuque_tree_import.py --toc-md`

## 两个关键点（都实踩）

1. **嵌套列表必须脱离 render 主循环**：`render()` 的主循环里没有 `li` 分支，若在 ul 分支里用 `render(child_ul)` 递归，那么 `render(ul)` 会去遍历 `ul.children`（全是 `li`）→ 每个 `li` 掉进 `else` 分支 → 变成「无前缀的裸文本 + 子项前缀错位」。正确做法：`render_list()` 独立递归（本文件已实现），`render()` 的 `ul/ol` 分支只调它。
2. **`inline()` 必须先跳过块级子节点**（`ul/ol/table/pre/blockquote`），否则 `inline(li)` 会把子列表文本拼进父项 → 同一内容出现两遍。

## 成品

库 id `84683312`「Mac 开发配置手册（2026-10-17）」slug `mac-dev-setup-20261017`，13 节点平铺，四查全绿（13 篇逐字符等长）。
