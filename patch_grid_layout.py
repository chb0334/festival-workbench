#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""把瀑布流(column-count)改为真正的 CSS Grid 网格，卡片整齐对齐。"""
import sys

COPIES = [
    "index.html",
    "index_online.html",
    "节日工作台数据库/工作台文件/index.html",
    "节日工作台数据库/工作台文件/index_online.html",
]

PATCHES = [
    # 1) 多列瀑布流 -> 真正的网格（密度通过最小列宽控制列数，响应式自动减列）
    (
        ".grid{column-count:4;column-gap:14px}\n"
        ".grid.density-l{column-count:3}\n"
        ".grid.density-m{column-count:4}\n"
        ".grid.density-s{column-count:5}",
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px;align-items:stretch}\n"
        ".grid.density-l{grid-template-columns:repeat(auto-fill,minmax(260px,1fr))}\n"
        ".grid.density-m{grid-template-columns:repeat(auto-fill,minmax(210px,1fr))}\n"
        ".grid.density-s{grid-template-columns:repeat(auto-fill,minmax(165px,1fr))}",
    ),
    # 2) 卡片去掉瀑布流专属属性（inline-block / 100%宽 / margin / break-inside）
    (
        ".card{display:inline-block;width:100%;margin:0 0 14px;background:var(--surface);border:1px solid var(--line);border-radius:10px;overflow:hidden;break-inside:avoid;cursor:pointer;transition:.15s}",
        ".card{background:var(--surface);border:1px solid var(--line);border-radius:10px;overflow:hidden;cursor:pointer;transition:.15s}",
    ),
    # 3) 移动端响应式也改为网格
    (
        "  .grid{column-count:2}",
        "  .grid{grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}",
    ),
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
            report.append(f"  ! 命中{c}次(期望1): {old[:24]}...")
        else:
            report.append(f"  ✓ 命中1次: {old[:24]}...")
    if apply and ok:
        for old, new in PATCHES:
            s = s.replace(old, new)
        open(fp, "w", encoding="utf-8").write(s)
        print(f"[{fp}] 已应用")
    elif apply and not ok:
        print(f"[{fp}] 未应用（异常命中）:\n" + "\n".join(report))
    else:
        print(f"[{fp}] dry:\n" + "\n".join(report))
