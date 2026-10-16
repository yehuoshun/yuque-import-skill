# 示例：鸟哥的 Linux 私房菜 - 基础学习篇（cn.linux.vbird.org/linux_basic）

`examples/vbird-server/` 的**同站适配版**（2026-10-16 实战，27 章 + 附录 A/B + 快速索引 = 30 篇，269 张图）。
站点排版与服务器架设篇完全相同（老式 PHP 表格站、标题用 `span.text_h1/h2`、正文 div+table 混排、装饰图墙），
**所以只需要改下面 4 处**，其余转换逻辑整段复用。

## 与 vbird-server 的 4 处差异

| # | 位置 | 服务器架设篇 | 基础学习篇 |
|---|---|---|---|
| 1 | `BASE` | `.../linux_server/` | `.../linux_basic/`（`link_md` 里过滤内链的关键词同步改成 `linux_basic`） |
| 2 | 章号 | 第一章起（中文数字不含「零」） | **第零章**起 → `CN` 映射加 `"零": 0`，章号正则 `第([零一二三四五六七八九十]+)章` |
| 3 | 正文窗口起点 | `<!-- 本文的正式部分 -->` | 同上，**但附录 A 页只有 `<!-- 本文的档头部分 -->`** → `find("本文的正式部分")` 失败后 fallback `find("本文的档头部分")` |
| 4 | 无章号页 | 无 | 附录 A / 附录 B / 快速索引 → 伪章号 `27/28/29` 接在章节后；标题改写成「附录 A：…」「…快速索引」（索引页 `text_head0` 是站点名，不能直接当标题） |

> 本篇**全简体**（`檔頭部分` 检测为假）→ 不触发简繁双版逻辑，无需 opencc。

## 文件

| 文件 | 作用 |
|---|---|
| `crawl_basic.py` | 正文窗口 + 迷你 DOM 渲染 → `site/NN-<章名>.md`（图片传语雀 CDN） |
| `fetch_all.py` | 同 `examples/vbird-server/fetch_all.py`（把 `BASE` 改成 `linux_basic` 即可，此处不重复放置） |

## 复用流程

```bash
mkdir -p tmp/vbird-basic && cd tmp/vbird-basic
cp -r <skill>/examples/vbird-server/fetch_all.py .
cp -r <skill>/examples/vbird-basic/crawl_basic.py .
sed -i 's#linux_server/#linux_basic/#' fetch_all.py

# 1) 探站：目录页抽全站链接（本页含分页 _N.php，用 _\d+\.php$ 排除）
curl -sL -A "Mozilla/5.0" "http://cn.linux.vbird.org/linux_basic/linux_basic.php" -o index.html
grep -oE 'href="[^"]*"' index.html | sed 's/href="//;s/"$//' | sed 's/#.*//' | sort -u > links.txt
#   只保留顶层章节页，剔除分页 / 子目录（旧版 RedHat6.1、Mandrake9.0、FC4）/ 主站链接
#   本章节页正则：^\d{4}[A-Za-z0-9_.-]*\.php$ 且不含 _\d+\.php$

# 2) 全量抓页面 → pages/
python3 fetch_all.py

# 3) 转换（先 DRY=1 干跑，再真跑传 CDN）
DRY=1 python3 crawl_basic.py
python3 crawl_basic.py            # 真跑：269 张图传 CDN（img_map.json 缓存，重跑不重传）

# 4) 产物级验证（别只看日志）
grep -lE "<(div|span|table|td|font|img|p|br)\b" site/*.md    # 残留标签应为空（代码样例除外）
grep -liE "ImageReady|SpryMenu|designer" site/*.md           # 导航污染应为空
grep -c 'img FAIL' crawl.log                                 # 0
grep -oh '!\[' site/*.md | wc -l                             # == img_map.json 条数 == 各章 src 非装饰 img 数之和
#   逐章对账：src 非装饰 <img> 数 == md 里 ![...] 数（本实战 269/269，逐章全对齐）
#   文本对账：md 去空白 / 源正文 → 1.0~1.2 正常（差值=新增 H1+日期）

# 5) 导入：create-book → move-stack（分组「文章收集」36149506）→ yuque_tree_import.py --toc-md
```

## 实战结果（2026-10-16）

- 库 **84644854**「鸟哥的Linux私房菜-基础学习篇（2026-10-16）」slug `niaoge-linux-basic-20261016`，归「文章收集」✅
- 30 篇（27 章 00~26 + 附录 A/B + 快速索引），2.6MB，最大 ch08 磁盘与文件系统 95.9KB（未超 512KB 不分片）
- 导入 22:53:54→22:54:25（`--toc-md` 一次 PUT 0.7s），**0 失败**
- 四查全绿：reconcile 30/错位 0；verify PASS；幽灵 0（docs 30 == TOC DOC 30）；抽查 5 篇 body 与本地逐字节等长、CDN 图到位、尾部一致

## 依赖

- 图片上传需语雀 cookie/ctoken（`skills/yuque-ai-mcp/config/config.json`，`--user-id` 默认 25689388）
- 本篇不触发简繁转换，故**不需要** opencc