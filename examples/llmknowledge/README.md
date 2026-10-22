# llmknowledge（《理解现代大语言模型系统-从RAG到全景》，2026-10-22）

- 站点：https://llmknowledge.org/zh/（llmknowledge.pages.dev 重定向至此）| 作者 koe
- 口径：**源仓库 md**（`koemia/llmknowledge` 的 `content/理解现代LLM系统_从RAG到全景.md`，CC BY-NC-ND 4.0）
  —— 与 d2l 同款：站点正文 = md 按 H2 切分（10 页 = 10 个 H2，标题一字不差），
  站点 HTML 只当 oracle 验证切分对应关系
- 单 md 711 行 / 102KB；10 篇 = 开始之前 + 第一~七章 + 附录工具库 + 速记卡片
- 脚注：49 个定义**内联在正文中**（跟随引用章节），切分后自然随章走；93 处引用全保真
- 图：7 张 SVG（rag-8-steps/dpt-4-steps/offline-indexing/rag-loop-a~d），
  md 里是 `<img src="images/x.svg" alt="...">` → 切分时转 markdown `![alt](src)` → 传 CDN（upload 吃 svg）
- 库：84856349，slug `llmknowledge-zh-20261022`，分组「文章收集」36149506
- 复现：`python3 split.py`（→ clean/ 10 篇 + images/）→ `yuque_rewrite_images.py clean img_map.json`
  → 删 images/ → tree_import → reconcile
