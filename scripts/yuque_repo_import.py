#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 开源项目 → 语雀导入 wrapper（2026-10-12 老板固化流程）

把「克隆/更新仓库 → 干净副本 → 建库 → 移入开源项目分组」这几步收成一条命令，
全量导入本体仍由 yuque_tree_import.py 负责（本脚本最后会打印出导入命令）。

用法:
  python3 yuque_repo_import.py prep          --url git@github.com:xxx/yyy.git --dir /path/to/work
  python3 yuque_repo_import.py create-book   --name "yyy（abc12345）" --slug yyy-abc12345 \
                                             --desc "https://github.com/xxx/yyy @ abc12345"
  python3 yuque_repo_import.py move-stack    --book-id 12345678 --stack-id 57018723

约定（老板定，2026-10-12）:
  - 知识库名 = 项目名（commit id 8位）
  - 知识库分组 = 开源项目（stack 57018723）
  - 描述 = <repo url> @ <commit>
  - 中间产物（镜像/干净副本/账本/日志）一律放 workspace/tmp/（沙箱重启 /tmp 会清空）

prep 输出:
  REPO_NAME / COMMIT / NODES(files+dirs) / CLEAN_DIR / 待执行导入命令
"""
import argparse, json, os, subprocess, sys, time, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yuque_tree_import import load_token, api, walk  # noqa: E402

BASE = "https://www.yuque.com/api/v2"
DEFAULT_STACK = 57018723          # 开源项目
DEFAULT_LOGIN = "yehuoshun"


# ---------- git ----------
def git(args, cwd=None):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, check=True)


def repo_name_from_url(url):
    name = url.rstrip("/").split("/")[-1]
    return name[:-4] if name.endswith(".git") else name


def default_branch(mirror):
    try:
        git(["remote", "set-head", "origin", "-a"], cwd=mirror)
        out = git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=mirror).stdout.strip()
        if out:
            return out.split("/", 1)[-1]
    except Exception:
        pass
    for b in ("main", "master"):
        try:
            git(["rev-parse", "--verify", f"origin/{b}"], cwd=mirror)
            return b
        except Exception:
            continue
    raise RuntimeError("找不到默认分支(main/master 都没有)")


def short_commit(mirror, branch):
    return git(["rev-parse", "--short", f"origin/{branch}"], cwd=mirror).stdout.strip()


def cmd_prep(args):
    work = os.path.abspath(args.dir)
    os.makedirs(work, exist_ok=True)
    name = repo_name_from_url(args.url)
    mirror = os.path.join(work, name)
    if os.path.isdir(os.path.join(mirror, ".git")):
        print(f"[prep] 更新已有镜像 {mirror}")
        git(["fetch", "origin"], cwd=mirror)
    else:
        print(f"[prep] 克隆 {args.url}")
        git(["clone", args.url, mirror])
    branch = default_branch(mirror)
    commit = short_commit(mirror, branch)
    # 硬同步工作树到 origin/<branch>：只 fetch 不 reset 会拿到脏/旧工作树
    # （2026-10-15 owllook cd207f9 事故：报新 commit、tar 出旧内容）
    head = git(["rev-parse", "HEAD"], cwd=mirror).stdout.strip()
    want = git(["rev-parse", f"origin/{branch}"], cwd=mirror).stdout.strip()
    dirty = git(["status", "--porcelain"], cwd=mirror).stdout.strip()
    if head != want or dirty:
        try:
            git(["checkout", "-f", branch], cwd=mirror)
        except subprocess.CalledProcessError:
            pass
        git(["reset", "--hard", f"origin/{branch}"], cwd=mirror)
        git(["clean", "-fdx"], cwd=mirror)
        print(f"[prep] 工作树已硬同步 → {commit}")
    clean = os.path.join(work, f"{name}-{commit}-clean")
    if not os.path.isdir(clean):
        os.makedirs(clean, exist_ok=True)
        # tar 排除 .git（rsync 未必装全平台，tar 通用）
        with subprocess.Popen(["tar", "cf", "-", "--exclude=.git", "."], cwd=mirror,
                              stdout=subprocess.PIPE) as p:
            with subprocess.Popen(["tar", "xf", "-", "-C", clean], stdin=p.stdout) as p2:
                p2.wait()
            p.wait()
    nodes = walk(clean)
    files = sum(1 for _, is_dir in nodes if not is_dir)
    dirs = sum(1 for _, is_dir in nodes if is_dir)
    print(f"[prep] repo={name} branch={branch} commit={commit}")
    print(f"[prep] nodes={len(nodes)} (dir {dirs} / file {files})")
    if len(nodes) > 5000:
        print(f"[prep] ⚠️ 节点数 {len(nodes)} 超语雀知识库上限 5000，必须分库"
              f"（按顶层目录拆多个库，命名 项目名-<顶层目录>（commit）；2026-10-14 老板拍板）", flush=True)
    print(f"[prep] clean_dir={clean}")
    print(f"[prep] 下一步: create-book + move-stack + yuque_tree_import.py --root {clean} --book <book_id>")
    return 0


# ---------- 建库（默认走 Web API 带 stack_id） ----------
def cmd_create_book(args):
    """建库。语雀的分组映射**只在建库那一刻建立**，事后再也补不上
    （PUT /api/mine/book_stack/move 对未分组库恒返 200 但不生效），
    所以有 cookie 时直接走 Web API `POST /api/books` 带 stack_id，一步到位。
    """
    import yuque_backend as yb
    cfg = yb._cookie_cfg() if args.stack_id else None
    if cfg:
        body = {"name": args.name, "type": "Book", "public": int(args.public),
                "description": args.desc or "", "stack_id": int(args.stack_id)}
        if args.slug:
            body["slug"] = args.slug
        d = {}
        for attempt in range(1, 6):
            d = yb._web_api(cfg, "POST", f"{yb.WEB}/books", body)
            if isinstance(d, dict) and d.get("data"):
                break
            if "slug" in str(d) and attempt < 5 and args.slug:
                print(f"[create-book] slug {body.get('slug')} 冲突, 追加 -{attempt + 1} 重试", flush=True)
                body["slug"] = f"{args.slug}-{attempt + 1}"
                continue
            raise RuntimeError(f"建库失败: {str(d)[:300]}")
        data = d["data"]
        time.sleep(1.3)                      # web API 限 1 QPS
        s = yb._stack_of(yb._web_api(cfg, "GET", f"{yb.WEB}/mine/book_stacks"), data.get("id"))
        print(f"[create-book] id={data.get('id')} name={data.get('name')} slug={data.get('slug')} "
              f"分组={s.get('name') if s else '未分组（异常！）'}")
        print("[create-book] 分组映射已在建库时建立，不用再跑 move-stack。下一步: yuque_tree_import.py")
        return 0
    # 没读到 cookie → 只能用 v2 建库，库会落在未分组，事后无法补（界面手动拖是唯一出路）
    token = load_token("TOKEN_L91")
    payload = {"name": args.name, "slug": args.slug or None, "description": args.desc or "",
               "public": int(args.public)}
    payload = {k: v for k, v in payload.items() if v is not None}
    # slug 撞名兜底(2026-10-13 老板定策略): 冲突时自动追加 -2/-3 序号重试
    #   策略: 开源项目 = 项目名-commit(天然防撞); 网站/自定义 = 网站名-YYYYMMDD, 同日同站会撞 → 序号兜底
    for attempt in range(1, 6):
        try:
            d = api(token, BASE, "POST", f"/users/{args.login}/repos", payload)
            break
        except RuntimeError as e:
            if "422" not in str(e) or "slug" not in str(e) or attempt == 5 or not args.slug:
                raise
            print(f"[create-book] slug {payload.get('slug')} 冲突, 追加 -{attempt + 1} 重试", flush=True)
            payload["slug"] = f"{args.slug}-{attempt + 1}"
    data = d.get("data", d)
    print(f"[create-book] id={data.get('id')} name={data.get('name')} slug={data.get('slug')}")
    print("[create-book] ⚠️ 没读到 cookie 配置（config/yuque_cookies.txt 或 YUQUE_COOKIE_CONFIG），"
          "库会落在『未分组』，而语雀没有事后补分组的接口 —— 只能到界面手动拖。")
    return 0


# ---------- 移入分组（cookie/ctoken Web API） ----------
def load_cookie_cfg(cookie_config):
    """cookie 配置：JSON 或纯文本 Cookie 串都认（复用 yuque_backend 的自动发现逻辑）"""
    import yuque_backend as yb
    c = yb._cookie_cfg(cookie_config)
    if not c:
        raise RuntimeError(f"没找到 cookie 配置（{cookie_config or '自动发现全部失败'}）")
    return c


def web_api(cfg, method, url, payload=None, retries=4):
    data = json.dumps(payload).encode() if payload is not None else None
    for i in range(retries):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Cookie", cfg["cookie"])
        if cfg.get("ctoken"):
            req.add_header("X-Csrf-Token", cfg["ctoken"])
        if payload is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** i * 1.5 + 1)
                continue
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:300]}")
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(2 ** i * 1.5 + 1)
    raise RuntimeError("retries exhausted")


def cmd_move_stack(args):
    cfg = load_cookie_cfg(args.cookie_config)
    if not args.no_wait:
        # 新建库立刻移动会失败（2026-10-12 实踩），先等几秒
        print(f"[move-stack] 等待 {args.wait}s（新建库移动有时序坑）")
        time.sleep(args.wait)
    # ⚠️ 正确端点是 PUT /api/mine/book_stack/move（2026-08-31 MCP 源码修复实捶）：
    # 旧实现 PUT /api/books/{id} + {"stack_id": N} 返回成功但实际不生效（本 wrapper 初版实踩：库落进「其他」分组）
    # 2026-10-13 三次实踩规律：首次 PUT 常静默无效(返回 {}), 传播需 30s~4min+;
    #   仅重试验证(10x3s)在第三例仍失败 → v1.2.2 改为【每轮重发 PUT(幂等) + 验证】, 轮间 20s
    #   总窗口 ≈ 等待 + 10×(20s+3s) ≈ 30s+230s ≈ 4.3min
    for attempt in range(10):
        if attempt > 0:
            time.sleep(20)
        d = web_api(cfg, "PUT", "https://www.yuque.com/api/mine/book_stack/move",
                    {"targetStackId": int(args.stack_id), "targetBookIds": [int(args.book_id)]})
        print(f"[move-stack] 第 {attempt + 1} 次移动响应: {json.dumps(d, ensure_ascii=False)[:120]}", flush=True)
        # 验证：move 接口成功/失败都返回 200+{}，必须回查 book_stacks 确认落在目标分组
        time.sleep(3)
        stacks = web_api(cfg, "GET", "https://www.yuque.com/api/mine/book_stacks")
        cur = None
        for st in (stacks if isinstance(stacks, list) else (stacks.get("data") or [])):
            if not isinstance(st, dict):
                continue
            if any(str(b.get("id")) == str(args.book_id) for b in (st.get("books") or [])):
                cur = st
                if str(st.get("id")) == str(args.stack_id):
                    print(f"[move-stack] 验证通过: {args.book_id} ∈ {st.get('name')} (stack {args.stack_id}) ✅")
                    return 0
        # 2026-11-12 实锤：库压根不在任何分组 → 语雀不会给已建好的库补映射，重试纯属白等
        if attempt == 0 and cur is None:
            raise RuntimeError(
                f"库 {args.book_id} 当前不在任何分组，move 返回 {{}} 是正常的无效响应。"
                "语雀的分组映射只在建库那一刻建立，事后没有接口能补 —— "
                "正确做法是 create-book --stack-id 建库即带分组，剩下的只能到界面手动拖。")
        print(f"[move-stack] 验证第 {attempt + 1} 次未通过（当前: "
              f"{cur.get('name') if cur else '未分组'}），重试...", flush=True)
    raise RuntimeError(f"验证失败: 库 {args.book_id} 不在分组 {args.stack_id}（当前: "
                       f"{cur.get('name') if cur else '未分组'}）")


def main():
    ap = argparse.ArgumentParser(description="GitHub 开源项目 → 语雀 导入 wrapper")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prep", help="克隆/更新镜像 → 干净副本 → 报 commit 和节点数")
    p.add_argument("--url", required=True, help="git 克隆地址（https 或 git@ssh）")
    p.add_argument("--dir", required=True, help="工作目录（建议 workspace/tmp/ 下）")
    p.set_defaults(fn=cmd_prep)

    p = sub.add_parser("create-book", help="建知识库（默认 Web API 带 stack_id，建库即入分组）")
    p.add_argument("--name", required=True, help="库名，按规范: 项目名（commit id）")
    p.add_argument("--slug", default=None)
    p.add_argument("--desc", default="")
    p.add_argument("--public", default="0")
    p.add_argument("--login", default=DEFAULT_LOGIN)
    p.add_argument("--stack-id", type=int, default=DEFAULT_STACK)
    p.set_defaults(fn=cmd_create_book)

    p = sub.add_parser("move-stack", help="移入分组（cookie Web API）+ 验证")
    p.add_argument("--book-id", required=True)
    p.add_argument("--stack-id", type=int, default=DEFAULT_STACK)
    p.add_argument("--cookie-config",
                   default=None, help="cookie 配置（JSON 或纯文本 Cookie 串）；默认自动发现")
    p.add_argument("--wait", type=int, default=30,
                  help="建库后等待秒数(默认 30; 2026-10-13 两次实踩需 ~45s+ 才可移, 旧默认 10 不够)")
    p.add_argument("--no-wait", action="store_true", help="跳过移动前等待（重复移动用）")
    p.set_defaults(fn=cmd_move_stack)

    args = ap.parse_args()
    try:
        sys.exit(args.fn(args))
    except Exception as e:
        print(f"[error] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
