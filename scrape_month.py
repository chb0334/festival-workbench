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
  - 亚马逊：反爬强、且销量/评分等“硬证据”需官方 PA-API 密钥（环境变量
    AMAZON_PA_API_KEY / AMAZON_PA_API_SECRET）。未配置密钥时自动跳过并告警，
    不会产出缺证据的空数据。

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
PLATFORMS = ["亚马逊", "独立站", "Pinterest", "TikTok", "Facebook", "Instagram", "Etsy", "其他"]
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


def parse_amazon_pa_api(query, limit=10):
    """
    亚马逊：必须有官方 PA-API 密钥才能合规拿到标题/价格/销量/评分。
    未配置时返回空并告警（不产出缺证据的空数据）。
    """
    key = os.environ.get("AMAZON_PA_API_KEY")
    secret = os.environ.get("AMAZON_PA_API_SECRET")
    if not (key and secret):
        print("  ⚠ 亚马逊未配置 PA-API 密钥，已跳过（不会产出缺证据数据）。")
        return []
    # TODO: 调用 Amazon Product Advertising API 5.0，按 query 检索并映射字段。
    # 该分支需接入官方 SDK 与签名逻辑，此处留接口。
    print("  … 亚马逊 PA-API 分支待接入（需密钥 + 签名）。")
    return []


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
        records += parse_etsy(query)
        records += parse_image_search(query)
        records += parse_amazon_pa_api(query)
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
