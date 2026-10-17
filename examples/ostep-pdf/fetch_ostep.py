#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OSTEP 章节清单 + PDF 下载。"""
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import urllib.request

BASE = "https://pages.cs.wisc.edu/~remzi/OSTEP/"
WORK = "/home/admin/.openclaw/workspace/tmp/ostep"
PDFDIR = os.path.join(WORK, "pdf")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

PLAN = [
    ("00-前言", None, "Dedication", "dedication.pdf"),
    ("00-前言", None, "Preface", "preface.pdf"),
    ("00-前言", None, "TOC", "toc.pdf"),

    ("01-Introduction", 1, "Dialogue", "dialogue-threeeasy.pdf"),
    ("01-Introduction", 2, "Introduction", "intro.pdf"),

    ("02-Virtualization", 3, "Dialogue", "dialogue-virtualization.pdf"),
    ("02-Virtualization", 4, "Processes", "cpu-intro.pdf"),
    ("02-Virtualization", 5, "Process API", "cpu-api.pdf"),
    ("02-Virtualization", 6, "Direct Execution", "cpu-mechanisms.pdf"),
    ("02-Virtualization", 7, "CPU Scheduling", "cpu-sched.pdf"),
    ("02-Virtualization", 8, "Multi-level Feedback", "cpu-sched-mlfq.pdf"),
    ("02-Virtualization", 9, "Lottery Scheduling", "cpu-sched-lottery.pdf"),
    ("02-Virtualization", 10, "Multi-CPU Scheduling", "cpu-sched-multi.pdf"),
    ("02-Virtualization", 11, "Summary", "cpu-dialogue.pdf"),
    ("02-Virtualization", 12, "Dialogue", "dialogue-vm.pdf"),
    ("02-Virtualization", 13, "Address Spaces", "vm-intro.pdf"),
    ("02-Virtualization", 14, "Memory API", "vm-api.pdf"),
    ("02-Virtualization", 15, "Address Translation", "vm-mechanism.pdf"),
    ("02-Virtualization", 16, "Segmentation", "vm-segmentation.pdf"),
    ("02-Virtualization", 17, "Free Space Management", "vm-freespace.pdf"),
    ("02-Virtualization", 18, "Introduction to Paging", "vm-paging.pdf"),
    ("02-Virtualization", 19, "Translation Lookaside Buffers", "vm-tlbs.pdf"),
    ("02-Virtualization", 20, "Advanced Page Tables", "vm-smalltables.pdf"),
    ("02-Virtualization", 21, "Swapping - Mechanisms", "vm-beyondphys.pdf"),
    ("02-Virtualization", 22, "Swapping - Policies", "vm-beyondphys-policy.pdf"),
    ("02-Virtualization", 23, "Complete VM Systems", "vm-complete.pdf"),
    ("02-Virtualization", 24, "Summary", "vm-dialogue.pdf"),

    ("03-Concurrency", 25, "Dialogue", "dialogue-concurrency.pdf"),
    ("03-Concurrency", 26, "Concurrency and Threads", "threads-intro.pdf"),
    ("03-Concurrency", 27, "Thread API", "threads-api.pdf"),
    ("03-Concurrency", 28, "Locks", "threads-locks.pdf"),
    ("03-Concurrency", 29, "Locked Data Structures", "threads-locks-usage.pdf"),
    ("03-Concurrency", 30, "Condition Variables", "threads-cv.pdf"),
    ("03-Concurrency", 31, "Semaphores", "threads-sema.pdf"),
    ("03-Concurrency", 32, "Concurrency Bugs", "threads-bugs.pdf"),
    ("03-Concurrency", 33, "Event-based Concurrency", "threads-events.pdf"),
    ("03-Concurrency", 34, "Summary", "threads-dialogue.pdf"),

    ("04-Persistence", 35, "Dialogue", "dialogue-persistence.pdf"),
    ("04-Persistence", 36, "I-O Devices", "file-devices.pdf"),
    ("04-Persistence", 37, "Hard Disk Drives", "file-disks.pdf"),
    ("04-Persistence", 38, "Redundant Disk Arrays (RAID)", "file-raid.pdf"),
    ("04-Persistence", 39, "Files and Directories", "file-intro.pdf"),
    ("04-Persistence", 40, "File System Implementation", "file-implementation.pdf"),
    ("04-Persistence", 41, "Fast File System (FFS)", "file-ffs.pdf"),
    ("04-Persistence", 42, "FSCK and Journaling", "file-journaling.pdf"),
    ("04-Persistence", 43, "Log-structured File System (LFS)", "file-lfs.pdf"),
    ("04-Persistence", 44, "Flash-based SSDs", "file-ssd.pdf"),
    ("04-Persistence", 45, "Data Integrity and Protection", "file-integrity.pdf"),
    ("04-Persistence", 46, "Summary", "file-dialogue.pdf"),
    ("04-Persistence", 47, "Dialogue", "dialogue-distribution.pdf"),
    ("04-Persistence", 48, "Distributed Systems", "dist-intro.pdf"),
    ("04-Persistence", 49, "Network File System (NFS)", "dist-nfs.pdf"),
    ("04-Persistence", 50, "Andrew File System (AFS)", "dist-afs.pdf"),
    ("04-Persistence", 51, "Summary", "dist-dialogue.pdf"),

    ("05-Security", 52, "Dialogue", "dialogue-security.pdf"),
    ("05-Security", 53, "Intro Security", "security-intro.pdf"),
    ("05-Security", 54, "Authentication", "security-authentication.pdf"),
    ("05-Security", 55, "Access Control", "security-access.pdf"),
    ("05-Security", 56, "Cryptography", "security-crypto.pdf"),
    ("05-Security", 57, "Distributed", "security-distributed.pdf"),

    ("06-Appendices", None, "Dialogue - VMM", "dialogue-vmm.pdf"),
    ("06-Appendices", None, "Virtual Machines", "vmm-intro.pdf"),
    ("06-Appendices", None, "Dialogue - Monitors", "dialogue-monitors.pdf"),
    ("06-Appendices", None, "Monitors", "threads-monitors.pdf"),
    ("06-Appendices", None, "Dialogue - Labs", "dialogue-labs.pdf"),
    ("06-Appendices", None, "Lab Tutorial", "lab-tutorial.pdf"),
    ("06-Appendices", None, "Systems Labs", "lab-projects-systems.pdf"),
    ("06-Appendices", None, "xv6 Labs", "lab-projects-xv6.pdf"),
]


