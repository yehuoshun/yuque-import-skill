# Mastering Elasticsearch 中文版（xtmhm2000/mastering-elasticsearch）→ 语雀

**实战日期**：2026-10-18 ｜ **来源**：`http://udn.yyuap.com/doc/mastering-elasticsearch/`（老板给的列表链接，**域名已死，DNS 不解析**）
**源仓库**：`https://github.com/xtmhm2000/mastering-elasticsearch` @ **d2b8d61**（2014-12，desc「mastering elasticsearch翻译」，GitBook 源；**`homepage` 字段没写域名 → 坑 38 的判据失效**，靠 `gh search repos` 反查命中）
**落点**：语雀库 id **84707668**「Mastering Elasticsearch 中文版（d2b8d61）」，slug `mastering-elasticsearch-cn-d2b8d61`，分组「开源项目」(57018723)
**规模**：**47 节点（6 目录 / 41 文档）**；18 张本地图传 CDN（49 处引用）；原版英文 PDF 走 `type=attachment` 挂前言

---

## 这个仓库长什么样（4 个特征）

| 特征 | 实测 |
|---|---|
| SUMMARY 三层 | 前言 + 9 章 + 章内 2~3 层（`chapter-1/11_README.md` → `chapter-1/111_README.md`） |
| 章标题自带「第N章」 | `# 第1章 认识Elasticsearch` → 目录名必须**剥前缀**（`NN-` 已编码序号，不剥就成 `01-第1章 xxx`） |
| **残缺译本** | **第 3/6/7/8/9 章正文全空**（31~38 字节，只剩一行标题）；另 **16 个子节文件 0 字节**（第 3/6/7 章烂尾，SUMMARY 未收录） |
| 排版垫片图 | `notes/{pixel.gif,lm.png,rm.png}` 共 **96 处**（1px/13px + `position:absolute` 布局 div）→ 剥离，不传 CDN |

---

## 复用流程

```bash
# 1. 死域名 → 反查源仓库（仓库 homepage 没写域名时唯一路径）
gh search repos "mastering elasticsearch" --limit 15 \
  --json fullName,stargazersCount,description,updatedAt \
  --jq '.[] | "\(.fullName) ★\(.stargazersCount) \(.updatedAt[:10]) | \(.description[:80] // "")"'
# ⚠️ 别用 `gh api search/repositories?q=中文+空格` 手拼 query（未编码 → 返回一堆无关仓库）

# 2. 动手前先量残缺度（老译本常烂尾）
wc -c chapter-*/README.md | sort -n        # 只有 31 字节 = 只有一行标题的空壳章
find . -name "*.md" -not -path "./.git/*" -size 0 | wc -l

# 3. 传原版 PDF 附件（仓库自带的英文原版电子书）
#    POST https://www.yuque.com/api/upload/attach?attachable_type=User&attachable_id=<uid>&type=attachment&ctoken=<ctoken>
#    取返回 data.url → 写进 00-前言.md 末尾：「**原版英文 PDF 附件**：[点击下载](url)」；端点细节见 references/pdf-book-to-yuque.md

# 4. 重建干净树（本目录 mes-build.py，改顶部 SRC/OUT + 传 PDF URL）
python3 mes-build.py "https://www.yuque.com/attachments/yuque/0/2026/pdf/.../xxx.pdf"

# 5. 本地图 → CDN → 删 _imgs（硬规则 10：_imgs 与 img_map.json 不许留在导入根）
python3 ../yuque-import-skill/scripts/yuque_rewrite_images.py mes-d2b8d61-clean mes-img_map.json --throttle 1.5
rm -rf mes-d2b8d61-clean/_imgs

# 6. 建库 → 移分组 → 导入目录树（toc-md，默认路径）
python3 ../yuque-import-skill/scripts/yuque_repo_import.py create-book --name "Mastering Elasticsearch 中文版（d2b8d61）" --slug mastering-elasticsearch-cn-d2b8d61 --desc "..."
python3 ../yuque-import-skill/scripts/yuque_repo_import.py move-stack --book-id 84707668 --stack-id 57018723
python3 ../yuque-import-skill/scripts/yuque_tree_import.py --root mes-d2b8d61-clean --book 84707668 --progress mes-d2b8d61-progress.json --toc-md

# 7. 根级归位（本次两发：00 前言 prepend 一次成；03 根级 DOC 被排到 TITLE 后 → prepend 到 04 前）
#    每发 GET /toc 回读校验（见 references/api-notes.md 根级排序条）
```

## 建树规则（mes-build.py 里实现的）

1. **SUMMARY 递归建树**（别写死层数），节点号 = 点分路径 `NN` / `NN.MM` / `NN.MM.KK`；有子 → 目录 `NN-标题/` + 落地页 `NN-标题.md`；叶子 → `NN-标题.md`（`'-' < '.' < '0'` 保证落地页排子节点前）
2. **章标题剥「第N章」**：`re.match(r'^第(\d+)章\s*', title)` 命中即剥
3. **空壳处置**：SUMMARY 收录的空壳章照建（保结构）；**未收录且 0 字节的孤儿跳过**（本次 16 个，不再复刻「0 字节也造节点」）
4. **垫片图剥离**：`<img\s+src="(?:\.\./)?notes/(?:pixel\.gif|lm\.png|rm\.png)"[^>]*/>\s*` 整体删；`note.png` 保留
5. **图引用缺层回退**：原路径不存在 → 试「同名前插一层 `imgs/`」（修源仓库笔误 `../44_cluster.png`）
6. **PDF 附件双轨**：`00-前言.md` 末尾追加附件链接

## 验收（四查，全绿）

- 全路径唯一 41/41；TOC 路径集合 == 本地集合
- `docs` 总数 41 == TOC DOC 41 → 幽灵 0
- 逐字符回读 41 篇：不等 0 / 空 0
- CDN 抽验 5/5 实拉 200；`yuque_toc_reconcile.py` 错位 0
- 根级顺序 `00-前言.md` → `09-...`（注意：**结构核对不查同层相对顺序**，顺序要单独断言）

## 残留说明

- 第 3/6/7/8/9 章只有标题（源译文就没写完）→ 库是「残缺但可用」，干货在 1/2/4/5 章；已向老板报残缺度
- 源仓库 2014 年后未再更新