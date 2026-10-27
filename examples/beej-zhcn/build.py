#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""myliao2007/beej-zhcn（Beej's Guide to Network Programming 简体中文版）→ clean tree"""
import os,re,shutil

SRC="/home/admin/.openclaw/workspace/tmp/beej-zhcn"
OUT="/home/admin/.openclaw/workspace/tmp/beej-zhcn-clean"
SAFE=str.maketrans({"/":"／","\\":"＼",":":"：","*":"＊","?":"？",'"':"＂","<":"＜",">":"＞","|":"｜"})
def safe(s): return s.translate(SAFE).strip().strip(".")

items=[]
for ln in open(f"{SRC}/SUMMARY.md",encoding="utf-8"):
    m=re.match(r"^(\s*)\*\s*\[(.+?)\]\((.+?)\)\s*$",ln)
    if m:
        items.append({"level":len(m.group(1))//2,"title":m.group(2).replace("\\",""),
                      "path":m.group(3).replace("\\",""),"children":[]})
root_items=[]; st=[]
for it in items:
    while st and st[-1]["level"]>=it["level"]: st.pop()
    (st[-1]["children"] if st else root_items).append(it)
    st.append(it)

if os.path.exists(OUT): shutil.rmtree(OUT)
os.makedirs(OUT); os.makedirs(f"{OUT}/imgs")
copied=set()

def strip_h1(b):
    ls=b.split("\n")
    for i,l in enumerate(ls[:5]):
        if l.strip().startswith("# "): return "\n".join(ls[i+1:]).lstrip("\n")
    return b

def fix_imgs(b,rel):
    def rep(m):
        alt,src=m.group(1),m.group(2)
        if "/.gitbook/assets/" in src or src.startswith(".gitbook/assets/"):
            fn=os.path.basename(src); p=f"{SRC}/.gitbook/assets/{fn}"
            if os.path.exists(p):
                if fn not in copied: shutil.copy2(p,f"{OUT}/imgs/{fn}"); copied.add(fn)
                return f"![{alt}]({rel}imgs/{fn})"
        return m.group(0)
    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)",rep,b)

stats={"docs":0,"dirs":0}
def emit(nodes,dirpath,depth):
    rel="../"*depth
    for i,it in enumerate(nodes,1):
        src=f"{SRC}/{it['path']}"; assert os.path.exists(src),it["path"]
        body=fix_imgs(strip_h1(open(src,encoding="utf-8").read()),rel)
        base=f"{i:02d}-{safe(it['title'])}"
        if it["children"]:
            d=f"{dirpath}/{base}"; os.makedirs(d)
            body=fix_imgs(strip_h1(open(src,encoding="utf-8").read()),"../"*(depth+1))
            open(f"{d}/00-{safe(it['title'])}.md","w",encoding="utf-8").write(body); stats["docs"]+=1
            emit(it["children"],d,depth+1); stats["dirs"]+=1
        else:
            open(f"{dirpath}/{base}.md","w",encoding="utf-8").write(body); stats["docs"]+=1
emit(root_items,OUT,0)
print("SUMMARY条目",len(items),"→ 文档",stats["docs"],"目录",stats["dirs"],"图",len(copied))
