# 案例：Elasticsearch 权威指南（中文版）→ 语雀（2026-10-18）

老板给的是**已死的老 GitBook 链接**，最后按「同名源仓库」口径导入。

- 给的链接：`https://legacy.gitbook.com/book/fuxiaopang/learnelasticsearch/details`
  - `legacy.gitbook.com` → **301 跳 gitbook 首页**（老站关闭）
  - `fuxiaopang.gitbooks.io/learnelasticsearch/` → **302 到 `https://www.learnes.net/`**（域名被抢注成空壳页，无正文）
- 实际源：`git@github.com:looly/elasticsearch-definitive-guide-cn.git` @ **ef70bab**（2045★，Elasticsearch 权威指南中文版）
- 库：`Elasticsearch 权威指南（中文版）（ef70bab）`，book_id **84706781**，slug `elasticsearch-definitive-guide-cn-ef70bab`，分组「开源项目」

## 两个脚本

| 脚本 | 干什么 |
|---|---|
| `build_tree.py` | 按 SUMMARY.md 顺序重建整棵树（源是 `NNN_Chapter/NN_Title.md` 扁平编号，层级只在 SUMMARY 里） |
| `rewrite_external_images.py` | 把 md 里的**绝对外链图**（raw.githubusercontent）按 basename 反查本地 `images/` → 传语雀 CDN → 重写引用 |

```bash
# 1. 克隆（raw.githubusercontent / 直连不通时走代理）
git clone https://gh-proxy.com/https://github.com/looly/elasticsearch-definitive-guide-cn.git esdg-src

# 2. 改 build_tree.py 顶部的 SRC / OUT 后重建干净副本
python3 build_tree.py

# 3. 外链图 CDN 化（先 --dry 看命中）
python3 rewrite_external_images.py --dry
python3 rewrite_external_images.py

# 4. 导入（toc-md 模式）
python3 scripts/yuque_tree_import.py --root <OUT> --book <book_id> --progress <账本> --toc-md
```

## 本案例踩到的点（详见 references/github-repo-to-yuque.md 坑 36/37）

1. **图是绝对外链**：`https://raw.githubusercontent.com/<org>/<repo>/master/images/x.png` —— 默认的 `yuque_rewrite_images.py` 只认相对路径，一条都不匹配，必须旁路脚本按 basename 反查本地文件再重写。`elastic.co` 的 11 张外链实测 200，保留。
2. **SUMMARY 大小写与磁盘不符**：`500_Cluster_Admin/` 里全是小写（`10_intro.md`），SUMMARY 写 `00_Intro.md` → 路径解析要大小写不敏感。
3. **SUMMARY 断链**：10 处（5 个章首页 + 4 个文件不存在）→ 章首页兜底 = 该章第一个 intro 类子节提升为章首页（坑 36 的三级兜底）。
4. **SUMMARY 顺序 ≠ 文件名编号**：源编号乱序（05,100,105,10,110…），一律按 SUMMARY 顺序重排 `NN-` / `NN.MM-`。
5. **验收脚本别打爆限额**：`GET /repos/{book}/docs` 的 `page` 参数无效（恒返首页）→ 用 `offset`；TOC 节点的 `id`/`doc_id` 都是空串 → 正文回读取账本 `progress.json` 的 `doc_id`。

## 结果

- 351 节点（36 目录 / 315 文档），0 失败；toc-md 目录树 351 行 15567 字节 → PUT **2.1s**，结构核对 PASS
- 四查：TOC 351 == 本地 351；全路径唯一 True；TOC 路径集合 == 本地集合 True；幽灵 0；CDN 抽 5/5 200
- 根级 `00-前言.md` / `00-版本变动.md` 经 `prependNode` 归位到 36 个 TITLE 之前
