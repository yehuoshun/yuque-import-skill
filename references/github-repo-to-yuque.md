# GitHub 开源项目 → 语雀导入 SOP（2026-10-12 老板固化）

> 触发模板：「把 `<repo>` 按开源项目流程到语雀」——repo 可给 https 或 `git@` SSH 链接。
> 实战记录：HowToCook / kairisei-ma-ch / STS2 全家桶 / legado / deepwrite×3 / owllook / Git-Cheat-Sheet 等 20+ 项目。
> ⚠️ 2026-10-14 老板拍板：**GitHub Actions 版批量导入已砍掉**（CI 易失败 + 难排错：360min job 上限硬掉、进程被杀后零中间日志、慢链路无法干预）。批量导入一律按本 SOP 在本地跑，账本跑完手动 commit。

## 一、规范（老板定，不要改）

| 项 | 值 |
|---|---|
| 知识库名 | `项目名（commit id）`，commit 取 8 位短哈希，如 `deepwrite（85577e7）` |
| slug | **老板 2026-10-13 定策略**：开源项目 = `项目名-commit`（天然防撞，同 repo 不同 commit 不同 slug）；网站/自定义 = `网站名-YYYYMMDD`（同日同站会撞 → create-book 已内置撞名兜底：422 时自动追加 `-2/-3` 序号重试）；slug 为 v2 API 必填字段（不传 422 missing_field，官方不会自动生成） |
| 描述 | `<repo url> @ <commit>`（如 `https://github.com/swjybky/deepwrite @ 85577e7`） |
| 知识库分组 | **开源项目**（stack id `57018723`） |
| 归属 | 私人空间下（`/users/<用户名>/repos`） |
| 可见性 | private（public=0） |
| 节点上限 | **5000（语雀硬上限，2026-10-14 老板拍板）**：`prep` 节点数 >5000 必须分库——按顶层目录拆成多个库（命名 `项目名-<顶层目录>（commit）`，slug `项目名-<目录>-commit`），不硬塞单库；导入脚本 `prep` 已内置 >5000 警告 |
| 中间产物 | 镜像 / 干净副本 / 账本 / 日志一律放 `workspace/tmp/`（沙箱重启会清 `/tmp`） |

## 二、流程（七步）

前置：`source ~/.openclaw/secrets/credentials.env`（TOKEN_L91）；`cd code/yuque-import-skill`。

1. **prep（克隆/更新 + 干净副本 + 节点数）**
   ```bash
   python3 scripts/yuque_repo_import.py prep --url <git-url> --dir /home/admin/.openclaw/workspace/tmp
   # 输出: repo / branch / commit(8位) / nodes(dir+file) / clean_dir
   ```
   - 已有镜像会自动 fetch 增量更新；HEAD 没变且该 commit 已导过 → 直接复用旧库，不用重导
2. **dry-run 核数**（用上一步的 clean_dir 和 commit 起名账本）
   ```bash
   python3 scripts/yuque_tree_import.py --root <clean_dir> --book <book_id> \
     --progress /home/admin/.openclaw/workspace/tmp/<repo>-<commit>-progress.json --dry
   ```
3. **建库 + 移分组**
   ```bash
   python3 scripts/yuque_repo_import.py create-book --name "<项目名>（<commit>）" \
     --slug <项目名>-<commit> --desc "<repo url> @ <commit>"
   # 拿到 book_id 后：
   python3 scripts/yuque_repo_import.py move-stack --book-id <book_id> --stack-id 57018723
   ```
   - move-stack 内置 30s 等待 + 每轮重发移动(幂等) + 验证, 总窗口 ~4.3min（新建库立刻移动会失败，2026-10-12 实踩；10-13 三例复现：传播 30s~4min 不定，仅重试验证不够 → v1.2.2 改为重发+验证循环）+ 移动后自动验证分组
