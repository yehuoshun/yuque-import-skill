# examples/dart-language-tour-wayback —— MediaWiki 单页 wiki（Wayback 快照）

- 源：http://dart.lidian.info/wiki/Language_Tour（原站 DNS 已死）→ Wayback `20200415002731`
- 库：85147555 / slug `dart-language-tour-20261030` / https://www.yuque.com/yehuoshun/dart-language-tour-20261030
- 结果：15 文档（00-说明 + 14 节），六查全绿。

## 复用要点（详见 references/website-crawl-to-yuque.md 坑 84）

1. 死站 → Wayback `…/web/<ts>id_/<url>`；本机被墙时用 re-harness `fetch-files.yml` 出口抓。
2. 正文容器 `div.mw-parser-output`（Vector 皮肤；别用 `#bodyContent`）。
3. 按 `<h2>` 拆篇、丢「目录」节；h3/h4 留作小节标题。
4. `<pre class="prettyprint lang-x">` → ```x 围栏。
5. 行内 `<code>` 取 **纯文本**（否则内嵌 `<b>/<i>` 变星号）。
6. `/wiki/...` 与 `#锚点` 转纯文字；剔 `.mw-editsection` / `.reference`。

脚本：`build.py`（依赖 bs4 + html5lib；输入 = 快照 HTML）。
