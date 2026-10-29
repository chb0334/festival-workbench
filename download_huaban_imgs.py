#!/usr/bin/env python3.11
"""把工作台里花瓣网记录的图片下载到本地仓库，解决花瓣 CDN auth_key 过期裂图。

流程:
  1. 读取 index.html DATA 中 platform=="花瓣网" 的记录（拿 source_url 即 pin 页）
  2. 带用户 cookie 用 Playwright 逐个打开 pin 页，取 og:image 新鲜签名 URL
  3. 同一浏览器上下文内立刻下载图片 -> images/huaban/<pin_id>.webp
  4. 输出映射 huaban_img_map.json: {source_url: 本地文件名}

用法:
  python3.11 download_huaban_imgs.py --limit 1    # 先验证 1 张
  python3.11 download_huaban_imgs.py              # 全量 219 张
  python3.11 download_huaban_imgs.py --resume     # 跳过已下载的
"""
import re, json, os, time, sys, argparse
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

OUT_DIR = "images/huaban"
MAP_FILE = "huaban_img_map.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def load_cookies(path="huaban_cookies.txt"):
    txt = open(path, encoding="utf-8").read().strip()
    cookies = []
    for part in txt.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies.append({"name": k.strip(), "value": v.strip(),
                            "domain": ".huaban.com", "path": "/"})
    return cookies


def load_huaban_records():
    s = open("index.html", encoding="utf-8").read()
    m = re.search(r"var DATA\s*=\s*(\[.*?\]);", s, re.S)
    arr = json.loads(m.group(1))
    return [r for r in arr if r.get("platform") == "花瓣网" and r.get("source_url")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    recs = load_huaban_records()
    mapping = {}
    if a.resume and os.path.exists(MAP_FILE):
        mapping = json.load(open(MAP_FILE, encoding="utf-8"))

    todo = [r for r in recs if r["source_url"] not in mapping]
    if a.limit:
        todo = todo[: a.limit]
    print(f"花瓣网记录 {len(recs)} | 已下载 {len(mapping)} | 本次待下载 {len(todo)}")

    cookies = load_cookies()
    ok = fail = 0
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True,
                              args=["--disable-blink-features=AutomationControlled",
                                    "--no-sandbox"])
        ctx = b.new_context(user_agent=UA, locale="zh-CN")
        ctx.add_cookies(cookies)
        pg = ctx.new_page()
        pg.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        pg.set_default_timeout(30000)

        for i, r in enumerate(todo, 1):
            pin_url = r["source_url"]
            pin_id = urlparse(pin_url).path.rsplit("/", 1)[-1] or f"p{i}"
            fname = f"{pin_id}.webp"
            fpath = os.path.join(OUT_DIR, fname)
            try:
                pg.goto(pin_url, timeout=30000, wait_until="domcontentloaded")
                time.sleep(2.5)
                img_url = pg.evaluate(
                    "()=>{const m=document.querySelector('meta[property=\"og:image\"]');"
                    "return m?m.content:'';}")
                if not img_url:
                    # 回退：页面里第一张 hbimg 大图
                    img_url = pg.evaluate(
                        "()=>{const im=[...document.images]"
                        ".find(x=>(x.src||'').includes('hbimg'));return im?im.src:'';}")
                if not img_url:
                    raise RuntimeError("页面无图片")
                resp = ctx.request.get(img_url, timeout=20000)
                if resp.status != 200:
                    raise RuntimeError(f"下载 HTTP {resp.status}")
                body = resp.body()
                if len(body) < 500:
                    raise RuntimeError(f"内容过小 {len(body)}B")
                open(fpath, "wb").write(body)
                mapping[pin_url] = fname
                ok += 1
                print(f"  [{i}/{len(todo)}] {pin_id} ✓ {len(body)//1024}KB")
            except Exception as e:
                fail += 1
                print(f"  [{i}/{len(todo)}] {pin_id} ✗ {repr(e)[:70]}")
            if i % 20 == 0:
                json.dump(mapping, open(MAP_FILE, "w", encoding="utf-8"),
                          ensure_ascii=False, indent=1)
                print(f"  >> 映射已保存 {len(mapping)} 条")
            time.sleep(1.5)
        b.close()

    json.dump(mapping, open(MAP_FILE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n完成: 成功 {ok} | 失败 {fail} | 映射总数 {len(mapping)} -> {MAP_FILE}")


if __name__ == "__main__":
    main()
