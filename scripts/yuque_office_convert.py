#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""办公文档 → Markdown（yuque-import-skill 导入前预处理）

支持的输入：.docx / .pptx / .xlsx / .csv
不支持的输入：.doc / .ppt / .xls（旧二进制格式）→ 记 unsupported，不静默跳过

用法:
  python3 scripts/yuque_office_convert.py --src <输入目录> --out <输出目录>
  python3 scripts/yuque_office_convert.py --src in --out out --include .docx,.csv
  python3 scripts/yuque_office_convert.py --src in --out out --dry

约定（与 yuque-import-skill 一致）:
  - 默认不覆盖：输出已存在 → skipped（--overwrite 才写）
  - 输入/输出目录必须分离（嵌套也拒绝）
  - 转换产物为空 → failed，不写占位文件（对应 SKILL 硬规则 8：正文 word_count>0）
  - 内嵌图片落到 out/_office_assets/<相对路径去扩展名>/，正文写相对引用；
    导入前先跑 yuque_rewrite_images.py 传 CDN，再把 _office_assets 从导入根删掉（硬规则 10）

依赖: mammoth（.docx，自带 cobble/lxml 依赖）/ python-pptx（.pptx）/ openpyxl（.xlsx）/ 标准库 csv
"""
import argparse
import csv
import os
import sys
from datetime import date
from pathlib import Path

SUPPORTED = {".docx", ".pptx", ".xlsx", ".csv"}
UNSUPPORTED = {".doc", ".ppt", ".xls"}
ASSETS_DIRNAME = "_office_assets"


def log(msg):
    print(msg, flush=True)


def md_table(rows):
    """二维列表 → Markdown 表格。空列表返回空串（由调用方判空）。"""
    cells = [[("" if c is None else str(c)).replace("|", "\\|").replace("\n", "<br>")
              for c in row] for row in rows]
    cells = [r for r in cells if any(c.strip() for c in r)]
    if not cells:
        return ""
    width = max(len(r) for r in cells)
    cells = [r + [""] * (width - len(r)) for r in cells]
    head, body = cells[0], cells[1:]
    out = ["| " + " | ".join(head) + " |",
           "| " + " | ".join(["---"] * width) + " |"]
    out += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(out)


def save_image(blob, assets_dir, hint):
    """图片字节落盘，返回相对导入根正斜杠路径。同名自动加序号。"""
    assets_dir.mkdir(parents=True, exist_ok=True)
    ext = ".png"
    n = 1
    while True:
        name = "%s-%02d%s" % (hint, n, ext)
        path = assets_dir / name
        if not path.exists():
            break
        n += 1
    path.write_bytes(blob)
    return path.as_posix()


def conv_csv(path, assets_dir, rel_stem):
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        rows = list(csv.reader(f))
    return md_table(rows)

def conv_xlsx(path, assets_dir, rel_stem):
    """每个工作表一个 ## 小节 + Markdown 表。read_only 流式读取，用完显式关闭。"""
    from openpyxl import load_workbook

    wb = load_workbook(path, data_only=True, read_only=True)
    try:
        parts = []
        for ws in wb.worksheets:
            rows = [[("" if c is None else c) for c in row]
                    for row in ws.iter_rows(values_only=True)]
            table = md_table(rows)
            if table:
                parts.append("## %s\n\n%s" % (ws.title, table))
        return "\n\n".join(parts)
    finally:
        wb.close()


def conv_docx(path, assets_dir, rel_stem):
    """mammoth 转 docx：样式→标题级别自动映射，内嵌图落 assets 目录。"""
    import mammoth

    def _img(image):
        src = save_image(image.open().read(), assets_dir, rel_stem)
        return {"src": src}

    with open(path, "rb") as f:
        result = mammoth.convert_to_markdown(
            f, convert_image=mammoth.images.img_element(_img))
    for msg in result.messages:
        log("    mammoth: %s" % msg.message)
    return result.value


def _pptx_slide_blocks(slide, assets_dir, rel_stem, idx):
    """单页 → 文本块列表。标题用 ###，正文原样段落，表格转 Markdown。"""
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    blocks = []
    for shape in slide.shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            src = save_image(shape.image.blob, assets_dir, "%s-s%d" % (rel_stem, idx))
            blocks.append("![slide%d](%s)" % (idx, src))
        elif getattr(shape, "has_table", False) and shape.has_table:
            rows = [[cell.text for cell in row.cells] for row in shape.table.rows]
            table = md_table(rows)
            if table:
                blocks.append(table)
        elif shape.has_text_frame:
            # 段落之间用空行，否则语雀 markdown 把多个 bullet 挤成一坨
            text = "\n\n".join(p.text.strip() for p in shape.text_frame.paragraphs
                               if p.text.strip())
            if not text:
                continue
            blocks.append("### " + text if shape == slide.shapes.title else text)
    return blocks


