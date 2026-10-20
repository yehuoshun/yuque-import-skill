import json,urllib.request,urllib.parse,gzip,io,sys,time

def index(cid,prefix,limit=800):
    url=f"https://index.commoncrawl.org/{cid}-index?url={urllib.parse.quote(prefix,safe='')}&matchType=prefix&output=json&limit={limit}"
    for a in range(4):
        try:
            r=urllib.request.urlopen(url,timeout=90).read().decode()
            if not r.strip(): time.sleep(3); continue
            return [json.loads(l) for l in r.strip().split("\n") if l.strip()]
        except Exception as e:
            print("idx err",e); time.sleep(5)
    return []

def fetch(rec):
    off=int(rec["offset"]); ln=int(rec["length"])
    url=f"https://data.commoncrawl.org/{rec['filename']}"
    req=urllib.request.Request(url,headers={"Range":f"bytes={off}-{off+ln-1}"})
    for a in range(4):
        try:
            data=urllib.request.urlopen(req,timeout=120).read()
            raw=gzip.decompress(data)
            # strip WARC header then HTTP header
            i=raw.find(b"\r\n\r\n")
            rest=raw[i+4:]
            j=rest.find(b"\r\n\r\n")
            return rest[j+4:]
        except Exception as e:
            print("fetch err",e); time.sleep(5)
    return None

if __name__=="__main__":
    cid=sys.argv[1]; target=sys.argv[2]; out=sys.argv[3]
    recs=index(cid,"sketchcn.com/")
    hits=[r for r in recs if r["url"].rstrip("/")==target.rstrip("/")]
    print("hits",len(hits))
    for r in hits:
        print(r["timestamp"],r["url"],r["status"],r["length"])
    best=hits[0]
    html=fetch(best)
    print("html bytes",len(html) if html else None)
    open(out,"wb").write(html or b"")
