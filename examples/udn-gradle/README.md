# UDN 开源文档 wiki → 语雀（网站口径）

**首例**：`http://doc.yonyoucloud.com/doc/wiki/project/gradle/`（《Gradle 使用指南》中文翻译）
**导入**：2026-10-23 ｜ 库 **84898768**（`Gradle 使用指南（2026-10-23）` / slug `gradle-guide-20261023` / 分组「文章收集」36149506 / 37 节点）

> 背景：队列条「Gradle 中文使用文档」原本指向 `yuedu.baidu.com/ebook/f23af265998fcc22bcd10da2`（百度阅读），
> 该电子书已随平台下线（302 跳 `yd.baidu.com` 首页）、Wayback 连不上 → 老板拍板换源到 UDN 这本同主题中文译本。

## 站点结构

- **静态多页 wiki**：书根 `.../gradle/`，页面 = `index.html` + 36 个 `<slug>.html`。
- **侧栏页面清单**：每页都有 `div.left_title > a[href]`，按 DOM 顺序 = 书的顺序；`index.html` 是「关于」页。
- **正文容器**：`div.markdown-body`。紧跟其后的 `div.previous-and-next`（上一篇/下一篇）+ 百度分享按钮都在容器外 → 天然切掉。
- 扁平无层级（章之间无嵌套），中文标题只在侧栏（正文 `<h1>` 与之相同）。
- 图片：`images/*.png` 相对路径，全站 9 张。

## 转换要点（`build.py`）

1. `get_pages()`：抓 `index.html` → `div.left_title > a[href]` → `[(href, 中文标题)]`（去重、保序）。
2. 逐页抓 HTML → `div.markdown-body` → bs4 递归渲成 markdown（复用 `examples/wizardforcel-gitbook/build.py` 的 `render/inline`）。
3. 文件名 `NN-中文标题.md`（`00-关于.md` 是 index）→ toc-md 下天然免归位。
4. 图片：相对路径 → 下载 → 传语雀 CDN → 重写（`img_map.json` 断点续传）。
5. **正文首个 H1 == 侧栏标题 → 剥**（语雀侧已有文档标题）。

### 本案例特有的坑（坑 59）

- ⚠️ **表格表头是 `<td>` 不是 `<th>`**：站点 74 个表格全是 `<thead><tr><td>…</td></tr></thead><tbody>…`，
  表头行也是 `<td>` → `table_md()` 取 `find_all(["td","th"])`、**首行当表头**即可（不要只认 `<th>`，否则表头会丢）。
- 代码块是 `<pre><code>`（无 `language-*` 类）→ 无语言围栏。
- 零星脏标签 `<s1><e2>…</e2></s1>`（scala-package 1 处）→ fallback 分支递归渲染后自然只剩文字，无需特判。
- 页面会有「继续阅读 XXX」这类正文句子，**不是**截断标记；判截断要看正文末句是否完整 + 有无「剩余 N 页未读」类文案（本站无，全文完整）。
- 站点偶发 5xx/超时 → `fetch()` 退避重试（6 次，2+2i 秒）。

## 用法

```bash
source ~/.openclaw/secrets/credentials.env   # TOKEN_L91
python3 build.py \
  --base "http://doc.yonyoucloud.com/doc/wiki/project/gradle/" \
  --out /home/admin/.openclaw/workspace/tmp/gradlezh/site \
  --img-map /home/admin/.openclaw/workspace/tmp/gradlezh/img_map.json
# 然后：create-book → move-stack 36149506 → yuque_tree_import.py --toc-md → 对账 → 六查
```

换同族的 UDN wiki 书（如 `.../doc/wiki/project/<别的书>/`）只要换 `--base`。

## 实测结果（2026-10-23）

- 侧栏 37 页 → 37 md；9 图全传 CDN（0 失败）。
- toc-md 目录树 37 行 / 1608B，**PUT 0.7s**、结构核对 PASS、0 失败；根级全 DOC 无排序问题。
- 六查全绿：TOC 37 == 本地 37、全路径唯一、对账 0、幽灵 0（docs 37 == TOC DOC 37）、37 篇 word_count 全 >0、逐篇回读 **37/37 逐字符相等**。
