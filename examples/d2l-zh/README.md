# 案例：MyST/Sphinx 书站的「md 源仓库」取法（《动手学深度学习》zh.d2l.ai，2026-10-21）

触发链接 `https://zh.d2l.ai` —— 阿斯顿·张、李沐、扎卡里·C·立顿、亚历山大·J·斯莫拉《动手学深度学习》在线版
（Sphinx 2.0.0 静态站）。

**与 `examples/hrl-boyuai` 正好相反的取法**：两边站上公式都是 MathJax **SVG、无 alttext、TeX 源不可得**
（hrl 只能「公式当图」）；但 d2l 的源仓库 **`d2l-ai/d2l-zh`（Apache-2.0，master）里就是 `.md` 源、
公式是真 LaTeX** → **不爬 HTML，改吃仓库 md**；站点 HTML 只当**标题/编号 oracle**（下面第 2 点）。

## 结论先行

| 项 | 值 |
|---|---|
| 库 | `动手学深度学习（20261021）` id=**84822487** slug=`d2l-zh-20261021` |
| 分组 | 「文章收集」stack 36149506（网站口径） |
| 源 | `d2l-ai/d2l-zh` master @ `e6b18ccea71451a55fcd861d7b96fddf2587b09a` |
| 节点 | **156**（140 DOC = 前言/安装/符号/16 章正文/参考文献 + 16 章节目录 TITLE） |
| 图 | 184 张（源 `img/` 261 svg + 92 png + 14 jpg 的引用去重后全传 CDN） |
| 口径 | **只留 PyTorch**（站上 4 个框架选项卡：mxnet 默认/pytorch/tensorflow/paddle） |
| 正文 | 标题编号 923 处 / 公式编号 76（= 源 `:eqlabel:` 76 全覆盖）/ 表编号 7 / 参考文献 159 条 |
| 验收 | 幽灵 **0**、占位文档 **0**、fail **0**（六查口径） |
| 耗时 | 传图 ~10min（184 张，throttle 3）+ 导入 ~6min（toc-md） |

## 复现（5 步）

```bash
# 1) 浅克隆源仓库（gh-proxy 加速）
git clone --depth 1 https://gh-proxy.com/https://github.com/d2l-ai/d2l-zh.git src

# 2) 抓站点全部页面（只当 oracle：标题带编号 + numref 的渲染文本）
python3 fetch_pages.py        # → site/chapter_x__y.html（140 页）
#    注：d2l_nav.json（140 条「路径 + 中文标题」，决定目录顺序）由站点侧栏导航整理而来

# 3) 抽映射表
python3 build_refmap.py       # → refmap.json：numref 339 / defs 778（图·表·式·节编号）/ key2ref 159（bibkey→"作者 et al., 年"）
python3 analyze_tabs2.py      # 证据：无 #@tab 标记的 cell = mxnet 面板（见下第 1 点）

# 4) 转换 + 组装中文目录树
python3 convert.py            # 转换规则见下第 3 点（build.py 会 import convert.py）
python3 build.py              # → clean/：00-前言 / 01-安装 / 02-符号 / 03..18-第N章 XX/ / 19-参考文献.md

# 5) 图片：先传 CDN 重写引用，**再把图片目录移出导入根**，最后导入
python3 ../../scripts/yuque_rewrite_images.py <tmp_workdir>/clean <tmp_workdir>/img_map.json --user-id 25689388 --throttle 3
mv <tmp_workdir>/clean/_img <tmp_workdir>/_img_hold      # ← 必须！见坑 ③
python3 ../../scripts/yuque_tree_import.py --root <tmp_workdir>/clean --book <book_id> --progress progress.json --toc-md
python3 ../../scripts/yuque_check_ghosts.py --book <book_id>
```

（`src/` `site/` `d2l_nav.json` `refmap.json` 都放在本目录下即可；`fetch_pages.py` / `build_refmap.py` /
`analyze_tabs2.py` 支持 `SRC_DIR` / `SITE_OUT` / `NAV_JSON` / `BIB` / `REFMAP_OUT` 环境变量覆盖。）

## 关键实现

### 1. 四个框架选项卡 → 只留 PyTorch

站上每章顶部有 mxnet（默认激活）/ pytorch / tensorflow / paddle 四个面板；源 md 里用 MyST 的
`:begin_tab:` + ```{.python .input} 单元格首行的 `#@tab` 标记区分。

- **无 `#@tab` 标记的单元格 = mxnet 变体**（`analyze_tabs2.py` 拿站上各面板的代码块与源单元格逐块比对，
  确认未标记者与 mxnet 面板一致）→ 所以规则是：**只留 `#@tab pytorch` / `#@tab all`**，无标记的一律丢。
- 文本块同理：`:begin_tab:` 里的框架列表**含 pytorch** 才保留（`mxnet, tensorflow` 这种多框架列表要按逗号拆开判断）。
- 库描述里注明「内容为 PyTorch 版」，读者不会拿 mxnet 代码对不上。

### 2. 站点 HTML 当 oracle（2 个用途）

1. **标题编号**：源 md 标题不带编号（`## 标量`），站上是 `<span class="section-number">2.3.1. </span>` →
   按**页面内顺序**逐个匹配补出 `## 2.3.1 标量`（本次 923 处；前言/安装/符号等无编号章节自然跳过）。
   比对前要**归一化**（去空白与 `[**…**]` 强调标记——d2l 源里 `## [**定义损失函数**]` 在站上是纯标题）。
