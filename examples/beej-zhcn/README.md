# 老 GitBook 2.x **源仓库**（SUMMARY.md + 章节 md）→ 语雀（2026-10-28）

**首例**：`myliao2007/beej-zhcn`（《Beej's Guide to Network Programming 简体中文版》@ 2843ddc，CC0，30★）
→ 库 **85036349**（slug `beej-guide-zhcn-2843ddc`，分组「开源项目」待补），89 节点（10 目录 / 79 文档），六查全绿。

## 什么时候用它

书单/仓库是**老 GitBook 2.x 源仓库**：根目录 `SUMMARY.md`（`* [标题](路径.md)`，缩进 2 空格 = 一层）+ 各章 md，
**没有** `book.json`/`conf.py`/`sidebars.js`。有别于：
- `wizardforcel-gitbook`（那是 gitbooks.io **渲染站**抓 HTML）
- `gitbook-v2-md`（那是 gitbook.io **新平台**，走 llms.txt + `.md` 直链）

## 用法

```bash
python3 examples/beej-zhcn/build.py            # 改脚本顶部 SRC/OUT 两个常量
python3 scripts/yuque_rewrite_images.py <OUT> img_map.json --cookie-config <cfg>
rm -rf <OUT>/imgs <OUT>/img_map.json           # 硬规则 10
python3 scripts/yuque_repo_import.py create-book --name "书名（<commit>）" --slug 书名-<commit> --desc "..."
python3 scripts/yuque_tree_import.py --root <OUT> --book <id> --progress <p> --toc-md
```

## 关键点

1. **不信文件名，认 SUMMARY.md**：`NN-<安全标题>.md` / 目录 `NN-<安全标题>/`，编号按 SUMMARY **同级出现顺序**（目录与文档混编也能保序）。上级标题里的 `\_` 转义要还原。
2. **章目录 = 目录 + 导读文档**：SUMMARY 里 `1. 前言 → introduction/README.md` 这种「目录自身有正文」的，目录内放 `00-<章名>.md`，子节 `01-…`。
3. **上游标题自带章节号前缀**（`06-Client-Server 基础`、`07-高等技术`、`10-参考文献`）→ 目录名会变成 `09-06-…` 双前缀，观感差；本次保留原样（保真优先），要洗就在 `safe()` 前加 `re.sub(r"^\d{1,2}-","",title)`。
4. **根级 DOC 必落后于 TITLE（坑 29 常态）**：`01-簡介.md`/`02-…` 这些根级文档导完会排到所有目录之后 → 按 SUMMARY 序发 `prependNode`（本次 5 发收敛）。别指望 `NN-` 前缀能自动排对，toc-md 只保证 TITLE 内部序。
5. **图**：老 GitBook 仓库图在 `.gitbook/assets/`，md 里写 `../.gitbook/assets/x.png`；转换时算**相对深度**重写到 `imgs/`（章目录里的文档是 `../imgs/`，二级是 `../../imgs/`，写死一个前缀必报「本地缺失」）。
6. **正文里没有站内 md 互链**（链接都在 SUMMARY.md）→ 不需要重写链接；`\_` 转义保留即可。
7. **只引用了 1 张图，仓库里多出的图/PDF 是孤儿**（`encapsulation_packet.png`、`bgnet_A4_2012.pdf`）→ 孤儿不进库；PDF 本可按硬规则 12 传附件，本次未传（正文无引用）。
