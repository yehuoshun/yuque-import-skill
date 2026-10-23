# GitHub 开源项目 → 语雀导入 SOP（2026-10-12 老板固化）

> 触发模板：「把 `<repo>` 按开源项目流程到语雀」——repo 可给 https 或 `git@` SSH 链接。
> 实战记录：HowToCook / kairisei-ma-ch / STS2 全家桶 / legado / deepwrite×3 / owllook / Git-Cheat-Sheet 等 20+ 项目。
> ⚠️ 2026-10-14 老板拍板：**GitHub Actions 版批量导入已砍掉**（CI 易失败 + 难排错：360min job 上限硬掉、进程被杀后零中间日志、慢链路无法干预）。批量导入一律按本 SOP 在本地跑，账本跑完手动 commit。

## 一、规范（老板定，不要改）

| 项 | 值 |
|---|---|
| 知识库名 | `项目名（commit id）`，commit 取 8 位短哈希，如 `deepwrite（85577e7）` |
| slug | **老板 2026-10-13 定策略**：开源项目 = `项目名-commit`（天然防撞，同 repo 不同 commit 不同 slug）；网站/自定义 = `网站名-YYYYMMDD`（同日同站会撞 → create-book 已内置撞名兜底：422 时自动追加 `-2/-3` 序号重试）；slug 为 v2 API 必填字段（不传 422 missing_field，官方不会自动生成） |
| 描述 | **必须标注来源（2026-10-18 老板拍板，硬规则 11）**：`来源：<repo url> @ <commit> ｜ <口径说明> ｜ 导入 <日期>`。单源也要带「来源：」前缀；站点+仓库双源（如资源索引站）两个都写；双轨库注明。禁止空描述/只有库名 |
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
   - **并行导入（2026-10-21 老板拍板可行，见坑 48）**：一次拆成多个库（硬规则 9）或同一批导多个仓库时，**可以并行跑**——toc-md 全程只走 v2（100 QPS），低 QPS 的 Web API 只用在上传附件（且已提前做完）。实测两库并行合速 **~2.4 节点/秒**（单库 ~1.2），比串行省 ~25 分钟。
     - ⚠️ **前置条件：请求数 ≤ 5000/小时**（账号级，同账号所有 Token 共享）。估算：**一次导入的请求数 ≈ 文件数**（目录不耗请求、分片各算 1），多库/多仓同时跑要把总数加起来看（本次 A 3345 + B 1537 ≈ 4900，已卡边）；超了就串行或跨小时错峰。
     - 中止串行链改并行时：**先把链里「第二个库」的命令掐掉**（`kill -9` 包装 shell + python），否则前库跑完会再起一遍后库、两个进程写同一账本。前库靠账本断点续传，重启后自动 skip 已记账节点。
5. **心跳汇报**：25% / 50% / 75% / 完成，各报一次（读 progress 账本算百分比）
6. **对账**：`python3 scripts/yuque_toc_reconcile.py --root <clean_dir> --book <book_id> --progress <账本> [--fix]`
7. **验收六查**（缺一不可）：
   - TOC 节点数 == 本地节点数 —— **⚠️ 只对无分片库成立**；超限分片后节点数必然 > 本地文件数（标题 `x.json (1/14)`），改用 `scripts/yuque_import_verify.py` 做「本地文件树 ↔ TOC 全映射 + 分片号连续 + 全路径唯一」验收（2026-10-15 legado 固化）
   - 有分片时跑 `scripts/yuque_verify_shards.py`（分片**内容**逐字符比对，路径 PASS 不代表正文没丢）
   - 对账「错位 DOC: 0」
   - **幽灵文档 = 0**：`python3 scripts/yuque_check_ghosts.py --book <id>`（2026-10-21 升为必做，见坑 49）——不能只看 `meta.total` 数字，要对 doc_id 集合求差；toc-md 模式也会中（断点残留 / 重试双写）
   - 深层路径抽查（如 `apps/.../components/xxx.vue`、`package.json`）实际可达
   - **全库「占位文档」扫描 = 0 篇**（2026-10-21 升为必做，见坑 50）：逐页拉 `GET /repos/{id}/docs`，**每篇 `word_count` 必须 >0**（或 body 不以 `<!-- 二进制文件`/`<!-- 源仓库中该文件为空` 开头）；**别只抽查 3 篇**——同一次导入往往是少数几篇中招（本次 RUC 3/15 篇、fudan 2/12 篇），抽查必漏。

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
17. **限流（官方文档）**：每小时最多 5000 次、每秒最多 100 次，**同账号所有 Token 共享**；响应头带 `X-RateLimit-Limit/Remaining`。**batchMove 单次节点数服务端硬上限 = 500**（超过报 HTTP 400 `limit_exceeded: 单次最多只允许操作 500 个节点`，2026-10-16 rea 实战实测）；200 节点以内验证正常（无 100 上限）。逐节点干活很吃配额——toc-md 模式每文件只需 1 次请求，天然省配额。
    - ⚠️ **两个「5000」别混（2026-10-21 老板拍板）**：这里的 5000/小时是**账号级请求数（速率）**；硬规则 9 的 5000 是**单库节点数（容量）**。独立、同时生效。toc-md 下**估算请求数 ≈ 文件数**（目录不耗、分片各 1）——多库/多仓并行前先把总请求数加起来看会不会破 5000/小时（rea d0067ba 两库 3345+1537≈4900，已卡边，见坑 48）
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
31. **GitHub Pages（gh-pages 分支）书站：源就是 md，别爬 HTML；front matter 必剥（2026-10-17 happypeter/LGCB《Linux Guide for Complete Beginners》实战）**：站点 `happypeter.github.io/LGCB/book/` 是 **Jekyll 渲染产物**，但 `gh-pages` 分支里躺着 md 源（`book/*.md` + `book/images/` + `_layouts/` + `_config.yml`）——**直接 clone gh-pages 导 md**，比爬生成的 HTML 干净得多（HTML 里还夹着站点模板的 header/menu/footer）。三个要点：
   ① **Jekyll front matter 必须剥**：每篇 md 开头是 `---\nlayout: book\ntitle: 你好，命令行\n---`——不剥就变成正文头部的 YAML 垃圾。剥法：`re.match(r'^---\s*\n(.*?)\n---\s*\n', t, re.S)`；**剥出来的 `title` 别丢**（中文标题！文件名是 `02_hello_cli.md` 这种英文 slug）——用来生成「目录」文档。
   ② **`book/index.html` 是站点的目录页**（同样是 Jekyll 页）——不要原样当 HTML 文档导（站内 `.html` 链接到语雀会成死链），而是解析它的 `<tr class="episode-wrap">` 表（序号/标题/时长）**重新生成一篇 `目录.md`**（markdown 表格：序号 | 章节 | 时长 | 文件名），顺带写上站点与源仓库地址。
   ③ 文档标题仍按硬规则 7 用**文件名**（`02_hello_cli.md`），中文标题靠目录页对照。本次：13 章 + 目录.md = **14 节点**（0 目录，平铺）；33 张被引用的图全传 CDN（未引用的 5 张不传）、删 `book/images/`；`--toc-md` PUT 0.4s；四查 + 14 篇逐字符比对全绿；库 id 84683210。
    **续例（2026-10-18 billie66/TLCL《快乐的 Linux 命令行》）**：同构站（gh-pages + Jekyll + `book/chapNN.md` 37 章），但**章多时按站点目录页的分部建目录**（`book/index.html` 的 `<h2>` 分组 = 5 部：引言/学习 shell/配置文件和 shell 环境/常见任务和基本工具/编写 Shell 脚本）→ `00-引言/01-引言.md` … 5 目录 + 37 章 + 根级 `目录.md` = 43 节点。三个补充：
   ① **文件名要洗 `/`**（“流程控制：while/until 循环”直接当文件名会 ENOENT）
   ② **图片引用按 md 所在目录解析**——章节进了子目录后，原 `images/x.png` 要改成 `../images/x.png` 才能被 rewrite 脚本找到
   ③ **中英对照书保留原文**（TLCL 每段英文 + 中文），不删英文；站点首页（`index.html`，比 md 源里的 HTML 混排规范）用 bs4 转 md 当根级「目录.md」（含分部目录表）
34. **GitBook 源仓库的「章节首页 + 章节目录」双结构 + md 图片 title 语法**（2026-10-18 chyyuu/ucore_os_docs 实踩）：
    - 这类仓库常是 `labN.md`（章节首页，位于**根**）+ `labN/`（该章各节）/ `labN_figs/`（图）三件套。直接全导的话，语雀 TOC 会把 `labN/` 目录排在前、`labN.md` 落到根级文件区（全部排到 9 个目录**之后**），与书的内容顺序相反。做法：**把 `labN.md` 拷进 `labN/` 同名保留**（`lab0/lab0.md`）—— `.` 的字符序小于 `_`，目录内自然排第一 ✅（本次 9 个 lab、202 节点）
    - **md 图片可带 title**：`![alt](../lab0_figs/image001.png "ucore系统结构图")` —— 旧版 `yuque_rewrite_images.py` 会把 `path "title"` 整体当 src → 报本地缺失、图全不传。已修：`sub_md` 先 `split(None, 1)` 拆 path/title，只重写 path（v1.3.62）
    - 老板给的 gitbook.com 旧链可能已死（302 → legacy → gitbook 首页）→ 去 GitHub 搜书名/仓库名找官方源（本次 `objectkuan/ucore-docs` 404 / `objectkuan/ucore_docs` 已重定向 → 官方是 `chyyuu/ucore_os_docs`）
    - 单行 md（如只一行标题的 `lab0.md`）入语雀后行尾 `\n` 会变 `\r`，逐字符比对会报差异（实际无影响，别当事故）

