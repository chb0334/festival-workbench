#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
把某个月采集的 JSON 合并进工作台 index_online.html 的 DATA 数组。
合并后顶栏「采集月份」会自动多出该月份；原数据不动。

运行：
  python3.11 merge_month.py 2026-11          # 自动定位到 节日工作台数据库/每月原始数据/2026-11.json
  python3.11 merge_month.py 节日工作台数据库/每月原始数据/2026-11.json
  python3.11 merge_month.py 2026-11 --html index_online.html

特性：
  - 自动分配不冲突的 id（在现有最大 id 基础上递增）
  - 按 (year,month,holiday,platform,title,source_url) 去重，避免重复跑同月
  - 仅替换 var DATA = ([...]); 这一行，不动其余代码
  - 合并后自动同步一份源文件到 节日工作台数据库/工作台文件/
"""

import argparse
import json
import os
import re
import sys

DATA_RE = re.compile(r"var DATA = (\[.*?\]);", re.S)


def load_html(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def save_html(path, html):
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def merge(html_path, json_path):
    html = load_html(html_path)
    m = DATA_RE.search(html)
    if not m:
        print("✗ 未找到 var DATA = [...]; 结构异常"); sys.exit(1)
    existing = json.loads(m.group(1))

    with open(json_path, encoding="utf-8") as f:
        incoming = json.load(f)
    if not isinstance(incoming, list):
        print("✗ 传入 JSON 必须是数组"); sys.exit(1)

    max_id = max([d.get("id", 0) for d in existing] or [0])
    seen = set()
    for d in existing:
        seen.add(_key(d))

    added = 0
    for d in incoming:
        d.pop("id", None)
        k = _key(d)
        if k in seen:
            continue  # 去重：同月重复跑不重复加
        max_id += 1
        d["id"] = max_id
        if not d.get("year"):
            d["year"] = "2026"
        if not d.get("month"):
            d["month"] = "未标注"
        existing.append(d)
        seen.add(k)
        added += 1

    new_data_js = "var DATA = " + json.dumps(existing, ensure_ascii=False) + ";"
    html = DATA_RE.sub(lambda _: new_data_js, html, count=1)
    save_html(html_path, html)
    # 同步一份源文件到「数据库/工作台文件」，保持数据库文件夹自包含
    try:
        import shutil
        db_src = os.path.join("节日工作台数据库", "工作台文件", "index_online.html")
        os.makedirs(os.path.dirname(db_src), exist_ok=True)
        shutil.copy(html_path, db_src)
    except Exception:
        pass
    print(f"✓ 合并完成：新增 {added} 条，全库现共 {len(existing)} 条。")
    print(f"  月份分布：{_month_dist(existing)}")
    return added


def _key(d):
    return (
        d.get("year", ""), d.get("month", ""), d.get("holiday", ""),
        d.get("platform", ""), (d.get("title") or "")[:60],
        d.get("source_url", "") or d.get("asin", ""),
    )


def _month_dist(data):
    from collections import Counter
    import re as _re
    def mo(d):
        mm = _re.match(r"(\d{4})-(\d{2})", d.get("collected_at") or "")
        return d.get("month") or (f"{int(mm.group(2))}月" if mm else "未标注")
    return dict(Counter(mo(d) for d in data))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("json", help="当月采集结果 JSON；也可直接传 '2026-11' 自动定位到数据库文件夹")
    ap.add_argument("--html", default="index_online.html")
    args = ap.parse_args()
    jp = args.json
    if not jp.endswith(".json"):
        jp = os.path.join("节日工作台数据库", "每月原始数据", f"{jp}.json")
    if not os.path.exists(jp):
        print(f"✗ 找不到数据文件：{jp}"); sys.exit(1)
    merge(args.html, jp)
