# phoenix-doc-in-chinese → 语雀（2026-10-30）

《Phoenix 框架中文文档》—_Phoenix 官方指南（phoenix_guides, Chris McCord 等）的社区中文译本_，
译于 Phoenix 1.2/1.3 时代（Elixir 1.4 / Erlang 18+）。

- 书单原链：https://mydearxym.gitbooks.io/phoenix-doc-in-chinese/content/
- 实际来源：https://github.com/mydearxym/phoenix-doc-in-chinese @ `52f09cb`（2017-10-14）
- 语雀库 **85147782**，slug `phoenix-doc-in-chinese-52f09cb`，**39 节点（4 目录 / 35 文档）**，六查全绿。

## 为什么吃仓库 md 而不是爬站

老 gitbooks.io 站**开着但中文页全 404**：`index.html` 200，`概览.html` / `安装.html` /
`测试/A_概述.html` 全是 404，只有 `DD_Plug.html` 这类纯 ASCII 名能取。
GitBook 自带的 `search_index.json`（2.4MB，200）**只有纯文本 body**——代码围栏、表格、
标题层级全丢，不能当正文源。→ 反查源仓库（站首页 body 里就写着 Github 地址）走开源项目口径。

## 用法

```bash
git clone https://github.com/mydearxym/phoenix-doc-in-chinese.git /tmp/phx
python3 build.py --src /tmp/phx --out ./build
# 手写 build/00-说明.md（来源/commit/残缺度）
python3 ../../scripts/yuque_tree_import.py --root ./build --book <id> \
    --progress ./progress.json --toc-md
```

## 结构

| 节点 | 内容 |
|---|---|
| `00-介绍.md` | 仓库 README（书链 + 文档大纲 + 未完成说明） |
| `00-说明.md` | 来源/commit/残缺度/收敛说明（手写） |
| `01-基础部分/` | 概览、安装、A_起步 … H_ecto模型（11 篇） |
| `02-测试/` | A_概述、E_模型、G_控制器、H_视图、J_channels（5 篇） |
| `03-部署/` | A_概述、E_heroku、I_exrm_release（3 篇） |
| `04-进阶内容/` | A_升级phoenix … V_学习 Elixir（14 篇） |

## 关键点（细节见 references 坑 87）

1. **SUMMARY 笔误**：`部署/I_exrm_release.md` 磁盘是 `I_exrm_releases.md` → `os.path.exists` 失败会静默丢整章，加 `s.md` 兜底。
2. **标题层级五国混战**：`###` 当章标题、`#####` 当小节、整篇平铺都出现 → 别「整体降一级」，用**去重层级集合 → H2/H3/H4 相对归一**，且**跟代码围栏**。
3. **标题剥离比对两种形态**：`norm(title)` 与 `norm(去前缀版)`（`DD_Plug`→`Plug`），归一化去掉空格/下划线（正文写 `ecto 模型` 而 SUMMARY 是 `H_ecto模型`）；只剥首个标题行，且必须相等才剥。
4. **链接**：站内自指/相对 `.md/.html` → 纯文字；`http(s)` 外链原样（判相对前先放行 http）。
5. **根级 DOC 归位**：`00-介绍`/`00-说明` 落 TITLE 之后 → 逆序两发 `prependNode`，按 `prev_uuid` 链验收（坑 75）。
6. **残缺度照录**：测试/视图（官方也没有）、heroku 部署（国内不可达）、exrm（将被 distillery 取代）三处 stub 保留，`00-说明` + 库描述写明。