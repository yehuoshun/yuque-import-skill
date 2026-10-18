# LearnOpenGL CN（MkDocs 教程站）→ 语雀

实战：`LearnOpenGL-CN/LearnOpenGL-CN` @`3315608`（默认分支 `new-theme`）→ 库 84708519，82 节点（15 目录 / 67 文档）。
口径与坑见 `references/github-repo-to-yuque.md` **坑 42**。

## 复用流程

```bash
# 1. 稀疏克隆（仓库 ~220MB，只取 docs/ 省时间；注意分支是 new-theme）
git clone --depth 1 -b new-theme --filter=blob:none --sparse <repo> && cd <repo> && git sparse-checkout set docs
# 2. 生成导入根：docs/* 提到根，剔主题脚手架 css/ mathjax/（正文不引用）
# 3. 资源重写（图 → CDN；mp4/zip/rar → type=attachment 附件）
python3 rewrite_assets.py <clean_dir> <img_map.json> --throttle 5      # 先 --dry 核数
# 4. 删 img/ 与 data/ 目录后导入
python3 ../../scripts/yuque_tree_import.py --root <clean_dir> --book <id> --progress <p> --toc-md
# 5. 根级 DOC 归位（toc-md 会把根级 DOC 排到 TITLE 之后）
python3 fix_root_order.py <book_id>    # 先改文件里的 EXPECT 为期望根级顺序
```

## 本仓特有的三个点

1. **相对路径按渲染后站点 URL 深度写**（不是按文件位置）：`01 Getting started/05 Shaders.md` 里 `../img/...`、嵌套目录 `../../../img/...`
   → 通用重写脚本报 26 处本地缺失；`rewrite_assets.py` 用「按 md 目录解析 → 逐级剥 `../` → 后缀唯一匹配」三级兜底。
2. **`<video src="...mp4">` 要单独正则**，上传走 `type=attachment`（返回 `yuque.com/attachments/...`，会话门控，同 PDF 附件性质）。
3. **量级**：369 个资源（358 图引用 + 20 文件引用）`--throttle 5` ≈ 27 分钟，0 失败（贴着 ~500/窗口 429 红线，别调快）。

## 结果（2026-10-18）

82 节点（15 目录 / 67 文档）；toc-md PUT 1.1s；对账错位 0；四查全绿（路径唯一 / 集合相等 / 幽灵 0）；67 篇逐篇回读 0 差、word_count 无 0；根级 4 DOC 归位 4 轮收敛。
版权：译文 CC BY-NC 4.0，图片素材 © Joey de Vries 保留所有权利 → 只进私有库。
