# joel-wiki —— Joel on Software 中译本（local.joelonsoftware.com wiki 页）

**来源**：`http://local.joelonsoftware.com/wiki/Chinese_(Simplified)`
（队列给的是 Wayback 快照 `web.archive.org/web/20170616013024/...`，但 **archive.org 在本沙箱不可达**）
**取回渠道**：**Common Crawl**（`CC-MAIN-2017-26`，快照 2017-06-28，与 Wayback 2017-06-16 同期）
**站点性质**：MediaWiki 1.16（Monobook 皮肤）单页；页面即 12 篇 Joel Spolsky 文章中文译本的合集
**成果**：12 篇文档 / 0 目录 / 0 失败 / 六查全绿 + 12 篇逐篇回读 0 差；库 **84899616**，slug `joel-on-software-zh-20261023`，分组「文章收集」36149506

---

## 一、取回原文（Common Crawl，archive.org 被墙时的兜底）

```bash
# 1) 查 CC 索引（2017 年那批；域名 2018 后已死，近年索引查不到）
curl -sS "http://index.commoncrawl.org/CC-MAIN-2017-26-index?url=local.joelonsoftware.com%2Fwiki%2FChinese_%28Simplified%29&output=json"
# → 拿到 filename / offset / length
# 2) 用 Range 只拉这一条 WARC 记录，gunzip 掉两层头，得原页 HTML
python3 - <<'PY'
import urllib.request, gzip
fn="crawl-data/CC-MAIN-2017-26/segments/1498128322870.59/warc/CC-MAIN-20170628050821-20170628070821-00020.warc.gz"
off, ln = 258399266, 65866
req=urllib.request.Request("https://data.commoncrawl.org/"+fn,
        headers={"Range":f"bytes={off}-{off+ln-1}","User-Agent":"Mozilla/5.0"})
data=gzip.decompress(urllib.request.urlopen(req, timeout=120).read())
i=data.index(b"\r\n\r\n"); rest=data[i+4:]          # 剥 WARC 头
j=rest.index(b"\r\n\r\n"); html=rest[j+4:]          # 剥 HTTP 头
open("page.html","wb").write(html)
PY
```

> ⚠️ index.commoncrawl.org 会间歇 504，重试即可；**图片另查**（本例 5 张 CA*.jpg 明确 `No Captures`，只能丢）。

## 二、转 md（按 h2 拆篇）

```bash
python3 build.py        # 读 ./page.html → 写 ./site/*.md
```

- 正文容器：**`div#bodyContent`**（Monobook 皮肤；`div#mw-content-text` 是 Vector 皮肤，这里**不存在**，用错选择器会拿到整页含侧栏/页脚）
- 切篇：`<h2>` 即 12 篇文章标题；`<h2>Contents</h2>` 的目录 table（`#toc`）要整块丢
- 构件：`p` / `a` / `b,strong,i,em` / `ul` / `pre` / 少量 `table`；`<img>` 全部丢弃（源站死 + CC 无收录），在受影响的文章末尾加一行「插图已省略」注释
- 文件名 `NN-标题.md` 两位序号前缀（免 fix_order）；标题含半角 `/` → 换全角 `／`（本例「膨胀软件与80/20的谣传」）
- 正文里字面出现的 `<a>`（ASP.NET 那篇）要转义成 `\<a>`，否则被当原始 HTML 吃掉

## 三、导入

```bash
python3 scripts/yuque_repo_import.py create-book --name "Joel谈软件（2026-10-23）" \
    --slug joel-on-software-zh-20261023 --desc "来源：<url>（原站已死，经 CC 取回）｜ … ｜ 导入 2026-10-23"
python3 scripts/yuque_repo_import.py move-stack --book-id 84899616 --stack-id 36149506
python3 scripts/yuque_tree_import.py --root site --book 84899616 --progress ./progress.json --toc-md
```

> ⚠️ `--test N` + `--toc-md` 收尾必报「生成目录树失败」（只建了前 N 篇，凑不齐整树）——**预期**，正式全量再跑一次即消。