def conv_pptx(path, assets_dir, rel_stem):
    """逐页转换：## Slide N + 形状文本/表格/图片 + 备注。"""
    from pptx import Presentation

    prs = Presentation(path)
    parts = []
    for idx, slide in enumerate(prs.slides, 1):
        blocks = _pptx_slide_blocks(slide, assets_dir, rel_stem, idx)
        notes = ""
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame is not None:
            notes = slide.notes_slide.notes_text_frame.text.strip()
        if notes:
            blocks.append("> 备注：%s" % notes)
        parts.append("## Slide %d\n\n%s" % (idx, "\n\n".join(blocks)))
    return "\n\n".join(parts)


CONVERTERS = {".docx": conv_docx, ".pptx": conv_pptx, ".xlsx": conv_xlsx, ".csv": conv_csv}


def convert_one(src, src_root, out_root, overwrite, provenance):
    """单文件转换。返回 (status, detail)：ok / skipped / failed / unsupported。"""
    rel = src.relative_to(src_root)
    ext = src.suffix.lower()
    if ext in UNSUPPORTED:
        return "unsupported", "%s（旧二进制格式，需先另存为新版）" % ext
    out_path = (out_root / rel).with_suffix(".md")
    if out_path.exists() and not overwrite:
        return "skipped", "输出已存在"
    rel_stem = str(rel.with_suffix("")).replace(os.sep, "/")
    assets_dir = out_root / ASSETS_DIRNAME / rel_stem
    try:
        body = CONVERTERS[ext](src, assets_dir, Path(rel_stem).name)
    except Exception as exc:  # 转换库对坏文件抛的异常类型不统一，统一兜住记 failed
        return "failed", "%s: %s" % (type(exc).__name__, exc)
    if not body or not body.strip():
        return "failed", "转换产物为空（不写占位）"
    head = ""
    if provenance:
        head = "> 源文件：`%s` ｜ 由 yuque_office_convert 转换 ｜ %s\n\n" % (rel.as_posix(), date.today())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(head + body.rstrip() + "\n", encoding="utf-8", newline="\n")
    return "ok", "%d 字" % len(body)


def main():
    ap = argparse.ArgumentParser(description="办公文档 → Markdown（导入前预处理）")
    ap.add_argument("--src", required=True, help="输入文件或目录")
    ap.add_argument("--out", required=True, help="输出目录（必须与输入分离）")
    ap.add_argument("--include", help="只处理这些后缀，逗号分隔，如 .docx,.csv")
    ap.add_argument("--overwrite", action="store_true", help="覆盖已存在的输出")
    ap.add_argument("--no-provenance", action="store_true", help="不写源文件注记行")
    ap.add_argument("--dry", action="store_true", help="只列清单不写盘")
    args = ap.parse_args()

    src = Path(args.src).resolve()
    out = Path(args.out).resolve()
    if not src.exists():
        log("错误：输入路径不存在 - %s" % src)
        return 2
    if src == out or out in src.parents or src in out.parents:
        log("错误：输入与输出目录必须分离（当前 src=%s out=%s）" % (src, out))
        return 2
    if not args.dry:
        out.mkdir(parents=True, exist_ok=True)
    wanted = ({s.strip().lower() for s in args.include.split(",")}
              if args.include else SUPPORTED | UNSUPPORTED)
    src_root = src if src.is_dir() else src.parent
    files = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file())
    files = [p for p in files if p.suffix.lower() in wanted]

    stats = {"ok": 0, "skipped": 0, "failed": 0, "unsupported": 0}
    problems = []
    for path in files:
        if args.dry:
            status, detail = "ok", "（dry：未写盘）"
        else:
            status, detail = convert_one(path, src_root, out, args.overwrite,
                                         not args.no_provenance)
        stats[status] = stats.get(status, 0) + 1
        mark = {"ok": "✓", "skipped": "-", "failed": "✗", "unsupported": "!"}[status]
        log("%s %s  %s" % (mark, path.relative_to(src_root).as_posix(), detail))
        if status in ("failed", "unsupported"):
            problems.append(path.relative_to(src_root).as_posix())

    log("\n汇总：ok %(ok)d / skipped %(skipped)d / failed %(failed)d / unsupported %(unsupported)d" % stats)
    if problems:
        log("需处理：")
        for p in problems:
            log("  - %s" % p)
    if stats["ok"] and not args.dry:
        log("提示：导入前先跑 yuque_rewrite_images.py 传 %s 里的图，"
            "再把该目录从导入根删掉（硬规则 10）" % ASSETS_DIRNAME)
    return 1 if stats["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
