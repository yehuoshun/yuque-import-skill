# 案例：dumi 静态书站 + MathJax SVG 公式（《动手学强化学习》，2026-10-21）

触发链接 `https://hrl.boyuai.com`（张伟楠、沈键、俞勇《动手学强化学习》在线版）。
识别：页面 `generator` 是 **dumi（umi 3.5.17）**，`window.g_useSSR=true` —— 这是**静态 SSR 站**，
正文（含配图/公式）**全在返回的 HTML 里**（`div.__dumi-default-layout-content > div.markdown`），
不需要跑 JS。

**官方 GitHub `boyu-ai/Hands-on-RL` 只有纯代码 notebook**（20 个 `.ipynb`，**0 个 markdown cell**，
README 明说「纯代码版本」）→ **没有正文源可救**，只能抓 HTML。走**网站口径**。

## 结论先行

| 项 | 值 |
|---|---|
| 库 | `动手学强化学习（20261021）` id=84821175 slug=hrl-boyuai-20261021 |
| 分组 | 「文章收集」stack 36149506（网站口径） |
| 节点 | **27**（3 TITLE + 24 DOC：21 章正文 + 前言 + 总结展望 + 课件页） |
| 图 | 84 张（82 个 `/static/*` + 2 个内联 `data:image/png;base64`） |
| 公式 | **1737 处出现 / 795 个唯一**（全 MathJax SVG） |
| 代码块 | 185（Pygments `prism-code language-*`） |
| 耗时 | 上传 879 资源 ~27min（throttle 1.5）+ 导入 ~22s（toc-md） |

## ⚠️ 最大坑：公式只有 MathJax SVG，没有 LaTeX 源

站上每处公式是 `<span class="math math-inline">` / `<div class="math math-display">` 包一个
`<mjx-container><svg>…</svg></mjx-container>`。**TeX 源已不可得**：

- **无 `alttext`**（`grep -c alttext` = 0）
- **无 `<mjx-assistive-mml>` / MathML**（assistive-mml 计数 = 0）
- `<use data-c="…">` 只有字符码，`data-mjx-texclass` 只有粗粒度类别 → 都还原不出 TeX
- umi.js/searchIndex 里也没有正文（`grep 初探强化学习 umi.js` = 0）

→ 结论：**保真只能「把公式当图」**：抽 `<svg>` 存独立 `.svg`，传语雀 CDN（`upload_image` 吃 svg，
返回 `cdn.nlark.com/…/*.svg`），正文内嵌 `![](cdn.svg)`。

### 抽 SVG 的两个硬点

1. **必须贪婪匹配**：MathJax 的伸缩符号（大括号/求和号）会生成**嵌套 `<svg>`** ——
   `<svg …><use/><svg …/><use/></svg>`。用非贪婪 `(<svg\b.*?</svg>)` 会**在第一个内层 `</svg>` 截断**
   （本次 795 个里有 8 个中招 → 文件被截成半截）。改 `(<svg\b.*</svg>)`（配 `re.S`）后 795/795 XML 全部合法。
2. **`ex` → `px` 换算**：MathJax 把尺寸写成 `width="40.603ex"`。当 `<svg>` 被抽成**独立文件**用
   `<img>` 引入时，`ex` 相对字体、不可靠 → 按 `1ex ≈ 8px` 改写成 `px`，尺寸才稳定。
3. 去重：按「去 id/去 href」归一化取 md5（跨页同式复用），1737 处 → 795 个文件。
4. 自检：**每个 svg 的 `xlink:href="#id"` 必须能在自身 `<defs id>` 里找到**（MathJax 的 defs 在
   每个 svg 内部，所以自洽）——本次 795/795 引用全解析、无外链。

## 其它转换要点（`convert.py`）

- **正文窗口**：`__dumi-default-layout-content` 的 `>` 之后 → 到下一个 `<script>`。
  ⚠️ 起止点若从 `index of("__dumi-default-layout-content")` 起，会**把开标签尾巴 `…">` 一起带进去**
  （首跑泄漏 `__dumi-default-layout-content">` 到正文首行）→ 要从 `>` 之后起。
