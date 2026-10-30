# golangdoc.translations → 语雀

- **源**：https://github.com/golang-china/golangdoc.translations @ `fe925a2`（BSD-style）
- **库**：85149174 ／ slug `go-doc-translations-fe925a2`（开源项目口径，分组 57018723）
- **产物**：28 目录 + 129 文档 = 157 节点；4 图 CDN

## 这是个「半成品翻译工程」，三种双语载体（各有明确分隔标记）

| 载体 | 中文标记 | 处理 |
|---|---|---|
| `doc/zh_CN/*.html` | 英文包在 `<div class="english">` | **删掉 div.english**，剩下即中文 |
| `blog/zh_CN/content/*.article` | `.html _tr/div_begin_zh_CN.html` … `.html _tr/div_end.html` | 只保留标记之间的行（文件头单读：标题/日期/Tags/作者） |
| `src/**/doc_zh_CN.go` | 每个 API 先英文注释段、后中文注释段 | 逐注释组找第一处含中文的段落起点，保留到组尾 + 声明签名 |

## 关键判据：只收「真有译文」的篇目

仓库里大量文件是**英文原样**（只翻了一部分）。用**中文字符密度**过滤，别用「含中文」：

```python
cjk = len(re.findall(r"[\u4e00-\u9fff]", md)) / len(md)
keep = cjk >= 0.05
```

实测：`doc` 25 篇 html → 只有 18 篇 ≥5%（`go_spec.html` 0.6%、`go1.html` 1.4% 被剔）；`blog` 92 篇 → 仅 8 篇（其余 0.0~0.1%，`welcome.article` 里的「世界」是假阳性）；`talks` 42 篇 slide、`tour` 6 篇 → **全站 0 篇翻译**，不建空壳目录。

## 两个小坑

1. **`<img src="/doc/gopher/x.png">` 是站点绝对路径**，仓库实际在 `doc/zh_CN/gopher/`；`resolve_img` 要按 base_dir → 仓库根 → 各 zh_CN 子目录 → 按文件名唯一命中 逐级回退。
2. **Go 代码样例里的 `<img src="{{.X}}">` 会被 `yuque_rewrite_images.py` 的 HTML_RE 误判成待传图片**（`html/template` 包文档里 2 处）→ `--dry` 报「本地缺失 2」，是假阳性，不影响导入。
