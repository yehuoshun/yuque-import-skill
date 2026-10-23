---
name: yuque-import-skill
description: 语雀知识库全量目录导入与对账修复技能。把本地目录树整棵导入语雀（文件夹=TITLE 目录节点、文件=文档，DFS 先序保持层级，断点续传），导入后对账修复错位节点。当用户要求「把这个目录/代码库/资料树导入语雀」「按目录结构建语雀知识库」「把 GitHub 项目/开源仓库导入语雀」「按开源项目流程到语雀」「把网站/教程站抓取到语雀」「网页抓取导入语雀」「语雀导入遇到挂错层级/重复节点」「把小说/这本 txt/epub 导入语雀」「小说导入语雀」时使用。
---

# 语雀全量目录导入 — AI 工作流

> 实战验证：sts2-res 反编译源码 3921 节点整库导入，零重复零缺失（2026-10-05）。

---

## 🚫 硬规则（优先级最高，逐条遵守）

1. **断点必须每节点落盘**：progress.json 在每个节点「创建+挂载成功」后立即保存，禁止攒批（攒批=中断丢一批 + 父级映射缺失 → 文档挂根错位，v1 事故）
2. **根节点判断用 `not parent_uuid`**：语雀 TOC 里根节点的 `parent_uuid` 是**空串 `""`** 不是 null，`n.get("parent_uuid")` 为 falsy 即根
3. **文档创建后不会自动进 TOC**：`create_doc` 之后必须 `PUT /toc` + `appendNode` 挂载，两步缺一不可
4. **路径重建算法**：从节点自身开始 `while True: parts.append(title); 若 parent_uuid 为空则 break; 上移父节点`——先加自己再上移；从父开始拼会丢根层前缀导致全量误报错位
5. **挂载校验**：appendNode 返回的 TOC 里必须 find_node 到刚挂的节点（title/doc_id 双查），找不到＝当作失败重试，不许静默跳过
6. **同父节点重名检测**：导入前先跑对账（reconcile），重复组数>0 时先清重复再导
7. **文件名带后缀**：文档标题 = 文件名（含扩展名），目录 TITLE = 文件夹名，与磁盘一致
8. **单篇内容校验（2026-10-13 老板定）**：创建/更新响应自带 `word_count`——真实文本正文必须 `>0`，否则正文没进去（曾静默丢成占位注释，hi-byte 误判事故）；占位/图片段（`<!--`/`![` 开头）和纯空白允许 0。校验失败按普通失败走静置重试
9. **知识库节点上限 5000（2026-10-14 老板拍板）**：语雀单库节点硬上限 5000。`prep` 节点数（含超限文件 512KB 切分的预估分片）> 5000 时必须分库：按顶层目录拆多个库（命名 `项目名-<顶层目录>（commit）`），不硬塞单库；`yuque_repo_import.py prep` 已内置 >5000 警告。**首选拆法（2026-10-21 rea 首次实锤）**：主库保留全部、只把最大的一块挪出去（本次挪 `tests/`），两库描述**互指对方完整 URL** —— 见 `references/github-repo-to-yuque.md` 坑 47
   ⚠️ **别把两个「5000」混了（2026-10-21 老板拍板强调）**：本条是「**单库节点数**上限 5000」（容量/结构限制，超了必须分库）；限流里的 5000 是「**账号级请求数/小时**」（速率限制，超了报 429）。两者**独立且同时生效**——分库能解前者，但分库后多库并跑的请求数要合起来看要不要撞后者。
10. **图片目录别进导入根目录（2026-10-15 HgInit 实战）**：tree_import 会把图片/二进制文件建成**独立占位文档**（每张图一个节点，垃圾）。图片必须：先 `upload_image` 预传语雀 CDN（cookie 见 `--cookie-config`）+ 重写 md 引用为 CDN URL（`img_map.json` 缓存防重传）——**现成脚本 `scripts/yuque_rewrite_images.py`**（同时吃 markdown `![]()` 与 HTML `<img src>` 两种写法，**单/双引号都吃**；`--throttle` 控速、`--dry` 只统计），再从导入根目录**删掉图片文件夹**，只导 .md。Sphinx/仓库类 rst→md 转换后尤其注意（`_images/` 等目录）；缓存文件（`img_map.json` 等）同样不能留在导入根目录

11. **知识库描述必须标注来源（2026-10-18 老板拍板）**：`create-book --desc` 一律写清来源，格式 `来源：<URL>[@ <commit>] ｜ <口径/作者说明> ｜ 导入 <日期>`（有多源就都写上，如「站点 + 源仓库」）。开源项目口径至少 `来源：<repo url> @ <commit>`；网站口径写 `来源：<源站 URL>`；双轨库（原版 + 解析）要注明「原版原件附件 + 解析」。**禁止空描述、禁止只有库名**——描述就是下次能凭它找回来源的那一行。
   ⚠️ **描述有长度上限（2026-10-20 实捶）**：`create-book` 的 `--desc` 太长会返回 `HTTP 400 验证失败，一般是路径名冲突，或者文章标题不符合要求`（**报错信息完全误导，跟名字/slug 无关**）——实测 251 字符通过、261 字符被拒（约 250 封顶）。超了就把括号说明压短，别去改库名/换 slug。
   📌 **多库（同一源拆成多个知识库）必须互指（2026-10-21 老板拍板）**：每个库的描述里都要写清「本库包含什么 + 其余部分另见对方**完整 URL**」，格式 `来源：<URL> @ <commit> ｜ <本库范围> ｜ <其余范围>另见 <对方库完整 URL> ｜ 导入 <日期>`；**两边都写，禁止只写一边**（只写一边等于断链）。拆库口径见硬规则 9 + `references` 坑 47。