- **代码块**：`<pre class="prism-code language-XXX">`，每行一个 `<div class="token-line">`（含
  `<span class="token …">`）→ 取每个 token-line 的 `get_text()`，一行一段；语言取 `language-XXX`。
  先删 `<button …copy-btn…></button>`。
- **表格**：`<table><thead><tr><th>…</th></tr></thead><tbody>…`；有的外面套
  `div.__dumi-default-table > div.__dumi-default-table-content`。
- **图片**：`/static/xxx.png|jpg|gif` → 下载到 `_img/`；**2 张是内联 `data:image/png;base64`**
  （正文插图，不是装饰）→ 解码存 `_img/data_<md5>.png`。
- **标题锚点**：`<hN id="…"><a aria-hidden="true" …><span class="icon icon-link"></span></a>标题</hN>`
  → 剥掉 `icon-link` 图标与 `a[aria-hidden]`。
- **外链**：`<a target=_blank href=https://…>文字<svg class="__dumi-default-external-link-icon">…</svg></a>`
  → `[文字](url)`，外部图标 svg 自然被丢弃；**站内链**（`href="/chapter/…"`）→ 纯文本。
- **图注**：紧邻图后的 `<center>图1-1 …</center>` → 普通行。
- **部分页**：`/chapter/1` `/chapter/2` `/chapter/3` 是空的（只有翻页器）→ **建成 TITLE 目录**
  （本文库里就是 `01-强化学习基础篇` 等 3 个 TITLE）。
- **课件页**：`/slides` 列 17 个 PDF（`boyuai.oss…/课件pdf/*.pdf`）→ 按硬规则 12，**正文保留官方
  OSS 直链，不上传附件**（老板拍板 B）。

## ⚠️ 子目录相对路径（主 agent 阶段 1 的 bug，子 agent 抓到）

`build.py` 最初给所有 md 写 `_img/x.png`，但 21 篇落在 depth-1 子目录（`01-…/xx.md`）里 →
`yuque_rewrite_images.py`（按 md 所在目录解析相对路径）**全部报「本地缺失」**（dry 报缺失 1821）。
修法：`build.py` 按 dest 深度补前缀 `prefix = "../" * dest.count("/")`，`convert.py` 全部资源引用前拼
`ASSET_PREFIX`。**与 refs 坑 38 同族**（嵌套目录下图片引用要写 `../`）——凡「根级有 `_img/` + 文档落子目录」
的树都要检查这一点。

## 复现命令

```bash
# 0) 拿 URL 清单（sitemap + 页内 href 双查）
curl -sL https://hrl.boyuai.com/sitemap.xml
# 1) 抓 27 页（curl -sL，中文路径别用 py urllib 会 301 自环）
python3 examples/hrl-boyuai/fetch_pages.py
# 2) 转 md（抽 MathJax SVG → _math/，图 → _img/，子目录前缀 ../）
python3 examples/hrl-boyuai/build.py
# 3) 传资源到 CDN + 重写引用
python3 scripts/yuque_rewrite_images.py hrl-clean hrl-img_map.json --throttle 1.5
rm -rf hrl-clean/_img hrl-clean/_math
# 4) 建库 + 分组 + 导入
python3 scripts/yuque_repo_import.py create-book --name "动手学强化学习（20261021）" \
    --slug hrl-boyuai-20261021 --desc "来源：https://hrl.boyuai.com（张伟楠、沈键、俞勇《动手学强化学习》官方在线版，站抓取）｜ 公式为 SVG 图 ｜ 导入 2026-10-21"
python3 scripts/yuque_repo_import.py move-stack --book-id 84821175 --stack-id 36149506
python3 scripts/yuque_tree_import.py --root hrl-clean --book 84821175 --progress hrl-progress.json --toc-md
# 5) 收尾：根级 DOC 归位（prependNode sibling）→ 对账 → 幽灵 0 → 全库 word_count>0
```

验收（六查全绿）：TOC 27 ✅ ｜ 全路径唯一 ✅ ｜ 对账 0 ✅ ｜ 无分片 ✅ ｜ 幽灵 0（docs 24 == TOC DOC 24）✅ ｜ word_count 24/24 >0（252~9030）✅
