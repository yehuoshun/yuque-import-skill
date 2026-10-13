# 小说（TXT / EPUB）→ 语雀 导入 SOP

> 来源：原 fanqie-novel-to-yuque 仓库，2026-10-14 并入 yuque-import-skill 成为小说数据源模块。
> 本地小说 **txt / epub 文件** → 解析章节 → 自动创建语雀知识库 + 批量导入 + TOC 排序修复。

## 定位

- 本模块管**本地小说文件**（txt/epub）导入，数据源是文件，零网络抓取。
- 与目录树导入（`yuque_tree_import.py`）的区别：小说按「章节」而非「文件树」组织，解析层完全独立（章节标题正则 + epub spine）。
- 调用链路：走 **mcporter + yuque-mcp**（OpenClaw 环境已配置），与 skill 其它脚本的 HTTP 直连（TOKEN_L91）链路并存，互不干扰。

## 依赖

- **mcporter** + **yuque-mcp**（OpenClaw 管理，已配好）
- 纯 Python 标准库，无第三方包（含 epub 解析）
- token：不需要（yuque-mcp 自带认证）

## 使用

### 完整流程（推荐）

自动创建语雀知识库 → 解析章节 → 批量导入 → 修复 TOC：

```bash
python3 scripts/yuque_novel_import.py \
    --txt /path/to/novel.txt \
    --title "书名" --author "作者" --description "简介"
```

epub 的书名/作者/简介可从元数据自动带出，`--create` 时可不传：

```bash
python3 scripts/yuque_novel_import.py --file /path/to/novel.epub --create
```

### 分步操作

```bash
# 只解析不导入（预览章节列表）
python3 scripts/yuque_novel_import.py --txt novel.txt --dry-run

# 导入到已有知识库（--book-id 或环境变量 BOOK_ID）
python3 scripts/yuque_novel_import.py --txt novel.txt --book-id <book_id>

# 分批导入（大文件防超时，进度自动续传）
python3 scripts/yuque_novel_import.py --txt novel.txt --start 1 --end 200 --book-id <book_id>

# 不修 TOC（导入完成后文档顺序可能不对）
python3 scripts/yuque_novel_import.py --txt novel.txt --no-toc-fix --book-id <book_id>
```

### EPUB 单独预览

```bash
python3 scripts/yuque_novel_epub_reader.py novel.epub
```

### TOC 修复单独跑

```bash
# 只检查不修改
python3 scripts/yuque_novel_toc_fix.py --book-id <book_id> --dry-run
# 修复（对比 progress/chapters_<book_id>.json 与语雀 TOC，从后往前移动错位文档）
python3 scripts/yuque_novel_toc_fix.py --book-id <book_id>
```

## 章节标题识别规则（txt / epub 通用）

支持以下格式（一行内单独出现，不超过 50 字符）：

| 类型 | 示例 |
|------|------|
| 中文数字章节 | 第1章、第一章、第三十五回、第二集 |
| 特殊章节 | 楔子、序章、序言、前言、引子 |
| 结尾章节 | 尾声、终章、后记、完结感言 |
| 番外 | 番外、外传 |

自定义格式需改 `yuque_novel_import.py` 的 `_TITLE_RE` 正则。

## EPUB 切分规则

| epub 结构 | 切分方式 |
|-----------|----------|
| 该 xhtml 有 `h1`/`h2`/`h3` | 只按 heading 切（正文行不参与判定，防误切） |
| 该 xhtml 无 heading | 按章节标题行切（同 txt 规则） |
| 完全识别不到标题 | 兜底「每个 xhtml 一章」（标题取首个 heading 或文件名） |

- 标题之前的内容（封面/版权页）兜底为「前言」章，**不静默丢正文**
- 不支持 DRM 加密 epub（加密文件在 `META-INF/encryption.xml`）
- 乱码/HTML 残留检测由 `yuque_novel_content_check.py` 完成，导入前后各出一份报告

## 断点续传与进度

- 进度文件按知识库隔离：`progress/progress_<book_id>.json`（completed/failed 章节清单），**不同库/不同书互不干扰，无需手动清进度**
- 章节列表同库隔离：`progress/chapters_<book_id>.json`，供 TOC 修复使用
- 上传阶段幂等：重跑同一命令自动跳过已完成章节
- 默认每 0.5 秒上传一章（防限流），`--interval` 可调
- TOC 修复只在全部章节导入完成后自动执行

## 已知坑

- 章节切分基于正则匹配标题行，**确保 txt 中每章标题独占一行**
- EPUB 用 `<p class="chapter">` 之类样式而非 heading 时走标签行规则；结构过于畸形（txt 粗转的 epub、回目被拆多行）切分可能不准，先 `--dry-run` 看预览
- `--create` 建新库后不写 config.json（skill 仓库不混个人配置），本次会话直接继续导入，后续用 `--book-id` 指定
- mcporter stdio 间歇启动失败：导入脚本重试 1 次、TOC 修复脚本重试 2 次；参数/权限类错误（`MCP error`）不重试直接失败

## 文件清单

| 文件 | 用途 |
|------|------|
| `scripts/yuque_novel_import.py` | 核心脚本：解析（txt/epub）+ 上传语雀 + 进度管理 + 分批导入 + 自动修 TOC |
| `scripts/yuque_novel_epub_reader.py` | EPUB 解析后端（container→OPF→spine→xhtml→章节，纯标准库） |
| `scripts/yuque_novel_content_check.py` | 正文内容校验（字数 / HTML 残留 / 乱码检测 / 章节报告） |
| `scripts/yuque_novel_toc_fix.py` | TOC 章节顺序修复（对比章节列表，从后往前移动错位文档，带重试） |
| `scripts/test_novel_toc_fix_retry.py` | TOC 修复重试逻辑回归单测（不联网，5 项） |

## 回归验证

```bash
cd scripts && python3 test_novel_toc_fix_retry.py
# 期望：5 项全过（坏输出重试 / MCP error 不重试 / 第 2 次成功 / 移动重试 3 轮成功 / 3 轮全败中止）
```
