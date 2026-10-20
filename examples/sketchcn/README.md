# Sketch 中文用户手册（sketchcn.com）→ 语雀（站点下线 + 同源镜像仓库救图实战）

2026-10-20 实战。老板给的是 `http://sketchcn.com/sketch-chinese-user-manual.html#introduce`，
打开一看：**域名在售**（4.cn 的 for-sale 停放页，1.7KB），整站早没了。

## 一份薄薄的成绩单

| 项 | 值 |
|---|---|
| 正文来源 | Common Crawl **CC-MAIN-2019-18** 快照 `20190425144522`（最后一次收录该页，149KB HTML） |
| 配图来源 | 同源镜像仓库 `i5ting/sketchcn`（站长的翻译工作仓：`index.md` + `images/` + `sketchcn.com/` 整站快照） |
| 语雀库 | id=84783868 `Sketch 中文用户手册（2026-10-20）`，slug `sketch-chinese-manual-20261020`，分组「文章收集」36149506 |
| 结构 | 单页长文档按 `<h1>` 拆 15 章 + `00-前言`（书名/来源/目录）= 16 篇，平铺 |
| 导入 | `--toc-md` 目录树 16 行 / 569B，PUT **0.4s**，结构核对 PASS，0 失败 |
| 验收 | TOC 16 == 本地 16；全路径唯一 True；缺失 0；16 篇 word_count 全 >0；44 张 CDN 图逐篇对得上 |
| 图 | **44/44 全救回**（CC 对 `sketchcn.com/images/` 明确「No Captures」；图全部来自镜像仓库） |

## 关键动作（下一次遇到「站点下线」照抄）

1. **先探站**：`curl -I` 返回 200 但只有 1.7KB + `<h1>[xxx.com] is for sale</h1>` → 域名停放页 = 站点下线，别浪费时间抓正文。
2. **Common Crawl 用 prefix 查询**：`index.commoncrawl.org/{coll}-index?url=sketchcn.com%2F&matchType=prefix&output=json&limit=600`
   —— 先拿「哪些 collection 收录了这个域名」，再挑**时间最新的、且含目标页**的那个（本页只到 2019-04-25；2020 之后只剩域名停放页）。
3. **archive.org 别指望**：沙箱里 `web.archive.org` DNS 被投毒到 `face:b00c::`（Facebook），一律超时——直接走 CC。
4. **图片用 CC 明确结论收口**：`index.commoncrawl.org/CC-MAIN-2019-18-index?url=sketchcn.com%2Fimages%2F*`
   → `{"message": "No Captures found for: sketchcn.com/images/"}` 是**确定性空**（区别于 504 超时），
   可以据此断定「CC 没有图」，不用反复重试。