4. **test 6 试水** → 全量导入（**后台跑**，禁 nohup——exec-guard 会拦；用 exec `background=true`）
   ```bash
   # ✅ 推荐：toc-md 模式（官方 v2 一次性目录，2026-10-16 起默认）
   python3 scripts/yuque_tree_import.py --root <clean_dir> --book <book_id> \
     --progress /home/admin/.openclaw/workspace/tmp/<repo>-<commit>-progress.json --toc-md
   # 回退（旧流程，逐节点挂载 / batchMove）：去掉 --toc-md；batch 模式加 --batch-mode
   ```
   - toc-md 原理：`POST /repos/{book}/docs` 建文档后**自动挂 TOC 根**，收尾拼一棵 Markdown 目录树 → 一次 `PUT /api/v2/repos/{book_id} {toc: "..."}`（官方 OAS 20260722）。同树实测：与 batch 模式 TOC **集合+顺序完全一致**，134 节点 PUT 仅 1.1s，收尾从 ~80 分钟降到秒级，且**不需要 cookie**
   - 旧全量命令（无 `--toc-md`，逐节点挂真实父）：测试时高频创建会触发 TOC 写路径积压（坑 67），现已不推荐
5. **心跳汇报**：25% / 50% / 75% / 完成，各报一次（读 progress 账本算百分比）
6. **对账**：`python3 scripts/yuque_toc_reconcile.py --root <clean_dir> --book <book_id> --progress <账本> [--fix]`
7. **验收四查**（缺一不可）：
   - TOC 节点数 == 本地节点数 —— **⚠️ 只对无分片库成立**；超限分片后节点数必然 > 本地文件数（标题 `x.json (1/14)`），改用 `scripts/yuque_import_verify.py` 做「本地文件树 ↔ TOC 全映射 + 分片号连续 + 全路径唯一」验收（2026-10-15 legado 固化）
   - 对账「错位 DOC: 0」
   - 幽灵文档 = 0：`yuque_list_docs` 的 total == TOC 里 DOC 数（cleanup_leftover 只删 TOC 条目不删 doc 本体，曾积 7 个幽灵）
   - 深层路径抽查（如 `apps/.../components/xxx.vue`、`package.json`）实际可达

收尾：汇报库链接 + 节点数 + 对账结果；更新 `memory/YYYY-MM-DD.md`。

## 三、坑清单（全踩过，逐条防）

1. **新建库立刻 move-stack 会失败**（重试 3 次仍失败）→ 等 ~10s 或带 `--wait` 重调
2. **appendNode 不带 target_uuid 建根级 TITLE → 坏节点**：往它下面挂子节点静默落根（HTTP 200 无报错）。
   修复：删坏节点 → `appendNode action_mode=sibling + target_uuid=<前一个根节点>` 重建
3. **沙箱重启**：进程死、`/tmp` 清空 → 账本/日志必须 `workspace/tmp/`；重启后重跑同命令即断点续传
4. **nohup 后台被 exec-guard 禁** → 用 exec `background=true`；杀进程用 `pkill -9 -f yuque_tree_import`（kill 不杀 python 孤儿）
5. **removeNode 删子树乐观回显陷阱**：响应看着正常实则整库 TOC 连带被清 → 删除/移动后必须 `GET /toc` + `GET /docs/{id}` 双重复查
6. **对账脚本别用 `.lstrip('./')` 判断路径**（会把 `.agents` 的点剥掉虚报 41 个）→ 用 `startswith('./')`（脚本已修，若再遇先查这）
7. **移动后验证分组**：`get_book_stacks` 看分组名，别只看 stack_id 数值（曾误移「文章收集」36149506）
8. **移动端点是 `PUT /api/mine/book_stack/move`**（body `{targetStackId, targetBookIds}`）——旧 `PUT /api/books/{id}` + `{stack_id}` 返回成功但不生效，2026-10-12 实踩（库落进「其他」分组）；wrapper 已内置回查验证兜底

## 四、reST/Sphinx 工程特殊处理（2026-10-13 固化，Got GitHub 实战）

触发：源仓库是 Sphinx/DocBook 类（`.rst` 文件 + `conf.py/Makefile/_build` 构建垃圾）。

1. **探结构**：`find . -maxdepth 2 -type d`——正文在章节目录（如 `01-explore-github/`），`_build/_static/_templates/_theme/contrib/graphics` 全是构建产物
2. **剔垃圾**：`yuque_rst_convert.py --src <clean_dir> --out <book_dir>`（默认跳过 `_build,_static,_templates,_theme,contrib,graphics,images`）
   - rst→md 用 docutils 0.23 中间层（pandoc 沙箱装不上：tuna 403 / PyPI 超时）
   - `.md`（如 README.md）原样复制；root 级 `index.rst`（书总目录）/`preface.inc` 转出后按需改名（如 `00-目录.md`/`00-前言.md`）
