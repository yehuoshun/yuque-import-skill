# examples/bootstrap5-zh — Bootstrap 5 繁體中文手冊（六角學院）

fpb52 #121 · 库 85181327 · 站点 bootstrap5.hexschool.com/docs/5.1 · 2026-10-31

**没有公开的 md 源仓库**（hexschool/bootstrap_zh 只有 docs/4.2；hexschool/bootstrap5 的 gh-pages 只有渲染后的 HTML）
→ 走网站口径：抓 `div.bd-content` 转 Markdown。

## 复现

```bash
mkdir -p /tmp/fpb121 && cp build.py reorder.py /tmp/fpb121/ && cd /tmp/fpb121
python3 build.py          # 抓 98 页 → build/（raw/ 有缓存，可重跑）
# 传图（3 张 brand svg）→ 删 build/assets → 建库 → 导入
python3 <skill>/scripts/yuque_rewrite_images.py build img_map.json --cookie-config <cfg>
rm -rf build/assets
python3 <skill>/scripts/yuque_repo_import.py create-book --name "Bootstrap 5 繁體中文手冊（2026-10-31）" --slug bootstrap5-zh-20261031 --desc "..."
python3 <skill>/scripts/yuque_tree_import.py --root build --book <id> --progress progress.json --toc-md
TOKEN_L91=... python3 reorder.py <book_id>   # 根级归位成站点顺序
```

## 转换要点

- 侧栏 `nav#bd-docs-nav` = 10 分区的分组名/篇名/顺序，全量 97 页；另加 `/docs/5.1/migration/` 作根级 `90-Migrating to v5.md`
- 正文容器 `div.bd-content`；`div.bd-example`（实时预览）**整体丢弃**，示例源码在紧随其后的 `div.highlight > pre > code[class=language-*]` 里，`get_text("")` 可无损还原（**别用 `get_text(" ")`，Chroma 的 span 会被插空格**成 `< button type = "button"`）
- `div.bd-callout` → `> **标题**` 引用块；`table` → md 表；`div.list-group` 里一堆 `<a><img>`（Team 页）要逐条转 `- ` 列表，否则会糊成一行
- 站内链接 `/docs/5.1/...` → 补成绝对 URL；`/docs/5.1/assets/*` → `assets/*`（子目录文档要写 `../assets/`，rewrite 按 md 所在目录解析）
- ⚠️ `--dry` 报的 92 处「本地缺失」全是代码样例里的 `<img src="..." alt="...">` 占位符，非真缺图
- ⚠️ toc-md 生成的根级顺序按 Unicode 排（元件/內容/工具/快速開始…）→ `reorder.py` 用「prependNode 提首个 + 逐项 appendNode 到前一个之后」链式归位，一通到底

结果：109 节点（10 目录 / 99 文档），3 图 CDN；六查全绿。