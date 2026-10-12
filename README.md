# yuque-import-skill 🦞

语雀知识库**全量目录导入** skill：把本地目录树整棵搬进语雀，文件夹=目录节点、文件=文档，层级与磁盘一致。

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
```

Token：环境变量 `TOKEN_L91`（或 `~/.openclaw/secrets/credentials.env`），脚本不硬编码。

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
references/
  github-repo-to-yuque.md   开源项目导入 SOP + 坑清单（2026-10-12 老板固化）
  website-crawl-to-yuque.md 网站抓取导入 SOP + 窗口定位方法论（2026-10-13 固化）
```

## 验证记录

- 2026-10-05：sts2-res（sts2.dll 反编译源码）3921 节点 → 语雀「sts2-0.107.1（杀戮尖塔2）」知识库，零重复零缺失零错位