**坑 36（GBK/非 UTF-8 源码误判二进制 → 整篇正文变占位，2026-10-18 linyiqun/DataMiningAlgorithm 实战）**：老的 Java 教程仓库（201X 年）源码常是 **GBK 编码**（中文注释），脚本二进制检测「UTF-8 解码失败 → binary」会把它们全判成二进制 → 110 篇正文写成 `<!-- 二进制文件 0 MB, 跳过内容导入 -->` 占位，**结构验收四查全绿也拦不住**（路径映射只看节点在不在，不看正文）。当场表现：`AprioriTool.java` body 是占位、word_count=0、git 里文件却是正常文本；`iconv -f GBK` 在部分沙箱直接报 `conversion from GBK is not supported`（iconv 缺 GBK 表），别用 iconv 验证，用 Python `raw.decode('gbk')`。修法：① 写回填脚本，`raw.decode('gbk')` 后按 `fmt_content` 同等格式（` ```java` 围栏）`PUT /repos/{book}/docs/{doc_id}` 更新正文 + word_count>0 校验 + 回读（复用 `yuque_repair_placeholders.py` 的 update_doc 模式，但它的 `errors="replace"` 会把 GBK 变乱码，得自己 decode('gbk')）；② 回填后全量扫一遍 `二进制文件|跳过内容导入` 残留必须为 0；③ 教训：**碰到老仓库（Java/C#/中文注释）先全量测一遍编码**（`find . -type f` 逐个 try UTF-8 decode），中招的多是编码非 UTF-8 的源码文件而不是 md/txt。

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

**toc-md 的两个反复踩点（2026-10-18 datamining-guide 复现）**：① 根级 DOC（如 `00-前言.md`）收尾后**排在所有 TITLE 目录之后** → 补一发 `prependNode/action_mode=sibling, node_uuid=<根级DOC>, target_uuid=<第一个TITLE>` 归位；② `yuque_rewrite_images.py --dry` 曾恒报 `重写 0 处 / 缺失 0`（dry 短路了 mp 填值）→ v1.3.65 已修，现在 dry 会如实报处数，**跑 433 张图前先用 dry 核数**。

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

**rst 转换器已踩坑补充（2026-10-15 HgInit 实战，v1.3.12；2026-10-17 linuxtools_rst 补）**：
- BOM（`\ufeff`）卡首行指令/正则 → 转换前整体剥离（epigraph 原文泄漏真因）
- `.. image::` 全丢 → inline() 补 `<img>`→`![alt](src)`；图片文件夹（如 `_images/`）别进导入根目录，先 `upload_image` 传 CDN + 重写 md 引用，再只导 md（否则每张图变成独立占位文档）
- docutils html5 提示框是 `<aside class="admonition">` 不是 div；正则加捕获组后 `admon()` 的 group 号会移位
- blockquote 分支补 `> ` 前缀（epigraph 引语）
- 段落尾 `::` + 空行 + 列 0 指令 → 指令被吞进 literal 块，`::` 收成单冒号
- **Sphinx 交叉引用角色 → 剥成纯文本**（不只是 `:doc:`，`:ref:`/`:term:`/`:func:` 等同族）。2026-10-17 linuxtools_rst 实测：docutils 不认这些角色 → `参见 :ref:`ldd`` **原样留在正文**（12 处垃圾）。修法：转换前 `ROLE_RE.sub(_strip_role, src)`，`:ref:`显示文本 <目标>`` → `显示文本`、`:ref:`目标`` → `目标`
- **`.. image:: /_static/x.png` 是站点绝对路径**：转出来就是 `![]](/_static/x.png)`，`os.path.join` 遇绝对路径会**直接跳出导入根** → rewrite 报 missing。先在 md 里把 `(/` 前缀改成按层级算的相对路径（根下 `_static/`、子目录 `../_static/`），再跑 `yuque_rewrite_images.py`
- **`.. literalinclude::` 必须转换前展开成 `.. code:: <lang>`**（docutils 不认 Sphinx 扩展指令，会**静默丢掉整段代码**）；**`doctitle_xform=False`** 否则首节提升为标题、子节全压成 h1（大纲扁平）；**块间要空行**（同类 li/表格/引用用单 `\n`）；`.. contents::` 剥掉；`pre` 围栏带语言 —— 见坑 55（2026-10-22 design_patterns）

**坑 35（GitBook 3.x 源仓库的书，2026-10-18 yourtion/DataminingGuideBook 实战）**：老板给的是**站点**链接（`dataminingguide.books.yourtion.com`，页面 meta `generator=GitBook 3.2.2` + `author=Yourtion`），但**同名源仓库就是书稿源** → 先 `api.github.com/search/repositories?q=<书名>` 找到 `yourtion/DataminingGuideBook`，**吃 md 不抓 HTML**（口径随源走：库名带 commit、分组「开源项目」，同 TLCL/uCore）。两个特征要认清：
- 这类 GitBook 3.x 源**没有目录层级**——正文是 `chapter-N/chapter-N-M.md` 扁平编号，层级与标题**只存在 SUMMARY.md 的缩进里** → 必须解析 SUMMARY.md 重建树，靠文件名推不出来
- 重建时的排序技巧：章首页 `NN-章名.md` + 子节 `NN.M-标题.md`，**`-`(0x2D) < `.`(0x2E) 让章首页天然排第一**（toc-md 模式下顺序其实来自目录树，命名只为磁盘/人眼一致）
- 把章首页也塞进 `NN-章名/` 而不是平铺到根：**原仓库 depth=1、新树也 depth=1 → `../img/...` 引用天然仍有效，零路径改写**
- 图：441 处引用 / 433 张图（8 处重复引用同一张），`img_map.json` 以相对路径为 key → 同图只传一次
- 完整可复用脚本 + README：`examples/datamining-guide/`

**坑 36（老 GitBook「独立域名」型书仓，2026-10-18 looly/elasticsearch-definitive-guide-cn 实战）**：老板给的 `https://legacy.gitbook.com/book/fuxiaopang/learnelasticsearch/details` 已死——`legacy.gitbook.com` **301 → `www.gitbook.com/?utm_source=legacy`（首页）**，而老式 `fuxiaopang.gitbooks.io/learnelasticsearch` **302 → `https://www.learnes.net/`**（该域名已被某公司抢注成空壳页，gb2312 + 无正文）→ 站点内容不可恢复，只能找源仓库（本次 `looly/elasticsearch-definitive-guide-cn`，2045★，同书名）。**三条可复用手法**：
- **图是绝对外链时的 CDN 化**：本仓库图有两套写法——`https://raw.githubusercontent.com/<org>/<repo>/master/images/x.png`（沙箱/部分网络拉不动，**默认 rewrite 脚本只认相对路径，一条都不匹配**）+ `https://www.elastic.co/.../images/x.png`（实测 200 外链，保留）。做法：写个 20 行的旁路脚本，**按 URL basename 反查 `images/` 里的本地文件** → `upload_image` 传 CDN → 正则替换回 md；`img_map.json` 照旧做断点续传。16 张图（raw 13 + 相对 2 + 封面 1）→ 16 处引用全重写，CDN 抽 5/5 实拉 200；elastic.co 的 11 张外链零改动
- **SUMMARY 大小写与磁盘不符 + 断链**：`500_Cluster_Admin` 目录里全是小写（`10_intro.md`/`15_marvel.md`），SUMMARY 却写 `00_Intro.md`/`15_Marvel.md` → 直接按路径查全 404。**路径解析必须大小写不敏感**（先建「小写相对路径 → 真实路径」索引）。另有 10 处真断链（5 章首页 `00_Intro.md` 不存在 + 4 个文件不存在）→ 章首页缺失时按序兜底：① 该章 SUMMARY 子节里第一个 intro 类（intro/overview/readme）文件**提升为章首页**；② 章节目录里未被引用的 intro 类文件提升；③ 都没有就当纯 TITLE（本次 5 例全部兜底成功）
- **SUMMARY 顺序 ≠ 文件名编号顺序**：源文件编号非单调（`300_Aggregations` 是 05,100,105,10,110,… 乱序），SUMMARY 才是阅读序 → **编号一律按 SUMMARY 顺序重排**（章 `NN-`、子节 `NN.MM-`），别信文件名

**坑 37（验收脚本自己打爆 API 限额，2026-10-18 ESDG 实战）**：写验收脚本要把两个「看着对、其实错」的坑先钉死：
- `GET /repos/{book}/docs` 的 **`page` 参数无效**（恒返首页 100 条）→ 拿 page 循环「直到 len<100」**永远不退出**，900 秒把语雀**账号级 5000 次/小时**限额打爆（后续全是 `429 Too Many Requests`）。分页必须用 **`offset`**
- **TOC 节点里 `id` 和 `doc_id` 都是空串**（DOC/TITLE 都一样）→ 想按 TOC 回读正文拿不到 doc_id。正文回读一律**取导入账本 `progress.json` 的 `doc_id`**（账本才是权威）
- 教训：验收器上线前先拿 2 篇小样本跑一遍（能变红也能变绿）再全量跑；无限循环 + 无口径校验会同时烧掉时间和配额（本次 315 篇正文回读作废重跑）

**坑 38（站点域名直接死掉 + SUMMARY 四~五层嵌套 + 旧版整编孤儿，2026-10-18 chenryn/ELKstack-guide-cn 实战）**：老板给的列表链接 `http://kibana.logstash.es`（书《ELKstack 中文指南》）**域名已废，DNS 都不解析**；`archive.org` 快照沙箱超时（老毛病）→ 只能找源仓库。判据很干脆：**GitHub 仓库的 `homepage` 字段就写着这个死域名**（`chenryn/ELKstack-guide-cn` @ a30092e，764★）→ 确证「站点 = 本仓库」，吃 md 源、库名带 commit、分组「开源项目」。

这个仓库的形状比普通 GitBook 源复杂，四个特征都要认：
- **SUMMARY.md 四~五层嵌套**，中文标题 + 英文扁平磁盘路径（`logstash/plugins/filter/grok.md`）→ 通用递归建树，不要写死两层
- **空链接纯分组节点**：`* [插件配置]()` / `[接口使用示例]()` / `[性能优化]()` / `[output配置]()`（4 个）→ **落成 TITLE 目录、无文档**（别当断链丢掉）
- **目录首页断链**：SUMMARY 引用了 `elasticsearch/auth/README.md`、`elasticsearch/hadoop/README.md`、`elasticsearch/monitor/api/README.md`、`logstash/performance/monitor/README.md`，**文件根本不存在**（4 个）→ 同样落 TITLE 目录、无落地页
- **孤儿 35 篇**（未被 SUMMARY 引用）：`kibana/v3/**` 旧版 Kibana 3 整编 + `kibana/v5/README.md` + `kibana/difference.md` + `elasticsearch/auth/searchguard.md` + `elasticsearch/monitor/marvel.md`。本书前言明说「K3/K4 并存，本书分别讲解」，而 master 的 SUMMARY 已把 v3 摘掉（仓库自述「master 统一调整为 5.0 状态，老版本在 ELK release tag」）→ **按「内容不丢」口径全纳入**：v3 建顶级组「Kibana 3（旧版）」（镜像源目录、子目录名中文化、文档标题取首个 `# ` H1、无 H1 回退文件名），`kibana/v5/README.md` 塞进 Kibana 5 组内 `04.00-…`，`difference.md` 落根级，searchguard/marvel 追加进对应分组（编号 = 组内已有最大号 +1，**别用 `len(os.listdir)` 计数——落地页会把编号顶掉一位**）

**命名方案（多层通用，排序靠分隔符）**：节点号 = 点分路径 `01` / `01.01` / `01.01.01`；有子节点 → 目录 `NN-标题/` + 目录内落地页 `NN-标题.md`；叶子 → `NN-标题.md`。`'-'(0x2D) < '.'(0x2E) < '0'(0x30) < 字母 < CJK` → 落地页 `04-Kibana 5.md` 天然排在 `04.00-…`/`04.01-…` 前。**别用 `_`(0x5F) 或空格当分隔符**（会把落地页顶到字母标题之后）。

**外链图：能救的救，救不了的别耗**——105 处外链里约 45 处已死：`www.elasticsearch.org/*`（302 → elastic.co 首页，返回 HTML 不是图）、`www.elastic.co/guide/en/kibana/current/images/*`（Kibana 文档改版后 404）、`logstash.es`、`timroes.de`、`marvel` 等。口径：① **必救 = GitHub raw 族**（`raw.githubusercontent.com` / `github.com/*/raw/*`，CN 不可达必裂图）→ 在 build 脚本里**预下载**（走 `gh-proxy.com`）落进 `_imgs/`，交标准 rewrite 脚本一起传 CDN；② 死域名/改版 404 的**原样保留**（源仓库自己就烂，逐个查 Wayback 性价比极低）。本地图统一收进 `_imgs/<源相对路径洗 __>` 并把 md 引用改成到该处的相对路径 → 标准 `yuque_rewrite_images.py` 一把过（93 处重写 / 92 张图 / 0 缺失），传完删 `_imgs`。

实测：196 篇建文档 ~2.5 分钟 0 失败；toc-md 230 行目录树 **PUT 1.6s**、结构核对 PASS；四查全绿（全路径唯一、TOC==本地、幽灵 0、196 篇逐字符回读不等 0 空 0、reconcile 0）；根级 `00-前言.md` 被 toc-md 排到 5 个 TITLE 之后 → `prependNode + sibling` 一发归位。可复用脚本 + README：`examples/elkstack-guide/`。

**坑 39（站点域名死透但仓库不自证 + 反查源仓库 + 残缺译本甄别，2026-10-18 xtmhm2000/mastering-elasticsearch 实战）**：老板给的 `http://udn.yyuap.com/doc/mastering-elasticsearch/`（《Mastering Elasticsearch 中文版》）**DNS 不解析**（http/https 都瞬断 000），archive.org 快照沙箱超时 → 又是「找源仓库」场景。与坑 38 的差别：**仓库 `homepage` 字段没写这个死域名**（判据失效）→ 改走**关键词检索反查**：

- **检索手法**：`gh search repos "mastering elasticsearch"` / `"<书名> 翻译"` / `"<书名> 中文"`，配 `--json fullName,stargazersCount,description,updatedAt --jq` 精筛；仓库 description 写着「xx翻译」+ 树里有 `SUMMARY.md`/`chapter-*`/`imgs/` → 基本就是 GitBook 源。本次一条命中 `xtmhm2000/mastering-elasticsearch`（desc "mastering elasticsearch翻译"，2014-12，★0）
- ⚠️ **别用 `gh api search/repositories?q=<中文+空格>` 手拼 query**：中文/空格没编码时返回一堆无关仓库（本次第一次搜全是无关项目，白折腾一轮）→ 一律用 `gh search repos`（CLI 自己编码）
- **残缺译本甄别（动手前必做，别闷头导完）**：老译本仓库常烂尾 → 先 `wc -c chapter-*/README.md`（或全树 md 扫 0 字节）量一遍，识别「只有一行标题」的空壳章。本次 **第 3/6/7/8/9 章正文全空**（31~38 字节 = 就一行 `# 第N章 xxx`），另有 **16 个子节文件 0 字节**。处置口径：**SUMMARY 收录的空壳章照建节点**（保结构完整）；**未被 SUMMARY 收录且 0 字节的孤儿文件跳过**（不造垃圾节点）；导完**主动向老板报残缺度**（本次报「正文只有 1/2/4/5 章，其余只有标题」+ 问要不要找更全译本），不能只说四查全绿
- **章标题自带「第N章」→ 目录名剥前缀**：SUMMARY 标题常写成 `第1章 认识Elasticsearch`，而目录名已由 `NN-` 编码序号 → 不剥就落成 `01-第1章 xxx` 重复编号。做法：`re.match(r'^第(\d+)章\s*', title)` 命中就剥（本次 9 章全剥），得 `01-认识Elasticsearch`，落地页同号排子节点前
- **排版垫片图剥离**：源里 `<img src="../notes/pixel.gif" style="height:100%; width:1px;">` / `lm.png` / `rm.png`（1px/13px 尺寸 + 包在 `position:absolute` 布局 div 里）是排版脚手架，**不是内容** → build 时正则整体剥掉（本次 96 处 / 32 篇），不传 CDN（否则每篇挂 4 张 1px 图，白烧配额）；`note.png` 这类小图标保留。正则：`<img\s+src="(?:\.\./)?notes/(?:pixel\.gif|lm\.png|rm\.png)"[^>]*/>\s*`
- **相对图引用缺层 → 回退补层**：源仓库笔误 `../44_cluster.png`（实际在 `imgs/`）→ 收集图时**先试原路径，不存在再试「同名前插一层 `imgs/`」**（本次 1 处，不修就裂图）
- **源仓库自带原版 PDF/电子书 → 走双轨**：本次仓库根躺着 `Mastering ElasticSearch [eBook].pdf`（英文原版 3.4MB）→ 同 `type=attachment` 上传（端点见 `pdf-book-to-yuque.md`），链接写进 `00-前言.md` 正文末尾：「**原版英文 PDF 附件**：[点击下载](url)」

实测：47 节点（6 目录 / 41 文档）、18 图 CDN（49 处引用、0 缺失）、toc-md **PUT 0.6s**、四查全绿（41 篇逐字符回读 0 差 / 幽灵 0 / reconcile 0）；根级 TITLE/DOC 混排顺手二次归位（见 `api-notes.md` 根级排序条）。可复用脚本 + README：`examples/mastering-es-guide/`。

**案例（Sphinx/readthedocs 书仓，2026-10-17 me115/linuxtools_rst 实战）**：需 Sphinx 源仓库（`conf.py`/`index.rst`/`Makefile`）导站时，**只导 toctree 覆盖的页面 + 图片**；仓库根常同时躺着脚手架（`_build/`、`der/`、`sphinx_rtd_theme/`、`*.zip`、`*.epub`）和**早期版本的重复单文件**（本次 `top.rst`/`020-file-manage.rst`/`crontab.rst` 与 `tool/top.rst`/`base/02_file_manage.rst`/`tool/crontab.rst` 撞车，`base/ref.rst`/`base/README.rst`/`base/crond introduce.rst` 不在任何 toctree）——按 toctree 展开收集，别整树导。本次：`index.rst` + `base/`(index+9) + `advance/`(index+3) + `tool/`(index+19) = **35 篇 → 38 节点**（3 目录）；6 张图传 CDN（`_static/` 里其余 4 张封面/psd 未被引用不传）；无需爬 HTML（站点就是这些 rst 渲染的）。

**续例（同作者 me115/design_patterns《图说设计模式》，2026-10-22，坑 55）**：同族 Sphinx/reST 书稿，但正文靠 `.. literalinclude::` 内联各模式示例源码 → **转换器必须先展开 literalinclude**（否则「代码分析」节全空），另修 `doctitle_xform`（保层级）+ 块间空行 + `pre` 带语言围栏。脚手架全剔、**`code/` 不入库**（源码已内联 + 里含 `.o/.exe`）；上游 `_static` 图名大小写写错（`State1.png` vs 磁盘 `state1.png`，站点 404）→ 大小写不敏感解析。clean 25 节点（3 目录/22 文档）；脚本 `examples/design-patterns/`。

**坑 40（AsciiDoc 书稿源 + 老 gitbooks.io 站当逐页 oracle，2026-10-18 sinosmond/puppet-27-cookbook-CN 实战）**：老板给的还是 gitbook.com 旧链（302 → gitbook 首页，死），但**书内 Footer/正文自述「源码位于 <repo>」** → 判据升级：老 gitbooks.io 书页（`https://<user>.gitbooks.io/<slug>/content/`）**还活着**时，先看书里有没有自述源仓库；本次 `sinosmond/puppet-27-cookbook-CN`（AsciiDoc 书稿）比抓 HTML 强得多（`[source,puppet]` 语言标签 / 块标题 / 出处引用都在）。

- **AsciiDoc 源识别**：全树 `.txt` 无 `.md`，且有 `book.txt`（标题下划线 + `:Author:` 属性 + `include::` 清单）+ `entries.txt`（`:Recipe101: xxx` 属性字典）+ `asciidoc.conf`；层级只在 `include::` 里
- **必须自写转换器**（`examples/puppet-cookbook/adoc-build.py`，规则表见该目录 README）：节标题降级、`[source,x]+----`→围栏（带语言）、`....`/`..................` 字面块、`[NOTE]/[TIP]/[IMPORTANT]+====`→引用块、`[quote,说话人,出处]`→引文+出处、`****` 侧栏、`--` 开放块、`.块标题`、`[[锚点]]`/`<<锚点,文字>>`、`+x+`→行内码、列表续项 `+`
- **⭐ 关键口径：只替换 entries.txt 里定义过的属性**。Puppet 代码里满屏 `{name}`/`{md5}`/`{hostname}`（未定义属性），asciidoc 渲染也是原样输出 → 转换器若无脑替换会毁代码块
- **状态机必须认闭合类型**：`....` 块只能用 `^\.{4,}$` 收、`----` 块只能用 `^-{4,}$` 收（shell 输出里满是 `-----` 分隔线）；闭合行**要自己输出**围栏（漏了就整篇少一半围栏，收尾自查 `grep -c '^\s*```'` 为偶数）
- **`[master]`/`[myapp]`/`[mysqld]` 不是块属性**：只认白名单（`[source,x]`/admonition/`[quote,`），代码块状态内一律不解析
- **书稿 `.txt` 常带 UTF-8 BOM** → `\ufeff[[anchor]]` 破锚点正则；读源码用 `encoding="utf-8-sig"`（写 md 仍用 `utf-8`）
- **⭐ 老 gitbooks.io 站可以当逐页正文 oracle**：站点页（`index.html` + `1..N.html`）与本地书稿 1:1，按**标题**配对、归一化后算相似度 → 首次就抓出 2 个转换器 bug（围栏/续项缩进）与「站点是旧版书稿」的事实。**判据要分三档**：≥0.99 = 通过；低于阈值但**站点文本是本地子串**（只有 insert 无 delete/replace）= **站点滞后**（源仓库 HEAD 比渲染站新，可接受，本次 3 页）；有 delete/replace = 真差异 → FAIL。抓站点**必须限速**（并发 8 会有 ~13/122 页返回 GitBook「Page Not Found」假 404，串行重抓即正常；抓完 `grep -l "Page Not Found" *.html` 自查）
- **前置篇目的落地方式**：`book.txt` 里的封面（标题/作者/版本/`[IMPORTANT]` 版权声明）落 `00-书名页.md`；`00-translator_preamble/01-colophon/02-author/03-preface` 分别落 `02-译者序/`、`03-原书版权页.md`、`04-关于作者.md`、`05-前言/`，章首页 + 子节按 `NN` / `NN.MM` 编号 → 与站点序号天然对齐
- **toc-md 后根级 DOC 又落到 TITLE 之后**（老坑 29）：本次 4 个根级 DOC（00/01/03/04）分散在 TITLE 之后，**一次 prependNode 只挪一个节点** → 写循环（每轮回读 TOC、按期望序找「紧随其后且存在的目标」prepend），3 轮收敛（`examples/puppet-cookbook/fix_root_order.py`，可复用）
- 版权提醒：本书是 **Packt 封闭版权**译本（译者自述禁止公网发布 HTML/PDF）→ 只进私有库，`00-书名页.md` 保留版权声明原文，**不要**同步到任何公开渠道

实测：134 节点（11 目录 / 123 文档）、12 图 CDN（0 缺失）、toc-md **PUT 1.0s**、四查全绿 + 120 页 ≥0.99（3 页站点滞后）+ 123 篇逐篇回读 0 差。可复用脚本 + README：`examples/puppet-cookbook/`。

**坑 41（单篇长文型仓库：按 `## N.` 拆篇 + 跨文档锚点必失效，2026-10-18 justinyhuang/Functional-Programming-For-The-Rest-of-Us-Cn 实战）**：仓库可能**不是多章书，而是一篇文章**（博客文章/文章译本）——本例只有 `FunctionalProgrammingForTheRestOfUs.cn.md`（59.9KB，13 个 `## N.标题`）+ `.en.md` 英文原文 + `README.md`（译者说明）。口径（2026-10-18 老板拍板）：
1. **按 `## N.` 拆篇**（不整篇塞一篇文档）→ 目录 = 书名，内含 `00-译者说明.md`（README 去掉自带的 setext H1）+ `01-开篇.md` … `13-欢迎联系.md`（两位序号；**文件名要剥「N.」前缀，还要剥标题里的 `<sup>` 与 markdown 链接**——`## 8.[惰性求值](http://…)` 直接当文件名会 ENOENT）
2. **H1 丢弃**（= 库名/目录名）；H1 紧跟的**日期行别丢**，留在 `01-开篇.md` 首行
3. **英文原文不收**（列表条目是中文译本）；源仓库常无 LICENSE（原文是 defmacro.org 博客），库本来 private 无所谓
4. **拆篇的固有代价：原文跨文档的内部锚点必失效**——本例 `[1](#f1)` … `[8](#f8)` 的脚注定义全在第 13 章，拆开后点不动（语雀不跨文档同步锚点）。口径：**原样保留、不做手术**（拆篇换来的是可读性）

本例实测：15 节点（1 目录 / 14 文档），toc-md **PUT 0.6s**、四查全绿 + 14 篇逐篇回读 0 差；字节差 101B = 丢掉的 H1 行 + README 标题行（拆篇零丢失的快速判据）。⚠️ 提示：`--toc-md` **不要配 `--test N` 试水**（坑 26），直接全量跑。

**坑 42（MkDocs 教程站：相对路径按「站点 URL 深度」写 + 视频/数据包走附件，2026-10-18 LearnOpenGL CN 实战）**：站点 `learnopengl-cn.github.io` 是 MkDocs 渲染产物，源仓库 `LearnOpenGL-CN/LearnOpenGL-CN`（默认分支是 **`new-theme`** 不是 main！）`homepage` 自证 → 走源仓库口径。
    - **导入根 = `docs/`**，且要剔主题脚手架 `css/` `mathjax/`（只在 mkdocs.yml 里被引用，正文不引用）；`docs/img/README.md`（图片目录版权说明）随 img 目录一起剔。
    - **⭐ 相对路径不是按文件位置写的，是按渲染后站点 URL 深度写的**：`docs/01 Getting started/05 Shaders.md` 里写 `../img/01/05/x.png`（站点 URL `/01 Getting started/05 Shaders/` → 上一级才对），嵌套目录里更夸张写成 `../../../img/08/01/x.jpg` → **通用 `yuque_rewrite_images.py` 直接报 26 处「本地缺失」**（会把图全留成相对路径 = 裂图）。对策：自写带**路径归一化**的重写脚本——① 先按 md 所在目录解析；② 失败则**逐级剥 `../`** 再按导入根解析；③ 仍失败则**按后缀唯一匹配**（`img/08/01/x.jpg`）。实战脚本：`tmp/lo-rewrite.py`（本次实现，可复用）。
    - **非图片资源（mp4 / zip / rar）**：`<video src="...mp4" controls>` 这种 HTML 视频标签要单独一条正则（`(<video\b[^>]*?\bsrc=)(["'])([^"']+)(["'])`）；⚠️ **2026-10-21 起不再上传附件（硬规则 12：附件只给 PDF）**——旧做法是 `type=attachment`（`upload_attach()`）→ `https://www.yuque.com/attachments/...`；新做法：**保留原相对路径/上游外链、不重写、不删**，并在文档里注明「未上传」。zip/rar 这类正文里 `[这里](../data/x.zip)` 的下载链接同理。
    - **量级与限流**：本次 358 处图引用 + 20 处文件引用 = 369 个资源，`--throttle 5`（~12-15 个/分）全程 **0 失败**、约 27 分钟（贴着 ~500 张/窗口的 429 红线，别把 throttle 调更小）。
    - 收尾：82 节点（15 目录 / 67 文档）toc-md **PUT 1.1s**；**4 个根级 DOC（index/intro/legacy/code_repo）被排到 8 个 TITLE 目录之后** → 复用 `examples/puppet-cookbook/fix_root_order.py`（改写 EXPECT 为期望根级序）**4 轮收敛**；四查全绿 + 67 篇逐篇回读 0 差、word_count 无 0。
    - 版权：正文本站译文 CC BY-NC 4.0，**图片/素材 © Joey de Vries 保留所有权利** → 只进私有库、不同步公开渠道。

**坑 43（章节目录名无语义 + 逐章自带同名图：先 CDN 重写再重建树，标题只信 SUMMARY，2026-10-18 zilongshanren/opengl-tutorials 实战）**：源仓库是 GitBook 源（`README.md` + `SUMMARY.md` + 18 个 `tutNN/zh.md` + `tutNN/res/`）——**目录名 `tutNN` 无语义，可读标题只存在 `SUMMARY.md`**，镜像仓库树会得到 18 个叫 `tutNN` 的目录。
    - **方案 B（2026-10-18 老板拍板）**：`README.md` → `00-前言.md`；SUMMARY 第 i 分部 → `0i-<分部名>/`；文档名 `NN-<SUMMARY 标题剥「第N课[:：]」>.md`（NN = 课号，全局连续）；`SUMMARY.md` 不入库（就是目录本身）→ 21 节点（2 目录 / 19 文档）。
    - **⭐ 顺序铁律：先在原布局跑 `yuque_rewrite_images.py`，再重建树**（`./res/x.png` 在原始布局按 md 目录天然解析，重建后相对路径就没了锚点）。反序会踩**同名图串台**：本仓库 `icon_smile.gif` **同时存在于 `tut08/res/` 与 `tut13/res/`**（两张不同的图、同名），两章归到同一分部后共享 `res/` 会互相覆盖。`examples/opengl-tutorials/build_tree.py` 只 copy md、**不 copy 任何图片**，并内置两条断言（目标树无非 md 文件 / 无残留非 http 图片引用）。
    - **标题以 SUMMARY 为准，别信磁盘 heading**：本例 `tut08/zh.md` heading 写「基础光照模型」（SUMMARY：「基本着色」）、`tut18/zh.md` heading 错字「Billbard」（SUMMARY：「Billboard和粒子」）→ 按 heading 命名会把笔误写进库。
    - 全角「：」留在标题里不用洗；本章标题无 `/`；md 全 UTF-8、无分片。
    - **toc-md 后根级 DOC `00-前言.md` 又被排到 TITLE 之后**（老坑 29）→ 一发 `prependNode/action_mode=sibling`（node_uuid=前言, target_uuid=首个 TITLE）归位。
    - 实测：114 张图 1.5s 节流全传 CDN（~3 分钟、0 失败、114 引用 ↔ 114 图 1:1）；toc-md **PUT 0.5s**；四查全绿 + 19 篇逐篇回读 0 差 0 空。可复用脚本 + README：`examples/opengl-tutorials/`。

**坑 44（资源索引型仓库：仓库不装正文而装清单 → 解析单轨 + 分类索引，2026-10-18 aoaostar/legado @ fd0ec7f9 实战）**：`aoaostar/legado` 是「阅读」APP 的资源索引站（默认分支 **`release`** 不是 main；CI 每天重写 `README.md`/`index.html`），仓库里只有 README（分类目录）+ index.html + `sources/*.json`（21 条引用 / 20 个文件 / 48.8MB，最大 `b778fe6b.json` 20MB / 3907 条书源）。老板口径：B = 索引 + 附件**双轨**。
    ⚠️ **口径已变更（2026-10-21 老板拍板，硬规则 12）**：**附件只给 PDF**——原「原件附件轨」（`sources/*.json` 上传 `type=attachment` 建 `01-原版附件.md`）**停用**。新做法：只留解析轨 + 分类索引，索引里的「原件」列给**上游直链**（`legado.aoaostar.com/sources/<file>`，仓库 README 本来就有）；历史 3 版（`fd0ec7f9`/`0dde287`/`8b13d08`）已按旧双轨入库，**不动**。下文双轨描述保留作历史记录。
    - **别把 20MB JSON 原样当文档导**（会走 512KB 切分 → 几十个分片，既丑又把「原件」当正文）。
    - **解析轨**：每个 JSON 逐条转表 → `08-解析/sources/<名>.json.md`（书源/TTS 列 名称+网址+分组+启用；净化规则列正则；主题单对象列字段值；zip 解包内 `readConfig.json` 列字段）→ **体积暴降**（20MB 原件 → 303KB 文档），全部 <512KB **零分片**。
    - **原版轨**：`type=attachment` 上传全部原件（`upload_attach`，MIME 按扩展名，大文件 timeout 拉到 300s + 5s 节流）→ 根级 `01-原版附件.md` 表格列 分类/名称/条数/📎原件/直链/`legado://` 一键导入。实测 20 文件（含 10.8MB / 6.9MB×2 / 20MB）全传成功，带 cookie `curl -L` 复拉 **md5 全对**。
    - **分类索引**：README 的 `<h2 id="id_N">` → `02-书源.md` … `07-在线朗读引擎.md`（名称/条数/来源网站/上游更新时间/直链/一键导入/原件）；`00-前言.md` 写来源（站点+仓库+commit+上游同步时间）、库结构、怎么用。
    - **不入库**：`CNAME` / `sources/cache.lock` / `.github/workflows/`（站点与 CI 产物）。
    - **三个坑**：① 同一文件被两条引用（「月下自酌」「纵横不败」都指 `856adf0e.json`）→ 附件按文件名去重、索引按条目各列一行；② **根级 TITLE 会排到根级 DOC 之前**（与老坑 29 相反）→ 一发 `appendNode action_mode=sibling, node_uuid=<TITLE>, target_uuid=<最后一个根级DOC>` 归位；③ 非 md（index.html）入库会包 ` ```html ` 包围且**吃掉首部换行** → 回读比对按 `"```html\n\n" + src.lstrip("\n") + "\n```"` 算（差 1 字符不是丢内容）。
    - 实测：32 节点（2 目录 / 30 文档）、toc-md **PUT 0.5s**、四查全绿（全路径唯一 / 幽灵 0 / 根级序一致 / 30 篇逐篇回读 0 差 0 空、含 20 个附件 md5 抽验）；库 id 84711589。可复用脚本：`examples/legado-sources/`（build.py 四模式：prep/upload/all）。
    - **根级 TITLE / DOC 顺序（toc-md 常态）**：`PUT /repos/{id} {toc}` 把根级 **TITLE（目录）排在根级 DOC（松散文件）之前**。仓库根同时有目录与文件且**语义无要求**时（如 deepwrite：`.agents`/`apps`/`docs`/`packages`/`tools` + `package.json`/`LICENSE`…）这是**正常态、不必强行归位**（deepwrite 历史 ×4 库都是这个态）；只有「`00-前言.md` 必须排最前」这类**语义要求**才发 `prependNode/action_mode=sibling` 归位（且一次只能挪一个，多个要写循环）。
    - **桌面/打包类图标走占位，别指望 CDN**：`*.ico` 不在 `IMAGE_EXTS` → 落到二进制占位（`<!-- 二进制文件 … -->`）；`png/jpg` 类未引用资源会被 `upload_image` 传成 **CDN 占位文档**（`![名](cdn.nlark.com/…)`）。验收时这两者都不该算「异常」，按对应期望值比。

**坑 45（md 图片路径里的「成对括号」被截断 → 整条漏传，2026-10-20 Anduin2017/HowToCook @ f6da4528 实踩，v1.3.85 已修）**：`yuque_rewrite_images.py` 的 `MD_RE` 原写 `(!\[[^\]]*\]\()([^)]+)(\))`——**path 用 `[^)]+` 会在第一个 `)` 处停**，于是 `![石凉粉(冰粉)成品1](./石凉粉(冰粉)成品1.jpg)` 只截到 `./石凉粉(冰粉` → 判成「本地缺失」，图不传、正文留相对路径 = 裂图（本次 4 处：`石凉粉(冰粉)成品1/2.jpg`、`血浆鸭(特辣)/(微辣).jpg`；dry-run 会如实报「本地缺失 N」，别当噪音跳过）。
    - **修法**：path 改为允许**一层成对括号** `((?:[^()]|\([^()]*\))*)`；补单测 3 项（带括号路径 / 带括号+title / 带括号后缀说明）→ `scripts/test_rewrite_images_re.py` 现 12 项全绿。
    - **通用坑**：中文菜谱/图纸类仓库的文件名爱用括号（`石凉粉(冰粉)`、`血浆鸭(特辣)`），md 图片正则、链接提取一律要按「成对括号」写，别用 `[^)]+`。

**复用记录：Anduin2017/HowToCook（2026-10-20 @ f6da4528，库 84776562，622 节点）**
    - 默认分支 **master**（不是 main）；仓库形态：`dishes/<分类>/<菜名>/<菜名>.md` + **同目录配图**、`tips/`（技巧与 `learn/images/*.svg`）、根级 README/LICENSE/package.json/CI 配置。
    - **这是硬规则 10（图片目录别进导入根）在「配图与文档同目录」场景的落地样板**：358 张图（212 jpg / 96 jpeg / 42 png / 3 webp / 3 svg / 2 JPG）**全传 CDN + 重写 350 处引用 + 连图带目录删干净**（`find -iname '*.jpg' … -delete` + `find -type d -empty -delete`）→ 622 节点（216 目录 / 406 文档），文档数是「md + README/LICENSE/json/CI 文件」的真实数量。
    - **旧口径的代价（对照）**：上一版 743d7f46（库 84598602）把图片当文件导 → **760 篇里有 355 个 word_count=0 的空壳图片节点**，且正文 `![](./改刀.jpg)` 全是裂图。重导后 `word_count 0 篇 = 0`。
    - **8 张孤儿图**（`dishes/aquatic/葱油桂鱼/*.jpg`、`土豆炖排骨/*`、`青椒土豆炒肉/*`、`炒凉粉成品.jpg` 等，无任何 md 引用）直接随删除走，不建节点（上游自己漏引）。
    - 收尾：`--toc-md` PUT 4.5s 结构 PASS；**根级顺序天然正确**（TITLE 目录在前、DOC 文件在后，合老板 Windows 规则，无需归位——与 legado 那次「TITLE 反在 DOC 后」相反，取决于仓库根有没有目录）。

**复用记录：Anduin2017/HowToCook（2026-10-21 @ 0e106eea，库 84817850，622 节点；第 5 版）**
    - 复跑同 SOP 无新坑：master @ **0e106eea**（2026-10-20 18:07）距上版 f6da4528 仅 **2 commit / 只动 README.md**（+衍生作品、CI 自动修），节点数不变 622。
    - 配图重传：**350 唯一 URL / 353 处引用重写 / 12 外链跳过 / 0 缺失**（`--throttle 5`，约 30 分钟，0 失败 0 限流）；含带括号文件名（`石凉粉(冰粉)成品1.jpg`）与带全角冒号标题（`step①：准备米粉.jpg`）均正常（坑 45 已修）。上传后 `find -iname '*.jpg'…-delete` + 空目录删除 → 622 节点。
    - 收尾 `--toc-md` 目录树 622 行 / 23KB **PUT 3.4s**、结构核对 PASS；根级顺序天然正确（TITLE 3 在前 / DOC 8 在后）。五查全绿：TOC 622 == 本地 622、全路径唯一 True、缺失 0、对账错位 0、幽灵 0（docs 406 == TOC DOC 406）、**406 篇逐篇回读 word_count 全 >0 / 二进制占位 0**（唯一命中「本地图片引用」的是 `.github/manual_lint.js` 里的代码注释，非正文引用，属正常）。旧库 84776562 保留。

**坑 46（toc-md 整树 PUT 的 30s 读超时在接近 5000 节点的库上会挂，2026-10-20 morluto/rea @ 58d6043 实踩，v1.3.87 已修）**：`api()` 里所有请求写死 `timeout=30`，而 `PUT /repos/{id}` 设整树目录是**服务端重排操作**——耗时随节点数线性涨：4425 节点实测 22s、3917 行 21.6s（都卡在 30s 内，没暴露），本次 **4984 行 / 251KB 实测 35.4s** → 每次都 30s 超时，4 次重试全挂，`--toc-md` 收尾报 `fail: PUT toc 失败: TimeoutError: The read operation timed out`。
    - **有个坑中坑**：客户端超时**不代表服务端没执行**——实测超时后 GET `/toc` 一看，**整棵树其实已经写进去了**（4984 节点全对）。所以别急着重导正文：补跑一次 `--toc-md`（全 skip → 只拼树 + 再 PUT + 回读回填 uuid + 结构核对）即可，正文零损失。
    - **修法**：`api(...)` 加 `timeout=30` 形参（默认不变），**整树 PUT 那处单独传 `timeout=300`**；其余接口维持 30s。别全局调大——普通 CRUD 卡 5 分钟没意义。
    - **经验值**：节点数 → 整树 PUT 时长 ≈ 节点数/140 秒（4600 节点 ≈ 33s）。超 4000 节点就该预期 >30s。

**复用记录：morluto/rea（2026-10-20 @ 58d6043，库 84779255，4984 节点）**
    - 默认分支 main；**上游就是本机 REA 逆向环境（skill v41 + MCP + Ghidra 12.1.4）的源仓库**，俗称「用 agent 逆向一切」。
    - 距上版 9e259f87c（库 84713190）**83 commit / 300+ 文件变动**（src 168、docs 77、scripts 39）；本地节点从 4703 涨到 5026 → **首次触发「单库超 5000」**。
    - **口径决策（老板 10-20 拍板）**：不强拆库、不剔语言目录，**剔 `.github/`**（44 文件 / 8 目录 = CI workflow ×40 + issue 模板 + PR 模板 + action 定义，纯脚手架，正合硬规则 23）→ 4962 节点（380 目录 / 4582 文件）单库落地。**排 `.github` 前后实测 5031 → 4979（+分片）**。
    - 配图：仓库共 10 张图，**只有 4 张被 md 引用**（`docs/assets/{discord.svg,rea-hopper-analysis.png,rea-showcases.png}` + `website/public/assets/figures/rea-investigation-flow.svg`）→ 传 CDN；其余 6 张（favicon/social-card/4 张 figures svg）**无引用不传**，连图目录一起删。**两类引用都要改**：85 处 markdown 图片语法（脚本吃）+ **21 处「查看大图」普通链接**（脚本不吃，一条 `re.sub` 改到同一张图的 CDN URL，同坑 29）。
    - **`licenses/dinosaur.txt` 必须保留**（Chromium/BSD 许可文本，被 `licenses/README.md` / `THIRD_PARTY_NOTICES.md` 引用）——它在 `website/public/assets/licenses/` 里，**`rm -rf` 整个 assets 会误伤**（同坑 29 第②条）。做法：只删图片文件 + 空目录，非图片全留。
    - **submodule 空目录别删**：`third_party/{binwalk,jadx-headless-mcp,unblob,ghidra-nativeaot,wakaru}` 是 git submodule，fresh clone 里是空目录，`find -type d -empty -delete` 会顺手清掉 5 个节点（它们在上版库里是正常 TITLE 节点）→ 删空目录后要按 `.gitmodules` 补回来。
    - 四查：TOC 4984 == 本地 4962 + 22 分片；对账错位 0；幽灵 0（docs total 4604 == TOC DOC 4604）；深层 3 篇 word_count>0 + 4 张 CDN 图 200 + **分片内容 21/21 逐字符相等**（含 20 个 `website/locales/*/messages.po`，行边界切分）。
    - 计时：14:09 起建文档 → 15:14:42 建完（4582 篇 / 65 分钟，~70 篇/分）；收尾 PUT 35.4s（超时补跑）。旧库 84713190（9e259f87c）按旧库保留口径不动。

**坑 47（单库超 5000 的实拆法：按语义拆 2 库 + 描述互指，2026-10-21 morluto/rea d0067ba 首次实锤）**：上版 4979 刚好卡进单库，本版 +151 commit 后 **5270 节点，剔 .github 也塞不下** → 硬规则 9 真正落地。老板拍板的拆法（方案 A，最省心的拆法）：
    - **主库保留全部，只把最大的一块脚手架性质的目录挪出去**（本次挪 `tests/`）：`rea（d0067ba）`= 除 `tests/` 外全部 3621 节点；`rea-tests（d0067ba）`= `tests/` 1649 节点。**比「按代码/资料二分」更好**——主库仍是完整可读的项目本体，副库命名也天然合 `项目名-<顶层目录>（commit）`。
    - **描述必须互指对方库的完整 URL**（老板明确要求）：`… ｜ 测试套件另见 https://www.yuque.com/<login>/<slug> ｜ 导入 <日期>`——两库都写，别只写一边。注意算进 ~250 字上限（坑 39）。
    - 实施：`cp -al`（硬链接复制，不占空间）把 clean_dir 拆成两个导入根 → 各自 `--toc-md` 独立导入；`img_map` 里已是**绝对 CDN URL**，所以先重写图、后拆树，跨库引用不断。
    - 本次实测：A 3621 → TOC 3643（+22 分片）、B 1649 → TOC 1649；两库描述互指后 `create-book` 均一次成功。