2. **交叉引用文本**：`:numref:`/`:eqref:`/`:ref:` 的渲染结果**只能从站上取**（`<span class="std std-numref">图1.1.1</span>`），
   源 md 里只有标签名。`build_refmap.py` 从抓下的 HTML 抽三张表：
   - `numref`（339）：引用处 → 站上渲染文本（「图1.1.1」「2.2节」「1节」）
   - `defs`（778）：定义处编号（图/表/式/小节），引用表缺失时兜底
   - `key2ref`（159）：`d2l.bib` 的 bibkey → 「Goodfellow et al., 2016」（多引文按站上 `; ` 连接）
   - 标签要按 Sphinx 规则归一：`lower().replace('_','-').replace('+','-')`（`eq_sgd-xt+1-xstar` 靠这条对上）
   - 站上只有 **4 个** 真·坏书签（源里标签写错），在 `convert.py` 的 `OVERRIDE` 里手工兜底

### 3. 转换规则清单（`convert.py`）

| 源 | 目标 |
|---|---|
| ```{.python .input} + `#@tab pytorch/all` | ```python（去掉标记行） |
| 无标记 / mxnet / tensorflow / paddle 单元格 | 整块丢弃 |
| `:cite:` | `(作者 et al., 年)`，多篇 `; ` 连接 |
| `:numref:` / `:eqref:` / `:ref:` | 站点渲染文本 |
| `:label:` / `:width:` | 删除（编号已进标题） |
| `:eqlabel:` | 删该行，**在公式块后补一行 `（2.3.1）`**（语雀不吃 `\tag`） |
| 图 `![cap](../img/x.svg)` | alt 改成 `图7.2.1 cap`（用紧随的 `:label:` 换号），路径后处理统一改写 |
| 表格（`|` 开头） | 表前补 `**表14.5.1**` 一行 |
| ```toc / ```eval_rst | 整块丢（eval_rst 里的 `autoclass/autofunction` 名单转成 `* name` 清单） |
| `(**强调**)` / `[**强调**]` | `**强调**` |
| 开头 H1 | 丢弃（沿用 hrl 口径：正文从 `##` 起，文档标题=文件名） |

### 4. 目录/命名口径（`build.py`）

- 根级：`00-前言.md` `01-安装.md` `02-符号.md`；章节目录 `03-第1章 引言` … `18-第16章 附录：深度学习工具`；`19-参考文献.md`
- 章内顺序用**站点原标题**：章首页 `2. 预备知识.md` 排在 `2.1 数据操作.md` 之前（`"2. "` 的空格 < `"2.1"` 的 `1`，
  `sorted(os.listdir)` 天然正确，不用加序号前缀）
- 参考文献：源 `zreferences.md` 近乎空（autodoc）→ **从站上 zreferences 页重建**（159 条，`<dt>` 标签 + `<dd>` 正文）
- 16.6 `d2l API 文档`：源里是 eval_rst 自动文档块、站上也是空页 → 只保留标题 + 成员名单，不硬编内容

## 坑（本次实踩）

**① 裸 `:end_tab:` + 多框架 `:begin_tab:` 列表 → 转换器会「吞掉文件尾」（最险的一条）**
d2l 源的块结束标记是**裸的** `:end_tab:`（不带反引号参数），而 `:begin_tab:` 参数可能是**多框架列表**
（`:begin_tab:`mxnet, tensorflow``）。若正则只认单框架 + 带参数的 `:end_tab:`：
begin 行不会被识别 → 后一个单框架 `:begin_tab:`pytorch`` 便一路扫到 **EOF**，**整篇后半段被当成「一个 tab 段落」原样吞掉**
（首跑症状：某文件只 911B、图片没重写、`#@tab`/`_origin` 之类指令残留 29 处、正文静默缺失）。
修法三件套：`begin_tab` 参数按 `[,\s]+` 拆列表判 `pytorch`；`end_tab` 正则兼容 **两种**（`(?:`[^`]*`)?`）；
扫描**找不到闭合要兜底**（当普通文本处理，绝不吞到 EOF）。**所有「跨行块」扫描都要加未闭合兜底**——同类隐患还有代码栅栏。

**② `:eqlabel:` 不能当普通 meta 行提前删掉**
它必须在「删该行 + 在公式块后补编号」的后处理里处理；若和 `:label:`/`:width:` 一起丢，**公式编号全灭**（本次 76 处）。

**③ 图片目录放进导入根 = 每张图变成一篇占位文档（硬规则 10）**
`yuque_tree_import.py` 的 `walk()` 把导入根下**所有文件**当节点：首跑节点数 **341**（= 140 md + 184 图 + 17 目录）
而不是 156。修法：`yuque_rewrite_images.py` 可以在根内做完（它只改 md 引用），但**导入前必须把 `_img/` 移出导入根**，
验收通过后再删。本文档顶部第 5 步就是这个顺序。

**④ 断点停手的孤儿 doc（坑 49 同族）**
停手那一刻 `POST /docs` 已成功但账本没落盘 → 服务端多 1 篇（本次 `10.2 注意力汇聚…`）。
用 `yuque_check_ghosts.py` 抓出、`DELETE` 后重跑即可，**不要直接 resume**（会重复建）。

## 验收记录

- `yuque_check_ghosts.py` 退出码 0：docs total **140** == TOC DOC **140**
- 全库占位扫描：140 篇 `word_count` **全部 >0**
- 抽查：`2.3 线性代数`（标题 2.3.x、公式（2.3.x）、wc 8001）、`7.2 使用块的网络（VGG）`（图 CDN）、`19-参考文献.md`（wc 4602）
- 中途停手 → 移图续跑 → 精确 156 节点，**fail 0**