3. **导入**：章节目录天然成 TITLE 组（树导入自带层级），一般无需再整理目录；根文档留根
4. 转换器已踩坑（脚本 docstring 内）：docutils html5 脚注引用是 `role=doc-noteref` 且必须先于链接正则剥离；`</\1>` 不能配非捕获组

## 五、坑清单补充

9. **中断克隆的 NFS 卡死句柄（2026-10-13 实捶）**：SIGTERM 半截克隆会在 tmp 留 `.nfsXXXXXX` 锁文件，`rm -rf` 报 Device or resource busy、git fetch 也失败——把整个目录 `mv` 走（锁文件跟着走），再重新克隆到干净路径。避免半截克隆残留的方法：克隆前先 `pkill -9 -f <repo名>` 确认无残留进程
10. **同名文件按标题操作是雷（2026-10-13 实捶）**：多目录同名（如各章节都有 `index.md`）时，任何按【标题】匹配的更新/对账都会互相覆盖（GotGitHub 5 个章节 index 被覆盖事故）。铁律：**定位一律用「父目录+标题」**（TOC 节点 parent_uuid → 父 TITLE 标题 + 自身标题）；更新后必须 GET 回读逐字节比对。**2026-10-15 rea 复踩**：库里同时有根级 `package.json`（真实文件）和 `website/.../notes-electron/package.json`（错位节点），只看标题把根级那个当重复删了 → 丢一篇正文（后靠账本回滚重建）。删任何节点前先拿账本 uuid 对上，**标题相同 ≠ 同一条目**
11. **prep 只 fetch 不快进 → 导旧内容（2026-10-15 owllook 事故，已修）**：老版 `prep` 更新已有镜像时只跑 `git fetch origin`，工作树仍停在旧 commit，随后 tar 出来的是**旧工作树**——但打印的 commit 是新短哈希，于是「库名/描述写新 commit、内容全是旧的」，静默错版。当场表现：新 commit 只动 3 个文件，节点数却和旧 commit 一样（224→224），新文件 `build-check.yml`/`.vscode/tasks.json`/`public/fonts/fa-solid-400.woff2` 在干净副本里查不到。修法：fetch 后比对 `HEAD` vs `origin/<branch>`（脏工作树也算），不一致就 `checkout -f <branch>` + `reset --hard origin/<branch>` + `clean -fdx`，打印「工作树已硬同步 → <commit>」。**防呆**：prep 报的节点数没变 = 第一嫌疑，先核 `git log -1` 和 `git status -sb`（`behind N` 就是没同步）。
12. **产物验证必须跑 tail 抽查（2026-10-13 老板抓包）**：网站抓取后 grep 导航特征词只防「出现在正文任意处」，底部面包屑导航（上一页/下一页/»）在尾部照样漏——验证清单加：`for f in site/*.md; do tail -2 $f; done` 全量扫尾，或 grep 特征词覆盖 `上一页|下一页|»|导航目录词`。GotGitHub 40 篇尾部导航全中，就是没跑 tail 漏的
13. **分片标题含 `/`，验收别拼字符串（2026-10-15 legado 实战）**：超 512KB 分片后标题是 `2a1f129b.json (1/14)`——**这个 `/` 是真雷**：`os.path.dirname("sources/2a1f129b.json (1/14)")` 得到 `sources/2a1f129b.json (1`，一键把 6 个分片文件全判成「缺失」（实际 95 个分片节点都在）。验收一律按 TITLE 列表（uuid 父链）比，别拼字符串；节点数口径换成分片感知版 → `scripts/yuque_import_verify.py`。
14. **杀掉/重启导入后必跑 reconcile --fix（2026-10-15 rea 实战）**：TOC 写路径积压期，节点会「HTTP 200 但落在根级」（本次 9 个：`licenses/Apache-2.0.txt`、`third_party/binwalk`、`src/ida/IdaWorkspace.ts` 等）。① 高频失败时先静置 ~10 分钟排空语雀写队列，再用 `--pend-sleep 300 --pend-retries 5` 重启（断点续传不丢已导节点）；② **重启后无条件跑一次 `yuque_toc_reconcile.py --fix`**——脚本自己不会发现「已记账但挂错层级」；③ 个别 TITLE 修不动时手搓 `PUT /toc {action:appendNode, action_mode:child, target_uuid=<父>, node_uuid=<它>}` 再复查；④ 误删了节点不要慌：备份账本 → 删掉该路径的 key → 重跑同一条导入命令，按原路径重建（本次根级 package.json 就是这么补回来的）。

