# 网站抓取 → 语雀导入 SOP（2026-10-13 固化）

> 触发模板：「把 <网址> 抓取到语雀」「这个网站教程导到语雀」。
> 实战源（按时间）：gitref（content_box 容器）、Nulab（Gatsby page-data + 图片抠图）、
> Git Magic（DocBook content div）、廖雪峰（Tailwind 站，评论区 JS 带偏窗口事故）、
> 看云 kancloud（SEO 副本直出 md 源码）、Pro Git gitbooks.io（GitBook3 + asciidoc 实体转义）、
> SVN Book（DocBook XSL 多页站，bs4 渲染器）。
> 通用爬虫模板：`scripts/yuque_website_crawl.py`（复制到 tmp/<站点>/crawl.py，改 SITE 配置区）。

## 一、流程（六步）

1. **探站**：curl 首页 → 找章节链接全集（侧边栏目录）+ 正文容器特征（id/class）+ 结束标记
   ```bash
   curl -sL <url> -A "Mozilla/5.0" -o probe.html && grep -oE 'href="[^"]*"' probe.html | sort -u
   ```
2. **复制模板 + 填 SITE 配置**：pages（顺序=目录顺序，命名 `NN-标题.md`）、nav_end_marker / content_start / content_end_re
3. **抓取**：`python3 crawl.py` → site/*.md；图片自动下载传语雀 CDN（img_map.json 缓存防重传）
4. **产物级验证（必做，别只看日志）**：
   ```bash
   grep -l "导航特征词" site/*.md                    # 导航污染 = 0
   grep -lE "<[a-z]+" site/*.md                       # 残留标签(排除代码样例)
   grep -o "index.html" site/*.md | wc -l             # 站内链接残留 = 0
   tail -3 site/*.md                                  # 尾部抽查(模板尾巴/导航链接)
   grep -c '${' site/*.md                              # JS 模板尾巴 = 0
   for f in site/*.md; do tail -2 "$f"; done          # 尾部全量扫(2026-10-13 老板抓包: 底部面包屑导航只在尾部, 前四项抓不到)
   grep -lE '上一页|下一页|»|目录|导航' site/*.md        # 导航特征词(含尾部) = 0
   ```
5. **建库 + 移分组 + 导入**（命名规范 2026-10-14 老板固化：库名=`网站名（日期）`，slug=`网站名-YYYYMMDD`（URL 也带日期，已建库不追改），分组=「文章收集」36149506，描述带源站 URL；走 `yuque_repo_import.py` create-book/move-stack + `yuque_tree_import.py`）
6. **验收四查**：TOC 数==本地 / 错位 0 / 幽灵文档 0 / 深层抽查；含中文必查 word_count==0（v1.1.5 已单篇内置）

## 二、正文窗口定位（血泪方法论，逐条遵守）

1. **先剥 `<script>/<style>/<link>/<!-- -->`，再定位窗口**——评论区 JS 里的字符串
   （`'comment-form'`、`${user_name}`）会带偏窗口定位，正文被拦腰截断（廖雪峰实踩，第一版 34 篇全断）
2. **窗口终点用【标签形式】标记**：`<div class="comment-form"` 正则，禁止 `find("comment-form")` 裸字符串
3. 窗口起点 = 导航/侧边栏最后一个条目（`rfind(nav_end_marker)`）之后的正文标题（第一个 `<h1`）
4. 后处理三清：作者卡片/社交行（drop_lines_with）、评论模板尾巴 `${...}`（截断到行内 `${`）、
   章节导航纯链接（strip_nav_links，首尾 `^\[..\]\(..\)$` 行）

## 三、图片方案

- 相对路径 `<img src="X">`（排除 data:/http/绝对路径）：下载 → 语雀 CDN（upload_image）→ md 引用 CDN URL
- `img_map.json` 缓存 src→url：重跑/重抓不重复上传（CDN 会留垃圾对象）
- img 正则抓**整标签**再解析 src/alt（只抓 src 时取 alt 会 `no such group` 全站报错）

## 四、爬虫低级坑（都实踩过）

1. **链接重写正则分组**：`\[([^\]]*)\]\(([^)]*)\)` —— group(1)=**链接文字**，group(2)=**URL**。
   用反了 = 全部链接原样返回（日志全绿，产物全没改），必须靠产物级 grep 抓
2. **纯链接行判断**：尾部空行会挡住 `^\[..\]$` 匹配——先 `rstrip()` 再逐行清
3. 站内链接重写：把 `../xxx/index.html` 映射成本库 md 文件名（跨章互链可点）
4. DocBook 站（gitmagic）：`<div class="content">` 起切 + h1-4/pre/p/li/dt/dd 块解析；
   Tailwind 站（廖雪峰）：侧边栏 gsc-index + h1 + comment-form div；Gatsby 站（Nulab）：page-data.json
5. 图片引用基线：`grep -o "!\[" site/*.md | wc -l` 与预期图数对比，少图 = 窗口切错
6. **嵌套 div 不能非贪婪 `(.*?)</div>`**（2026-10-15 Pro Git 实踩）：内层 div 的闭合会把块截断，
   admonitionblock（Note/Tip 提示块）内容整块丢失。解法：**深度计数**——从块起点扫 `<div`+1 / `</div>`-1，
   归零才是真闭合（模板 crawl.py 的 split_divs() 可抄）
7. **递归切分嵌套块时标题二次输出**（Pro Git 实踩）：sect 块 inner 含标题，递归再切时标题走 gap 又输出一次。
   解法：提取标题后 `re.sub(r"<h([1-4])[^>]*>.*?</h\1>", "", inner, count=1)` 从 inner 删掉
8. **交替分支正则的闭合引用必须指向 tag 组**（Mercurial/Pro Git 双踩）：`<(h[1-4]|pre|li)([^>]*)>(.*?)</\2>`
   的 `\2` 引用的是 attrs 组 → h1/pre 全匹配失败。数清分组，闭合引用写 tag 组（`</\3>` 之类）
9. **`(p)` 会匹配 `<pre` 前缀**：p 分支必须写成 `<p(?=[\s>])` 排除 pre（Mercurial 实踩）
10. **HTML4 站 `<p>` 不闭合**（MoinMoin 实踩 23开11闭）：p 匹配 `(.*?)</p>` 会吞掉后面整个 pre/标题。
    解法：p 用块级标签边界 lookahead 截断 `(?=</p>|<h[1-4]\b|<pre\b|<p\b|<ul\b|<table\b|<hr\b|<div\b)`
11. **urllib 请求中文 URL 报 UnicodeEncodeError**（Pro Git 实踩）：unquote 后的 URL 先
    `urllib.parse.quote(url, safe="/:?=&%#")` 再请求；同理 toc 清单若存相对路径，拼 URL 用 `BASE+path`
    别用 `url.replace(BASE, "")`（replace 不生效就 404）
12. **章标题链接 = 该章第一节 URL**（Pro Git 实踩）：书目录里章名链接 href 与第一节相同 → 按 URL 去重，
    文件名用**页标题**（非章名）；章标题带 `A1.`/`附录` 前缀时去编号正则要连字母前缀一起处理
13. **全文 HTML 实体转义**（bingohuang.gitbooks.io Pro Git / 看云 双踩）：静态站把非 ASCII 全转成
    `&#x4E2D;` 形式（中文变实体码），正文正则全匹配不上 → 提取后统一 `html.unescape()` 还原
14. **站点间歇性 401**（gitbooks.io 实踩，页面和图片都中招）：fetch 必须**指数退避重试**（~6 次），
    单次失败不能放弃，否则抓取结果随机缺页/缺图
15. **asciidoc 死链 xref `[_git_branching]`**（Pro Git 实踩 73 处）：Asciidoctor 交叉引用锚
    留在正文成死链 → 抓全站 `<hN id="_xxx">标题` 建映射表替换成中文标题；站点自身坏 id
    （`_email_notification`/`_git_on_the_server`）手工补映射。顺带清 asciidoc 引用对 ``x'' → “x”
16. **SEO 副本站：正文 = 原始 markdown 源码**（看云实踩）：React 站直出 `<div class="seo">`，
    内层 `<div class="content">` 放的是 **md 源码**（实体转义）→ 直接 unescape 落盘，
    不用 HTML→md 转换器；`<div class="catalog"><ul>` 直接给全站目录（每页都有，顺序即目录序）
17. **图片防盗链**（看云实踩）：box.kancloud.cn 直连 403，必须带 `Referer: <页面URL>` 才 200；
    爬虫 fetch 统一带 Referer，图片下载同款
18. **DocBook XSL 多页站别用正则**（svnbook 实踩）：嵌套 div 太深 → 直接上 **bs4 递归渲染器**
    （h1-6/p/pre/ul.ol/dl/table/figure/blockquote/admonition/sidebar/footnotes/indexdiv 各一支）
19. **DocBook 的 blockquote/admonition 是 `<table>` 渲染**（svnbook 实踩）：
    `div.warning>table>tr>[td.icon+th][td 内容]` → 当普通表格转会塞进空单元格+图标、quote 里再套表。
    要从 td 抽文本、丢图标格、th 当标签
20. **页内目录 div.toc 的取舍**（svnbook 实踩）：节/章页的内目录是同页锚点 → 丢；
    但分部页/参考手册页正文只有这个目录 → 不处理会得 **1 字节空文档** → 补「**目录**」+ 子文档相对链接回灌
21. **`<a class="indexterm">` 双面性**（svnbook 实踩）：普通页里是空锚点标记（剥），
    索引页里是带文本的真链接（剥了整页索引变「，」）→ 只剥「无 href 且无文本」的
22. **语雀 TOC 根级顺序坑**（svnbook 实踩）：tree_import 先建 TITLE 后建 DOC → 根级 DOC 排到目录之后
    → `PUT /toc {action:prependNode, action_mode:sibling, node_uuid, target_uuid}` 一次归位


## 五、站点案例速查

| 站点 | 窗口起点 | 窗口终点 | 备注 |
|---|---|---|---|
| gitref.justjavac.com | `<div id="content_box"` | 页脚 | 最早 v1 |
| nulab.com（Gatsby） | page-data.json 正文 | 评论区 | 图片抠图按 slug 分目录 |
| blynn gitmagic（DocBook） | `<div class="content">` | navfooter | 全站无表格 |
| liaoxuefeng.com（Tailwind） | 侧边栏后 `<h1` | `<div class="comment-form"` | 必须先剥 script；作者卡片在正文前 |
| snowdream86.gitbooks.io（GitBook 单页） | `<section class="normal" id="section-..."` | `</section>` | 单页书按 h3 切分（2026-10-13） |
| worldhello.net/gotgithub（老版 Sphinx） | `<div class="body"` 后 `<div class="section"` | **`<div class="related"`（底部导航, 不是 footer!）** | 布局=正文→底部导航→footer, 终点选 footer 会混入面包屑（2026-10-13 老板抓包）；图片包在 `<a class="reference internal image-reference">` 里要先剥壳；Sphinx 无 alt 时 alt=src 路径要清洗 |
| zh-hginit.readthedocs.io（新版 ReadTheDocs） | **不爬 HTML**：RTD 项目页（readthedocs.org/projects/<slug>/）有源仓库链接，直接 clone 拿 rst 源 → `yuque_rst_convert.py` 转 md | — | 嵌套多→章=文档平铺（7 篇），小节保留为文档内标题；`:doc:` 跨文档角色剥纯文本；`_images/` 预传 CDN 后从导入根目录删掉（2026-10-15 HgInit 实战） |
| wiki.mercurial-scm.org（MoinMoin 归档, 2026-10-15） | `<div dir="ltr" id="content">` 后第一个 `<h1` | `<hr><p class="line874">`（分类尾巴前, 全站统一） | **p 标签不闭合**(HTML4 省略 </p>, 23开11闭)→p 用块级标签 lookahead 截断；行号锚点 `<span class="anchor" id="line-N">` 剥标签即净；页面自带目录块 `<div class="table-of-contents">` 整块删；附件 URL 带 `&amp;` 要先 decode 再下载 |
| git-scm.com/book/zh（Asciidoctor, 2026-10-15） | `<div id="main"` 剥开标签后 | `<div id="nav">`（prev|next 翻页导航） | 块语义 div：paragraph/sect1-4/listingblock/imageblock/admonitionblock/tableblock；**嵌套 div 必须深度计数找闭合**(非贪婪 </div> 截断内层→admonition 内容丢)；**章级标题 h2 是裸标签**混在无 class 引言 div 里(re.search 找)；admonition class 是双类 `admonitionblock note` 要包含匹配；递归切分嵌套块时标题会二次输出(提取后从 inner 删)；章标题链接 href=该章第一节 URL 要按 URL 去重；**中文 URL 请求前先 quote** |
| bingohuang.gitbooks.io/progit2（GitBook 3 + Asciidoctor, 2026-10-15） | `<section class="normal markdown-section">` | `</section>`（每页唯一） | 正文容器 markdown-section；**全文非 ASCII 实体转义**(&#x4E2D;)→h.unescape 还原；侧边栏 `ul.summary` 的 li.chapter[data-level/data-path] 直接给全树；图片相对路径 `../images/` 按页面 URL 解析；**gitbooks.io 间歇 401**→fetch 指数退避 6 次；正文块仍是 Asciidoctor div(sect2-4/listingblock/imageblock)；xref 死链 `[_xxx]` 按全站 `<hN id>` 映射换中文标题 |
| svnbook.red-bean.com/nightly/zh（DocBook XSL 多页站, 2026-10-15） | `div.navheader` 之后 | `div.navfooter`（前一页/下一页/上一级） | 每章/节/命令手册各自成页；分部页正文只有小节目录(补「**目录**」+相对链接防空文档)；blockquote/admonition 是 `<table>` 渲染(抽 td 文本、丢图标、th 当标签)；`<a class="indexterm">` 只剥无 href 无文本的(索引页里是真链接)；正文首标题去掉但 titlepage 作者/日期要留；bs4 递归渲染器替代正则；**抓取 ~12min/导入 ~10min 长任务先报 ETA** |
| kancloud.cn/kancloud/<book>（看云 SEO 副本, 2026-10-15） | `<div class="seo">` 内 `<div class="content">`（=原始 md 源码, 实体转义） | `</div><div class="catalog">`（全站目录, 每页都有） | 不用 HTML→md：unescape 即落盘；`catalog` 顺序=目录序、页面 URL=`/kancloud/<book>/<数字id>`；**box.kancloud.cn 防盗链**→带 Referer 才 200；书站类库名用书名(slug 仍带日期, 如 intro-to-prog-20261015) |
