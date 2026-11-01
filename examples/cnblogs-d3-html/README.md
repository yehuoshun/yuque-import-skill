# 案例：博客系列页 HTML → md（博客园 cnblogs 标签页）（《楚狂人的D3教程》，2026-11-01）

触发链接是博客园**标签页** `cnblogs.com/winleisure/tag/D3.js/`（文章列表，不是书）。
走网站口径（库名带导入日期、分组「文章收集」stack 36149506）。

## 结论先行

| 项 | 值 |
|---|---|
| 库 | `楚狂人D3教程（2026-11-01）` id=85212142 slug=chukuangren-d3-20261101 |
| 节点 | **8**（00-说明 + 7 篇笔记） |
| 图 | 36 张原文站 dashingd3js.com 已关闭 → 全标注「原图缺失」；1 张 cnblogs 图床图传 CDN |
| 六查 | 全绿（幽灵 0 / 回读 3 篇逐字符相等） |

## 抓取要点

1. **标签页文章列表**：新版模板是 `<div class="PostList" role="article">` 包 `<div class="postTitl2"><a ...><span>标题</span></a>`，不是老的 `postTitle2`；正则按 `PostList` 块切。
2. **正文容器**：`<div id="cnblogs_post_body" class="blogpost-body blogpost-body-html">`，**内部有嵌套 div**，非贪婪 `(.*?)</div>` 会被内层截断 → 必须**配平 div 深度**提取。
3. **懒加载图**：`<img ... data-src="//images0.cnblogs.com/...">`，必须读 `data-src`（`src` 为空或是占位），并用 `![]()` 里的 `src` 而不是 `data-src` 属性名判断。
4. **「点图看大图」包装**：`<a href="大图"><img data-src="小图"></a>` → 转换时剥掉链接只留图（否则产生 `[![...](a)](b)` 嵌套，且 b 若未下载会成死链）。
5. 图床判断：`images0.cnblogs.com` 仍可用（真下真传 CDN）；`dashingd3js.com` 这类原文站多年后基本 404 → 统一替换成 `> 🖼 原图缺失（原站 xxx 已关闭）：alt` 引用块，别留叉图。

## 转换器坑（build.py）

1. **`render()` 入口必须 `lstrip()`**：正文片段常以缩进空白开头，`re.match(r'<tag...')` 锚定失败 → 落到 `strip_tags` 兜底 → **整篇标签被剥光、图片和代码块全丢**（本文档首版就是这个 bug，正文 39KB 只剩 27KB 纯文本）。
2. **自闭合标签 `img`/`br` 不匹配 `<(tag)>(.*?)</\1>`**：必须在 `render_children` 开头先用 `re.sub(r'<img\s+([^>]*?)/?>', ...)` / `<br\s*/?>` 预处理，否则图全丢。
3. **md 图片 alt 里不能有 `]`**（如 `xxx[2]`）：`yuque_rewrite_images.py` 的 `MD_RE = r'!\[[^\]]*\]\('` 会在 `]` 处截断导致**整条图片引用不被识别（图不上传、不重写，静默跳过）** → 转换时洗掉 alt 里的方括号。
4. 博客园作者常用 `<p><strong>xxx</strong></p>` 充当小标题（没有 `<h2>`），转成 `**xxx**` 可接受，不必强行造标题层级。
5. 代码块是 `<pre>` + `<span style="color:...">` 语法高亮 → 剥 span 取 `itertext`，语言按内容猜（`javascript`/`html`）。

## 收尾坑

- **先做图重写，再导入**：toc-md 模式不更新已存在文档正文；图没传上去就导入 → 只能删库重导（本例删 85212126 重建 85212142）。
- 删库后**必须删 progress 账本**，否则节点全 skip、新库空、TOC 挂旧 doc_id。