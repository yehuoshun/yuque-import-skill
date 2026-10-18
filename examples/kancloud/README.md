# 看云（kancloud）书 → 语雀（2026-10-18）

源：`http://www.kancloud.cn/kancloud/a-programmer-prepares`（《程序员的自我修养》，20 章 / 124 篇）
成品：库 id `84705560`「程序员的自我修养（2026-10-18）」slug `a-programmer-prepares-20261018`，
**144 节点**（20 目录 / 124 篇），分组「文章收集」，四查全绿。

## 要点

1. **SEO 副本站就是 md 源码**：`div.seo > div.content` 里是**未渲染的 markdown**（HTML 转义）——
   `html.unescape` 后去掉统一左缩进直接落盘，比抓渲染后的正文干净得多
2. **目录取两处**：
   - 任意内容页的 `div.catalog > ul > li > a` → 全部条目（124 条，单层平铺，id 连续）
   - 书首页 `/kancloud/<book>` 的目录链 → **主章清单**（20 条）
   - 主章 id 之间的条目 = 该章的子节 → 建 `NN-主章/` 目录，内含 `NN-主章.md` + `NN.M-子节.md`
     （`-`(45) < `.`(46)，主章文件自然排第一）
3. **图床防盗链**：`box.kancloud.cn` 裸请求 403，**必须带 `Referer: http://www.kancloud.cn/kancloud/<book>`** 才 200
   → 见 `kancloud_images.py`（带 Referer 下载 → 语雀 CDN → 重写 md 引用，img_map 缓存）
4. 个别页 `div.content` 为空（作者没写）→ 用 `# 标题` 占位，避开语雀「正文不能为空」校验

## 用法

```bash
python3 crawl_kancloud.py          # 抓全部页 → tmp/programmer-prepares-clean/
python3 kancloud_images.py         # 图床转 CDN + 重写
```
换书：改 `BASE`/`MAIN_IDS`（主章 id 从书首页拿）/`OUT`/`CACHE`。