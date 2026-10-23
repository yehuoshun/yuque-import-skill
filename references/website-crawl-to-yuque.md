# 网站抓取 → 语雀导入 SOP（2026-10-13 固化）

> 触发模板：「把 <网址> 抓取到语雀」「这个网站教程导到语雀」。
> 实战源（按时间）：gitref（content_box 容器）、Nulab（Gatsby page-data + 图片抠图）、
> Git Magic（DocBook content div）、廖雪峰（Tailwind 站，评论区 JS 带偏窗口事故）、
> 看云 kancloud（SEO 副本直出 md 源码）、Pro Git gitbooks.io（GitBook3 + asciidoc 实体转义）、
> SVN Book（DocBook XSL 多页站，bs4 渲染器）、cn.linux.vbird.org/linux_server（老式 PHP 表格站，2026-10-16）、
> cn.linux.vbird.org/linux_basic（同站基础学习篇，复用同一转换器，2026-10-16）、
> docs.freebsd.org/zh-cn/books/handbook（FreeBSD 官方文档站，Asciidoctor/Hugo，2026-10-17）、
> jinbuguo.com/lfs/lfs62（LFS 6.2 中文版，DocBook XSL 老多页站 + GitHub 镜像，2026-10-17）、
> sketchcn.com（《Sketch 中文用户手册》Adobe Muse 单页站，**域名已停售下线** → CC 2019-04-25 快照 + GitHub 同源镜像仓库救图，2026-10-20）、
> zh.d2l.ai（《动手学深度学习》Sphinx 书站，**站点无 TeX 源 → 反向改吃源仓库 `.md`**，2026-10-21）。
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

36. **社区/论坛站整体下线（域名 302 到厂商新站 + 反爬 403）→ Common Crawl WARC 兜底**（2026-10-18 EMC 中文支持论坛《SAN 管理入门系列》实战，`examples/emc-community-cc/`）：
    - **症状**：`community.emc.com/docs/DOC-16067` 302 到 `dell.com/support`；社区页对 curl/headless 一律 **Akamai 403**（TLS/JA3 层面挡，换 UA/HTTP2 无用）；archive.org 在沙箱被墙（DNS 投毒到私网 + 出口白名单）
    - **兜底链路**：**Common Crawl**（无需 key、`index.commoncrawl.org` + `data.commoncrawl.org` 通常可达）
      1. `https://index.commoncrawl.org/collinfo.json` 拿 collection 列表
      2. **用 prefix 查询一次拿全**：`/{coll}-index?url=<域名>%2F<路径前缀>&matchType=prefix&output=json&limit=200` → 返回每条含 `filename/offset/length/timestamp/status`
         （逐条精确查询又慢又容易被 504 限流；「No Captures」是确定性空，504/空响应要重试 3-4 次，加 `sleep`）
      3. 按 `Range: bytes=<offset>-<offset+length-1>` GET `https://data.commoncrawl.org/<filename>` → gunzip → **WARC response 体**（跳过两层 `\r\n\r\n`：先 WARC 头，再 HTTP 头）即原文 HTML
    - **2019 年的快照最有价值**：老论坛在 2016 迁移后仍留旧页，CC-MAIN-2018/2019 有全量；更老的 collection（2013-2014）反而常「No Captures」
    - **正文定位（Jive/DECN 类社区）**：`<!-- [DocumentBodyStart:<uuid>] --><div class="jive-rendered-content">` … `<!-- [DocumentBodyEnd`。Word 粘贴带来的符号字体项目符 **`ü`/`Ø`/`•`/`–` 是字面字符**（不是标签）→ 转换器按「首字符 → 层级」映射成 `- ` / `  - `；`<h1>` = 小节标题（介绍/更多信息/参考/应用于）
    - **图片多半救不回来**：`/servlet/JiveServlet/downloadImage/...` 这类附件 CC 基本不收录（本次 128 个 collection 前缀查询全空，4 张只救回 2 张——靠**第三方转载站**（cnblogs pipci）镜像的图）。缺图就如实记账，别去 Dell 新站硬抓（它把正文/图都放 Sprinklr JS 里，云爬虫也只拿得到评论区）
    - **命名/口径**：站点类走网站口径（库名 `系列名（日期）`、分组「文章收集」36149506）；描述里**必须注明「站点已下线，正文经 Common Crawl <年份> 快照恢复」**（硬规则 11）

37. **站点下线 + CC 无图 → 先找 GitHub 上的同源镜像仓库**（2026-10-20 sketchcn.com《Sketch 中文用户手册》实战，`examples/sketchcn/`）：
    - **域名停放页的特征**：`curl -I` 返回 200，但 body 只有 1~2KB，正文是 `<h1>[域名] is for sale</h1>`（4.cn 之类）→ 站点已下线，别在正文抓取上耗时间
    - **CC prefix 查询先摸清收录面**：`/{coll}-index?url=<域名>%2F&matchType=prefix` 逐个 collection 扫，挑**时间最新且含目标页**的（本次目标页只到 CC-MAIN-2019-18 / 20190425144522；2020 之后的快照只剩停放页）
    - **图的无解要「确定性」收口**：`?url=sketchcn.com%2Fimages%2F*` 返回 **`"No Captures found for: …"`** = 确定性空（≠ 504 超时）→ 才能断定「CC 没有这张图」，不用反复重试
    - **⭐ 反向找镜像仓库**：`api.github.com/search/repositories?q=<域名>` 或 `q=<页面 slug>`。本次命中 `i5ting/sketchcn`（**repo description 直接写了目标 URL**）——站长把翻译工作仓推上去了，里面有 **翻译源 md（可当标题 oracle）+ images/ 全量图 + 整站 HTML 快照**
    - **两份快照取谁**：先 diff（本次只差 7 处），**正文取更新的 CC 版**（菜单项从「编辑 >」改成「图层 >」），**图片取仓库版**
    - **Muse（Adobe Muse）站的转换要点**：h3/h4 小标题是 `<p class="nomal-text" id="u…">` → 拿翻译源 md 的标题做 oracle 还原（126/178 命中）+「本页另有同名真 h2 → 压到 h3」补丁；项目符 `・` 是字面字符（同坑 36）；`<p class="code">` → 代码块；窗口 = 手风琴导航 `<ul>` 之后 → `<div class="verticalspacer">` 之前
    - **保真度自检（比 grep 残留标签更硬）**：源 HTML 窗口所有 `<p>` 文本逐条在产物 md 全文里做「去空白/去项目符」子串匹配，本次 510 条未命中 3（三句欢迎语，补进前言）→ 100% 覆盖。⚠️ 若正文里有 `[文字](url)` 链接，**比对前先把 md 的链接语法剥成纯文字**，否则会假报「未命中」

