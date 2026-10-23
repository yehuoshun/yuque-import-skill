# gitbook-v2-md —— 现代 GitBook v2 站（gitbook.io 新平台）→ 语雀

**实战首例**：`https://einverne.gitbook.io/selenium-doc/`（《Selenium 中文文档》，队列「项目相关」第 9 条，2026-10-23）
**成果**：10 节点（2 目录 / 8 文档）/ 0 失败 / 六查全绿 + 8 篇逐篇回读 0 差；库 **84899817**，slug `selenium-doc-zh-20261023`，分组「文章收集」36149506

---

## ⭐ 关键结论：**不用抓 HTML，站自带官方 Markdown 导出**

现代 GitBook（`*.gitbook.io`，Next.js/RSC 平台）给两个免费入口，直接拿干净 md：

1. **全量索引**：`https://<site>/llms.txt` → 所有页面的标题 + `路径.md` 直链（**顺序 = 侧栏序**）
2. **每页 Markdown**：页面 URL 后**加 `.md`**（根页是 `/master.md`）→ 返回该页 md 源

页面 HTML 里也写了这句：「This page is also available as Markdown / For the complete documentation index, see llms.txt」。

> 另有 `https://<site>/~gitbook/site-index` 返回 `{pages:[{title,pathname,breadcrumbs}]}` JSON，**带层级/面包屑**，可用来还原目录树（llms.txt 是扁平的）。

## 流程

```bash
# 1) 拉索引拿页面清单（含层级）
curl -sSL https://einverne.gitbook.io/selenium-doc/llms.txt -o llms.txt
curl -sSL https://einverne.gitbook.io/selenium-doc/~gitbook/site-index -o site-index.json
# 2) 逐页拉 .md（根页 = master.md）
curl -sSL https://einverne.gitbook.io/selenium-doc/guan-fang-wen-dang/selenium-1.md -o raw/...
# 3) build.py：剥样板 callout + 剥首个 H1 + 外链图改本地 → site/*.md
python3 build.py
# 4) 传 CDN + 重写（图放 site/imgs/，引用写 ../imgs/），跑完删 imgs/
python3 scripts/yuque_rewrite_images.py site img_map.json
rm -rf site/imgs img_map.json
# 5) create-book / move-stack / tree_import --toc-md（同标准流程）
```

## 逐条要点

- **样板 callout 要剥**：每页 md 首块是 GitBook 注入的
  `> For the complete documentation index, see [llms.txt](...)...`（一段）——整块删，别留在正文。
- **首个 H1 == 标题** → 剥（标题已由 文件名/目录 提供）。
- **分组页（页 + 子页并存）**：GitBook 允许一个页既是「组」又有自己的正文（本例 `官方文档` / `wiki` 页正文只是子页链接清单）。
  口径：**当 TITLE 目录用、正文丢弃**（清单与语雀 TOC 重复）。
- **目录排序**：tree_import 用 `sorted(os.listdir)` → ASCII 目录名（`wiki`）会排在中文字典前。
  要还原站点序 → 目录名加数字前缀（`01-官方文档` / `02-wiki`）。
- **根级 DOC 排序**（坑 29 常态）：目录前缀是 `01-`/`02-` 时，根级 `00-介绍.md` 仍会排到 TITLE 之后 →
  导完补一发 `PUT /toc {action:prependNode, action_mode:sibling, node_uuid:<00-介绍>, target_uuid:<第一个TITLE>}` 归位（本例 1 发收敛）。
- **外链图能救就救**：本例 6 张图指向死掉的 `seleniumhq.org/docs/_images/*`（全 404）→ 用 GitHub 代码搜索按文件名反查，
  在官方镜像仓 `vdt/selenium`（`selenium-core/selenium-website/src/main/rst/images/`）找齐 6/6 → 传 CDN。
  （`raw.githubusercontent.com` 被墙 → 走 `https://gh-proxy.com/https://raw.githubusercontent.com/...`；`api.github.com` 可直连。）
- **口径**：源仓库已删（`fool2fish/selenium-doc` → GitHub 404，`gitlab.com/einverne/selenium-doc` 为改版）→ **网站口径**（库名带日期、分组「文章收集」）。