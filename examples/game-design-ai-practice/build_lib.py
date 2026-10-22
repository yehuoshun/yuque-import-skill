#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《游戏策划实务即用的 AI·Claude Code 活用法（简体中文版）》→ 语雀 clean 目录构建。

源仓库：eremes81/game-design-ai-practice-zh-hans（GitHub Pages 书站 + manuscript/ md 源）
本站口径：正本站 https://eremes81.github.io/game-design-ai-practice-zh-hans/

做的事（只做「文件系统层面」重命名，不碰正文）：
  1. partNN-xxx/             → `NN-第N部分 · 中文名/`（两位序号前缀，天然字典序正确）
  2. chapter-N-xxx.md        → `N.M 中文标题.md`（标题取自文件内首个 H1）
  3. part21 / part23 的 H1 是「Part NN · 第M章 ...」异体 → 归一化为 `NN.M ...`
  4. 标题里的半角 `/` → 全角 `／`（文件系统不允许 `/`；语雀 toc-md 收全角无碍）
  5. 标题里的 markdown 过度转义 `\\~` → `~`
  6. `_front-matter.md` → `00-序 · 封面 · 阅读方法.md`；`_colophon.md` → `01-版权页.md`
  7. 当且仅当文件首个 H1 == 最终文档标题时，删掉该 H1 行（避免语雀「标题 + 正文首行 H1」双标题；
     不相等时保留，故零信息损失）

用法：
  python3 build_lib.py --src <clone>/manuscript --out <clean_dir>
"""
import argparse
import os
import re
import shutil
import sys

# 部分目录名 → 显示名（来源：仓库 README.md 的「完整目录」章节，逐条核对）
PART_NAMES = {
    "part01-foundation": "第1部分 · 基础",
    "part02-info-architecture": "第2部分 · 信息架构",
    "part03-system-design": "第3部分 · 系统设计",
    "part04-combat-design": "第4部分 · 战斗设计",
    "part05-narrative-design": "第5部分 · 叙事",
    "part06-content-design": "第6部分 · 内容设计",
    "part07-level-design": "第7部分 · 关卡设计",
    "part08-balance-design": "第8部分 · 数值平衡",
    "part09-ux-ui-design": "第9部分 · UX/UI",
    "part10-qa-design": "第10部分 · QA",
    "part11-character-pet-mount": "第11部分 · 角色·宠物·坐骑",
    "part12-art-direction": "第12部分 · 美术",
    "part13-data-kpi": "第13部分 · 数据与 KPI",
    "part14-mobile-platform": "第14部分 · 移动端",
    "part15-live-ops": "第15部分 · 长期运营（Live Ops）",
    "part16-communicator": "第16部分 · 沟通者",
    "part17-meeting-notes": "第17部分 · 会议记录",
    "part18-decision-impact": "第18部分 · 决策与影响",
    "part19-team-lead": "第19部分 · 主管与团队领导",
    "part20-team-collab": "第20部分 · 团队协作",
    "part21-self-improving": "第21部分 · 自我改进",
    "part22-governance": "第22部分 · 治理",
    "part23-extension": "第23部分 · 扩展与未来",
    "part24-ops-deep": "第24部分 · 运营实战",
    "part99-appendix": "后记与附录",
}

# 根级特例文件 → 文档标题（H1 是书名/「版权页」，不适合直接当标题）
ROOT_SPECIAL = {
    "_front-matter.md": "00-序 · 封面 · 阅读方法",
    "_colophon.md": "01-版权页",
}

# part21 / part23 的 H1 异体：「Part 21 · 第1章 复盘是一切的起点」→「21.1 复盘是一切的起点」
RE_PART_H1 = re.compile(r"^Part\s+(\d+)\s*·\s*第(\d+)章\.?\s*")


def sanitize(title: str) -> str:
    """文件名安全化（只改文件系统不允许/会被转义误显的字符，不动语义）。"""
    t = title.replace("/", "／")          # 半角斜杠 → 全角（文件名不允许 `/`）
    t = t.replace("\\~", "~")             # markdown 过度转义 → 字面量
    t = re.sub(r"\s+", " ", t).strip()
    return t


def first_h1(text: str):
    """返回 (行号, 标题文本) 或 (None, None)；跳过前置 YAML frontmatter。"""
    in_fm = False
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if i == 0 and ln.strip() == "---":
            in_fm = True
            continue
        if in_fm:
            if ln.strip() == "---":
                in_fm = False
            continue
        if ln.startswith("# "):
            return i, ln[2:].strip()
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="clone 仓库的 manuscript/ 目录")
    ap.add_argument("--out", required=True, help="输出 clean 目录（不存在则创建，存在则清空）")
    args = ap.parse_args()

    src, out = os.path.abspath(args.src), os.path.abspath(args.out)
    if not os.path.isdir(src):
        sys.exit(f"源目录不存在: {src}")
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)

    n_dir = n_doc = n_h1_stripped = 0
    warnings = []

    # 根级散落 md（_front-matter / _colophon）
    for name in sorted(os.listdir(src)):
        p = os.path.join(src, name)
        if not os.path.isfile(p) or not name.endswith(".md"):
            continue
        title = ROOT_SPECIAL.get(name, sanitize(os.path.splitext(name)[0]))
        text = open(p, encoding="utf-8").read()
        h1_i, h1 = first_h1(text)
        if h1 and sanitize(h1) == title:
            text = "\n".join(text.split("\n")[:h1_i] + text.split("\n")[h1_i + 1:]).lstrip("\n")
            n_h1_stripped += 1
        dst = os.path.join(out, title + ".md")
        if os.path.exists(dst):
            sys.exit(f"重名冲突: {dst}")
        open(dst, "w", encoding="utf-8").write(text)
        n_doc += 1

    # part 目录
    for idx, dname in enumerate(sorted(d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))), 1):
        if dname not in PART_NAMES:
            warnings.append(f"未映射的目录（跳过）: {dname}")
            continue
        prefix = dname[4:6] if dname.startswith("part") else f"{idx:02d}"
        out_dir = os.path.join(out, sanitize(f"{prefix}-{PART_NAMES[dname]}"))
        os.makedirs(out_dir)
        n_dir += 1
        for name in sorted(os.listdir(os.path.join(src, dname))):
            p = os.path.join(src, dname, name)
            if not os.path.isfile(p) or not name.endswith(".md"):
                continue
            text = open(p, encoding="utf-8").read()
            h1_i, h1 = first_h1(text)
            if not h1:
                warnings.append(f"无 H1（用文件名兜底）: {dname}/{name}")
                h1 = os.path.splitext(name)[0]
            h1 = RE_PART_H1.sub(r"\1.\2 ", h1)
            title = sanitize(h1)
            if h1_i is not None and sanitize(h1) == title:
                lines = text.split("\n")
                text = "\n".join(lines[:h1_i] + lines[h1_i + 1:]).lstrip("\n")
                n_h1_stripped += 1
            dst = os.path.join(out_dir, title + ".md")
            if os.path.exists(dst):
                sys.exit(f"重名冲突: {dst}")
            open(dst, "w", encoding="utf-8").write(text)
            n_doc += 1

    print(f"clean 目录: {out}")
    print(f"  目录 {n_dir} / 文档 {n_doc} = 节点 {n_dir + n_doc}")
    print(f"  剥掉与标题重复的首个 H1: {n_h1_stripped} 篇")
    for w in warnings:
        print("  ⚠", w)


if __name__ == "__main__":
    main()