38. **同站第二批（Sketch 2 手册 + 15 篇技巧分享）踩到的 4 个新彗**（2026-10-20，同一站点；脚本 `examples/sketchcn/build_extra.py`）：
    - **一个页面装多篇文章 → 按日期祭标重排**：《技巧分享》每页 5 篇，每篇 `<h1>` 前有个 `id="uNNNN-6"` 的 月/日 徽标（`<p>Apr</p><p>4</p>`）→ 先抽徽标当元数据、再 `DATE_DIV_RE` 把徽标块剔掉；**按日期全局排序**后再命名 `NN-标题.md`（本次 5 页 15 篇，2014-03-09 ~ 06-02）
    - **底部翻页按钮 1/2/3/4 是导航**：`<a href="sketch-tips-tricks-N.html"><p>N</p></a>` 四个短句会被当成 `### 1 ### 2 ### 3 ### 4` → 按 href 模式整块剔掉（站内链接一律不要）
    - **连续 ≥3 个「标题」= 图的说明标签，不是标题**：一组键盘截图下的 `隐藏工具栏/隐藏图层列表/隐藏检查器/同时隐藏...` 四个短句被启发生成器全部升成 `###` → 收尾加一步 `demote_head_runs(lines, 3)`：**≥3 个连续标题（中间只有空行）整体降回普通行**
    - **嵌套目录下图片引用要写 `../images/x`**：`yuque_rewrite_images.py` 是**按 md 文件所在目录**解析相对路径（`base = os.path.dirname(fp)`）—— 文档放到 TITLE 子目录后，还写 `images/x` 全部报「本地缺失」（0 上传）；要写 `../images/x`（同时记得：图收集阶段别只抳 HTML 的 `src=`，tips 那边已是 markdown 图引用，要用 `!\[...\]\(images/...` 正则）
    - 另：嵌套目录 + 根级 `00-前言.md` 的库，toc-md 收尾后前言会落到两个 TITLE **之后** → 一发 `prependNode sibling` 归位（同坑 29）

39. **`create-book` 描述太长 → `HTTP 400 验证失败`，报错信息完全误导**（2026-10-20 实捶）：报「一般是路径名冲突，或者文章标题不符合要求」但**换名字/换 slug 都没用**，真正原因是 `--desc` 超长（实测 251 字通过、261 字被拒，约 250 封顶）。排查姿态：拿短 desc + 同名同 slug 试一发就能区分（本次白白建/删了 5 个测试库）。

