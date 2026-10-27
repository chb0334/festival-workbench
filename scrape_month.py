#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
节日产品图库 · 每月采集脚本（按月份打标）
=================================================
用途：每月 30 号跑一次，把当月的节日产品图采集进工作台。
      每条数据自动带上 month（如 "11月"）与 collected_at（采集时间），
      合并进 index_online.html 后，顶栏「采集月份」会自动多出对应月份。

数据源策略（诚实说明）：
  - Pinterest / 独立站 / Etsy / 图片搜索：相对好抓，适合补齐图库与空缺节日。
  - 亚马逊：反爬极强。有官方 PA-API 密钥（环境变量 AMAZON_PA_API_KEY /
    AMAZON_PA_API_SECRET）时走合规接口；无密钥时走网页尽力抓取（跨品类扩展，
    命中率低，且网页不公开月销量，证据只能是评论数/评分、tier 偏低）。
  - 花瓣网（huaban.com）：挂了腾讯 EdgeOne 人机验证，纯请求/无头浏览器都常被拦，
    命中率低，采不到时静默跳过。
  - 西柚洞察（xydc.com）选品雷达热销榜：需登录态，配置环境变量 XIYOU_COOKIE
    （微信扫码登录后的 Cookie）才能返回数据，否则返回登录墙、静默跳过。

运行：
  python3.11 scrape_month.py --year 2026 --month 11
  # 也支持从环境变量读取：SCRAPE_YEAR / SCRAPE_MONTH

依赖：
  pip install requests beautifulsoup4

输出：
  data/2026-11.json   —— 当月采集结果（数组，字段与工作台 DATA 一致）
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

