#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""统一本地化亚马逊图片：
   1) img 直接是 m.media-amazon.com 远程URL的 -> 下载到 images/I/ 并替换
   2) img 是 images/I/<bn> 但文件缺失的 -> 用亚马逊CDN补下
   对 4 份工作台 HTML 同步处理。"""
import json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
HTMLS = ["index.html", "index_online.html",
         "节日工作台数据库/工作台文件/index.html",
         "节日工作台数据库/工作台文件/index_online.html"]
PAT_URL = re.compile(r"https://m\.media-amazon\.com/images/I/([A-Za-z0-9_%.\-]+\.(?:jpg|jpeg|png|webp|gif))")
PAT_REF = re.compile(r"images/I/([A-Za-z0-9_%.\-]+\.(?:jpg|jpeg|png|webp|gif))")


def collect_targets():
    s = open("index.html", encoding="utf-8").read()
    urls = set(PAT_URL.findall(s))  # basenames from remote urls
    refs = set(PAT_REF.findall(s))  # basenames referenced locally
    missing = [r for r in refs if not os.path.exists("images/I/" + r)]
    # 缺失的用亚马逊CDN补
    for r in missing:
        urls.add(r)
    return urls, missing


def download(bn, tries=4):
    fn = "images/I/" + bn
    if os.path.exists(fn) and os.path.getsize(fn) > 300:
        return ("skip", bn)
    url = "https://m.media-amazon.com/images/I/" + bn
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read()
            if len(data) < 300:
                raise IOError("too small")
            open(fn, "wb").write(data)
            return ("ok", bn)
        except Exception as e:
            if t == tries - 1:
                return ("fail", bn + " | " + str(e)[:60])
            time.sleep(2)
    return ("fail", bn)


def main():
    os.makedirs("images/I", exist_ok=True)
    apply = "--apply" in sys.argv
    urls, missing = collect_targets()
    print("需本地化basename数:", len(urls), " 其中本地缺失需补下:", len(missing))
    if not apply:
        print("（dry）跳过下载与替换")
        return
    ok = skip = fail = 0
    fails = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(download, b): b for b in urls}
        for f in as_completed(futs):
            status, b = f.result()
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip += 1
            else:
                fail += 1
                fails.append(b)
    print("下载: ok=%d skip=%d fail=%d" % (ok, skip, fail))
    for x in fails:
        print("  失败:", x)
    # 替换 4 份 HTML 的远程URL
    for fp in HTMLS:
        txt = open(fp, encoding="utf-8").read()
        new = PAT_URL.sub(r"images/I/\1", txt)
        left = len(PAT_URL.findall(new))
        open(fp, "w", encoding="utf-8").write(new)
        print("[%s] 远程URL替换后剩余: %d" % (fp, left))
    # 复验
    urls2, missing2 = collect_targets()
    print("复验: 本地引用唯一=%d 仍缺失=%d 残留远程URL=%d" %
          (len(urls2), len(missing2), len(PAT_URL.findall(open("index.html", encoding="utf-8").read()))))


if __name__ == "__main__":
    main()
