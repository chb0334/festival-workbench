#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""把工作台里所有 workbuddy-space-static 远程图本地化到 images/remote/，
   文件名用 URL basename(hash.jpg)，支持续传、并发、重试。"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = "."
HTMLS = ["index.html", "index_online.html",
         "节日工作台数据库/工作台文件/index.html",
         "节日工作台数据库/工作台文件/index_online.html"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


def collect_urls():
    s = open("index.html", encoding="utf-8").read()
    i = s.index("var DATA")
    st = s.index("[", i)
    d = 0
    for j in range(st, len(s)):
        if s[j] == "[":
            d += 1
        elif s[j] == "]":
            d -= 1
            if d == 0:
                en = j
                break
    arr = json.loads(s[st:en + 1])
    urls = []
    for r in arr:
        img = r.get("img") or ""
        if "workbuddy-space-static.codebuddy.work" in img:
            urls.append(img)
    # 去重保序
    seen = set()
    uniq = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def download(u, tries=3):
    fn = os.path.join("images/remote", os.path.basename(u))
    if os.path.exists(fn) and os.path.getsize(fn) > 500:
        return ("skip", u)
    for t in range(tries):
        try:
            req = urllib.request.Request(
                u, headers={"User-Agent": UA,
                            "Referer": "https://workbuddy-space-static.codebuddy.work/"})
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read()
            if len(data) < 500:
                raise IOError("too small %d" % len(data))
            open(fn, "wb").write(data)
            return ("ok", u)
        except Exception as e:
            if t == tries - 1:
                return ("fail", u + " | " + str(e)[:80])
            time.sleep(1.5)
    return ("fail", u)


def main():
    urls = collect_urls()
    print("待下载远程图(去重):", len(urls))
    os.makedirs("images/remote", exist_ok=True)
    ok = skip = fail = 0
    fails = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=20) as ex:
        futs = {ex.submit(download, u): u for u in urls}
        done = 0
        for f in as_completed(futs):
            status, u = f.result()
            done += 1
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip += 1
            else:
                fail += 1
                fails.append(u)
            if done % 50 == 0:
                print("进度 %d/%d  ok=%d skip=%d fail=%d  耗时%.0fs"
                      % (done, len(urls), ok, skip, fail, time.time() - t0))
    print("=== 完成 ===")
    print("ok=%d skip=%d(已存在) fail=%d 总耗时%.0fs" % (ok, skip, fail, time.time() - t0))
    if fails:
        print("失败列表:")
        for f in fails:
            print("  ", f)


if __name__ == "__main__":
    main()
