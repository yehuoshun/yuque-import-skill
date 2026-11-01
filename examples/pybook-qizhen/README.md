# Docusaurus sidebars 定序书仓 → 语雀（2026-11-01 #249 py.qizhen.xyz 实战）

**触发**：`<sub>.qizhen.xyz`（ruanqizhen 系列站）Python 教程，源仓库 `ruanqizhen/python_book`（与 #8 labview_book / #10 cocode 同套路）。

## 库信息
- 库 85209159 / slug `python-book-bfca014` / 开源项目口径
- 源：`https://github.com/ruanqizhen/python_book @ bfca014`
- 64 节点（6 目录 / 58 文档）/ 17 图 CDN（每组拷全量副本，img_map 去重）/ 六查全绿

## 要点
1. **sidebars.js = 发布面定序**（category label = 目录名，items = 文档 id = 文件名去 .md）
2. 前言 = `README`（type: doc），尾声 = `epilogue`，`type: link` 外链剔
3. 只吃 `docs/` 中文 md；**剔 `i18n/en/`**（英文版整树）和 src/static/Microsoft/ 脚手架
4. 图引用 `images/xxx.png` 相对 md 所在目录 → **每个分组目录拷一份全量 images/**（rewrite 按 md 目录解析；img_map 缓存同名去重）
5. 剥 frontmatter（`---` 块）与首个 H1（标题由文件名给）
6. 文档标题 = 首个 H1（若无用文件名）

## 复用
```bash
python3 build.py  # 输出 site/（58 md + 6×17 图副本）
# 之后：yuque_rewrite_images.py 传 CDN → 删各 images/ 目录 → tree_import --toc-md → 六查
```
