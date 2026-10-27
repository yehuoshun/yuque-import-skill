# 《C/C++面向WebAssembly编程》→ 语雀（cppwasm-book @ 946acba）

语雀库：<https://www.yuque.com/yehuoshun/cppwasm-book-946acba>（book_id 85034630，开源项目口径）

## 源仓库形态

`3dgen/cppwasm-book`（1401 star，已出版纸书，2024-04-17 最后一更）
- 原链 `https://github.com/3dgen/cppwasm-book/tree/master/zh` → **正文只在 `zh/`**
- `zh/` 是老 GitBook 3.x 源：`book.json`（`structure.readme = preface.md`）+ `SUMMARY.md`（目录）+ 各章 `chN-xxx/`
- 同级 `en/`（英文版）、`examples/`（配套源码）、根 `Makefile`/`server.go`/`cover.jpg` 全是非正文

## 导入口径（发布面）

| 项 | 取值 |
|---|---|
| 前言 | `zh/preface.md` → `00-前言.md`（book.json 的 readme） |
| 章目录 | SUMMARY.md 一级条目 → TITLE（`第1章 Emscripten快速入门` … 共 7 个） |
| 章导读 | 各章 `readme.md` → `<章目录>/00-本章导读.md` |
| 节 | SUMMARY.md 二级条目 → `<节标题>.md`（33 篇，2.7 的 `/` 换全角 `／`、7.4 剥反引号） |
| 剔除 | 6 个标题-only 空壳（each 6B；ch0-intro/readme 28B，SUMMARY 里同样注释着）、`zh/README.md`（与 preface 重复）、`SUMMARY.md`、`book.json`、封面图 |
| 图 | 59 处引用 / 59 张：分章 `images/*.png` 52 张 + `cover.png` + `weixin-wasm-hackers.jpg`，全传 CDN 后删图片目录 |

节点：**48 = 7 TITLE + 41 DOC**。

## 用法

```bash
# 1) 克隆
git clone git@github.com:3dgen/cppwasm-book.git ~/.openclaw/workspace/tmp/cppwasm-book
# 2) 建导入树（SUMMARY 解析 + 空壳剔 + H1 剥 + 分章拷图）
python3 examples/cppwasm-book/build_lib.py \
  --repo ~/.openclaw/workspace/tmp/cppwasm-book \
  --out  ~/.openclaw/workspace/tmp/cppwasm-book-946acba-clean
# 3) 图 → CDN（59 张，--dry 先看「本地缺失 0」）
python3 scripts/yuque_rewrite_images.py <clean> <imgmap.json> --throttle 2
rm -rf <clean>/*/images <clean>/*.png <clean>/*.jpg
# 4) 建库 + move-stack + toc-md 全量
python3 scripts/yuque_repo_import.py create-book --name "C/C++面向WebAssembly编程（946acba）" \
  --slug cppwasm-book-946acba --desc "来源：<url> @ 946acba ｜ ... ｜ 导入 <日期>"
python3 scripts/yuque_tree_import.py --root <clean> --book <id> --progress <账本> --toc-md
```

## 坑（本次实踩）

1. **`/tree/master/<lang>/` 必须先探仓库结构**：`git ls-tree`/API tree 一眼就能看出正文在 `zh/`，同级 `en/` + `examples/` 直接排除。
2. **空壳判据用字节数**（`len(body.strip())<10`）：本书 6 个 6B 壳在磁盘上是真文件，按存在性判会把它们导成空文档（word_count=0，六查第 6 条会红）。
3. **SUMMARY 的注释状态与空壳互为佐证**：`<!--* [第0章 …](ch0-intro/readme.md)-->` 被注释 + 文件 28B = TODO 残留，两边一起看才敢删。
4. **`README.md` 与 `preface.md` 重复时弃 README**：本书 README 是仓库门面（前言 + 进度清单 + 版权），GitBook 的首页由 `book.json` 的 `structure.readme` 决定 = `preface.md`。
5. **分章拷图必须按「源目录 → 输出章目录」映射**：首版用源目录名（`ch3-runtime`）建目录，而输出目录叫 `第3章 Emscripten运行时` → rewrite 脚本 59 处全报「本地缺失」。
6. **标题清洗两条**：半角 `/` → 全角 `／`（文件名雷）、剥行内反引号（目录树切分雷）。
7. **根级 DOC 顺序**：toc-md 收尾后 `00-前言.md` 会排到 7 个 TITLE 之后 → 补一发 `PUT /toc {action:prependNode, action_mode:sibling, node_uuid:<前言>, target_uuid:<第1章>}`。