**坑 48（并行导入是安全的，瓶颈不在 QPS 在「账号级 5000 请求/小时」，2026-10-21 实捶）**：老板提醒点破——**v2 API 限流是 100 QPS + 每小时 5000 次（同账号所有 Token 共享）**，低 QPS 的是 Web API（cookie），而 **toc-md 模式全程只走 v2**（附件上传才用 cookie，且已提前做完）。于是两库可以并行跑：实测并行合速 **~2.4 节点/秒**（单库约 1.2），A 3621 节点 09:42→10:27、B 1649 节点 09:42→10:03，比串行省 ~25 分钟，**0 失败、无 429**。
    - **红线算法**：一次导入的请求数 ≈ 文件数（目录不耗请求，分片各算 1）。本次 A 3345 文件 + B 1537 = **~4900 次，恰好卡在 5000/小时边缘** → 再大就得串行，或跨小时错峰起跑。
    - 并行前要**把原串行链的「第二个库」掐掉**（否则 A 跑完会再起一遍 B，两个进程写同一账本 → 账本打架）。做法：直接 `kill -9` 包装 shell + python，A 靠账本断点续传（本次已记账 268 节点，重启后自动 skip）。

**坑 49（toc-md 模式同样会留幽灵 doc，来源有两个，2026-10-21 实捶）**：验收「幽灵 0」不能只跑 reconcile——本次 A/B **各多出 1 个不在 TOC 里的 doc 本体**：
    - ① **杀进程残留**：断点那一刻 `POST /docs` 已成功、但 `progress.json` 还没落盘就 `kill -9`（A 的 `wasm-interface.txt`，created_at 正好是 kill 的那一秒）。
    - ② **重试双写**：创建响应超时/异常 → 脚本重试 → 服务端其实已建好（B 的 `jsonOutput.test.ts`，高负载下重试产生）。
    - **抓法**：逐页拉 `GET /repos/{id}/docs` 取全部 doc_id，与 TOC 的 DOC doc_id 集合求差；**别只看 `meta.total` 数字**——数字对不上时得知道是哪个。现成脚本：`scripts/yuque_check_ghosts.py --book <id>`（退出码 0/1，已成为验收第 5 查；`--delete` 自动删+回查 404）。
      ⚠️ `--toc` 参数吃**原始 API 响应**（`{"data":[…]}`）；自己 dump 出来的裸数组以前会 `TypeError: list indices must be integers`（2026-10-21 实踩）→ v1.3.92 起两种形状都兼容，不传 `--toc` 则由脚本现拉。
    - **收法**：`DELETE /repos/{id}/docs/{id}`（本次两个都 200），**回查 `GET …/docs/{id}` 应为 404**，再复核 `meta.total == TOC DOC`。删前先确认同名文件在 TOC 里**已有一份**（避免误删真身，同坑 10）——脚本会自动打印 TOC 同名 doc_id 供确认。

