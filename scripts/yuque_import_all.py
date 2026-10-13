#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开源项目批量导入编排器（GitHub Actions / 手动通用）

把 repos.json 清单里的 GitHub 仓库按「开源项目流程」导入语雀：
prep(克隆/增量) → commit 账本去重 → create-book → move-stack → 全量导入 → 对账 → 验收四查 → 记账 → 钉钉汇报

用法:
  python3 yuque_import_all.py --repos repos.json --ledger last-imported.json \
      [--stack-id 57018723] [--workdir <dir>] [--login yehuoshun] \
      [--pend-sleep 60] [--pend-retries 3] [--only <过滤词>] [--dry] [--no-notify]

约定（2026-10-12 老板固化）:
  - 知识库名 = 项目名（commit id 8位）, slug = 项目名-commit, 描述 = <repo url> @ <commit>
  - 知识库分组 = 开源项目（stack 57018723）
  - 中间产物一律放 --workdir（CI 里走 actions/cache, 本地放 workspace/tmp）

认证:
  - v2 token: 环境变量 TOKEN_L91（CI secrets）或 ~/.openclaw/secrets/credentials.env（本地）
  - cookie/ctoken: 环境变量 YUQUE_COOKIE / YUQUE_CTOKEN（CI secrets, 脚本会写入 workdir/cookie.json）;
    本地缺省回退 scripts 默认路径（yuque-ai-mcp config.json）

钉钉:
  - 环境变量 DINGTALK_WEBHOOK 存在且未传 --no-notify 时, 跑完自动发汇报（消息必含 "GitHub" 关键词）
