# examples/zguide-cn —— 《ZMQ 指南》中文版（anjuke/zguide-cn @ 91d94b7）

- 源仓库：https://github.com/anjuke/zguide-cn（扁平仓：`README.md` 目录 + `chapter1~5.md` 正文 + `chapterN.txt` gitdown 源 + `images/` 69 图 + `bin/` gitdown 工具）
- 库：85147220 / slug `zguide-cn-91d94b7` / https://www.yuque.com/yehuoshun/zguide-cn-91d94b7
- 结果：78 节点（5 章 TITLE + 73 文档），六查全绿。

## 复用命令

```bash
python3 scripts/yuque_repo_import.py prep --url git@github.com:anjuke/zguide-cn.git --dir <tmp>
# 见 examples/zguide-cn/build.py：读 <clean> 生成 <out>（章目录 + 分节文档 + 00-说明）
python3 examples/zguide-cn/build.py
# 图：build.py 已把 GitHub raw 绝对外链改回 ../images/x.png
python3 scripts/yuque_rewrite_images.py <out> <imgmap.json> --throttle 3
rm -rf <out>/images            # 硬规则 10：图片目录不进导入根
python3 scripts/yuque_tree_import.py --root <out> --book <id> --progress <p> --toc-md
```

## 形态要点（详见 references/github-repo-to-yuque.md 坑 81）

1. **chapter1.md 全文重复书首**（`# ZMQ 指南` + 作者/致谢/授权），chapter2~5 无 → 剥离，改由 `00-说明.md` 承载书首，避免每章都挂一遍致谢。
2. **配图是 GitHub 绝对外链** `https://github.com/anjuke/zguide-cn/raw/master/images/chapterN_M.png`（自己仓库的 raw 链）——`yuque_rewrite_images.py` 对外链一律跳过，不先改写回 `../images/...` 就会静默留外链/裂图。
3. **章标题取 README 目录**（源 `chapter4.md` 的 H2 漏了「第四章」前缀）。
4. 拆节跟踪代码围栏（`awk` 式 `^###` 会误中围栏内 `#` 注释），半角 `/` 洗全角（`异步C/S结构`→`异步C／S结构`）。