15. **目录标题一律原样写，禁转义（2026-10-16 实测）**：`PUT /repos/{id}` 的 markdown `toc` 里，`[weird[1] (x).md](slug)` 原样写是对的；加反斜杠 `\[` 或 HTML 实体 `&#91;` 会被**当字面量写进标题**（标题变脏）。语雀按**最后一个 `](slug)`** 切分——实测 7/7 恶心标题全对：`x]` / `a]b` / `a](b` / `p[q](r` / `尾]` / `(paren]` / `】中文】` / `a\b`
16. **官方 v2 的 removeNode 语义（2026-10-16 核 OAS 20260722）**：`action_mode=sibling` 删当前节点，`action_mode=child` **删当前节点及子节点**；官方明写「删除节点不会删除关联文档」（→ 幽灵 doc 必须另走 `DELETE /repos/{id}/docs/{id}`）。旧「removeNode 乐观回显清库」事故更像 **action_mode 用错/缺省**（挂在根上就得清库），不再是单纯的响应假成功问题
17. **限流（官方文档）**：每小时最多 5000 次、每秒最多 100 次，**同账号所有 Token 共享**；响应头带 `X-RateLimit-Limit/Remaining`。**batchMove 单次节点数服务端硬上限 = 500**（超过报 HTTP 400 `limit_exceeded: 单次最多只允许操作 500 个节点`，2026-10-16 rea 实战实测）；200 节点以内验证正常（无 100 上限）。逐节点干活很吃配额——toc-md 模式每文件只需 1 次请求，天然省配额
18. **batch 模式遇「同名目录」会串 uuid → 整树错位（2026-10-16 rea 重导版实战）**：仓库里有多处同名目录（如 `bridge/cutter` 与 `src/cutter`；`scripts/fixtures/firmware`、`scripts/verify/firmware`、`tests/fixtures/firmware`）时，batch 模式（节点统一挂根 + batchMove 归位）记录目录 uuid 会按标题匹配到「另一个同名的根级节点」，导致 progress 里**两条 rel 指向同一个 uuid**；随后 batchMove 按这些 uuid 归位 → 大批节点父链错乱（本次实测 2938 条错位、2179 文件路径对不上、TOC 全路径唯一 = False；用 verify 脚本一跑即现）。**对策：含同名目录/文件的仓库不要用 batch 模式，直接上 `--toc-md`（按本地树 DFS 拼 markdown 一次 PUT 设整棵目录，天然按层级区分同名，无 uuid 归属歧义）**
19. **救援：batch 留下的错位树，用 toc-md 原地重建（免重导正文，2026-10-16 rea 实战）**：文档本体（doc_id/正文）是好的，只是父链乱。做法：① 拉全量 docs（`GET /repos/{id}/docs` 分页）建 `doc_id → slug` 映射；② 回填进 progress 各 segment 的 `slug`（batch 模式的 progress 不存 slug，否则 `build_toc_md` 直接 KeyError 'slug'）；③ 原样跑 `yuque_tree_import.py --toc-md`（全 skip → 只拼树 + 一次 PUT + 回读回填 uuid + 结构核对）。本次 4425 节点 PUT 22s，结构核对 PASS、对账 0 错位、verify PASS、幽灵 0，TOC 4446 节点（DOC 4080 + TITLE 366）全路径唯一 True。**toc-md 的 PUT 以本地树为准重排整棵目录，同名 TITLE/旧节点被复用重挂，无需手工清理**
20. **batch 归位失败不会真正降级（2026-10-16 核实）**：`flush_group` 在 batchMove 异常分支只记 fail 并打「→ 降级单节点」，**实际并未逐节点降级**；失败节点不会自动兜底，重跑也不自愈。所以 batch 模式一旦批量失败就是硬伤 → 改用 toc-md 或手搓重建
21. **`--test N` + `--toc-md` 混合流程的 slug 坑（2026-10-16 elinux 实战，脚本已修）**：先用 `--test N`（非 toc-md，appendNode 路径记账只有 uuid/doc_id、**无 slug**）探路，再全量 `--toc-md`，收尾 `build_toc_md` 会 `KeyError: 'slug'`（挂在测试阶段那几篇上）。修法：`build_toc_md` 缺 slug 时按 `doc_id` 回查 `GET /repos/{book}/docs/{doc_id}` 补上（已内置自动生效）。
    **顺带纠一个认知**：脚本 docstring 写「POST /docs 后自动挂 TOC 根」，但 **1949 次连续建文档后 TOC 里只有最初 6 个节点**（自动挂根在高频下没生效/积压）——**不影响结果**：toc-md 的整树 PUT 以本地树为准重排，最终 TOC 2936 节点全对（DOC 1950 + TITLE 986）。所以 toc-md 模式下不必纠结「文档是否已进 TOC」。
