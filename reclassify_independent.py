#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
独立站重分类 v2：聚焦"节日餐具/杯具/器皿"竞品。

判定规则（用户指定）：商品必须同时命中
  (1) 节日核心名  +  (2) 餐具品类词(plates/cups/cutlery)
才归入对应节日；否则不收录（剔除）。
例：halloween + plates -> 万圣节；christmas + cups -> 圣诞节。

目的：把独立站从"泛节日商品"收窄到"节日 + 餐具/杯具/器皿"类竞品，
与工作台餐具类节日竞品主线一致，并彻底避免 costume/装饰品串味。

用法：
  python3.11 reclassify_independent.py            # 仅打印统计（dry-run）
  python3.11 reclassify_independent.py --apply    # 写回 index.html
"""
import re
import sys
import json

INDEX = "/workspace/index.html"

# 节日核心名（用于组合判定；用节日名而非泛符号，避免 pumpkin/skeleton 等串入）
HOLIDAY_BASE = {
    "万圣节": ["halloween", "hallowe'en"],
    "圣诞节": ["christmas", "xmas"],
    "感恩节": ["thanksgiving"],
    "独立日": ["4th of july", "july 4", "patriotic", "independence day"],
    "复活节": ["easter"],
    "情人节": ["valentine", "valentines"],
}
# 餐具品类词：用户指定 plates/cups/cutlery，并扩展覆盖 Shopify 派对餐具店
# 真实用词（napkins/bowls/table setting/tableware 等），含单复数
CATS = ["plate", "plates", "cup", "cups", "cutlery", "napkin", "napkins", "bowl",
        "bowls", "tableware", "table setting", "table for", "place card",
        "place cards", "dinnerware", "serveware", "mug", "mugs", "straw",
        "straws", "dish", "dishes", "flatware"]
ORDER = ["万圣节", "圣诞节", "感恩节", "独立日", "复活节", "情人节"]


def _hit(low, kw):
    return re.search(r"(?<![a-z])" + re.escape(kw) + r"(?![a-z])", low) is not None


def _has_cat(low):
    return any(_hit(low, c) for c in CATS)


def classify(text):
    """返回 (节日, 命中节日词) 或 (None, None)。必须 节日名 AND 品类词。"""
    low = " " + (text or "").lower() + " "
    if not _has_cat(low):
        return None, None
    for hol in ORDER:
        for base in HOLIDAY_BASE[hol]:
            if _hit(low, base):
                return hol, base
    return None, None


def load_data():
    s = open(INDEX, encoding="utf-8").read()
    m = re.search(r"var DATA\s*=\s*(\[.*?\]);", s, re.S)
    if not m:
        raise SystemExit("找不到 var DATA")
    return s, json.loads(m.group(1))


def tags_text(rec):
    t = rec.get("tags")
    if isinstance(t, list):
        return " ".join(map(str, t))
    return str(t or "")


def main():
    apply = "--apply" in sys.argv
    s, arr = load_data()
    from collections import Counter
    indep = [r for r in arr if r.get("platform") == "独立站"]
    before = Counter(r["holiday"] for r in indep)

    keep = Counter()
    changed, dropped = [], []
    drop_ids = set()
    for r in arr:
        if r.get("platform") != "独立站":
            continue
        blob = " ".join(filter(None, [r.get("title", ""), tags_text(r), r.get("brand", "")]))
        new_hol, base = classify(blob)
        if new_hol is None:
            drop_ids.add(r["id"])
            dropped.append(r)
        else:
            if r.get("holiday") != new_hol:
                changed.append((r["id"], r.get("holiday"), new_hol, r.get("title", "")[:55]))
            r["holiday"] = new_hol
            r["holiday_reason"] = f"节日餐具竞品：含「{base}」+ 餐具词(plates/cups/cutlery)"
            keep[new_hol] += 1

    print("=== 修正前 独立站各节日分布 ===")
    for k, v in before.most_common():
        print(f"  {k}: {v}")
    print("=== 新规则(节日名+餐具词)后 独立站分布 ===")
    for k, v in keep.most_common():
        print(f"  {k}: {v}")
    print(f"\n独立站总数: {len(indep)} -> {len(indep) - len(dropped)}  (剔除 {len(dropped)})")
    print(f"改标签条目数: {len(changed)}")
    print("\n--- 改标签样例 ---")
    for i, t in changed[:12]:
        print(f"  {i}: {t}")
    print("\n--- 将被剔除的样例(非 节日+餐具) ---")
    for r in dropped[:25]:
        print(f"  [{r.get('holiday')}] {r.get('title','')[:65]}")
    if len(dropped) > 25:
        print(f"  ... 共 {len(dropped)} 条")

    if not apply:
        print("\n[DRY-RUN] 未写回。加 --apply 执行。")
        return

    new_arr = [r for r in arr if r["id"] not in drop_ids]
    new_json = json.dumps(new_arr, ensure_ascii=False)
    new_s = re.sub(r"(var DATA\s*=\s*)\[.*?\];", lambda m: m.group(1) + new_json + ";", s, flags=re.S, count=1)
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(new_s)
    print(f"\n[APPLIED] 已写回 index.html，剩余记录 {len(new_arr)} 条。")


if __name__ == "__main__":
    main()
