# refactoringguru.cn《深入设计模式》（设计模式全节）→ 语雀 84861074

2026-10-22 实战。fpb-zh 队列「设计模式」第 1 条：`https://refactoringguru.cn/design-patterns`
（RefactoringGuru 官方中文站的设计模式全节，站点本身是《深入设计模式》一书的免费在线版）。

## 结果

| 项 | 值 |
|---|---|
| 库 | 84861074 `深入设计模式（2026-10-22）`（slug `refactoringguru-design-patterns-20261022`）|
| 分组 | 文章收集 stack 36149506 ✅（回查确认）|
| 节点 | **275**（14 目录 / 261 文件）< 5000 单库 |
| 图片 | 151 张全传语雀 CDN（`content/` 插图 + `diagrams/` 结构图），0 失败 |
| 导入 | toc-md 一次 PUT 2.2s，结构核对 PASS，0 失败（dir 13 / doc 256 / skip 6）|
| 六查 | TOC 275 == 本地 275 == docs 261+14；全路径唯一 True；对账 0 错位；幽灵 0；**261 篇 word_count 全 >0**；逐篇回读 261/261 命中 |

## 站点形状（261 页）

- 简介 `/design-patterns`（hero 图 + 长文）、目录 `/catalog`、3 分类页、22 模式页
- 2 篇附加文：`/factory-comparison`（工厂模式比较）、`/visitor-double-dispatch`（双分派）
- 电子书销售页 `/book`
- **代码示例：10 语言 landing + 22 模式 × 10 语言 = 220 篇**（`/<pattern>/<lang>/example`）
  —— 量大但是该节的正文内容，全导。

## 目录（clean 树）

```
00-设计模式简介.md / 01-设计模式目录.md / 06-深入设计模式（电子书）.md   ← 根级 DOC
02-创建型模式/   00-概览 + 01..05 模式 + 06-工厂模式比较
03-结构型模式/   00-概览 + 06..12 模式
04-行为模式/     00-概览 + 13..22 模式 + 23-双分派与访问者模式
05-代码示例/     00-概览 + 05.01-C# … 05.10-TypeScript（每语言 00-landing + 01..22 模式）
```
模式全局编号 1..22（创建型 1-5 / 结构型 6-12 / 行为 13-22）。子目录 `05.NN-语言` 用
**两位零填**（`05.01`…`05.10`），否则字典序会 `05.1 < 05.10 < 05.2` 排错。

## 复用

```bash
python3 fetch.py            # 261 页 → site/（断点缓存 pages/）+ 图片 → site/_img/
# 图片传 CDN 并重写引用 → 删 site/_img
python3 ../scripts/yuque_rewrite_images.py site img_map.json --throttle 1.0
rm -rf site/_img
python3 ../scripts/yuque_tree_import.py --root site --book <id> --progress progress.json --toc-md
```

## 本次新踩的坑（已并入 references 坑 53）

1. **`body` 也带 `no-feature` 类 → 祖先过滤会一票否决全站**：`/design-patterns` 落地页的 hero
   在 `div.no-feature` 里，为了剔它写了「祖先含 `no-feature` 就跳过」——结果卡片型页面（目录/分类/
   语言 landing/示例概览共 **11 页**）的 `<body>` 恰好也带 `no-feature` → 全被滤空成 1 字节文档。
   正解：祖先检查**排除 `body`/`html`/`main`**，只查 main 以内的祖先。教训：拿祖先类名做过滤时，
   `body` 上的类名会一票否决一切。
2. **`span.chpuleN/chpuriN` 是 CJK 排版辅助 span**：承载**中文标点本身 + 一个空格**
   （`<span class=chpule2>，</span><span class=chpuri2> </span>`）→ 必须保留文本，并在收尾把
   `标点 + 空格` 折回 `标点`，否则正文会成为「实例 ， 并」。
3. **软连字符 `&shy;`（\xad）遍布标题与代码**（`Demo&shy;Single&shy;Thread`）→ 全局删 `\xad`。
4. **`span.hidden-in-book`** = 站点显示 / 电子书隐藏的补充词（"单例**模式**" 的「模式」）→ 保留文本。
5. **结构图有两个 img**：`structure-img-non-indexed`（桌面 `d-xl-block`）/ `structure-img-indexed`
   （移动 `d-xl-none`）→ **只取前一个**，否则同一张图进两遍。
6. **优缺点用图标区分**：`div.pros-cons` 左右两列 `<ul>`，首项 `<i class="fa-check">` = 优点 /
   `fa-times` = 缺点 → 按首项图标插 `**优点：**` / `**缺点：**` 标签。
7. **适用场景 problem/solution 用图标**：`div.applicability-problem`（`fa-bug`）/
   `div.applicability-solution`（`fa-bolt`）→ 渲染成 `> 🐞 …` / `⚡ …`。
8. **代码示例页最省事**：`<pre class="code" lang="java">` 直接给围栏语言（`output` → 空）。
9. **卡片型页面的正文全在 `<a class="pattern-card*">` 里**（目录页 / 分类页 / 语言 landing）→
   不专门渲染就是「每个字段一行、没有项目符」；按 `.pattern-name`/`.pattern-aka`/意图渲染成
   `- **名称**（English） — 意图`。
10. **语言图标 `<img class="dp-bg">` / `patterns/cards/*-mini.png` / `patterns/icons/*.svg` 都是装饰**
    → 只放行 `/images/patterns/content/` 与 `/images/patterns/diagrams/` 两类。
11. **`--test N` + `--toc-md` 必报「生成目录树失败: 缺少文档记录」**——toc-md 要全量目录记录，
    这是**预期行为**，不是真失败（试水阶段跑它会留 5 篇挂根，正式全量会重挂）。
12. **toc-md 收尾后根级 DOC 又排到 TITLE 之后**（坑 29 复发）→ 两发 `prependNode sibling`
    **按逆序**归位（先 `01` 到第一个 TITLE 前，再 `00` 到 `01` 前）。
13. `yuque_rewrite_images.py --dry` 报的 2 处「本地缺失」是 PHP 代码样例里的
    `<img src='$url'>` / `/images/star-wars.jpeg`，**代码里的 HTML 是正文**，别当真缺失。