22. **老 gitbooks.io 链接已死（2026-10-16 elinux 实战）**：`<name>.gitbooks.io/<book>/content/<lang>/` 这类旧版 URL 集体 404（旧版托管下线）；现站（`<name>-1.gitbook.io/<book>/`）可能只剩 1 页（`curl /~gitbook/site-index` 一看便知：`pages` 就 1 条）。→ **别硬爬，改从源仓库导**（GitHub 搜书名/站名找 repo）。另：`git clone` HTTPS 走代理也 502 → 用 SSH（`git@github.com:...`）秒下。
23. **书型仓库：只导内容树，工程脚手架不进库（2026-10-17 yeasy/docker_practice 实战）**：书仓库常在根目录混着 `scripts/ tools/ tests/ .github/ .docker/ .devcontainer/ examples/ package(-lock).json check_*.py docker-compose.yml _config.yml Makefile` 等脚手架 —— 全导会把 `package-lock.json`（94KB）、CI 工作流、单元测试全塞进知识库。口径：**导入根 = 章节目录（如 `01_..21_`、`appendix`）+ `README.md`/`SUMMARY.md`/`CHANGELOG.md`/`CONTRIBUTING.md`**，脚手架全剔（在报告里列清楚，老板要再补）。图片：先 `scripts/yuque_rewrite_images.py`（扫 md **与 HTML `<img src>`** 的相对引用→传 CDN→重写；**未被引用的图不传**），随后把 `_images/` 目录 + `.graffle` 源块 + 所有图片文件从导入根**删干净**（否则每张图变成占位文档）。本次 279 节点（42 目录 / 237 文件）→ toc-md 目录树 279 行 / 10KB、PUT **1.6s**、四查全绿。
    **反向情形**：若仓库就是**纯 GitBook 源**（只有章节目录 + `README/SUMMARY/book.json` + `images/`，无脚手架，如 `widuu/chinese_docker`）→ **直接全导**（除 `.git/.gitignore`），`book.json` 保留（书元数据）；图片仍走 rewrite_md_images + 删 `images/` 目录（2026-10-17，66 节点，PUT 0.8s）。