12. **附件（`type=attachment`）只给 PDF（2026-10-21 老板拍板）**：**只有 PDF 原件允许上传附件**；其他任何文件一律**不上传附件**——包括资源索引型仓库的原件 JSON（legado 那套「原件附件轨」停用）、MkDocs 站的 mp4/zip/rar、素材包等。落地：① 原件若上游有直链（如 `legado.aoaostar.com/sources/<file>`）就在索引里给**直链**，不上传；② 本地才有的非 PDF 资源**保留原相对路径、不重写、不删**，并在文档里注明「未上传」；③ **图片例外**，仍走 `type=image` CDN（硬规则 10，那是图片接口不是附件）。

---

## 流程

### 一、导入（scripts/yuque_tree_import.py）

```bash
# dry-run 看节点清单和树序
python3 scripts/yuque_tree_import.py --root /path/to/dir --book <book_id> --progress ./progress.json --dry

# 试水前 6 个节点（验证 API/结构）
python3 scripts/yuque_tree_import.py --root /path/to/dir --book <book_id> --progress ./progress.json --test 6

# 全量导入（后台跑，断点续传；失败自动静置重试）
python3 scripts/yuque_tree_import.py --root /path/to/dir --book <book_id> --progress ./progress.json
# 可选：调整失败静置策略（默认 --pend-sleep 600 --pend-retries 3）
python3 scripts/yuque_tree_import.py --root /path/to/dir --book <book_id> --progress ./progress.json --pend-sleep 300 --pend-retries 5
```

- token 来源：环境变量 `TOKEN_L91` 或 `~/.openclaw/secrets/credentials.env` 的 `export TOKEN_L91="..."`，**脚本不硬编码 token**
- 失败静置重试：单个节点挂载失败（如 `TITLE 节点未在返回目录中找到`）→ 静置 `--pend-sleep` 秒（默认 600）→ 清理残留同名节点 → 重试，最多 `--pend-retries` 轮（默认 3）；仍失败才记 fail。**背景（2026-10-07 实验证实）**：高频连续创建（几百节点不间断）会让语雀 TOC 写路径积压，新建空目录挂子静默失败（响应乐观回显但实际挂根）；静置 ~10 分钟自愈，节流（每请求间隔 1.5s + 每百节点休息）可完全规避。故默认保持高频 + 失败静置重试，不主动降速，除非想稳到底（用 `--pend-sleep` 调小）+ 外部节流。
- **batch 模式（2026-10-16 新增，防积压终极方案）**：`--batch-mode [--batch-size N] [--x-login 用户名]`
  - 原理：doc 层（create_doc）不受 TOC 队列限制可连续造；**TOC 挂载改两段式**——节点统一 appendNode 挂根（根层追加实测稳定）→ 攒批 → Web API `PUT /api/catalog_nodes/batch`（batchMove，一次请求 N 个节点）批量归位。把「N 次高风险子树插入」变成「N 次低风险挂根 + N/B 次服务端批量移动」
  - 实测（2026-10-16 测试库，11 节点 5 目录 6 文件含 512KB 分片）：0 失败、无残留、DFS 序正确（目录前文件后、分片 1→2→3）
  - **顺序语义（实测）**：batchMove 的 prependChild = 「整体插到目标最前、保持数组内顺序」；同父多批若按序 flush 后批会插到前批前 → 脚本已实现「逆序逐片 flush」（最后一片先挂）保证正序
  - 依赖：`--cookie-config` 需有效 cookie/ctoken（Web API 认证，会过期）；中断后重跑自动扫描 progress 里位置未归位的节点重新入队
- **⭐ toc-md 模式（2026-10-16 新增，官方 v2 能力，推荐默认）**：`--toc-md`
  - 原理：官方 OAS（`yuque_openapi_20260722.yaml`）中 `PUT /api/v2/repos/{book_id}` 的 **`toc` 字段 = Markdown 目录树**（原文「可利用此字段批量更新知识库的目录」）。文档经 `POST /repos/{book}/docs` 建好后**自动挂到 TOC 根**，目录分组由目录树本身生成 → **逐文件建文档 + 一次 PUT 设整棵目录**即完成，无需逐节点 `appendNode`，也无需 batchMove
  - 用法：`python3 scripts/yuque_tree_import.py --root <dir> --book <id> --progress <p> --toc-md`
  - 实测（一次性库，同树对照）：134 节点库 **PUT 仅 1.1s**；与 batch 模式同树导入的 TOC **集合与顺序逐项完全一致**；分片/特殊字符标题（`weird[1] (x).md`/`a](b`/`p[q](r`/中文）7/7 原样正确；幽灵 0；对账 0 错位
  - **标题原样写，禁转义**（实测：`\[`/`\]` 与 `&#91;` 会被当字面量写进标题 → 变脏）；语雀按最后一个 `](slug)` 切分，嵌套/不平衡括号都能扛
  - 对比 batch 模式：请求数 ~减半（不再对每篇文档发 `appendNode`），收尾 ~80 分钟 → **秒级**；无需 cookie
  - 收尾自动：拼目录树 → PUT → 回读回填 uuid（含分片段）到账本 → 结构核对，输出 `[toc-md] 结构核对 PASS ✅`；核对失败会把缺失路径记入 fail
  - ⚠️ **收尾后根级 DOC 会排到 TITLE 目录之后**（doc 先建挂根、TITLE 后由目录树生成）→ 按需补一发 `PUT /toc {action:prependNode, action_mode:sibling, node_uuid:<根级DOC>, target_uuid:<第一个TITLE>}` 归位（2026-10-17 FreeBSD 手册实踩，refs 坑 29）
  - 编排器 `yuque_import_all.py` 已默认启用（`--no-toc-md` 可回退旧流程）

