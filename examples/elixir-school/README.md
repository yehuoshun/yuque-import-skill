# examples/elixir-school —— 站点由源仓库渲染的课程仓（吃 md 非 HTML）

- 源：https://github.com/elixirschool/elixirschool @ 4e5bea2 → `lessons/zh-hans/*.md`（站点 elixirschool.com/zh-hans 由它渲染）
- 库：85147606 / slug `elixir-school-zh-4e5bea2` / https://www.yuque.com/yehuoshun/elixir-school-zh-4e5bea2
- 结果：8 TITLE + 48 DOC = 56 节点，7 图 CDN，六查全绿。

## 复用要点（详见 references/github-repo-to-yuque.md 坑 83）

1. **发布面/顺序取站点侧栏**（仓库全量会多出未发布篇，如 distillery 页面 500）。
2. frontmatter 是 Elixir map `%{ title, excerpt }` + `---`（非 YAML）。
3. 缩进代码块转围栏时排除 4 空格缩进的**嵌套列表项**。
4. 图 `/images/x.png` → `../images/x.png` → CDN → 删目录。
5. `/zh-hans/lessons/...` 与 `#锚点` → 纯文字；`//host` → `https://`。
6. `{{ site.xxx }}` Liquid 残留照抄（站点自身也没渲染）。

脚本：`build.py`（输入 = 仓库 clone）。