24. **语雀附件上传接口有账号级限流：突发批量传图 ~500 张即 429（2026-10-17 freebsd-ask 实战）**：845 张图连传（~2 张/秒）到第 500 张后，`POST /api/upload/attach` 恒返 `429 {"status":429,"message":"操作过于频繁，请稍后再试"}`，**无 Retry-After 头**；同时段 v2 API（`GET /repos/{id}`）完全正常 → 是附件上传端单独的账号级风控（User/Book 两种 attachable 都限）。窗口 **~40 分钟后自愈**（07:12 封 → 08:10 恢复）。做法：① `upload_image` 内置 **429/5xx 退避重试**（5/10/20/40/60s，最多 6 次）；② 批量传图脚本加 **节流 5s/张**（~12 张/分钟）；③ 断点续传靠 `img_map.json` 缓存，重跑只补未传的；④ 后台“失败等 120s 再试”耐心重试陪跑，窗口一开自动续。本次 845 张：500 张 → 等 40 分钟 → 345 张（5s 节流）≈ 1 小时。
25. **VuePress 类文档站的图是 HTML `<img src>`，只认 markdown 的图片重写脚本会整站漏图（2026-10-17 bilibili-API-collect 实战）**：`assets/img/*.svg` 这类 UI 示意图在这类仓库里几乎全写成 `<img src="../../assets/img/like.svg" ...>`（也有 `width/height` 等属性），旧 `rewrite_md_images.py` 的 `!\[[^\]]*\]\(([^)]+)\)` 一条都匹配不上 → 图全裂。**已固化 `scripts/yuque_rewrite_images.py`**：同时吃 markdown `![]()` 与 HTML `<img src>`（先跑 HTML_RE 再跑 MD_RE），外链原样跳过，`img_map.json` 断点续传，`--throttle` 控速防 429，`--dry` 只统计。本次 77 张本地图（89 处引用）→ 全传 CDN，0 失败（远低于 500 阈值）。**验收补一条**：`md 里 CDN 引用处数 == img_map 的 URL 在 md 中出现次数`（本次 89 处 / 77 唯一 URL），再抽 5 张实拉 200 看 content-type。
26. **`--toc-md` 模式不能配 `--test N`（2026-10-17 实测）**：`--test 6 --toc-md` 跑完会记 1 条 fail ——「(toc-md) 生成目录树失败: 缺少文档记录, 无法生成目录: docs/activity/list.md」。原因：收尾的目录树按**本地全量树**拼，而测试阶段 progress 只记了 6 个节点 → 树里其余节点找不到 doc 记录。toc-md 模式**直接全量跑**（前几篇若已导会走 skip，幂等）；真要试水就单跑不带 `--toc-md` 的 `--test N`（只验 API/权限/正文），再全量 `--toc-md`（此时靠坑 21 的 slug 兜底）。
27. **已 archived / 被下架的仓库：prep 拿到的是空壳，内容只能从 fork 取（2026-10-17 bilibili-API-collect 实战）**：`SocialSisterYi/bilibili-API-collect` 2026-01-28 收到 B 站委托律所律师函，默认分支改名 `deprecated`、**历史被 force-push 抹成 3 个 commit**（只剩 `README.md` + `reason.jpg`，prep 报 `nodes=2`）→ 本仓库历史里已无正文，`git log`/`HEAD~1` 都翻不出来。做法：① `git ls-remote --heads origin` 看还剩哪些分支；② GitHub API `GET /repos/{owner}/{repo}` 看 `archived`，`GET /repos/{owner}/{repo}/forks?sort=stargazers` 挑活跃 fork（本次 `Goooler/bilibili-API-collect`（trunk）2026-09 仍在更，`BACNext/bilibili-API-collect-backup` 是下架当天备份）；③ **prep 的镜像目录名 = repo 名**，已有旧镜像会被复用并 `git fetch origin`（认的还是旧 origin）→ 先把旧目录 `mv` 走再 prep 新 URL；④ 库描述/命名照 fork URL + commit 写。⚠️ 若原仓库是因**法律/版权**下架，重新发布前先跟老板确认（本次老板拍板走 fork）。
28. **JSON 超限分片曾整段丢内容（2026-10-17 实捶，v1.3.50 已修 + 补验收）**：`_split_json_list` 里写的是 `_json_text(cur, start, idx)`——`start/idx` 是**文件级绝对下标**，而 `cur` 是**每次 flush 后重置的段内列表** → `cur[145:207]` 恒为 `[]`，于是：第 1 片对（start=0）、第 2 片丢尾巴、**第 3 片起全是 `[\n\n]` 空壳**。legado `sources/b778fe6b.json`（20.9MB / 3907 条）实测只进去 0.79MB（其余 3~40 片全是空壳）。正确写法：取整段 `cur[0:len(cur)]`。影响面：**只命中顶层是 JSON 数组的文件**（顶层对象/非 JSON 走行边界切分，那套用 `"".join(cur)` 是对的）——全量排查账本后只有 **legado 库**中招（rea 的 `6.5.0.contributions.json`、kairisei 的 `cn602-save-template.json` 都是顶层对象 → 不受影响）。
    **两个教训**：① `yuque_import_verify.py` 只验**路径映射**（节点在不在 / 分片号连不连续），**不看正文** → 几个库全 PASS 没拦住；新增 `scripts/yuque_verify_shards.py`（逐片回拉正文、拼回与本地逐条/逐字符比对）+ SKILL 验收第 4 条强制跑。② 改切分类逻辑必须配「**拼回去 == 原文件**」的回拼单测（`scripts/test_split_json_shards.py`，6 项，不联网），单看片数/片长看不出来。
    **验收脚本自己也会错（2026-10-17 rea 实战，同日已修）**：`yuque_verify_shards.py` 首版有两个 bug → 把 rea 的 **20/20 个分片文件全报假失败**（看着像内容丢了，其实完好）：① 剥壳时**先剥围栏再切尾注**，尾注的前导 `\n\n` 没人吃 → 每片多 6 字符；② `except Exception as e` 的 `e` 出了作用域就被 Python 删了 → `UnboundLocalError`。修法：**先 `rfind("<!-- 分段")` 切尾注并吃掉前导 `\n\n`，再去围栏**；错误信息存单独变量。judging 方法改双路：先「拼回文本逐字符相等」（覆盖行边界切分），不行再「数组回拼逐条相等」（覆盖 JSON 条目边界，段内是重排版 JSON，本来就不可能文本相等）——两条都写了单测。**教训：验收器本身也要先证能变红/能变绿**，否则假失败会把好结果报成事故。