5. **⭐ 站点内容的反向镜像常挂在 GitHub 上**：`api.github.com/search/repositories?q=<域名>` / `q=<页面 slug>`
   - 本次一击命中 `i5ting/sketchcn`（repo description 直接写着 `http://sketchcn.com/sketch-chinese-user-manual.html#introduce`）
   - 仓库里同时有：**翻译源 md**（标题 oracle）、**images/**（160 张，含正文用的 44 张）、**sketchcn.com/**（整站 HTML 快照，含 `sketch-tips-tricks-1..4` 与 Sketch 2 手册）
   - 免费仓 clone 走 `https://gh-proxy.com/https://github.com/...`（直连慢）
6. **HTML 快照 vs 仓库快照取谁**：两者 diff 只有 7 处（CC 的 2019-04-25 版更晚：菜单项「编辑 >」已改「图层 >」、导航多了「插件素材」）→ **正文以 CC 快照为准，图片以仓库补**。

## 转换器要点（Adobe Muse 站，`build_manual.py`）

- **正文窗口**：侧栏手风琴导航（`<ul>` + `AccordionPanel`）之后 → `<div class="verticalspacer">` 之前；
  从「欢迎使用 Sketch 3」往回找最近的 `<div` 定起点最省事。
- **先剥 `<script>/<style>` + HTML 注释**（Muse 站有大量 Muse.* JS）。
- **块扫描**：`<(h[1-4])…>\|<p …>\|<img …>`，按出现顺序出块；行内只认 `<a href>`（外链保 URL、站内锚点剥成纯文本）与 `<span>`。
- **⭐ h3/h4 小标题在 Muse 里是 `<p>`**（`<p class="nomal-text" id="u4650-61">隐藏命令</p>`）：
  用**翻译源 `index.md` 的标题当 oracle**（去掉「（English）」后缀）→ 126/178 命中，还原成 `###`。
  额外规则：该标题在本页**另有真 `<h2>` 标签**（如「添加图层」在「图层」章）→ 这里是更小一级，压到 `###`。
- **列表**：Muse 把项目符写成**字面字符** `・`（还有 `•·Øü–`）→ 首字符映射成 `- `；收尾把连续列表项之间的空行压掉。
- **代码行**：`<p class="code">` → 三反引号块（`defaults write … -bool YES`）。
- **装饰图**：`images/mail.png`、`logo-diamond@2x.png`、`toolbox.png` 等都在正文窗口外，天然不沾；
  窗口内 44 张全部是正文截图 → 全量落盘。

## 复用流程

```bash
# 1. 探站（发现域名停放）→ 找 CC 里收录目标页的 collection
python3 cc_fetch.py CC-MAIN-2019-18 "http://sketchcn.com/sketch-chinese-user-manual.html" manual-2019-18.html

# 2. clone 同源镜像仓库拿图片 + 标题 oracle
git clone --depth 1 https://gh-proxy.com/https://github.com/i5ting/sketchcn.git

# 3. HTML → 分章 md（顶部 SRC_HTML / ORACLE_MD / IMG_SRC_DIRS 三个常量按需改）
python3 build_manual.py            # → clean/*.md + clean/images/

# 4. 图片传语雀 CDN（44 张 / throttle 3s / 约 2.5min）→ 再把 clean/images 删干净
python3 ../../scripts/yuque_rewrite_images.py clean ./sketch-img_map.json --throttle 3

# 5. 建库 + 移分组（「文章收集」36149506）+ 导入
python3 ../../scripts/yuque_repo_import.py create-book --name "Sketch 中文用户手册（2026-10-20）" \
  --slug sketch-chinese-manual-20261020 --desc "来源：… ｜ 站点已下线… ｜ 导入 2026-10-20"
python3 ../../scripts/yuque_tree_import.py --root ./clean --book <book_id> --progress ./progress.json --toc-md
```

## 转换保真度自检（本次做法，建议保留）

把源 HTML 窗口里所有 `<p>` 文本抽出来，逐条在生成的 md 全文里做「去空白/去项目符」的子串匹配：

```text
源段落 510，未命中 3（= 三句欢迎语，已补进 00-前言）
```

**100% 覆盖**才算过；比 grep 残留标签更硬。
---

## 第二批：Sketch 2 手册 + 15 篇技巧分享（同一个站，另建一库）

老板拍板「另建一个」（2026-10-20）。同一镜像仓库里还有 `chinese-user-manual-for-sketch2.html`
与 `sketch-tips-tricks-1~4.html`，一起入库。

| 项 | 值 |
|---|---|
| 正文来源 | Sketch 2 手册 CC-MAIN-2019-18 / 20190425144526；技巧分享 tips1 CC-MAIN-2019-18、tips2·3 CC-MAIN-2019-13、tips4 CC-MAIN-2019-22（tips1 在 2019-13 的索引查询超时，用 2019-18 的） |
| 语雀库 | id=84784119 `Sketch 中文网 · Sketch2 手册与技巧分享（2026-10-20）`，slug `sketchcn-sketch2-20261020`，分组「文章收集」36149506 |
| 结构 | 29 节点：`00-前言` + `01-Sketch 2 用户手册/`（11 章）+ `02-技巧分享/`（15 篇） |
| 导入 | `--toc-md` 目录树 29 行 / 1511B，PUT **0.8s**，结构核对 PASS，0 失败；根级前言落到两个 TITLE 之后 → 一发 `prependNode sibling` 归位 |
| 验收 | TOC 27 DOC == 本地 27；全路径唯一 True；缺失 0；27 篇 word_count 全 >0；83 处 CDN 图逐篇对得上 |
| 图 | **79 张**（其中 3 个动画 GIF 6.8MB/4.9MB/4.7MB）全传 CDN，0 失败 |

### 这轮新增的 4 个坑（已写进 refs 坑 38）

1. **一页多篇 → 按日期徽标重排**：每页 5 篇，每篇 `<h1>` 前有 `<div id="uNNNN-6"><p>Apr</p><p>4</p></div>`
   月/日徽标 → 抽出来当元数据、剔掉徽标块、**全局按日期排序**后编号（15 篇 = 2014-03-09 ~ 06-02）。
2. **底部翻页按钮 1/2/3/4**（`<a href="sketch-tips-tricks-N.html"><p>N</p></a>`）会被当成
   `### 1 ### 2 ### 3 ### 4` → 按 href 模式整块剔掉。
3. **连续 ≥3 个「标题」= 图的说明标签**：`隐藏工具栏/隐藏图层列表/隐藏检查器/同时隐藏图层列表和检查器`
   四个短句被启发式全升成 `###` → 收尾 `demote_head_runs(lines, 3)` 整体降回普通行。
4. **嵌套目录下图片引用要写 `../images/x`**：`yuque_rewrite_images.py` 按 **md 文件所在目录**解析
   相对路径（`base = os.path.dirname(fp)`）→ 文档进子目录后写 `images/x` 会全报「本地缺失」（0 上传）。
   另外：图收集时 **tips 那边已经是 markdown 图引用**，别只用 HTML 的 `src=` 正则抓（会漏 37 张）。

复用流程：`python3 build_extra.py` → `yuque_rewrite_images.py clean2 …` → 建库 + 移分组 + `--toc-md` + 前言归位。

> 另记一条 API 坑：`create-book --desc` 超长约 250 字符会返回 **`HTTP 400 验证失败，一般是路径名冲突…`**
> （报错完全误导，跟库名/slug 无关；实测 251 字通过、261 字被拒）。排查时拿短 desc 同名同 slug 试一发即可区分。
