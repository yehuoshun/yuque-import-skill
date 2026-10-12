---
name: yuque-import-skill
description: 语雀知识库全量目录导入与对账修复技能。把本地目录树整棵导入语雀（文件夹=TITLE 目录节点、文件=文档，DFS 先序保持层级，断点续传），导入后对账修复错位节点。当用户要求「把这个目录/代码库/资料树导入语雀」「按目录结构建语雀知识库」「把 GitHub 项目/开源仓库导入语雀」「按开源项目流程到语雀」「语雀导入遇到挂错层级/重复节点」时使用。
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
- 内容格式：`.md` 原样 / `.cs` → ` ```csharp ` 代码块 / 其余 → 纯文本代码块
- 超限自动处理：二进制（NUL/无效 UTF-8 占比高）→ 图片类（png/jpg/gif/webp/svg…）自动上传语雀 CDN 并 `![文件名](cdn_url)` 嵌入（需 cookie/ctoken，见 `--cookie-config`）；非图片 → 占位说明；文本超 2MB → 自动拆成多文档 `xxx (1/N)` `(2/N)` …，内容零丢失
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

---

## API 速查（详见 references/api-notes.md）

| 操作 | 方法/路径 | 关键参数 |
|------|----------|---------|
| 创建文档 | POST `/repos/{book}/docs` | title, format=markdown, body（≤4MB，超 2MB 自动分段） |
| 挂载/移动/删除节点 | PUT `/repos/{book}/toc` | action: appendNode/prependNode/editNode/removeNode; action_mode: sibling/child; type: DOC/TITLE/LINK |
| 建分组 | PUT toc | action=appendNode, action_mode=child, type=TITLE, title=分组名 |
| 知识库分组（书架 stack）移动 | PUT `/api/books/{id}` body `{"stack_id": 数字}` | stack_id 是语雀分组（书架）ID，非 TOC 分组；需 cookie/ctoken 认证（v2 token 不支持） |
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
- 同名文件在不同路径（如 eng/orbs.json 与 zhs/orbs.json）：语雀自动处理，实测无冲突

## 开源项目导入（GitHub repo → 语雀，2026-10-12 老板固化）

触发模板：「把 `<repo>` 按开源项目流程到语雀」。规范：库名 `项目名（commit id）`、分组「开源项目」（stack 57018723）、描述 `<url> @ <commit>`。

```bash
# 1. 克隆/更新 + 干净副本 + 节点数
python3 scripts/yuque_repo_import.py prep --url <git-url> --dir /home/admin/.openclaw/workspace/tmp
# 2. dry-run 核数 → 3. 建库 → 4. 移分组（内置等待+验证）
python3 scripts/yuque_repo_import.py create-book --name "<项目名>（<commit>）" --slug <项目名>-<commit> --desc "<url> @ <commit>"
python3 scripts/yuque_repo_import.py move-stack --book-id <book_id> --stack-id 57018723
# 5. test 6 → 全量（后台+心跳 25/50/75/完成）→ 对账 → 验收四查
python3 scripts/yuque_tree_import.py --root <clean_dir> --book <book_id> --progress <账本> --test 6
```

完整 SOP + 坑清单：`references/github-repo-to-yuque.md`（必读，含 7 条踩过的坑）。

## 使用方式

一句触发：「把 X 目录整棵导入语雀知识库 Y」「按目录结构建库」「把 X 仓库按开源项目流程到语雀」。执行：dry → test → 全量（后台+进度心跳）→ 对账 → 验收汇报。开源项目类走 `references/github-repo-to-yuque.md` SOP。