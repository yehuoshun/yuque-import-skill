# 语雀 TOC / 文档 API 要点（实战验证 2026-10-05）

> 基地址：`https://www.yuque.com/api/v2`，认证头：`X-Auth-Token: <token>`

⚠️ **cookie Web API 写侧账号级风控（2026-10-27 fpb52 #56/#57 系统性实证，20+ 次重试未愈）**：`PUT /api/mine/book_stack/move` **恒返 200 + `{}` 静默不落位**（非 429、无限流头、config ctoken==cookie 内 ctoken 排查过 CSRF）——move-stack 验证全败，22 个库待归位。同刻附件上传 429、**GET book_stacks 正常、v2 写（改描述/toc-md 导入）完全正常** → 只有 cookie Web API 写侧被控。**系统性佐证**：并发 3 库（85028586/85028477/测试库 85029508）同刻同病；但历史库分组正常（10-12 前都能移）→ 当日故障，非长期行为。**判别三件套**：① PUT 恒 200{} + 回查 book_stacks 不落位；② 多库并发同病；③ v2 GET/PUT 正常作对照组。**处置**：内容链路（导入 toc-md）走 v2 不受影响 → **先导内容、move-stack 后补**（move 幂等，后补无副作用）；窗口未观测到自愈（≥1 天），隔日重试 `move-stack --book-id <id> --stack-id <sid> --no-wait`。

⚠️ **cookie 类登录态会无声过期（2026-10-24 实捶）**：文件在 ≠ 登录在——`config.json` 里的 cookie/ctoken 可能已失效（响应 401/跳登录），文件时间戳还是旧的。脚本不会主动告诉你过期。**每小时轮次是发现它的唯一探针**（跑库时 v2 API 正常但 Web API（上传/batchMove）全 401 就该警觉）；连续多轮同一错误 = 该换凭据了，别再等。

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
- **撞 429「Too Many Requests」= 小时配额（5000/h）烧完了，不是高频抖动**（2026-10-18 实战：验收脚本分页死循环 9 分钟，把一小时额度刷光 → 之后全 429，响应头 `x-ratelimit-remaining: 4999` 表示窗口已重置）。**配额是整点刷新**（2026-10-18 实测；脚本已内置 `wait_quota_reset(pad=60)`：撞 429 自动等到「**下一个整点 + 60 秒**」再重试（老板 2026-10-18 定：留 1 分钟余量，防网络波动导致整点没刷上），同进程只等一次，之后仍 429 走短退避最终 raise。
  ⚠️ **2026-10-27 实测修正：reset 点不一定是整点（疑似按授权时刻滚动的 1h 窗口）**——fpb52 #56/#57 并行时 12:00-13:00 段耗尽后，13:00 整点并未恢复，实测 13:45 左右才 reset（13:46 探测 `x-ratelimit-remaining: 4995` 满血）。**等整点是安全保守做法（多等无害），要精确就读取 429 响应的 `Retry-After`（秒）/ `x-ratelimit-reset` 头**；429 三分法见 `classify_429`（高频秒级/配额耗尽/附件无头风控）。教训：自己写的验收/遍历脚本要先小样本跑通再全量，别写出死循环刷接口。
