# 《游戏策划实务即用的 AI·Claude Code 活用法（简体中文版）》→ 语雀

2026-10-22 实战。源：`eremes81/game-design-ai-practice-zh-hans` @ `df9a7ab`（正本站 https://eremes81.github.io/game-design-ai-practice-zh-hans/ ，CC BY-NC-SA 4.0 → 私人库自用）。
产物：库 `84860110`，slug `game-design-ai-practice-zh-hans-20261022`，**127 节点**（25 目录 / 102 文档），0 失败，六查全绿。

## 仓库形态（先认清再动手）

```
index.html              2.1MB  ← 全书拼一起的渲染产物，⚠️ 不是正文源
manuscript/             102 个 .md ← ✅ 真正的正文源
  _front-matter.md      序（H1 是书名）
  _colophon.md          版权页
  part01-foundation/    chapter-0…3.md
  …
  part24-ops-deep/
  part99-appendix/      epilogue.md + appendix-A…N.md
assets/cover.svg        站点封面（正文没引用它）
robots.txt / sitemap.xml / .nojekyll / LICENSE / .gitignore   ← 站点脚手架，不入库
```

- **没有 SUMMARY.md**：中文标题全在每篇的**首个 H1**，部分名（第1部分 · 基础 …）在 `README.md` 的「完整目录」里。
- **没有图片**：全树无 `images/` 目录。正文 2 处 `![](images/…)`（17.3）与 README 明说的 `char_skill_ui.png` 都是**上游本来就缺的占位符**，保留原样、不重写、别找。
- **有 67 处内联 `<svg>`**：作者手绘矢量图（架构图/关系图/矩阵图），语雀 markdown 导入**原样保留**（回读 body 里 `<svg>` 完整），不需要抽图传 CDN。

## 用法

```bash
# 1. clone（走 gh-proxy 提速）
git clone https://gh-proxy.com/https://github.com/eremes81/game-design-ai-practice-zh-hans.git

# 2. 构建 clean 树（只改文件名/目录名，正文只剥「与标题重复的首个 H1」）
python3 build_lib.py --src <clone>/manuscript --out <clean_dir>
# 输出：目录 25 / 文档 102 = 节点 127；剥掉与标题重复的首个 H1: 100 篇

# 3. 建库 + 归组（网站口径：库名带日期、slug 带日期、「文章收集」stack 36149506）
python3 scripts/yuque_repo_import.py create-book \
  --name "游戏策划实务即用的 AI·Claude Code 活用法（简体中文版）（2026-10-22）" \
  --slug game-design-ai-practice-zh-hans-20261022 --desc "来源：…"
python3 scripts/yuque_repo_import.py move-stack --book-id <id> --stack-id 36149506

# 4. toc-md 导入（127 节点约 90s；先 --test 6 验证 svg 保真再全量）
python3 scripts/yuque_tree_import.py --root <clean_dir> --book <id> \
  --progress <ledger>.json --toc-md --test 6
python3 scripts/yuque_tree_import.py --root <clean_dir> --book <id> \
  --progress <ledger>.json --toc-md

# 5. 验收六查 + 根级顺序归位（见下）
```

## 构建规则（build_lib.py 干的 7 件事）

| # | 规则 | 为什么 |
|---|---|---|
| 1 | `partNN-xxx/` → `NN-第N部分 · 中文名/` | 部分名取自 README「完整目录」；**两位序号前缀让字典序天然正确**（否则 `第10部分` 会排到 `第1部分` 前面） |
| 2 | `chapter-N-xxx.md` → `N.M 中文标题.md` | 标题取自文件内首个 H1（无 SUMMARY.md 时的唯一权威） |
| 3 | `Part 21 · 第1章. xxx` → `21.1 xxx` | part21/part23 的 H1 是异体，不归一化会与全书 `N.M` 断层 |
| 4 | 半角 `/` → 全角 `／` | 文件系统不允许 `/`（5 处：`UX/UI`、`ArtGuide/06_UI`、`iOS / Android / PC`、`触摸 / 鼠标输入`、`decisions/`、`公司 / 个人 PC`）；语雀 toc-md 收全角无碍 |
| 5 | `\~` → `~` | markdown 过度转义，语雀会当字面量显示成 `\~`（5.1 标题） |
| 6 | `_front-matter.md` → `00-序 · 封面 · 阅读方法.md`；`_colophon.md` → `01-版权页.md` | 两篇根级前置文档，排到最前 |
| 7 | **仅当**首个 H1 == 最终文档标题时删掉该 H1 行 | 避免语雀「文档标题 + 正文首行 H1」双标题；不相等时保留 → 零信息损失（本书 100/102 命中，front-matter 的 H1 是书名故保留） |

## 根级顺序归位（坑 29 复发 + 本次新细节）

toc-md 收尾后根级 DOC 会排到 25 个 TITLE **之后**。用 `PUT /toc {action:prependNode, action_mode:sibling}` 顶回最前。

⚠️ **连续 prepend 两个节点必须按逆序做**：先 `01-版权页` → prepend 到 `01-第1部分 · 基础` 前，再 `00-序` → prepend 到 `01-版权页` 前。
本次先序后版权页，结果拿到 `版权页, 序`（同 target 连续 prepend 会反序）——第二发打回重做。

## 验收记录（六查全绿）

| 项 | 结果 |
|---|---|
| TOC 节点数 | 127 == 本地 127 ✅（结构核对 PASS，缺口 0） |
| 全路径唯一 / 缺失 | True / 0 ✅ |
| 幽灵文档 | 0（docs 102 == TOC DOC 102）✅ |
| 占位/空文档 | 0（102 篇逐篇回读 `word_count` 全 >0）✅ |
| 分片 | 无（最大文件 15.5KB，远低于 512KB）✅ |
| 保真抽查 | 2.3：`word_count` 6233 / svg 3 / mermaid 1；24.2：4191 / svg 0 / mermaid 5 ✅ |
| 根级顺序 | `00-序` → `01-版权页` → `01-第1部分…` → … → `99-后记与附录` ✅ |
