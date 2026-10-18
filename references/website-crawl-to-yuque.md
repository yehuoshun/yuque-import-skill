# 网站抓取 → 语雀导入 SOP（2026-10-13 固化）

> 触发模板：「把 <网址> 抓取到语雀」「这个网站教程导到语雀」。
> 实战源（按时间）：gitref（content_box 容器）、Nulab（Gatsby page-data + 图片抠图）、
> Git Magic（DocBook content div）、廖雪峰（Tailwind 站，评论区 JS 带偏窗口事故）、
> 看云 kancloud（SEO 副本直出 md 源码）、Pro Git gitbooks.io（GitBook3 + asciidoc 实体转义）、
> SVN Book（DocBook XSL 多页站，bs4 渲染器）、cn.linux.vbird.org/linux_server（老式 PHP 表格站，2026-10-16）、
> cn.linux.vbird.org/linux_basic（同站基础学习篇，复用同一转换器，2026-10-16）、
> docs.freebsd.org/zh-cn/books/handbook（FreeBSD 官方文档站，Asciidoctor/Hugo，2026-10-17）、
> jinbuguo.com/lfs/lfs62（LFS 6.2 中文版，DocBook XSL 老多页站 + GitHub 镜像，2026-10-17）。
> 通用爬虫模板：`scripts/yuque_website_crawl.py`（正则/窗口式，复制到 tmp/<站点>/crawl.py 改 SITE 配置区）；DOM 规整的站（GitBook/Asciidoctor/Hugo）用 bs4 递归渲染更稳，可抄 `examples/freebsd-handbook/`、`examples/mac-dev-setup/`。

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
5. **建库 + 移分组 + 导入**（命名规范 2026-10-14 老板固化：库名=`网站名（日期）`，slug=`网站名-YYYYMMDD`（URL 也带日期，已建库不追改），分组=「文章收集」36149506，描述**必须标注来源（硬规则 11，2026-10-18）**：`来源：<源站 URL> ｜ <站点/作者说明> ｜ 导入 <日期>`；走 `yuque_repo_import.py` create-book/move-stack + `yuque_tree_import.py`）
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
23. **老站「整章全文页」与「分页」并存 → 只导一种**（vbird 服务器架设篇实踩 2026-10-16）：
    每章有 `NNNNname.php`（整章）与 `NNNNname_1.._N.php`（分页）两套，标题/章名完全相同。
    实测全文页文本长度 ≈ 分页拼接之和（本站 21/22 章比值 1.01~1.06）→ **连分页一起导会让整库内容翻倍重复**。
    动手前先抽 1~2 章做「全文页 vs Σ分页」长度比对，比值≈1 就只导全文页；分页文件用 `_\d+\.php$` 排除。
24. **装饰性图标必须按 alt 剔除**（vbird 实踩）：每级标题前都挂 `<img src="../../image/logo.png" alt="大标题的图示|小标题的图示">`（本站 596 张），
    另有人物头像 `鸟哥的图示`。不剔则每篇多几百个占位/噪声图（且全部白传 CDN）。
    剔除后只传正文截图（本站 218 张，逐章图片数可核对：`src 非装饰 img 数 == md 里 ![...] 数`）。
    顺带：顶部 ImageReady 切片导航图墙、页脚版权区靠「正文标记 → 页脚标记」窗口直接跳过，不用逐块识别。
25. **标题不是 h 标签的站，先归一化成 heading 再走块渲染**（vbird 实踩）：正文用 `<span class="text_h1|text_h2">`
    表达 ## / ###（另有 `text_head0` = 章名、`text_history` = 更新日期）；终端输出是 `<table class="term"><td class="term"><pre>`；
    Tips/例题是单格 `<table width="90%">`（单格→递归成块，单段长文本→引用块）。
    直接正则拆 `<p>` 会把「无 `<p>` 的 div（文字 + 表格混排）」整块压成一行 → 用 html.parser 建迷你 DOM 再块渲染更稳。
26. **同站简繁混排 → 简体版另出一篇，不改原篇**（vbird 实踩，老板 2026-10-16 拍板）：
    繁体章的正文标记也是繁体（`本文的檔頭部分`/`連結區`）→ 窗口正则要同时吃「档/檔 头/頭」（`本文的正式部分` 简繁同形）。
    口径：**保留繁体原文 + 额外产出「（简体版）」**。转换器选 **opencc `tw2sp`**（词级正确：設定→设置、透过→通过、资讯→信息、执行绪→线程）；
    `zhconv` 的 `zh-cn` 只做部分词转换（設定→设定、透過→透过），质量不够。
    命名兼容排序：`20-X.md` < `20-X（简体版）.md`（短串在前）→ 顺序自然落在原篇后面。