**坑 50（PDF 抽章混入 C0/NUL 控制符 → 整篇正文被判成二进制写成占位，2026-10-21 两本 LLM 书实捶）**：把「书 PDF + 课件 + 代码」型仓库做**双轨导入**（PDF 抽成逐章文档 + 原件挂附件）时，PyMuPDF 抽出的正文里会混进**公式/字体的渲染残渣**（`\x00` 开头、`\x00\x01` 等 C0 控制符）。这些控制符落进 md 后，导入器的二进制检测（`"\x00" in text` → binary）会把这**整篇**判成二进制 → 正文写成 `<!-- 二进制文件 0 MB, 跳过内容导入 -->` 占位、`word_count=0`，**结构类验收（节点数/全路径/对账/幽灵）全绿也拦不住**（同族事故见坑 36 GBK）。
   - **本次规模**：RUC《大语言模型》15 章中 **3 章中招**（第八/十/十二章，NUL 1~3 个）；fudan《大规模语言模型》12 章中 **2 章中招**（第五/六章）。
   - **根因修法（写在抽取器里，别事后补）**：抽出的文本先剥 C0 控制符再落盘 —— `re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)`（**保留 `\t\n\r`**）；落盘后再扫一遍兜底。
   - **事后修法**（已入库的）：剥控制符重写本地 md → `PUT /repos/{book}/docs/{slug}` 更新**已存在的 doc**（用账本里的 slug，**不要新建**，否则出幽灵）→ 复核 `word_count>0` + body 与本地**逐字符相等**。
   - **验收口径变更**：验收从「深层抽查 3 篇 word_count>0」升级为「**全库**逐篇 `word_count>0`（或 body 非占位）」（见 §二·7 第 6 查）——抽查必漏（中招是少数篇）。
   - 可复用脚本：`examples/llmbooks-dual-track/`（`build_lib.py`：抽章 + 剥控制符 + 附件/PPTX 文档预建 + 账本注入，`README.md` 含完整流程与验收）。