- 内容格式：`.md` 原样 / `.cs` → ` ```csharp ` 代码块 / 其余 → 纯文本代码块
- 超限自动处理：二进制（NUL/无效 UTF-8 占比高）→ 图片类（png/jpg/gif/webp/svg…）自动上传语雀 CDN 并 `![文件名](cdn_url)` 嵌入（需 cookie/ctoken，见 `--cookie-config`）；非图片 → 占位说明；文本超 512KB（`--max-body` 可调，**默认 512KB**，2026-10-14 老板拍板：1MB 语雀端加载也要等很久；上限别碰 4MB——语雀端直接打不开）→ 自动拆成多文档 `xxx (1/N)` `(2/N)` …，内容零丢失。**切分必须按语义边界，禁硬拆**（2026-10-14 老板：硬拆影响观感）：JSON 顶层数组→按条目边界（每段是完整记录组成的可解析 JSON），其余→按行边界（绝不切破行；单行自身超限才硬切）；每段正文头带范围注记 `分段 i/N · 第 a-b 个条目（共 M 个）· 首条「xx」· 源文件 X MB 超限，按 JSON 条目边界切分`；代码块按扩展名标注语言（json/ts/vue/py…）
- 中断后重跑同一命令即续传，跳过已完成节点

### 二、对账修复（scripts/yuque_toc_reconcile.py）

```bash
# 只对账（打印错位清单）
python3 scripts/yuque_toc_reconcile.py --root /path/to/dir --book <book_id> --progress ./progress.json

