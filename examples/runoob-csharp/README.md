# 菜鸟教程（runoob）整教程系列 → 语雀（2026-10-28 换源实战）

**首例（整系列）**：C# 教程（`runoob.com/csharp/`）→ 库 **85069246**（slug `runoob-csharp-20261028`，分组「开源项目」待补），41 文档平铺 + 12 图 CDN，六查全绿。
（先例 #29 是同一转换器的单系列「正则表达式」13 篇 → 84956009。）

## 什么时候用它

书单条目是**商业版权书无免费正文**，需要换源到同主题免费中文教程，且目标站 = **菜鸟教程**：
- `div.article-intro#content` 正文窗口（右侧栏/广告/导航全在窗外）
- 代码块 `div.example_code` / `pre`（含 `hl-*` 高亮 span）
- 交互工具块（tryit/quiz/在线测试框）无正文价值 → 剥除不收录

## 用法

```bash
python3 examples/runoob-csharp/fetch.py     # 42 页 → pages/（左栏链接写死在脚本里）
python3 examples/runoob-csharp/build.py     # → site/ 平铺 md（图自动传 CDN）
python3 scripts/yuque_repo_import.py create-book --name ... --slug runoob-<主题>-YYYYMMDD --desc "..."
python3 scripts/yuque_tree_import.py --root site --book <id> --progress <p> --toc-md
```

## 关键点

1. **左栏 = 目录**：`<div id="leftcolumn">` 的 `<a href="/csharp/...">` 顺序即章节序；标题「C# 教程」这种就是**目录首页**（有简介正文）→ 收为 01；「语言测验」（quiz）交互页不收录。
2. **换源判定流程（#68 实踩）**：豆瓣商业书页（Pro C# 5.0，人邮社）无免费正文 → ① GitHub 搜仓库：全无正文（个人读书笔记 17KB / 视频课配套 .cs / 随书代码）② **learn.microsoft.com 官方文档正文是权限墙**：正常 UA SSR 输出「访问此页面需要授权」（正文 `<div class="content">` 里只有 `<h1>`），Googlebot UA 直接被 Akamai Access Denied → 官方站抓不了 ③ 落到 runoob 同主题教程。
3. **站内链接纯文字化**：`/csharp/xxx.html` → 只留文字（点过去是站外原站）；`/try/` 交互链接剥；外链保留 `[文字](URL)`。
4. **图**：runoob 图在 `wp-content/uploads/`，每篇几张（流程/架构图），`img_to_cdn` 断点续传（img_map.json）；**代码块里的 `<int>`、`<access specifier>` 是 C# 语法占位符不是 HTML 残留**，别误判清洗。
5. **平铺 41 篇无目录** → 无坑 29 根级 DOC 乱序问题；文件名 `NN-标题.md` 顺序即 TOC 顺序。