**坑 51（源仓库是「Windows 手写 md」：图引用四类脏，2026-10-22 scutan90/DeepLearning-500-questions 实捶）**：老书仓库（作者在 Windows 上边写边贴本地路径）的图片引用会同时出现四类脏，**只跑 `yuque_rewrite_images.py` 会漏掉一大批图（显示裂图）**：
   - ① **反斜杠**：`img\ch14\思维导图.png`（本次 16 处）
   - ② **盘符绝对路径**：`H:/<repo>/ch18_.../img/x.png`、`C:\Users\<用户名>\Desktop\x.png`（3 处）——文件其实就在 `img/` 里
   - ③ **URL 编码的中文名**：`img/ch7/DCGAN%E7%BB%93%E6%9E%84%E5%9B%BE.png`（5 处，`urllib.parse.unquote` 后就是磁盘上的 `DCGAN结构图.png`）
   - ④ **文件名带空格**：`img/ch8/Mask R-CNN-01.png`、`img/ch7/lsgan loss compare.png`（5 处）——`yuque_rewrite_images.py` 为吃 `![alt](path "title")` 做了 `raw.split(None, 1)`，**会把带空格路径截断**（`img/ch8/Mask`）→ 判「本地缺失」整条漏传
   - **治前 3 类**：`fix_refs.py`（`examples/deeplearning-500-questions/`）就地修——候选顺序「原样 → `\`→`/` → `unquote` → 组合」都不中时，再按 **basename 在全树反查**（唯一命中才替换；多命中且恰有一个在本 md 子树内才用），本次修 21 处
   - **治第 4 类**：`upload_space_imgs.py` 单独扫「本地存在且路径含空格」的引用 → `upload_image` 传 CDN → 替换成 https（主脚本随后自动跳过），本次 5 张
   - **别急着改主脚本**：`split(None,1)` 是给 `"title"` 用的，改坏了会连累所有带 title 的引用；用外挂旁路最省事
   - **顺带**：修完后**必然还剩一批「真缺失」**（本次 14 处：ch08 `CBNet-1..8`/`mmdetection.png`、ch09 `9.10.5-1..5`）——上游改图名没更文，**修不了、别找**，原样留裂图并在报告里说明
   - 完整流程 + 三个可复用脚本（`fix_refs.py` / `upload_space_imgs.py` / `fix_root_order.py`）：`examples/deeplearning-500-questions/`

**坑 55（Sphinx/reST 书稿：`literalinclude` 静默丢代码 + 首节提升压平大纲 + 块间无空行，2026-10-22 me115/design_patterns《图说设计模式》实战，v1.3.108 已修）**：Sphinx 工程（`conf.py`/`index.rst`/`Makefile`）用 `yuque_rst_convert.py` 转换时，三处会静默失真：
   - ① **`.. literalinclude:: /code/X/main.cpp` 被 docutils 整条丢弃**（那是 Sphinx 扩展指令，docutils 不认 → report_level 压住系统消息，正文里「代码分析」节的代码**全没了**，四查全绿也拦不住）。修法：转换前展开成 `.. code:: <lang>`（**docutils 核心自带 code 指令**）——路径 `/` 开头 = Sphinx srcdir（`--srcdir`，默认同 `--src`）、否则相对当前 rst 目录；语言取 `:language:` 选项、否则按扩展名映射；**代码里含 `<`/`&` 由 docutils 转义、剥标签后 `h.unescape` 还原**，与源文件逐字符等（tab 会按 docutils 规则展开，站点同样）。
   - ② **`doctitle_xform` 默认把首节提升为文档标题** → 剩余节全被渲成 `h1`，语雀大纲**扁平**（13 个 h1 并列）。修法：`settings_overrides["doctitle_xform"]=False`，恢复自然层级（章 h1 / 节 h2 / 小节 h3）。
   - ③ **块级元素用单 `\n` 拼接** → 相邻两段 `<p>` 在 markdown 里**并成一段**。修法：块收成 `(kind, text)`，按类型 join（**同类 `li`/表格行/引用行/`dt`-`dd` 用 `\n`，其余 `\n\n`**）。顺带把 `.. contents:: 目录` 整条剥掉（本地大纲与语雀侧边大纲重复）。
   - 另有：**`pre` 围栏带语言**（从 `<pre class="code cpp literal-block">` 的 class 取）→ ` ```cpp `；`_static/` 图片是 Sphinx **绝对路径** `/_static/x.jpg` → 先按目标目录深度改相对（根 `_static/`、子目录 `../_static/`）再跑 rewrite + 删目录（同 linuxtools 的 `/_static/` 处理）。
   - **范围口径**：只导书稿正文（`index/read_uml/三个分类目录/readme`），脚手架（`conf.py`/`Makefile`/`make.bat`/`sphinx_rtd_theme/`/`.EAP`/`.vsd`）全剔；**`code/` 也不入库**——各章示例源码已由 literalinclude 内联进正文，且子目录是编译产物（84 个 `.o` + 16 个 `.exe`）。
   - ⚠️ 上游 rst 图名**大小写写错**（`State1.png`/`State2.png` vs 磁盘小写 `state1.png`/`state2.png`，站点同错 = 404）→ 拷图按**大小写不敏感**解析真身。
   - 可复用脚本：`examples/design-patterns/`（`build_lib.py` 建中文树 + `fix_root_order.py` 根级 DOC 归位）。实测 25 节点（3 目录/22 文档）、69 图传 CDN、toc-md PUT 0.9s、六查全绿 + 22 篇逐篇回读 0 差；库 84861785。

