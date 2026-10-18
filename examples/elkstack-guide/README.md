# ELKstack 中文指南（chenryn/ELKstack-guide-cn）→ 语雀

**实战日期**：2026-10-18 ｜ **来源**：`http://kibana.logstash.es`（老板给的列表链接，**域名已死，DNS 不解析**）
**源仓库**：`https://github.com/chenryn/ELKstack-guide-cn` @ **a30092e**（764★，饶琛琳，纯 GitBook 源；仓库 `homepage` 字段就写着 `http://kibana.logstash.es/` → 确证「站点 = 本仓库」）
**落点**：语雀库 id **84707435**「ELKstack 中文指南（a30092e）」，slug `elkstack-guide-cn-a30092e`，分组「开源项目」(57018723)
**规模**：**230 节点（34 目录 / 196 文档）**；92 张本地图传 CDN（93 处引用）

---

## 复用流程

```bash
# 1. 站点 → 源仓库（站点 DNS 死了也别慌，先查 GitHub 同名仓库 / 搜书名）
gh api "search/repositories?q=ELKstack&sort=stars" --jq '.items[] | "\(.full_name) ★\(.stargazers_count)"'
git clone --depth 1 https://gh-proxy.com/https://github.com/chenryn/ELKstack-guide-cn.git elkstack-src

# 2. 重建干净树（本目录 build_tree.py，改顶部 SRC/OUT 即可）
python3 build_tree.py

# 3. 本地图 → CDN（脚本会把 _imgs/ 里的图按相对路径引用上传并重写）
python3 scripts/yuque_rewrite_images.py <OUT> <img_map.json> --throttle 1.5
rm -rf <OUT>/_imgs                       # 硬规则 10：图片目录必须删

# 4. 建库 + 移分组 + toc-md 导入
python3 scripts/yuque_repo_import.py create-book --name "ELKstack 中文指南（a30092e）" \
    --slug elkstack-guide-cn-a30092e --desc "http://kibana.logstash.es/ @ a30092e"
python3 scripts/yuque_repo_import.py move-stack --book-id <id> --stack-id 57018723
python3 scripts/yuque_tree_import.py --root <OUT> --book <id> --progress <账本>.json --toc-md

# 5. 根级 DOC 归位（toc-md 会把根级 DOC 排到 TITLE 目录之后）
#    PUT /toc {action:prependNode, action_mode:sibling, node_uuid:<根级DOC>, target_uuid:<第一个TITLE>}
```

实测：196 篇建文档 ~2.5 分钟（0 失败），toc-md 230 行目录树 **PUT 1.6s**，结构核对 PASS。

---

## 这个仓库的四个形状特征（都在 build_tree.py 里处理了）

1. **SUMMARY.md 是唯一的结构来源**，4~5 层嵌套、中文标题 + 英文扁平磁盘路径（`logstash/plugins/filter/grok.md`）
2. **空链接纯分组节点**：`* [插件配置]()`、`[接口使用示例]()`、`[性能优化]()`、`[output配置]()` → 落成 **TITLE 目录、无文档**
3. **4 个目录首页断链**：SUMMARY 引用 `elasticsearch/auth/README.md`、`elasticsearch/hadoop/README.md`、`elasticsearch/monitor/api/README.md`、`logstash/performance/monitor/README.md` 但**文件不存在** → 同样落成 TITLE 目录（无落地页）
4. **孤儿文件 35 篇**（未被 SUMMARY 引用）：`kibana/v3/**` 旧版 Kibana 3 整编 + `kibana/v5/README.md` + `kibana/difference.md` + `elasticsearch/auth/searchguard.md` + `elasticsearch/monitor/marvel.md`。书的前言明说「K3/K4 并存，本书分别讲解」，master 的 SUMMARY 却已移除 v3 → **按「内容不丢」口径全部纳入**：
   - `kibana/v3/**` → 顶级组 `05-Kibana 3（旧版）`（镜像源目录，子目录名中文化：advanced→进阶 / auth→认证与权限 / dashboard→仪表板 / panels→面板详解 / source-code-analysis→源码解析；文档标题取首个 `# ` H1，无 H1 回退文件名）
   - `kibana/v5/README.md` → Kibana 5 组内 `04.00-Kibana4（章节首页）.md`
   - `kibana/difference.md` → 根级 `06-Kibana 各版本的对比.md`
   - searchguard / marvel → 追加进 `03.14-权限管理` / `03.15-监控方案`（编号取组内已有最大号 +1）

## 命名规则（点分编号，保证同级排序）

```
节点号 = 点分路径 "01" / "01.01" / "01.01.01"
有子节点 → 目录 "<num>-<title>/"；节点链接存在 → 目录内落地页 "<num>-<title>.md"
无子节点 → 文件 "<num>-<title>.md"
根级 README.md → "00-前言.md"
```
`'-'(0x2D) < '.'(0x2E) < '0'(0x30) < 字母 < CJK` → 落地页 `04-Kibana 5.md` 天然排在
`04.00-…` / `04.01-…` 之前；子目录 `01.01-入门示例/` 排在落地页之后。**（不要用 `_` 或空格：`'_'=0x5F` 会把落地页顶到字母标题后面）**

## 外链图片：能救的救，救不了的别浪费时间

105 处外链图里 **约 45 处已死**：`www.elasticsearch.org/*`（302 到 elastic.co 首页，返回 HTML）、
`www.elastic.co/guide/en/kibana/current/images/*`（Kibana 文档改版后 404）、`logstash.es`、`timroes.de`、
`www.elastic.co/guide/en/marvel/...` 等。判定与处理：

- **必救**：`raw.githubusercontent.com` / `github.com/*/raw/*`（CN 不可达 + 会裂图）→ 本次 5 处，**build_tree.py 里预下载**（走 `gh-proxy.com`）落进 `_imgs/`，交给标准 rewrite 脚本一起传 CDN
- **原样保留**：源仓库自己就是坏链的（死域名/改版 404），改了也没内容可换——**别在这上面耗时间**；真要修得逐个查 Wayback，性价比极低
- 实测仍活着的：`elastic.co/guide/en/elasticsearch/guide/...`（elas_*.png 9 张）、`beats/filebeat|metricbeat`、`watcher`、`chenlinux.com`、`logz.io`、`ntop.org`、`rsyslog.com`、`pub.idqqimg.com`

## 四查结果（全绿）

| 项 | 结果 |
|---|---|
| TOC 节点 / 本地节点 | 230 == 230（DOC 196 + TITLE 34） |
| 全路径唯一 | True（196/196） |
| TOC 路径集合 == 本地集合 | True（仅在 TOC 0 / 仅在本地 0） |
| 幽灵文档 | 0（docs 196 == TOC DOC 196，分页用 `offset`） |
| 逐字符回读 | 196 篇，**不等 0 / 空 0**（doc_id 取账本） |
| 对账 reconcile | 错位 DOC 0 ✅ |
| CDN 抽验 | 5/5 实拉 200（共 93 处引用 / 92 张唯一图） |
| 根级顺序 | 00-前言.md → 05-Kibana 3（旧版）→ 06..10（prependNode 归位后） |