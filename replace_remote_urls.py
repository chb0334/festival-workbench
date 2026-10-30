#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""把 4 份工作台 HTML 里的 workbuddy-space-static 远程 URL 替换为本地 images/remote/ 路径。"""
import json, os, re, sys

HTMLS = ["index.html", "index_online.html",
         "节日工作台数据库/工作台文件/index.html",
         "节日工作台数据库/工作台文件/index_online.html"]
PAT = re.compile(r"https://workbuddy-space-static\.codebuddy\.work/image/([A-Za-z0-9_]+\.(?:jpg|jpeg|png|webp|gif))")

apply = "--apply" in sys.argv

# 先校验：所有远程URL本地都齐
s = open("index.html", encoding="utf-8").read()
urls = PAT.findall(s)
missing = [u for u in urls if not os.path.exists("images/remote/" + u)]
print("远程图引用数:", len(urls), " 本地缺失:", len(missing))
if missing:
    print("缺失样本:", missing[:5])
    if apply:
        print("⚠ 存在缺失，仍继续替换（缺失的会指向不存在文件）")
else:
    print("✓ 全部远程图已本地化")

for fp in HTMLS:
    txt = open(fp, encoding="utf-8").read()
    n = len(PAT.findall(txt))
    if apply:
        new = PAT.sub(r"images/remote/\1", txt)
        open(fp, "w", encoding="utf-8").write(new)
        # 确认替换干净
        left = len(PAT.findall(new))
        print(f"[{fp}] 替换 {n} 处 -> 剩余远程引用 {left}")
    else:
        print(f"[{fp}] 待替换 {n} 处（dry）")