**复用记录：ecomfe/spec（2026-10-22 @ 18a2da2，库 84864088，12 节点）**
    - 百度 ecomfe 前端团队「编码规范」合集（4598★），仓库形态极简、无脚手架：根级 12 篇 md（README + chart/javascript/es-next/html/css/less/e-json/module/package/directory/react）+ `chart/` 目录**纯配图**（23 张，全部被 `chart.md` 引用）。
    - **`chart/` 是「配图目录」不是「子文档目录」**——硬规则 10 落地：23 张图先 `yuque_rewrite_images.py` 传 CDN（23 处引用重写 / 0 缺失）→ `rm -rf chart/`；`chart.md` 本就是根级文档，无需重建树。收尾 12 节点（0 目录 / 12 文档，扁平）。
    - `.gitattributes`（16B 仓库配置）**不入库**（仓库脚手架，同硬规则 23）。
    - ⚠️ **正文里的「示例代码」图片引用别当裂图**：`html-style-guide.md` 有 2 处 `<img src="image.png">`（演示 HTML 写法的代码片段，磁盘无实体）→ rewrite 脚本如实报「本地缺失 2」，**属预期、原样保留**（同坑 29 第②条思路：先判断是不是真配图再决定处理）。
    - 实测：toc-md 目录树 12 行 / 455B **PUT 0.4s**、结构核对 PASS、0 失败；六查全绿（TOC 12 == 本地 12、全路径唯一、对账 0、幽灵 0、12 篇逐篇回读逐字符相等、word_count 12/12 >0）；抽 3 张 CDN 图 200。库名按仓库名口径「spec（18a2da2）」。

