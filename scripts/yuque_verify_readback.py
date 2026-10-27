#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验收六查之 ⑤⑥：全库 word_count>0 + 逐篇回读对比（progress 账本 rel 路径映射，禁按 basename）。

通用版（2026-10-27 由 fpb-056/057 的 verify56/57.py 参数化入库）：
  python3 scripts/yuque_verify_readback.py --book <id> --root <本地树根> --progress <progress.json> --toc <toc.json>

关键约定：
  - 回读映射走 progress.json 的 rel 路径 → doc（禁按 basename：跨语言/多目录同名文件会取错版本，见 refs 六查）
  - docs 列表用 offset 翻页（page 参数无效，见 refs 坑 37）
  - 归一化对比容忍行尾/换行差异；小差异(≤8 行且长度比 0.7~1.4)只打印不判失败
  - 退出码：0=全绿；1=有异常
"""
import argparse, json, os, sys, time, urllib.request, urllib.error, difflib, re

BASE = 'https://www.yuque.com/api/v2'


def api(token, path, retries=4):
    for i in range(retries):
        req = urllib.request.Request(BASE + path)
        req.add_header('X-Auth-Token', token)
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** i * 1.5 + 1)
                continue
            raise
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(2 ** i * 1.5 + 1)
    raise RuntimeError('retries exhausted')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', required=True, type=int)
    ap.add_argument('--root', required=True, help='本地内容树根（与导入时一致）')
    ap.add_argument('--progress', required=True)
    ap.add_argument('--toc', required=True, help='GET /repos/{id}/toc 的原始响应 json')
    ap.add_argument('--token-env', default='TOKEN_L91')
    ap.add_argument('--cdn-pattern', default=r'https://cdn\.nlark\.com/[^)\s]+', help='本地 CDN 图引用统计正则')
    args = ap.parse_args()

    token = os.environ.get(args.token_env)
    if not token:
        sys.exit('找不到 token: 设置环境变量 %s' % args.token_env)

    prog = json.load(open(args.progress, encoding='utf-8'))
    toc = json.load(open(args.toc, encoding='utf-8'))['data']
    by_uuid = {n['uuid']: n for n in toc}

    rel2node = {}
    for rel, v in prog.get('nodes', {}).items():
        if isinstance(v, dict) and v.get('type') == 'doc':
            rel2node[rel] = v
    print('progress 账本文档数:', len(rel2node))
    if not rel2node:
        sys.exit('progress 无 doc 节点，检查 --progress 路径')

    print('\n===== ⑤ word_count 全库扫描 =====')
    docs_all, offset = [], 0
    while True:
        d = api(token, f'/repos/{args.book}/docs?offset={offset}&limit=100')
        data = d.get('data', [])
        docs_all.extend(data)
        if len(data) < 100:
            break
        offset += 100
    print('docs API total:', len(docs_all))
    zero = [x for x in docs_all if (x.get('word_count') or 0) <= 0]
    print('word_count<=0 的文档数:', len(zero))
    for x in zero[:10]:
        print('  ZERO wc:', x.get('id'), x.get('title'))
    wc_map = {str(x['id']): x for x in docs_all}
    ids_in_toc = [str(n.get('doc_id')) for n in toc if n['type'] == 'DOC']
    missing_from_api = [i for i in ids_in_toc if i not in wc_map]
    print('TOC DOC 里 docs API 缺失:', missing_from_api)

    print('\n===== ⑥ 逐篇回读（progress rel 路径映射，禁 basename） =====')
    cdn_re = re.compile(args.cdn_pattern)
    bad, stats = [], {'cdn': 0, 'checked': 0}

    for rel, v in sorted(rel2node.items()):
        node = by_uuid.get(v['uuid'])
        if not node:
            bad.append((rel, 'TOC 无此 uuid'))
            continue
        if node['type'] != 'DOC':
            continue
        doc_id = node.get('doc_id')
        local_path = os.path.join(args.root, rel)
        if not os.path.exists(local_path):
            bad.append((rel, '本地缺失'))
            continue
        local = open(local_path, encoding='utf-8').read()
        rd = api(token, f'/repos/{args.book}/docs/{doc_id}')
        remote = rd.get('data', {})
        body = remote.get('body') or remote.get('body_draft') or ''
        stats['checked'] += 1
        stats['cdn'] += len(cdn_re.findall(local))
        if (remote.get('word_count') or 0) <= 0:
            bad.append((rel, '回读 word_count<=0'))
        l_norm = local.strip().replace('\r\n', '\n').replace('\r', '\n')
        b_norm = body.strip().replace('\r\n', '\n').replace('\r', '\n')
        if l_norm == b_norm:
            print('  ✅', rel)
            continue
        diff = list(difflib.unified_diff(b_norm.split('\n'), l_norm.split('\n'), lineterm='', n=1))
        chg = len([x for x in diff if x.startswith(('+', '-')) and not x.startswith(('+++', '---'))])
        if chg <= 8 and len(b_norm) > 0.7 * len(l_norm) and len(b_norm) < 1.4 * len(l_norm):
            print(f'  ~ {rel} diff 行 {chg}（小差异，抽样看详情）')
            for x in diff[:14]:
                print('     ', x[:100])
        else:
            bad.append((rel, f'正文差异 {chg} 行'))
            print(f'  ❌ {rel} diff {chg} 行')
            for x in diff[:20]:
                print('     ', x[:120])

    print('\n===== 汇总 =====')
    print('回读篇数:', stats['checked'])
    print('本地 CDN 图引用:', stats['cdn'])
    print('异常:', len(bad))
    for b in bad[:20]:
        print('  BAD', b)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