27. **同站换篇：正文窗口标记不保证一致，要有 fallback**（vbird 基础学习篇实踩 2026-10-16）：
    服务器架设篇每页都有 `<!-- 本文的正式部分 -->`；基础学习篇**附录 A 页只有 `<!-- 本文的档头部分 -->`**（无「正式部分」）→ 窗口起点要
    `find("本文的正式部分")` 失败后 fallback 到 `find("本文的档头部分")`。同站不同篇先全站 grep 一遍标记再动手。
28. **Asciidoctor/Hugo 文档站（DocBook 之后的同门）**（docs.freebsd.org 官方手册实踩 2026-10-17）：
    DOM 与 git-scm.com/book 同族（`div.sect1-4`/`paragraph`/`listingblock`/`literalblock`/`admonitionblock`/
    `imageblock`/`ulist`/`olist`/`dlist`/`exampleblock`/`tableblock`），但**别上正则，直接 bs4 递归渲染器**（同坑 18）。要点：
    - 正文容器 = `main.main-wrapper-book > div.book-content`（页脚 `div.last-modified`/`div.buttons` 在容器外，天然不沾）
    - 页内目录是 `div.toc-mobile`（删）；每页顶部还有一条**站点级公告 admonitionblock**（「This translation may be out of date」）→ 按文字匹配剔
    - admonitionblock 是 `<table><td class=icon><i title=Note></i><td class=content>…</td>` → 取 `td.content` 递归，渲染成 `> **注意**` 引用块（label 按 note/tip/important/warning/caution 映射）
    - 表格标题在 `<caption class=title>`（**在表格元素内**！只收 td/th 会把标题整条丢掉）→ 提到表前一行 `**表 1. …**`
    - **无 `<thead>` 的表**：不处理会渲出空表头行 → 拿**首行数据当表头**
    - `span.filename|guimenuitem|keyseq|parameter` → 行内 code，**取 get_text() 再包**（内层本身是 `<kbd>` → 不然出 `` ``Alt`+`F1`` `` 双层反引号）
    - 站点图片相对路径 `../../../../images/...` 用 `urljoin` 归一到 docs.freebsd.org，直连可下（167 张，无 429 压力）
    - 站内交叉链接（`../disks/#xxx`）→ 纯文字（语雀无相对链接）；`man.freebsd.org` 等外链保留
    - 站点是**多书站**时先从侧边栏 `nav#MenuContents` 取**顶层 ul 的直接 li** = 本书节点全集；**裸正则扫全部 `<li>` 会把各节锚点也当节点**（42 → 342 条误判，实踩）
29. **`--toc-md` 收尾后根级 DOC 仍会排到 TITLE 之后**（FreeBSD 手册实踩 2026-10-17，坑 22 的 toc-md 版）：
    doc 先建（挂根）、TITLE 目录由 toc-md 生成 → 根级 DOC（如「00-前言.md」）落到 5 个目录**之后**。
    收尾补一发 `PUT /toc {action:prependNode, action_mode:sibling, node_uuid:前言, target_uuid:第一部分}` 归位，回读确认。
    排序前缀照旧：根级文档用 `00-`（`0` < 汉字，字典序天然在前），章节 `01-`…；附录用 `A-`/`B-`/`C-`/`D-`。
30. **DocBook 老站的坑二连**（jinbuguo.com/lfs/lfs62 LFS 6.2 中文版实踩 2026-10-17，svnbook 坑 18-21 的补充）：
    - **老 HTML 表格不闭合 → bs4 把 navfooter 吸进 wrap**（e2fsprogs 实踩，正文尾巴混入「后退/前进/上一级/首页」）：
      渲染前先 `soup.find_all("div", class_=["navfooter","navheader","headertitles","headerlinks"])` 逐个 decompose，别依赖树结构
    - **页面顺序 = index.html `div.toc` 里所有 `<a>` 的出现顺序（扁平）**；本站 toc 的 ul 嵌套树会章 li 混入后续章节的节条目，
      按树分组必错。章标题另取各章首页 h1（章首页输出文件名用章标题，别用 toc 锚点文字）
    - 导入后期望路径与 TOC 不一致（改名改序后）：同步改 progress.json 的 key（含裸目录 key）再跑 reconcile
    - 目录名清理：`--toc-md` 后 TITLE 名=文件夹名（带 chapterNN- 前缀）→ `PUT /toc editNode + action_mode` 改名；
      **editNode 必须带 action_mode**（sibling/child），缺了 400 missing action_mode；顺序调整用 prependNode/appendNode（坑 22/29 同款）
    - 转换器 `examples/lfs-handbook/`（DocBook wrap/package/installation/segmentedlist/admonhead 结构全套）
