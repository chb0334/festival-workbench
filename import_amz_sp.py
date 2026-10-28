#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把「卖家精灵 × 亚马逊」导出数据录入当月原始数据文件。

支持两种输入（自动识别）：
  A. 书签/控制台导出的文本：含 ===AMZ_SP_START=== ... ===AMZ_SP_END===
  B. 卖家精灵「产品数据库」导出的 CSV / Excel（.csv / .xlsx）

用法（拿到用户发来的文件后）：
    python3 import_amz_sp.py --file 导出.csv --year 2026 --month 10
    python3 import_amz_sp.py --file 导出.txt  --year 2026 --month 10   # 书签文本

- 按 ASIN 去重（与当月已有数据比对，避免重复）
- 产出与 scrape_month._make_record 完全一致的记录结构，
  证据类型记为「月销量（卖家精灵）」、tier=5（有销量，最高证据）
- 写入 节日工作台数据库/每月原始数据/YYYY-MM.json
- 之后运行 merge_month.py（或等月底自动合并）即进工作台
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scrape_month as sm  # 复用 HOLIDAY_QUERIES 与 _make_record 字段结构


# ----------------------------------------------------------------------------
# 输入解析
# ----------------------------------------------------------------------------
def parse_export_text(text):
    """书签文本：从多个 ===AMZ_SP_START=== ... ===AMZ_SP_END=== 块解析 JSON。"""
    blocks = re.findall(r"===AMZ_SP_START===(.*?)===AMZ_SP_END===", text, re.S)
    items = []
    for b in blocks:
        try:
            items.extend(json.loads(b))
        except Exception as e:
            print("  ⚠ 某段 JSON 解析失败，已跳过：", e)
    return items


def _find_col(columns, *keys):
    """列名（不区分大小写）包含任一 key 即返回。"""
    for c in columns:
        cl = str(c).lower()
        if any(k in cl for k in keys):
            return c
    return None


def _col_sales(columns):
    """优先「月销量」；其次「销量/sales」但排除「销售额/revenue」。"""
    for c in columns:
        if "月销量" in str(c):
            return c
    for c in columns:
        cl = str(c).lower()
        if ("sales" in cl or "销量" in cl) and "销售额" not in str(c) and "revenue" not in cl:
            return c
    return None


def parse_csv(path):
    """卖家精灵产品数据库导出的 CSV/Excel → 统一 items 结构。"""
    try:
        import pandas as pd
    except Exception as e:
        print("  ⚠ 需要 pandas 读表格：", e)
        return []
    if path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path, encoding="utf-8-sig", on_bad_lines="skip")
    cols = list(df.columns)
    c_asin = _find_col(cols, "asin")
    c_title = _find_col(cols, "产品名称", "名称", "title", "product")
    c_img = _find_col(cols, "图片", "image", "img")
    c_price = _find_col(cols, "价格", "price")
    c_sales = _col_sales(cols)
    c_rev = _find_col(cols, "月销售额", "销售额", "revenue")
    c_rating = _find_col(cols, "评分", "rating")
    c_reviews = _find_col(cols, "评论", "reviews", "ratings")
    if not c_asin:
        print("  ⚠ 未在表头找到 ASIN 列，表头为：", cols)
        return []
    items = []
    for _, row in df.iterrows():
        asin = str(row[c_asin]).strip()
        if not re.match(r"^[A-Z0-9]{10}$", asin):
            continue  # 跳过非标准 ASIN（合计行/表头等）
        g = lambda c: ("" if c is None else str(row[c]).strip())
        title = g(c_title) or asin
        item = {
            "asin": asin,
            "title": title,
            "image": g(c_img),
            "url": "https://www.amazon.com/dp/" + asin,
            "price": g(c_price),
            "sales": g(c_sales),
            "revenue": g(c_rev),
            "rating": g(c_rating),
            "reviews": g(c_reviews),
            "cardText": (title + " " + g(c_sales) + " " + g(c_reviews)).strip(),
        }
        items.append(item)
    print("  CSV 解析：共 %d 行，识别 %d 条有效 ASIN 商品" % (len(df), len(items)))
    return items


