#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""爬取亚马逊「节日+餐具/杯子/纸巾」商品，必须带月销量标签才保留。

流程:
  Phase 1  搜索页采集: 9 组关键词 (halloween/thanksgiving/christmas × cutlery/cups/napkins)
  Phase 2  逐 ASIN 详情页: 验证「bought in past month」销量标签(证据), 抓价格/评分/评价数/主图
  Phase 3  下载主图到 images/amz/<ASIN>.jpg 本地化

反爬:
  - Playwright chromium 复用 context, 过一次挑战页
  - 隐藏 webdriver 特征, 随机 UA
  - 每次请求间隔 2.5-4s (用户指定 2-3s 量级), 挑战页自动点击放行
  - 每 5 条 flush 到 amz_items_raw.json / amz_items_final.json, 可断点续跑

输出:
  amz_items_raw.json    — 搜索阶段全部候选
  amz_items_final.json  — 有销量标签的最终清单(入库用)
"""
import re, sys, os, json, time, random, argparse

OUT_RAW = "amz_items_raw.json"
OUT_FINAL = "amz_items_final.json"
IMG_DIR = "images/amz"

HOLIDAYS = [("halloween", "万圣节"), ("thanksgiving", "感恩节"), ("christmas", "圣诞节")]
TERMS = [("cutlery", "餐具"), ("cups", "杯子"), ("napkins", "纸巾")]

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

def jload(path, default):
    if os.path.exists(path):
        try:
            return json.load(open(path))
        except Exception:
            pass
    return default

def jdump(obj, path):
    json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def is_challenge(txt):
    return "click the button below to continue shopping" in txt.lower()

def extract_sales(html):
    m = re.search(r'id="pqv-bought-in-last-month"[^>]*>(.*?)</p>', html, re.I | re.S)
    if m:
        txt = re.sub(r'<[^>]+>', ' ', m.group(1))
        txt = re.sub(r'\s+', ' ', txt).strip()
        if 'bought' in txt.lower():
            val = re.search(r'([\d,.]+\s*[KkMm]?\+?)', txt, re.I)
            return True, (val.group(1).strip() if val else txt)
    m = re.search(r'class="a-text-bold">\s*([\d,]+\s*[KkMm]?\+?)\s*bought', html, re.I)
    if m:
        return True, m.group(1).strip()
    return False, ""

def extract_meta(html):
    """从详情页 HTML 提取 标题/价格/评分/评价数/主图"""
    out = {"title": "", "price": "", "rating": "", "reviews": "", "img": ""}
    m = re.search(r'id="productTitle"[^>]*>\s*(.*?)\s*</', html, re.S)
    if m: out["title"] = re.sub(r'\s+', ' ', m.group(1)).strip()[:300]
    m = re.search(r'class="a-price[^"]*"[^>]*>\s*<span class="a-offscreen">([^<]+)</span>', html)
    if m: out["price"] = m.group(1)
    m = re.search(r'id="acrPopover"[^>]*title="([\d.]+)', html)
    if not m:
        m = re.search(r'([\d.]+)\s+out of 5 stars', html)
    if m: out["rating"] = m.group(1)
    m = re.search(r'id="acrCustomerReviewText"[^>]*>\s*([\d,]+)', html)
    if m: out["reviews"] = m.group(1)
    m = re.search(r'"hiRes"\s*:\s*"(https://m\.media-amazon\.com/images/I/[^"]+)"', html)
    if not m:
        m = re.search(r'id="landingImage"[^>]*data-old-hires="([^"]+)"', html)
    if not m:
        m = re.search(r'id="landingImage"[^>]*src="([^"]+)"', html)
    if m: out["img"] = m.group(1)
    return out

def extract_search_cards(page):
    """从搜索结果页 DOM 抽商品卡"""
    return page.evaluate("""
    () => {
      const out = [];
      document.querySelectorAll('div[data-component-type="s-search-result"][data-asin]').forEach(el => {
        const asin = el.getAttribute('data-asin');
        if (!asin) return;
        const t = el.querySelector('h2 span');
        const price = el.querySelector('.a-price .a-offscreen');
        const rating = el.querySelector('.a-icon-alt');
        const reviews = el.querySelector("span[aria-label*='stars'] + span .s-underline-text, a[href*='reviews'] .s-underline-text");
        const img = el.querySelector('img.s-image');
        const badge = el.textContent.includes('Best Seller') ? 'Best Seller' : '';
        out.push({
          asin: asin,
          title: t ? t.textContent.trim() : '',
          price: price ? price.textContent.trim() : '',
          rating: rating ? rating.textContent.replace(' out of 5 stars','').trim() : '',
          reviews: reviews ? reviews.textContent.trim().replace(/,/g,'') : '',
          img: img ? img.src : '',
          badge: badge
        });
      });
      return out;
    }""")

def safe_goto(pg, url, tries=3):
    for i in range(tries):
        try:
            pg.goto(url, wait_until="domcontentloaded", timeout=35000)
            time.sleep(random.uniform(2.2, 3.2))
            if is_challenge(pg.content()):
                try:
                    pg.locator('button[type="submit"]').first.click(timeout=8000)
                    pg.wait_for_load_state("networkidle", timeout=15000)
                    time.sleep(2)
                except Exception:
                    pass
                pg.goto(url, wait_until="domcontentloaded", timeout=35000)
                time.sleep(random.uniform(2, 3))
            if not is_challenge(pg.content()):
                return True
        except Exception as e:
            print(f"  goto异常: {repr(e)[:80]}")
            time.sleep(3)
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-kw", type=int, default=40, help="每组关键词最多采集条数")
    ap.add_argument("--skip-search", action="store_true", help="跳过搜索阶段(续跑详情阶段)")
    args = ap.parse_args()

    os.makedirs(IMG_DIR, exist_ok=True)
    _raw0 = jload(OUT_RAW, {})
    raw = {}
    if isinstance(_raw0, list):
        for r in _raw0:
            if isinstance(r, dict) and r.get("asin"):
                raw[r["asin"]] = r
    else:
        raw = _raw0 or {}
    _fin0 = jload(OUT_FINAL, [])
    final = {r["asin"]: r for r in _fin0 if isinstance(r, dict) and r.get("asin")}

    # 已有工作台 ASIN, 避免重复入库
    exist = set()
    if os.path.exists("index.html"):
        s = open("index.html", encoding="utf-8").read()
        exist = set(re.findall(r'"asin":\s*"([A-Z0-9]{10})"', s))
    print(f"工作台现有亚马逊 ASIN: {len(exist)} 个(将去重跳过)")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True,
                              args=["--no-sandbox", "--disable-dev-shm-usage",
                                    "--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(user_agent=random.choice(UAS),
                            viewport={"width": 1366, "height": 900},
                            locale="en-US", timezone_id="America/New_York")
        ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        pg = ctx.new_page()
        pg.set_default_timeout(35000)


        # 首页过挑战
        print("[首页] 预热过挑战…")
        safe_goto(pg, "https://www.amazon.com/")

        # ===== Phase 1: 搜索 =====
        if not args.skip_search:
            for hen, hcn in HOLIDAYS:
                for term, tcn in TERMS:
                    kw = f"{hen} {term}"
                    if any(r.get("kw") == kw for r in raw.values()):
                        print(f"[搜索] {kw} 已采集过, 跳过")
                        continue
                    print(f"[搜索] {kw} ({hcn}+{tcn}) …")
                    url = f"https://www.amazon.com/s?k={hen}+{term}"
                    if not safe_goto(pg, url):
                        print(f"  ⚠️ {kw} 搜索页失败, 跳过")
                        continue
                    pg.evaluate("window.scrollTo(0, 1200);")
                    time.sleep(random.uniform(1.5, 2.5))
                    pg.evaluate("window.scrollTo(0, 3000);")
                    time.sleep(random.uniform(1.5, 2.5))
                    try:
                        pg.wait_for_selector('div[data-component-type="s-search-result"]', timeout=8000)
                    except Exception:
                        pass
                    cards = extract_search_cards(pg)
                    n = 0
                    for c in cards[:args.per_kw]:
                        a = c["asin"]
                        if a in raw or a in exist:
                            continue
                        raw[a] = {
                            "asin": a, "kw": kw, "holiday": hcn, "term": tcn,
                            "title": c["title"], "price": c["price"],
                            "rating": c["rating"], "reviews": c["reviews"],
                            "img_card": c["img"], "badge": c["badge"],
                        }
                        n += 1
                    print(f"  → 新增 {n} 条候选 (累计 {len(raw)})")
                    jdump(list(raw.values()), OUT_RAW)
                    time.sleep(random.uniform(2.5, 4))
        # 关键词里已存在的不管; 把 term/holiday 补齐(断点续跑时可能缺)
        for a, r in raw.items():
            if "holiday" not in r:
                kw = r.get("kw", "")
                for hen, hcn in HOLIDAYS:
                    if kw.startswith(hen): r["holiday"] = hcn
                for term, tcn in TERMS:
                    if kw.endswith(term): r["term"] = tcn

        # ===== Phase 2: 详情页验证销量标签 =====
        todo = [a for a, r in raw.items() if a not in final]
        print(f"\n[详情] 待验证 {len(todo)} 个 ASIN (已有结论 {len(final)})")
        for i, asin in enumerate(todo, 1):
            url = f"https://www.amazon.com/dp/{asin}?currencyOfPreference=USD"
            ok = safe_goto(pg, url)
            if not ok:
                print(f"  [{i}/{len(todo)}] {asin} ⚠️ 挑战页/超时, 稍后可重跑")
                time.sleep(random.uniform(2.5, 4))
                continue
            try:
                pg.evaluate("window.scrollTo(0,400);")
                time.sleep(1.2)
                pg.evaluate("window.scrollTo(0,0);")
                try:
                    pg.wait_for_selector("#social-proofing-faceout-title-tk_bought", timeout=2500)
                except Exception:
                    pass
            except Exception:
                pass
            html = pg.content()
            has, val = extract_sales(html)
            meta = extract_meta(html)
            r = raw[asin]
            if has:
                rec = dict(r)
                rec.update({
                    "sales_text": val, "title": meta["title"] or r["title"],
                    "price": meta["price"] or r["price"],
                    "rating": r.get("rating") or meta["rating"],
                    "reviews": r.get("reviews") or meta["reviews"],
                    "img_hires": meta["img"], "url": url,
                    "checked_at": time.strftime("%Y-%m-%d"),
                })
                final[asin] = rec
                print(f"  [{i}/{len(todo)}] {asin} ✅ 月销 {val} | {rec['title'][:50]}")
            else:
                print(f"  [{i}/{len(todo)}] {asin} ❌ 无销量标签, 丢弃")
            if i % 5 == 0:
                jdump(list(raw.values()), OUT_RAW)
                jdump(list(final.values()), OUT_FINAL)
            time.sleep(random.uniform(2.5, 4))

        jdump(list(raw.values()), OUT_RAW)
        jdump(list(final.values()), OUT_FINAL)
        b.close()

    # ===== Phase 3: 图片本地化 =====
    print(f"\n[图片] 有标签商品 {len(final)} 个, 下载主图…")
    import requests
    got = miss = 0
    for asin, r in final.items():
        local = os.path.join(IMG_DIR, f"{asin}.jpg")
        if os.path.exists(local) and os.path.getsize(local) > 5000:
            r["img_local"] = local
            continue
        u = r.get("img_hires") or r.get("img_card")
        if not u:
            miss += 1
            continue
        u = re.sub(r'\._[^.]+_\.', '._SL1200_.', u)  # 提升清晰度
        try:
            resp = requests.get(u, headers={"User-Agent": random.choice(UAS)}, timeout=20)
            if resp.status_code == 200 and len(resp.content) > 5000:
                open(local, "wb").write(resp.content)
                r["img_local"] = local
                got += 1
            else:
                miss += 1
        except Exception:
            miss += 1
        time.sleep(random.uniform(0.8, 1.5))
    jdump(list(final.values()), OUT_FINAL)
    print(f"[图片] 新下载 {got} | 失败 {miss} | 完成")

    print(f"\n✅ 最终可用(带月销量标签): {len(final)} 条 -> {OUT_FINAL}")

if __name__ == "__main__":
    main()
