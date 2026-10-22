# 《图说设计模式》me115/design_patterns → 语雀（2026-10-22 首例）

源：`https://github.com/me115/design_patterns`（默认分支 `master` @ `0cbd785`，Sphinx/reST 书稿）
产物：库 `图说设计模式（0cbd785）` = **84861785**，slug `design-patterns-0cbd785`，分组「开源项目」57018723
站点 oracle：`https://design-patterns.readthedocs.io/zh-cn/latest/`（还活着，可对照标题/代码块数）

## 一、这次踩的新坑（已固化进 `scripts/yuque_rst_convert.py`；refs 坑 55）

Sphinx/reST 书稿转换器原来有三处不足，这本全踩到了：

1. **`.. literalinclude::` 被 docutils 静默丢弃** → 「代码分析」整节代码全丢。
   转换前展开成 `.. code:: <lang>`（docutils 核心自带）指令：读源码文件（`/` 开头 = Sphinx srcdir，
   否则相对当前 rst 目录）→ 顶格缩进 4 空格 → 语言优先取 `:language:` 选项、否则按扩展名映射。
   比文字对得上的还有：`<pre class="code cpp literal-block">` 的 class 可判语言 → 围栏写成 ` ```cpp `。
2. **`doctitle_xform` 默认把首节提升为标题** → 子节全被压成 h1，语雀大纲**扁平**。
   改 `doctitle_xform: False`：保留自然层级（章 h1 / 节 h2 / 小节 h3）。
3. **块之间没空行** → 相邻两段 `<p>` 在 markdown 里**并成一段**。改为按块类型 join
   （同类 `li`/表格行/引用行/`dt`-`dd` 用单 `\n`，其余 `\n\n`）。
   顺带 `.. contents:: 目录` 整条剥掉（本地大纲与语雀侧边大纲重复）。

## 二、口径与范围

- **有 repo → 开源项目口径**（库名带 commit、分组「开源项目」）。
- **只导书稿正文，脚手架全剔**：`conf.py` `Makefile` `make.bat` `sphinx_rtd_theme/` `_static/`
  `design_patterns.EAP`（4MB EA 工程）`state_diagram.vsd` `dp_tmp.txt`。
- **`code/` 也不入库**（口径判断留痕）：各章「代码分析」节的 C++ 源码已由 `literalinclude`
  **内联进正文**，站点同样没有独立的 code 章节；且 `code/*/mingw5/` 是编译产物（84 个 `.o` + 16 个 `.exe`），
  进库只会变占位文档。→ 正文零丢失，仓库 `code/` 不入库（如老板要单独附录，只导 `.cpp/.h` 即可）。
- 站点只覆盖 **16 个模式**（创建型 5 / 结构型 6 / 行为型 5）；各分类页里列的其它模式（组合/原型/职责链/
  解释器/迭代器/备忘录/模板方法/访问者）**上游没有正文** → 不造节点。

## 三、clean 树（3 目录 / 22 文档 = 25 节点）

```
00-前言.md                    ← index.rst（剥掉 "Indices and tables" 伪章节）
01-看懂UML类图和时序图.md      ← read_uml.rst
02-创建型模式/{00-创建型模式, 01-简单工厂模式( Simple Factory Pattern ), 02-工厂方法模式(Factory Method Pattern),
               03-抽象工厂模式(Abstract Factory), 04-建造者模式, 05-单例模式}
03-结构型模式/{00-结构型模式, 01-适配器…06-代理模式}
04-行为型模式/{00-行为型模式, 01-命令…05-策略模式}
99-仓库说明.md                ← readme.rst（仓库说明 + 在线浏览）
```

- 文档名 = `NN-` + 转换后 md 的**首个 H1**（保留英文名，如 `抽象工厂模式(Abstract Factory)`）；
  首 H1 与文件名标题重复 → 剥掉（避免语雀双标题）。
- 数字前缀让字典序天然正确；`00-` 落地页在组内天然第一。

## 四、图

- `_static/` 76 张，**被引用的 69 张**全传 CDN（`--throttle 2`，0 失败）；未引用的 9 张随目录删掉。
- 引用原是 Sphinx 绝对路径 `/_static/x.jpg` → 重写为相对（根级 `_static/`、子目录 `../_static/`），
  跑 `yuque_rewrite_images.py` 后把 `_static/` 从导入根**删干净**（硬规则 10）。
- ⚠️ 上游 rst 把两张图写成 `State1.png`/`State2.png`，磁盘是**小写** `state1.png`/`state2.png`
  （站点同错 = 404）→ 拷图时按**大小写不敏感**解析真身，正文引用名照抄。

## 五、复现命令

```bash
cd code/yuque-import-skill && source ~/.openclaw/secrets/credentials.env
python3 scripts/yuque_repo_import.py prep --url https://github.com/me115/design_patterns --dir ~/.openclaw/workspace/tmp
python3 examples/design-patterns/build_lib.py \
    --clean ~/.openclaw/workspace/tmp/design_patterns-0cbd785-clean \
    --out   ~/.openclaw/workspace/tmp/design_patterns-0cbd785-book
python3 scripts/yuque_rewrite_images.py <book> <img_map.json> --throttle 2
rm -rf <book>/_static
python3 scripts/yuque_repo_import.py create-book --name "图说设计模式（0cbd785）" \
    --slug design-patterns-0cbd785 --desc "来源：<url> @ 0cbd785 ｜ … ｜ 导入 2026-10-22"
python3 scripts/yuque_repo_import.py move-stack --book-id <id> --stack-id 57018723
python3 scripts/yuque_tree_import.py --root <book> --book <id> --progress <ledger> --toc-md
python3 examples/design-patterns/fix_root_order.py <id>   # 根级 DOC 归位（toc-md 会把 TOC 排到 DOC 前）
```

## 六、验收（六查 + 逐篇回读，全绿）

| 查 | 结果 |
|---|---|
| TOC 25 == 本地 25（3 目录 + 22 文档） | ✅ |
| 全路径唯一 | True |
| 对账错位 | 0 |
| 分片 | 无（最大正文 < 512KB） |
| 幽灵 doc | 0（docs total 22 == TOC DOC 22） |
| 全库 word_count > 0 | 22/22（无占位） |
| 逐篇回读（语雀 body == 本地 md，strip 后） | 22/22 命中 0 差 |

抽查 `04-行为型模式/04-状态模式.md`：word_count 2991、5 个 ` ```cpp ` 代码块（= 站点 5 个高亮块）、
CDN 图实拉 200。toc-md 一次 PUT 25 行 **0.9s**、结构核对 PASS。