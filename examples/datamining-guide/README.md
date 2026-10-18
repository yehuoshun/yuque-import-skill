# 案例：GitBook 站点 + 同名源仓库（《面向程序员的数据挖掘指南》，2026-10-18）

老板给的触发链接是**站点** `http://dataminingguide.books.yourtion.com/`，页面 meta 写着
`generator = GitBook 3.2.2`、`author = Yourtion` —— 这类「个人 GitBook 站」八成有**同名源仓库**，
先搜再决定：`api.github.com/search/repositories?q=<书名>` → 命中
`yourtion/DataminingGuideBook`（Gitbook 源，HEAD `5e05231`）→ **吃 md 源，不抓 HTML**。

## 结论先行

| 项 | 值 |
|---|---|
| 库 | `面向程序员的数据挖掘指南（5e05231）` id=84705592 slug=dataminingguide-5e05231 |
| 分组 | 「开源项目」stack 57018723（**源仓库口径**，不是网站口径的「文章收集」） |
| 节点 | **63**（1 根级文档 + 8 目录 + 54 篇正文），405KB |
| 图 | 433 张全部 CDN，441 处引用重写（含重复引用），0 缺失 |
| 耗时 | 图 13.5min（throttle 1.5）+ 导入 **42s**（toc-md 模式） |

## 源仓库形状（识别特征）

```
book.json            # {} 空配置，不入库
SUMMARY.md           # 8 章 × 若干子节，扁平 54 行 → 目录树的唯一权威
README.md            # 书的欢迎辞/前言 → 00-前言.md
chapter-1/chapter-1-0.md   # 章首页（chapter-N-0）
chapter-1/chapter-1-1.md   # 子节（chapter-N-M，M≥1）
img/chapter-N/*.png        # 图（md 里引用写成 ../img/chapter-N/xxx.png）
```

**特征**：GitBook 3.x 源，**没有目录层级**（章节是扁平编号文件名，靠 SUMMARY.md 缩进表达层级），
标题只存在 SUMMARY.md 里 —— 所以必须解析 SUMMARY.md 重建树，不能靠文件名。

## 重建规则（examples/datamining-guide/build_tree.py）

```
README.md                    → 00-前言.md                     （根级文档）
chapter-N/chapter-N-0.md     → NN-章名/NN-章名.md              （章首页，放章节目录里）
chapter-N/chapter-N-M.md     → NN-章名/NN.M-<SUMMARY 标题>.md   （子节）
SUMMARY.md / book.json       → 不入库（前者就是目录本身、后者空配置）
img/                         → 原样拷进 clean 根，rewrite 传 CDN 后**删除整个目录**
```

- 章名取 SUMMARY.md 顶层条目；子节标题取对应缩进条目
- **`NN-章名.md` 与 `NN.M-子节.md` 的排序靠 `-`(0x2D) < `.`(0x2E)**：章首页天然排第一。
  不过 toc-md 模式下顺序来自目录树本身，这个命名只是让磁盘/人眼一致
- 文件名洗 `[/\\:*?"<>|]`（本次 `06.4-为什么我们需要贝叶斯法则？.md` 的 `？` 是中文全角，不用洗；
  真踩过的是 TLCL 的 `流程控制：while/until 循环`）
- 原仓库是 depth=1（`chapter-N/x.md`），新树也是 depth=1（`NN-章名/x.md`）→
  **`../img/...` 引用天然仍然有效**，不需要改路径。这是为什么把章首页也塞进子目录而不是平铺到根

## 踩坑

1. **`yuque_rewrite_images.py --dry` 统计恒为 0/0/0**（本次修，v1.3.65）：旧版 `resolve()` 里
   `if key not in mp and not args.dry:` → dry 模式永远不填 mp → 返回 None → 既不计 rewritten 也不计 missing。
   本次差点误判「441 处图引用一张没扫到」。修法：dry 直接 `return "DRY:"+src` 占位（不写盘、不动 img_map）。
2. **toc-md 收尾后根级 DOC 排到 TITLE 目录之后**（refs 坑 29 复现）：`00-前言.md` 落到 8 个目录后面 →
   补一发 `prependNode/action_mode=sibling, node_uuid=<前言>, target_uuid=<01-简介>` 归位。
3. **图片文件名与章节号无关的重复引用**：441 处引用对应 433 张图（有 8 处重复引用同一张图），
   `img_map.json` 以**相对路径为 key** → 同图只传一次，不会重复上传。
4. 章节号是「章-序号」但图是「chapter-N-M.png」且编号跟正文小节**不对应**（图号是全书递增的），
   不要试图按图号反推章节。

## 复现命令

```bash
git clone -q --depth 50 https://gh-proxy.com/https://github.com/yourtion/DataminingGuideBook.git dmg-probe
python3 examples/datamining-guide/build_tree.py dmg-probe dmg-5e05231-clean
python3 scripts/yuque_rewrite_images.py dmg-5e05231-clean dmg-img_map.json --throttle 1.5   # 先 --dry 看处数
rm -rf dmg-5e05231-clean/img
python3 scripts/yuque_repo_import.py create-book --name "面向程序员的数据挖掘指南（5e05231）" \
    --slug dataminingguide-5e05231 --desc "<站点 URL> | git@github.com:yourtion/DataminingGuideBook.git @ 5e05231"
python3 scripts/yuque_repo_import.py move-stack --book-id 84705592 --stack-id 57018723
python3 scripts/yuque_tree_import.py --root dmg-5e05231-clean --book 84705592 --progress dmg-progress.json --toc-md
# 收尾：根级 DOC 归位 → 对账 → yuque_import_verify.py → 逐字符回读
```
