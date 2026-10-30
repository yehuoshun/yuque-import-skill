#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_office_convert.py — yuque_office_convert.py 回归单测
========================================================
不联网、不碰语雀：临时目录里造最小 docx / csv / 坏文件，验证
「正常转换」「空产物不写占位」「坏文件记 failed 且不中断」。

用法（在 scripts 目录下）:
    python3 test_office_convert.py
"""
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import yuque_office_convert as oc

DOC_CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
          'officedocument.wordprocessingml.document.main+xml"/></Types>')
DOC_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
            'relationships/officeDocument" Target="word/document.xml"/></Relationships>')


def make_docx(path, body_xml):
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           '<w:body>%s</w:body></w:document>' % body_xml)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", DOC_CT)
        z.writestr("_rels/.rels", DOC_RELS)
        z.writestr("word/document.xml", doc)


def run_case(src_dir, out_dir, overwrite=False):
    src_root = Path(src_dir)
    stats = {"ok": 0, "skipped": 0, "failed": 0, "unsupported": 0}
    for path in sorted(src_root.rglob("*")):
        if path.is_file():
            status, _ = oc.convert_one(path, src_root, Path(out_dir), overwrite, True)
            stats[status] = stats.get(status, 0) + 1
    return stats


def main():
    tmp = Path(tempfile.mkdtemp(prefix="office_convert_test_"))
    try:
        src, out = tmp / "in", tmp / "out"
        src.mkdir()

        # ---------- 测试 1：正常输入（docx 标题 + 正文） → 标题级别保留、注记行存在 ----------
        make_docx(src / "guide.docx",
                  '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
                  '<w:r><w:t>Install Guide</w:t></w:r></w:p>'
                  '<w:p><w:r><w:t>Run the command.</w:t></w:r></w:p>')
        (src / "table.csv").write_text("name,value\nalpha,1\nbeta,2\n", encoding="utf-8")
        st = run_case(src, out)
        md = (out / "guide.md").read_text(encoding="utf-8")
        assert st["ok"] == 2, "两个文件都应 ok，实际 %r" % st
        assert md.startswith("> 源文件：`guide.docx`"), "缺源文件注记行"
        assert "# Install Guide" in md and "Run the command" in md, "标题级别或正文丢失"
        csv_md = (out / "table.md").read_text(encoding="utf-8")
        assert "| name | value |" in csv_md and "| alpha | 1 |" in csv_md, "CSV 表头/数据错"
        print("✅ 测试1 正常：docx→md 保留结构、csv→表格、注记行就位")

        # ---------- 测试 2：边界输入（空 docx / 已存在输出不覆盖） → failed 不写占位 + skipped ----------
        make_docx(src / "empty.docx", "<w:p/>")
        st = run_case(src, out)
        assert st["failed"] == 1, "空产物应记 failed，实际 %r" % st
        assert not (out / "empty.md").exists(), "空产物不许写占位文件"
        assert st["skipped"] == 2, "已存在输出应 skipped，实际 %r" % st
        print("✅ 测试2 边界：空产物 failed 且不落盘；已存在输出 skipped")

        # ---------- 测试 3：异常输入（坏 docx 字节 + 旧格式 .xls） → failed/unsupported 且不中断 ----------
        (src / "broken.docx").write_bytes(b"not a zip at all")
        (src / "legacy.xls").write_bytes(b"\xd0\xcf\x11\xe0")
        st = run_case(src, out)
        assert st["failed"] == 2, "坏文件应记 failed，实际 %r" % st
        assert st["unsupported"] == 1, ".xls 应记 unsupported，实际 %r" % st
        assert st["skipped"] == 2, "坏文件不该影响已有产物的 skipped 计数，实际 %r" % st
        print("✅ 测试3 异常：坏 docx failed、.xls unsupported，且后续文件继续处理")

        # ---------- 附加：src/out 同目录必须拒绝（CLI 层，退出码 2） ----------
        rc = os.system("python3 yuque_office_convert.py --src %s --out %s >/dev/null 2>&1"
                       % (src, src))
        assert rc == 512, "同目录应退出码 2（os.system 返回 512），实际 %d" % rc
        print("✅ 附加：输入输出同目录被拒绝（退出码 2）")
        print("\n全部通过 ✅")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()