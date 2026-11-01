# Node.js 包教不包会（alsotang/node-lessons）

> 实战：2026-11-01 fpb52 #189，库 85214141 / slug node-lessons-5e0e72e，21 节点（20 课/附 + 00-说明）六查全绿

## 特征与口径

- 仓库 = 教程书：根 `README.md`（前言 + 课程列表 `* Lesson N: [《课名》](...)`）+ `lessonN/README.md` 每课一篇
- **课名取根 README 课程列表的文本书名号标题**（不是 lessonN/README 的 H1——两者一致但列表更贴近目录）；文件名 `NN-课名.md` 零填充定序
- lesson14 附一篇非 README 的《解密设计模式-王垠.md》→ 独立文档 `14-附-解密设计模式（王垠）.md`
- 根 README 自带的「注意：2015 年书、异步最佳实践已演进」作者提醒必须写进 00-说明（同书价值判断）

## 图

- 课内截图全是 **GitHub blob / raw 外链**（`github.com/.../blob/master/lessonN/1.png` / `raw.githubusercontent.com/...`）→ 按 **URL basename 反查本地**（`lessonN/<basename>` 就在 clone 里）改写为本地路径 → rewrite CDN
- 转写正则 `!\[([^\]]*)\]\((https?://[^)]+)\)` 匹配外链图，`os.path.basename(url)` 找回本地文件

## 坑

- 文件名 slug 字符类里**别把 `s` 匹配进去**（raw string 双反斜杠 `\\s` 陷阱，见 ext4api-docs README 坑 3）
- 每个 lessonN/ 目录里 `.md` 之外还会拷 png 到 site/lessonN/ → rewrite 后**连目录带图删净**（硬规则 10）