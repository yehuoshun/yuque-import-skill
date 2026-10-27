import json,os,subprocess,concurrent.futures as cf
BASE="https://c-faq-chn.sourceforge.net/ccfaq/"
items=json.load(open('/home/admin/.openclaw/workspace/tmp/cfaq-toc.json'))
os.makedirs('raw',exist_ok=True)
def g(i):
    href=i['href']; p=f"raw/{href}"
    if os.path.exists(p) and os.path.getsize(p)>500: return "cached"
    for _ in range(3):
        r=subprocess.run(["curl","-s","--max-time","40","-o",p,"-w","%{http_code}",BASE+href],capture_output=True,text=True)
        if r.stdout.strip()=="200" and os.path.getsize(p)>500: return "ok"
    return "FAIL "+href
with cf.ThreadPoolExecutor(6) as ex: res=list(ex.map(g,items))
from collections import Counter
print(Counter(r.split()[0] for r in res))
print([r for r in res if r.startswith("FAIL")][:5])
