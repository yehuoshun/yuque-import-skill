#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""动手学深度学习（d2l-zh，MyST/Sphinx md 源）→ 干净 markdown。

规则：
  * 代码 cell：只保留 `#@tab pytorch` / `#@tab all`（= 站上 PyTorch 标签页内容）；
    无标记 = mxnet 变体 → 丢弃；其余框架标记 → 丢弃
  * `:numref:`/`:eqref:`/`:ref:` → 用站上渲染文本（图1.1.1 / 2.2节 / (2.3.1)）
  * `:cite:` → (作者 et al., 年)（多篇用 "; " 连接，与站一致）
  * `:label:`/`:eqlabel:`/`:width:` 指令行删掉（编号信息转移到图/表/公式标题）
  * `:begin_tab:` 文本块只留 pytorch；```eval_rst``` / ```toc``` 块丢弃
  * 标题按站上 section-number 补编号（2.3.1 → "## 2.3.1 标量"）
  * 图片引用 ../img/X → 独立 _img/ 目录（prefix 决定 ../ 层数）
"""
import re, os, json, html, collections

HERE = os.path.dirname(os.path.abspath(__file__))
REFMAP = json.load(open(os.path.join(HERE, "refmap.json")))

# 站上没解析成功的 3 个引用（书里标签缺失/写错），手工按章节语义补
OVERRIDE = {
    "subsec-vgg-blocks": "7.2节",
    "subsec-multi-output-channels": "6.4节",
    "tab-glove": "表14.5.1",
}


def txt(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def normkey(label):
    """贴近 Sphinx 的 id 归一：下划线/加号 → 连字符，小写"""
    return label.lower().replace("_", "-").replace("+", "-")


def hnorm(s):
    """标题比对归一：去掉空白与强调标记"""
    return re.sub(r'[\s\[\]\*`(){}【】]', '', s)


def reftext(label, stats):
    k = normkey(label)
    for src in ("numref", "defs"):
        v = REFMAP[src].get(k)
        if v:
            return v
    if k in OVERRIDE:
        return OVERRIDE[k]
    stats["ref_unresolved"] += 1
    return label            # 站上同样显示原始标签（书里坏引用）


def cite_text(keys, stats):
    labels = []
    for k in [x.strip() for x in keys.split(",") if x.strip()]:
        v = REFMAP["key2ref"].get(k)
        if not v:
            stats["cite_unresolved"] += 1
            v = k
        labels.append(v)
    return "(" + "; ".join(labels) + ")"


# ---------- 站上标题（带编号）作为标题 oracle ----------
def site_headings(page_html):
    h = open(page_html, encoding="utf-8", errors="replace").read()
    res = []
    for m in re.finditer(r'<h([1-6])>(.*?)</h\1>', h, re.S):
        lvl = int(m.group(1))
        inner = m.group(2)
        num = ""
        nm = re.match(r'\s*<span class="section-number">([^<]*)</span>', inner)
        if nm:
            num = nm.group(1).strip()
            inner = inner[nm.end():]
        inner = inner.split('<div')[0]
        title = txt(inner)
        title = re.sub(r"¶.*$", "", title).strip()
        if title:
            res.append((lvl, num.rstrip("."), title))
    return res


# ---------- 主转换 ----------
def convert(text, rm_headings, prefix, stats):
    lines = text.split("\n")
    n = len(lines)
    out = []
    i = 0
    # 标题编号游标
    hp = 0

    def inl(s):
        """行内指令处理"""
        s = re.sub(r':cite:`([^`]+)`', lambda m: cite_text(m.group(1), stats), s)
        s = re.sub(r':(?:numref|eqref|ref|doc|term):`([^`]+)`',
                   lambda m: reftext(m.group(1), stats), s)
        s = re.sub(r'\s+([，。；：、）])', r'\1', s)   # 删引用后残留的空格
        return s

    def emit_heading(lv, title):
        nonlocal hp
        num = ""
        tn = hnorm(title)
        for k in range(hp, len(rm_headings)):
            if hnorm(rm_headings[k][2]) == tn:
                num, hp = rm_headings[k][1], k + 1
                break
        stats["heading_numbered" if num else "heading_plain"] += 1
        out.append("#" * lv + " " + ((num + " ") if num else "") + title)

    while i < n:
        line = lines[i]
        # 代码块
        m = re.match(r'^```(.*)$', line)
        if m:
            info = m.group(1).strip()
            j = i + 1
            body = []
            closed = False
            while j < n:
                if lines[j].startswith("```"):
                    closed = True
                    break
                body.append(lines[j]); j += 1
            if not closed:            # 描不完就当前行当普通文本（防吞文件尾）
                stats["fence_unclosed"] += 1
                out.append(inl(line))
                i += 1
                continue
            if info.startswith("{.python"):
                mk = None
                if body and body[0].strip().startswith("#@tab"):
                    mk = re.match(r'\s*#@tab\s+(\w+)', body[0]).group(1)
                if mk in ("pytorch", "all"):
                    stats["code_keep"] += 1
                    bl = [l for l in body if not re.match(r'^\s*#@tab\s+\w+\s*$', l)]
                    while bl and not bl[0].strip():
                        bl.pop(0)
                    while bl and not bl[-1].strip():
                        bl.pop()
                    out.append("```python"); out.extend(bl); out.append("```")
                else:
                    stats["code_drop_" + (mk or "unmarked")] += 1
                    if lines[i:j].count("") == 0:
                        pass
            elif info in ("toc",) or info.startswith("eval_rst"):
                stats["block_drop_" + (info or "?")] += 1
                # eval_rst 里的 autoclass/autofunction 成员名保留成清单
                mem = [re.sub(r'^\s*\.\.\s*(?:autoclass|autofunction|automethod|autoattribute)::\s*', '',
                              l).strip() for l in body
                       if re.match(r'^\s*\.\.\s*(?:autoclass|autofunction|automethod|autoattribute)::', l)]
                for name in mem:
                    out.append("* `%s`" % name)
                if mem:
                    out.append("")
            else:
                lang = "text"
                if info.startswith("{."):
                    lang = info[2:].split()[0].rstrip("}")
                elif info:
                    lang = info
                out.append("```" + lang); out.extend(body); out.append("```")
            i = j + 1
            continue
        # 文本 tab（多框架列表或单框架；end_tab 可能是裸的）
        m = re.match(r'^:begin_tab:`([^`]+)`\s*$', line)
        if m:
            tabs = re.split(r'[,\s]+', m.group(1).strip())
            j = i + 1
            seg = []
            closed = False
            while j < n:
                if re.match(r'^:end_tab:(?:`[^`]*`)?\s*$', lines[j]):
                    closed = True
                    break
                seg.append(lines[j]); j += 1
            if not closed:            # 防吞文件尾：当普通文本
                stats["tab_unclosed"] += 1
                out.append(inl(line))
                i += 1
                continue
            if "pytorch" in tabs:
                stats["texttab_keep"] += 1
                for l in seg:
                    out.append(inl(l))
            else:
                stats["texttab_drop_" + m.group(1).replace(",", "+").replace(" ", "")] += 1
            i = j + 1
            continue
        # 指令行（eqlabel 保留给公式编号后处理）
        st = line.strip()
        if re.match(r'^:(?:label|width):`[^`]*`$', st):
            stats["meta_drop"] += 1
            i += 1
            continue
        # 标题
        m = re.match(r'^(#{1,6})\s+(.*)$', line)
        if m:
            if len(m.group(1)) == 1 and not out:
                stats["h1_dropped"] += 1
                i += 1
                continue
            emit_heading(len(m.group(1)), inl(m.group(2).strip()))
            i += 1
            continue
        # 图片（可带 label → 补图号；路径重写放到全文后处理）
        m = re.match(r'^!\[(.*?)\]\(([^)]+)\)\s*$', line)
        if m:
            cap, path = m.group(1), m.group(2)
            num = None
            for k in range(1, 4):
                if i + k >= n:
                    break
                lm = re.match(r'^\s*:label:`([^`]+)`\s*$', lines[i + k])
                if lm:
                    num = reftext(lm.group(1), stats)
                    break
                if not lines[i + k].strip():
                    break
            alt = (num + " " + cap).strip() if num else cap
            out.append("![%s](%s)" % (inl(alt), path))
            stats["img_ref"] += 1
            i += 1
            continue
        # 表格：起始行 + 紧随其后的 label → 表号
        if line.startswith("|") and (i == 0 or not lines[i - 1].startswith("|")):
            j = i
            while j < n and lines[j].startswith("|"):
                j += 1
            num = None
            for k in range(j, min(j + 3, n)):
                lm = re.match(r'^\s*:label:`([^`]+)`\s*$', lines[k])
                if lm:
                    num = reftext(lm.group(1), stats)
                    break
                if lines[k].strip():
                    break
            if num:
                out.append("**%s**" % num)
                out.append("")
                stats["table_numbered"] += 1
            for k in range(i, j):
                out.append(inl(lines[k]))
            i = j
            continue
        # 公式：只做 :eqlabel: 编号（不解析 $$ 结构，避免把块内 $$ 当开块）
        out.append(inl(line))
        i += 1

    md = "\n".join(out)
    # ---- 公式编号：:eqlabel: 行删掉，编号补到它前面那个公式块之后 ----
    lines = md.split("\n")
    keep = []
    for idx, l in enumerate(lines):
        m = re.match(r'^\s*:eqlabel:`([^`]+)`\s*$', l)
        if not m:
            keep.append(l)
            continue
        num = reftext(m.group(1), stats)
        stats["eq_numbered"] += 1
        # 向上找公式块结束行（含 $$ 的最近一行）
        p = len(keep) - 1
        while p >= 0 and "$$" not in keep[p]:
            p -= 1
        if p >= 0:
            keep.insert(p + 1, "")
            keep.insert(p + 2, "（%s）" % num.strip("()"))
    md = "\n".join(keep)
    # ---- 杂项清洗 ----
    md = re.sub(r'\(\*\*(.*?)\*\*\)', r'**\1**', md)      # (**强调**) → **强调**
    md = re.sub(r'\[\*\*(.*?)\*\*\]', r'**\1**', md)      # [**强调**] → **强调**
    md = re.sub(r'^(#+)\s*\[\*\*(.*?)\*\*\]\s*$', r'\1 **\2**', md, flags=re.M)
    # 图片路径重写（含 begin_tab 内的）
    md = re.sub(r'(!\[[^\]]*\]\()(?:\.\./)?img/([^)]+)(\))',
                lambda m: m.group(1) + prefix + "_img/" + os.path.basename(m.group(2)) + m.group(3), md)
    md = re.sub(r'\n{3,}', '\n\n', md)
    md = md.strip() + "\n"
    return md