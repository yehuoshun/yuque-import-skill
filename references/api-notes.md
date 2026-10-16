# 语雀 TOC / 文档 API 要点（实战验证 2026-10-05）

> 基地址：`https://www.yuque.com/api/v2`，认证头：`X-Auth-Token: <token>`

## 根节点判定（最容易翻车的点）

- TOC 返回的**根级节点 `parent_uuid` 是空串 `""`，不是 null、不是缺失**
- 判断根：`if not n.get("parent_uuid")`（空串为 falsy）✅
- 之前错误写法 `n["parent_uuid"] is None` → 全量误判挂根

## TOC 节点字段（V2TocItem）

| 字段 | 说明 |
|------|------|
| uuid | 节点唯一 ID（移动/编辑/删除都用它） |
| type | DOC=文档 / LINK=外链 / TITLE=分组标题 |
| title | 节点名称 |
| doc_id | type=DOC 时的文档 ID |
| parent_uuid | 父节点 uuid，空串=根 |
| prev_uuid / sibling_uuid / child_uuid | 同级前/后、首个子节点 |

## 文档 CRUD

- 创建：`POST /repos/{book_id}/docs`，body `{"title":"xx.cs","format":"markdown","body":"...markdown..."}` → 返回 `data.id`
- 读：`GET /repos/{book_id}/docs/{id}`（id 支持 slug）
- 改：`PUT /repos/{book_id}/docs/{id}`
- 删：`DELETE /repos/{book_id}/docs/{id}`

⚠️ **create_doc 创建的文档不会自动进 TOC**，必须手动 appendNode 挂载，否则文档存在但目录树里看不到。

## TOC 节点操作（PUT /repos/{book_id}/toc）

创建分组：`{"action":"appendNode","action_mode":"child","type":"TITLE","title":"目录名","target_uuid":父uuid(根可省)}`
创建文档节点：`{"action":"appendNode","action_mode":"child","type":"DOC","doc_ids":[id],"target_uuid":父uuid}`
移动节点：`{"action":"appendNode","action_mode":"child","target_uuid":新父uuid,"node_uuid":当前uuid}`
删除（含子）：`{"action":"removeNode","action_mode":"child","node_uuid":...}`

返回完整 TOC 数组，可立即校验（find_node 按 parent_uuid+title/doc_id）。

## 路径重建（对账用）

```python
def build_path_map(toc):
    by_uuid = {n["uuid"]: n for n in toc}
    m = {}
    for n in toc:
        parts, cur = [], n
        while True:                      # 先加自己，再上移查父
            parts.append(cur["title"])
            if not cur.get("parent_uuid"):
                break
            cur = by_uuid[cur["parent_uuid"]]
        m[n["uuid"]] = "/".join(reversed(parts))
    return m
```

## 导入事故复盘（2026-10-05，3921 节点实战）

| 事故 | 根因 | 修复 |
|------|------|------|
| 45 文档挂根 | 导入进程中断，最后一批「已创建未记账」；重跑时父目录未在账本 → 挂根 | 对账脚本移动归位 |
| 全量误报错位(3693) | 路径重建从「父」开始拼，根 TITLE 前缀丢失 | 改「先加自己再上移」 |
| 重复 TITLE(eng×2) | 中断+重跑，父目录重复创建 | removeNode 清孤儿 |

## 高频连续创建 → TOC 写路径积压（2026-10-07 实验证实）

