# 深度学习500问（scutan90/DeepLearning-500-questions）→ 语雀

实战：`scutan90/DeepLearning-500-questions` @`6087a06`（默认分支 `master`）→ 库 **84856909**，
**81 节点（20 目录 / 61 文档 / 551 张图）**。口径与坑见 `references/github-repo-to-yuque.md` **坑 51**。

## 仓库形状

书型仓库（中文版 19 章），根目录混着站点脚手架：

```
DeepLearning-500-questions/
├── ch01_数学基础/ ... ch19_软件专利申请及权利保护/   ← 正文
│     └── 第X章_*.md + readme.md + modify_log.txt + img/（或 media/）
├── README.md            简介 + 作者简介
├── 目录预览.md          全书目录
├── _sidebar.md / index.html / docsify.js   ← docsify 站点脚手架（剔）
├── English version/     未完成翻译（只有 4/19 章，且不在 _sidebar 里）（剔）
├── 深度学习500问-Tan-00目录.docx          ← 剔
└── qun.png / LICENSE / .DS_Store / .gitignore / .nojekyll / 深度学习2020（剔）
```

- **站点 = docsify（index.html + `_sidebar.md` 驱动）→ 内容就是仓库 md，不用爬 HTML，也不用 oracle**
- ch18 有**两个**章节目录（`后端架构选型、离线及实时计算` + `后端架构选型及应用场景`，后者在 sidebar 里编号 19）→ 两个都保留，别当重复删
- ch07 有 `ch7.md`（正文）+ `ch7.pdf`（未引用）；ch17 多一篇 `17.8.1 NCNN部署.md`；两章带 0 字节 `modify_log.txt` 是正常的

## 复用流程

```bash
# 0) 前置
cd code/yuque-import-skill && source ~/.openclaw/secrets/credentials.env

# 1) prep（克隆 + 硬同步 + 干净副本 + 节点数）
python3 scripts/yuque_repo_import.py prep \
  --url git@github.com:scutan90/DeepLearning-500-questions.git \
  --dir /home/admin/.openclaw/workspace/tmp
# → commit 6087a06 / clean_dir=...-6087a06-clean / 1326 节点

# 2) 生成导入根（只留正文：ch*/ + README.md + 目录预览.md）
SRC=...-clean; STAGE=...-stage; mkdir -p $STAGE
for d in $SRC/ch*/; do cp -a "$d" $STAGE/; done
cp -a $SRC/README.md $SRC/目录预览.md $STAGE/
rm -f "$STAGE/ch07_生成对抗网络(GAN)/ch7.pdf" \
      "$STAGE/ch18_后端架构选型及应用场景/img/新建文件夹/emnlp2018.pdf"

# 3) 修脏图片引用（Windows 反斜杠 / 绝对路径 / URL 编码）—— 见下「本仓特有的点」
python3 examples/deeplearning-500-questions/fix_refs.py $STAGE

# 4) 带空格文件名的图先单独传（主脚本会截断）—— 再跑主脚本
python3 examples/deeplearning-500-questions/upload_space_imgs.py $STAGE <img_map.json>
python3 scripts/yuque_rewrite_images.py $STAGE <img_map.json> --throttle 5   # 551 张 ≈ 46 分钟

# 5) 连图带目录删净（ch19/img 只剩 1.doc → 一并删，见「未上传」口径）
for d in $STAGE/ch*/; do rm -rf "$d/img" "$d/media"; done

# 6) 建库 + 归组 + 导入 + 收尾
python3 scripts/yuque_repo_import.py create-book --name "DeepLearning-500-questions（6087a06）" \
  --slug deeplearning-500-questions-6087a06 --desc "<见下>"
python3 scripts/yuque_repo_import.py move-stack --book-id <id> --stack-id 57018723
python3 scripts/yuque_tree_import.py --root $STAGE --book <id> --progress <p> --toc-md
python3 examples/deeplearning-500-questions/fix_root_order.py <book_id>   # 根级 DOC 归位（坑 29）
```

## 本仓特有的点（可复用）

1. **源引用是「Windows 手写 md」的典型脏**，四类都得治（这是最大价值点）：

   | 类型 | 实例 | 数量 |
   |---|---|---|
   | 反斜杠 | `img\ch14\思维导图.png` | 16 |
   | 盘符绝对路径 | `H:/DeepLearning-500-questions/ch18_.../img/x.png`、`C:\Users\XinRui\Desktop\x.png` | 3 |
   | URL 编码的中文名 | `img/ch7/DCGAN%E7%BB%93%E6%9E%84%E5%9B%BE.png` | 5 |
   | 文件名带空格 | `img/ch8/Mask R-CNN-01.png`、`img/ch7/lsgan loss compare.png` | 5 |

   - 前 3 类：`fix_refs.py` 就地修（候选顺序 = 原样 → 反斜杠转正斜杠 → `unquote` → 组合；都不中再按 **basename 反查全树**，唯一命中才替换）→ 共修 21 处
   - 第 4 类：`yuque_rewrite_images.py` 为吃 `![alt](path "title")` 做了 `split(None, 1)`，带空格路径会被截断判「本地缺失」→ 用 `upload_space_imgs.py` 先单独传这 5 张（替换成 https 后主脚本自动跳过）
2. **上游真坏引用 14 处**：ch08 `CBNet-1..8` / `mmdetection.png`、ch09 `9.10.5-1..5` —— 仓库里根本没这些文件（作者改了名没更文），**修不了，原样留裂图**，别浪费时间找。
3. **非 PDF 本地资源（`ch19/img/1.doc`，专利模板）按硬规则 12 不上传**：正文引用保留原相对路径 + 加一句「（注：该 Word 模板为仓库本地文件，未上传语雀）」，**文件本体删掉**（留着会变成 `img` TITLE + 占位 DOC 两个垃圾节点）——注意 `toc-md` 重排目录不会删旧 doc，要 `DELETE /repos/{id}/docs/{id}` 清干净（本次 doc 289168169）。
4. **量级**：551 张图 × `--throttle 5` ≈ 46 分钟、0 失败 0 重试（贴 ~500/窗口 429 红线，别调快）；`img_map` 556 条全唯一。

## 结果（2026-10-22）

- 库 **84856909**（`yehuoshun/deeplearning-500-questions-6087a06`，分组「开源项目」57018723，private，61 项）
- 描述：`来源：https://github.com/scutan90/DeepLearning-500-questions @ 6087a06 ｜ 中文版正文 19 章 + 目录预览 + README；英文版未完成翻译、docsify 站点脚手架与 docx 原件未入库 ｜ 导入 2026-10-22`（147 字符，未触 250 上限）
- 81 节点（20 目录 / 61 文档）；toc-md 目录树 81 行一次 PUT 0.9s、结构核对 PASS、0 失败
- 根级顺序归位 4 轮收敛：`README.md → 目录预览.md → ch01 … ch19`（坑 29 同坑，连续第 N 版）
- 验收六查全绿：TOC 81 == 本地 81、全路径唯一 True、单文档映射 61/61 缺失 0、对账错位 0、幽灵 0（docs 61 == TOC DOC 61）、**61 篇 word_count 全 >0（最小 7）**、CDN 抽查 8/8 HTTP 200（556 URL 全唯一）
- 版权：书 © 谈继勇等，仓库 `LICENSE` 为 **GPL-3.0** → 只进私有库
