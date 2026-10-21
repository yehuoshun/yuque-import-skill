#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""【可复用】MkDocs/静态站源仓库：md 内本地资源（图片 / PDF / mp4·zip·rar）→ 语雀上传 + 重写（LearnOpenGL CN 实战产物）
比通用脚本多两件事：
  1) 路径归一化：源仓库的相对路径是按 MkDocs「站点 URL 深度」写的（`../img/` 从 `01 xxx/01.md`
     出发其实应指根下 img/；嵌套目录里还写成 `../../../img/`）→ 先按 md 所在目录解析，失败就
     逐级剥 `../` 再按导入根解析，最后按后缀唯一匹配。
  2) 按扩展名分流：图片走 upload_image(type=image)；**PDF 走 type=attachment**；
     其余非图片（mp4/zip/rar/7z）**默认不上传（2026-10-21 口径：附件只给 PDF）**，原文保留。
用法: python3 rewrite_assets.py <root> <map.json> [--throttle 5] [--dry] [--allow-attach]
"""
import argparse, json, os, re, sys, time, mimetypes, urllib.request, urllib.error, uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts"))
from yuque_tree_import import load_upload_cfg, upload_image  # noqa

MD_IMG = re.compile(r'(!\[[^\]]*\]\()([^)]+)(\))')
HTML_IMG = re.compile(r'(<img\b[^>]*?\bsrc=)(["\'])([^"\']+)(["\'])')
HTML_VIDEO = re.compile(r'(<video\b[^>]*?\bsrc=)(["\'])([^"\']+)(["\'])')
MD_FILE = re.compile(r'(\[[^\]]*\]\()([^)]+\.(?:zip|rar|7z|mp4|pdf))([^)]*\))')

IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
USER_ID = "25689388"


def is_ext(u):
    return bool(re.match(r'^(https?:|data:|mailto:|#)', u.strip()))


def attach_allowed(abspath, a):
    """2026-10-21 口径（硬规则 12）：附件只给 PDF；其余非图片资源默认不上传、原文保留。"""
    return os.path.splitext(abspath)[1].lower() == ".pdf" or a.allow_attach


def upload_attach(cookie, ctoken, path):
    """非图片资源：type=attachment，MIME 按扩展名。"""
    ext = os.path.splitext(path)[1].lower()
    mime = mimetypes.types_map.get(ext, "application/octet-stream")
    boundary = "----YuqueImport" + uuid.uuid4().hex
    with open(path, "rb") as f:
        data = f.read()
    body = b"\r\n".join([
        ('--' + boundary).encode(),
        ('Content-Disposition: form-data; name="file"; filename="%s"' % os.path.basename(path)).encode(),
        ("Content-Type: %s" % mime).encode(),
        b"", data, ('--' + boundary + '--').encode()])
    url = ("https://www.yuque.com/api/upload/attach?attachable_type=User&attachable_id=%s&type=attachment&ctoken=%s"
           % (USER_ID, ctoken))
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)
    req.add_header("Cookie", cookie)
    req.add_header("Referer", "https://www.yuque.com/")
    req.add_header("Origin", "https://www.yuque.com")
    for i in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read().decode())
            return d.get("data", {}).get("url") or None
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and i < 5:
                time.sleep(min(10 * (2 ** i), 120)); continue
            return None
        except Exception:
            if i < 2:
                time.sleep(2); continue
            return None
    return None


def get_url(abspath, key, a, cfg, mp):
    if key in mp:
        return mp[key]
    if a.dry:
        return "DRY"
    ext = os.path.splitext(abspath)[1].lower()
    if ext in IMG_EXT:
        u = upload_image(cfg["cookie"], cfg["ctoken"], USER_ID, abspath)
    else:
        u = upload_attach(cfg["cookie"], cfg["ctoken"], abspath)
    if u:
        mp[key] = u
        json.dump(mp, open(a.map, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("  ↑ %s -> %s" % (key, u[:70]), flush=True)
        time.sleep(a.throttle)
    else:
        print("  ✗ 上传失败 %s" % key, flush=True)
    return u


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"); ap.add_argument("map")
    ap.add_argument("--throttle", type=float, default=5.0)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--allow-attach", action="store_true",
                    help="允许非 PDF 资源走 type=attachment（2026-10-21 口径：附件只给 PDF，默认关）")
    ap.add_argument("--cookie-config",
                    default="~/.openclaw/workspace/skills/yuque-ai-mcp/config/config.json")
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    cfg = load_upload_cfg(a.cookie_config)
    if not cfg and not a.dry:
        print("cookie 不可用", file=sys.stderr); sys.exit(1)

    mp = json.load(open(a.map, encoding="utf-8")) if os.path.exists(a.map) else {}
    files = []
    for dp, dns, fns in os.walk(root):
        for f in fns:
            files.append(os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/"))
    idx = {f: f for f in files}

    def resolve(src, md_dir):
        s = src.strip().split(" ")[0].strip("\"'")
        if is_ext(s):
            return None, "external"
        cand = os.path.normpath(os.path.join(md_dir, s))
        if os.path.exists(cand):
            return os.path.abspath(cand), None
        p = s
        while p.startswith("../"):
            p = p[3:]
        p = p.lstrip("./")
        if p in idx:
            return os.path.join(root, idx[p]), None
        hits = [f for f in files if f.endswith("/" + p) or f == p]
        if len(hits) == 1:
            return os.path.join(root, hits[0]), None
        return None, "missing"

    stat = {"img": 0, "file": 0, "skip_noattach": 0, "missing": 0, "ext": 0, "fail": 0}
    for dp, dns, fns in os.walk(root):
        for fn in sorted(fns):
            if not fn.lower().endswith(".md"):
                continue
            p = os.path.join(dp, fn)
            txt = open(p, encoding="utf-8").read()
            md_dir = os.path.dirname(p)

            def sub(prefix, src, suffix, kind):
                apath, why = resolve(src, md_dir)
                if why == "external":
                    stat["ext"] += 1; return prefix + src + suffix
                if why == "missing":
                    stat["missing"] += 1
                    print("  缺失 %s : %s" % (os.path.relpath(p, root), src)); return prefix + src + suffix
                if kind == "file" and not attach_allowed(apath, a):
                    stat["skip_noattach"] += 1
                    print("  未上传(非 PDF) %s : %s" % (os.path.relpath(p, root), src))
                    return prefix + src + suffix
                key = os.path.relpath(apath, root).replace(os.sep, "/")
                u = get_url(apath, key, a, cfg, mp)
                if not u:
                    stat["fail"] += 1; return prefix + src + suffix
                stat[kind] += 1
                return prefix + u + suffix

            txt = MD_IMG.sub(lambda m: sub(m.group(1), m.group(2), m.group(3), "img"), txt)
            txt = HTML_IMG.sub(lambda m: sub(m.group(1) + m.group(2), m.group(3), m.group(4), "img"), txt)
            txt = HTML_VIDEO.sub(lambda m: sub(m.group(1) + m.group(2), m.group(3), m.group(4), "file"), txt)
            txt = MD_FILE.sub(lambda m: sub(m.group(1), m.group(2), m.group(3), "file"), txt)
            if not a.dry:
                open(p, "w", encoding="utf-8").write(txt)
    print("完成:", stat, "| map 条目", len(mp))


if __name__ == "__main__":
    main()