# 网站抓取 → 语雀导入 SOP（2026-10-13 固化）

> 触发模板：「把 <网址> 抓取到语雀」「这个网站教程导到语雀」。
> 实战源（按时间）：gitref（content_box 容器）、Nulab（Gatsby page-data + 图片抠图）、
> Git Magic（DocBook content div）、廖雪峰（Tailwind 站，评论区 JS 带偏窗口事故）。
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
