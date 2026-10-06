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

## 批量导入注意

- 断点文件建议放工作目录外（如 tmp/），每节点一次 `os.replace` 原子落盘
- 语雀无严格 QPS 限制，但 429 偶发，指数退避 2^n×1.5s + 1s，4 次重试足够
- 单文档 body 上限 4MB（2026-10-06 Shadowbus 实战确认）：>4MB 报 HTTP 400 `body is too large`。文本超 2MB 即自动多段拆分（标题 `xxx (1/N)`/`(2/N)`，每段 ≤2MB 留 JSON 转义余量，内容零丢失）；二进制文件（如 PNG）会被 `errors=replace` 文本化膨胀放大（3.4MB PNG → 6MB body），已自动占位说明
- walk 不排除 .git：clone 的仓库直接导入会把 .git 也导进去，先 rsync/cp 排除 .git 或用干净副本