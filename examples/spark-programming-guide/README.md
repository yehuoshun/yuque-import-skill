# 案例：GitBook 站点 + 同名源仓库（《Spark 编程指南简体中文版》，2026-10-18）

老板给的触发链接是**站点** `https://aiyanbo.gitbooks.io/spark-programming-guide-zh-cn/content/`，
同名 GitHub 仓库 `aiyanbo/spark-programming-guide-zh-cn`（GitBook 3.x 源，master @ `487c68a`）就是书稿源
→ **吃 md 源，不抓 HTML**（开源项目流程：库名带 commit、分组「开源项目」stack 57018723）。

## 结论先行

| 项 | 值 |
|---|---|
| 库 | `Spark 编程指南简体中文版（487c68a）` id=84705967 slug=spark-programming-guide-zh-cn-487c68a |
| 分组 | 「开源项目」stack 57018723 |
| 节点 | **81**（13 目录 + 68 文档含 00-前言.md），407KB |
| 图 | 12 张全部 CDN（12 处引用，1:1），0 缺失 |
| 耗时 | 图 ~20s + 导入 ~46s（toc-md PUT 0.7s） |

## 源仓库形状（识别特征）

```
SUMMARY.md      # 3~4 层嵌套目录（快速上手/编程指南/Spark Streaming/Spark SQL/GraphX/部署/更多文档）
README.md       # Introduction（书标题+内嵌目录）→ 00-前言.md
quick-start/     programming-guide/(rdds/…)  spark-streaming/(basic-concepts/…)
spark-sql/(data-sources/…) graphx-programming-guide/ deploying/ more/ img/ cover.jpg
```

**特征**：GitBook 3.x 源，**层级只在 SUMMARY.md 的缩进里**（2~4 层：章 → 节 → 子节 → 孙节，
如 编程指南 → Spark RDDs → RDD 操作 → 传递函数到 Spark）——必须解析 SUMMARY.md 重建树，靠文件名推不出层级。

## 重建规则（examples/spark-programming-guide/build_tree.py）

```
README.md                                                               → 00-前言.md（根级）
SUMMARY.md 缩进 = 树（唯一权威）                                         → 不入库（它就是目录）
每层节点有 children → dir `prefix-标题/`；自带文件 → 章首页 `prefix-标题.md` 放 dir 内
  子节点 = `prefix.k-标题.md`；`-`(0x2D) < `.`(0x2E) 章首页天然排第一
父子链同路径的重复条目（部署/提交应用程序、更多文档/Spark配置）            → 去重：内容并入章首页，子节点提升（flatten）
孤儿 md（不在 SUMMARY、属书内容）                                        → 按源目录补进树：
    spark-streaming/basic-concepts/{custom-receiver,flume,kafka,kinesis} → 03.2.11..14
    spark-sql/compatibility-with-other-systems/{hive,shark}             → 04.7-与其他系统兼容/
LICENSE / cover.jpg（未被引用）                                          → 不入库；img/ 原样拷入，rewrite 后删除
```

- 新树与源仓库**每个文件深度保持一致**（章目录 depth=1、子目录 depth=2）→ `../img/`、`../../img/` 引用天然仍有效。
  唯一深度漂移的是 RDD 操作 下的 4 篇（源 2 层 → 新 3 层）和 rdd_persistence.md（2→1），它们都不引用图片，无需改写
- 孤儿标题取文件首个 `# ` 标题（与Apache Hive的兼容性 / Shark用户迁移指南 / 自定义receiver指南…）

## 踩坑（本案例新增/复现）

1. **flatten 去重**：直接 `_skip` 掉父子同路径的节点会把**它下面的子树**一起丢掉（更多文档→Spark配置→RDD持久化
   这条链，RDD 持久化 差点消失）——去重必须把被去重节点的 children 提升到父级，再按新列表编号。
2. **孤儿循环重复记账**：两个 spark-sql 孤儿各自 `append TITLE` → 04.7 目录被记了 2 次（目录数 14 vs 实际 13）——
   建目录前查 `created_dirs` 集合，只记一次。
3. **00-前言.md 没进 plan**：build_tree 的 doc/plan 统计和 import 脚本的磁盘扫描对不上（67 vs 68）——copy 后要
   `plan.append(("00-前言.md", "DOC"))`。
4. **坑 35 复现**：toc-md 收尾后根级 DOC 落到所有 TITLE 之后 → `prependNode/action_mode=sibling,
   node_uuid=<前言>, target_uuid=<01-快速上手>` 归位；**第一次 PUT 后立刻 GET 可能还在旧序（读侧传播延迟），
   等几秒再 GET 双确认，或直接看 PUT 响应里的 data 顺序**。
5. 建树脚本重跑会**用源文件覆盖 clean 目录**（CDN 重写被冲掉）→ 重跑后必须重跑 `yuque_rewrite_images.py`
   （img_map.json 缓存命中，零上传）再删 img/。

## 复现命令

```bash
python3 examples/spark-programming-guide/build_tree.py <mirror> spark-487c68a-clean
python3 scripts/yuque_rewrite_images.py spark-487c68a-clean spark-img_map.json --dry   # 核 12 处
python3 scripts/yuque_rewrite_images.py spark-487c68a-clean spark-img_map.json --throttle 1.5
rm -rf spark-487c68a-clean/img
python3 scripts/yuque_repo_import.py create-book --name "Spark 编程指南简体中文版（487c68a）" \
    --slug spark-programming-guide-zh-cn-487c68a --desc "https://github.com/aiyanbo/spark-programming-guide-zh-cn @ 487c68a"
python3 scripts/yuque_repo_import.py move-stack --book-id 84705967 --stack-id 57018723
python3 scripts/yuque_tree_import.py --root spark-487c68a-clean --book 84705967 \
    --progress spark-487c68a-progress.json --test 6          # 先试水（不带 --toc-md，坑 26）
python3 scripts/yuque_tree_import.py --root spark-487c68a-clean --book 84705967 \
    --progress spark-487c68a-progress.json --toc-md          # 全量
# 收尾：prependNode 前言归位 → 对账 → yuque_import_verify.py → 幽灵/正文/图验收
```