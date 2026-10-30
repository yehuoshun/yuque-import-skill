# cpie-cn → 语雀（2026-10-30）

《Erlang并发编程》—_Concurrent Programming in Erlang_ (Joe Armstrong / Robert Virding /
Claes Wikström / Mike Williams, Prentice Hall) **第一部分的完整中文译本**，连城发起、多志愿者协作，
CC BY-NC-ND 2.5 中国大陆。

- 源仓库：https://github.com/liancheng/cpie-cn @ `0a550d4`（2013-11-02）
- 在线：https://cpie-cn.readthedocs.org/en/latest/
- 语雀库 **85147901**，slug `cpie-cn-0a550d4`，**20 节点（1 目录 / 19 文档）**，六查全绿。

## 用法

```bash
git clone https://github.com/liancheng/cpie-cn.git /tmp/cpie
python3 build.py --src /tmp/cpie --out ./build     # 生成 build/ 与 build-work/
# 手写 build/00-说明.md（来源/commit/残缺度）
python3 ../../scripts/yuque_rewrite_images.py ./build ./img_map.json --throttle 2
rm -rf ./build/_static
python3 ../../scripts/yuque_repo_import.py create-book --name "Erlang并发编程（0a550d4）" \
    --slug cpie-cn-0a550d4 --desc "..."
python3 ../../scripts/yuque_tree_import.py --root ./build --book <id> \
    --progress ./progress.json --toc-md
```

## 结构

```
00-前言.md         ← index.rst（版权声明/告读者/术语表；H1 = 书名）
00-说明.md         ← 手写
01-翻译计划.md      ← cpie-cn-project.rst（译者列表/进度表/译者须知）
02-序言.md / 03-致谢.md / 04-简介.md
05-第I部分 编程/    ← TITLE（part-i_index.rst 只含 toctree）
  01-第1章 … 09-第9章
  10-附录A Erlang 语法参考 / 11-附录C 标准库 / 12-附录D Erlang的错误处理 / 13-附录E 驱动
```

（**附录B 内置函数**上游为空壳，146B 只有标题 → 不建节点。）

## 关键点（细节见 references 坑 88）

1. **缩进的 `.. literalinclude::` 静默丢码**：程序9.3 写在 `.. topic::` 里（缩进 4 空格），
   原 `LI_RE` 只认列 0 → 整段 C 源码无声消失。已修 `yuque_rst_convert.py` 支持缩进；
   本例单篇 `PUT /docs/{id}` 更新（不新建）。
2. **`conf.py` 的 `rst_prolog` 不被 docutils 读**：`|eps|`→ε、`|->|`→→、`|=>|`→⇒、
   `|double-accute-*|`→ő/ä/Ä、`|latex|`→LaTeX、`|date|`… 逐文件前置注入 prolog
   （整树复制到 `build-work/`，保 `literalinclude` 相对路径）。⚠️ 注入时**先读后写**
   （`w` 会先截断文件）。
3. **图 alt 默认是路径** → 换成 basename；引用 `_static/…`（无前导斜杠）子目录补 `../`；
   21 图（含 cc.png 与 8 张译者邮箱图）全传 CDN，跑完删 `_static/`。
4. **`prependNode` 归位**：别一次押一串（同一批节点因锚点当前位置不同结果会变）→
   以一个「当前不在期望位置」的锚点，按期望顺序逐个 prepend，**每步回读 `prev_uuid` 链验收**。