29. **删「图片目录」前要扫两类漏网引用 + 目录里夹杂的非图片文件（2026-10-17 rea 实战，上版遗留问题）**：`yuque_rewrite_images.py` 只吃 `![]()` 与 `<img src>`，实战里出现两种漏网：① **「查看大图」的普通链接** `[文字](../../website/public/assets/figures/x.svg)`（不是图片语法）→ 图片文件被删后成了死链（rea 20 处）——用一条 `re.sub` 把它们改到**同一张图的 CDN URL**（图已传过就复用，不必重传）；② **图片目录里夹杂被引用的非图片文件**，如 `website/public/assets/licenses/dinosaur.txt`（Chromium/BSD 许可文本，被 3 篇 md 引用）——**整目录 `rm -rf` 会连带删掉它**（rea 上版就这么丢了内容）。做法：删目录前先 `grep -rnoE '\]\([^)]+\)' --include='*.md'`（不限定 `!`）列出所有指向该目录的引用，逐个判断是「图片（改 CDN）」还是「文本（保留）」；删完再扫一遍残留本地引用必须为 0。
    **顺带**：存量 `img_map.json` 可跨版本复用（key = 相对导入根的路径）——同仓库重导时先 `cp` 旧 map 做缓存，零上传直接用上版 CDN URL。
30. **HTML `<img>` 的 src 可能是单引号、也可能伸到导入根之外（2026-10-17 tinyclub/linux-doc 实战，v1.3.55 已修）**：`yuque_rewrite_images.py` 的 `HTML_RE` 原写死 `src="` → `<img src='../pic/x.jpg' width='110px'/>`（GitBook 老书的公众号二维码就这么写）**整条漏传**，正文里留着相对路径 = 裂图。修法：正则改 4 组 `(<img\b[^>]*?\bsrc=)(["\'])([^"\']+)(["\'])`（引号原样保留），sub 拆成 `sub_html`/`sub_md` 两个（组数不同，共用会错位）；补不联网单测 `scripts/test_rewrite_images_re.py`（9 项，单双引号 + 多行属性 + 反例）。
    **另一坑：`../` 伸到导入根外的引用**。`resolve()` 走 `os.path.normpath(os.path.join(base, src))`，只要磁盘上存在就能传 + 重写，但**图片目录的「删干净」只覆盖导入根以内的**——所以要把导入根外的图先 `cp` 到根外的镜像位置（本次做法：clean 结构做成 `<clean>/zh-cn/…` + `<clean>/pic/…`，导入根取 `<clean>/zh-cn`，收尾只删根内的 `zh-cn/pic`，根外 `pic/` 天然不进库）。
    **案例**：tinyclub/linux-doc（《Linux Documentation 中文版》GPL v2 翻译计划，最后一次 push 2021-01）——老板给的是 gitbooks 旧站 `tinylab.gitbooks.io/linux-doc/content/zh-cn/`（301 → `tinylab-1.gitbook.io`），站点内容 = 仓库 `zh-cn/` 子树 → 走**纯 GitBook 源全导口径**（保留 `book.json`/`SUMMARY.md`），5 目录 / 17 文件 = 22 节点；3 张图（2 张在 `zh-cn/pic/`、1 张在根 `pic/`）全传 CDN；`--toc-md` PUT 0.4s；四查 + 17 篇正文逐字符比对全绿（`book.json` +12 = 代码围栏）；库 id 84683048。⚠️ `SUMMARY.md` 里有断链（`timer/` 应为 `timers/`、`resource-contorl.md` 拼错），**按文件系统树导**不受影响，但正文链接保留原样。

