# 《Go 指南》中文版（A Tour of Go）仓库直取（fpb52 #106）

- 书单原链 `https://tour.go-zh.org/list` 的 Wayback 快照，但 **源站本机 502、web.archive.org 直连 000**。
- 站点由 `gotour` 把 `content/*.article` 渲染成页面 → **仓库即唯一真源**，直接吃 `Go-zh/tour` @ `4a8e183`。
- `.article` 语法：`* 标题` 分节；`.play xxx.go` / `.code` 指令 → 读文件展开成 ```go 围栏（无切片参数，直接整文件）；
  `.image p w h` → 图片；`[[url][text]]`（Org 链接）→ Markdown（`javascript:` 伪协议 → 纯文本）；
  `#appengine:` 前缀行是 AppEngine 专用注释 → 剔；代码里的 `// +build OMIT` 构建标记 → 剔。
- 同父重名节（「练习：等价二叉查找树」出现两次）→ 第二篇加「（续）」。
- 产出：6 模块 98 节 = 105 节点（6 TITLE / 99 DOC），六查全绿；库 85155047（slug `tour-go-zh-4a8e183`）。

用法：
```bash
git clone git@github.com:Go-zh/tour.git tour-src && python3 build_tour.py
```
