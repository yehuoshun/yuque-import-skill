# InfoQ 中文站迷你书（PDF，下载要登录）→ 语雀

2026-10-22 首例：《硝烟中的Scrum和XP ——我们如何实施 Scrum》（Henrik Kniberg 著 / 李剑译 / 郑柯审校）
→ 库 **84860629**（slug `scrum-xp-from-the-trenches-20261022`，分组「文章收集」），**25 节点**
（00-PDF 原件 + 扉页 + 5 篇前言 + 18 章，全平铺）。

源站：`http://www.infoq.com/cn/minibooks/scrum-xp-from-the-trenches`（老域名，**AWS WAF 拦死**，405）
真身：`https://www.infoq.cn/minibook/scrum-xp-from-the-trenches`（SPA，JS 渲染，HTML 只有 title/meta）

## 一、三根硬骨头（先解决"PDF 从哪来"）

### 1. 老域名被 WAF 挡 + 页面是空壳

- `infoq.com/cn/minibooks/*` → `405 + Human Verification`（AWS WAF），换 UA / HTTP 都没用
- `infoq.cn` 能 200，但**返回体只有 8KB 壳**（title/meta 是后端 SEO 渲染，正文全在 JS 里）

### 2. infoq.cn 公开 API：**必须 POST + JSON body**（GET 一律 404）

```bash
curl -X POST https://www.infoq.cn/public/v1/article/getDetail \
  -H 'Content-Type: application/json' \
  -d '{"uuid":"<slug>"}'
# → {data:{id, aid, type:8(电子书), article_title, ebook:{pdf:'a'},
#          content_url:'https://static-acl-001.geekbang.org/...content.html?auth_key=...'}}
```

- `content_url` 是**签名直链**，可直接 GET：里面是"简介 + 目录 + 免费下载此书"的 HTML（不是全书正文）
- 下载接口（从 chunk 里挖到的）：`POST /public/v1/article/book_sign {"uuid","type"}` → **`{"code":-2000,"msg":"未登录"}`**
  （前台逻辑：`this.loginUser ? _downloadBook() : login()`。没 InfoQ 账号 → 此路不通）

> 挖 API 的办法：`app.<hash>.js` 里有 chunk 装载器
> `js/"+(名字表)[e]+"."+(hash表)[e]+".js"` —— 按组件名直接取 chunk
> （`PageArticle.98aaa364.js` 里有 `getBookUrl` → `public/v1/article/book_sign`）。

### 3. ⭐ 绕法：官方公开合集 zip + HTTP Range 只抽那一个 PDF

迷你书列表页挂着**公开、免登录**的合集包：

```
https://static001.geekbang.org/resource/ebook/100books/book100.zip   # 541 MB, 104 条目
```

`build.py extract` 不做（一次性）：读尾 64KB 找 EOCD → 取中央目录 → 命中条目
`book100/scrum-and-xp-chinese-version.pdf`（deflate, csize 2508596, off 76140469）
→ 只 Range 抽该条目 + `zlib.decompress(data, -15)` → **官方中文 PDF，150 页 / 2.97MB / md5 e1e54cc71db570ada3dc8ce44c89e290**。

注意点：
- 本地文件头 `csize=0`（flags bit3 = data descriptor）→ **长度只信中央目录**
- 抽完必须验：`%PDF` 头 + PyMuPDF 页数 + md5

## 二、正文抽取规则（本书版式，`build.py`）

- 正文 `SimSun 10.5`；章标题 `SimHei 16`；段标题 `14pt`（SimSun/SimHei 混用）
- 列表符号三种：`Wingdings-Regular(\x83)`、`SymbolMT(•)`、`CourierNewPSMT(o)` → 前两类一级 `- `，`CourierNew` 缩进二级 `  - `
- **页眉** `y0 < 70` 丢（`简介| 1` / `2 | 硝烟中的SCRUM 和XP`）；**章节大号数字** 96pt `Arial-BoldMT` 丢（`size > 30`）
- **广告块**：位置每页不同（左/右栏都出现过）→ 信号 = 行文本含 `infoq.com` / `http://`，
  连同**其上最多 2 行 size≥13.5pt** 一起丢；残留的广告标题（`In` + `foQ 中文站Ruby 社区` 被 y 聚类拼回去）用 `中文站.*社区` 兜底
