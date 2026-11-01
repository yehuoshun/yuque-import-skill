# 案例：AsciiDoc 书稿源（index.adoc + include::）（《JavaScript Promise迷你书（中文版）》，2026-11-01）

触发链接是**在线渲染站** `http://liubin.github.io/promises-book/`（301 → liubin.org/promises-book，Asciidoctor 单页全本），
源仓库 `liubin/promises-book` 里躺的是 **AsciiDoc 书稿**（`index.adoc` 主控 + `include::` 拼装，无任何 .md）——
走开源项目口径（库名带 commit、分组「开源项目」stack 57018723）。

## 结论先行

| 项 | 值 |
|---|---|
| 库 | `JavaScript Promise迷你书（中文版）（930f798）` id=85211548 slug=promises-book-zh-930f798 |
| 节点 | **34**（4 章目录 + 30 文档） |
| 图 | 14 张全部 CDN（11 张本地 `img/*.png` + 3 张行内引用 `image:` 形态） |
| 转换 | 复用 `examples/puppet-cookbook/adoc-build.py` 的转换器（importlib 加载，`ab.OUT`/`ab.ATTRS` 注入） |

## 源形状

```
index.adoc                     封面 + 前置 + include::Ch0..Ch4 / Appendix-*
Ch0_Introduction/readme.adoc   前言（= 前言 + == 小节）
ChN_*/readme.adoc              = Chapter.N - 标题 + :imagesdir: + include:: 各节
ChN_*/<section>.adoc           == 节标题（正文主体）
Appendix-Reference/readme.adoc == Promise#then / #catch / resolve / reject / all / race
Appendix-Glossary/{glossary,resource-link,about-author}.adoc
Appendix-Note/                 未进 index.adoc（不在发布面）→ 不收
```

## 本案例新增的 4 条转换规则（相对 puppet-cookbook 版）

| AsciiDoc | Markdown | 说明 |
|---|---|---|
| 标题整体降一级 | `=`→`#`、`==`→`##` | puppet 版 Conv 把 `=`/`==` 都映射成 `#`；本案例先把标题统一加一层 `=` 再交 Conv，得到自然层级；每篇再剥首个 H1（标题由文件名给） |
| 定义列表 `Term::` + 缩进行 | `- **Term**` + 缩进定义行 | 术语集/参考网站通篇是这种；**定义必须另起行**（并回一行会让 Conv 的 `+x+` 行内规则跨行配对，把 `Promises/A+` 咬成反引号） |
| `[role="executable"]` / `ifeval::[]` / `endif::[]` | 整行剥 | 非 Conv 白名单属性；ifeval 是 html5-only 包裹，剥壳留内容 |
| 行内 `image:rel[...]` / `image:https://...[alt, link=]` | `image::rel[alt]` → 走 replace_images；外链 → `![alt](url)`、带 link 则 `[![alt](url)](link)` | 源里 `image:`（单冒号）与 `image::` 混用；正则必须 `(?<!:)image:(?!:)`，否则会把 `image::` 写成 `image:::`（图片复制静默失败） |

## 踩过的坑

1. **`image::` 被 `image:` 规则二次命中**：`(?<!:)image:(\S+?)\[...\]` 会把 `image::img/a.png` 捕成 `:img/a.png` → 图片仍引用 `_imgs/` 但**复制失败**（本地缺失），CDN 重写全跳过。正则加 `(?!:)`。
2. **Asciidoctor 单页站可以当 oracle**：`liubin.org/promises-book/` 单页 363KB，h1~h4 层级 = 书序，可直接核对章号（6 用語集 / 7 参考网站 / 8 关于作者 / 9 关于译者）。
3. **未发布目录不要收**：`Appendix-Note/`（日语「おまけ」）不在 `index.adoc` 里，不在发布面。
4. **文件名洗全角**：`专栏: xxx？` → `专栏：xxx？`（`:`→`：`、`?`→`？`，别用 `/` 顶替——`then or catch？` 会变 `catch／`）。

## 复现

```bash
git clone --depth 1 git@github.com:liubin/promises-book.git tmp/fpb166-src
python3 examples/promise-book-adoc/build.py        # → tmp/fpb166-promise-book/site（30 文档/4 目录）
python3 scripts/yuque_rewrite_images.py tmp/fpb166-promise-book/site tmp/fpb166-imgmap.json   # 14 图 → CDN
rm -rf tmp/fpb166-promise-book/site/_imgs
python3 scripts/yuque_repo_import.py create-book --name "…（930f798）" --slug promises-book-zh-930f798 --desc "来源：… @ 930f798 ｜ … ｜ 导入 2026-11-01"
python3 scripts/yuque_tree_import.py --root tmp/fpb166-promise-book/site --book <id> --progress tmp/fpb166-progress.json --toc-md
```
