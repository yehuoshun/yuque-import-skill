# 《Ubuntu 参考手册》抓取器（MediaWiki 站，2026-10-18）

源：`http://wiki.ubuntu.org.cn/UbuntuManual`（Ubuntu 中文 wiki，MediaWiki 1.42；改自 Debian 中文参考手册）
成品：库 id `84683525`「Ubuntu 参考手册（2026-10-18）」slug `ubuntu-manual-20261018`，17 页平铺，四查全绿。

## 站点特征 / 关键决策

- **`api.php` 被 Cloudflare 拦**（https 403 "Just a moment…"，http 301→https），但**普通页面路径放行** → 只能抓 HTML（带浏览器 UA）
- 页面清单：抓 `/分类:Ubuntu_参考手册` 页面的成员链接（17 个），而不是 API（`list=categorymembers`）
- 页面 URL：`/UbuntuManual:Ubuntu_基础`（空格→`_`，整体 `urllib.parse.quote`）
- 正文容器 `div.mw-parser-output`；正文起点 = 第一个带 `span.mw-headline` 的 h2
- **丢弃**：顶部导航 ul（"…导航"）+ 导航 table + 自动目录 `div.toc`；**每页尾部的 MediaWiki 调试块**（`NewPP limit report` / `Transclusion expansion time report`）截断
- 站内链接剥成纯文本；`sup.reference` / `span.mw-editsection` 丢弃；`<nowiki>` 清洗
- 本手册无图（`img` 0 张）→ 无需 CDN

## 用法

改 `PAGES`（输出名, 页面名）清单即可复用；`python3 crawl_ubuntu_manual.py [输出名子串]` —— 带参数只抓指定页（便于迭代调试）。