- **现象**：几百个节点不间断高频创建后，新建空 TITLE 目录 appendNode 子节点静默失败——响应里 parent_uuid 正确（乐观回显），实际 GET 节点在根；或响应里根本找不到节点。老目录（已有子）挂载始终正常。
- **复现**：高频创建 50 节点后探针即失败；`GET /toc` 与 `GET /api/catalog_nodes`（Web 目录）两套 API 读出一致的“挂根/不存在”，Web 单节点/批量 move 也假成功（返回 success 实际不动）。
- **自愈/规避**：停止写入静置 ~10 分钟恢复（5/5 探针通过）；降速（每请求间隔 1.5s + 每 100 节点休息 45s）1000 节点 0 失败。与 TOC 总量上限（5000）无关，与库无关（两个全新库同样复现）。
- **限速对象（2026-10-16 rea 全库实测确认）**：只有 TOC 写动作（appendNode / removeNode / moveNode / prependNode 等 `PUT /toc` 系列）需要降速——它们走串行队列，灌快了假成功挂根；**doc 层（create_doc / PUT /docs 正文回灌）走独立存储服务，不受 TOC 队列影响，可以连续/并行造**（rea 单 4048 doc 全建成、仅 TOC 挂载失败，5 个幽灵全是 create 成功+挂载失败的孤儿）。推论：理论上可生产-消费并行——create_doc 多 worker 连续跑 → doc_id 入队 → 单线程慢速 appendNode（挂载端绝不并行，并行=排队=更快挤爆）。
- **真批量端点（2026-10-16 老板抓包 + 实测确认）**：Web 内部 API `PUT /api/catalog_nodes/batch`（Cookie 认证：cookie + x-csrf-token(=yuque_ctoken) + x-login，body `{"batch_action":"batchMove","node_uuids":[...],"target_uuid":...,"book_id":N,"target_book_id":N,"transfer_action":"prependChild","insert_to_catalog":true}`）一次移动 N 个节点。v2 `PUT /toc` 无批量（数组 body 422）；MCP `yuque_batch_update_toc` 是 for 循环假 batch；无 batchCreate（只有 batchMove）。**实测语义**：① 服务端「整体插到目标最前、保持数组内顺序」——传正序得正序（分片 1→2→3）；② 同父分批 flush 后批会插到前批前（乱序）→ 必须「逆序逐片 flush」；③ 批内节点顺序保持 = 目录/文件 DFS 序无需反转。已落地 `yuque_tree_import.py --batch-mode`（挂根攒批 + batchMove 归位 + 校验降级 + 中断恢复）。
- **处置**：脚本已内置 `--pend-sleep` 失败静置重试（默认 600s 递增退避(10/20/30 分钟)×3 轮）；残留同名节点由 cleanup_leftover 自动清理；极端情况（父子嵌死锁）用 Web 前端拖拽或重建子树。

## 官方 v2 能力核实（2026-10-16，来源 OAS `yuque_openapi_20260722.yaml` v2.0.1）

- **一次性设目录**：`PUT /api/v2/repos/{book_id}` body **`toc` 字段 = Markdown 目录树**（原文「可利用此字段批量更新知识库的目录」）。已落地为 `yuque_tree_import.py --toc-md`（推荐默认）
- `POST /repos/{book}/docs` 建文档后**自动挂到 TOC 根**（不再需要逐个 appendNode）
- **TOC 事务**：`PUT /api/v2/repos/{book_id}/toc` 单节点，`action` = `appendNode`(尾插)/`prependNode`(头插)/`editNode`/`removeNode`，`action_mode` **必填** = `sibling`/`child`；**removeNode + child = 连子节点一起删**（sibling = 只删当前）；**「删除节点不会删除关联文档」**（幽灵 doc 得另走 `DELETE /docs/{id}`）
- `target_uuid` 不填**默认根节点**；`node_uuid` 移动/更新/删除必填；`doc_id` 已 deprecated → 用 `doc_ids`
- **限流（官方 Overview 文档）**：每小时 5000 次、每秒 100 次，**同账号所有 Token 共享**，响应头 `X-RateLimit-Limit/Remaining`
- 官方 v2 无 batch 路径；`/api/catalog_nodes/batch`（batchMove）是 Web 内部 API，不在 OAS 里
- **batchMove 响应体 = 完整 TOC 快照**（`{"meta":{...},"data":[全 TOC 节点, 带 parent_uuid/prev_uuid/sibling_uuid/level]}`）——可直接拿来核位，无需再 GET /toc；单次 200 节点实测正常（无 100 上限）
- **删库**：`DELETE /api/v2/repos/{id}` 有效（Web `DELETE /api/books/{id}` 不存在）

## 批量导入注意

- 断点文件建议放工作目录外（如 tmp/），每节点一次 `os.replace` 原子落盘
- 语雀无严格 QPS 限制，但 429 偶发，指数退避 2^n×1.5s + 1s，4 次重试足够
- 单文档 body 上限 4MB（2026-10-06 Shadowbus 实战确认）：>4MB 报 HTTP 400 `body is too large`。文本超 512KB 即自动多段拆分（标题 `xxx (1/N)`/`(2/N)`，**按语义边界切分，禁硬拆**（2026-10-14 老板：硬拆影响观感）：JSON 顶层数组→按条目边界（每段是完整记录组成的可解析 JSON）；其余→按行边界（绝不切破行，单行自身超限才硬切）；每段头带范围注记（条目区间+首条名 / 行区间）。内容零丢失；阈值 `--max-body` 可调，**默认 512KB，2026-10-14 老板拍板：1MB 语雀端加载也要等很久**；上限别碰 4MB——语雀端直接打不开。后期渲染仍卡再调小）；二进制文件（如 PNG）会被 `errors=replace` 文本化膨胀放大（3.4MB PNG → 6MB body），**图片类已改走 Web API 上传 CDN**（`POST /api/upload/attach?type=image`，需 Cookie + ctoken + Referer/Origin 头，图片上限 20MB），非图片二进制自动占位说明
- walk 不排除 .git：clone 的仓库直接导入会把 .git 也导进去，先 rsync/cp 排除 .git 或用干净副本