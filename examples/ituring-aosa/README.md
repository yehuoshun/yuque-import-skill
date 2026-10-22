# 图灵社区《开源软件架构》→ 语雀（2026-10-22，网站口径）

源：https://www.ituring.com.cn/book/1143 —《开源软件架构》(The Architecture of Open Source Applications，中文版，
iTran 乐译开放书，CC BY 3.0)。库里 39 章全部 `isFree`，可直接取正文。

实战产物：库 **84864438**（`开源软件架构（2026-10-22）`，slug `aosa-zh-20261022`，分组「文章收集」），
41 节点（2 目录 / 39 文档），74 图全传 CDN，六查全绿。

## 复用脚本

- `build.py` — 拉 API → HTML→Markdown → 下图片到 `site/_img/` → 建树 `site/`。
  - `python3 build.py`（带 `raw/` 缓存）｜ `python3 build.py --refresh`（重拉 API）
  - 之后：`python3 ../../scripts/yuque_rewrite_images.py site <img_map.json> --throttle 3`
    （把 `site/_img/` 全传语雀 CDN 并重写 md），再 `rm -rf site/_img`，然后走 `yuque_tree_import.py --toc-md`。

## 关键点（照抄时别漏）

1. **正文不在 HTML 里**：`www.ituring.com.cn/book/<id>` 是 Vue SPA 外壳；真 API 在 **`api.ituring.com.cn`**。
   - 图书详情：`GET https://api.ituring.com.cn/api/book/{id}`（**book 小写**）→ `ebook.chapters[]`（`id/isFree/subject`）
   - 章节正文：`GET https://api.ituring.com.cn/api/Book/mini/{章节id}`（**Book 大写**）→ `{subject, htmlOfBody}`
   - 图灵自营电子书（非开放书）走 `/api/Book/Tupub/{id}`；`htmlOfBody` 就是整章 HTML。
2. **API 路径大小写敏感**，且不存在时会返回 **200 的 SPA 外壳**（不是 404）→ 判失败要看响应体里有没有 JSON 字段。
3. **脏 HTML**：`htmlOfBody` 里 `<p>` 大量不闭合、互相嵌套（尾巴堆 `</p></p>`）→ `render()` 对「含块级子元素」的
   `<p>` 要下钻递归，否则整章被并成一大段。
4. **图片三类历史外链**（旧地址多处已死）：
   - `http://www.aosabook.org/images/<book>/X.png` → 站点改版后 404，改 `https://aosabook.org/static/<book>/X.png`
   - `raw.github.com/stfairy/aosa-violet/...`（图床仓已删）→ 同名图在 `https://aosabook.org/static/violet/`
   - `/download/xxx`（无 host）→ 补 `https://download.ituring.com.cn`
5. **无扩展名图（`.small`）会被 `upload_image` 拒**（按扩展名判类型）→ 先改 `.png` 再传。
6. **同卷同名章节**（本书 `卷2 第6章 Git` 有两份独立译文）→ 标题加「（译文一/二）」防同父重名。

## 目录

```
examples/ituring-aosa/
├── build.py        # 转换器（自包含，可 --refresh 重拉）
├── README.md
├── raw/            # 缓存的 API JSON（*.json = 各章 htmlOfBody；_book.json = 图书详情）—— .gitignore
└── site/           # 转换产物（md 树，图片引用已重写为 CDN）—— .gitignore
```