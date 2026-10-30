# the-little-go-book_ZH_CN → 语雀

- **源**：https://github.com/songleo/the-little-go-book_ZH_CN @ `4c124a9`（CC BY-NC-SA 4.0）
- **库**：85149264 ／ slug `little-go-book-zh-cn-4c124a9`（开源项目口径，57018723）
- **产物**：7 目录 + 47 文档 = 54 节点；2 图 CDN

## 结构

```
eBook/N.0.md → 第NN章 <章名>/00-本章导读.md   （章名从 1.0 的「第1章 基础知识」或 2.0 的「2.0 结构体」两种写法里取）
eBook/N.M.md → 第NN章 <章名>/N.M <节名>.md
about-this-book.md / introduction.md → 前言/
conclusion.md → 结论.md
README.md → 00-说明.md
```

## 三个小坑

1. **章标题两种写法**：第 1 章写「第1章 基础知识」，第 2~6 章写「2.0 结构体」→ 两种前缀都要剥。
2. **导航段有两种形态**：多数篇目是 `## 链接` 小节，但 `4.2 接口.md` 是**裸列表且 CRLF 换行**（没有标题）→ 除了按标题切，还要从尾部逐行剥 `- [目录](directory.md)` / `- 上一节：` / `- 下一节：`，并统一 CRLF→LF。
3. **根级文档的图路径**：`../images/x.jpg` 只对「章/前言子目录里的 md」成立；`00-说明.md` 在 clean 根，必须写 `images/x.jpg`（写 `../` 会指到树外 → 上传脚本报「本地缺失」）。
