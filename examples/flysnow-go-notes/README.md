# flysnow.org「Go语言实战笔记」三系列（fpb52 #105）

- 索引来源：GitHub 仓库 `rujews/go-in-action-notes` @ `3da951a` —— **README 只是外链清单**（3 系列 41 条），正文全在作者博客。
- 正文来源：`https://www.flysnow.org`（Astro 新主题，正文容器 `div.post-content`）。
- 坑：README 里 Gin 系列 6 条给的是**微信公众号链**（`mp.weixin.qq.com`，抓取返回「环境异常」反爬页）→ 换官网**同系列同序** 6 页（H1 逐条核对一致）。
- 转换：`h2/h3` → 标题；`div.highlight > pre[data-language]` → 围栏（`span.line` 逐行）；表格 → Markdown；行内 `code/a/strong` 还原；剔页尾「本文为原创文章 / 欢迎扫码关注公众号」+ 二维码图 + 「精彩文章推荐」导航尾块；内部 `<a>` 包图 → 直接出 `![]()`。
- 产出：45 节点（3 TITLE / 42 DOC），六查全绿；库 85155035（slug `go-in-action-notes-20261031`，网站口径-文章收集）。

用法：
```bash
python3 fetch.py          # 抓 41 页（README 索引解析 + 1.2s 节流）
python3 build.py          # 转 md 到 build/（含图片本地化）
```
