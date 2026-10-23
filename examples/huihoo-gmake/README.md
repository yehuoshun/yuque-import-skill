# docs.huihoo.com GNU make 指南（GB2312 单页长文）→ 语雀（2026-10-23）

**可复用转换器**：`build.py` + 站点原件快照 `gmake.html`（站点 522 间歇，脚本优先读本地快照）。

首例：《多文件项目和 GNU Make 工具》（C-Scene 项目 #2，George Foot 著 / 哈少译，GNU make 指南）
→ 库 **84896556**（`GNU make 指南（2026-10-23）`，slug `gmake-guide-20261023`，分组「文章收集」），
20 节点（4 目录 / 16 文件），六查全绿，0 失败。

## 用法

```bash
# 站点在线时
python3 build.py   # 自动 fetch + 解析
# 站点 522/离线时：先 curl 存 gmake.html（脚本自动读本地）
curl -sSL http://docs.huihoo.com/gnu/linux/gmake.html -o gmake.html
python3 build.py
# 然后：yuque_tree_import.py --root <site> --book <id> --progress <p> --toc-md
```

## 关键点（照抄时别漏）

1. **GB2312 编码**：`raw.decode("gb2312", "replace")` 再处理，别用 utf-8。
2. **单页长文按纯文本编号标题拆章**：页面无 h1-h6、无分页、无锚点；章节是正文行
   `0) 介绍` / `1.2 何时分解你的项目` / `3 总结` 这种纯文本编号。识别规则：
   - 章 = `N) 标题` 或 `N 标题`（无括号的「总结」型，行尾无句号、长度 <30）
   - 节 = `N.N 标题`（**原站 1.1 无空格**：`1.1为什么使用它们?`，正则用 `\s*` 允许零空格）
   - ⚠️ **正文引用会误中**：文中「参考下面的 2.4 节）」以 `2.4 节）。` 开头 → 排除
     `节）。` 结尾的候选；同编号标题去重。
3. **代码块是文本标记不是 `<pre>`**：`=== makefile 开始 ===` / `=== makefile 结束 ===`
   区间 → 区间内行标记为 code，**连续 code 行攒成单个围栏块**（逐行围栏会碎成 N 个代码块）。
4. **正文伪标签**：`<target> : <dependency> <dependency> ...` 是 makefile 语法文本，
   不是真实 HTML 标签 → 剥标签前先把 `<target>/<dependency>/<command>/<tab>` 保护成
   `&lt;...&gt;`，否则变 `: ...`（内容丢失）。
5. **页眉作者/版权信息**（第一标题前的行）→ 根级 `00-译者说明.md`（C-Scene 来源、
   译者、免责声明）。
6. **站点 522 间歇（Cloudflare）**：urllib 直连会随机 HTTP 522 → 先 curl 存本地副本，
   脚本有本地快照就优先读本地。`[email&#160;protected]` 是 Cloudflare 邮箱混淆，
   保留原样（上游如此）。

## 同族

docs.huihoo.com 下还有别的 GNU/linux 文档（如 `docs.huihoo.com/gnu/linux/` 其他篇），
结构同为 GB2312 单页长文可复用本转换器（换 URL + 本地快照即可）。
