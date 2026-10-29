#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""图片类型重划分：盘子 / 杯子 / 餐具 / 纸巾 / 场景图 / 素材图。
按标题关键词优先级分类，四份副本同步。"""
import json, re, subprocess, sys, os
from collections import Counter

COPIES = [
    "index.html",
    "index_online.html",
    "节日工作台数据库/工作台文件/index.html",
    "节日工作台数据库/工作台文件/index_online.html",
]

# 优先级：盘子 → 杯子 → 餐具 → 纸巾（套餐类标题如 plates and napkins 归主品盘子）
P_PLATE   = re.compile(r'plate|dish|charger|盘子', re.I)
P_CUP     = re.compile(r'\bcup|mug|tumbler|杯子', re.I)
P_CUTLERY = re.compile(r'cutlery|silverware|utensil|fork|spoon|knife|spork|tableware|dinnerware|serveware|bowl|straw|餐具', re.I)
P_NAPKIN  = re.compile(r'napkin|纸巾|餐巾', re.I)
P_SERVE   = re.compile(r'tray|platter|board', re.I)  # 托盘类，低优先级（ napkin tray 归纸巾）

def classify(r):
    t = (r.get('title') or '') + ' ' + (r.get('holiday') or '')
    old = r.get('design_type') or ''
    if P_PLATE.search(t):   return '盘子'
    if P_CUP.search(t):     return '杯子'
    if P_CUTLERY.search(t): return '餐具'
    if P_NAPKIN.search(t):  return '纸巾'
    if P_SERVE.search(t):   return '餐具'
    if old == '场景图':     return '场景图'
    return '素材图'  # 兜底：设计灵感/手工帖/无关键词的周边

def load(fp):
    s = open(fp, encoding='utf-8').read()
    i = s.index('var DATA'); st = s.index('[', i); d = 0
    for j in range(st, len(s)):
        if s[j] == '[': d += 1
        elif s[j] == ']':
            d -= 1
            if d == 0: en = j; break
    return s, st, en, json.loads(s[st:en+1])

def save(fp, s, st, en, arr):
    open(fp, 'w', encoding='utf-8').write(s[:st] + json.dumps(arr, ensure_ascii=False) + s[en+1:])

def main():
    apply = '--apply' in sys.argv
    dist = Counter(); changed = 0
    for fp in COPIES:
        if not os.path.exists(fp):
            print('跳过:', fp); continue
        s, st, en, arr = load(fp)
        n = 0
        for r in arr:
            nt = classify(r)
            if r.get('design_type') != nt:
                r['design_type'] = nt; n += 1
            dist[nt] += 1
        print(f'{fp}: 改 {n} 条 (总 {len(arr)})')
        if apply:
            save(fp, s, st, en, arr)
    print('新分布:', dict(dist))
    if apply:
        subprocess.run(['git', 'add', *COPIES], check=False)
        subprocess.run(['git', 'commit', '-q', '-m',
                        '图片类型重划分为：盘子/杯子/餐具/纸巾/场景图/素材图（按标题关键词，四份副本同步）'], check=False)
        print('已 git 提交')

if __name__ == '__main__':
    main()
