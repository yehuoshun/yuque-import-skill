# LFS 6.2 中文版（Linux 构建指南）→ 语雀

2026-10-17 实战固化。源 = 金步国翻译的 **LFS 6.2 中文版**（Linux From Scratch，金步国 0-5 章 /
ipconfigme 6-7 章 / bobkey 8-9 章，2008-03-01 最终正式版）。

## 源站现状（重要）

- 老板给的入口 `http://works.jinbuguo.com/lfs/lfs62/index.html` → **NXDOMAIN**（子域已注销）
- `www.jinbuguo.com/lfs/lfs62/` 仍被官方引用（linuxfromscratch.org/lfs/read.html 的 6.2 中文链接指向它），但 **502**（应用层挂）
- 完整镜像（155 文件，含全部页面 + images/icon + css，UTF-8）在 GitHub：
  `github.com/p-moon/develop-reference-data` 的 `www.jinbuguo.com/lfs/lfs62/` 目录
  （该仓库是个人「开发参考资料」聚合库，稀疏 checkout 只拉这一个目录即可）
- 官方 LFS 6.2 英文 HTML：`linuxfromscratch.org/museum/lfs-museum/6.2/LFS-BOOK-6.2-HTML/`（koddos 有镜像）

## 技术要点（详见 references/website-crawl-to-yuque.md 坑 30）

- **DocBook XSL 老多页站**（与 svnbook 同族）：`navheader / div.wrap(正文) / navfooter`，
  正文块 = titlepage(h1) + div.package(segmentedlist 属性) + div.installation(安装流程) +
  div.note/important（admonhead/admontitle + admonbody）+ pre.userinput(命令) + pre.screen(输出) +
  variablelist(dl) + itemizedlist(ul)，表格只有少数页有（entry 简单）。
- ⚠️ **老 HTML 表格不闭合 → bs4 会把 navfooter 吸进 wrap**（e2fsprogs 实踩）：
  渲染前必须 `soup.find_all("div", class_=["navfooter","navheader",...])` 整体 decompose，防导航污染
- 页面顺序 = **index.html `div.toc` 里所有 `<a>` 的出现顺序**（扁平）；toc 的 ul 嵌套树在本站不靠谱
  （章 li 会混入后续章节的节条目，按树分组必错）。
- 章标题 = 各章首页（chapterXX/chapterXX.html）的 h1；章首页输出文件名用章标题，不用 toc 锚点文字。
- 行内：`<tt class=filename>/<kbd` → 反引号；`variablelist` 的 dt 包 ** 时先 `strip("*")` 防 `***` 三层；
  note 头部的 icon `<img>`（images/*.png）→ 装饰，全跳过（零 CDN 上传）。
- 导入后 root DOC（00-前言与全书目录.md）落最后 → prependNode 归位（skill 坑 29 同款）。

## 复现

```bash
git clone --depth 1 --sparse https://github.com/p-moon/develop-reference-data.git pmoon   # 直连 502 走 gh-proxy
cd pmoon && git sparse-checkout set www.jinbuguo.com/lfs/lfs62
cd .. && python3 crawl.py    # → clean/（1 + 11 目录 + 142 篇）
# 建库 move-stack（文章收集 36149506）→ yuque_tree_import --toc-md
# 收尾：prependNode 前言归位 + editNode 把 chapterNN- 前缀目录名改成 `N. 章标题` + appendNode 附录移末尾
```

## 本单结果

- 库 `84676049`「Linux 构建指南（LFS 6.2 中文版）」slug `lfs-6.2-zh-20261017`，分组「文章收集」(36149506)，private
- 153 节点（11 目录：序言 + 第 1-9 章 + 附录；142 文档：前言+目录 1 + 序言 7 + 各章 131 + 附录 3），0 失败
- 无图片上传（全站图=装饰 icon）；四查全绿（错位 0 / verify PASS / 幽灵 0 / 抽查 5 篇逐字符等长）