40. **aibydoing.com（Quantecon/Jupyter-Book 站 + 作者反全站复制，2026-10-21 实战）**：
    - **动手前先查站内版权声明**：作者明文「请勿整理全站内容分发成电子书/请勿帮开源化/商用需授权」→ 与开源仓库（带 license）不同，网站类**导入前先探站看版权页，碰红线必须停手报老板拍板**（本次老板拍「B=全量导，仅私人库自用不分发」才动手；库描述也注明「纯私人学习用途」）
    - **正文容器自带 alert 类**：Quantecon 主题正文 = `main.qe-page__content > div.main-content.alert.alert-light` → 剔广告按 `div.alert` 删会把正文一起剁（首跑全库 0 图）→ **必须豁免 main-content**；封面/Pro 卡/buymecoffee 是独立 `div.alert` 兄弟节点，可精准剔
    - **math 是 `span.math` 内嵌 `\(...\)`/`\[...\]`** → 还原成 `$/$$`；代码是 Pygments `div.highlight-ipython3 > pre`（get_text 即代码，语言看 highlight-xxx class）；目录卡片（标题/字数/更新时间）在首页 h3 分组下 `a > div.custom-card`
    - **QA 误报甄别**：grep「上一章/Pro 会员/${」≠ 导航污染——先看上下文再动（作者行文引用、LaTeX `${...}$`）
    - 另：`yuque_tree_import.py` 的 `save_prog` 在 `--progress` 传裸文件名时 `os.makedirs('')` 直接崩（v1.3.97 已修：dirname 空则跳过）

41. **dumi（umi）静态书站 + MathJax SVG 公式、无 TeX 源（hrl.boyuai.com / 《动手学强化学习》，2026-10-21 实战）**：
    - **识别**：`window.g_useSSR=true` + `<script src="/umi.js">` + `div.__dumi-default-layout-content` = dumi SSR 站，**正文全在 HTML**（不用跑 JS）。先查官方 GitHub：本次 `boyu-ai/Hands-on-RL` **只有纯代码 notebook（0 个 markdown cell）** → 无正文源，只能抓 HTML（网站口径）。
    - **⚠️ 公式是 MathJax SVG，TeX 源已不可得**：`<mjx-container><svg>`，**无 `alttext`、无 assistive-mml、无 MathML**（`grep -c alttext` = 0）；`data-c` 只有字符码、`data-mjx-texclass` 只有类别 → 都还原不出 TeX；umi.js / searchIndex 里也没有正文 → **保真只能「公式当图」**：抽 `<svg>` 存 `.svg` → `upload_image` 传 CDN（**接口吃 svg**，回 `cdn.nlark.com/…/*.svg`）→ 正文 `![](cdn)`。本次 1737 处 → 去重 795 个唯一。
    - **抽 svg 必须贪婪匹配**：MathJax 的伸缩符号（大括号/求和号）会生成**嵌套 `<svg>`** → 非贪婪 `(<svg\b.*?</svg>)` 会在第一个内层 `</svg>` 截断（本次 795 里 8 个截成半截）→ 改 `(<svg\b.*</svg>)` + `re.S`。自检两发：`ET.parse` 全过 + 每个 `xlink:href="#id"` 都能在自身 `<defs>` 找到。
    - **`ex` → `px` 换算**：MathJax 尺寸写成 `width="40.6ex"`，抽成独立文件用 `<img>` 引时 `ex` 相对字体不可靠 → 按 `1ex≈8px` 改写。
    - **正文窗口起点别从 `index("__dumi-default-layout-content")` 算**：那是类名属性**内部**，会把开标签尾巴 `…">` 带进正文首行 → 从该串后的第一个 `>` 之后起。
    - **转换**：代码 = `<pre class="prism-code language-X">` 的逐行 `<div class="token-line">`（先删 copy `<button>`）；表格 = `table>thead/tbody`（外层可能套 `div.__dumi-default-table`）；标题锚点 = `<hN><a aria-hidden><span class="icon icon-link"></span></a>标题`；外链图标 = `svg.__dumi-default-external-link-icon`（丢弃）；站内链 → 纯文本。
    - **空的「部分页」建 TITLE 不建 DOC**：`/chapter/1` `/chapter/2` `/chapter/3` 只有翻页器 → 建成「基础篇/进阶篇/前沿篇」三个 TITLE。
    - **内联 base64 图**：正文里有 `<img src="data:image/png;base64,…">`（本次 2 张真插图，不是装饰）→ 必须解码另存，只匹配 `/static/` 会把它们整张丢掉（图数 84 vs 82 的差值就是它们）。
    - **子目录相对路径（与坑 38 同族）**：根级 `_img/` `_math/` + 文档落 depth-1 子目录时，引用要写 `../_img/x`（`yuque_rewrite_images.py` 按 md 所在目录解析，写 `_img/x` 会全报本地缺失）。
    - 转换器 + 复现命令：`examples/hrl-boyuai/`（`fetch_pages.py` / `convert.py` / `build.py`，含「子目录前缀」修法）。

**【姊妹案例】MyST/Sphinx 书站的「md 源仓库」取法（zh.d2l.ai / 《动手学深度学习》，2026-10-21 实战，`examples/d2l-zh/`）**：
    - **站点无 TeX 源 ≠ 只能当图**：d2l 站上公式同样是 MathJax SVG（无 alttext，与坑 41 同款），但源仓库 `d2l-ai/d2l-zh`（Apache-2.0）**逐章就是 `.md` 源、公式真 LaTeX** → 走**源仓库 md** 口径，站点 HTML 只当 oracle。**动手前先查源仓库**：hrl 的仓只有纯代码 notebook（只能当图），d2l 的仓有全量 md（保真度直接拉满）。
    - **站点 HTML 的两个 oracle 用途**：① 源 md 标题不带编号 → 按**页内顺序**对 `<span class="section-number">` 补出 `## 2.3.1 标量`（比对前归一化空白与 `[**…**]` 强调标记）；② `:numref:`/`:eqref:` 的**渲染文本只能从站上取**（源里只有标签名）→ 抽 `numref`（引用处文本）/`defs`（定义处编号）/`bibkey→引文` 三张表，标签按 Sphinx 规则归一（`lower().replace('_','-').replace('+','-')`）。
    - **四个框架选项卡 → 只留 PyTorch**：MyST `:begin_tab:` + 代码单元格首行 `#@tab`；**无 `#@tab` 标记的单元格 = mxnet（站上默认面板）**（拿站上各面板代码块与源单元格逐块比对证实）→ 只留 `pytorch`/`all`；多框架列表（`:begin_tab:`mxnet, tensorflow``）要按 `[,\s]+` 拆开判。
    - ⚠️ **裸 `:end_tab:` 会让转换器吞掉文件尾（本次最险的一条）**：d2l 源的块结束标记是**裸的** `:end_tab:`（不带反引号参数），而 begin 参数可能是多框架列表 —— 正则若只认「单框架 + 带参 end」，后一个 `:begin_tab:`pytorch`` 会一路扫到 **EOF**，**整篇后半段被静默吞掉**（首跑症状：文档只剩 911B、指令残留 29 处、图片没重写、正文无声缺失）。修法三件套：begin 按 `[,\s]+` 拆列表判 pytorch / end 兼容两种写法 `(?:`[^`]*`)?` / **扫不到闭合必须兜底当普通文本**（所有跨行块扫描同理，代码栅栏一样）。
    - `:eqlabel:` 别跟 `:label:`/`:width:` 一起提前删（否则公式编号全灭）；图片目录导入前必须移出导入根（硬规则 10，本次首跑节点 341 ≠ 156）。
    - 复现命令 + 完整转换规则表 + 验收记录：`examples/d2l-zh/README.md`。
    - **更省事的一档（pumpkin-book，2026-10-22）**：docsify/GitBook 这类**直接渲染 md 的站**，站上页面与源仓库 md 往往**逐字节相同**（先 `curl` 一个页面 + `wc -c` 与仓库同名文件比一下就知道）→ 不吃 HTML、也不用 oracle。⚠️ 但**站点可能落后于仓库**（南瓜书线上还是 docsify、master 已迁 vitepress），只要页面 md 与仓库 md 相同就以仓库为准。

52. **「纯净书仓」：GitHub Pages 书站 + `manuscript/` md 源（eremes81/game-design-ai-practice-zh-hans /《游戏策划实务即用的 AI·Claude Code 活用法》简体中文版，2026-10-22 实战）**：
    - **识别**：仓库根 = 站点源 —— `index.html`（2.1MB，**全书拼一起的渲染产物，别当正文吃**）+ `manuscript/`（102 个 `.md` = 真正正文）+ `assets/cover.svg` + `robots.txt`/`sitemap.xml`/`.nojekyll`。**只吃 `manuscript/`**，脚手架一律不入库。
    - **无 `SUMMARY.md`**：中文标题只在**每篇首个 H1**，部分名在 `README.md`「完整目录」的 `### 第N部分 · XXX` → **README 当 oracle、H1 当标题源**（两者逐条核对）。
    - ⚠️ **H1 == 文档标题 → 剥掉该 H1**（否则语雀「文档标题 + 正文首行 H1」双标题）。规则收紧为「**只剥等于最终标题的那一个**」（本书 102 篇剥 100；front-matter 的 H1 是书名 ≠ 标题 → 保留）→ 零信息损失。（对比 pumpkin 的「扫全文首个 `# `」：那版是整篇首 H1 一律剥。）
    - ⚠️ **标题里含半角 `/` → 文件系统不允许** → 换全角 `／`（本书 5 处：`UX/UI`、`ArtGuide/06_UI`、`iOS / Android / PC`、`触摸 / 鼠标输入`、`decisions/`、`公司 / 个人 PC`）。语雀 toc-md 收全角无碍。
    - ⚠️ **部分章的 H1 是异体**（part21/part23 写成 `Part 21 · 第1章. xxx`）→ 归一化成 `21.1 xxx`，否则与全书 `N.M` 风格断层。
    - **两位序号目录前缀**（`01-第1部分 · 基础` … `24-第24部分 · 运营实战`、`99-后记与附录`）→ 字典序天然正确，**不用 fix_order**（对比 nndl 的「一<三<二」归位坑）。
    - ✅ **全书 67 处内联 `<svg>`（作者手绘矢量图）语雀 markdown 导入原样保留**（回读 body 里 `<svg>` 完整、` ```mermaid ` 块也在）→ 这类书**不需要**像 d2l/hrl 那样把公式抽成图传 CDN。
    - **图 = 上游本来就缺的占位符**（README 明说「少数示例位图为无原图的占位符」）：全树无 `images/`，2 处 `![](images/…)` 保留原样不重写、别找。
    - 根级 DOC（`00-序` / `01-版权页`）toc-md 后会排到 25 个 TITLE **之后** → `prependNode` sibling 归位（坑 29 复发）。⚠️ **连移两个节点要按逆序 prepend**：先 `01-版权页` → prepend 到第一个 TITLE 前，再 `00-序` → prepend 到 `01-版权页` 前；**同 target 连续 prepend 会反序**（本次先序后版权页，得到 `版权页, 序`）。
    - 结果：127 节点 / 0 失败 / 结构核对 PASS / 六查全绿；库 84860110，slug `game-design-ai-practice-zh-hans-20261022`；`examples/game-design-ai-practice/`（`build_lib.py` 7 条规则 + 验收表）。

53. **RefactoringGuru 中文站（refactoringguru.cn/design-patterns，《深入设计模式》设计模式全节，2026-10-22 实战，`examples/refactoringguru-design-patterns/`）**：
    - **形状**：261 页 = 简介/目录/3 分类 + 22 模式 + 工厂比较 + 双分派 + 电子书页 + **10 语言 landing + 22 模式 × 10 语言 = 220 篇代码示例**；HTML 结构规整（`div.section.*` / `figure.code>pre[lang]` / 卡片 `a.pattern-card*`）→ bs4 递归渲染器即可。
    - ⭐ **`<body>` 也带 `no-feature` 类 → 祖先过滤会一票否决全站**：`/design-patterns` 落地页的 hero 在 `div.no-feature` 里，为剔它写了「祖先含 `no-feature` 就跳过」→ 卡片型页面（目录/分类/语言 landing/示例概览共 **11 页**）的 `<body>` 恰好也带该类 → **全被滤空成 1 字节文档**（首跑 10 个 1B 文件才暴露）。正解：祖先检查**排除 `body`/`html`/`main`**。教训：拿祖先类名做过滤，`body` 上的类名会一票否决一切。
    - **CJK 排版辅助 span**：`span.chpuleN` 承载**中文标点本身**、`span.chpuriN` 承载**一个空格**（`<span class=chpule2>，</span><span class=chpuri2> </span>`）→ 必须保留其文本，收尾再把「标点+空格」折回标点，否则正文成「实例 ， 并」。
    - **软连字符 `&shy;`（\xad）**遍布标题与代码（`Demo&shy;Single&shy;Thread`）→ 全局删 `\xad`。**`span.hidden-in-book`** = 站点显示/电子书隐藏的补充词（「单例**模式**」的「模式」）→ 保留。
    - **结构图两个 img**：`structure-img-non-indexed`（桌面）/ `structure-img-indexed`（移动）→ 只取前一个（否则同图进两遍）。
    - **图标即语义**：优缺点 `div.pros-cons` 左右两列 `<ul>`，首项 `<i class=fa-check>`=优点 / `fa-times`=缺点 → 插 `**优点：**`/`**缺点：**` 标签；适用场景 `div.applicability-problem`（`fa-bug`）/ `-solution`（`fa-bolt`）→ `> 🐞 …` / `⚡ …`；`span.fa-stars`/`dp-popularity` 的 `i.fa-star` vs `fa-star-o` → ★/☆。
    - **卡片型页面正文全在 `<a class=pattern-card>` 里**（目录/分类/语言 landing）→ 不专门渲染就是「每字段一行、无项目符」；按 `.pattern-name`/`.pattern-aka`/意图渲成 `- **名称**（English） — 意图`。
    - **图只放行 `/images/patterns/content/` 与 `/images/patterns/diagrams/`**；`patterns/cards/*-mini.png`、`patterns/icons/*.svg`、语言 hero `dp-bg` 全是装饰。
    - ⚠️ **`--test N` + `--toc-md` 必报「生成目录树失败: 缺少文档记录」**——toc-md 要全量目录记录，是**预期行为不是真失败**。
    - ⚠️ **toc-md 收尾后根级 DOC 又排到 TITLE 后**（坑 29 复发）→ 两发 `prependNode sibling` **按逆序**归位（先 `01` 到第一个 TITLE 前，再 `00` 到 `01` 前）。子目录 `05.NN-语言` 必须**两位零填**（`05.01`…`05.10`），否则字典序 `05.1 < 05.10 < 05.2`。
    - 结果：275 节点（14 目录/261 文件）/ 151 图全传 CDN / 0 失败 / 结构核对 PASS / 六查全绿 + 261 篇逐篇回读 0 未命中；库 84861074。
    - `yuque_rewrite_images.py --dry` 报的 2 处「本地缺失」是 PHP 代码样例里的 `<img src='$url'>`，**代码里的 HTML 是正文**，别当真缺失。

54. **CSDN 博客系列（索引页 + 129 篇正文，刘伟/Sunny「史上最全设计模式导学目录」，2026-10-22 实战，`examples/csdn-lovelion-design-patterns/`）**：
    - ⚠️ **CSDN 反爬 = HTTP 521**：连续/快速请求回 521 + 2KB 空壳（首轮探测 130 页中就中 2 页），**退避重试（3/6/9…S）后全 200**。判据别只看状态码——**响应里没有 `content_views` 就当失败重试**。
    - **正文容器 = `div#content_views`**（干净，广告/推荐位在容器外）；文章自身标题 = `h1.title-article`（在容器外，`<title>` 带「_CSDN博客」后缀要剥）；**代码块 `<pre><code class="language-java">`** 语言直接取（本库 225 块全带）。
    - ⚠️ **CSDN 的 `<table>` 是版式盒子不是数据表**：`<table border="1">` 常被做成「思考」提示框（外层 1 行 1 格 + 内嵌 1 张表）→ 按数据表渲会出一堆空单元格。判据：**含嵌套 table 或每行 ≤1 格 → 渲成 `> ` 引用块**（本库 248 处）。
    - **图片**：2012-2014 老图域名还活着（`img-my.csdn.net`/`img-blog.csdn.net`，带 `Referer: blog.csdn.net` 全 200）；**表情图 `static.blog.csdn.net/xheditor/xheditor_emot/default/*.gif` 已 404** → 跳过；无扩展名 URL 靠 `Content-Type` 猜扩展名。
    - **索引页只有 `<p>/<strong>`、无 h 标签**（链接 = 129 篇系列文章）→ 口径取**拓成全量系列库**（导学目录 + 129 篇 = 130 篇 / 163 节点），而非只导 1 页索引；索引页的站内链接照 SOP 渲成纯文本。
    - 结果：163 节点（33 目录/130 文件）/ 187 图全传 CDN / 0 失败 / 结构核对 PASS / 六查全绿 + 130 篇逐篇回读 0 未命中；库 84861605。

55. **图灵社区（ituring.com.cn，Vue SPA + 隐藏 JSON API，2026-10-22《开源软件架构》实战，`examples/ituring-aosa/`）**：
    - ⚠️ **页面 HTML 里没有正文**：`www.ituring.com.cn/book/<id>` 只是 Vue SPA 外壳（`<div id=app>` + `app.js`），抓 HTML 一无所获。**真正 API 在 `api.ituring.com.cn`**（另一个子域），猜路径（如 `/api/book/1143`）会拿到 **200 的 SPA 外壳**（看着成功、实则全站首页）→ **以“响应里没 JSON 字段”当失败判据**。
    - 接口（从 `app.923b6618.js` 里的 `urls` 对象挖出）：图书详情 `GET https://api.ituring.com.cn/api/book/{id}`（**book 小写**）→ `ebook.chapters[]`（每章 `id/isFree`）；章节正文 `GET https://api.ituring.com.cn/api/Book/mini/{章节id}`（**Book 大写**）→ `{subject, htmlOfBody}`。图灵自己书（非开放书）走 `/api/Book/Tupub/{id}`。全部 39 章 `isFree=true` 可直接拿。
    - `htmlOfBody` 是**脏 HTML**：`<p>` 大量不闭合、互相嵌套（`</p></p></p>` 堆尾巴）→ 转换器 `render()` 遇含**块级子元素**的 `<p>` 必须**下钻 render**而不是 inline，否则整章被归成一个大段。
    - **图片三类历史外链，旧地址已死**：① `http://www.aosabook.org/images/<book>/X.png` → 站点改版后 **404**，新地址 `https://aosabook.org/static/<book>/X.png`；② `raw.github.com/stfairy/aosa-violet/...`（图床仓已删）→ 同名图在 `aosabook.org/static/violet/`；③ `/download/xxx`（无 host 的相对路径）→ 补 `https://download.ituring.com.cn`。**图片无扩展名（`.small`）会被 `upload_image` 拒**（按扩展名判类型）→ 改成 `.png` 再传。
    - 同一目录下**同卷同名章节**（本书 `卷2 第6章 Git` 有两份独立译文）→ 标题加「（译文一/二）」防同父重名（硬规则 6）。
    - 口径：无 repo → **网站口径**（库名 `开源软件架构（2026-10-22）`、slug `aosa-zh-20261022`、分组「文章收集」）；树 = 前言（根级）+ `卷1/` `卷2/` 两个 TITLE + 39 篇。结果：41 节点 / 74 图全传 CDN / 0 失败 / 结构核对 PASS / 六查全绿 + 39 篇逐篇回读 0 未命中；库 84864438。

56. **wizardforcel / 老 gitbooks.io 静态站（GitBook 2.x，`https://<name>.gitbooks.io/<book>/content/`，2026-10-22《让开发自动化系列专栏》实战，`examples/wizardforcel-gitbook/`）**：
    - ⚠️ **gitbooks.io 间歇 401**（同 progit2 坑）→ `fetch()` 必须退避重试（实测 6 次、2/4/6…s 后全 200）；首轮裸请求直接 401 抛异常。
    - 结构固定：侧栏 `ul.summary li.chapter[data-path]` 就是页面清单（**顺序 = 侧栏序，不用手填**，标题里 `<b>N.</b>` 是序号）；正文容器 = `section.normal`（页外 nav-prev/nav-next 天然在外）。
    - **无源仓库**（`wizardforcel/ibm-j-ap` 在 GitHub 不存在）→ 抓 HTML。**正文首个 H1 == 文档标题 → 剥掉**（语雀侧已有文档标题）。
    - 图在 `img/`（相对路径）→ 边转边传 CDN；⚠️ **本站 `img/build-failure.jpg`、`img/cpd-ant.jpg` 源站 404**（建站时就缺）→ 保留原站 URL，裂图即上游如此，修不了。
    - 文件名用 `NN-副标题.md` 两位序号前缀免归位；标题含 `/` 换全角。
    - 结果：18 节点（0 目录/18 文档）/ 78 图传 CDN（2 上游 404）/ 0 失败 / 结构核对 PASS / 六查全绿 + 18 篇逐篇回读 0 未命中；库 84864611，slug `ibm-j-ap-20261022`。**同族站（ibm-j-cq 等）直接换 `--base` + `--book-name` 复用**。

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
| community.emc.com（EMC 中文支持论坛，Jive/DECN，**站已下线**，2026-10-18） | 正文 = `<!-- [DocumentBodyStart:…] -->` 后的 `div.jive-rendered-content`（**从 Common Crawl WARC 取 HTML**） | `<!-- [DocumentBodyEnd` | 8 篇系列（DOC-16067/68/69/80-84，互为链接）；项目符 `ü/Ø/•/–` 是字面字符→手写映射成嵌套列表；`/servlet/JiveServlet/downloadImage/` 图 CC 未收录（4 张只救回 2 张，靠转载站镜像）；转换器 `examples/emc-community-cc/`（见坑 36） |
| sketchcn.com（《Sketch 中文用户手册》，**Adobe Muse 单页站 + 域名在售**，2026-10-20） | 正文 = 手风琴导航 `<ul>` 之后 → `<div class="verticalspacer">` 之前（**从 Common Crawl WARC 取 HTML**，CC-MAIN-2019-18 / 20190425144522） | （同上，容器自带边界） | 单页长文档按 `<h1>` 拆 15 章 + 前言 = 16 篇；h3/h4 是 `<p class="nomal-text" id="u…">` → 用翻译源 md 标题做 oracle 还原；项目符 `・` 字面字符；**44 张图 CC 明确无收录，全部由 GitHub 同源镜像仓 `i5ting/sketchcn` 补回**；转换器 `examples/sketchcn/`（见坑 37） |
| hrl.boyuai.com（《动手学强化学习》，dumi/umi SSR 书站，2026-10-21） | 正文 = `div.__dumi-default-layout-content` 的 `>` 之后（从类名后第一个 `>` 起，坑 41） | 下一个 `<script>` | 24 篇（21 章 + 前言 + 总结 + 课件页）+ 3 个空部分页→TITLE；**公式 1737 处全是 MathJax SVG、无 TeX 源/无 alttext/无 MathML** → 抽 svg 传 CDN 当图（795 唯一；**嵌套 svg 要贪婪匹配**；ex→px）；代码 `prism-code language-*` 的 token-line；2 张内联 base64 图要解码；子目录引用补 `../`；课件 17 PDF 只留 OSS 直链；六查全绿；库 84821175；`examples/hrl-boyuai/`（坑 41） |
| aibydoing.com（《动手实战人工智能》，Quantecon/Jupyter-Book 站，**作者反全站复制**，2026-10-21） | `<main class="qe-page__content">` 内 `div.main-content.alert.alert-light`（剔 div.alert 必须豁免它，坑 40） | 容器自带边界（prev-next-area/giscus/buymecoffee 是独立节点） | 96 篇 notebook（13 章节）+ 首页 = 97 节点；span.math `\(..\)`→`$..$`；Pygments pre→代码块；图 523 张全传 CDN（covers 装饰图剔）；**版权红线先停手报老板拍板（B=私人库自用）**；六查全绿；库 84820613 |
| zh.d2l.ai（《动手学深度学习》，Sphinx 2.0.0 书站，2026-10-21） | **不爬 HTML**：站上公式是 MathJax SVG 无 TeX 源 → 直接吃源仓库 `d2l-ai/d2l-zh` 的 `.md`（真 LaTeX）；站点 HTML 只当**标题编号 + `:numref:` 渲染文本**的 oracle | — | 140 文档 + 16 章目录 = 156 节点；只留 **PyTorch**（4 框架选项卡，未标 `#@tab` = mxnet）；图 184 全传 CDN；图片目录必须移出导入根（硬规则 10）；六查全绿；库 84822487；`examples/d2l-zh/` |
| llmknowledge.org/zh（《理解现代大语言模型系统-从RAG到全景》，koe，2026-10-22） | 同 d2l 姊妹案例：**不爬 HTML**，吃源仓库 `koemia/llmknowledge` 的**单个大 md**（102KB/711 行）；站点 10 页 = md 10 个 H2 一一对应（标题一字不差），站点 HTML 只当 oracle 验证切分 | — | 单 md 按 H2 切 10 篇（开始之前/第一~七章/附录工具库/速记卡片）；**49 个脚注定义内联在正文里**随章走、93 处引用全保真（语雀渲染 `[^x]` 原样）；7 张 SVG 图是 `<img src>` 形式 → 切分时转 `![alt](src)` 再传 CDN；**CC BY-NC-ND 4.0 许可**（非商业·署名·禁止演绎）→ 同 aibydoing 口径私人库自用、描述注明版权来源；10 节点/0 失败/六查全绿；库 84856349，slug `llmknowledge-zh-20261022`；`examples/llmknowledge/` |
| datawhalechina.github.io/pumpkin-book（Datawhale《南瓜书》，**docsify 站但源仓库已迁 vitepress**，2026-10-22） | **不爬 HTML**：线上还跑旧 docsify（`_sidebar.md` + `chapterN/chapterN.md`），实测线上 `chapter1/chapter1.md` 与仓库 `docs/chapter1/chapter1.md` **逐字节相同（18349B）** → 站点无独立内容，**连 oracle 都不用**，直接吃仓库 `docs/`（比 d2l 还省一档） | — | 20 节点（0 目录/20 文件全平铺）= 00-前言（README HTML 清洗）+ 01-勘误表 + 第1~16章 + 法文版残篇 2 篇；`> [!IMPORTANT]` callout → `> **📌 本章学习须知**`；**剥 H1 要扫全文首个 `# xxx` 行**（章节 1-11 的 H1 在 callout 之后，只看首行会漏 11 篇）；**图只救 `raw.githubusercontent` 的 7 张**（前言 6 + 法文版 roc.png），16 处公式图全在 Datawhale 自家阿里云 OSS（SVG，保持原样比转 CDN 更高保真）；六查全绿；库 84856649，slug `pumpkin-book-20261022`；`examples/pumpkin-book/` |
| blog.csdn.net/lovelion（《史上最全设计模式导学目录》刘伟/Sunny 系列，2026-10-22） | `div#content_views`（容器外 = 广告/推荐，天然不沾）；标题取 `h1.title-article` | 容器自带边界 | **索引页拓成全量系列**：导学目录 + 129 篇（7 原则/24 模式/足球复习 4/综合实例 5）= 163 节点；⚠️ CSDN 反爬 **HTTP 521** → 退避重试且以「无 `content_views`」为失败判据；代码 `<pre><code class=language-x>`；**表格=版式盒子**（含嵌套 table 或每行≤1 格 → `> ` 引用块，248 处）；老图域名带 Referer 可下、表情 gif 已 404 跳过；六查全绿 + 130 篇逐篇回读 0 未命中；库 84861605，slug `csdn-lovelion-design-patterns-20261022`；`examples/csdn-lovelion-design-patterns/`（坑 54） |
| refactoringguru.cn/design-patterns（《深入设计模式》设计模式全节，2026-10-22） | 正文 = `main div.page.text, main article.page.text`（**祖先过滤要排除 body/html**——body 也带 `no-feature`，坑 53）；`/design-patterns` 落地页另剔 `div.illustration-container` hero | 容器自带边界（prom/banner/aside.feature 独立节点） | 261 页（简介/目录/3 分类/22 模式/工厂比较/双分派/电子书页 + **10 语言 landing + 220 篇代码示例**）= 275 节点；`chpule/chpuri` 保留标点折空格、删 `&shy;`、结构图取非-indexed、图标即语义（优缺点/适用场景/星级）、卡片按 `.pattern-name/.pattern-aka/意图` 渲成列表；图只传 `content/`+`diagrams/`（151 张）；`--test N`+`--toc-md` 必报目录树失败=预期；根级 DOC 两发逆序归位（坑 29）；六查全绿 + 261 篇逐篇回读 0 未命中；库 84861074，slug `refactoringguru-design-patterns-20261022`；`examples/refactoringguru-design-patterns/`（坑 53） |
| eremes81.github.io/game-design-ai-practice-zh-hans（《游戏策划实务即用的 AI·Claude Code 活用法》简体中文版，**GitHub Pages 书站 + 纯净书仓**，2026-10-22） | **不爬 HTML**：仓库 `manuscript/` 就是站点源（`index.html` 是 2.1MB 单文件渲染产物）；无 SUMMARY → README「完整目录」当部分名 oracle、每篇 H1 当标题源 | — | 127 节点（**25 目录 + 102 文档**，24 部分 100 章 + 附录 A–N + 后记）；`01-第1部分…` 序号前缀免 fix_order；H1==标题则剥（100/102）；标题 `/`→`／`（5 处）；part21/23 异体 H1 归一化 `N.M`；**67 处内联 `<svg>` 语雀原样保留**（不用抽图传 CDN）；图全是上游缺的占位符；根级 DOC 归位（两发按逆序）；六查全绿；库 84860110，slug `game-design-ai-practice-zh-hans-20261022`；`examples/game-design-ai-practice/`（坑 52） |
| ituring.com.cn/book/1143（《开源软件架构》The Architecture of Open Source Applications 中文版 / iTran乐译开放书，**Vue SPA + 隐藏 JSON API**，2026-10-22） | **不爬 HTML**：页面是 SPA 外壳，正文全在 `api.ituring.com.cn` → 图书详情 `GET /api/book/{id}`（book 小写）拿 `ebook.chapters[]`，章节正文 `GET /api/Book/mini/{章节id}`（Book 大写）拿 `{subject, htmlOfBody}` | — | 39 章全 `isFree` 可读；`htmlOfBody` 脏 HTML（`<p>` 未闭合互相嵌套）→ 含块级子元素的 `<p>` 要下钻 render；图三类历史外链（aosabook.org 旧 `/images/`→新 `/static/`；raw.github.com 图床已删→官方 static；`/download/xxx` 补 host）；`.small` 无扩展名图先改 `.png` 再传 CDN；本书 `卷2 第6章 Git` 两份独立译文→标题加「（译文一/二）」；41 节点（2 目录/39 文档）六查全绿 + 39 篇逐篇回读 0 未命中；库 84864438，slug `aosa-zh-20261022`；`examples/ituring-aosa/`（坑 55） |
| wizardforcel.gitbooks.io/<book>（老 gitbooks.io GitBook 2.x 静态站，无源仓库，2026-10-22《让开发自动化系列专栏》ibm-j-ap） | **抓 HTML**：侧栏 `ul.summary li.chapter[data-path]` 定页面清单（顺序=侧栏序）；正文容器 `section.normal` | — | ⚠️ **gitbooks.io 间歇 401** → fetch 退避重试（6 次）；18 节点（0 目录/18 文档，`NN-` 序号前缀免归位）；正文首 H1==标题则剥；图 `img/` 相对 → 边转边传 CDN（78/80，2 张上游 404）；标题 `/`→`／`；六查全绿 + 18 篇逐篇回读 0 未命中；库 84864611，slug `ibm-j-ap-20261022`；**可复用转换器** `examples/wizardforcel-gitbook/build.py`（坑 56） |
| local.joelonsoftware.com/wiki/Chinese_(Simplified)（《Joel on Software》中译本 12 篇，**MediaWiki 1.16 Monobook 单页**，原站 DNS 已死 + archive.org 被墙，2026-10-23） | **不爬 HTML**：走 **Common Crawl**（`CC-MAIN-2017-26` 快照，与队列给的 Wayback 20170616 同期）取原页；正文容器 **`div#bodyContent`**（Monobook 皮肤；`div#mw-content-text` 是 Vector 皮肤，本站**不存在**，用错选择器会拿到含侧栏/页脚的整页）；按 `<h2>` 拆篇（`<h2>Contents</h2>` 的 `#toc` 目录 table 整块丢） | 容器自带边界（`#siteSub`/`#contentSub`/`#jump-to-nav` 显式丢） | 12 节点（0 目录 / 12 文档，`NN-标题.md` 前缀免归位）；⚠️ 标题含半角 `/` → 换全角 `／`（「膨胀软件与80／20的谣传」）；⚠️ 正文**字面**出现的 `<a>`（ASP.NET 那篇）要转义成 `\<a>`，否则被当原始 HTML 吃掉；**5 张插图 CA1–CA5.jpg CC 明确无收录**（archive.org/arquivo.pt/timetravel 全不可达）→ 丢弃 + 受影响文章末尾加「插图已省略」注释；六查全绿 + 12 篇逐篇回读 0 差；库 84899616，slug `joel-on-software-zh-20261023`；`examples/joel-wiki/`（坑 60） |
| einverne.gitbook.io/selenium-doc（《Selenium 中文文档》，**现代 GitBook v2 平台**，2026-10-23；源仓库 fool2fish/selenium-doc 已 GitHub 404，GitBook 版为 gitlab.com/einverne/selenium-doc 的改版） | **不爬 HTML**：站自带**官方 Markdown 导出**——`/llms.txt` 全量索引（顺序 = 侧栏序）+ 页面 URL 加 `.md`（根页 `/master.md`）；`/~gitbook/site-index` 给带面包屑的层级 JSON | — | 10 节点（**2 目录 + 8 文档**：`01-官方文档/` 4 篇 + `02-wiki/` 3 篇 + 根级 `00-介绍.md`）；⚠️ 每页 md 首块是 GitBook 样板 callout（`> For the complete documentation index…`）要整块剥；首个 H1==标题则剥；**「页 + 子页并存」的分组页当 TITLE 目录用、正文丢弃**（正文只是子页链接清单）；目录名加数字前缀还原站点序（ASCII 的 `wiki` 会排在中文 `官方文档` 前）；根级 `00-介绍.md` 补 1 发 prependNode 归位（坑 29）；**6 张外链图（老站 seleniumhq.org/docs/_images/* 全 404）从官方镜像仓 `vdt/selenium` 按文件名找齐 6/6 传 CDN**；六查全绿 + 8 篇逐篇回读 0 差；库 84899817，slug `selenium-doc-zh-20261023`；`examples/gitbook-v2-md/`（坑 61） |
| doc.yonyoucloud.com/doc/wiki/project/gradle（UDN 开源文档《Gradle 使用指南》中文翻译 Gradle 1.x，**静态多页 wiki**，2026-10-23；原队列条「Gradle 中文使用文档」@百度阅读已下线 → 改吃本站） | 侧栏 `div.left_title > a[href]` 定页面清单（顺序 = 书序，index 是「关于」）；正文容器 `div.markdown-body` | 容器自带边界（`div.previous-and-next` 在容器外，天然不沾） | 37 节点（0 目录 / 37 文档，`NN-中文标题` 前缀免归位；00-关于 + 36 章）；⚠️ **表格表头是 `<td>` 不是 `<th>`**（`<thead><tr><td>`，首行当表头）；代码 `<pre><code>` 无语言类；正文首 H1==侧栏标题则剥；图 `images/*.png` 相对 → 传 CDN **9/9**；六查全绿 + 37 篇逐篇回读 0 差；库 84898768，slug `gradle-guide-20261023`；`examples/udn-gradle/build.py`（坑 59） |
