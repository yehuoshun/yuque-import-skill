# 案例：AsciiDoc 书稿源（《Puppet 2.7 Cookbook 中文版》，2026-10-18）

老板给的触发链接是**老 gitbook 站点** `https://www.gitbook.com/book/wizardforcel/puppet-27-cookbook/details`
（302 → gitbook 首页，已死），但书内自述写着「中文翻译版的源码位于
`https://github.com/sinosmond/puppet-27-cookbook-CN`」（21★）——**源仓库是 AsciiDoc 书稿**，
不是 md 源。走开源项目口径（库名带 commit、分组「开源项目」stack 57018723）。

## 结论先行

| 项 | 值 |
|---|---|
| 库 | `Puppet 2.7 Cookbook 中文版（5415c55）` id=84708168 slug=puppet-27-cookbook-cn-5415c55 |
| 分组 | 「开源项目」stack 57018723 |
| 节点 | **134**（11 目录 + 123 文档：95 个处方 + 9 章首页 + 前置 5 篇 + 9 个子节） |
| 图 | 12 张全部 CDN（12 处引用 1:1，0 缺失） |
| 耗时 | 图 ~25s + 建文档 ~85s（toc-md 目录树 134 行 **PUT 1.0s**）+ 归位/验收 ~3min |

## 识别特征（AsciiDoc 书稿）

```
book.txt                 # 主控：标题下划线 + :Author:/:description: + [IMPORTANT] + include:: 清单
entries.txt              # :Recipe101: 使用版本控制 … 属性字典（节标题属性全在这）
asciidoc.conf            # asciidoc 配置（iconsdir/pygments 等）
00-translator_preamble.txt / 01-colophon.txt / 02-author.txt / 03-preface.txt   # 前置 4 篇
ch01-Puppet_Infrastructure.txt … ch09-*.txt   # 章首页（引言 + include::recipes/chNNsecMM-*.txt）
recipes/chNNsecMM-*.txt  # 95 个处方 = 正文主体
image/*.png              # 12 张插图（引用写作 image::image/x.png[]）
```
**特征**：`.txt` 里全是 AsciiDoc 标记（`==` 节标题 / `[source,puppet]` + `----` / `....` 字面块 /
`[NOTE]/[TIP]/[IMPORTANT]` + `====` / `+x+` 行内等宽 / `*粗*` / `{属性}` / `[[锚点]]` / `<<锚点,文字>>`），
**没有任何 `.md`**；层级只在 `include::` 里 → 必须写 AsciiDoc→Markdown 转换器（本目录 `adoc-build.py`）。

## 转换规则（adoc-build.py 实现）

| AsciiDoc | Markdown | 备注 |
|---|---|---|
| `== / === / ==== 标题` | `# / ## / ###` | 降一级；章首页 `==` → `#` |
| `{Recipe101}` `{Gettingready}` `{Howtodoit}` `{Howitworks}` `{Theresmore}` `{Seealso}` | 中文文字 | **只替换 entries.txt 里定义过的属性**；代码块里的 `{name}`/`{md5}` 未定义 → 原样保留（关键！） |
| `[source,puppet]` + `----` | ` ```puppet ` | 305 处；另 ruby/bash/yaml/apache |
| `....` / `..................`（≥4 点） | ` ``` ` | 字面块（shell 输出），无语言 |
| `[NOTE]/[TIP]/[IMPORTANT]` + `====…====` | `> **注/提示/重要**` | 块标题 `.译者注` 并入标签 → `> **注（译者注）**` |
| `[quote, 说话人, 出处]` + 一段 | `> 引文 "出处"` + `> —— 说话人` | 出处紧跟引文（与站点渲染一致） |
| `****…****` 侧栏 / `--…--` 开放块 | `>` 引用块 / 只剥壳 | |
| `.块标题` | `**块标题**` 独立一行 | 警告块的块标题除外（并入标签） |
| `[[anchor]]` / `<<anchor,文字>>` | 删除 / 取文字 | |
| `+x+` `++x++` → `` `x` ``；`*x*`→`**x**`；`http://u[文字]`→`[文字](u)`；`http://u[]`→`<u>` | | |
| `- / * / **` 列表 | `-`，按星号数缩进 2 空格 | |
| `1.` / 子项 `a.`（缩进 3 空格） | `1.`，缩进 3 空格 | 字母序号统一成 `1.`（md 不认字母） |
| 列表项后的 `+`（续项） | 后续块缩进到列表项内容列 | 代码块也能进列表项；`--` 开放块内的空行**不断**续项 |

## 踩过的坑（写转换器时的真实 bug，逐条留着）

