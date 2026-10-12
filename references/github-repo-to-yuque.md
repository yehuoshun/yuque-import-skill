# GitHub 开源项目 → 语雀导入 SOP（2026-10-12 老板固化）

> 触发模板：「把 `<repo>` 按开源项目流程到语雀」——repo 可给 https 或 `git@` SSH 链接。
> 实战记录：HowToCook / kairisei-ma-ch / STS2 全家桶 / legado / deepwrite×3 / owllook / Git-Cheat-Sheet 等 20+ 项目。

## 一、规范（老板定，不要改）

| 项 | 值 |
|---|---|
| 知识库名 | `项目名（commit id）`，commit 取 8 位短哈希，如 `deepwrite（85577e7）` |
| slug | `项目名-commit`（全小写，如 `deepwrite-85577e7`） |
| 描述 | `<repo url> @ <commit>`（如 `https://github.com/swjybky/deepwrite @ 85577e7`） |
| 知识库分组 | **开源项目**（stack id `57018723`） |
| 归属 | 私人空间 yehuoshun 下（`/users/yehuoshun/repos`） |
| 可见性 | private（public=0） |
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
   - move-stack 内置 10s 等待（新建库立刻移动会失败，2026-10-12 实踩）+ 移动后自动验证分组
4. **test 6 试水** → 全量导入（**后台跑**，禁 nohup——exec-guard 会拦；用 exec `background=true`）
   ```bash
   python3 scripts/yuque_tree_import.py --root <clean_dir> --book <book_id> \
     --progress /home/admin/.openclaw/workspace/tmp/<repo>-<commit>-progress.json --test 6
   # 全量: 同命令去掉 --test，输出重定向到 workspace/tmp/<repo>-<commit>-import.log
   ```
5. **心跳汇报**：25% / 50% / 75% / 完成，各报一次（读 progress 账本算百分比）
6. **对账**：`python3 scripts/yuque_toc_reconcile.py --root <clean_dir> --book <book_id> --progress <账本> [--fix]`
7. **验收四查**（缺一不可）：
   - TOC 节点数 == 本地节点数
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

## 四、wrapper 子命令速查

```
yuque_repo_import.py prep         --url <git-url> --dir <工作目录>
yuque_repo_import.py create-book  --name <项目名（commit）> --slug <项目名-commit> --desc <url @ commit> [--login yehuoshun] [--stack-id 57018723]
yuque_repo_import.py move-stack   --book-id <id> --stack-id 57018723 [--wait 10] [--no-wait]
```

token 来源同主脚本：环境变量 `TOKEN_L91` 或 `~/.openclaw/secrets/credentials.env`；cookie 默认读
`skills/yuque-ai-mcp/config/config.json`（可用 `--cookie-config` 覆盖）。
