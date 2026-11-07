#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_novel_toc_fix_retry.py — yuque_novel_toc_fix.py 重试逻辑回归单测
========================================================
不联网：monkeypatch 网络层（subprocess.run / get_toc_docs / mcporter_call），
验证「stdio 抽风重试」「MCP error 不重试」「移动失败重试 3 轮」「HTTP 分支分发」「复验重算轮」行为。

用法:
    python3 test_novel_toc_fix_retry.py
"""
import json
import os

import yuque_backend as yb
import yuque_novel_toc_fix

os.environ['YUQUE_TRANSPORT'] = 'mcp'   # 强制走 MCP 分支，测试不联网
yb._MODE = 'mcp'

# ---------- 测试 1：输出解析失败 → 重试 retries 次后放弃 ----------
calls = {'n': 0}


def fake_run_bad(cmd, **kw):
    calls['n'] += 1

    class R:
        stdout = 'not json at all'
        stderr = ''
        returncode = 1
    return R()


orig_run = yb.subprocess.run
yb.subprocess.run = fake_run_bad
r = yb._mcporter_call('yuque_get_toc', {'book_id': '1'}, retries=2)
assert isinstance(r, dict) and r.get('error') and calls['n'] == 2, \
    f"应重试 2 次后返回 error，实际 {calls['n']} 次 / {r}"
print("✅ 坏输出：重试 2 次后返回 error")

# ---------- 测试 2：MCP error（参数/权限错误）不重试 ----------
calls['n'] = 0


def fake_run_mcperr(cmd, **kw):
    calls['n'] += 1

    class R:
        stdout = 'MCP error: book_id must be string'
        stderr = ''
        returncode = 1
    return R()


yb.subprocess.run = fake_run_mcperr
r = yb._mcporter_call('yuque_get_toc', {'book_id': '1'}, retries=2)
assert isinstance(r, dict) and r.get('error') and calls['n'] == 1, \
    f"MCP error 不应重试，实际 {calls['n']} 次 / {r}"
print("✅ MCP error：不重试，直接失败")

# ---------- 测试 3：坏输出后第 2 次成功 ----------
calls['n'] = 0


def fake_run_then_ok(cmd, **kw):
    calls['n'] += 1

    class R:
        stdout = 'not json' if calls['n'] == 1 else json.dumps({'ok': True})
        stderr = ''
        returncode = 1 if calls['n'] == 1 else 0
    return R()


yb.subprocess.run = fake_run_then_ok
r = yb._mcporter_call('yuque_get_toc', {'book_id': '1'}, retries=3)
assert r == {'ok': True} and calls['n'] == 2, f"应第 2 次成功，实际 {calls['n']} 次 / {r}"
print("✅ 坏输出后第 2 次成功：正常返回")

yb.subprocess.run = orig_run

# ---------- 测试 4：单节点移动失败重试 3 轮后成功 ----------
seq = {'get': 0, 'move': 0}


def fake_get_toc(book_id):
    seq['get'] += 1
    if seq['get'] == 1:  # 初始：乱序 B,A
        return [{'type': 'DOC', 'title': 'B', 'uuid': 'b'},
                {'type': 'DOC', 'title': 'A', 'uuid': 'a'}]
    return [{'type': 'DOC', 'title': 'A', 'uuid': 'a'},  # 复验：正确顺序
            {'type': 'DOC', 'title': 'B', 'uuid': 'b'}]


def fake_call(tool, args_dict, timeout=60, retries=2):
    if tool == 'yuque_update_toc':
        seq['move'] += 1
        if seq['move'] <= 2:  # 前两轮失败
            return None
        return {'data': 'ok'}
    return None


yuque_novel_toc_fix.get_toc_docs = fake_get_toc
yuque_novel_toc_fix.mcporter_call = fake_call

tmp = '/tmp/reorder_test_chapters.json'
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump([['A', ''], ['B', '']], f, ensure_ascii=False)
ok = yuque_novel_toc_fix.reorder('1', tmp, verbose=False)
assert ok, "reorder 应成功"
assert seq['move'] == 3, f"移动应重试到第 3 轮，实际 {seq['move']} 轮"
os.remove(tmp)
print("✅ 单节点移动：前 2 轮失败后第 3 轮成功")

# ---------- 测试 5：3 轮全失败 → 中止返回 False ----------
seq = {'get': 0, 'move': 0}


def fake_get_toc2(book_id):
    seq['get'] += 1
    if seq['get'] == 1:
        return [{'type': 'DOC', 'title': 'B', 'uuid': 'b'},
                {'type': 'DOC', 'title': 'A', 'uuid': 'a'}]
    return [{'type': 'DOC', 'title': 'A', 'uuid': 'a'},
            {'type': 'DOC', 'title': 'B', 'uuid': 'b'}]


def fake_call2(tool, args_dict, timeout=60, retries=2):
    if tool == 'yuque_update_toc':
        seq['move'] += 1
        return None  # 永远失败
    return None


yuque_novel_toc_fix.get_toc_docs = fake_get_toc2
yuque_novel_toc_fix.mcporter_call = fake_call2

with open(tmp, 'w', encoding='utf-8') as f:
    json.dump([['A', ''], ['B', '']], f, ensure_ascii=False)
ok = yuque_novel_toc_fix.reorder('1', tmp, verbose=False)
assert not ok, "3 轮全失败应中止返回 False"
assert seq['move'] == 3, f"应恰好 3 轮，实际 {seq['move']}"
os.remove(tmp)
print("✅ 3 轮全失败：中止返回 False，不无限重试")

# ---------- 测试 6：HTTP 直连分支的工具分发（mock 掉 _api，不联网） ----------
seen = {}


def fake_api(method, path, payload=None, retries=4, base=None, auth=True):
    seen['method'], seen['path'], seen['payload'] = method, path, payload
    if path == '/user':
        return {'data': {'login': 'u'}}
    if path.endswith('/docs') and method == 'POST':
        return {'data': {'id': 999, 'title': payload.get('title')}}
    if path.endswith('/toc') and method == 'GET':
        return {'data': [{'type': 'DOC', 'title': 'A', 'uuid': 'a'}]}
    if path.endswith('/toc') and method == 'PUT':
        return {'data': [{'type': 'DOC', 'title': 'A', 'uuid': 'a'}]}
    if path.endswith('/repos') and method == 'POST':
        return {'data': {'id': 888, 'name': payload.get('name'), 'slug': payload.get('slug'), 'login': 'u'}}
    return {'error': 'unexpected'}


orig_api = yb._api
yb._api = fake_api
yb._MODE = 'http'
yb._LOGIN = None

d = yb.call('yuque_create_repo', {'name': 'zz-test-book', 'description': 'x'})
assert d.get('id') == 888 and seen['path'].endswith('/repos'), d
assert seen['payload'].get('slug') == 'zz-test-book', f"应生成 slug: {seen['payload']}"

d = yb.call('yuque_create_doc', {'book_id': '1', 'title': '第一章', 'body': 'b', 'format': 'markdown'})
assert d.get('id') == 999 and seen['path'] == '/repos/1/docs', d

toc = yb.call('yuque_get_toc', {'book_id': '1'})
assert isinstance(toc, list) and seen['path'] == '/repos/1/toc', toc

r = yb.call('yuque_update_toc', {'book_id': '1', 'action': 'prependNode',
                                 'action_mode': 'sibling', 'node_uuid': 'a', 'target_uuid': 'b'})
assert isinstance(r, dict) and 'data' in r, r
assert seen['payload'] == {'action': 'prependNode', 'action_mode': 'sibling',
                           'node_uuid': 'a', 'target_uuid': 'b'}, seen['payload']
byb_err = yb.call('yuque_unknown_tool', {'book_id': '1'})
assert byb_err.get('error'), byb_err
yb._api = orig_api
yb._MODE = 'mcp'
print("✅ HTTP 分支：建库/建文档/读TOC/改TOC 分发正确")

# ---------- 测试 7：复验不达目标 → 重算下一轮（副本延迟收敛） ----------
seq = {'get': 0, 'move': 0}


def fake_get_toc3(book_id):
    seq['get'] += 1
    # 第 1 次读：乱序；第 2 次读（第 1 轮复验）：仍未生效；第 3 次读（第 2 轮）：正确
    if seq['get'] >= 3:
        return [{'type': 'DOC', 'title': 'A', 'uuid': 'a'},
                {'type': 'DOC', 'title': 'B', 'uuid': 'b'}]
    return [{'type': 'DOC', 'title': 'B', 'uuid': 'b'},
            {'type': 'DOC', 'title': 'A', 'uuid': 'a'}]


def fake_call3(tool, args_dict, timeout=60, retries=2):
    if tool == 'yuque_update_toc':
        seq['move'] += 1
        return {'data': 'ok'}
    return None


yuque_novel_toc_fix.get_toc_docs = fake_get_toc3
yuque_novel_toc_fix.mcporter_call = fake_call3
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump([['A', ''], ['B', '']], f, ensure_ascii=False)
import time as _t  # noqa: F401
_orig_sleep = yuque_novel_toc_fix.time.sleep
yuque_novel_toc_fix.time.sleep = lambda *a, **k: None   # 跳过轮间等待，测试跑快
ok = yuque_novel_toc_fix.reorder('1', tmp, verbose=False)
yuque_novel_toc_fix.time.sleep = _orig_sleep
assert ok, "第 2 轮应收敛为 True"
assert seq['move'] == 1, f"只需一轮移动，第二轮重读已是正确顺序，实际 {seq['move']}"
os.remove(tmp)
print("✅ 复验未生效：自动重算下一轮并收敛")

print("\n🎉 全部 7 项测试通过")
