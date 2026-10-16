# 示例：鸟哥的 Linux 私房菜 - 服务器架设篇（cn.linux.vbird.org）

老式 PHP 表格站 → 语雀的**完整可复用**示例（2026-10-16 实战，22 章 / 23 篇 / 218 图）。
通用模板 `scripts/yuque_website_crawl.py` 啃不动这类站（标题不是 h 标签、正文是 div+table 混排、
嵌套表、装饰图墙），所以这里是**站点专用转换器**，抄走改 SITE 常量即可适配同类老站。

## 文件

| 文件 | 作用 |
|---|---|
| `fetch_all.py` | 按 `links.txt` 批量抓页面 → `pages/`（带缓存、UA、重试） |
| `crawl_vbird.py` | 正文窗口 + 迷你 DOM 渲染 → `site/NN-<章名>.md`（图片传语雀 CDN） |

## 复用流程

```bash
mkdir -p tmp/<site> && cd tmp/<site>
cp -r <skill>/examples/vbird-server/* .

# 1) 探站：从目录页抽全站链接
curl -sL -A "Mozilla/5.0" "<目录页 URL>" -o index.html
grep -oE 'href="[^"]*"' index.html | sed 's/href="//;s/"$//' | sort -u > links.txt
#   旧版说明页等按需剔除（本站剔 centos4.php / redhat9.php）

# 2) 全量抓页面
python3 fetch_all.py            # → pages/*.php

# 3) 转换（先 DRY=1 干跑验证，不传图）
DRY=1 python3 crawl_vbird.py    # → site/*.md，图片 src 仍是原 URL
python3 crawl_vbird.py          # 真跑：图片上传语雀 CDN（img_map.json 缓存，重跑不重传）

# 4) 产物级验证（别只看日志）
grep -l "designer\|导航关键词" site/*.md           # 导航污染应为空
grep -lE "<(div|span|table|td|font|img)\b" site/*.md  # 残留标签应为空（代码样例内除外）
#   图片对账：src 非装饰 <img> 数 == md 里 ![...] 数（逐章比）
#   文本对账：md 去掉空白后的字符数 / 源正文 → 1.0~1.2 为正常（差值=新增 H1+日期）

# 5) 导入：yuque_repo_import.py create-book + move-stack → yuque_tree_import.py --toc-md
#    （库名 <网站名>（<日期>），分组「文章收集」36149506）
```

## 本站关键设计（改造成同类站时重点看这几处）

- **正文窗口**：`<!-- 本文的正式部分 -->` → 页脚 `<div style="padding-top: 0px; text-align: center;">`
  - 繁体页的「档头/连结区」标记是繁体（`檔頭部分`/`連結區`），但 **`本文的正式部分` 简繁同形**，
    所以只要一个起点正则；顶部 ImageReady 切片导航图墙、页脚版权区靠窗口直接跳过
- **标题**：`<span class="text_h1">`→`##`、`<span class="text_h2">`→`###`（不是 h 标签）；
  章名在 `text_head0`（内含嵌套 `<span class="text_head_en">`，正则要用 `</span>\s*(?:</a>|<br)` 收尾）、
  更新日期在 `text_history`
- **终端块**：`<table class="term"><td class="term"><pre>` → 代码围栏（用占位符 `@@CODEn@@`，
  渲染完再替换，避免被 `clean_inline` 折叠成行内）
- **表格**：单格 `<table>` → 递归成块（单段文本→引用块；含代码/多块→原样块）；
  多行多列 → markdown 管道表
- **列表**：`ul/ol → li`（带嵌套缩进）、`text_import1/2` → 加粗
- **图片**：`alt in {大标题的图示, 小标题的图示, 鸟哥的图示}` 或 src 含 `logo.png`/`vbird_face.gif` → 剔除；
  其余下载 → `upload_image` 传语雀 CDN → `![alt](cdn)`
- **简繁混排**：检测 `檔頭部分`（繁体章）→ 额外用 opencc `tw2sp` 产出「（简体版）」，原文保留
- **排序**：章号从「第N章」中文数字转阿拉伯后排序（**不是**文件名前缀序，本站前缀分组与章号不一致）
- **分页去重**：站点同时有 `NNNNname.php`（整章全文）与 `NNNNname_1.._N.php`（分页），
  实测全文页 ≈ Σ分页（比值 1.01~1.06）→ **只导全文页**（`_\d+\.php$` 排除）

## 已知坑

见 `references/website-crawl-to-yuque.md` 坑 **23~26**（全文页/分页去重、装饰图剔除、
span 标题站先归一化、简繁混排另出简体版）。

## 依赖

- `opencc-python-reimplemented`（简体版；PyPI 直连不通时走镜像：
  `pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com opencc-python-reimplemented`）
- 图片上传需要语雀 cookie/ctoken（`skills/yuque-ai-mcp/config/config.json`，`--user-id` 默认 25689388）