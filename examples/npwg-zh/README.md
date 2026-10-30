# examples/npwg-zh —《Network Programming with Go》中文翻译版（astaxie/NPWG_zh）

fpb52 #111 · 库 85155113 · @ 50b2885 · 2026-10-31

## 源形态
仓库 `zh/` 下是一本 **en/zh 双语 HTML 书**（XHTML + sigil `sgc-*` 样式）：
- `zh/index.html` = 书首页 + 章节目录（15 章，给章序）
- `zh/Text/chapter-*.html` = 15 个章节页（en/zh 同级姊妹块：`<p class="en">` + `<p class="zh">`、`<h2 class="en">`+`<h2 class="zh">`）
- `zh/Images/` = 配图（gif/png）

## 口径
- **只保留中文**：丢弃 `class="en"` 的块，保留 `class=zh/cn`。
- **一章一篇**（按 index.html 章序），`NN-标题.md` 前缀 = 字典序即书序 → 免归位。
- 根级 `00-说明.md`（README）+ `90-勘误.md`（Errata.md）。
- 图：`../Images/x` → 拷到导入根 `Images/` 并改写引用 → `yuque_rewrite_images.py` 传 CDN → 删 `Images/`。

## 四个坑（build.py 已处理）
1. **源 XHTML `<p>` 未闭合** → `html.parser` 会把后续整章内容吞进最后一个 `<p class="zh">`（本章 87KB 目录树只剩 2KB 的假象）→ **必须用 `html5lib` 解析器**（按 HTML5 规则自动闭合 p）。
2. **章标题只在首个 `<h1>` 的 `zh/cn` 类里**；`chapter-xml`/`chapter-html` 的 h1 无类且纯英文 → 需回退（取第一个含 CJK 的 h1，再回退第一个 h1）。
3. **每章尾部固定 footer**（`Copyright Jan Newmarch` / `Flattr/PayPal` 捐赠段 + `paypalobjects` 追踪像素 `<img>` + `<form>`）→ 整块剥。
4. **class-less 的「英文标题+中文标题」相邻同级对**（如 `<h2>Introduction</h2><h2>介绍</h2>`）→ 折叠时丢掉英文那条。

## 复现
```bash
python3 yuque_repo_import.py prep --url https://github.com/astaxie/NPWG_zh --dir <work>
python3 build.py                       # 产出 build/
python3 yuque_rewrite_images.py build img_map.json --throttle 1.5
find build -type f ! -name '*.md' -delete && find build -type d -empty -delete
python3 yuque_tree_import.py --root build --book <id> --progress progress.json --toc-md
```

## 结果
17 节点（0 目录 / 17 文档），28 图 CDN（30 处引用），六查全绿（错位 0 / 幽灵 0 / word_count 17/17>0 min 113 / 回读 0 异常 / 根序正确 / TOC==本地）。
