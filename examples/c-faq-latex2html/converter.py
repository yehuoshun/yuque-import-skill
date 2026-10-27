# -*- coding: utf-8 -*-
"""LaTeX2HTML（C 语言常见问题集 中译本）逐页 HTML → Markdown"""
import re
from html.parser import HTMLParser

NAV_IMGS={"prev.png","prev_g.png","up.png","up_g.png","next.png","next_g.png","contents.png","index.png"}

class Conv(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out=[]          # 成型的行
        self.line=[]         # 当前行缓冲
        self.skip=0
        self.pre=None        # 代码块缓冲
        self.head=None       # 标题缓冲（首个标题丢弃）
        self.first_head_done=False
        self.in_table=0; self.rows=[]; self.cell=None
        self.listdepth=0; self.dt_open=False; self.href=None

    # ---- 缓冲工具 ----
    def flush(self):
        if self.line:
            s=re.sub(r"[\s\u00a0]+"," ","".join(self.line)).strip()
            s=s.replace(" **：","**：")
            s=re.sub(r"(?<=[\u3000-\u9fff\uff00-\uffef\u2018-\u201d])\s+(?=[\u3000-\u9fff\uff00-\uffef\u2018-\u201d])","",s)
            if s: self.out.append(s)
            self.line=[]
    def blank(self):
        self.flush()
        if self.out and self.out[-1]!="": self.out.append("")

    # ---- 数据 ----
    def handle_data(self,d):
        if self.skip: return
        if self.pre is not None: self.pre.append(d); return
        if self.in_table and self.cell is not None: self.cell.append(d); return
        if self.head is not None: self.head.append(d); return
        self.line.append(d)

    def handle_starttag(self,tag,attrs):
        a=dict(attrs); cls=a.get("class","")
        if self.skip:
            if tag in("ul","ol","dl","div"): self.skip+=1
            return
        if tag in("ul","ol","dl") and cls=="ChildLinks": self.skip=1; return
        if tag=="div" and cls=="navigation": self.skip=1; return
        if tag in("h1","h2","h3"):
            self.blank(); self.head=[]; self.headtag=tag; return
        if tag=="pre":
            self.blank(); self.pre=[]
        elif tag=="p": self.blank()
        elif tag=="br":
            if self.pre is not None: self.line.append("\n")
            else: self.line.append("  \n")
        elif tag=="hr": self.blank()
        elif tag in("ul","ol"):
            self.listdepth+=1; self.blank()
        elif tag=="li":
            self.flush(); self.line.append("  "*max(0,self.listdepth-1)+"- ")
        elif tag=="dl": self.blank()
        elif tag=="dt":
            self.flush(); self.line.append("- **"); self.dt_open=True
        elif tag=="dd":
            if self.dt_open: self.line.append("**： "); self.dt_open=False
        elif tag in("i","em","cite"): self.line.append("*")
        elif tag in("b","strong"): self.line.append("**")
        elif tag in("tt","code","kbd","samp"):
            if self.pre is None: self.line.append("`")
        elif tag=="sup": self.line.append("^")
        elif tag=="sub": self.line.append("_")
        elif tag=="a":
            self.href=a.get("href","")
            if self.href.startswith("http"): self.line.append("[")
        elif tag=="img":
            src=a.get("src","")
            if src and src not in NAV_IMGS: self.line.append(f"![]({src})")
        elif tag=="table":
            self.blank(); self.in_table=1; self.rows=[]
        elif tag=="tr":
            if self.in_table: self.rows.append([])
        elif tag in("td","th"):
            if self.in_table: self.cell=[]; self.rows[-1].append(self.cell)

    def handle_endtag(self,tag):
        if self.skip:
            if tag in("ul","ol","dl","div"): self.skip-=1
            return
        if tag in("h1","h2","h3") and self.head is not None:
            txt=re.sub(r"[\s\u00a0]+"," ","".join(self.head)).strip()
            if self.first_head_done: self.blank(); self.line.append(("### " if tag=="h3" else "## ")+txt)
            self.first_head_done=True; self.head=None; self.blank(); return
        if tag=="pre" and self.pre is not None:
            lines="".join(self.pre).split("\n")
            ind=[len(l)-len(l.lstrip(" ")) for l in lines if l.strip()]
            k=min(ind) if ind else 0
            body=[l[k:] if l.strip() else "" for l in lines]
            while body and not body[0].strip(): body.pop(0)
            while body and not body[-1].strip(): body.pop()
            self.out.append("```"); self.out.extend(body); self.out.append("```"); self.out.append("")
            self.pre=None; return
        if tag=="p": self.blank()
        elif tag in("ul","ol"): self.listdepth=max(0,self.listdepth-1); self.blank()
        elif tag=="li": self.flush()
        elif tag=="dt": self.line.append("**： "); self.dt_open=False
        elif tag=="dd": self.flush()
        elif tag=="dl": self.flush(); self.blank()
        elif tag in("i","em","cite"): self.line.append("*")
        elif tag in("b","strong"): self.line.append("**")
        elif tag in("tt","code","kbd","samp"):
            if self.pre is None: self.line.append("`")
        elif tag=="a":
            if (self.href or "").startswith("http"): self.line.append(f"]({self.href})")
            self.href=None
        elif tag=="table" and self.in_table:
            rows=[[re.sub(r"\s+"," ","".join(c)).strip().replace("|","\\|") for c in r] for r in self.rows if r]
            if rows:
                w=max(len(r) for r in rows); rows=[r+[""]*(w-len(r)) for r in rows]
                blk=["| "+" | ".join(rows[0])+" |","|"+"|".join(["---"]*w)+"|"]
                blk+=["| "+" | ".join(r)+" |" for r in rows[1:]]
                self.flush(); self.out.extend(blk); self.out.append("")
            self.in_table=0; self.rows=[]; self.cell=None
        elif tag in("td","th"): self.cell=None

def convert(path):
    t=open(path,'rb').read().decode('gb18030','ignore')
    i=t.find('End of Navigation Panel')
    if i>=0: i=t.find('-->',i)+3
    j=t.rfind('<DIV CLASS="navigation">')
    c=t[i:j] if i>=0 and j>i else t
    p=Conv(); p.feed(c); p.flush(); p.blank()
    md="\n".join(p.out)
    md=re.sub(r"\n{3,}","\n\n",md)
    return md.strip()+"\n"
