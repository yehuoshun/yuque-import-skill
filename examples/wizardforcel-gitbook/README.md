# wizardforcel / 老 gitbooks.io 静态站 → 语雀（2026-10-22）

**可复用转换器**：`build.py` —— 吃 `https://<name>.gitbooks.io/<book>/content/` 这类老 gitbooks.io
GitBook 2.x 渲染站（侧栏 `ul.summary` + 正文 `section.normal`），无源仓库时的网站口径。

首例：《让开发自动化系列专栏》（IBM developerWorks by Paul Duvall，wizardforcel 简中译本）
→ 库 **84864611**（`让开发自动化系列专栏（2026-10-22）`，slug `ibm-j-ap-20261022`，分组「文章收集」），
18 节点（0 目录 / 18 文档，文件名带 `NN-` 序号前缀免归位），78/80 图传 CDN，六查全绿。

## 用法

```bash
python3 build.py --base https://wizardforcel.gitbooks.io/ibm-j-ap/content/ \
    --out /path/site --img-map /path/img_map.json --book-name "让开发自动化系列专栏"
# 然后：yuque_tree_import.py --root <site> --book <id> --progress <p> --toc-md
```

- 页面清单**自动从 `ul.summary li.chapter[data-path]` 解析**（顺序 = 侧栏序），无需手填。
- `--book-name` 用于剥标题前缀（`让开发自动化: `）并给 `index.html` 起名 `00-系列介绍.md`。
- 正文站内图（`img/xxx.gif` 相对路径）**边转边传 CDN**（`img_map.json` 断点续传），完事导入根没有图片文件。

## 关键点（照抄时别漏）

1. **gitbooks.io 间歇 401** → `fetch()` 必须退避重试（6 次，2/4/6…s）。首轮直接裸请求会 401 挂掉。
2. 正文容器 = `section.normal`（页外 `nav-prev/nav-next` 天然在外）；侧栏标题里 `<b>N.</b>` 是序号。
3. **正文首个 H1 == 文档标题 → 剥掉**（语雀侧已有文档标题），避免重复。
4. 文件名用 `NN-副标题.md` 两位序号前缀 → 字典序天然正确；标题含 `/` 换全角 `／`。
5. ⚠️ **上游真缺图**：本站 `img/build-failure.jpg`、`img/cpd-ant.jpg` 源站 404（gitbooks.io 建站时没带上）
   → 保留原站 URL（裂图即上游如此，修不了）。

## 同族后续

队列里 `wizardforcel.gitbooks.io/ibm-j-cq`（《追求代码质量》）等同款站，直接换 `--base` + `--book-name` 复用。