# go-fundamental-programming — 无闻《Go 编程基础》→ 语雀

- **源**：https://github.com/Unknwon/go-fundamental-programming @ `3336687`（CC BY-SA 3.0，代码 BSD-3）
- **库**：85149002 ／ slug `go-fundamental-programming-3336687`（开源项目口径，分组 57018723）
- **产物**：1 目录（示例代码，6 个 .go）+ 22 文档（15 篇课堂笔记 + 00-说明）= 23 节点，无图

## 结构

```
README.md            → 00-说明.md（剥指向 lectures/*.md 的相对链，保留站外视频/资料链）
lectures/lectureN.md → 第NN课 <标题>.md（零填充前缀；Setext 标题当文档名，正文不重复 H1）
lectures/*.go        → 示例代码/<原名>.go（导入器按 .go 扩展名包 ```go 围栏）
```

## 小坑

1. 笔记用 **Setext H1**（`第 N 课：xxx` + `====`）→ 取作文档名后要从正文剥掉。
2. `### 课程大纲` 是 **tab 缩进的时间点**（markdown 会当代码块）→ 转 `- \`[mm:ss]\` 内容` 列表。
3. `### 课程链接` 是 **仓库内相对链**（`lectureN.md`）→ 语雀里是死链，转纯文本；站外链保留。
