# EMC 中文支持论坛《SAN 管理入门系列》→ 语雀（Common Crawl 兜底实战）

2026-10-18 实战。**场景：整站下线** —— `community.emc.com/docs/DOC-16067`（系列第 1 篇）
302 到 `dell.com/support`，社区页对 curl / headless 一律 Akamai 403；archive.org 在沙箱被墙。

## 一份薄薄的成绩单

| 项 | 值 |
|---|---|
| 系列 | 8 篇：DOC-16067(一) / 16068(二) / 16069(三) / 16080(四) / 16081(五) / 16082(六) / 16083(七) / 16084(八) |
| 正文来源 | Common Crawl 2019 快照（CC-MAIN-2019-47/39/26/18、2018-43/34） |
| 语雀库 | id=84712887 `SAN管理入门系列（2026-10-18）`，分组「文章收集」36149506 |
| 导入 | `--toc-md` 一次 PUT 0.4s / 结构核对 PASS / 0 失败 |
| 验收 | TOC 8 == 本地 8，同名唯一，8 篇 word_count 全 >0 |
| 图 | 4 张只救回 2 张（第 6/8 篇用 cnblogs pipci 转载镜像；第 1/5 篇源图 CC 未收录，缺） |

## 复用流程

```bash
# 1. 索引 prefix 一次查全 → 拉 WARC → 还原 HTML
python3 cc_warc.py --pages pages.txt --out ./raw \
  --prefix 'community.emc.com%2Fdocs%2FDOC-160'

# 2. Jive 页 HTML → md（改 build_jive.py 顶部 DOCS/SRC/OUT）
python3 build_jive.py

# 3. 图片（转载站镜像补齐的那几张）转语雀 CDN，再删图目录
python3 ../../scripts/yuque_rewrite_images.py ./book ./img_map.json --throttle 3

# 4. 建库 + 移分组 + 导入
python3 ../../scripts/yuque_repo_import.py create-book --name "SAN管理入门系列（2026-10-18）" \
  --slug san-management-primer-20261018 \
  --desc "来源：https://community.emc.com/docs/DOC-16067（EMC 中文支持论坛，站点已下线，正文经 Common Crawl 2019 快照恢复）｜8 篇系列｜导入 2026-10-18"
python3 ../../scripts/yuque_repo_import.py move-stack --book-id <id> --stack-id 36149506
python3 ../../scripts/yuque_tree_import.py --root ./book --book <id> --progress ./progress.json --toc-md
```

## 踩过的点（详见 references/website-crawl-to-yuque.md 坑 36）

1. **只能用 prefix 查索引**：逐条精确查询慢 + 频繁 504；`matchType=prefix&limit=200` 一次拿全，客户端过滤。
2. **"No Captures" 是确定性空，"504/空响应" 要重试**（3-4 次 + sleep）。老 collection（2013-2014）常空，**2018-2019 才是金矿**。
3. **WARC 体剥两层头**：`\r\n\r\n`（WARC 头）→ 再一个 `\r\n\r\n`（HTTP 头）→ 剩下才是 HTML。
4. **项目符是字面字符**：`ü`/`Ø`/`•`/`–`（Word 符号字体），不是 `<ul>`；`<em>` 相邻会拼出 `**` 脏标记 → 直接丢 `<em>`。
5. **附件图基本救不回**：`/servlet/JiveServlet/downloadImage/...` 128 个 collection 前缀查询全空；能救的只有**第三方转载站镜像**（本次 cnblogs `img2020.cnblogs.com`）。缺图如实报，别去新站硬抓（Sprinklr JS 渲染，云爬虫只拿得到评论区）。