**复用记录：lf201014/STS2_MarisaMod（2026-10-23 @ 186005c，库 84896891，964 节点；本仓第 4 版）**
    - 杀戮尖塔2「魔理沙」Mod（Godot 4 + C#）。历史三版：84301043（10-07 全仓库 958 节点，无描述+随机 slug）、84355418（10-09）、84555533（10-14 @ 2ced719，963 节点，slug `sts2_marisamod-2ced719`）。
    - **Godot 工程的「全仓库口径」= 连 `.import`（208）/`.uid`（184）/`windows/` 构建产物（DLL/lib/exp + 6 个 `~*.TMP` 链接器残渣）/`marisamod.pck`（21MB）一起导**——与本仓历史三版完全一致，别自作主张剔元数据。
    - **图不需要手工 rewrite**：仓库里只有 1 篇 md（README，无图引用），199 张图全靠 `.tscn`/`.tres` 的 res:// 路径引用 → 直接交给 tree_import 的二进制分支自动传 CDN（`![name](cdn)` 嵌文档），**别跑 `yuque_rewrite_images.py`（一条都匹配不上）**。`icon.svg` 是文本走代码围栏（svg 只在「被判二进制」时才走 CDN 分支）。
    - 验收：`word_count==0` 会有 220 篇（199 图 + 21 二进制占位），**这是预期不是事故**——别按「全库 word_count>0」硬卡；卡的是「文本篇 word_count>0」（本次 679/679）。
    - 增量重导很快：HEAD 距上版只 1 commit/11 文件时，prep+导 964 节点 ~11 分钟（图传 CDN 占一半时间），toc-md PUT 6.9s。
    - 顺带：`git clone --depth 1` 后想核「上版到本版改了啥」→ `curl api.github.com/repos/<o>/<r>/compare/<old>...<new>`（比翻本地强，沙箱无 GitHub 登录也能用）。

