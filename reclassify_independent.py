#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
独立站数据重分类（精准修正版）。

只处理「被误标为万圣节」的独立站记录，其他节日标签原样保留——
因为原采集靠 Shopify 的 product_type/vendor 字段归类，那些字段没存进
index.html，全量重分类会误删靠 product_type 归类的真节日商品。

对 holiday=="万圣节" 的记录：
  1. 若含其他节日专属强词(christmas/thanksgiving/new year/easter/valentine…)
     -> 改到该节日（修正被万圣节优先级抢占的错误）
  2. 否则若含万圣节专属词 或 costume -> 保留为万圣节
     （costume 是万圣节核心品类，Star Wars/Mickey 等角色服作为万圣节竞品保留）
  3. 否则（无万圣词、无 costume、无其他节日词）-> 剔除（泛品/非节日）

用法：
  python3.11 reclassify_independent.py            # 仅打印统计（dry-run）
  python3.11 reclassify_independent.py --apply    # 写回 index.html
"""
import re
import sys
import json

INDEX = "/workspace/index.html"

HOLIDAY_KW = {
    "万圣节": ["halloween", "hallowe'en", "haunted", "pumpkin", "skeleton",
               "ghost", "witch", "spider", "spooky", "monster", "skull",
               "zombie", "boo", "bat", "mummy", "vampire", "graveyard",
               "cobweb", "cauldron", "candy corn", "jack-o", "jack o",
               "creepy", "frankenstein", "werewolf"],
    "圣诞节": ["christmas", "xmas", "santa", "reindeer", "ornament", "wreath",
               "snowman", "advent", "nutcracker", "gingerbread", "elf",
               "sleigh", "tinsel", "poinsettia", "mistletoe", "stocking",
               "santa claus", "christmas tree", "noel", "grinch"],
    "感恩节": ["thanksgiving", "turkey", "harvest", "gourd", "pilgrim",
               "cornucopia", "thankful"],
    "独立日": ["4th of july", "july 4", "patriotic", "independence day",
               "american flag", "stars and stripes", "star spangled",
               "fireworks", "usa flag", "red white blue"],
    "复活节": ["easter", "bunny", "easter egg", "pastel"],
    "情人节": ["valentine", "valentines", "be mine", "love heart"],
}
OTHER = ["圣诞节", "感恩节", "独立日", "复活节", "情人节"]


def _hit(low, kw):
    return re.search(r"(?<![a-z])" + re.escape(kw) + r"(?![a-z])", low) is not None


def reclassify_halloween(text):
    """返回 (新节日, 命中词)。仅用于原 holiday=='万圣节' 的记录。"""
    low = " " + (text or "").lower() + " "
    # 1. 其他节日强词优先（修正抢占）
    for hol in OTHER:
        for kw in HOLIDAY_KW[hol]:
            if _hit(low, kw):
                return hol, kw
    # 2. 万圣节保留：专属词 或 costume
    for kw in HOLIDAY_KW["万圣节"]:
        if _hit(low, kw):
            return "万圣节", kw
    if _hit(low, "costume") or _hit(low, "costumes"):
        return "万圣节", "costume"
    # 3. 都不满足 -> 剔除
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
    before_h = Counter(r["holiday"] for r in indep if r["holiday"] == "万圣节")

    keep_count, change_count, drop_count = 0, 0, 0
    moved = Counter()          # 万圣节 -> 其他节日 的迁移计数
    dropped_samples, changed_samples = [], []

    drop_ids = set()
    for r in arr:
        if r.get("platform") != "独立站" or r.get("holiday") != "万圣节":
            continue
        blob = " ".join(filter(None, [r.get("title", ""), tags_text(r), r.get("brand", "")]))
        new_hol, kw = reclassify_halloween(blob)
        if new_hol is None:
            drop_ids.add(r["id"])
            drop_count += 1
            dropped_samples.append(r.get("title", "")[:70])
        else:
            if new_hol != "万圣节":
                change_count += 1
                moved[new_hol] += 1
                changed_samples.append((new_hol, r.get("title", "")[:60]))
            else:
                keep_count += 1
            r["holiday"] = new_hol
            r["holiday_reason"] = (
                f"标题/标签含「{kw}」（重分类修正）" if new_hol != "万圣节"
                else f"万圣节竞品：含「{kw}」"
            )

    print("=== 万圣节标签处理前：独立站中被标为万圣节 =", sum(before_h.values()), "条 ===")
    print("=== 精准修正结果（仅作用于万圣节标签）===")
    print(f"  保留为万圣节 : {keep_count}")
    print(f"  改到其他节日 : {change_count}  -> {dict(moved)}")
    print(f"  剔除(非节日): {drop_count}")
    print(f"\n其他节日标签原样保留：圣诞/感恩节/复活节/独立日/情人节 共 "
          f"{len(indep) - sum(before_h.values())} 条未动")
    print(f"独立站总数: {len(indep)} -> {len(indep) - drop_count}  (净剔除 {drop_count})")
    print("\n--- 改到其他节日的样例 ---")
    for hol, t in changed_samples[:15]:
        print(f"  -> {hol}: {t}")
    print("\n--- 将被剔除的样例(非节日/泛品) ---")
    for t in dropped_samples[:25]:
        print(f"  {t}")
    if len(dropped_samples) > 25:
        print(f"  ... 共 {len(dropped_samples)} 条")

    if not apply:
        print("\n[DRY-RUN] 未写回。加 --apply 执行。")
        return

    new_arr = [r for r in arr if r["id"] not in drop_ids]
    new_json = json.dumps(new_arr, ensure_ascii=False)
    new_s = re.sub(r"(var DATA\s*=\s*)\[.*?\];", lambda m: m.group(1) + new_json + ";", s, flags=re.S)
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(new_s)
    print(f"\n[APPLIED] 已写回 index.html，剩余记录 {len(new_arr)} 条。")


if __name__ == "__main__":
    main()
