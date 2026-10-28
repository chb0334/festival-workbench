#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""按 amz_sales_check.json 中 status=="no" 的 ASIN，删除四份工作台副本里
对应的亚马逊记录，并保持四份同步（仅替换各文件内 var DATA 数组，保留各自 UI 差异）。

默认 dry-run；--apply 才真正写回。
"""
import re, json, argparse

FILES = [
    "/workspace/index.html",
    "/workspace/index_online.html",
    "/workspace/节日工作台数据库/工作台文件/index.html",
    "/workspace/节日工作台数据库/工作台文件/index_online.html",
]

def extract_arr(s):
    i = s.index("var DATA")
    start = s.index("[", i)
    depth = 0
    end = -1
    for j in range(start, len(s)):
        c = s[j]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                end = j
                break
    return s, start, end

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    export = json.load(open(a.file, encoding="utf-8"))
    no_asins = {r["asin"] for r in export if r.get("status") == "no" and r.get("asin")}
    print(f"待删无销量 ASIN 数: {len(no_asins)}\n")

    totals = {}
    for path in FILES:
        s = open(path, encoding="utf-8").read()
        s, start, end = extract_arr(s)
        arr = json.loads(s[start:end + 1])
        before = len(arr)
        amz_before = sum(1 for r in arr if r.get("platform") == "亚马逊")
        arr2 = [r for r in arr if not (r.get("platform") == "亚马逊" and r.get("asin") in no_asins)]
        removed = before - len(arr2)
        amz_after = sum(1 for r in arr2 if r.get("platform") == "亚马逊")
        totals[path] = (before, len(arr2), amz_before, amz_after, removed)
        print(f"{path}")
        print(f"  总 {before} -> {len(arr2)} | 亚马逊 {amz_before} -> {amz_after} | 删除 {removed}")

        if a.apply:
            new_html = s[:start] + json.dumps(arr2, ensure_ascii=False, indent=2) + s[end + 1:]
            open(path, "w", encoding="utf-8").write(new_html)

    if not a.apply:
        print("\n[DRY-RUN] 未实际写回。加 --apply 执行。")

if __name__ == "__main__":
    main()