def parse_input(path):
    raw = open(path, encoding="utf-8", errors="ignore").read()
    if "===AMZ_SP_START===" in raw:
        return parse_export_text(raw)
    return parse_csv(path)


# ----------------------------------------------------------------------------
# 字段映射 / 记录构造
# ----------------------------------------------------------------------------
def resolve_sales(item):
    s = (item.get("sales") or "").strip()
    if s and s.lower() != "nan":
        return s
    ct = item.get("cardText") or ""
    for p in [r"月销量[：:\s]*([\d,]+(?:\.\d+)?\s*[kKwW]?)",
              r"销量[：:\s]*([\d,]+(?:\.\d+)?\s*[kKwW]?)",
              r"([\d,]+(?:\.\d+)?\s*[kKwW]?)\s*月销"]:
        m = re.search(p, ct, re.I)
        if m:
            return m.group(1).strip()
    return ""


def classify(text):
    low = text.lower()
    for h, q in sm.HOLIDAY_QUERIES.items():
        if q.split()[0].lower() in low:
            return h
    return "其他"


def to_record(item, year, month):
    asin = (item.get("asin") or "").strip()
    title = (item.get("title") or "").strip() or (asin or "亚马逊商品")
    rec = sm._make_record(title, "亚马逊", "")
    sv = resolve_sales(item)
    if sv and re.match(r"^\d+\.0$", sv.strip()):   # CSV 浮点 1200.0 → 1200
        sv = sv.strip()[:-2]
    rec.update({
        "asin": asin,
        "source_url": item.get("url") or ("https://www.amazon.com/dp/" + asin if asin else ""),
        "img": item.get("image") or "",
        "thumb": item.get("image") or "",
        "price": (item.get("price") or "").strip(),
        "year": str(year),
        "month": "%d月" % int(month),
        "holiday": classify(title + " " + (item.get("cardText") or "")),
        "evidence_type": "月销量（卖家精灵）",
        "evidence_value": sv,
        "evidence_note": "卖家精灵产品数据库导出，含月销量估算"
                        + (("；月销售额 " + item["revenue"]) if item.get("revenue") and item["revenue"].lower() != "nan" else ""),
        "tier": 5,
        "collected_by": "卖家精灵导出",
        "collected_at": sm.now_tag(),
        "tags": "amazon,sellersprite",
        "holiday_reason": title,
    })
    return rec


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="卖家精灵导出：书签文本(.txt) 或 产品数据库 CSV/Excel")
    ap.add_argument("--year", default="2026")
    ap.add_argument("--month", default="10")
    ap.add_argument("--target", default=None, help="当月原始数据 JSON 路径（默认自动定位）")
    args = ap.parse_args()

    items = parse_input(args.file)
    if not items:
        print("未解析到商品。书签文本需含 ===AMZ_SP_START=== 包裹；CSV 需含 ASIN 列。")
        return

    target = args.target or os.path.join(
        "节日工作台数据库", "每月原始数据",
        "%s-%02d.json" % (args.year, int(args.month)))
    existing = json.load(open(target, encoding="utf-8")) if os.path.exists(target) else []
    seen = {r.get("asin") for r in existing if r.get("asin")}
    added = 0
    for it in items:
        a = (it.get("asin") or "").strip()
        if a and a in seen:
            continue
        existing.append(to_record(it, args.year, args.month))
        if a:
            seen.add(a)
        added += 1

    json.dump(existing, open(target, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("✅ 录入 %d 条卖家精灵亚马逊数据（去重后；目标文件现共 %d 条）" % (added, len(existing)))
    print("   文件：%s" % target)
    print("   下一步：运行 merge_month.py 合并进工作台，或等月底自动合并。")


if __name__ == "__main__":
    main()
