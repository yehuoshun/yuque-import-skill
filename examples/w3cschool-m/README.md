# w3cschool 手册抓取（m 站免挑战版）

2026-11-01 fpb52 #178 实战。库 85213131 / slug `electron-doc-w3cschool-20261101`。

## 源

`https://www.w3cschool.cn/electronmanual/`（w3cschool 收录的《Electron 中文文档》手册镜像）。

## ⚠️ WAF 挑战（2026-11-01 实捶，最重要）

**www.w3cschool.cn 有 ypre cookie 挑战**：
- 首次请求返回 `<script>` 挑战页（442B）：`abcd(a,b)=5*|3a-2b|` 算 `ypre_token2` + 固定格式 `ypre_authtoken`，`location.href` 重定向回原 URL
- **但带解出的 cookie 重试子页返回 404「认证失败」**——cookie 是每请求随机/一次性，解算 JS 算法也解决不了
- 纯无 cookie 慢速重试（间隔 6-10s）放行率约 1/3，62 页要 40+ 分钟且随时可能全封

✅ **正解：改抓移动版 `m.w3cschool.cn`（同一 URL 路径），无挑战直接 200**。iPhone UA 即可。

## 结构

- 目录容器：移动版首页 `.content-block`（**不是**桌面的 `#nestable_handbook`），链接是**绝对 URL**（`https://m.w3cschool.cn/electronmanual/xxx.html`），要正则抽 `/electronmanual/[^"]+` 并 dedup（「开始阅读」按钮与第一条目同 URL）
- 正文容器：`div.content-intro`（移动/桌面同款；#73 thinkcpp 用的 `div.view-body.think-editor-content` 是旧模板，新站已换）
- 62 篇扁平平铺，目录序 = 侧栏序

## 图片（外链形态）

w3cschool 手册图多为外链：cloud.githubusercontent（活）、atts.w3cschool（活）、camo.githubusercontent（**代理已死**，路径尾是 **hex 编码**的原始 URL——不是 base64！`bytes.fromhex(tail).decode()` 可解出原始地址，MSDN/Ubuntu 源多数也 503/404）→ 死的标「原图缺失」。

## 产物

- `build.py`：m 站抓取 + cookie 挑战兜底 + 正文转换（本目录）
