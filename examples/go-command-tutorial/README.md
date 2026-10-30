# go_command_tutorial（郝林《Go 命令教程》）→ 语雀

- **源**：https://github.com/hyper-carrot/go_command_tutorial @ `9a76c06`（docsify 单章教程，原为《Go 并发编程实战》被砍掉的一章）
- **库**：85149418 ／ slug `go-command-tutorial-9a76c06`（开源项目口径，57018723）
- **产物**：1 目录 + 16 文档 = 17 节点；4 图 CDN

## 结构

```
0.0.md      → 第0章 标准命令详解/00-本章导读.md
0.N.md      → 第0章 标准命令详解/0.0N <命令>.md   （N=1..14，go build/install/get/clean/doc/run/test/list/fmt/fix/vet/pprof/cgo/env）
README.md   → 00-说明.md
catalog.md / _sidebar.md / SUMMARY.md → 不收（三种导航页，与语雀 TOC 重复）
```

## 两个坑

1. **`0.10` 会排到 `0.9` 前面**（字典序）→ 节号必须零填充成 `0.01 … 0.14`，否则 TOC 顺序乱掉。
2. **`00-本章导读.md` / `00-说明.md` 都被 toc-md 排到末尾**（根级 DOC 与章内 DOC 同理）→ 收尾两发 `prependNode(action_mode=sibling)`：章导读挂到 `0.01` 前、根级说明挂到第一个 TITLE 前。图片路径：文档进章目录后要写 `../images/`，根级说明写 `images/`。