# 对账 + 移动修复
python3 scripts/yuque_toc_reconcile.py --root /path/to/dir --book <book_id> --progress ./progress.json --fix
```

- 期望路径 = progress 账本（与导入同源），实际路径 = 语雀 TOC 按 parent_uuid 链重建
- 两者不一致 → appendNode(child, target=期望父级 uuid, node_uuid=当前) 移回

### 三、验收（必做）

1. 语雀端 TOC 节点数 == 本地节点数
2. 全路径唯一性：`len(paths) == len(set(paths))`（无重复无缺失）
3. 抽查深层路径（如 `src/Core/Models/AbstractModel.cs`）实际可达
4. **有超限分片的库必须跑分片内容验收**（2026-10-17 加，见 `references` 坑 28）：
   `python3 scripts/yuque_verify_shards.py --root <clean_dir> --book <id> --progress <账本>`
   —— 路径映射对不对 **不代表正文没丢**；JSON 顶层数组切分的 bug 就是路径验收全 PASS 但第 2 片起正文全空。
5. **幽灵文档必须为 0（2026-10-21 老板拍板升为必做，见 `references` 坑 49）**：TOC 里没有、但库里真实存在的 doc 本体。
   `python3 scripts/yuque_check_ghosts.py --book <id> [--toc <toc.json>] [--delete]`（退出码 0 = 无幽灵；脚本会拉全量 `GET /repos/{id}/docs` 与 TOC 的 DOC doc_id 集合**求差**，**别只看 `meta.total` 数字**——对不上时得知道是哪一个；口径 = `docs total == TOC DOC 数`）
   - 两个常见来源：① `kill -9` / 重启那一刻 `POST /docs` 已成功但账本未落盘；② 创建响应超时/异常 → 脚本重试 → 服务端其实已建好（双写）。**toc-md 模式同样会中**。
   - 清理：`DELETE /repos/{id}/docs/{id}`（200）+ 回查 `GET …/docs/{id}` 应 404 + 复核 `meta.total == TOC DOC`；**删前先确认同名文件在 TOC 里已有一份**（防误删真身，同坑 10）。
6. **全库「占位文档」扫描 = 0 篇（2026-10-21 升为必做，见 `references` 坑 50）**：逐页拉 `GET /repos/{id}/docs`，**每篇 `word_count` 必须 >0**（或 body 不以 `<!-- 二进制文件`/`<!-- 源仓库中该文件为空` 开头）。**别只抽查几篇**——中招总是少数篇（PDF 抽章混入 NUL/控制符 → 整篇被当二进制；GBK 源码同族，坑 36），抽查必漏。修复用账本里的 slug 走 `PUT /repos/{id}/docs/{slug}` 更新**已有 doc**（不新建，否则出幽灵）。

---

## API 速查（详见 references/api-notes.md）

| 操作 | 方法/路径 | 关键参数 |
|------|----------|---------|
| 创建文档 | POST `/repos/{book}/docs` | title, format=markdown, body（≤4MB，超 512KB 自动分段，`--max-body` 可调） |
| 挂载/移动/删除节点 | PUT `/repos/{book}/toc` | action: appendNode/prependNode/editNode/removeNode; action_mode: sibling/child; type: DOC/TITLE/LINK |
| 建分组 | PUT toc | action=appendNode, action_mode=child, type=TITLE, title=分组名 |
| 知识库分组（书架 stack）移动 | PUT `/api/mine/book_stack/move`（Web API，cookie/ctoken）body `{"targetStackId": 数字, "targetBookIds": [book_id]}`；**旧 `PUT /api/books/{id}` + `{"stack_id": N}` 返回成功但不生效（2026-08-31 修，2026-10-12 实踩复现）** | stack_id 是语雀分组（书架）ID，非 TOC 分组；需 cookie/ctoken 认证（v2 token 不支持）；移动后必须回查 book_stacks 验证 |
| 查全部分组 | `yuque_get_book_stacks`（yuque-mcp 工具） | 返回所有 stack：id/name/books；MCP 全组工具：create/rename/delete/sort/update_book_stack |
| 建文档节点 | PUT toc | action=appendNode, action_mode=child, type=DOC, doc_ids=[doc_id] |
| 移动 | PUT toc | action=appendNode, action_mode=child, target_uuid=新父, node_uuid=当前 |
| 拉全量 TOC | GET `/repos/{book}/toc` | 返回扁平数组，parent_uuid 链重建树 |

## 已知坑（全踩过）

- `prependNode` 创建时（传 doc_ids）不支持，必须先 appendNode 再 prependNode
- `removeNode`+`appendNode` 会产生新 uuid，旧 uuid 不可复用
- `editNode` 改 prev_uuid/sibling_uuid 不生效，排序只能用 prependNode
- **removeNode 删子树乐观回显陷阱（2026-10-12 实捶）**：`PUT /toc {action: removeNode}` 删带子节点的 TITLE 时，响应会**乐观回显残留节点（看似正常），实际执行却把整库 TOC 连带清掉**，甚至文档本体被删（抽查 /docs 404）。铁律：**任何删除/移动后，必须立刻重新 GET /toc + GET /docs/{id} 双重复查**，不能信删除响应；如整树重导，逐个 `DELETE /repos/{book}/docs/{id}`（200）比 removeNode 干净——删除后同样复查。教训来源：2026-10-12 gitref 误导移除时 gitref 8 篇被连带删除
- **网页抓取必须滤导航**：抓整站 HTML→md 时，页面左侧/顶部导航栏（品牌、菜单、章节列表）会混进正文，每篇重复。抓取器应只提取正文容器（如 gitref 的 `id="content_box"` 包裹区），导航区块整体丢弃。gitref 初版 nav 混入 8 篇、重抓修复（2026-10-12）
- 限流：429/5xx 指数退避重试（脚本已内置 4 次）
- **知识库分组 ≠ TOC 分组**：TOC 分组是文档树目录；知识库分组（stack）是把整个知识库归类到个人空间书架（如「开源项目」）。v2 token 拿不到 stack 接口，必须 cookie/ctoken（yuque-mcp 已内置，用 `yuque_update_book_stack(book_id, stack_id)`；手动版 `PUT /api/books/{id}` + `{"stack_id": N}`）。2026-10-12 踩坑：误把 stack 36149506（文章收集）当开源项目，靠 MCP `get_book_stacks` 才发现真分组是 57018723。**移动后必须用 get_book_stacks 验证分组名而非只看 stack_id 数值**
- **二进制检测 hi-byte>0.9 启发式是雷（2026-10-12 实捶，v1.1.3 已删）**：中文 UTF-8 三字节全 >127，中文密集文本（.md/.cs 注释/.txt）比例轻易超 0.9 → 被误判二进制 → 正文丢成占位注释，HowToCook 46 篇/deepwrite 63 篇/Nulab 12 篇等 21 库 169 篇中招。判定文本只用「UTF-8 解码成功 + 无 NUL 字节」；真二进制由 NUL/解码失败捕获。已受损库用 `yuque_repair_placeholders.py`（TOC 路径映射回填）修复
- 同名文件在不同路径（如 eng/orbs.json 与 zhs/orbs.json）：语雀自动处理，实测无冲突

## 开源项目导入（GitHub repo → 语雀，2026-10-12 老板固化）

触发模板：「把 `<repo>` 按开源项目流程到语雀」。规范：库名 `项目名（commit id）`、分组「开源项目」（stack 57018723）、描述 `来源：<url> @ <commit> ｜ <口径说明> ｜ 导入 <日期>`（硬规则 11，2026-10-18 老板拍板：描述必须标注来源）。

```bash
# 1. 克隆/更新 + 干净副本 + 节点数
python3 scripts/yuque_repo_import.py prep --url <git-url> --dir /home/admin/.openclaw/workspace/tmp
# 2. dry-run 核数 → 3. 建库 → 4. 移分组（内置等待+验证）
python3 scripts/yuque_repo_import.py create-book --name "<项目名>（<commit>）" --slug <项目名>-<commit> --desc "<url> @ <commit>"
python3 scripts/yuque_repo_import.py move-stack --book-id <book_id> --stack-id 57018723
# 5. test 6 → 全量（后台+心跳 25/50/75/完成）→ 对账 → 验收六查
python3 scripts/yuque_tree_import.py --root <clean_dir> --book <book_id> --progress <账本> --test 6
```

完整 SOP + 坑清单：`references/github-repo-to-yuque.md`（必读，含 7 条踩过的坑）。

**源仓库是 Sphinx/reST 书稿时**（`conf.py`/`index.rst`/`Makefile`，可用 `yuque_rst_convert.py`）：正文常用 `.. literalinclude::` 内联示例源码 → **转换器必须先展开成 `.. code:: <lang>`（否则代码静默全丢）**，另开 `doctitle_xform=False` 保层级、块间补空行、剥 `.. contents::`；脚手架全剔、**`code/` 不入库**（源码已内联 + 里多含 `.o/.exe`）；`_static/` 是绝对路径要先改相对再传 CDN。见坑 55 + `examples/design-patterns/`（2026-10-22《图说设计模式》）。

**源仓库是 AsciiDoc 书稿时**（老 gitbook 书 + `book.txt`/`entries.txt`/`include::`，全树无 `.md`，2026-10-18 puppet-27-cookbook 实战）：走同一个开源项目口径，但要**自写 AsciiDoc→md 转换器**（规则表 + 8 条转换坑见 `examples/puppet-cookbook/README.md`）；老 gitbooks.io 渲染站还活着时，可拿它当**逐页正文 oracle**（校验转换器有没有丢字）。详见 references 坑 40。
GitBook 3.x 源仓库的书（站点给链接但同名 source repo 在 GitHub，正文是 `chapter-N/chapter-N-M.md` 扁平编号、层级只在 SUMMARY.md 里）：可复用脚本 + README 见 `examples/datamining-guide/`（2026-10-18《面向程序员的数据挖掘指南》实战，含重建规则与 2 个新坑）。
**老 GitBook「独立域名」型书仓**（`legacy.gitbook.com/...` 死链 / `*.gitbooks.io` 302 到已被抢注的空壳域名，如 learnes.net）：同样改吃源仓库 md；SUMMARY 常与磁盘**大小写不符 + 断链**，且**图可能是绝对外链**（raw.githubusercontent）需按 basename 反查本地文件重写成 CDN —— 复用脚本 + README 见 `examples/elasticsearch-guide/`（2026-10-18《Elasticsearch 权威指南（中文版）》实战，坑 36/37）。
**站点域名直接死掉 + SUMMARY 多层嵌套 + 旧版整编孤儿**（如 `kibana.logstash.es` DNS 不解析，仓库 `homepage` 指认源仓库）：复用脚本 + README 见 `examples/elkstack-guide/`（2026-10-18《ELKstack 中文指南》实战，坑 38；含空链接/断链节点落 TITLE、点分编号多层命名、v3 旧版孤儿归档、外链图「能救的救」口径）。

**站点域名死掉且仓库不自证（`homepage` 不写域名）+ 残缺译本**（如 `udn.yyuap.com` DNS 不解析，靠 `gh search repos "<书名> 翻译"` 反查）：复用脚本 + README 见 `examples/mastering-es-guide/`（2026-10-18《Mastering Elasticsearch 中文版》实战，坑 39）。⚠️ **老译本仓库常烂尾**——动手前先扫空壳（`wc -c` 各章）：SUMMARY 收录的空壳章照建节点，未收录且 0 字节的孤儿**跳过**，并**主动向老板报残缺度**。
**MkDocs/VuePress 教程站的源仓库（站点是渲染产物，仓库里躺着 md 源）**：只吃 `docs/`（剔 `css/` `mathjax/` `yeti/` 主题脚手架）；⚠️ **相对路径按渲染后站点 URL 的深度写**（`../img/…` 会多一层、嵌套目录甚至 `../../../img/…`）→ 用带路径归一化的重写脚本；**mp4/zip/rar 不再上传附件**（2026-10-21 口径：附件只给 PDF）→ 正文保留原相对路径/上游外链、注明「未上传」，不重写；默认分支可能不是 main（如 `new-theme`）—— 复用脚本 + README 见 `examples/learnopengl-mkdocs/`（2026-10-18《LearnOpenGL CN》实战，82 节点 / 369 个资源，坑 42）。
**章节目录名无语义（`tutNN/`）+ 逐章自带 `tutNN/res/` 同名图**：可读标题只在 `SUMMARY.md` 里 → 按 SUMMARY 重建树（`NN-标题` 剥「第N课：」）；⚠️ **先在原布局跑 CDN 重写、再重建树**（同名图跨章串台）；标题只信 SUMMARY（磁盘 heading 有笔误）—— 复用脚本 + README 见 `examples/opengl-tutorials/`（2026-10-18《OpenGL 教程》实战，21 节点，坑 43）。
**资源索引型仓库（仓库不装正文，装的是「别的 App 的资源清单」，如 `aoaostar/legado` 的「阅读」APP 书源站）**：走**解析单轨**（⚠️ **2026-10-21 口径变更**：附件只给 PDF，原「原件附件轨」**停用**——历史 3 版 `fd0ec7f9`/`0dde287`/`8b13d08` 都是双轨，脚本 `upload` 模式不再执行，源码留档）——把每个 `sources/*.json` 逐条转表（书源/TTS 列名称+网址、净化规则列正则）挂 `08-解析/sources/`，索引里的「原件」列改为**上游直链**（`legado.aoaostar.com/sources/<file>`，仓库 README 本来就有），不再建 `01-原版附件.md`；顶上加 6 篇分类索引（名称/条数/来源网站/上游更新时间/直链/一键导入）；站点/CI 产物（`CNAME`/`cache.lock`/`.github/`）不入库 —— 复用脚本 `examples/legado-sources/`（2026-10-18 legado fd0ec7f9 首版，32 节点，坑 44）。
**单篇长文型仓库（仓库里只有一篇文章，不是多章书）**：按 `## N.` 拆篇 + README 做 `00-译者说明.md`，英文原文不收，文件名剥「N.」与标题内链接/sup；拆篇会让原文内部锚点（脚注 `#f1`）跨文档失效，原样保留 —— 口径见 references 坑 41（2026-10-18《傻瓜函数编程》实战，15 节点）。
**未完成译本（纯 GitBook 源，仓库里一堆「标题-only 空壳」章）**：先扫官方站侧栏 `li.chapter[data-path]`（= **实际发布的书页清单**）+ `wc -c` 全量量空壳 → 导入根 = **发布层 ∪ 有正文的孤儿**，标题-only 空壳全剔、`SUMMARY.md`（=目录本身）剔；扁平 GitBook 源无层级，直接平铺 —— 口径 + 实测见 references 坑 58（2026-10-23 waylau/Gradle-2-User-Guide，26 节点，库 84898523）。

## PDF 书导入（只有 PDF 的官方站，2026-10-18 固化）

触发模板：「把这本 PDF 书/这个站（只有 PDF）导入语雀」。SOP：`references/pdf-book-to-yuque.md`；实战首例 + 脚本：`examples/ostep-pdf/`（fetch_ostep.py + extract_ostep.py + README 含排版识别表与 8 条坑）。

要点：PyMuPDF `get_text("dict")` 按字号/字体/缩进重建结构；断词用 `words_alpha.txt` 词表判断「删连字符拼接 vs 保留复合词」；矢量图文字会混入正文，图本身按老板口径可跳过；只有 PDF 的官方站走网站口径（库名带日期、分组「文章收集」）。

**变体：LaTeX 中文教材（多本一套，2026-10-22 蒲公英书系列 nndl.ai）** —— 站上只有落地页、正文是 release 里的 LaTeX PDF；同一站多本书 → **分开建库**（老板拍板）。标题用**书签文本锚定**（节号/标题同 y 拆两行要合并、附录节号带字母）；右侧**边注栏**用 `margin_x` 分流成 `> 📝` 引用块；**代码行攒成围栏代码块**（否则代码注释 `#` 会当 H1 炸大纲）；**根级 TITLE 会按 Unicode 字典序错序**（一<三<二<附）需 `fix_order.py` 归位。复用脚本 + 完整坑清单：`examples/nndl-pdf-series/`，SOP 细节见 `references/pdf-book-to-yuque.md` §六。

**老书仓库（作者在 Windows 上边写边贴本地图路径）→ 图引用四类脏**（反斜杠 16 / 盘符绝对路径 3 / URL 编码中文名 5 / 文件名带空格 5）：前三类用 `fix_refs.py` 就地修（含按 basename 全树反查），带空格的 5 张用 `upload_space_imgs.py` 旁路单独传（主脚本的 `split(None,1)` 会截断带空格路径）→ 复用脚本 + README 见 `examples/deeplearning-500-questions/`（2026-10-22《深度学习500问》实战，81 节点 / 551 图，坑 51）。⚠️ 修完必剩一批**上游真缺失**（改图名没更文），修不了、别找。

**变体：InfoQ 中文站迷你书（只有 PDF，且下载要登录，2026-10-22《硝烟中的Scrum和XP》首例，库 84860629）** —— 老域名 `infoq.com/cn/minibooks/*` 被 AWS WAF 挡（405）→ 用 `infoq.cn`；公开 API **必须 POST + JSON body**（`/public/v1/article/getDetail {"uuid":<slug>}`）；下载接口 `article/book_sign` 要登录（`-2000 未登录`）→ ⭐ **绕法：迷你书列表页有公开免登录合集 `static001.geekbang.org/resource/ebook/100books/book100.zip`（541MB），用 HTTP Range 读中央目录只抽目标条目 + zlib(-15)**。书签漏前言 → 按页码区间列文档映射。复用脚本 + 坑清单：`examples/infoq-minibook-pdf/`（`build.py` + README），SOP 细则见 `references/pdf-book-to-yuque.md` §七。

**变体：仓库 = 书 PDF + 课件 + 代码（双轨，2026-10-21 两本 LLM 书固化）** —— 源是 GitHub 仓库时走**开源项目口径**（库名带 commit、分组「开源项目」），内容拆成 `01-正文/`（PDF 按**书签**抽逐章文档）+ `02-代码/` + `03-课件/`（PDF 走附件 / PPTX 不上传）+ `04-原件（全书 PDF）/`（PDF 附件），脚手架不入库。⚠️ 抽章必须**剥 C0 控制符**（`\x00` 等会整篇被判二进制→占位，坑 50），验收要**全库**扫 `word_count>0`（六查第 6 条）。复用脚本 + 完整坑清单：`examples/llmbooks-dual-track/`（`build_lib.py`，含附件文档「预建+账本注入」手法）。

## 网站抓取导入（网页 → 语雀，2026-10-13 固化，2026-10-14 补命名规范）

触发模板：「把 `<网址>` 抓取到语雀」。规范：库名 `网站名（日期）`（日期=导入日，如 2026-10-14）、**slug 同样带日期** `网站名-YYYYMMDD`（如 atguigu-python-20261014，2026-10-14 老板定；已建库不追改）、分组「文章收集」（stack 36149506）、描述带源站 URL。通用爬虫模板 `scripts/yuque_website_crawl.py`（复制后改 SITE 配置区）+ 完整 SOP `references/website-crawl-to-yuque.md`（正文窗口定位方法论 + 图片 CDN 方案 + 产物级验证清单 + 实战案例表）。**老式 PHP 表格站（标题用 span、正文 div+table 混排）完整可复用示例：`examples/vbird-server/`**（fetch_all.py 抓页 + crawl_vbird.py 迷你 DOM 转换 + README 复用流程）。
**同站另一篇（基础学习篇）的适配版：`examples/vbird-basic/`**（crawl_basic.py；只改 4 处：BASE、章号正则加「零」、窗口加「档头部分」fallback、附录/索引伪章号 27/28/29——见坑 27/28）。
**dumi（umi）静态书站 + MathJax SVG 公式（`window.g_useSSR=true` / `div.__dumi-default-layout-content` / `umi.js`，2026-10-21 hrl.boyuai.com 实捶）**：正文全在 HTML，不用跑 JS；但**公式是 MathJax SVG 且无 TeX 源（无 alttext/无 MathML）→ 只能抽 `<svg>` 传 CDN 当图**（`upload_image` 吃 svg）；⚠️ **MathJax 伸缩符号会生成嵌套 `<svg>` → 抽 svg 必须贪婪匹配**（非贪婪会在内层 `</svg>` 截断）；`ex` 尺寸要换 `px`；正文窗口起点不能算在类名属性内部（会漏 `…">` 到首行）。转换器 + 复现命令：`examples/hrl-boyuai/`（坑 41）。
**「纯净书仓」（GitHub Pages 书站，仓库 `manuscript/` 就是站点 md 源，2026-10-22《游戏策划实务即用的 AI·Claude Code 活用法》简体中文版实战）**：根目录 `index.html` 是**全书拼一起的渲染产物，别当正文吃**，只吃 `manuscript/`；⚠️ 这类书的正文自带**内联 `<svg>`（本书 67 处手绘矢量图），语雀 markdown 导入原样保留** → **不需要**像 d2l/hrl 那样抽公式图传 CDN（反向经验）；无 `SUMMARY.md` 时 **README「完整目录」当部分名 oracle、每篇首个 H1 当标题**；目录名用 `NN-第N部分 · 中文名`、文档名 `N.M 标题.md`（**两位序号前缀让字典序天然正确，免 fix_order**）；⚠️ **标题含半角 `/` 必须换全角 `／`**（文件系统限制）；首个 H1 与文档标题重复则剥掉。见坑 52 + `examples/game-design-ai-practice/`（`build_lib.py`）。
**CSDN 博客系列（索引页 + 作品目录，微博/专栏类，`blog.csdn.net/<user>/article/details/<id>`，2026-10-22）**：正文 = `div#content_views`（广告/推荐在容器外）；标题 `h1.title-article`；代码 `<pre><code class=language-x>`；⚠️ **CSDN 反爬 = HTTP 521**（连续快速请求回 521 + 2KB 空壳）→ 退避重试且**以「响应无 `content_views`」为失败判据**；⚠️ **CSDN 的 `<table>` 常是版式盒子不是数据表**（含嵌套 table 或每行 ≤1 格 → 渲成 `> ` 引用块）；索引页无 h 标签（只有 `<p>/<strong>`），口径取**拓成全量系列**（导学目录 + 129 篇 = 163 节点，六查全绿）；坑 54 + `examples/csdn-lovelion-design-patterns/`。

**RefactoringGuru 中文站的设计模式全节（`refactoringguru.cn/design-patterns`，《深入设计模式》在线版，2026-10-22）**：HTML 结构规整（`div.section.*`/`figure.code>pre[lang]`/卡片 `a.pattern-card*`）→ bs4 递归渲染器一把；⚠️ **`<body>` 也带 `no-feature` 类**，拿祖先类名做过滤会一票否决全站（11 页被滤成 1 字节）→ 祖先检查必须排除 `body`/`html`；中文标点藏在 `span.chpuleN`、空格在 `span.chpuriN`，另有软连字符 `&shy;`；结构图有桌面/移动两张（取非 indexed）；图标即语义（优缺点 `fa-check`/`fa-times`、适用场景 `fa-bug`/`fa-bolt`、星级 `fa-star(-o)`）；图只放行 `content/` + `diagrams/`。261 页（含 22 模式 ×10 语言 = 220 篇代码示例）= 275 节点，六查全绿；坑 53 + `examples/refactoringguru-design-patterns/`。

**图灵社区开放书（`www.ituring.com.cn/book/<id>`，**Vue SPA + 隐藏 JSON API**，2026-10-22《开源软件架构》实战）**：⚠️ **页面 HTML 里没有正文**（只是 `<div id=app>` + `app.js` 外壳），真 API 在 **`api.ituring.com.cn`**——图书详情 `GET /api/book/{id}`（**book 小写**）拿 `ebook.chapters[]`，章节正文 `GET /api/Book/mini/{章节id}`（**Book 大写**）拿 `{subject, htmlOfBody}`（图灵自营书走 `/api/Book/Tupub/{id}`）；猜错路径会拿到 **200 的 SPA 外壳**（不是 404）→ 判失败看响应体有无 JSON 字段；`htmlOfBody` 是脏 HTML（`<p>` 不闭合互相嵌套）→ 含块级子元素的 `<p>` 要下钻 render；图三类历史外链（`aosabook.org/images/`→`/static/`、`raw.github.com` 图床已删→官方 static、`/download/xxx` 补 host）；`.small` 无扩展名图先改 `.png` 再传 CDN。坑 55 + `examples/ituring-aosa/`（`build.py`）。

**wizardforcel / 老 gitbooks.io 静态站（GitBook 2.x，`https://<name>.gitbooks.io/<book>/content/`，2026-10-22《让开发自动化系列专栏》实战）**：无源仓库时抓 HTML；侧栏 `ul.summary li.chapter[data-path]` 就是页面清单（**顺序=侧栏序，自动解析**）；正文容器 `section.normal`；⚠️ **gitbooks.io 间歇 401** → `fetch()` 退避重试（6 次）；正文首 H1==标题则剥；文件名 `NN-副标题.md` 序号前缀免归位；图 `img/` 相对路径边转边传 CDN。坑 56 + **可复用转换器** `examples/wizardforcel-gitbook/build.py`（换 `--base` + `--book-name` 即可导同族站，如 ibm-j-cq，2026-10-23 已实锤复用）。

**docs.huihoo.com 老站单页长文（GB2312 编码，无 h1-h6/无分页/无图，2026-10-23《GNU make 指南》实战）**：⚠️ **编码 `decode("gb2312")`**；章节是**纯文本编号标题**（`0) 介绍` / `1.2 何时分解你的项目` / `3 总结`）→ 正则识别 + 按章拆篇；⚠️ 标题可无空格（`1.1为什么使用它们?` 用 `\s*`）；⚠️ **正文引用会误中标题**（「参考下面的 2.4 节）」排除 `节）。` 结尾）；⚠️ **代码块是文本标记** `=== makefile 开始/结束 ===` 非 `<pre>`（区间识别 + **连续行攒单个围栏**，逐行围栏会碎）；⚠️ **正文伪标签** `<target> : <dependency>` 是 makefile 语法文本 → 剥标签前先保护（否则变 `: ...`）；⚠️ 站点 **522 间歇（Cloudflare）** → curl 存本地快照再解析；页眉作者/版权 → 根级 `00-译者说明.md`。坑 57 + `examples/huihoo-gmake/`（`build.py` + 本地快照）。

**UDN 开源文档 wiki（`doc.yonyoucloud.com/doc/wiki/<ns>/<book>/`，静态多页站，2026-10-23《Gradle 使用指南》实战）**：侧栏页面清单 = 每页 `div.left_title > a[href]`（**顺序 = 书序**，index 是「关于」）；正文容器 = `div.markdown-body`（紧跟着 `div.previous-and-next` 上/下篇导航，在容器外 → 天然切掉）；页面**扁平无层级** → `NN-中文标题.md` 序号前缀免归位；⚠️ **表格表头用 `<td>` 不是 `<th>`**（`<thead><tr><td>`，首行当表头）；代码 `<pre><code>` 无语言类；正文首 H1==侧栏标题则剥。37 节点（0 目录/37 文档，00-关于 + 36 章）、9 图传 CDN、六查全绿 + 37 篇逐篇回读 0 差；库 84898768，slug `gradle-guide-20261023`。坑 59 + `examples/udn-gradle/build.py`。

**整站下线且原站域名已死 / archive.org 被墙（HTTP 000）/ 快照只存 Wayback 链接（`local.joelonsoftware.com` wiki 页，《Joel on Software》中译本，2026-10-23）**：走 **Common Crawl 取原页**（`index.commoncrawl.org` 按 URL 查 → `data.commoncrawl.org` Range 拉 `.warc.gz` → gunzip 剥两层头得原页 HTML，取 2017 年那批 `CC-MAIN-2017-26`）；⚠️ 本例是 **MediaWiki Monobook 皮肤**，正文容器是 **`div#bodyContent`**（`div#mw-content-text` 只在 Vector 皮肤存在，别混）；按 `<h2>` 拆篇、丢 `#toc` 目录 table；⚠️ 正文字面 `<a>` 要转义；⚠️ CC **不收录图片**（5 张插图只能丢）；⭐ **archive.org 被墙时 CC 是同一批人马的可靠平替**（与坑 36 同族）。见坑 60 + `examples/joel-wiki/`。

**整站下线且域名已被停放（body 是 `[域名] is for sale` 的 1~2KB 页）**：CC 拿正文后**先搜 GitHub 同源镜像仓库**（`gh search repos <域名>`）——站长常把翻译/生成源推上去，`index.md`（标题 oracle）+ `images/`（配图）都能白拿，图就不用认栽（2026-10-20 sketchcn.com《Sketch 中文用户手册》实战，44/44 图救回；坑 37 + `examples/sketchcn/`）。

**整站下线（域名单跳厂商新站 + 反爬 403，archive.org 又被墙）**：走 **Common Crawl 兜底**——`index.commoncrawl.org` 用 **prefix 查询**拿 WARC 坐标（filename/offset/length）→ `data.commoncrawl.org` Range 拉 `.warc.gz` → gunzip 剥两层头得原页 HTML（老论坛看 **2018-2019** 快照，2013-2014 常空）。Jive/DECN 类社区正文在 `<!-- [DocumentBodyStart:…] -->`+`div.jive-rendered-content`，项目符 `ü/Ø/•/–` 是**字面字符**；附件图多半 CC 未收录（只能靠第三方转载镜像救）。复用脚本 + README 见 `examples/emc-community-cc/`（2026-10-18《SAN 管理入门系列》实战，8 篇，坑 36）。

```bash
python3 scripts/yuque_repo_import.py create-book --name "<网站名>（<日期>）" --slug <网站名>-<YYYYMMDD> --desc "<源站 URL> | 导入 <日期>"
python3 scripts/yuque_repo_import.py move-stack --book-id <book_id> --stack-id 36149506
```

核心铁律：**先剥 script/style 再切窗；窗口终点用标签形式标记（禁裸字符串 find）；链接重写正则 group(1)=文字 group(2)=URL；验证只看产物不看日志**。

## TOC 目录整理（平铺 → 分组，2026-10-13 固化）

网站抓取默认平铺，老板要求按章节建目录。`scripts/yuque_toc_organize.py --book <id> --plan <plan.json>`：建根级 TITLE 分组（sibling 模式防坏节点）→ node_uuid 形式移文档 → GET /toc 复查。plan.json 见脚本 docstring。坑：响应里根节点 parent_uuid 是 null 不是 ""；removeNode 只认 sibling（传 child 报 invalid action）；复用分组也要进 created_groups 列表（复查 zip 对齐）。

## 小说导入（txt / epub，2026-10-14 并入）

触发模板：「把这本小说导入语雀」「这本书导入语雀」（本地 txt/epub 文件）。完整 SOP：`references/novel-txt-epub-to-yuque.md`（必读）。

```bash
# 建新库 + 导入 + 修 TOC（epub 书名/作者/简介从元数据自动带出）
python3 scripts/yuque_novel_import.py --file /path/to/novel.epub --create
python3 scripts/yuque_novel_import.py --txt /path/to/novel.txt --title "书名" --author "作者" --description "简介"
# 已有库续导（进度按 book_id 隔离，自动断点续传）
python3 scripts/yuque_novel_import.py --txt novel.txt --book-id <book_id>
# 只预览章节（导入前必做，确认切分正确）
python3 scripts/yuque_novel_import.py --txt novel.txt --dry-run
```

- 链路：mcporter + yuque-mcp（非 HTTP 直连，无需 TOKEN_L91）；依赖 OpenClaw 环境已配 yuque-mcp
- 导入前先 `--dry-run` 看章节预览，再正式导；导入后自动校验内容（乱码/HTML 残留）并修 TOC
- 大文件分批：`--start 1 --end 200` 续导；中途断网重跑同命令即续传
- 回归单测：`cd scripts && python3 test_novel_toc_fix_retry.py`（5 项，不联网）

## 使用方式

一句触发：「把 X 目录整棵导入语雀知识库 Y」「按目录结构建库」「把 X 仓库按开源项目流程到语雀」「把 X 小说导入语雀」。执行：dry → test → 全量（后台+进度心跳）→ 对账 → 验收汇报。开源项目类走 `references/github-repo-to-yuque.md` SOP，小说类走 `references/novel-txt-epub-to-yuque.md` SOP。