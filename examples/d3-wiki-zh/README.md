# d3.wiki 中文手册（fpb52 #175，2026-11-01）

- 源：`git@github.com:mbostock/d3.wiki.git` @ `cecbbd1e`（GitHub 官方 wiki 仓库，可独立 SSH 克隆）
- 库：85212595 `d3官方API中文手册（cecbbd1e）`（slug `d3-wiki-zh-cecbbd1e`）
- 发布面：46 中文页 = 3 根文档（00-说明 / 01-D3.js 简介=CN-Home / 02-API 中文手册）+ 37 专篇挂 7 分组 TITLE（核心函数/地理/几何/布局/比例尺/SVG函数/行为）= 47 节点；时间分区未译不建；英/日/俄/繁/印尼页不收；剔 6B 垃圾页 `捆布局.md`
- 图：65 张本地（含 6 张 `github.com/mbostock/d3/wiki/*.png` 本地化）传 CDN；bl.ocks.org 外链 49 保留；f.cloud.github.com 死链 2 标注；wikimedia 外链 2
- `build.py`：wiki 语法转换器（面包屑剥 / `[[a|b]]` / 站内链→纯文本 / `<a name>` 签名行→行内反引号并剥 `**`/`*` / `[[label](url)]` 译者签名 / 标题降级 / 子目录图引用 `../` 前缀）
- 教训：**改 last-imported.json 用 indent=2**（当前文件就是 indent=2；11-01 凌晨记的「indent=1」与现状不符，v1.3.259 曾因此全文件重排，v1.3.260 修正）
