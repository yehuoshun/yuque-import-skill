#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from convert import convert_page, collect_imgs

RAW="/home/admin/.openclaw/workspace/tmp/hrl/raw"
CLEAN="/home/admin/.openclaw/workspace/tmp/hrl/clean"
IMG=os.path.join(CLEAN,"_img"); MATH=os.path.join(CLEAN,"_math")

PAGES=[
 ("00-前言.md","chapter__intro.html"),
 ("01-强化学习基础篇/01-初探强化学习.md","chapter__1__初探强化学习.html"),
 ("01-强化学习基础篇/02-多臂老虎机.md","chapter__1__多臂老虎机.html"),
 ("01-强化学习基础篇/03-马尔可夫决策过程.md","chapter__1__马尔可夫决策过程.html"),
 ("01-强化学习基础篇/04-动态规划算法.md","chapter__1__动态规划算法.html"),
 ("01-强化学习基础篇/05-时序差分算法.md","chapter__1__时序差分算法.html"),
 ("01-强化学习基础篇/06-Dyna-Q算法.md","chapter__1__dyna-q算法.html"),
 ("02-强化学习进阶篇/07-DQN算法.md","chapter__2__dqn算法.html"),
 ("02-强化学习进阶篇/08-DQN改进算法.md","chapter__2__dqn改进算法.html"),
 ("02-强化学习进阶篇/09-策略梯度算法.md","chapter__2__策略梯度算法.html"),
 ("02-强化学习进阶篇/10-Actor-Critic算法.md","chapter__2__actor-critic算法.html"),
 ("02-强化学习进阶篇/11-TRPO算法.md","chapter__2__trpo算法.html"),
 ("02-强化学习进阶篇/12-PPO算法.md","chapter__2__ppo算法.html"),
 ("02-强化学习进阶篇/13-DDPG算法.md","chapter__2__ddpg算法.html"),
 ("02-强化学习进阶篇/14-SAC算法.md","chapter__2__sac算法.html"),
 ("03-强化学习前沿篇/15-模仿学习.md","chapter__3__模仿学习.html"),
 ("03-强化学习前沿篇/16-模型预测控制.md","chapter__3__模型预测控制.html"),
 ("03-强化学习前沿篇/17-基于模型的策略优化.md","chapter__3__基于模型的策略优化.html"),
 ("03-强化学习前沿篇/18-离线强化学习.md","chapter__3__离线强化学习.html"),
 ("03-强化学习前沿篇/19-目标导向的强化学习.md","chapter__3__目标导向的强化学习.html"),
 ("03-强化学习前沿篇/20-多智能体强化学习入门.md","chapter__3__多智能体强化学习入门.html"),
 ("03-强化学习前沿篇/21-多智能体强化学习进阶.md","chapter__3__多智能体强化学习进阶.html"),
 ("22-总结与展望.md","chapter__ending.html"),
 ("23-课件.md","slides.html"),
]

def main():
    os.makedirs(IMG, exist_ok=True); os.makedirs(MATH, exist_ok=True)
    math_map={}
    all_imgs=[]
    report=[]
    for dest, src in PAGES:
        raw=open(os.path.join(RAW,src),encoding="utf-8").read()
        i=raw.find("__dumi-default-layout-content"); j=raw.find("<script", i)
        for nm in collect_imgs(raw[i:j], IMG):
            if nm not in all_imgs: all_imgs.append(nm)
        prefix = "../" * dest.count("/")   # 落到子目录的 md 相对自身须回退
        md, mstat = convert_page(raw, MATH, math_map, IMG, prefix=prefix)
        out=os.path.join(CLEAN,dest)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out,"w",encoding="utf-8").write(md)
        report.append((dest, len(md), mstat["n"], mstat["new"]))
        print(f"{dest:48s} md={len(md):7d} math={mstat['n']:4d} new={mstat['new']:4d}")
    # 下载图片
    print(f"\n图片 {len(all_imgs)} 张 → {IMG}")
    for k,nm in enumerate(all_imgs,1):
        p=os.path.join(IMG,nm)
        if os.path.exists(p): continue
        r=subprocess.run(["curl","-sL","--max-time","40","https://hrl.boyuai.com/static/"+nm,"-o",p])
        if r.returncode!=0 or os.path.getsize(p)==0:
            print("  MISS", nm)
    print("unique math svg:", len(math_map))
    json.dump({"pages":report,"n_img":len(all_imgs),"n_math":len(math_map)},
              open("/home/admin/.openclaw/workspace/tmp/hrl/build.json","w"), ensure_ascii=False, indent=1)

if __name__=="__main__":
    main()