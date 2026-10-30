# fortran-zjding — USTC《Fortran77和90/95编程入门》→ 语雀

- **源**：http://micro.ustc.edu.cn/Fortran/ZJDing/（丁泽军，中国科技大学天文与应用物理系，2001-10；Word 2002 导出的 HTML 教程，7 章 20 节）
- **库**：85148654 ／ slug `fortran-zjding-20261030`（网站口径，分组「文章收集」36149506）
- **产物**：7 章目录 + 20 节文档 + 00-说明 = 28 节点；71 个示例源文件（GBK/UTF-8）内联为代码块；139 张公式/流程图传 CDN

## 复用流程

```bash
# 1) 抓页面（index + 20 个 Sec 页）
mkdir -p /tmp/f95/raw
for p in Sec1-1 Sec1-2 ... Sec7-2; do curl -sS -o /tmp/f95/raw/$p.htm http://micro.ustc.edu.cn/Fortran/ZJDing/$p.htm; done

# 2) 抓示例源码（example/*.f|f90，GBK）
#    见 build.py 内 load_code()（gb18030 兜底）

# 3) 生成 clean 树（含 ../images/ 引用与 images/ 池）
python3 build.py /tmp/f95/clean

# 4) 传图 → 重写 CDN → 删图目录
python3 ../../scripts/yuque_rewrite_images.py /tmp/f95/clean /tmp/f95/imgmap.json --throttle 3
rm -rf /tmp/f95/clean/images

# 5) 建库 + 导入（toc-md）
python3 ../../scripts/yuque_repo_import.py create-book --name "Fortran77和90/95编程入门（2026-10-30）" --slug fortran-zjding-20261030 --desc "..."
python3 ../../scripts/yuque_tree_import.py --root /tmp/f95/clean --book <id> --progress /tmp/f95/progress.json --toc-md
```

## 结构要点

| 项 | 处理 |
|---|---|
| 层级 | Word `<p>` 的 `font-size`：22pt=章/节标题（章标题以「第N章」开头），16pt=二级节，`color:red` + `^[a-z]\)`=三级节 |
| 示例代码 | `example/*.f|f90` 外链 → 抓回内联为 ```fortran；GBK 用 gb18030 解码 |
| 公式/图 | MathType/Visio 图 → `../images/<page>_<file>` → CDN；12×12 装饰 GIF 丢弃 |
| 列表 | `mso-list` 段落 → `- `（**先于**缩进判代码，防缩进列表被误判成代码） |
| 上下标 | `<sup>x</sup>`→`^{x}`、`<sub>x</sub>`→`_{x}` |

## 坑（详见 references/website-crawl-to-yuque.md 坑 87）

1. **VML 藏在 `<!--[if gte vml 1]>` 条件注释里**，bs4 的 `Comment` 是 `NavigableString` 子类 → 不显式跳过就会把整段 VML 漏进正文。
2. **示例是外链不是内嵌**，必须逐文件抓回内联。
3. **图引用是相对 md 目录**（`yuque_rewrite_images.py` 口径）→ 多级目录要写 `../images/…`。