- 单文档 body 上限 4MB（2026-10-06 Shadowbus 实战确认）：>4MB 报 HTTP 400 `body is too large`。文本超 512KB 即自动多段拆分（标题 `xxx (1/N)`/`(2/N)`，**按语义边界切分，禁硬拆**（2026-10-14 老板：硬拆影响观感）：JSON 顶层数组→按条目边界（每段是完整记录组成的可解析 JSON）；其余→按行边界（绝不切破行，单行自身超限才硬切）；每段头带范围注记（条目区间+首条名 / 行区间）。内容零丢失；阈值 `--max-body` 可调，**默认 512KB，2026-10-14 老板拍板：1MB 语雀端加载也要等很久**；上限别碰 4MB——语雀端直接打不开。后期渲染仍卡再调小）；二进制文件（如 PNG）会被 `errors=replace` 文本化膨胀放大（3.4MB PNG → 6MB body），**图片类已改走 Web API 上传 CDN**（`POST /api/upload/attach?type=image`，需 Cookie + ctoken + Referer/Origin 头，图片上限 20MB），非图片二进制自动占位说明
- walk 不排除 .git：clone 的仓库直接导入会把 .git 也导进去，先 rsync/cp 排除 .git 或用干净副本
- **toc-md 收尾后根级 DOC 归位（`prependNode` + `action_mode=sibling`）偶发不生效**：响应回显正常（返回整棵 TOC 快照）但**实际顺序未变**——怀疑 TOC 写队列积压（同「新建空目录挂子静默失败」同源）。**铁律：每次移动后都 GET /toc 回读校验，不生效就重试 1~2 次（间隔 3~5s）**。2026-10-18 实战：ELKstack 一次成功、Logstash 最佳实践第一次没动、第二次成（同一脚本同一姿势）
- **根级 TITLE/DOC 混排时 DOC 整批落到 TITLE 之后（同一天 Mastering ES 实战，补上面这条）**：toc-md 走「先建 DOC 挂根、后由目录树生成 TITLE」→ 根级**既有目录又有文档**时，所有根级 DOC 会被顶到全部 TITLE 后面（本次根级 10 项：目录 01/02/04/05 在前，文档 03/06/07/08/09 全在后；PUT 0.6s 成功、结构核对也 PASS，**但顺序是错的**——结构核对不查同层相对顺序）。**归位手法**：逐发 `prependNode`，`node_uuid` = 错位的那篇 DOC，`target_uuid` = **它应在位置的下一个目录**，`action_mode:sibling`（把 DOC 插到该目录前）。本次 `03-索引底层控制.md` prepend 到 `04-探究分布式索引架构` 前，一发归位为 00→09 正序；每发后 GET /toc 校验（沿用上面的重试铁律）。⚠️ 所以验收脚本的「根级顺序」断言要**同时比集合和顺序**，别只查「根级首项是不是前言」
- **TOC 节点是否带 doc_id 因库而异**：2026-10-18 ESDG 库（84706781）的 TOC 节点 `id`/`doc_id` 都是空串；同日的 ELKstack（84707435）/LBP（84707547）却带真实 doc_id（如 288667688）。稳妥做法不变：正文回读一律取导入账本 `progress.json` 的 `doc_id`
- **429 处理已升级（2026-10-26，`scripts/yuque_tree_import.py` + `web_api()`）**：旧实现是「**进程内只等一次整点**」的布尔——等过一次后再撞 429 就掉进短退避 → `raise "retries exhausted"` → 节点进入 10/20/30 分钟静置后**记 fail**（2026-10-26 rea 主库实捶：17:29 二次 429 后只能 kill 重启，靠账本断点续传救回）。现改为按响应头决策的多轮等待：
  1. `X-RateLimit-Remaining: 0` ⇒ 判为**小时配额** → `wait_quota_reset()`，**可重复跨整点等待**，上限 `--quota-max-waits`（默认 12，超出才 raise）；
  2. `Retry-After <= 30` ⇒ 秒级限速，按它睡；
  3. `Remaining > 0` ⇒ 秒级限速，短退避（计 retries）；
  4. **无任何限流头** ⇒ 先 `probe_remaining()`（`GET /user` 读头）探测：`0` 才当配额，否则短退避——**避免把瞬时 429 误判成小时配额白睡一小时**。
  - 关键点：**配额等待不消耗 retries 预算**；等完加 `0–15s` 随机抖动，错开并行/多进程同时苏醒再撞配额。`web_api()`（batch 模式，cookie 路径）同步升级。
  - 实测（本地 429 假服务 + 真 `api()`）：`Remaining:0` 连续两次 429 → 两次等待后成功；无头 429 探测额度未耗尽 → 短退避不盲等；持续 429 到上限 → 正常 raise。
