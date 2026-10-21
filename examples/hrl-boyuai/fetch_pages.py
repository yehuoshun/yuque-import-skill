#!/usr/bin/env python3
import re, json, time, os, subprocess

BASE = "https://hrl.boyuai.com"
routes = [
 "/chapter/intro","/chapter/1","/chapter/1/初探强化学习","/chapter/1/多臂老虎机",
 "/chapter/1/马尔可夫决策过程","/chapter/1/动态规划算法","/chapter/1/时序差分算法","/chapter/1/dyna-q算法",
 "/chapter/2","/chapter/2/dqn算法","/chapter/2/dqn改进算法","/chapter/2/策略梯度算法",
 "/chapter/2/actor-critic算法","/chapter/2/trpo算法","/chapter/2/ppo算法","/chapter/2/ddpg算法","/chapter/2/sac算法",
 "/chapter/3","/chapter/3/模仿学习","/chapter/3/模型预测控制","/chapter/3/基于模型的策略优化",
 "/chapter/3/离线强化学习","/chapter/3/目标导向的强化学习","/chapter/3/多智能体强化学习入门","/chapter/3/多智能体强化学习进阶",
 "/chapter/ending","/slides",
]

def get(url):
    p = subprocess.run(["curl","-sL","--max-time","30","-A","Mozilla/5.0",url],
                       capture_output=True)
    return p.stdout.decode("utf-8","replace")

os.makedirs("/home/admin/.openclaw/workspace/tmp/hrl/raw", exist_ok=True)
rows=[]
for rt in routes:
    url = BASE + rt
    html = get(url)
    fn = "/home/admin/.openclaw/workspace/tmp/hrl/raw/" + rt.strip("/").replace("/","__") + ".html"
    open(fn,"w",encoding="utf-8").write(html)
    m = re.search(r'<div class="__dumi-default-layout-content">(.*?)</div></div><script', html, re.S)
    c = m.group(1) if m else ""
    nimg = len(re.findall(r'<img\s', c))
    nmath = len(re.findall(r'<mjx-container', c))
    ncode = len(re.findall(r'<pre', c))
    ntab = len(re.findall(r'<table', c))
    nh = len(re.findall(r'<h[123]\s', c))
    rows.append((rt, len(c), nimg, nmath, ncode, ntab, nh))
    print(f"{rt:44s} len={len(c):7d} img={nimg:3d} math={nmath:3d} pre={ncode:3d} tbl={ntab:2d} h={nh}")
    time.sleep(0.3)

tot_img=sum(r[2] for r in rows); tot_math=sum(r[3] for r in rows); tot_pre=sum(r[4] for r in rows)
print("TOTAL pages",len(rows),"img",tot_img,"math",tot_math,"pre",tot_pre)
json.dump(rows, open("/home/admin/.openclaw/workspace/tmp/hrl/probe.json","w"), ensure_ascii=False, indent=1)