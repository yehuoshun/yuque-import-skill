# yuque-import-skill

语雀知识库**全量目录导入** skill：把本地目录树整棵搬进语雀，文件夹=目录节点、文件=文档，层级与磁盘一致。

数据源全家桶（2026-10-14 起）：目录树 / GitHub 开源项目 / 网站抓取 / **本地小说 txt·epub**（原 fanqie-novel-to-yuque 仓库并入，见 `references/novel-txt-epub-to-yuque.md`）。

## 为什么有它

语雀 v2 API 的目录（TOC）模型坑很多：文档创建后不进目录、根节点 parent_uuid 是空串、挂载/移动全靠一个 PUT /toc 接口。直接手写极易翻车——3921 节点实战中踩了「中断丢批→45 文档挂根」「路径重建丢前缀→全量误报」两个大坑，全部固化成脚本+规则。

## 用法

```bash
# 1. 导入（dry → test → 全量）
python3 scripts/yuque_tree_import.py --root <本地目录> --book <知识库ID> --progress ./progress.json --dry
python3 scripts/yuque_tree_import.py --root <本地目录> --book <知识库ID> --progress ./progress.json --test 6
python3 scripts/yuque_tree_import.py --root <本地目录> --book <知识库ID> --progress ./progress.json

# 2. 对账修复（导入后必做）
python3 scripts/yuque_toc_reconcile.py --root <本地目录> --book <知识库ID> --progress ./progress.json
python3 scripts/yuque_toc_reconcile.py --root <本地目录> --book <知识库ID> --progress ./progress.json --fix

# 3.（可选）GitHub 开源项目 → 语雀 固化流程
#    库名 = 项目名（commit id），分组 = 开源项目（stack 57018723）
python3 scripts/yuque_repo_import.py prep        --url git@github.com:xxx/yyy.git --dir /path/to/work
python3 scripts/yuque_repo_import.py create-book --name "yyy（abc12345）" --slug yyy-abc12345 --desc "https://github.com/xxx/yyy @ abc12345"
python3 scripts/yuque_repo_import.py move-stack  --book-id <知识库ID> --stack-id 57018723

# 4. 占位文档修复（二进制误判事故善后，2026-10-12）
#    旧版 hi-byte>0.9 启发式曾把中文密集文本误判为二进制 → 正文丢失；v1.1.3 已删启发式
#    已受损库用 TOC 路径映射回填真实内容：
python3 scripts/yuque_repair_placeholders.py --book <知识库ID> --source <本地源目录>
python3 scripts/yuque_repair_placeholders.py --book <知识库ID> --github <owner/repo> [--prefix <子目录>]
# 完整 SOP：references/github-repo-to-yuque.md

# 5.（2026-10-13）批量编排 + GitHub Actions 全自动（手动触发, 快照制）
#    repos.json 清单 → 账本去重（commit 没变跳过）→ 建库/移分组/导入/四查/钉钉汇报
python3 scripts/yuque_import_all.py --repos repos.json --ledger last-imported.json \
    --workdir /home/admin/.openclaw/workspace/tmp --dry --no-notify   # 本地试跑
#    GitHub 页面 Actions → yuque-import → Run workflow（不设 schedule, 2026-10-13 老板拍板）

# 6.（2026-10-14）本地小说 txt/epub → 语雀（原 fanqie-novel-to-yuque，已并入）
#    完整 SOP：references/novel-txt-epub-to-yuque.md
python3 scripts/yuque_novel_import.py --txt /path/to/novel.txt --title "书名" --author "作者"   # 自动建库+导入+修TOC
python3 scripts/yuque_novel_import.py --file /path/to/novel.epub --create                     # epub 元数据自动带书名
python3 scripts/yuque_novel_import.py --txt novel.txt --book-id <book_id> --dry-run             # 只预览章节
```

Token：环境变量 `TOKEN_L91`（或 `~/.openclaw/secrets/credentials.env`），脚本不硬编码。
小说模块（`yuque_novel_*`）例外：走 mcporter + yuque-mcp 链路，不需要 token。

## 结构

```
SKILL.md                    主文件（硬规则+流程+坑）
references/api-notes.md     API 要点 + 实战事故复盘
scripts/
  yuque_tree_import.py      导入（DFS 先序、断点续传、每节点落盘）
  yuque_toc_reconcile.py    对账修复（路径重建、错位移动）
  yuque_repo_import.py      GitHub 开源项目 wrapper（prep/create-book/move-stack）
  yuque_repair_placeholders.py  占位文档回填修复（二进制误判事故善后）
  yuque_website_crawl.py    网站抓取通用模板（正文窗口定位 + 图片传 CDN）
  yuque_toc_organize.py     TOC 目录整理（平铺 → 分组, plan.json 驱动）
  yuque_rst_convert.py      Sphinx/reST 工程 → Markdown（docutils 中间层, 2026-10-13）
  yuque_import_all.py       批量编排器（清单/账本/四查/钉钉, GitHub Actions 用）
  yuque_novel_import.py     小说 txt/epub 导入（解析+上传+进度+自动修TOC, 2026-10-14 并入）
  yuque_novel_epub_reader.py  EPUB 解析后端（container→OPF→spine→xhtml→章节, 纯标准库）
  yuque_novel_content_check.py  正文校验（字数/HTML残留/乱码/章节报告）
  yuque_novel_toc_fix.py    小说 TOC 顺序修复（对比章节列表, 从后往前移, 带重试）
  test_novel_toc_fix_retry.py   小说 TOC 修复重试回归单测（不联网, 5 项）
repos.json                  开源项目导入清单（url/enabled/watch）
last-imported.json          导入账本（commit/book_id/book_url[slug 形式, 2026-10-13 起不含 username], 成功才更新）
.github/workflows/
  import-repos.yml          开源项目批量导入（workflow_dispatch, 账本去重+镜像缓存）
  notify.yml                钉钉事件通知（仓库标配）
references/
  github-repo-to-yuque.md   开源项目导入 SOP + 坑清单（2026-10-12 老板固化）
  website-crawl-to-yuque.md 网站抓取导入 SOP + 窗口定位方法论（2026-10-13 固化）
  novel-txt-epub-to-yuque.md 小说 txt/epub 导入 SOP + 章节识别规则 + 坑（2026-10-14 并入）
```

## 验证记录

- 2026-10-05：sts2-res（sts2.dll 反编译源码）3921 节点 → 语雀「sts2-0.107.1（杀戮尖塔2）」知识库，零重复零缺失零错位

## 相关项目

- [cnblogs-to-yuque](https://github.com/yehuoshun/cnblogs-to-yuque)：博客园文章 → 语雀自动采集（GitHub Actions 定时，RSS → 全文 → Markdown → 传图 CDN → 建文档 → state.json 去重）。同属「内容 → 语雀」工具族：它管单站定时采集，本 skill 管批量/手动导入（目录树、GitHub 开源项目、网站抓取、小说文件），共享语雀 v2 API 链路（建文档、attach 传图、去重账本）。
- [fanqie-novel-to-yuque](https://github.com/yehuoshun/fanqie-novel-to-yuque)：~~独立仓库~~ **已于 2026-10-14 并入本 skill**（scripts/yuque_novel_* + references/novel-txt-epub-to-yuque.md）。原仓库保留仅供历史参考，新改动一律进本 skill。