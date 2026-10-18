# legado「阅读」APP 资源索引站（aoaostar/legado）→ 语雀 实战样例

> 2026-10-18 老板拍板「B = 索引 + 附件（原版 + 解析双轨）/ 新规则：库描述必须标注来源」；
> 库 id **84711589**、slug `legado-fd0ec7f9`、分组「开源项目」(57018723)、private。
> 源：`https://github.com/aoaostar/legado` @ **fd0ec7f9**（默认分支 **`release`**；站点 <https://legado.aoaostar.com>）

## 仓库形状（资源索引型，不是书）

- `README.md`（10KB）= CI 生成的**分类目录**：`<h2 id="id_N">` 6 个分类 + 每条带 直链 / `legado://` 一键导入 / 来源网站 / 条数 / 更新时间 / 同步时间
- `index.html`（12.7KB）= 同一份目录的网页版
- `sources/` = **20 个资源文件 / 21 条引用 / 48.8MB**（最大 `b778fe6b.json` 20MB / 3907 条书源）
- `CNAME` / `sources/cache.lock` / `.github/workflows/build.yml` = 站点与 CI 产物（不入库）

6 分类 21 条：书源 7 / 订阅源 2 / 净化规则 1 / 阅读排版 1 / 主题 4 / 在线朗读引擎 6。

## 为什么走「原版 + 解析」双轨（别直接导 JSON）

直接把 20MB JSON 当文档导 → 命中 512KB 切分，`b778fe6b.json` 会碎成 40 个分片文档，
既丑又把「原件」当正文（历史版本正是这么错的）。老板口径：**原件该走附件、正文该是可读的解析**。

## 产出结构（32 节点 = 2 目录 / 30 文档）

```
00-前言.md                     来源（站点+仓库+commit+上游同步时间）/ 库结构 / 怎么用 / 口径
01-原版附件.md                 原版轨：21 条 → 分类/名称/条数/📎原件/直链/legado:// 一键导入
02-书源.md … 07-在线朗读引擎.md   解析轨索引：6 分类各一篇
08-解析/                       解析轨正文
  README.md                    （原件原样）
  index.html                   （原件原样，入库会包 ```html 围栏）
  sources/<名>.json.md          20 篇：逐条转表
```

## 解析规则（各类型 → markdown 表）

| 原件形状 | 解析成 |
|---|---|
| `bookSourceName/bookSourceUrl` 数组（书源） | `# ｜ 名称 ｜ 网址 ｜ 分组 ｜ 启用` |
| `sourceName/sourceUrl` 数组（订阅源） | 同上 |
| `pattern/replacement` 数组（净化规则） | `# ｜ 名称 ｜ 分组 ｜ 启用 ｜ 正则`（正则截 90 字） |
| 单对象（主题 `themeName`+颜色） | `字段 ｜ 值` |
| `name/url` 数组（httpTTS 朗读引擎） | `# ｜ 名称 ｜ 接口 URL` |
| `.zip`（阅读排版，内含 `readConfig.json`） | 压缩包清单 + 内层 JSON 字段表 |

**体积暴降**：20MB 原件 → 303KB 文档；全部 <512KB → **零分片**（历史版本 95 个分片）。

## 原版轨（附件）

```python
# type=attachment，MIME 按扩展名；大文件 timeout 300s；5s 节流；attach_map.json 断点续传
url = "https://www.yuque.com/api/upload/attach?attachable_type=User&attachable_id=<uid>&type=attachment&ctoken=<ctoken>"
```

实测：20 文件（含 10.8MB / 6.9MB×2 / 20MB）全传成功；带 cookie `curl -L` 复拉
**md5 全对**（`b778fe6b.json` 20,987,130 B 逐字节一致）。

## 踩坑

1. **同一文件被两条引用**：上游 README 的「月下自酌听书TTS合集」与「纵横不败大佬TTS听书源更新」
   都指 `856adf0e.json` → 附件按**文件名**去重（20 个），索引表按**条目**各列一行（21 行）。
2. **根级 TITLE 会排到根级 DOC 之前**（与老坑 29 相反）→ 一发
   `PUT /toc {action:appendNode, action_mode:sibling, node_uuid:<08-解析>, target_uuid:<最后一个根级DOC>}` 归位。
3. **非 md 文件（index.html）入库会包 ` ```html ` 围栏且吃掉首部换行** → 回读比对要按
   `"```html\n\n" + src.lstrip("\n") + "\n```"` 算（差 1 字符不是丢内容）。
4. 大文件上传偶发慢：`timeout=300` + 5s 节流 + 429/5xx 退避（沿用附件接口的账号级风控口径）。

## 复用

```bash
# 1) 克隆镜像（默认分支记得改 release）→ 2) 生成解析轨 + 索引（无附件链接）
python3 build.py prep
# 3) 上传原件附件（断点续传 attach_map.json）
python3 build.py upload
# 4) 再跑一次 prep 把附件 URL 灌进索引 → 建库 → move-stack → toc-md 导入
python3 build.py all
```

脚本顶部改 4 处：`SRC`（镜像路径）、`OUT`（clean_dir）、`COMMIT`、`ROOT`。

## 验收（四查全绿）

- 本地 32 == TOC 32 == docs 30 + TITLE 2；全路径唯一 True；幽灵 docs total 30 == TOC DOC 30
- 根级序 == 本地序（`00-前言 … 07-… , 08-解析`）
- **30 篇逐篇回读 0 差 0 空**；附件抽 3 个（含 20MB）`curl -L` 200 + md5 一致
- `toc-md` 目录树 32 行 → PUT **0.5s**，结构核对 PASS，0 失败