31. **无章号页（附录/索引）要单独定顺序与命名**（vbird 基础学习篇实踩 2026-10-16）：基础学习篇 27 章从**第零章**起（中文数字含「零」）+
    `附录 A`/`附录 B`/`快速索引` 三页无「第N章」→ 解析不出章号会全落兜底值、排序错乱。做法：章号正则加「零」；附录/索引给 `27/28/29`
    伪章号接在章节后（三位数前缀与两位章号字典序一致，DFS 导入序不错位）；标题带上「附录 A：…」，索引页 `text_head0` 是站点名要改名成「…快速索引」。
32. **GitBook 2.x 静态站（老 gitbooks.io）+ 嵌套列表渲染坑**（2026-10-17 mac-dev-setup 实战，`examples/mac-dev-setup/`）：
    - 老站**还在线时优先直接抓 HTML**：正文容器 = `section.normal`（上一/下一页导航是 `div.book-body > div.navigation*`，在容器外，天然不污染）；每页一个 `index.html`，站点目录顺序看侧栏 `ul.summary` 的 `<a>`；**`.md`/`SUMMARY.md`/`book.json` 一律 401**（别指望 Shell 版面旧 gitbook 站有 md 源）
    - **嵌套列表必须脱离 render 主循环**（本次血泪）：bs4 渲染器的 `render()` 主循环里**没有 `li` 分支**，只要在 `ul` 分支里用 `render(child_ul)` 递归，下一次 `render(ul)` 就会去遍历 `ul.children`（全是 `li`）→ 每个 `li` 掉进 `else` → 症状是「同一列表内容出现两遍 / 子项没缩进 / 缩进层级跳级」。正确做法：写独立的 `render_list()` 递归，`render()` 的 `ul/ol` 分支只调它
    - `inline()` 必须**先跳过块级子节点**（`ul/ol/table/pre/blockquote`），否则 `inline(li)` 会把子列表文本拼进父项 → 重复
    - 收尾清 GitBook 插件产物：读者数徽章（`bitdeli` 行）、`cover.jpg` 发布图等；**外链图源站可能早就 404**（本文两张七牛测试域名图）——修不了就保留原链并在报告里说明
33. **MediaWiki 站（wiki.ubuntu.org.cn）**（2026-10-18《Ubuntu 参考手册》实战）：
    - **`api.php` 被 Cloudflare 拦**（https 直接 403 “Just a moment…”，http 301→https）；但**普通页面路径放行** → 仍可抓 HTML（带浏览器 UA）。先试 API，不行就切页面抓取
    - 页面清单（分类成员）取 `/分类:<分类名>` 页面而不是 API（`list=categorymembers`）；命名空间页面 URL 形如 `/UbuntuManual:Ubuntu_基础`（空格→`_`，整体 quote）
    - 正文容器 = `div.mw-parser-output`；**要丢掉的东西**：顶部导航 `ul`（含“…导航”）+ 导航 `table` + **自动目录 `div.toc`**（含 `h2#mw-toc-heading`）→ 定位『第一个带 `span.mw-headline` 的 h2』之后才算正文；无标题页（封面/首页）从第一个 `<p>` 起到第一个 `hr/ul/table` 前
    - **每页尾部有 MediaWiki 调试块**（`NewPP limit report` / `Transclusion expansion time report` / `parser cache`）→ 从 `NewPP limit report` 处截断
    - 站内链接（`/UbuntuManual:xxx#anchor`）剥成纯文本；`sup.reference`（脚注引用）丢；`span.mw-editsection` 丢；`<nowiki>` 清洗
    - 实测：17 页（分类 17 个成员）/ 405KB → 库 84683525，四种查全绿
34. **单页长文档（xhtml）→ 按 h1 拆章**（2026-10-18 cb.vu/unixtoolbox_zh_CN 实战）：
    - archive.org 链接可能超时（沙箱屏蔽）→ **先试原站**（cb.vu 还活着，直接抓原页更全）
    - 站把完整 XHTML **内嵌**在 `<div id="toolboxContent">` 里 → **bs4 二次解析不出来**（h1/pre 全为 0，但 `decode_contents()` 里明明是标签；疑与嵌套 `<html>`/`<?xml?>`/DOCTYPE 有关）→ **改纯正则扫描块**（`<(h1|h2|h3|h4|pre|p|ul|table)…>(.*?)</\1>` 顺序扫），稳定且够用
    - 正文容器 `div.main`（`title/abstract` 单独取，`menu/changestyle/footerfirst/footerlast/pb` 全丢）；行内：`span.cmt`→保留、`span.fn/pp/keyword`→反引号、`a.xrefp`→纯文本；`<pre>` 内容原样进 bash 代码块
    - **拆分粒度**：单页长文档按 `h1` 切（本次 23 章 + 前言 = 24 篇）；文件名 `NN-<h1文本>.md`（洗 `/\\:*?"<>|`）；首页 `00-前言.md` = 书名 + 摘要 + 章节目录表
    - 尾巴常有 XHTML 注释/未闭合碎片（`end main -->`、孤立 `-->`、`<div`）→ 截断 + 逐行清
