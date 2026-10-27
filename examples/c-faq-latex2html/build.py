import json,os,re,shutil,sys
sys.path.insert(0,'/home/admin/.openclaw/workspace/tmp/cfaq-build')
from conv import convert
T="/home/admin/.openclaw/workspace/tmp"
SRC=f"{T}/cfaq-build/raw"; OUT=f"{T}/cfaq-clean"
SAFE=str.maketrans({"/":"／","\\":"＼",":":"：","*":"＊","?":"？",'"':"＂","<":"＜",">":"＞","|":"｜"})
CJK=r"[\u4e00-\u9fff\uff00-\uffef]"
def safe(s,n=None):
    s=re.sub(r"(?<=%s)\s*\n\s*(?=%s)"%(CJK,CJK),"",s)   # 中文换行直接拼
    s=s.translate(SAFE).replace("\n"," "); s=re.sub(r"\s+"," ",s).strip().strip(".")
    if n and len(s)>n: s=s[:n].rstrip()+"…"
    return s
items=json.load(open(f"{T}/cfaq-toc.json"))
chaps=[]
for it in items:
    if it["depth"]==1:
        if it["href"]=="node1.html": continue      # 目录页跳过
        chaps.append({**it,"qs":[]})
    else:
        chaps[-1]["qs"].append(it)
if os.path.exists(OUT): shutil.rmtree(OUT)
os.makedirs(OUT)
stats={"dirs":0,"docs":0,"empty":[]}
for ci,ch in enumerate(chaps,1):
    m=re.match(r"^(\d+)\.\s*(.*)$",ch["title"])
    no=int(m.group(1)) if m else ci; name=m.group(2) if m else ch["title"]
    base=f"{no:02d}-{safe(name,45)}"
    if ch["qs"]:
        d=f"{OUT}/{base}"; os.makedirs(d); stats["dirs"]+=1
        for qi,q in enumerate(ch["qs"],1):
            md=convert(f"{SRC}/{q['href']}")
            if len(md.strip())<5: stats["empty"].append(q["href"])
            qn=re.match(r"^([\d.]+)\s*(.*)$",q["title"]); qt=qn.group(2) if qn else q["title"]
            open(f"{d}/{qi:02d}-{safe(q['title'],48)}.md","w",encoding="utf-8").write(md)
            stats["docs"]+=1
    else:
        md=convert(f"{SRC}/{ch['href']}")
        if len(md.strip())<5: stats["empty"].append(ch["href"])
        open(f"{OUT}/{base}.md","w",encoding="utf-8").write(md); stats["docs"]+=1
# 图片
if os.path.exists(f"{SRC}/img1.png"):
    os.makedirs(f"{OUT}/imgs",exist_ok=True)
    shutil.copy(f"{SRC}/img1.png",f"{OUT}/imgs/img1.png")
    for dp,_,fs in os.walk(OUT):
        for f in fs:
            if f.endswith(".md"):
                p=os.path.join(dp,f); t=open(p,encoding="utf-8").read()
                if "](img1.png)" in t:
                    rel="../"*(os.path.relpath(dp,OUT).count(os.sep)+1)
                    open(p,"w",encoding="utf-8").write(t.replace("](img1.png)",f"]({rel}imgs/img1.png)"))
print("章节",len(chaps),"目录",stats["dirs"],"文档",stats["docs"],"空正文",stats["empty"])