HOLIDAYS = ["万圣节", "感恩节", "圣诞节", "复活节", "情人节", "独立日", "其他"]
PLATFORMS = ["亚马逊", "独立站", "Pinterest", "花瓣网", "西柚平台", "TikTok", "Facebook", "Instagram", "Etsy", "其他"]
DESIGN_TYPES = ["盘子实拍图", "素材图", "平面设计稿", "包装周边", "场景图"]
EVIDENCE_TYPES = ["月销量", "评论数", "点赞", "收藏", "转发", "Best Seller排名", "无"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 各节日对应的英文/搜索关键词（用于跨平台检索）
HOLIDAY_QUERIES = {
    "万圣节": "halloween party plates tableware",
    "感恩节": "thanksgiving dinner plates decor",
    "圣诞节": "christmas tableware plates decor",
    "复活节": "easter table decor plates",
    "情人节": "valentines day tableware decor",
    "独立日": "4th of july patriotic tableware",
    "其他": "festive holiday tableware",
}


def now_tag():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def fetch(url, timeout=15):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.text
    except Exception as e:  # noqa
        print(f"  ! 抓取失败 {url[:60]}… : {e}")
    return ""


def parse_pinterest(query, limit=20):
    """Pinterest 公开搜索页（示例解析，实际需要按页面结构调整/加代理）。"""
    out = []
    url = f"https://www.pinterest.com/search/pins/?q={requests.utils.quote(query)}"
    html = fetch(url)
    if not html:
        return out
    soup = BeautifulSoup(html, "html.parser")
    # Pinterest 内容多为 JS 渲染，纯静态解析命中有限；这里保留结构占位。
    for i, a in enumerate(soup.select("a[href*='/pin/']")[:limit]):
        title = a.get("title") or a.get_text(strip=True) or f"{query} pin {i+1}"
        out.append(_make_record(title, "Pinterest", query, img=""))
    return out


def parse_etsy(query, limit=20):
    """Etsy 搜索结果（示例解析）。"""
    out = []
    url = f"https://www.etsy.com/search?q={requests.utils.quote(query)}"
    html = fetch(url)
    if not html:
        return out
    soup = BeautifulSoup(html, "html.parser")
    for i, card in enumerate(soup.select("[data-listing-id]")[:limit]):
        title = card.get("title") or card.get_text(strip=True)[:80] or f"{query} {i+1}"
        out.append(_make_record(title, "Etsy", query, img=""))
    return out


def parse_image_search(query, limit=20):
    """Bing 图片搜索（示例解析，稳定可用，契合“图库”定位）。"""
    out = []
    url = f"https://www.bing.com/images/search?q={requests.utils.quote(query)}"
    html = fetch(url)
    if not html:
        return out
    soup = BeautifulSoup(html, "html.parser")
    for i, img in enumerate(soup.select("img.mimg")[:limit]):
        src = img.get("src") or img.get("data-src") or ""
        alt = img.get("alt") or f"{query} {i+1}"
        out.append(_make_record(alt, "独立站", query, img=src if src.startswith("http") else ""))
    return out


def parse_huaban(query, limit=20):
    """
    花瓣网（huaban.com）采集：花瓣挂了腾讯 EdgeOne 人机验证，
    纯 requests 会被 "Security Verification" 拦截。这里做三层尽力：
      1) 直接请求搜索页（被拦则跳过）
      2) 本机装有 playwright 时用无头浏览器再试一次
    都失败则静默跳过，不影响其他来源。
    """
    out = []
    q = requests.utils.quote(query)
    url = f"https://huaban.com/search/?q={q}"
    html = fetch(url)
    # 被验证码拦截时返回的是一小段混淆 JS，通过标记识别
    if html and "Security Verification" not in html and "EO_Bot_Ssid" not in html and len(html) > 5000:
        soup = BeautifulSoup(html, "html.parser")
        for i, a in enumerate(soup.select("a[href*='/pins/']")[:limit]):
            title = a.get("title") or a.get_text(strip=True) or f"{query} 花瓣 {i+1}"
            img = ""
            im = a.find("img")
            if im and (im.get("src") or "").startswith("http"):
                img = im["src"]
            rec = _make_record(title, "花瓣网", query, img=img)
            rec["source_url"] = "https://huaban.com" + (a.get("href") or "")
            out.append(rec)
    if not out:
        out = _huaban_playwright(query, limit)
    if not out:
        print("  ⚠ 花瓣网被人机验证拦截（腾讯 EdgeOne），已跳过，不影响其他来源。")
    else:
        print(f"  ✓ 花瓣网命中 {len(out)} 条")
    return out


def _huaban_playwright(query, limit=20):
    """无头浏览器兜底：仅在运行环境装有 playwright 时生效。"""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return []
    out = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            ctx = b.new_context(user_agent=HEADERS["User-Agent"], locale="zh-CN",
                                viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            page.goto(f"https://huaban.com/search/?q={requests.utils.quote(query)}",
                      timeout=45000)
            page.wait_for_timeout(8000)
            if "Security Verification" in page.title():
                b.close()
                return []
            for i, a in enumerate(page.query_selector_all("a[href*='/pins/']")[:limit]):
                title = (a.get_attribute("title") or a.inner_text() or f"{query} 花瓣 {i+1}").strip()
                img = ""
                im = a.query_selector("img")
                if im:
                    src = im.get_attribute("src") or ""
                    if src.startswith("http"):
                        img = src
                rec = _make_record(title, "花瓣网", query, img=img)
                href = a.get_attribute("href") or ""
                rec["source_url"] = "https://huaban.com" + href
                if title or img:
                    out.append(rec)
            b.close()
    except Exception:
        pass
    return out


def parse_xiyou(query, limit=30):
    """
    西柚洞察（xydc.com）选品雷达 · 热销榜（US）。

    重要：该接口需要登录态 Cookie，未登录时返回的是登录墙（HTML）而非数据。
    配置环境变量 XIYOU_COOKIE（浏览器微信扫码登录后的 Cookie 字符串）即可抓取；
    在 GitHub Actions 里配成 secret 也能让每月自动采集生效。
    未配置 / Cookie 失效时会静默跳过，不影响其他来源。

    热销榜是全品类榜单，这里只保留标题含本节日关键词的商品，并映射回对应节日。
    """
    cookie = os.environ.get("XIYOU_COOKIE", "")
    if not cookie:
        print("  ⚠ 西柚平台：未配置 XIYOU_COOKIE（需微信扫码登录态），已跳过。")
        return []
    h = dict(HEADERS)
    h["Referer"] = "https://www.xydc.com/"
    h["Cookie"] = cookie
    h["Accept"] = "application/json, text/plain, */*"
    out = []
    try:
        r = requests.get("https://insights.xydc.com/product-radar/hot-ranking/US",
                         headers=h, timeout=25)
        try:
            j = r.json()
        except Exception:
            print("  ⚠ 西柚平台：返回非 JSON（Cookie 失效/未登录），已跳过。")
            return []
        # 兼容多种结构：直接是列表，或嵌套 data/list/result
        items = j if isinstance(j, list) else (
            j.get("data") or j.get("list") or j.get("result") or [])
        if not isinstance(items, list):
            items = []
        kw = query.split()[0].lower()
        for it in items:
            if not isinstance(it, dict):
                continue
            title = (it.get("title") or it.get("name")
                     or it.get("productTitle") or "")
            asin = (it.get("asin") or it.get("productAsin")
                    or it.get("Asin") or "")
            img = (it.get("image") or it.get("imageUrl")
                   or it.get("mainImage") or it.get("img") or "")
            if isinstance(img, list):
                img = img[0] if img else ""
            # 只保留与本节日相关的热销品
            if kw and kw not in (title + asin).lower():
                continue
            rec = _make_record(title or asin, "西柚平台", query,
                               img=img if str(img).startswith("http") else "")
            rec["asin"] = asin
            rec["source_url"] = ("https://www.amazon.com/dp/" + asin
                                 if asin else ("https://www.xydc.com/detail/product_radar"
                                              "?xiyou-insights-web=%2Fproduct-radar%2Fhot-ranking%2FUS"))
            sales = (it.get("sales") or it.get("salesVolume")
                     or it.get("monthlySales") or it.get("gmv"))
            rank = (it.get("rank") or it.get("hotRank") or it.get("ranking"))
            if sales:
                rec["evidence_type"] = "月销量"
                rec["evidence_value"] = str(sales)
                rec["tier"] = 4
            elif rank:
                rec["evidence_type"] = "Best Seller排名"
                rec["evidence_value"] = str(rank)
                rec["tier"] = 3
            else:
                rec["evidence_type"] = "无"
                rec["tier"] = 1
            out.append(rec)
            if len(out) >= limit:
                break
    except Exception as e:
        print(f"  ⚠ 西柚平台抓取异常：{e}")
        return []
    if not out:
        print("  ⚠ 西柚平台：未匹配到本节日相关热销品（或 Cookie 失效）。")
    else:
        print(f"  ✓ 西柚平台命中 {len(out)} 条")
    return out


def parse_amazon(query, limit=10):
    """
    亚马逊采集：优先官方 PA-API（有密钥时），否则走网页尽力抓取。
    网页抓取在反爬严格时可能命中很少甚至为 0（已做容错，不影响其他来源）。
    注意：亚马逊网页不公开“月销量”，网页抓的证据只能是“评论数/评分”，tier 偏低。
    """
    key = os.environ.get("AMAZON_PA_API_KEY")
    secret = os.environ.get("AMAZON_PA_API_SECRET")
    if key and secret:
        print("  … 亚马逊 PA-API 分支待接入（有密钥）。")
        return []
    return parse_amazon_web(query, limit)


# 跨品类扩展：不再只抓“盘子”，覆盖各类节日产品形态
CATEGORIES = ["plates", "decorations", "ornaments", "table runner",
              "doormat", "throw pillow", "lighting", "gift",
              "banner", "wreath", "tablecloth", "centerpiece"]


def _bing_amazon_asins(kw):
    """用 Bing site:amazon.com 找商品 ASIN（含加密跳转解码尝试）。"""
    asins = set()
    try:
        r = requests.get("https://www.bing.com/search?q=" +
                         requests.utils.quote("site:amazon.com " + kw),
                         headers=HEADERS, timeout=15)
        asins |= set(re.findall(r"amazon\.com/(?:dp|gp/product)/([A-Z0-9]{10})", r.text))
        import urllib.parse as _up
        for c in re.findall(r"u=a1([^&\"]+)", r.text):
            dec = _up.unquote(_up.unquote(c))
            asins |= set(re.findall(r"amazon\.com/(?:dp|gp/product)/([A-Z0-9]{10})", dec))
    except Exception:
        pass
    return asins


def _parse_amazon_product(asin, holiday_query):
    """解析单个亚马逊商品页：标题/评分/评论数/主图；失败返回 None。"""
    try:
        r = requests.get("https://www.amazon.com/dp/" + asin,
                         headers=HEADERS, timeout=15)
        if r.status_code != 200 or len(r.text) < 5000:   # 短页面=拦截页
            return None
        m = re.search(r'id="productTitle"[^>]*>([^<]+)<', r.text)
        title = m.group(1).strip() if m else ""
        if not title:
            return None
        rating = (re.search(r"([\d.]+)\s*out of 5", r.text) or [None, ""])[1]
        reviews = (re.search(r"([\d,]+)\s*ratings?", r.text) or [None, ""])[1]
        im = re.search(r'"large":"(https://m\.media-amazon\.com[^"]+)"', r.text)
        img = im.group(1) if im else ""
        if reviews:
            ev_type, ev_val, tier = "评论数", reviews, 3
        elif rating:
            ev_type, ev_val, tier = "评分", rating, 2
        else:
            ev_type, ev_val, tier = "无", "", 1
        rec = _make_record(title, "亚马逊", holiday_query, img=img)
        rec.update({
            "asin": asin,
            "source_url": "https://www.amazon.com/dp/" + asin,
            "evidence_type": ev_type,
            "evidence_value": ev_val,
            "evidence_note": ("网页抓取（无月销量，建议补 PA-API）"
                             if ev_type != "无" else "网页抓取未获证据"),
            "tier": tier,
            "design_type": ("盘子实拍图" if "plate" in (title + holiday_query).lower()
                            else "素材图"),
        })
        return rec
    except Exception:
        return None


def parse_amazon_web(query, limit=10):
    """网页尽力抓取：跨品类扩展 + 搜索引擎找链接 + 商品页解析，失败静默跳过。"""
    out, seen = [], set()
    for cat in CATEGORIES:
        if len(out) >= limit:
            break
        kw = f"{query} {cat}"
        for asin in _bing_amazon_asins(kw):
            if asin in seen or len(out) >= limit:
                continue
            seen.add(asin)
            rec = _parse_amazon_product(asin, query)
            if rec:
                out.append(rec)
        time.sleep(1)
    if not out:
        print("  ⚠ 亚马逊网页抓取未命中（反爬拦截/网络限制），已跳过，不影响其他来源。")
    else:
        print(f"  ✓ 亚马逊网页抓取命中 {len(out)} 条")
    return out


def _make_record(title, platform, holiday_query, img="", thumb=""):
    # 根据搜索词反推节日（简单映射）
    holiday = "其他"
    for h, q in HOLIDAY_QUERIES.items():
        if q.split()[0].lower() in (title + holiday_query).lower():
            holiday = h
            break
    return {
        "id": None,  # 合并时统一分配
        "year": None,        # 合并时填
        "month": None,       # 合并时填（如 "11月"）
        "holiday": holiday,
        "platform": platform,
        "design_type": "素材图",
        "title": title,
        "source_url": "",
        "brand": "",
        "asin": "",
        "price": "",
        "evidence_type": "无",
        "evidence_value": "",
        "evidence_note": "本月自动采集，建议补充销量/评分证据",
        "collected_by": "AI采集",
        "collected_at": now_tag(),
        "tags": holiday_query.replace(" ", ","),
        "note": "",
        "favorite": False,
        "file": "",
        "thumb": thumb or img,
        "width": 0,
        "height": 0,
        "bytes": 0,
        "hash": "",
        "holiday_reason": holiday_query,
        "material": "",
        "color": "",
        "composition": "",
        "review_status": "",
        "tier": 1,
        "heat": 0.0,
        "img": img,
    }


def run(year, month):
    month_label = f"{int(month)}月"
    print(f"== 开始采集 {year} 年 {month_label} ==")
    records = []
    for holiday, query in HOLIDAY_QUERIES.items():
        print(f"-- 节日：{holiday}（{query}）")
        records += parse_pinterest(query)
        records += parse_huaban(query)
        records += parse_xiyou(query)
        records += parse_etsy(query)
        records += parse_image_search(query)
        records += parse_amazon(query)
        time.sleep(1)  # 礼貌限速
    # 统一打标
    for i, r in enumerate(records, 1):
        r["id"] = 100000 + i  # 合并脚本会重排，避免冲突
        r["year"] = str(year)
        r["month"] = month_label
    db_dir = os.path.join("节日工作台数据库", "每月原始数据")
    os.makedirs(db_dir, exist_ok=True)
    path = os.path.join(db_dir, f"{year}-{int(month):02d}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"== 完成：{len(records)} 条 → {path} ==")
    if not records:
        print("  （本月经所有来源均未采到数据，请检查网络/代理或密钥）")
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=int(os.environ.get("SCRAPE_YEAR", datetime.now().year)))
    ap.add_argument("--month", type=int, default=int(os.environ.get("SCRAPE_MONTH", datetime.now().month)))
    args = ap.parse_args()
    if not (1 <= args.month <= 12):
        print("月份需在 1-12"); sys.exit(1)
    run(args.year, args.month)
