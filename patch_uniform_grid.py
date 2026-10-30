#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""统一卡片图片比例：固定 1:1 封面 + object-fit:cover，让网格整齐等高。"""
import sys

COPIES = [
    "index.html",
    "index_online.html",
    "节日工作台数据库/工作台文件/index.html",
    "节日工作台数据库/工作台文件/index_online.html",
]

# 片段替换（短片段，避免转义错误）
PATCHES = [
    # 1) 卡片图容器固定 1:1 比例（背景色占位，避免加载前跳动）
    ("background:#f1efe9}", "background:#f1efe9;aspect-ratio:1/1}"),
    # 2) 图片填满容器并裁切（之前是 width:100%;height:auto 导致高度随比例变）
    ("width:100%;height:auto", "width:100%;height:100%;object-fit:cover"),
    # 3) 无图占位也撑满容器高度（之前固定 140px 会与 1:1 冲突）
    ('style="height:140px"', 'style="height:100%"'),
]

apply = "--apply" in sys.argv

for fp in COPIES:
    s = open(fp, encoding="utf-8").read()
    report = []
    ok = True
    for old, new in PATCHES:
        c = s.count(old)
        if c != 1:
            ok = False
            report.append(f"  ! [{old[:30]}] 命中{c}次(期望1)")
        else:
            report.append(f"  ✓ [{old[:30]}] 命中1次")
    if apply and ok:
        for old, new in PATCHES:
            s = s.replace(old, new)
        open(fp, "w", encoding="utf-8").write(s)
        print(f"[{fp}] 已应用")
    elif apply and not ok:
        print(f"[{fp}] 未应用（存在异常命中）:")
        print("\n".join(report))
    else:
        print(f"[{fp}] dry:")
        print("\n".join(report))