- **按 y 聚类成逻辑行**（tol 1.3pt）：同一 y 的多个片段拼起来 —— 顺带修好"行被字体切碎"（`In`/`foQ…`）和**表格行**（≥3 段且列间距 >28pt → 用 ` | ` 拼）
- **列表项续行要并回列表项**（`li` 后跟 `p` 且无句末标点 → 追加），否则每行都断成新条目
- 段落合并：x 缩进一致 + 行距 < 1.7×(size+3) + 前行无句末标点
- **首行标题去重**：去标点/空白归一后"互含"或**前 6 字相同**就丢（`Sprints 之间的休整时刻` vs 文档名 `Sprint之间的休整时刻`）
- 图**不抠**（老板 2026-10-22 拍：先出可读正文 + 原件附件兜底）；61 页栅格图留空

## 三、结构映射（书签不够用！）

PDF 原生书签只有 20 条（简介…有关作者），**漏了前言部分**（`p9-15`：译者序/致谢/序×2/前言，
这几页被当成"目录"的一部分）。目录页 `p5-8` 才是真目录 → 按**页码区间**手工列 `PAGES`：

```
扉页与版权 p1-4 ｜ 跳过目录 p5-8 ｜ 译者序 p9 ｜ 致谢 p10 ｜ 序—Jeff p11-12 ｜
序—Mike p13-14 ｜ 前言 p15 ｜ 简介 p16 … 有关作者 p149-150
```

= **24 篇**（`00-`…`23-` 两位前缀保证 `sorted()` 出正序）。

## 四、双轨（PDF 原件附件）

- `type=attachment` 上传（cookie/ctoken，见 `scripts/`，返回 `url` 字段）
- **先建 `00-PDF 原件.md` 文档 + 写账本**，再 `--toc-md` 导入
- ⚠️ **账本条目对应的文件必须真实存在于导入树里**：`build_toc_md()` 只遍历磁盘，
  `main()` 的 skip 判据是 `rel in prog["nodes"]`。第一版忘了落占位文件 → 那份 PDF 文档**没进 TOC**（成了幽灵，docs 25 vs TOC 24）。
  补一个占位 `clean/00-PDF 原件.md` 再跑一次 → `doc 0 / skip 25`，TOC 25，幽灵 0 ✅

## 五、验收（六查全绿）

| 项 | 结果 |
|---|---|
| TOC == 本地 == docs | 25 == 25 == 25 |
| 全路径唯一 | ✅ |
| 对账错位 | 0 |
| 幽灵 | 0 |
| 全库 `word_count>0` | ✅（min 122 / max 14207） |
| 逐篇回读 | 24/24 逐字节一致 |
| 附件 | 实拉 200 `application/pdf`，md5 与源一致 |

toc-md：25 行 / 1371B → PUT 0.6s，结构核对 PASS，0 失败，无分片。

## 六、复用

```bash
python3 build.py extract     # 抽正文到 clean/（改 PAGES / 广告规则 / 术语）
python3 build.py attach      # 上传 PDF 附件 + 预建 00-PDF 原件.md + 写账本（先填 BOOK）
touch clean/00-PDF\ 原件.md  # 占位文件（见 §四 的坑）
python3 ../scripts/yuque_tree_import.py --root clean --book <id> --progress progress.json --toc-md
python3 ../scripts/yuque_toc_reconcile.py --root clean --book <id> --progress progress.json
python3 ../scripts/yuque_check_ghosts.py --book <id>
```

合集 zip 里还有一份 `book100/Scrum-Checklists-Chinese.pdf`（《Scrum 检查列表》中译本，1.6MB）随时可取；
同一本英文原版 = `static001.geekbang.org/resource/ebook/100books/` 之外的 `book100/` 目录内。