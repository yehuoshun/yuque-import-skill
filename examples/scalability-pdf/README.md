# PDF 双轨导入：《走向分布式》 (Scalability! But at what COST?)

第二例（首例 OSTEP 见 ../ostep-pdf/），2026-10-18 → 库 `84706243`「走向分布式（20261018）」。
**双轨**：正文+图提取导入（30 章拆篇 = 30 篇文档）+ PDF 原件附件（挂根级 `00-PDF 原件.md`）。
图结果：位图 3 张（CAP 示意图 p16 / Kafka 架构图 p21 / partition 示意 p22）→ CDN 引用；矢量 0（全库只有页眉页脚横线）。

## 排版特征（本 PDF，与 OSTEP 不同点）

| 元素 | 特征 | 处理 |
|---|---|---|
| 正文 | 11.95pt 中文 WenQuanYiMicroHei / 西文 ArialMT | 段落；`get_text("dict")` span 原样拼接（PDF 自带空格 span，**不要手动插空格**） |
| 粗体 | Arial-BoldMT（正文极少，主要在 TOC） | `**x**` |
| 章标题页 | "CHAPTER"(y~102) + 罗马数字(y~132) + "DAY N: 标题"(17.22pt, y~180-245 可换行) | 装饰与标题行全丢，标题取自书内 TOC 原文（标题页全大写，TOC 原大小写） |
| 脚注/整理者注 | 9.96pt（"1…（by 邓草原）"） | `> ` blockquote |
| 上标引用 | 7.97pt 行尾 "1"/"2" | 原样保留，且句末判断要先剥尾随数字 |
| 项目符号 | "• " x≈91.2，内容折行 x≈101.3 | `- `；**列表内 x 上跳不能断段**，列表结束看 x 回缩（≤ 符号行 x-8） |
| 编号项 | "1. " x≈72/85.4 | 段边界（`^\d+[.、)]` 硬边界） |
| 页眉/页码 | 页眉 y≈35.6 / 页码 y≈742（H=792） | `top<60` / `bot>730` |
| 断词 | "Mem-ory"/"MapRe-duce"（TeX 断词） | words_alpha.txt 双侧完整词才留连字符；**dehyphen 拼接时别加空格**（`dehyphen(prev, nxt)` 直接接） |

## 图片插入规则

- 位图 `get_images()+extract_image` → PNG 存 `img/`；md 相对路径 `![alt](img/xxx.png)`
- **就近插入**：按 (page, y0) 顺序挂 pending，处理到「y 越过图顶」的下一行前 flush 进 blocks；
  页首有图（图顶 < 该页首行 y）→ 跨页段落强制断段，图插在上页段后
- 图题：本书无「图 N」题注 → alt 用手工语义描述（宁缺毋滥）
- 随后 `yuque_rewrite_images.py <clean> <img_map> --throttle 1.5`（--dry 先核）→ **删 clean/img/**（坑 10）

## PDF 原件附件（双轨另一轨）

- 上传 `type=attachment`：**URL 取返回的 `url` 字段**（`yuque.com/attachments/...`，会话门控）
- **filekey 拼 cdn.nlark.com 是 403 死路**（PDF attachment 不走公开 CDN）
- `00-PDF 原件.md` 根级文档：`# 标题（PDF 原件）` + 元信息 + `📎 [xxx.pdf（410KB）](url)` + 源站链接
- 验收：body 含正确 URL；带 cookie 实拉 200 application/pdf 且 md5 与源文件一致（本次 410039B 逐字节相同）

## 复用

`extract_scalability.py` 里改 `PDF` / `OUT` / `CHAPTER_PAGES` / `TITLES` / `ALT` 即可套用同类「Day 系列」PDF。