**坑 58（未完成译本：官方站侧栏 = 发布层，仓库里的「标题-only 空壳」未发布 → 剔空壳，2026-10-23 waylau/Gradle-2-User-Guide 实战）**：纯 GitBook 源仓库（`README.md` + `SUMMARY.md` + 扁平 `Chapter NN. xxx.md`）可能是**烂尾译本**——本次磁盘 73 个 md，但 66 章里只有 `Chapter 01–23` 有正文，`Chapter 24–66`（43 个）+ `Appendix A/B/C`（3 个）全是**标题-only 空壳**（~70B = 一行标题 + `===` 下划线 + 一个空格）。
- **判据（两个一起用）**：① 官方站（`https://<user>.gitbooks.io/<book>/`）侧栏 `li.chapter[data-path]` = **实际发布的书页清单**（本次 24 页 = index + ch01-23 + 附录E）——**空壳文件站上根本不发布**（SUMMARY.md 也只列了这 24 条，二者一致）；② `wc -c` 全量扫各章，量出空壳（阈值 ~150B）。
- **口径**：导入根 = **官方站发布层 ∪「有正文的孤儿」**。本次 = `README.md` + `Chapter 01–23` + `Appendix E`（站上发布）+ `Appendix D`（5.1KB 有正文但站上未发布 → 按「内容不丢」纳入）= **26 篇**；**剔掉** 46 个标题-only 空壳 + `SUMMARY.md`（= 目录本身，非书页；站上 index 才是首页）+ `.gitignore`（脚手架，硬规则 23）。**收尾主动向老板报残缺度**（本次报「译本只到 23 章 + 附录 D/E」）。
- **其他**：扁平 GitBook 源**无层级**（SUMMARY 全是同级 `* [..]`）→ 直接平铺、0 目录节点；本次图 24 处**全是外链**（`99btgc01.info` 死域名 + gradle logo CDN）→ **0 本地图**，不传 CDN、原样保留（同坑 36 的「死外链原样留」）。
- **实测**：26 节点（0 目录 / 26 文档）；toc-md 目录树 26 行 / 1930B **PUT 0.9s**、结构核对 PASS、0 失败；六查全绿（TOC 26==本地 26、全路径唯一 True、对账 0、幽灵 0、**26 篇 word_count 全 >0**、逐篇回读 **26/26 逐字符相等**）；库 **84898523**（slug `gradle-2-user-guide-45947642`）。⚠️ 全程直接 `--toc-md` 全量跑，**别配 `--test 6`**（本文件坑 26）。

**复用记录：waylau/Gradle-2-User-Guide（2026-10-23 @ 45947642，库 84898523，26 节点）**
    - 纯 GitBook 源《Gradle 2 用户指南》中文译本（waylau，2017-01-26 `add v 3` 后停更）。扁平结构，无子目录、无本地图。
    - 口径见上文坑 58（发布层 24 页 + 孤儿 `Appendix D`；剔 46 个标题-only 空壳 + `SUMMARY.md` + `.gitignore`）。
    - 与 waylau 同族书对照：`waylau/gradle-3-user-guide`（README 里提及）如老板要可同法导。
