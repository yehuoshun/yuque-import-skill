# examples/coffee-script-org —— 《CoffeeScript 中文》单页整站

- 源：http://coffee-script.org（coffeescript.org 的中文译本，单页 index，版本 1.7.1 / 页脚 2014）
- 库：85147459 / slug `coffee-script-org-20261030` / https://www.yuque.com/yehuoshun/coffee-script-org-20261030
- 结果：34 文档 + 1 TITLE = 35 节点，六查全绿。

## 复用要点（详见 references/website-crawl-to-yuque.md 坑 83）

1. 正文容器 `div.container`，从**第一个 `<h2>`** 起；跳过 flybar 导航 + REPL 编辑器。
2. 两层拆：主节 `<h2>`；「语言手册」内部 `<b class="header">` 子节（在 `<p>` 里，非 h3）→ `NN.MM` 子文档 + `00-本章导读`。
3. `<div class='code'>` 内两个 `<pre><code>` = coffee 源 + js 输出 → 双围栏；丢 `div.minibutton` 与内嵌 `<script>`；独立 `<pre>` 无语言。
4. 无 `<th>` 的表 → 造空表头。
5. 相对 `<a href>` 补 `http://coffee-script.org/` 绝对前缀。
6. bs4 + **html5lib**（本机无 lxml）；`b`/`i`/`tt`/`br`/`span` 均要处理。

脚本：`build.py`（依赖 `bs4` + `html5lib`；输入 `fpb086-index.html`，即 `curl -sSL http://coffee-script.org`）。
