#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
爬取 sophistiplate.com(Shopify 独立站)的「节日 + 餐具/杯子/纸巾」商品。

证据策略: 只保留在站内「Actual Best Sellers」畅销排行榜上有名(有排名)的商品,
证据类型 = Best Seller排名, 值 = 该商品在热销榜中的位置 #N。
无任何排名/畅销标签的商品丢弃(用户要求必须有证据)。

输出: indep_items.json — 待入库清单(字段对齐工作台)
"""
import re, os, json, time, random, sys

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
BASE = "https://sophistiplate.com"
OUT = "indep_items.json"
IMG_DIR = "images/independent"

TERM_RE = re.compile(r'cutlery|silverware|utensil|fork|spoon|knife|napkin|napkins|guest towel|\bcup|mug|tumbler|tumbler', re.I)
HOLIDAY_MAP = [
    (re.compile(r'halloween|pumpkin|spider|ghost|skull|bat\b|witch', re.I), "万圣节"),
    (re.compile(r'thanksgiving|harvest|turkey|fall|thanks', re.I), "感恩节"),
    (re.compile(r'christmas|xmas|santa|hanukkah|reindeer|snowflake|ornament', re.I), "圣诞节"),
]
DESIGN_MAP = [
    (re.compile(r'cutlery|silverware|utensil|fork|spoon|knife', re.I), "餐具"),
    (re.compile(r'napkin|guest towel', re.I), "纸巾"),
    (re.compile(r'\bcup|mug|tumbler', re.I), "杯子"),
]

def get_json(url, session):
    for _ in range(4):
        try:
            r = session.get(url, headers={"User-Agent": UA}, timeout=25)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print("  GET失败:", url[:80], repr(e)[:60])
            time.sleep(3)
    return None

def fetch_all_products(session):
    prod = {}
    for page in range(1, 30):
        d = get_json(f"{BASE}/products.json?limit=250&page={page}", session)
        if not d or not d.get("products"):
            break
        for p in d["products"]:
            prod[p["id"]] = p
        print(f"  products.json 第{page}页: 累计 {len(prod)}")
        if len(d["products"]) < 250:
            break
        time.sleep(0.5)
    return prod

def fetch_best_seller_rank(session):
    """Actual best sellers 集合, 按返回顺序给排名(前 300 足够, 排名越前越可信)"""
    rank = {}
    for page in range(1, 15):
        d = get_json(f"{BASE}/collections/actual-best-sellers/products.json?limit=250&page={page}", session)
        if not d or not d.get("products"):
            break
        for i, p in enumerate(d["products"], 1):
            rank.setdefault(p["id"], (page - 1) * 250 + i)
        print(f"  best-sellers 第{page}页: 已排名 {len(rank)}")
        if len(d["products"]) < 250:
            break
        time.sleep(0.5)
    return rank

def classify(text):
    for rx, c in DESIGN_MAP:
        if rx.search(text):
            return c
    return "素材图"

def detect_holiday(title, tags):
    blob = title + " " + " ".join(tags if isinstance(tags, list) else [])
    for rx, h in HOLIDAY_MAP:
        if rx.search(blob):
            return h
    return None

def main():
    import requests
    s = requests.Session()
    os.makedirs(IMG_DIR, exist_ok=True)

    print("[1/3] 拉取全部商品…")
    prod = fetch_all_products(s)
    print(f"商品总数: {len(prod)}")

    print("[2/3] 拉取畅销榜排名…")
    rank = fetch_best_seller_rank(s)
    print(f"有排名商品: {len(rank)}")

    # 已有工作台独立站 URL 去重
    existing = set()
    if os.path.exists("index.html"):
        html = open("index.html", encoding="utf-8").read()
        existing = set(re.findall(r'"source_url":\s*"https://sophistiplate\.com/products/[^"]+"', html))
    print(f"已有 sophistiplate 条目(去重): {len(existing)}")

    out = []
    for pid, p in prod.items():
        title = p.get("title", "")
        tags = p.get("tags", [])
        # 仅按标题判定是否为 餐具/杯子/纸巾 (避免 "plates & napkins" 这类组合标签误抓盘子)
        if not TERM_RE.search(title):
            continue
        hol = detect_holiday(title, tags)
        if not hol:
            continue
        r = rank.get(pid)
        if not r:
            continue  # 必须有畅销证据
        v = p.get("variants", [{}])
        price = v[0].get("price", "") if v else ""
        img = p.get("images", [{}])
        imgurl = img[0].get("src", "") if img else ""
        handle = p.get("handle", pid)
        out.append({
            "platform": "独立站",
            "brand": "sophistiplate.com",
            "title": title,
            "holiday": hol,
            "design_type": classify(title),
            "source_url": f"{BASE}/products/{handle}",
            "price": f"${price}",
            "evidence_type": "Best Seller排名",
            "evidence_value": f"#{r}",
            "evidence_note": f"站内 Actual Best Sellers 榜第{r}名 | 标签: {', '.join(tags[:8])}",
            "img_remote": imgurl,
            "tags": ",".join(tags[:10]),
            "asin": "", "collected_by": "AI采集",
            "collected_at": time.strftime("%Y-%m-%d %H:%M"),
        })

    # 去重
    seen, uniq = set(), []
    for r in out:
        if r["source_url"] in seen or r["source_url"] in existing:
            continue
        seen.add(r["source_url"]); uniq.append(r)
    out = uniq

    # 下载图片(并行, 短超时, 失败跳过)
    print(f"[3/3] 命中 {len(out)} 条, 并行下载主图…")
    from concurrent.futures import ThreadPoolExecutor, as_completed
    def dl(r):
        fn = re.sub(r'[^A-Za-z0-9]', '_', r["source_url"].split('/')[-1])[:60]
        local = os.path.join(IMG_DIR, fn + ".jpg")
        r["img_local"] = local
        if os.path.exists(local) and os.path.getsize(local) > 3000:
            return "ok"
        try:
            rr = s.get(r["img_remote"], headers={"User-Agent": UA}, timeout=12)
            if rr.status_code == 200 and len(rr.content) > 3000:
                open(local, "wb").write(rr.content); return "new"
            return "skip"
        except Exception:
            return "skip"
    got = ok = skip = 0
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(dl, r): r for r in out}
        for f in as_completed(futs):
            res = f.result()
            if res == "new": got += 1
            elif res == "ok": ok += 1
            else: skip += 1
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"✅ 独立站可用: {len(out)} 条 (有畅销证据) | 图新下载 {got} 已有 {ok} 失败 {skip} -> {OUT}")

if __name__ == "__main__":
    main()
