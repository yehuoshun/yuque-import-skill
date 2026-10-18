# OpenGL 教程（zilongshanren/opengl-tutorials）→ 语雀 实战样例

> 2026-10-18 老板拍板「方案 B」；库 id **84709042**、slug `opengl-tutorials-4500ac6`、分组「开源项目」(57018723)、private。
> 源：`https://github.com/zilongshanren/opengl-tutorials` @ **4500ac6**（master，2015-01-05；= 教程站 `opengl.zilongshanren.com` 的源仓库）

## 仓库形状

- GitBook 源：根级 `README.md`（前言/许可/贡献人）+ `SUMMARY.md`（目录本身）+ 18 个无语义章节目录 `tut01..tut18/`
- 每章 = `tutNN/zh.md` + 图片目录 `tutNN/res/`（共 114 张，png/jpg/gif）
- 图片引用**全是相对路径** `./res/x.png`（按 md 所在目录解析）、无 HTML `<img>`、无视频/附件
- 20 md 全 UTF-8、最大 22KB（无分片）；114 处引用 ↔ 114 张图 1:1

## 为什么是方案 B（而不是镜像仓库树）

镜像树会得到 18 个名字叫 `tutNN` 的目录（无语义），且需要把每章的 `res/` 一起搬进去。
方案 B 用 **SUMMARY.md 里的可读标题**重建：

```
00-前言.md                                  ← README.md
01-OpenGL基本知识/                            ← SUMMARY 第 1 分部
  01-新建一个窗口.md … 08-基本着色.md
02-OpenGL中级教程/                            ← SUMMARY 第 2 分部
  09-VBO索引.md … 18-Billboard和粒子.md
```

= **21 节点（2 目录 / 19 文档）**；`SUMMARY.md` 不入库（就是目录本身）。

## ⭐ 顺序铁律：先 CDN 重写，再重建树

```bash
# ① 在原布局重写（此时 ./res/x.png 按 md 目录天然解析）
python3 scripts/yuque_rewrite_images.py --cookie-config <cfg> --throttle 1.5 \
  tmp/opengl-tutorials-4500ac6-clean tmp/opengl-tutorials-4500ac6-img_map.json
# → 重写 114 处 / 外链 0 / 缺失 0；114 张全传 cdn.nlark.com（~3 分钟 0 失败）

# ② 再重建树（只 copy md，不 copy 任何图片）
python3 build_tree.py --apply
```

**反序（先重建再重写）会串图**：本仓库 `icon_smile.gif` **同时存在于 `tut08/res/` 与 `tut13/res/`**（两张不同的图、同名）。两章归到不同分部后若共享 `res/`，就会互相覆盖、两篇指向同一张图。`build_tree.py` 内置两条断言兜底：目标树不得含非 md 文件、不得残留非 http 图片引用。

## 其它踩点

- **标题以 `SUMMARY.md` 为准，别信磁盘 heading**：`tut08/zh.md` heading 写「基础光照模型」，SUMMARY 写「基本着色」；`tut18/zh.md` heading 有错字「Billbard」，SUMMARY 写「Billboard和粒子」——按 heading 命名会把笔误写进库。
- 全角「：」留在标题里不用洗（语雀按最后一个 `](slug)` 切分）；本章标题无 `/`。
- 收尾 **根级 DOC `00-前言.md` 被排到 2 个 TITLE 之后**（老坑 29）→ 一发
  `PUT /toc {action:prependNode, action_mode:sibling, node_uuid:<前言>, target_uuid:<01-目录>}` 归位。

## 验收结果

| 项 | 结果 |
|---|---|
| toc-md | 目录树 21 行 / 879B → PUT **0.5s**，结构核对 PASS，0 失败（dir 1 / doc 14 / skip 6） |
| TOC == progress == 本地 | 21 / 21 / 21 ✅ |
| TOC DOC == docs total | 19 == 19（幽灵 0）✅ |
| 全路径唯一 | True ✅ |
| 逐篇正文回读 | 19 篇逐字符等长，0 不等 / 0 空 ✅ |
| reconcile 错位 | 0 ✅ |
| CDN 图 | 114 引用 ↔ 114 条目 ↔ 114 唯一 URL；抽 5 张实拉 200 image/png ✅ |
| 根级序 | `00-前言.md` / `01-OpenGL基本知识` / `02-OpenGL中级教程` ✅ |

版权：内容 CC BY 3.0，免责声明写明版权归原作者、禁止赢利性再发布 → 只进私有库。