## 七、官方 v2 一次性目录（toc-md，2026-10-16 老板拍板设为默认）

**来源**：官方 OAS `yuque_openapi_20260722.yaml`（v2.0.1，入口页 `yuque.com/yuque/developer/openapi`；页面 JS 渲染，需带 cookie 走 `GET /api/docs/openapi?book_id=75338` 挖正文 → 再拿附件）

**能力**：`PUT /api/v2/repos/{book_id}`（或 `/repos/{group_login}/{book_slug}`）body 的 **`toc` 字段 = Markdown 目录树**：
```markdown
- [目录名]()
  - [文档名](doc_slug)
- [根级文档](doc_slug)
```
`[名称]()` 空链接 = 分组（TITLE），`[名称](slug)` = 文档节点；顺序即目录顺序。

**两个关键事实（实测）**：
1. `POST /repos/{book}/docs` 建好文档后**会自动挂到 TOC 根** → 不用再逐篇 `appendNode`
2. 收尾**一次 PUT** 就把整棵树摆好（134 节点实测 **1.1s**；**2936 节点 / 139KB 目录树实测 15.1s**，一次成功，2026-10-16 elinux）

**验证结论（一次性库对照，同源同树）**：toc-md 与 batch 模式导入的 TOC **集合完全一致 + 顺序完全一致**；分片（`big.json (1/2)`）、特殊字符/中文标题、根级文件与嵌套目录均正确；`yuque_import_verify.py` PASS；幽灵 0；对账错位 0。

**中断续传**：文档层可断点续传（progress 记 slug/doc_id）；收尾 PUT 幂等，重跑同一命令安全。

**回退**：`--no-toc-md`（编排器）/ 不加 `--toc-md`/`--batch-mode`（直接用 tree_import）→ 旧流程。

## 六、wrapper 子命令速查
```
yuque_repo_import.py prep         --url <git-url> --dir <工作目录>
yuque_repo_import.py create-book  --name <项目名（commit）> --slug <项目名-commit> --desc <url @ commit> [--login <用户名>] [--stack-id 57018723]
yuque_repo_import.py move-stack   --book-id <id> --stack-id 57018723 [--wait 30] [--no-wait]  # v1.2.2: 重发+验证循环
```

token 来源同主脚本：环境变量 `TOKEN_L91` 或 `~/.openclaw/secrets/credentials.env`；cookie 默认读
`skills/yuque-ai-mcp/config/config.json`（可用 `--cookie-config` 覆盖）。

**rst 转换器已踩坑补充（2026-10-15 HgInit 实战，v1.3.12）**：
- BOM（`\ufeff`）卡首行指令/正则 → 转换前整体剥离（epigraph 原文泄漏真因）
- `.. image::` 全丢 → inline() 补 `<img>`→`![alt](src)`；图片文件夹（如 `_images/`）别进导入根目录，先 `upload_image` 传 CDN + 重写 md 引用，再只导 md（否则每张图变成独立占位文档）
- docutils html5 提示框是 `<aside class="admonition">` 不是 div；正则加捕获组后 `admon()` 的 group 号会移位
- blockquote 分支补 `> ` 前缀（epigraph 引语）
- 段落尾 `::` + 空行 + 列 0 指令 → 指令被吞进 literal 块，`::` 收成单冒号
- Sphinx `:doc:` 跨文档角色在语雀是死链 → 剥成纯文本
