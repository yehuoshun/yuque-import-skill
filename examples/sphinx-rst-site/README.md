# Sphinx / readthedocs RST 站 → 语雀（Google C++ 风格指南实战，2026-10-30，库 85147043）

## 站点识别与取源
- `zh-google-styleguide.readthedocs.io/en/latest/google-cpp-styleguide/` = **Sphinx** 站（Read the Docs 主题）。
- **不爬 HTML**：readthedocs 暴露源文档 → `GET /en/latest/_sources/<project>/<page>.rst.txt`（200，即 Sphinx 源）。页面清单从 index.html 的 `href` 抓（`headers/scoping/classes/functions/magic/others/naming/comments/formatting/exceptions/end`）。
- 转换走 `scripts/yuque_rst_convert.py`（docutils html5 中间层）。**但该脚本对 Sphinx 站有 3 个陷阱**，本 example 的 `build_cpp_styleguide.py` 里以 monkey-patch 修掉（可直接复制复用）：

### 陷阱 1 · BLOCK_RE 的 `(p)` 会匹配 `<pre` 前缀（坑 9 变体，必踩）
`<(h[1-6]|pre|p|li|dt|dd|table|blockquote)([^>]*)>` 里 `p` 分支先于 `pre` 尝试：输入 `<pre class=...>` 时 `<p` + `([^>]*)`=`re class=...` + `>` 也成立 → `<pre>` 被当 `<p>`，非贪心 `(.*?)</p>` 找不到就近 `</p>` 就**跨界吞掉中间的全部内容**（症状：代码块被压成一行行内代码 + 后续正文粘连，147 块只出 142）。**修法：加 `\b`** → `<p\b` 不匹配 `pr`。

### 陷阱 2 · 提示框（admonition）内容被块间隙的 inline 压成一行
`.. tip::/note::/warning::` → `<aside class="admonition tip">`。若在 `<p>` 回填里走 gap 的 `inline()`，多行引用块会被压成一行（`> **Tip**： > 内容`）；且**嵌套提示框**（tip 里套 warning，如 6.17/6.19）用非贪婪 `(.*?)</aside>` 会在内层闭合处提前截断 → 内容错位/丢失。**修法**：深度计数提取联配的对 `</aside>`（支持嵌套）+ 用占位符把已转好的引用块摘出、扫完回填（`restore()`）。

### 陷阱 3 · docutils 新版行内字面量是 `<span class="docutils literal">` 而非 `<tt>`
原 `inline()` 只认 `<(code|tt|cite|kbd)>` → 所有 `` `` ` `` 行内代码**丢反引号**（变裸文本）。且它可能**拆成多段**：`` ``std::shared_ptr<const Foo>`` `` → `<span class="docutils literal"><span class="pre">std::shared_ptr&lt;const</span> Foo&gt;</span>`（内层 span 只包前半）。**修法**：① 用深度计数配对 span 整段转反引号（`_wrap_literals`）；② **不要提前 unescape** —— 否则 `<`/`>` 会被随后「剥标签」的正则当 HTML 吞掉（`<<` + 后续 `<span>` 合成假标签，丢一大段）。

## 其它口径
- 12 篇全平铺（0 目录 / 12 文档），文件名 `NN-章名.md`（`00-扉页`+`01-头文件`~`11-结束语`），序号前缀保序免归位。
- **剥首个 H1**（= 章标题，文件名已承载，避免语雀双标题）。
- 无图（纯文字 + 147 个 ```c++ 代码块）。
- 验收：147 code-block 全数落地、980 代码行**零缺失**、CJK 差 35（= 被剥章标题字数）、六查全绿、12 篇逐篇回读 0 差。

## 复现
```bash
# 抓 rst
for p in index headers scoping classes functions magic others naming comments formatting exceptions end; do
  curl -sS "https://zh-google-styleguide.readthedocs.io/en/latest/_sources/google-cpp-styleguide/$p.rst.txt" -o rst/$p.rst.txt; done
python3 build_cpp_styleguide.py   # → site/*.md
```