def main():
    os.makedirs(PDFDIR, exist_ok=True)
    plan = []
    for part, num, title, pdf in PLAN:
        stem = re.sub(r"[/\\:*?\"<>|]", "-", title)
        fname = ("%02d-%s.md" % (num, stem)) if num else ("%s.md" % stem)
        plan.append({"part": part, "num": num, "title": title, "pdf": pdf, "out": fname})
    json.dump(plan, open(os.path.join(WORK, "plan.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("章节数:", len(plan))

    def dl(item):
        path = os.path.join(PDFDIR, item["pdf"])
        if os.path.exists(path) and os.path.getsize(path) > 10000:
            return item["pdf"], "skip", os.path.getsize(path)
        for attempt in range(3):
            try:
                req = urllib.request.Request(BASE + item["pdf"], headers=UA)
                with urllib.request.urlopen(req, timeout=90) as r:
                    data = r.read()
                open(path, "wb").write(data)
                return item["pdf"], "ok", len(data)
            except Exception as e:  # noqa: BLE001
                if attempt == 2:
                    return item["pdf"], "ERR %s" % e, 0
                time.sleep(3)
    ok = err = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        for name, status, size in ex.map(dl, plan):
            if status.startswith("ERR"):
                err += 1
                print("FAIL %s %s" % (name, status))
            else:
                ok += 1
                print("%-28s %-4s %8d" % (name, status, size))
    print("下载完成 ok=%d err=%d" % (ok, err))


if __name__ == "__main__":
    main()