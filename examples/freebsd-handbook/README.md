# FreeBSD 使用手册（docs.freebsd.org/zh-cn/books/handbook）→ 语雀

2026-10-17 实战固化。源站是 **Asciidoctor / Hugo 渲染的官方文档站**（FreeBSD Documentation Portal），
与 git-scm.com/book 同族 DOM → 走 **bs4 递归渲染器**（不要正则）。

## 文件

| 文件 | 作用 |
|---|---|
| `fetch_all.py` | 解析侧边栏 `nav#MenuContents` 顶层 li → `plan.json`（5 part + 37 doc），抓全站页面 → `pages/<slug>.html` |
| `crawl.py` | bs4 递归渲染 → `clean/` 导入树；图片 `urljoin` 归一后传语雀 CDN（`img_map.json` 缓存） |

## 复现

```bash
mkdir -p /path/work && cd /path/work
python3 fetch_all.py          # → plan.json + pages/
python3 crawl.py              # → clean/ + img_map.json
# 建库（书站口径：库名带日期，分组「文章收集」36149506）
python3 <skill>/scripts/yuque_repo_import.py create-book --name "FreeBSD 使用手册（YYYY-MM-DD）" \
        --slug freebsd-handbook-YYYYMMDD --desc "<url> ｜ 导入 YYYY-MM-DD ｜ 源修订 <cgit id>"
python3 <skill>/scripts/yuque_repo_import.py move-stack --book-id <id> --stack-id 36149506
# 导入（toc-md）+ 收尾修根级顺序（见 references 坑 29）
python3 <skill>/scripts/yuque_tree_import.py --root clean --book <id> --progress p.json --toc-md
```

## 本站要点（详见 references/website-crawl-to-yuque.md 坑 28/29）

- 正文容器 `main.main-wrapper-book > div.book-content`（`div.last-modified`/`div.buttons` 天然在外，不用切窗口）
- 删 `div.toc-mobile`；删站点级公告 admonitionblock（含 `This translation may be out of date`）
- `admonitionblock` = `<table><td class=icon><td class=content>` → `> **注意/提示/重要/警告/当心**` 引用块
- 表格：标题在 `<caption class=title>`（在 table 内部）；无 `<thead>` 的表用**首行当表头**
- `span.filename|guimenuitem|keyseq|parameter` → 行内 code（取 get_text，别重复包反引号）
- 站内交叉链接 → 纯文字；`man.freebsd.org` 等外链保留
- 命名：`00-前言.md` / `部分 N. xxx/00-部分 N. xxx.md`（分部导读）/ `NN-第 N 章 xxx.md` / `A-附录 A. xxx.md`
- **`--toc-md` 后根级 DOC 会排到 TITLE 目录之后** → `PUT /toc {action:prependNode, action_mode:sibling}` 一次归位

## 本单结果

- 库 `84675796`「FreeBSD 使用手册（2026-10-17）」slug `freebsd-handbook-20261017`，分组「文章收集」(36149506)
- 46 节点（5 目录 / 41 文档）、167 张图（CDN）、0 失败；四查全绿（TOC 46==本地 46、错位 0、幽灵 0、4 篇逐字符等长）