"""
import argparse, json, os, re, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://www.yuque.com/api/v2"
DEFAULT_STACK = 57018723       # 开源项目
DEFAULT_LOGIN = "yehuoshun"


def run_script(name, args, env=None):
    """调同目录下的既有脚本（CLI 即接口, 保持各脚本解耦）"""
    e = os.environ.copy()
    e.setdefault("PYTHONIOENCODING", "utf-8")
    if env:
        e.update(env)
    return subprocess.run([sys.executable, os.path.join(HERE, name)] + args,
                          capture_output=True, text=True, env=e)


def cookie_config_path(workdir):
    """CI 环境把 cookie 写进 workdir/cookie.json, 供 move-stack/导入脚本 --cookie-config 使用"""
    cookie = os.environ.get("YUQUE_COOKIE")
    if not cookie:
        return None  # 本地回退脚本默认路径
    path = os.path.join(workdir, "cookie.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"cookie": cookie, "ctoken": os.environ.get("YUQUE_CTOKEN", "")}, f, ensure_ascii=False)
    return path


# ---------- 输出解析（脚本输出格式固定, 正则提取） ----------
def prep_parse(out):
    d = {}
    for line in out.splitlines():
        m = re.search(r"\[prep\] repo=(\S+) branch=(\S+) commit=(\S+)", line)
        if m:
            d["repo"], d["branch"], d["commit"] = m.group(1), m.group(2), m.group(3)
        m = re.search(r"\[prep\] nodes=(\d+) \(dir (\d+) / file (\d+)\)", line)
        if m:
            d["nodes"] = int(m.group(1))
        m = re.search(r"\[prep\] clean_dir=(\S+)", line)
        if m:
            d["clean_dir"] = m.group(1)
    return d


def create_book_parse(out):
    m = re.search(r"\[create-book\] id=(\d+)", out)
    if not m:
        raise RuntimeError("create-book 输出解析失败: " + out[-500:])
    return int(m.group(1))


# ---------- 验收四查（复用 reconcile 的路径重建, 不重复造轮子） ----------
def verify(book, progress_path):
    sys.path.insert(0, HERE)
    from yuque_toc_reconcile import build_path_map  # noqa: E402
    from yuque_tree_import import api, load_token  # noqa: E402

    token = load_token("TOKEN_L91")
    toc = api(token, BASE, "GET", f"/repos/{book}/toc")["data"]
    prog = json.load(open(progress_path, encoding="utf-8"))

    # 期望 TOC 节点数 = 目录 + 文档段数（超限拆分文档算多段）
    expected_toc = 0
    doc_ids = set()
    expected_paths = {}
    for rel, v in prog["nodes"].items():
        segs = v.get("segments") if isinstance(v, dict) else None
        if segs and len(segs) > 1:
            expected_toc += len(segs)
            for i, s in enumerate(segs, 1):
                expected_paths[s["uuid"]] = f"{rel} ({i}/{len(segs)})"
                doc_ids.add(s["doc_id"])
        elif isinstance(v, dict) and "uuid" in v:
            expected_toc += 1
            expected_paths[v["uuid"]] = rel
            if v.get("type") == "doc":
                doc_ids.add(v.get("doc_id"))

    actual_paths = build_path_map(toc)
    errors = []

    # 1. TOC 节点数 == 账本节点数
    if len(toc) != expected_toc:
        errors.append(f"TOC 节点 {len(toc)} != 账本 {expected_toc}")

    # 2. 错位/多余节点: 实际路径 != 期望路径
    misplaced = [n["title"] for n in toc
                 if n["uuid"] in expected_paths and actual_paths[n["uuid"]] != expected_paths[n["uuid"]]]
    extra = [n["title"] for n in toc if n["uuid"] not in expected_paths]
    if misplaced:
        errors.append(f"错位节点 {len(misplaced)}: {misplaced[:5]}")
    if extra:
        errors.append(f"多余节点 {len(extra)}: {extra[:5]}")

    # 3. 幽灵文档: 库里文档 total == 账本 doc_id 数
    total = None
    got = 0
    offset = 0
    while True:
        r = api(token, BASE, "GET", f"/repos/{book}/docs?limit=100&offset={offset}")
        got += len(r["data"])
        total = r.get("meta", {}).get("total")
        if got >= (total or 0) or not r["data"]:
            break
        offset += 100
    if total != len(doc_ids):
        errors.append(f"幽灵文档: 库内 {total} != 账本 {len(doc_ids)}")

    # 4. 全路径唯一 + 抽查首尾深层路径
    doc_paths = [p for n in toc for p in [actual_paths[n["uuid"]]] if n.get("type") == "DOC"]
    if len(doc_paths) != len(set(doc_paths)):
        errors.append("存在重复文档路径")
    samples = [rel for rel in list(prog["nodes"].keys())[:1] + list(prog["nodes"].keys())[-1:]]
    for s in samples:
        if s not in actual_paths.values():
            errors.append(f"抽查路径不可达: {s}")

    return errors


# ---------- 钉钉汇报（消息必含 "GitHub" 关键词） ----------
def dingtalk(text):
    wh = os.environ.get("DINGTALK_WEBHOOK")
    if not wh:
        return
    if "GitHub" not in text:
        text = "GitHub " + text
    try:
        req = urllib.request.Request(wh, data=json.dumps(
            {"msgtype": "text", "text": {"content": text}}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15)
        print("[notify] 钉钉已发送", flush=True)
    except Exception as e:
        print(f"[notify] 钉钉发送失败: {e}", flush=True)


# ---------- 主流程 ----------
def import_one(url, workdir, ledger, args):
    """返回 (status, repo, commit, book_id, book_url, errors); status: ok/skip/fail"""
    errors = []
    r = run_script("yuque_repo_import.py", ["prep", "--url", url, "--dir", workdir])
    info = prep_parse(r.stdout)
    if not info.get("commit"):
        return "fail", None, None, None, None, [f"prep 失败: {r.stderr[-300:] or r.stdout[-300:]}"]

    repo, commit = info["repo"], info["commit"]
    prev = ledger.get(url, {})
    if prev.get("commit") == commit:
        # commit 未变 → 跳过（dry 模式同样只走到这里, 不算新导入）
        return "skip", repo, commit, prev.get("book_id"), prev.get("book_url"), None

    if args.dry:
        return "skip", repo, commit, None, None, None

    name, slug, desc = f"{repo}（{commit}）", f"{repo}-{commit}", f"{url} @ {commit}"
    cc = cookie_config_path(workdir)
    cc_args = ["--cookie-config", cc] if cc else []

    r = run_script("yuque_repo_import.py",
                   ["create-book", "--name", name, "--slug", slug, "--desc", desc,
                    "--login", args.login, "--stack-id", str(args.stack_id)])
    if r.returncode != 0:
        return "fail", repo, commit, None, None, [f"create-book 失败: {r.stderr[-300:] or r.stdout[-300:]}"]
    book_id = create_book_parse(r.stdout)

    r = run_script("yuque_repo_import.py",
                   ["move-stack", "--book-id", str(book_id), "--stack-id", str(args.stack_id),
                    "--wait", "30"] + cc_args)
    if r.returncode != 0:
        return "fail", repo, commit, book_id, None, [f"move-stack 失败: {r.stderr[-300:] or r.stdout[-300:]}"]

    progress = os.path.join(workdir, f"{repo}-{commit}-progress.json")
    r = run_script("yuque_tree_import.py",
                   ["--root", info["clean_dir"], "--book", str(book_id), "--progress", progress,
                    "--pend-sleep", str(args.pend_sleep), "--pend-retries", str(args.pend_retries),
                    "--max-body", str(args.max_body)]
                   + cc_args)
    m = re.search(r'=== 完成 === (\{.*\})', r.stdout)
    stats = json.loads(m.group(1)) if m else {}
    if stats.get("fail"):
        errors.append(f"导入失败 {len(stats['fail'])} 个节点: {stats['fail'][:3]}")
    if not m:
        errors.append(f"导入未正常完成: {r.stdout[-300:] or r.stderr[-300:]}")

    errors += verify(book_id, progress)

    book_url = f"https://www.yuque.com/{args.login}/{slug}"
    return "ok", repo, commit, book_id, book_url, errors


def main():
    ap = argparse.ArgumentParser(description="开源项目批量导入编排器")
    ap.add_argument("--repos", required=True, help="repos.json 清单")
    ap.add_argument("--ledger", required=True, help="last-imported.json 账本（读+写）")
    ap.add_argument("--stack-id", type=int, default=DEFAULT_STACK)
    ap.add_argument("--workdir", default="import-work", help="镜像/账本/日志目录（CI 用 runner.temp, 本地用 workspace/tmp）")
    ap.add_argument("--login", default=DEFAULT_LOGIN)
    ap.add_argument("--pend-sleep", type=float, default=60, help="失败静置秒数(CI 里比默认 600 小)")
    ap.add_argument("--pend-retries", type=int, default=3)
    ap.add_argument("--max-body", type=int, default=200_000, help="单文档 body 上限(字节), 透传给 tree_import; 默认 200KB(2026-10-13 老板定)")
    ap.add_argument("--only", default="", help="只导匹配该子串的 repo")
    ap.add_argument("--dry", action="store_true", help="只跑 prep+账本去重, 不写语雀")
    ap.add_argument("--no-notify", action="store_true", help="不发钉钉")
    args = ap.parse_args()

    os.makedirs(args.workdir, exist_ok=True)
    repos_cfg = json.load(open(args.repos, encoding="utf-8"))
    repos = [r["url"] for r in repos_cfg["repos"] if r.get("enabled", True)]
    if args.only:
        repos = [u for u in repos if args.only.lower() in u.lower()]

    ledger = {}
    if os.path.exists(args.ledger):
        ledger = json.load(open(args.ledger, encoding="utf-8"))

    ok, skipped, failed = [], [], []
    for url in repos:
        status, repo, commit, book_id, book_url, errors = import_one(url, args.workdir, ledger, args)
        if status == "fail":
            failed.append({"repo": repo or url, "commit": commit, "errors": errors})
            print(f"[FAIL] {repo or url}: {errors}", flush=True)
            continue
        if status == "skip":
            skipped.append({"repo": repo, "commit": commit, "book_url": book_url})
            print(f"[SKIP] {repo} @ {commit} 已导入过(或 dry)", flush=True)
            continue
        ledger[url] = {"commit": commit, "book_id": book_id, "book_url": book_url,
                       "imported_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        ok.append({"repo": repo, "commit": commit, "book_id": book_id, "book_url": book_url})
        print(f"[OK] {repo}（{commit}）→ {book_url} ✅", flush=True)

    with open(args.ledger + ".tmp", "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)
    os.replace(args.ledger + ".tmp", args.ledger)

    summary = {"ok": ok, "skipped": skipped, "failed": failed}
    print("=== 汇总 ===", json.dumps(summary, ensure_ascii=False), flush=True)

    if not args.no_notify:
        lines = ["GitHub 开源项目导入汇报"]
        if ok:
            lines += [f"✅ 导入 {len(ok)} 个:"]
            lines += [f"  {o['repo']}（{o['commit']}）→ {o['book_url']}" for o in ok]
        if skipped:
            lines += [f"⏭ 跳过 {len(skipped)} 个（commit 未变）: " + ", ".join(s["repo"] for s in skipped)]
        if failed:
            lines += [f"❌ 失败 {len(failed)} 个: " + ", ".join(f["repo"] for f in failed)]
            lines += ["详情见 GitHub Actions 日志, 需人工介入"]
        dingtalk("\n".join(lines))

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
