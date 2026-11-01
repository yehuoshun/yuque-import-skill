# Ext4.1.0 中文文档（extjs-doc-cn/ext4api，Sencha Docs JSONP 数据源）

> 实战：2026-11-01 fpb52 #179，库 85213682 / slug ext4api-zh-d7288dd，497 节点（57 目录/440 文档）六查全绿

## 数据源特征

- 源仓库 `extjs-doc-cn/ext4api`（分支 **gh-pages**）是 Sencha Docs 在线文档站：**正文不是 md/HTML 页，而是 `output/<ClassName>.js` 数据文件**——每文件是 JSONP 包装（`Ext.data.JsonP.Ext_button_Button({...});`）的类文档 JSON
- 转换目标：类正文全在 JSON 的 **`html` 字段**（大文件 100KB~500KB，含类描述 + cfg/property/method/event 全量成员，中文翻译在其中）；`name` 字段 = 类名
- 439 个类按命名空间分目录（`Ext.app`/`Ext.data`/…，55 个 `Ext.*` 根级类集中 `00-Ext 核心`）

## 转换器要点（build.py）

1. **JSONP 剥壳**：`^Ext\.data\.JsonP\.\w+\((.*)\)\s*;?\s*$` → `json.loads(group(1))`
2. **剥 `<pre class="hierarchy">`**（继承树导航，噪音 + 站内死链多）
3. **html5lib + bs4 渲染**：member div（`class~=member`）单独处理为 `#### name : type` + `> 定义于 <defined-in>` + short/long 描述（short 是 `…` 截断预览，long 优先）
4. **站内链 `#!/api/...` → 纯文本**；`view-source` 链接剥；外链保留
5. **围栏外字面 HTML 标签转义**（`<div>Contents</div>` 示例 → `&lt;div&gt;`），按 ``` 围栏 split 只转围栏外
6. 真实配图（`<img src="images/...">`）复制到 site 同相对路径，子目录 md 引用加 `../` 前缀 → 走 rewrite CDN

## 坑（2026-11-01 实捶）

1. **源数据畸形嵌套**：member div 会嵌在**另一个 member 的 description 里**（甚至嵌在 `<table>` 单元格）→ p 分支遇块级子元素必须 `render_children` 递归，不能用 `txt()`/`get_text` 吞（否则内层 member 标题+描述糊成一团且 view-source 残留）
2. **文档示例里的字面 `<script>` 标签不闭合** → html5lib 把后续整个 body 当 script raw text 吞光 → 解析前先 `re.sub(r'<script\b[^>]*>', '&lt;script&gt;', html)` 转义
3. slug/文件名正则**字符类里的 `\s` 陷阱**：raw string 写 `r"[\\"..."\s]`（双反斜杠）会被正则解析成「字面反斜杠 + 字母 s」→ **所有 s 被替换成 `-`**（node inspector → node in-pector）；要空白类必须单反斜杠 `\s`
4. 页面同图两种引用形态（`img/x.png` 真图 vs 裸 `x.png` 404）按 `img/` 前缀判定，别把真图删了

## 用法

```bash
SRC=tmp/fpb179-ext4api-src   # clone -b gh-pages
python3 build.py             # 读 $SRC/output/*.js → site/
# 图：yuque_rewrite_images.py → 删 site/images
# 建库 + yuque_tree_import.py --toc-md 全量
```