1. **围栏闭合行必须自己输出**：闭合分隔符被吃掉不输出 → 每个代码块只剩一个围栏（37 篇 md 围栏奇数）。收尾自查：`grep -c '^\s*```'` 必须偶数。
2. **代码块闭合要认类型**：`....` 块必须用 `^\.{4,}$` 收，不能用 `^-{4,}$`（代码里全是 `-----` 分隔线，会被误收）；反之亦然。状态机里不能在闭合判断前把行写进输出。
3. **BOM**：书稿 `.txt` 全带 UTF-8 BOM → `\ufeff[[colophon]]` 破了 `^\[\[.*\]\]$` 锚点正则（16 个锚点残留）。读源码一律 `encoding="utf-8-sig"`（写文件仍用 `utf-8`）。
4. **`[master]`/`[myapp]`/`[mysqld]` 不是块属性**：git config / MySQL 配置片段里满屏 `[...]` 段头 → **只认白名单**（`[source,x]` / `[NOTE|TIP|IMPORTANT|WARNING|CAUTION]` / `[quote,…]`），且在代码块状态内一律不解析（引号包裹的 `[source,puppet]` 出现在 NOTE 正文里也是文字）。
5. **数组/编号列表项的续项缩进**：`push()` 会把刚设好的续项缩进又加到列表项自身 → 列表项先清 `cont` 再设，否则整列多缩 2~3 空格。
6. **`--` 开放块内的空行不能清续项**：`+ -- 空行 --` 序列里，空行清 `cont` 会让后续代码块掉出列表项 → 用 `open_depth` 计数挡住。
7. **警告块里嵌代码块**：`[NOTE]` + `====` 里还能再套 `[source,puppet]` + `----`（2 处）→ 注释状态里再开一层 `> ```lang ` 围栏。
8. **`class Conv.run` 里别定义局部函数**（`flush_title`）再看 `self` 使用顺序 —— 块标题丢了两次才发现（`.历史说明:` / `.Git and Github Useful Links`）。

## 验收：站点当 oracle 逐页比对（verify.py）

老 gitbooks.io 渲染站仍在线（`https://wizardforcel.gitbooks.io/puppet-27-cookbook/content/`，
`index.html` + `1..122.html` = 123 页，与本地 123 篇 1:1）→ 拿它当**逐页文本 oracle**：

- 按**标题**配对（站点 `6.1. 使用版本控制` ↔ 本地 `使用版本控制`），归一化（去标记/标点/空白）后算相似度
- **实测 120 页 ≥0.990（绝大多数恰好 1.0000）**；3 页低于阈值且**只增不减** → 站点渲染的是**旧版书稿**（源仓库 HEAD 有后续修订，如 09.02/09.10 两段译文），不是转换器丢字 → 验收器把「只增不减」单独归类为**站点滞后**，不算差异；真差异（有删有改）才 FAIL
- **站点抓取要限速**：并发 8 抓 122 页里有 13 页返回 GitBook 404 页（假 404）→ 串行重抓即正常，抓完必须 `grep -l "Page Not Found" *.html` 自查
- 另有 ④四查（节点数/全路径唯一/幽灵文档/根级顺序）+ ⑤逐篇回读（语雀正文 ↔ 本地 md，123 篇 0 差）
- ⚠️ 站点页 `06·7.1 生成报告` 这类标题在本机比对**按标题索引**，别按序号对（站点序号含索引、且本书章节序号与站点一致纯属巧合）

## 流程（可复用）

```bash
# 0. 克隆（GitHub 直连 502 → 走 gh-proxy）
git clone https://gh-proxy.com/https://github.com/sinosmond/puppet-27-cookbook-CN.git tmp/puppet27-src
# 1. AsciiDoc → md 干净树（含 image:: → _imgs/ 相对引用）
python3 examples/puppet-cookbook/adoc-build.py          # 123 文档 / 11 目录 / 12 图
# 2. 图传 CDN 并重写引用（缓存 img_map 断点续传），然后删 _imgs
python3 scripts/yuque_rewrite_images.py <clean> tmp/puppet27-img_map.json --throttle 2
rm -rf <clean>/_imgs
# 3. 建库 + 分组
python3 scripts/yuque_repo_import.py create-book --name "Puppet 2.7 Cookbook 中文版（5415c55）" \
    --slug puppet-27-cookbook-cn-5415c55 --desc "<repo url> @ 5415c55"
python3 scripts/yuque_repo_import.py move-stack --book-id <id> --stack-id 57018723
# 4. 导入（toc-md 默认口径）
python3 scripts/yuque_tree_import.py --root <clean> --book <id> --progress <账本> --toc-md
# 5. 根级归位（toc-md 后根级 DOC 会落到 TITLE 之后）
python3 examples/puppet-cookbook/fix_root_order.py <id>
# 6. 对账 + 验收
python3 scripts/yuque_toc_reconcile.py --root <clean> --book <id> --progress <账本>
python3 examples/puppet-cookbook/verify.py <id> --readback
```

## 实测结果

```
① 节点数: TOC 134 / 本地 134 → PASS      ② 全路径唯一: 134/134 → PASS
③ 幽灵文档: TOC DOC 123 / /docs 123 → PASS  ④ 根级顺序 → PASS
逐页比对: 120 页 ≥0.990，3 页站点滞后，0 页真实差异 → PASS
⑤ 逐篇回读: 差异页 0 → PASS
映射验收（yuque_import_verify.py）: 123/123 单文档映射、缺失 0、全路径唯一 → PASS
```

## 版权备注

原书为 **Packt 封闭版权**作品，译者自述「鉴于版权原因请不要在公网上直接发布任何
HTML/PDF/epub/mobi 版本的中文翻译」。本库导入**仅进语雀私有知识库**（老板个人库），
`00-书名页.md` 保留了书内 `[IMPORTANT]` 版权声明原文；**不要**把本库内容同步到任何公开站点/仓库。
