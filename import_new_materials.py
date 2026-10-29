#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
把新抓取的素材(亚马逊 / 独立站)合并进工作台四份副本。

- 亚马逊: amz_items_final.json (已带月销量标签证据 + 本地图 images/amz/<ASIN>.jpg)
- 独立站: indep_items.json (已带 Best Seller排名证据 + 本地图 images/independent/<fn>.jpg)

处理:
  - 按字段模板补齐工作台记录(对齐 index.html 现有结构)
  - design_type / evidence_type / evidence_value 直接沿用
  - 图片用本地相对路径(永久有图, 仿花瓣网做法)
  - 四份副本: index.html / index_online.html (根目录, 前缀 "") +
              节日工作台数据库/工作台文件/{index,index_online}.html (前缀 "../../")
  - 按 ASIN (亚马逊) / source_url (独立站) 去重, 不覆盖已有
  - id 顺延

用法:
  python3.11 import_new_materials.py            # dry-run 预览
  python3.11 import_new_materials.py --apply    # 实际写回四份副本
"""
import os, re, sys, json, shutil
from datetime import datetime

AMZ_J = "amz_items_final.json"
IND_J = "indep_items.json"
IMG_AMZ = "images/amz"
IMG_IND = "images/independent"

FILES = [
    ("index.html", ""),
    ("index_online.html", ""),
    ("节日工作台数据库/工作台文件/index.html", "../../"),
    ("节日工作台数据库/工作台文件/index_online.html", "../../"),
]

DESIGN_TERM = {  # 亚马逊 term -> design_type (兜底)
    "cutlery": "餐具", "cups": "杯子", "napkins": "纸巾",
}

def load_data(path):
    s = open(path, encoding="utf-8").read()
    i = s.index("var DATA")
    st = s.index("[", i)
    d = 0
    for j in range(st, len(s)):
        if s[j] == "[": d += 1
        elif s[j] == "]":
            d -= 1
            if d == 0:
                en = j; break
    return s, st, en, json.loads(s[st:en + 1])

def img_dims(path):
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.width, im.height, os.path.getsize(path)
    except Exception:
        return None, None, os.path.getsize(path) if os.path.exists(path) else 0

def build_amz(r):
    local = r.get("img_local", "")
    w, h, b = img_dims(local)
    term = (r.get("term") or "").lower()
    # term 可能是中文(餐具/杯子/纸巾) 或英文(cutlery/cups/napkins)
    dt = DESIGN_TERM.get(term) or r.get("term") or "素材图"
    note = []
    if r.get("rating"): note.append(f"{r['rating']}★")
    if r.get("reviews"): note.append(f"{r['reviews']} 评价")
    if r.get("price"): note.append(r["price"])
    if r.get("badge"): note.append(r["badge"])
    return {
        "year": "2026", "holiday": r.get("holiday", ""),
        "platform": "亚马逊", "design_type": dt,
        "title": r.get("title", "")[:300],
        "source_url": r.get("url", f"https://www.amazon.com/dp/{r.get('asin','')}"),
        "brand": "", "asin": r.get("asin", ""),
        "price": r.get("price", ""),
        "evidence_type": "月销量",
        "evidence_value": r.get("sales_text", ""),
        "evidence_note": " · ".join(note),
        "collected_by": "AI采集",
        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tags": f"amazon,{r.get('holiday','')}_{r.get('term','')}",
        "favorite": False, "file": "", "thumb": "",
        "width": w or 0, "height": h or 0, "bytes": b or 0,
        "hash": "", "holiday_reason": f"搜索词含「{r.get('kw','')}」",
        "material": "", "color": "", "composition": "",
        "review_status": "", "tier": 3, "heat": 0.0,
        "_img_local": local,
    }

def build_ind(r):
    local = r.get("img_local", "")
    w, h, b = img_dims(local)
    return {
        "year": "2026", "holiday": r.get("holiday", ""),
        "platform": "独立站", "design_type": r.get("design_type", "素材图"),
        "title": r.get("title", "")[:300],
        "source_url": r.get("source_url", ""),
        "brand": r.get("brand", ""), "asin": "",
        "price": r.get("price", ""),
        "evidence_type": r.get("evidence_type", "Best Seller排名"),
        "evidence_value": r.get("evidence_value", ""),
        "evidence_note": r.get("evidence_note", ""),
        "collected_by": "AI采集",
        "collected_at": r.get("collected_at", datetime.now().strftime("%Y-%m-%d %H:%M")),
        "tags": r.get("tags", ""),
        "favorite": False, "file": "", "thumb": "",
        "width": w or 0, "height": h or 0, "bytes": b or 0,
        "hash": "", "holiday_reason": f"独立站畅销榜: {r.get('evidence_value','')}",
        "material": "", "color": "", "composition": "",
        "review_status": "", "tier": 4, "heat": 0.0,
        "_img_local": local,
    }

def main():
    apply = "--apply" in sys.argv
    amz = json.load(open(AMZ_J, encoding="utf-8")) if os.path.exists(AMZ_J) else []
    ind = json.load(open(IND_J, encoding="utf-8")) if os.path.exists(IND_J) else []
    recs = [build_amz(r) for r in amz] + [build_ind(r) for r in ind]
    print(f"待入库: 亚马逊 {len(amz)} + 独立站 {len(ind)} = {len(recs)}")
    if not recs:
        print("无数据可入库")
        return

    total_written = {}
    for path, prefix in FILES:
        if not os.path.exists(path):
            print(f"  ⚠️ 跳过不存在: {path}")
            continue
        s, st, en, arr = load_data(path)
        exist_asin = {r.get("asin") for r in arr if r.get("platform") == "亚马逊"}
        exist_url = {r.get("source_url") for r in arr}
        maxid = max((r.get("id", 0) for r in arr), default=0)
        added = 0
        for r in recs:
            if r["platform"] == "亚马逊":
                if r["asin"] in exist_asin:
                    continue
            else:
                if r["source_url"] in exist_url:
                    continue
            rec = dict(r)
            rel = rec.pop("_img_local", "")
            if rel and os.path.exists(rel):
                rec["img"] = prefix + rel.replace(os.sep, "/")
            else:
                rec["img"] = ""
            rec["id"] = maxid + 1; maxid += 1
            arr.append(rec); added += 1
        if apply:
            new = s[:st] + json.dumps(arr, ensure_ascii=False) + s[en + 1:]
            open(path, "w", encoding="utf-8").write(new)
        total_written[path] = added
        print(f"  {path}: +{added} (去重后)")

    if apply:
        print("\n✅ 已写入四份副本。提交前请检查 git diff。")
    else:
        print("\n[DRY-RUN] 未写文件。加 --apply 实际入库。")

if __name__ == "__main__":
    main()