35. **看云（kancloud）书：主章/子节分组 + 图床防盗链**（2026-10-18《程序员的自我修养》实战）：
    - **SEO 副本仍是 md 源码**：`div.seo > div.content` 是**未渲染的 markdown**（HTML 转义）→ `html.unescape` 后去掉统一左缩进即落盘（比抓渲染后的正文干净得多）
    - **目录**：页面 `div.catalog > ul > li > a` 给出**全部 124 条**（单层平铺，id 连续），**书首页**的目录链（`/kancloud/<book>/<id>`）只含 **20 个主章** → 主章 id 之间的条目就是它的子节 → 据此建「主章目录 + 主章页 + 子节」结构（`02-程序员基础知识/02-程序员基础知识.md` + `02.1-字符编码.md`…；`-`(45) < `.`(46) 主章文件自然排第一）
    - **图床防盗链**：`box.kancloud.cn` 裸请求 **403**，带 `Referer: http://www.kancloud.cn/kancloud/<book>` 才 200 → 下载传 CDN 时必须带 Referer（本次 38 张图全转 CDN、0 失败）
    - 个别页 `div.content` **本身为空**（看云侧真没写）→ 用 `# 标题` 占位，避开语雀空文档校验


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
| jinbuguo.com/lfs/lfs62（LFS 6.2 中文版，DocBook XSL 老多页站，2026-10-17） | 正文 = `div.wrap`（navheader 后 navfooter 前） | 见坑 30：先 decompose navheader/navfooter 再渲染 | 源站 NXDOMAIN/502 → 镜像 p-moon/develop-reference-data；toc 扁平序 + 章首页 h1 取章名；note/important→引用块；pre.userinput 命令块；icon img 全跳过零图；153 节点；转换器 `examples/lfs-handbook/`（坑 30） |
| docs.freebsd.org/zh-cn/books/handbook（FreeBSD 官方手册，Asciidoctor/Hugo，2026-10-17） | 正文 = `main>div.book-content` | 容器自带边界（页脚 last-modified/buttons 在外） | 42 节点（5 部分目录 + 37 章/附录）；bs4 递归渲染器（见坑 28）；5 类 admonition → 引用块；表格 caption + 无 thead 首行当表头；167 图传 CDN；`--toc-md` + prependNode 修根级顺序（坑 29）；转换器 `examples/freebsd-handbook/` |
| cn.linux.vbird.org/linux_basic（同站基础学习篇, 2026-10-16） | `<!-- 本文的正式部分 -->`（附录 A 无此标记→fallback `<!-- 本文的档头部分 -->`） | 页脚 `<div style="padding-top: 0px; text-align: center;">` | 27 章（**第零章**起）+ 附录 A/B + 快速索引 = 30 篇；**全简体**（无繁体章，不触发简繁双版）；转换器抄 `examples/vbird-server/`，改 4 处：BASE→linux_basic、章号正则加「零」、窗口加「档头部分」fallback、附录/索引伪章号 27/28/29；269 张正文图全传 CDN（0 失败） |
| cn.linux.vbird.org/linux_server（老式 PHP 表格站, 2026-10-16） | `<!-- 本文的正式部分 -->`（繁体同形）之后 | 页脚 `<div style="padding-top: 0px; text-align: center;">` | 22 章；**标题是 `<span class="text_h1">` / `<span class="text_h2">` 不是 h 标签**，章名取 `text_head0`（内有嵌套 `text_head_en`，正则用 `</span>\s*(?:</a>|<br)` 收尾）；终端块 `<table class="term"><pre>`；Tips/例题=单格 `<table width="90%">`；**整章全文页与分页并存 → 只导全文页**（比值≈1）；装饰图（大标题/小标题/鸟哥图示 596 张）按 alt 剔除、正文截图 218 张传 CDN；繁体章额外出「（简体版）」（opencc tw2sp）；按「第N章」中文数字转阿拉伯排序（非文件名前缀序）；站点专用转换器与复用流程见 `examples/vbird-server/`（fetch_all.py + crawl_vbird.py + README） |
| aaaaaashu.gitbooks.io/mac-dev-setup（《Mac 开发配置手册》，GitBook 2.6.7 静态站，2026-10-17） | 正文 = `section.normal` | 容器自带边界（`div.book-body > div.navigation*` 在外） | 无源仓库（GitHub 同名 repo 不存在）→ 抓 HTML；13 页（侧栏 `ul.summary` 定序，平铺）；bs4 递归渲染（**嵌套列表丢前缀坑见坑 32**）；无站内图，2 张外链图源站已 404 保留；转换器 `examples/mac-dev-setup/` |
